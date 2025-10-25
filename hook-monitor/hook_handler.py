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
    
    # Read hook input from stdin
    hook_stdin = sys.stdin.read()
    
    # Save the output to ~/tmp/tool_input.jsonl (existing functionality)
    with open(os.path.expanduser("~/tmp/tool_input.jsonl"), "a") as f:
        f.write(hook_stdin)
        f.write("\n")
    
    # If CLAUDE_HOOK_MONITOR_URL is set, send POST request
    if hook_monitor_url:
        try:
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Claude-Hook-Monitor/1.0'
            }
            
            # Add bearer token if available
            if hook_monitor_token:
                headers['Authorization'] = f'Bearer {hook_monitor_token}'
            
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
    else:
        print("No hook monitor URL set", file=sys.stderr)

if __name__ == "__main__":
    main()