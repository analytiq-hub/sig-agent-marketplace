#!/usr/bin/env python3
import json
import sys
import os
import time
from datetime import datetime
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

def parse_transcript_file(transcript_path):
    """
    Parse transcript JSONL file line by line.
    Returns array of dictionaries up to the point of parsing failure.
    """
    parsed_records = []
    
    try:
        with open(transcript_path, 'r', encoding='utf-8') as file:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                    
                try:
                    record = json.loads(line)
                    parsed_records.append(record)
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON on line {line_num}: {e}", file=sys.stderr)
                    print(f"Failed line content: {line}", file=sys.stderr)
                    break  # Stop parsing on first error
                    
    except FileNotFoundError:
        print(f"Error: Transcript file not found: {transcript_path}", file=sys.stderr)
    except Exception as e:
        print(f"Error reading transcript file: {e}", file=sys.stderr)
    
    return parsed_records

def upload_to_log_service(log_url, sigagent_token, hook_data, transcript_records):
    """
    Upload parsed transcript records to the log service.
    """
    try:
        # Prepare payload with hook data and parsed transcript records
        payload = {
            'hook_data': hook_data,
            'transcript_records': transcript_records,
            'upload_timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Convert payload to JSON bytes
        json_data = json.dumps(payload).encode('utf-8')
        
        # Create request with headers
        req = Request(
            log_url,
            data=json_data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'sig-agent/1.0',
                'Authorization': f'Bearer {sigagent_token}'
            }
        )
        
        # Send POST request
        with urlopen(req, timeout=30) as response:
            response_data = response.read().decode('utf-8')
            
            if response.status >= 400:
                print(f"Log service error: {response_data}", file=sys.stderr)
            else:
                print(f"Successfully uploaded {len(transcript_records)} transcript records to log service")
                
    except HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else "No error details"
        print(f"Log service HTTP error {e.code}: {error_body}", file=sys.stderr)
    except URLError as e:
        print(f"Log service URL error: {e.reason}", file=sys.stderr)
    except Exception as e:
        print(f"Log service error: {e}", file=sys.stderr)

def main():
    # Read environment variables
    sigagent_url = os.getenv('SIGAGENT_URL', "https://app.sigagent.ai/fastapi")
    sigagent_token = os.getenv('SIGAGENT_TOKEN')
    
    # Check that both required environment variables are set
    if not sigagent_url:
        print("Error: SIGAGENT_URL environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    if not sigagent_token:
        print("Error: SIGAGENT_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    hook_url = f"{sigagent_url}/v0/claude/hook"
    log_url = f"{sigagent_url}/v0/claude/log"
    
    # Read hook input from stdin
    hook_stdin = sys.stdin.read()
    
    # Parse hook data to extract transcript_path
    try:
        hook_data = json.loads(hook_stdin)
        transcript_path = hook_data.get('transcript_path')
        
        if not transcript_path:
            print("Error: transcript_path not found in hook data", file=sys.stderr)
            sys.exit(1)
            
    except json.JSONDecodeError as e:
        print(f"Error parsing hook JSON: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Parse transcript file
    print(f"Parsing transcript file: {transcript_path}")
    transcript_records = parse_transcript_file(transcript_path)
    print(f"Successfully parsed {len(transcript_records)} transcript records")
    
    # Send POST request to monitoring service
    try:
        # Prepare payload
        payload = {
            'hook_stdin': hook_stdin,
            'hook_timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Convert payload to JSON bytes
        json_data = json.dumps(payload).encode('utf-8')
        
        # Create request with headers
        req = Request(
            hook_url,
            data=json_data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'sig-agent/1.0',
                'Authorization': f'Bearer {sigagent_token}'
            }
        )
        
        # Send POST request
        with urlopen(req, timeout=30) as response:
            response_data = response.read().decode('utf-8')
            
            # Log response for debugging if status indicates error
            if response.status >= 400:
                print(f"Hook monitor error: {response_data}", file=sys.stderr)

        # Upload parsed transcript records to log service
        upload_to_log_service(log_url, sigagent_token, hook_data, transcript_records)
            
    except HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else "No error details"
        print(f"Hook monitor HTTP error {e.code}: {error_body}", file=sys.stderr)
    except URLError as e:
        print(f"Hook monitor URL error: {e.reason}", file=sys.stderr)
    except Exception as e:
        print(f"Hook monitor error: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()