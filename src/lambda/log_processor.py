import json
import gzip
import base64

def handler(event, context):
    """
    Lambda function to process CloudWatch Logs from API Gateway subscription filter
    """
    print(f"Received event: {json.dumps(event)}")
    
    # Decode and decompress the log data
    log_data = event['awslogs']['data']
    decoded_data = base64.b64decode(log_data)
    uncompressed_data = gzip.decompress(decoded_data)
    log_events = json.loads(uncompressed_data)
    
    # Process each log event
    for log_event in log_events.get('logEvents', []):
        message = log_event.get('message', '')
        timestamp = log_event.get('timestamp', 0)
        
        # Parse the log message (API Gateway access log format)
        try:
            log_entry = json.loads(message)
            
            # Extract relevant information
            ip = log_entry.get('ip', 'unknown')
            http_method = log_entry.get('httpMethod', 'unknown')
            resource_path = log_entry.get('resourcePath', 'unknown')
            status = log_entry.get('status', 'unknown')
            request_time = log_entry.get('requestTime', 'unknown')
            
            # Your custom processing logic here
            print(f"Processing log: IP={ip}, Method={http_method}, Path={resource_path}, Status={status}")
            
            # Example: Filter or alert on specific conditions
            if status and int(status) >= 400:
                print(f"WARNING: Error detected - Status {status} for {resource_path} from IP {ip}")
            
        except json.JSONDecodeError:
            # If it's not JSON, process as plain text
            print(f"Plain text log: {message}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Processed {len(log_events.get("logEvents", []))} log events'
        })
    }

