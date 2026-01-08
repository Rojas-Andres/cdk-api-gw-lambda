import json
import boto3
import os
import gzip
from pathlib import Path

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
        object_key = record["s3"]["object"]["key"]
        object_size = record["s3"]["object"]["size"]

        print(f"Event: {event_name}")
        print(f"Bucket: {bucket_name}")
        print(f"Object Key: {object_key}")
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
                # Split by }{ to separate JSON objects
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

                    # Process each log event
                    for event_idx, log_event in enumerate(log_events, 1):
                        total_events += 1
                        timestamp = log_event.get("timestamp", 0)
                        message_str = log_event.get("message", "")

                        # Parse the message JSON string
                        try:
                            message_data = json.loads(message_str)
                            print(f"\n  Event #{event_idx}:")
                            print(f"    Timestamp: {timestamp}")
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
                            print(f"    Timestamp: {timestamp}")
                            print(f"    Message (raw): {message_str}")

                print("\n" + "=" * 80)
                print(f"Total events processed: {total_events}")
                print("=" * 80)

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
