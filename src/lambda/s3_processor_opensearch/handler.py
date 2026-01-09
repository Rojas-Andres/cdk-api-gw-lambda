import json
import os
import gzip
from pathlib import Path
from urllib.parse import unquote
from typing import Any, Dict, Iterable, List

import boto3
import requests
from requests_aws4auth import AWS4Auth

s3_client = boto3.client("s3")
session = boto3.Session()
credentials = session.get_credentials()
region = os.environ.get("AWS_REGION", session.region_name or "us-east-1")
awsauth = (
    AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        region,
        "es",
        session_token=credentials.token,
    )
    if credentials
    else None
)


def _iter_concatenated_json(text: str) -> Iterable[Dict[str, Any]]:
    """Yield JSON objects from concatenated JSON (no delimiters)."""
    current: List[str] = []
    brace_count = 0
    for ch in text:
        current.append(ch)
        if ch == "{":
            brace_count += 1
        elif ch == "}":
            brace_count -= 1
            if brace_count == 0 and current:
                try:
                    yield json.loads("".join(current))
                except json.JSONDecodeError:
                    print("Skipping malformed JSON chunk")
                current = []
    if current:
        print("Warning: leftover data after parsing concatenated JSON")


def _build_documents(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    for msg in messages:
        if msg.get("messageType") != "DATA_MESSAGE":
            continue
        log_group = msg.get("logGroup", "")
        log_stream = msg.get("logStream", "")
        for log_event in msg.get("logEvents", []):
            raw_message = log_event.get("message", "")
            try:
                parsed_message = json.loads(raw_message)
            except json.JSONDecodeError:
                parsed_message = {"raw_message": raw_message}

            doc = {
                "timestamp": log_event.get("timestamp"),
                "id": log_event.get("id"),
                "logGroup": log_group,
                "logStream": log_stream,
                "requestId": parsed_message.get("requestId"),
                "ip": parsed_message.get("ip"),
                "user": parsed_message.get("user"),
                "caller": parsed_message.get("caller"),
                "requestTime": parsed_message.get("requestTime"),
                "httpMethod": parsed_message.get("httpMethod"),
                "resourcePath": parsed_message.get("resourcePath"),
                "status": parsed_message.get("status"),
                "protocol": parsed_message.get("protocol"),
                "responseLength": parsed_message.get("responseLength"),
                "message": raw_message,
            }
            docs.append(doc)
    return docs


def _send_bulk(endpoint: str, index: str, docs: List[Dict[str, Any]]) -> None:
    if not docs:
        print("No documents to send to OpenSearch.")
        return

    lines = []
    for doc in docs:
        lines.append(json.dumps({"index": {"_index": index}}))
        lines.append(json.dumps(doc))
    payload = "\n".join(lines) + "\n"

    headers = {"Content-Type": "application/x-ndjson"}
    response = requests.post(
        f"{endpoint}/_bulk", data=payload, headers=headers, timeout=10, auth=awsauth
    )

    if response.status_code >= 300:
        print(f"OpenSearch bulk error: {response.status_code} -> {response.text[:500]}")
        return

    try:
        body = response.json()
    except Exception:
        print(f"OpenSearch bulk response not JSON: {response.text[:200]}")
        return

    if body.get("errors"):
        print(f"OpenSearch bulk reported errors: {json.dumps(body)[:500]}")
    else:
        print(f"Successfully indexed {len(docs)} documents into {index}")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    print(f"Received event: {json.dumps(event)}")

    opensearch_endpoint = os.environ.get("OPENSEARCH_ENDPOINT")
    opensearch_index = os.environ.get("OPENSEARCH_INDEX", "apigw-logs")

    if not opensearch_endpoint:
        msg = "OPENSEARCH_ENDPOINT not set; skipping ingestion."
        print(msg)
        return {"statusCode": 500, "body": json.dumps({"message": msg})}

    total_docs = 0

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        object_key_encoded = record["s3"]["object"]["key"]
        object_key = unquote(object_key_encoded)

        print(f"Processing s3://{bucket}/{object_key}")

        local_path = f"/tmp/{Path(object_key).name}"
        try:
            s3_client.download_file(bucket, object_key, local_path)

            with open(local_path, "rb") as f:
                file_bytes = f.read()

            if object_key.endswith(".gz") or object_key.endswith(".gzip"):
                file_bytes = gzip.decompress(file_bytes)

            content_text = file_bytes.decode("utf-8")

            messages = list(_iter_concatenated_json(content_text))
            docs = _build_documents(messages)
            total_docs += len(docs)

            _send_bulk(opensearch_endpoint, opensearch_index, docs)
        except Exception as exc:
            print(f"Error processing {object_key}: {exc}")
            raise
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"message": f"Indexed {total_docs} documents into OpenSearch"}
        ),
    }
