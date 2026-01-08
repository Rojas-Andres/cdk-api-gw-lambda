import json


def handler(event, context):
    """
    Lambda function triggered when a file is uploaded to S3
    """
    print(f"Received event: {json.dumps(event)}")
    print("Event", event)

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

            # Add your custom processing logic here
            # Example: Read the file, parse it, send to another service, etc.
            # import boto3
            # s3_client = boto3.client('s3')
            # response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            # file_content = response['Body'].read()

        elif event_name.startswith("ObjectRemoved:"):
            print(f"File deleted: s3://{bucket_name}/{object_key}")

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"message": f"Processed {len(event.get('Records', []))} S3 events"}
        ),
    }
