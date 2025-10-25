#!/usr/bin/env python3
import json
import sys
import os
import time
import requests
from datetime import datetime
from urllib.parse import urlparse

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
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Claude-Hook-Monitor/1.0',
            'Authorization': f'Bearer {hook_monitor_token}'
        }
        
        # Prepare payload
        payload = {
            'hook_stdin': hook_stdin,
            'hook_timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        # Send POST request
        response = requests.post(
            hook_monitor_url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        # Log response for debugging
        if response.status_code >= 400:
            print(f"Hook monitor error: {response.text}", file=sys.stderr)
            
    except requests.exceptions.RequestException as e:
        print(f"Hook monitor request failed: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Hook monitor error: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()