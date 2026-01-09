#!/usr/bin/env python3
"""
Script to generate fake CloudWatch Logs data for testing
Generates logs similar to API Gateway access logs
"""

import json
import gzip
import random
import uuid
from datetime import datetime, timedelta


def generate_random_ip():
    """Generate a random IP address."""
    return f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"


def _random_request_id() -> str:
    # Mimic short Base64-like ID ending with '='
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    return "".join(random.choice(alphabet) for _ in range(15)) + "="


def _random_email() -> str:
    user = f"user{random.randint(1000, 9999)}"
    domain = random.choice(["gmail.com", "hotmail.com", "yahoo.com"])
    return f"{user}@{domain}"


def _random_latency(low=80, high=400) -> str:
    return str(random.randint(low, high))


def _random_bytes(low=500, high=4000) -> str:
    return str(random.randint(low, high))


def _random_path() -> str:
    return random.choice(["/api/v1/items", "/api/v1/users", "/api/v1/income"])


def _random_application_version() -> str:
    return random.choice(["colombia", "panama", "mexico"])


def generate_fake_log_event(timestamp_ms, ip=None):
    """Generate a fake log event following the provided schema."""
    log_event_id = str(random.randint(10**50, 10**60))
    if ip is None:
        ip = generate_random_ip()

    request_time = datetime.fromtimestamp(timestamp_ms / 1000).strftime(
        "%d/%b/%Y:%H:%M:%S +0000"
    )

    message = {
        "requestTime": request_time,
        "requestId": _random_request_id(),
        "httpMethod": "GET",
        "path": _random_path(),
        "routeKey": "ANY /api/v1/{proxy+}",
        "status": "200",
        "bytes": _random_bytes(1500, 2500),
        "responseLatency": _random_latency(80, 250),
        "integrationRequestId": "-",
        "functionResponseStatus": "200",
        "integrationLatency": _random_latency(50, 220),
        "integrationServiceStatus": "200",
        "authorizeResultStatus": "-",
        "authorizerRequestId": "-",
        "principalId": "-",
        "email": _random_email(),
        "userId": str(uuid.uuid4()),
        "orgId": str(uuid.uuid4()),
        "idCompany": str(random.randint(10**6, 10**7 - 1)),
        "version": "-",
        "release": "-",
        "ip": ip,
        "host": "test.api.com",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "integrationErrorMessage": "-",
        "dataSource": "pos",
        "applicationVersion": _random_application_version(),
        "referer": "-",
    }

    return {
        "id": log_event_id,
        "timestamp": timestamp_ms,
        "message": json.dumps(message),
    }


def generate_fake_data_message(
    log_stream_id, num_events=1, base_timestamp=None, ip=None
):
    """Generate a fake DATA_MESSAGE with log events"""
    if base_timestamp is None:
        base_timestamp = int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)

    log_events = []
    for i in range(num_events):
        timestamp_ms = base_timestamp + (i * random.randint(100, 500))
        log_events.append(generate_fake_log_event(timestamp_ms, ip=ip))

    return {
        "messageType": "DATA_MESSAGE",
        "owner": "436951894705",
        "logGroup": "/aws/apigateway/LambdaStack-fastapi",
        "logStream": log_stream_id,
        "subscriptionFilters": ["KinesisS3Log"],
        "logEvents": log_events,
    }


def main():
    """Generate fake logs and save to JSON and GZIP files"""
    print("Generating fake log data...")

    # IP específica que tendrá más de 30 peticiones
    specific_ip = "190.99.139.120"
    num_requests_specific_ip = 35  # Más de 30 peticiones para la IP específica

    # Generate multiple data messages (similar to the example)
    num_messages = 30  # Number of DATA_MESSAGE objects with random IPs
    events_per_message = 1  # Events per message

    base_timestamp = int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)

    data_messages = []

    # FIRST: Generate messages with random IPs
    print(f"Generating {num_messages} requests with random IPs")
    for i in range(num_messages):
        log_stream_id = "".join(random.choices("0123456789abcdef", k=32))
        data_message = generate_fake_data_message(
            log_stream_id,
            num_events=events_per_message,
            base_timestamp=base_timestamp + (i * 1000),
            ip=None,  # Random IP
        )
        data_messages.append(data_message)

    # THEN: Generate events with specific IP (more than 30 requests)
    print(f"Generating {num_requests_specific_ip} requests from IP: {specific_ip}")
    for i in range(num_requests_specific_ip):
        log_stream_id = "".join(random.choices("0123456789abcdef", k=32))
        data_message = generate_fake_data_message(
            log_stream_id,
            num_events=events_per_message,
            base_timestamp=base_timestamp + (num_messages * 1000) + (i * 1000),
            ip=specific_ip,
        )
        data_messages.append(data_message)

    # Convert to JSON string (concatenated format like the example)
    json_content = ""
    for msg in data_messages:
        json_content += json.dumps(msg)

    # Save as JSON file (for validation)
    json_filename = "fake_logs.json"
    with open(json_filename, "w") as f:
        f.write(json_content)
    print(f"✓ Saved JSON file: {json_filename} ({len(json_content)} bytes)")

    # Save as GZIP file (without .json extension)
    gzip_filename = "fake_logs.gz"
    compressed_content = gzip.compress(json_content.encode("utf-8"))
    with open(gzip_filename, "wb") as f:
        f.write(compressed_content)

    gzip_size = len(compressed_content)
    print(f"✓ Saved GZIP file: {gzip_filename} ({gzip_size} bytes)")

    # Print summary
    total_events = sum(len(msg["logEvents"]) for msg in data_messages)
    total_messages = len(data_messages)

    # Count requests from specific IP
    specific_ip_count = 0
    for msg in data_messages:
        for event in msg.get("logEvents", []):
            try:
                message_data = json.loads(event.get("message", "{}"))
                if message_data.get("ip") == specific_ip:
                    specific_ip_count += 1
            except:
                pass

    print(f"\nSummary:")
    print(f"  - Total data messages: {total_messages}")
    print(f"  - Total log events: {total_events}")
    print(f"  - Requests from IP {specific_ip}: {specific_ip_count}")
    print(f"  - Requests from other IPs: {total_events - specific_ip_count}")
    print(f"  - JSON file size: {len(json_content)} bytes")
    print(f"  - GZIP file size: {gzip_size} bytes")
    print(f"  - Compression ratio: {len(json_content) / gzip_size:.2f}x")


if __name__ == "__main__":
    main()
