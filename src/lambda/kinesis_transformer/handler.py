import base64
import json
import time
import gzip


def handler(event, context):
    output = []

    for record in event["records"]:
        data_bytes = base64.b64decode(record["data"])

        try:
            payload_decoded = gzip.decompress(data_bytes).decode("utf-8")
        except (gzip.BadGzipFile, OSError):
            payload_decoded = data_bytes.decode("utf-8")

        payload = json.loads(payload_decoded)

        # 🔴 FILTRO CLAVE
        if payload.get("messageType") != "DATA_MESSAGE":
            output.append(
                {
                    "recordId": record["recordId"],
                    "result": "Dropped",
                    "data": record["data"],
                }
            )
            continue

        streams = []

        for log_event in payload.get("logEvents", []):
            ts_nano = str(log_event["timestamp"] * 1_000_000)
            streams.append(
                {
                    "stream": {
                        "job": "cloudwatch",
                        "logGroup": payload.get("logGroup"),
                        "logStream": payload.get("logStream"),
                    },
                    "values": [[ts_nano, log_event["message"]]],
                }
            )

        if not streams:
            output.append(
                {
                    "recordId": record["recordId"],
                    "result": "Dropped",
                    "data": record["data"],
                }
            )
            continue

        loki_payload = {"streams": streams}

        processed_data = base64.b64encode(
            json.dumps(loki_payload).encode("utf-8")
        ).decode("utf-8")

        output.append(
            {
                "recordId": record["recordId"],
                "result": "Ok",
                "data": processed_data,
            }
        )

    return {"records": output}
