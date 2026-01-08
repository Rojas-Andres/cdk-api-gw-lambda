import json
import boto3
import os
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

                # Read file content (for small files, you can read directly)
                # For large files, process in chunks or use the file path directly
                with open(local_file_path, "rb") as f:
                    file_content = f.read()

                print(f"File content read: {len(file_content)} bytes")

                # Add your custom processing logic here
                # Example: Parse JSON, CSV, process logs, etc.
                # You can use file_content (bytes) or local_file_path (file path)

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
