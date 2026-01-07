import json
import gzip
import base64
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit

metrics = Metrics(namespace="ApiMonitor")


@metrics.log_metrics  # <--- ESTO ES VITAL para publicar métricas automáticamente
def handler(event, context):
    """
    Lambda function to process CloudWatch Logs from API Gateway subscription filter
    """
    print(f"Received event: {json.dumps(event)}")

    # Decode and decompress the log data
    log_data = event["awslogs"]["data"]
    decoded_data = base64.b64decode(log_data)
    uncompressed_data = gzip.decompress(decoded_data)
    log_events = json.loads(uncompressed_data)

    total_events = len(log_events.get("logEvents", []))

    # Process each log event
    for log_event in log_events.get("logEvents", []):
        message = log_event.get("message", "")

        # Parse the log message (API Gateway access log format)
        try:
            log_entry = json.loads(message)

            # Extract relevant information
            ip = log_entry.get("ip", "unknown")
            resource_path = log_entry.get("resourcePath", "unknown")

            # Add metric with dimensions (clear dimensions before adding new ones)
            metrics.clear_default_dimensions()
            metrics.add_dimension(name="Path", value=resource_path)
            metrics.add_dimension(name="ClientIP", value=ip)
            metrics.add_metric(name="RequestCount", unit=MetricUnit.Count, value=1)

            print(f"Processing log: IP={ip}, Path={resource_path}")

        except json.JSONDecodeError:
            # If it's not JSON, skip this log entry
            print(f"Plain text log (skipping): {message}")

    return {
        "statusCode": 200,
        "body": json.dumps({"message": f"Processed {total_events} log events"}),
    }
