import json
import os
import gzip
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import unquote

import boto3
import clickhouse_connect

s3_client = boto3.client("s3")


def _load_bytes(bucket: str, key: str) -> bytes:
    local_path = f"/tmp/{Path(key).name}"
    s3_client.download_file(bucket, key, local_path)
    with open(local_path, "rb") as f:
        data = f.read()
    os.remove(local_path)
    return data


def _parse_records(raw: bytes) -> List[str]:
    # Decompress if needed
    if key_is_gzip := (raw[:2] == b"\x1f\x8b"):
        try:
            raw = gzip.decompress(raw)
        except OSError:
            pass
    text = raw.decode("utf-8", errors="replace")
    # Assume newline-delimited JSON; if not JSON, store raw line
    records: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            json.loads(line)
            records.append(line)
        except json.JSONDecodeError:
            records.append(line)
    return records


def _get_client(
    host: str, port: int, user: str, password: str, secure: bool
) -> clickhouse_connect.driver.Client:
    return clickhouse_connect.get_client(
        host=host,
        port=port,
        username=user,
        password=password,
        secure=secure,
    )


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    print(f"Received event: {json.dumps(event)}")

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

    total_records = 0

    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key_encoded = record["s3"]["object"]["key"]
        key = unquote(key_encoded)
        print(f"Processing s3://{bucket}/{key}")

        try:
            raw = _load_bytes(bucket, key)
            rows = _parse_records(raw)
            if not rows:
                print("No records parsed from object")
                continue

            client = _get_client(host, port, user, password, secure)
            # Insert as a single column 'data' (String). Ensure table schema matches.
            client.insert(
                table=table,
                data=[[r] for r in rows],
                column_names=["data"],
                database=db or None,
            )
            total_records += len(rows)
            print(f"Inserted {len(rows)} rows into {db}.{table}")
        except Exception as exc:
            print(f"Error processing {key}: {exc}")
            raise

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"message": f"Processed {total_records} records into ClickHouse"}
        ),
    }
