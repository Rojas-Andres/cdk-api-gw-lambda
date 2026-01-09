import json
import boto3
import os
import gzip
import requests
from pathlib import Path
from collections import defaultdict
from urllib.parse import unquote

s3_client = boto3.client("s3")


def handler(event, context):
    """
    Lambda function triggered when a file is uploaded to S3
    """
    print(f"Received event: {json.dumps(event)}")

    for record in event.get("Records", []):
        # Extract S3 event information
        event_name = record.get("eventName", "")
        bucket_name = record["s3"]["bucket"]["name"]
        object_key_encoded = record["s3"]["object"]["key"]
        # Decode URL-encoded object key (e.g., year%3D2026 -> year=2026)
        object_key = unquote(object_key_encoded)
        object_size = record["s3"]["object"]["size"]

        print(f"Event: {event_name}")
        print(f"Bucket: {bucket_name}")
        print(f"Object Key (encoded): {object_key_encoded}")
        print(f"Object Key (decoded): {object_key}")
        print(f"Object Size: {object_size} bytes")

        # Process the file upload
        if event_name.startswith("ObjectCreated:"):
            print(f"New file uploaded: s3://{bucket_name}/{object_key}")

            # Download file to /tmp (Lambda's writable directory)
            local_file_path = f"/tmp/{Path(object_key).name}"

            try:
                # Download file from S3 to /tmp
                print(f"Downloading file to {local_file_path}...")
                s3_client.download_file(bucket_name, object_key, local_file_path)

                # Get file size
                file_size = os.path.getsize(local_file_path)
                print(f"File downloaded successfully. Size: {file_size} bytes")

                # Read file content
                with open(local_file_path, "rb") as f:
                    file_content = f.read()

                print(f"File content read: {len(file_content)} bytes")

                # Check if file is gzipped and decompress if needed
                if object_key.endswith(".gz") or object_key.endswith(".gzip"):
                    print("File is gzipped, decompressing...")
                    try:
                        decompressed_content = gzip.decompress(file_content)
                        file_content = decompressed_content
                        print(f"Decompressed content size: {len(file_content)} bytes")
                    except Exception as e:
                        print(f"Warning: Could not decompress file: {str(e)}")

                # Decode as text
                try:
                    content_text = file_content.decode("utf-8")
                except UnicodeDecodeError:
                    content_text = file_content.decode("latin-1")

                print("=" * 80)
                print("PROCESSING LOG EVENTS:")
                print("=" * 80)

                # Parse JSON objects (may be concatenated)
                json_objects = []
                current_obj = ""
                brace_count = 0

                for char in content_text:
                    current_obj += char
                    if char == "{":
                        brace_count += 1
                    elif char == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            try:
                                json_obj = json.loads(current_obj)
                                json_objects.append(json_obj)
                            except json.JSONDecodeError as e:
                                print(f"Warning: Could not parse JSON object: {str(e)}")
                            current_obj = ""

                print(f"Found {len(json_objects)} log data messages")
                print("-" * 80)

                # Group logs by logGroup/logStream for Loki streams
                loki_streams = defaultdict(list)

                # Process each log data message
                total_events = 0
                for idx, data_message in enumerate(json_objects, 1):
                    if data_message.get("messageType") != "DATA_MESSAGE":
                        continue

                    log_group = data_message.get("logGroup", "")
                    log_stream = data_message.get("logStream", "")
                    log_events = data_message.get("logEvents", [])

                    print(f"\nData Message #{idx}:")
                    print(f"  Log Group: {log_group}")
                    print(f"  Log Stream: {log_stream}")
                    print(f"  Events Count: {len(log_events)}")

                    # Create stream key for grouping
                    stream_key = f"{log_group}/{log_stream}"

                    # Process each log event
                    for event_idx, log_event in enumerate(log_events, 1):
                        total_events += 1
                        timestamp_ms = log_event.get("timestamp", 0)
                        message_str = log_event.get("message", "")

                        # Convert timestamp from milliseconds to nanoseconds (Loki format)
                        timestamp_ns = str(timestamp_ms * 1_000_000)

                        # Add to Loki stream
                        loki_streams[stream_key].append([timestamp_ns, message_str])

                        # Parse and print the message JSON string
                        try:
                            message_data = json.loads(message_str)
                            print(f"\n  Event #{event_idx}:")
                            print(f"    Timestamp: {timestamp_ms}")
                            print(
                                f"    Request ID: {message_data.get('requestId', 'N/A')}"
                            )
                            print(f"    IP: {message_data.get('ip', 'N/A')}")
                            print(
                                f"    HTTP Method: {message_data.get('httpMethod', 'N/A')}"
                            )
                            print(
                                f"    Resource Path: {message_data.get('resourcePath', 'N/A')}"
                            )
                            print(f"    Status: {message_data.get('status', 'N/A')}")
                            print(
                                f"    Request Time: {message_data.get('requestTime', 'N/A')}"
                            )
                            print(
                                f"    Response Length: {message_data.get('responseLength', 'N/A')}"
                            )
                        except json.JSONDecodeError:
                            print(f"\n  Event #{event_idx}:")
                            print(f"    Timestamp: {timestamp_ms}")
                            print(f"    Message (raw): {message_str}")

                print("\n" + "=" * 80)
                print(f"Total events processed: {total_events}")
                print("=" * 80)

                # Send logs to Loki
                loki_endpoint = os.environ.get("LOKI_ENDPOINT")
                if loki_endpoint:
                    print("\n" + "=" * 80)
                    print("SENDING LOGS TO LOKI:")
                    print("=" * 80)

                    # Build Loki payload
                    loki_payload = {"streams": []}

                    for stream_key, values in loki_streams.items():
                        # Extract logGroup and logStream from key
                        parts = stream_key.split("/", 1)
                        log_group = parts[0] if len(parts) > 0 else "unknown"
                        log_stream = parts[1] if len(parts) > 1 else "unknown"

                        stream_obj = {
                            "stream": {
                                "job": "s3-processor",
                                "logGroup": log_group,
                                "logStream": log_stream,
                                "source": "cloudwatch-logs",
                            },
                            "values": values,
                        }
                        loki_payload["streams"].append(stream_obj)

                    # Send to Loki
                    try:
                        loki_url = f"{loki_endpoint}/loki/api/v1/push"
                        print(
                            f"Sending {len(loki_payload['streams'])} streams to Loki..."
                        )
                        print(f"Loki URL: {loki_url}")

                        response = requests.post(
                            loki_url,
                            json=loki_payload,
                            headers={"Content-Type": "application/json"},
                            timeout=30,
                        )

                        if response.status_code == 204:
                            print(f"✓ Successfully sent logs to Loki")
                            print("Payload: ", loki_payload)
                        else:
                            print(
                                f"✗ Error sending to Loki: Status {response.status_code}, Response: {response.text}"
                            )
                    except Exception as e:
                        print(f"✗ Error sending to Loki: {str(e)}")
                else:
                    print("Warning: LOKI_ENDPOINT not configured, skipping Loki send")

                # Clean up: delete file from /tmp after processing
                os.remove(local_file_path)
                print(f"Temporary file deleted: {local_file_path}")

            except Exception as e:
                print(f"Error processing file: {str(e)}")
                # Clean up on error
                if os.path.exists(local_file_path):
                    os.remove(local_file_path)
                raise

        elif event_name.startswith("ObjectRemoved:"):
            print(f"File deleted: s3://{bucket_name}/{object_key}")

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"message": f"Processed {len(event.get('Records', []))} S3 events"}
        ),
    }
