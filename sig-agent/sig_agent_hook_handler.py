#!/usr/bin/env python3
import json
import sys
import os
import time
import ssl
import tempfile
from datetime import datetime
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

try:
    import certifi
    CERTIFI_AVAILABLE = True
except ImportError:
    CERTIFI_AVAILABLE = False

def get_log_file_path():
    """
    Get log file path. Uses /tmp on Unix-like systems (macOS, Linux),
    system temp directory on Windows. Since this is debug-only logging,
    /tmp is simpler and more predictable.
    """
    if os.name == 'nt':  # Windows
        temp_dir = tempfile.gettempdir()
        return os.path.join(temp_dir, 'sig_agent_hook_handler.log')
    else:  # Unix-like (macOS, Linux)
        return '/tmp/sig_agent_hook_handler.log'

def log(message, is_error=False):
    """
    Log message to a portable temp directory log file with timestamp.
    Only logs if SIG_AGENT_DEBUG environment variable is set.
    Uses system temp directory (works on Windows, macOS, Linux).
    """
    # Only log if SIG_AGENT_DEBUG is enabled
    if not os.getenv('SIG_AGENT_DEBUG'):
        return
    
    timestamp = datetime.now().isoformat()
    log_entry = f"{timestamp} - {message}\n"
    try:
        log_path = get_log_file_path()
        with open(log_path, 'a', encoding='utf-8') as log_file:
            log_file.write(log_entry)
    except Exception as e:
        # Fallback to stderr if logging fails
        print(f"Logger error: {e}", file=sys.stderr)

def create_ssl_context():
    """
    Create an SSL context with proper certificate verification.
    Most portable approach: tries certifi first, then system defaults,
    only disables verification as last resort.
    """
    # Strategy 1: Use certifi if available (most portable and reliable)
    if CERTIFI_AVAILABLE:
        try:
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            log("Using certifi certificate bundle for SSL verification")
            return ssl_context
        except Exception as e:
            log(f"Failed to use certifi certificates: {e}, trying system defaults", is_error=True)
    
    # Strategy 2: Use system defaults (works on many platforms)
    try:
        ssl_context = ssl.create_default_context()
        # Check if we actually have certificates loaded
        if ssl_context.get_ca_certs():
            log("Using system default certificates for SSL verification")
            return ssl_context
        else:
            log("System default context has no certificates, will disable verification", is_error=True)
    except Exception as e:
        log(f"Failed to create system default SSL context: {e}, disabling verification", is_error=True)
    
    # Strategy 3: Disable verification (last resort - for self-signed certs or broken systems)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    log("WARNING: SSL certificate verification disabled - insecure mode", is_error=True)
    return ssl_context

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
                    log(f"Error parsing JSON on line {line_num}: {e}", is_error=True)
                    log(f"Failed line content: {line}", is_error=True)
                    break  # Stop parsing on first error
                    
    except FileNotFoundError:
        log(f"Error: Transcript file not found: {transcript_path}", is_error=True)
    except Exception as e:
        log(f"Error reading transcript file: {e}", is_error=True)
    
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
        ssl_context = create_ssl_context()
        with urlopen(req, timeout=30, context=ssl_context) as response:
            response_data = response.read().decode('utf-8')
            
            if response.status >= 400:
                log(f"Log service error: {response_data}", is_error=True)
            else:
                log(f"Successfully uploaded {len(transcript_records)} transcript records to log service")
                
    except HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else "No error details"
        log(f"Log service HTTP error {e.code}: {error_body}", is_error=True)
    except URLError as e:
        log(f"Log service URL error: {e.reason}", is_error=True)
    except Exception as e:
        log(f"Log service error: {e}", is_error=True)

def main():
    # Log arguments to /tmp/log.txt
    log(f"main() called with arguments: {sys.argv}")
    
    # Read OpenTelemetry environment variables
    sigagent_url = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')
    sigagent_token = None
    
    # Extract bearer token from OTEL_EXPORTER_OTLP_HEADERS
    otel_headers = os.getenv('OTEL_EXPORTER_OTLP_HEADERS')
    if otel_headers:
        # Parse headers to find Authorization=Bearer token
        headers_parts = otel_headers.split(',')
        for part in headers_parts:
            part = part.strip()
            if part.startswith('Authorization=Bearer '):
                sigagent_token = part.replace('Authorization=Bearer ', '')
                break
    
    # Check that both required OpenTelemetry environment variables are set
    if not sigagent_url:
        log("Error: OTEL_EXPORTER_OTLP_ENDPOINT environment variable is required", is_error=True)
        sys.exit(1)
    
    if not sigagent_token:
        log("Error: OTEL_EXPORTER_OTLP_HEADERS with Authorization=Bearer token is required", is_error=True)
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
            log("Error: transcript_path not found in hook data", is_error=True)
            sys.exit(1)
            
    except json.JSONDecodeError as e:
        log(f"Error parsing hook JSON: {e}", is_error=True)
        sys.exit(1)
    
    # Parse transcript file
    log(f"Parsing transcript file: {transcript_path}")
    transcript_records = parse_transcript_file(transcript_path)
    log(f"Successfully parsed {len(transcript_records)} transcript records")
    
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
        ssl_context = create_ssl_context()
        with urlopen(req, timeout=30, context=ssl_context) as response:
            response_data = response.read().decode('utf-8')
            
            # Log response for debugging if status indicates error
            if response.status >= 400:
                log(f"Hook monitor error: {response_data}", is_error=True)

        # Upload parsed transcript records to log service
        upload_to_log_service(log_url, sigagent_token, hook_data, transcript_records)
            
    except HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else "No error details"
        log(f"Hook monitor HTTP error {e.code}: {error_body}", is_error=True)
    except URLError as e:
        log(f"Hook monitor URL error: {e.reason}", is_error=True)
    except Exception as e:
        log(f"Hook monitor error: {e}", is_error=True)

if __name__ == "__main__":
    main()