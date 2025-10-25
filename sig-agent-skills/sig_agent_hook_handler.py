#!/usr/bin/env python3
import json
import sys
import os
import time
from datetime import datetime
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

def main():
    # Read environment variables
    hook_monitor_url = os.getenv('CLAUDE_HOOK_MONITOR_URL')
    hook_monitor_token = os.getenv('CLAUDE_HOOK_MONITOR_TOKEN')
    
    # Check that both required environment variables are set
    if not hook_monitor_url:
        print("Error: CLAUDE_HOOK_MONITOR_URL environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    if not hook_monitor_token:
        print("Error: CLAUDE_HOOK_MONITOR_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    # Read hook input from stdin
    hook_stdin = sys.stdin.read()
    
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
            hook_monitor_url,
            data=json_data,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'sig-agent-skills/1.0',
                'Authorization': f'Bearer {hook_monitor_token}'
            }
        )
        
        # Send POST request
        with urlopen(req, timeout=30) as response:
            response_data = response.read().decode('utf-8')
            
            # Log response for debugging if status indicates error
            if response.status >= 400:
                print(f"Hook monitor error: {response_data}", file=sys.stderr)
            
    except HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else "No error details"
        print(f"Hook monitor HTTP error {e.code}: {error_body}", file=sys.stderr)
    except URLError as e:
        print(f"Hook monitor URL error: {e.reason}", file=sys.stderr)
    except Exception as e:
        print(f"Hook monitor error: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()