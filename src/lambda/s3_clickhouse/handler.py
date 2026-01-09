import json
import os
import gzip
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import unquote

import boto3
import clickhouse_connect

s3_client = boto3.client("s3")

COLUMNS = [
    "requestTime",
    "requestId",
    "httpMethod",
    "path",
    "routeKey",
    "status",
    "bytes",
    "responseLatency",
    "integrationLatency",
    "functionResponseStatus",
    "email",
    "userId",
    "orgId",
    "idCompany",
    "ip",
    "host",
    "userAgent",
    "dataSource",
    "applicationVersion",
    "referer",
]


def _load_bytes(bucket: str, key: str) -> bytes:
    local_path = f"/tmp/{Path(key).name}"
    s3_client.download_file(bucket, key, local_path)
    with open(local_path, "rb") as f:
        data = f.read()
    os.remove(local_path)
    return data


def _iter_concatenated_json(text: str):
    """Yield JSON objects from concatenated JSON without delimiters."""
    buf = []
    brace = 0
    for ch in text:
        buf.append(ch)
        if ch == "{":
            brace += 1
        elif ch == "}":
            brace -= 1
            if brace == 0 and buf:
                chunk = "".join(buf)
                buf = []
                try:
                    yield json.loads(chunk)
                except json.JSONDecodeError:
                    print("Skipping malformed JSON chunk")
    if buf:
        try:
            yield json.loads("".join(buf))
        except json.JSONDecodeError:
            print("Skipping trailing malformed JSON chunk")


def _parse_messages(raw: bytes) -> List[Dict[str, Any]]:
    # Decompress if gzip
    if raw[:2] == b"\x1f\x8b":
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
    text = raw.decode("utf-8", errors="replace")

    messages: List[Dict[str, Any]] = []

    # Try NDJSON first
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    ndjson_success = True
    for ln in lines:
        try:
            obj = json.loads(ln)
            messages.append(obj)
        except json.JSONDecodeError:
            ndjson_success = False
            messages = []
            break

    if ndjson_success and messages:
        return messages

    # Fallback: concatenated JSON
    messages = list(_iter_concatenated_json(text))
    return messages


def _flatten_to_rows(messages: List[Dict[str, Any]]) -> List[List[Any]]:
    rows: List[List[Any]] = []

    def _parse_dt(val: str) -> datetime:
        try:
            return datetime.strptime(val, "%d/%b/%Y:%H:%M:%S %z").astimezone(
                timezone.utc
            )
        except Exception:
            return datetime.now(timezone.utc)

    def _int(val, default=0):
        try:
            return int(val)
        except Exception:
            return default

    def _row_from_msg(msg: Dict[str, Any]) -> List[Any]:
        return [
            _parse_dt(msg.get("requestTime", "")),
            msg.get("requestId", ""),
            msg.get("httpMethod", ""),
            msg.get("path", ""),
            msg.get("routeKey", ""),
            _int(msg.get("status", 0)),
            _int(msg.get("bytes", 0)),
            _int(msg.get("responseLatency", 0)),
            _int(msg.get("integrationLatency", 0)),
            _int(msg.get("functionResponseStatus", 0)),
            msg.get("email", ""),
            msg.get("userId", ""),
            msg.get("orgId", ""),
            msg.get("idCompany", ""),
            msg.get("ip", ""),
            msg.get("host", ""),
            msg.get("userAgent", ""),
            msg.get("dataSource", ""),
            msg.get("applicationVersion", ""),
            msg.get("referer", ""),
        ]

    for msg in messages:
        # CloudWatch subscription style
        if msg.get("messageType") == "DATA_MESSAGE" and "logEvents" in msg:
            for ev in msg.get("logEvents", []):
                raw = ev.get("message", "")
                try:
                    parsed = json.loads(raw)
                    rows.append(_row_from_msg(parsed))
                except json.JSONDecodeError:
                    continue
        else:
            rows.append(_row_from_msg(msg))

    return rows


def _get_client(host: str, port: int, user: str, password: str, secure: bool):
    return clickhouse_connect.get_client(
        host=host,
        port=port,
        username=user,
        password=password,
        secure=secure,
    )


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # print(f"Received event: {json.dumps(event)}")
    print("event received", event)

    db = os.getenv("CLICKHOUSE_DATABASE", "")
    table = os.getenv("CLICKHOUSE_TABLE", "")
    host = os.getenv("CLICKHOUSE_HOST", "")
    port = int(os.getenv("CLICKHOUSE_PORT", "8443"))
    user = os.getenv("CLICKHOUSE_USER", "")
    password = os.getenv("CLICKHOUSE_PASSWORD", "")
    secure = os.getenv("CLICKHOUSE_SECURE", "true").lower() == "true"

    if not db or not table or not host:
        msg = "CLICKHOUSE_DATABASE, CLICKHOUSE_TABLE, or CLICKHOUSE_HOST not set; skipping ingest."
        print(msg)
        return {"statusCode": 200, "body": json.dumps({"message": msg})}

    client = _get_client(host, port, user, password, secure)
    total_rows = 0
    all_rows: List[List[Any]] = []

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key_encoded = record["s3"]["object"]["key"]
        key = unquote(key_encoded)
        print(f"Processing s3://{bucket}/{key}")

        try:
            raw = _load_bytes(bucket, key)
            messages = _parse_messages(raw)
            rows = _flatten_to_rows(messages)
            if not rows:
                print("No rows parsed from object")
                continue

            all_rows.extend(rows)
            print(f"Parsed {len(rows)} rows from {key}")
        except Exception as exc:
            print(f"Error processing {key}: {exc}")
            raise

    if all_rows:
        client.insert(
            table=table,
            data=all_rows,
            column_names=COLUMNS,
            database=db or None,
        )
        total_rows = len(all_rows)
        print(f"Inserted {total_rows} rows into {db}.{table} (bulk in a single call)")
    else:
        print("No rows to insert into ClickHouse.")

    return {
        "statusCode": 200,
        "body": json.dumps({"message": f"Processed {total_rows} rows into ClickHouse"}),
    }
