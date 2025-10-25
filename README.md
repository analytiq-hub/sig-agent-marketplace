# SigAgent Skills Plugin

This repository contains a Claude hook handler plugin that monitors and logs tool usage for S. The plugin captures tool input data and optionally forwards it to a monitoring service for analysis and tracking.gent

## About This Plugin

The SigAgent Skills plugin provides a hook handler that:
- Captures tool input data from Claude's stdin
- Forwards the data to a remote monitoring service via HTTP POST
- Requires both monitoring URL and authentication token to be configured
- Supports authentication via bearer token

This plugin is designed for organizations that need to monitor and analyze how their Claude agents are using tools and skills in production environments.

## Features

- **Remote Monitoring**: HTTP POST to configured monitoring URL
- **Authentication**: Bearer token authentication for secure data transmission
- **Error Handling**: Robust error handling with detailed logging
- **Required Configuration**: Both monitoring URL and authentication token must be configured

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd sig-agent-skills
```

2. Make the hook handler executable:
```bash
chmod +x sig-agent-skills/sig_agent_hook_handler.py
```

3. Configure required environment variables:
```bash
export CLAUDE_HOOK_MONITOR_URL="https://your-monitoring-service.com/api/hooks"
export CLAUDE_HOOK_MONITOR_TOKEN="your-bearer-token"
```

## Configuration

The plugin requires the following environment variables:

- `CLAUDE_HOOK_MONITOR_URL` (required): The URL where tool input data should be sent via HTTP POST
- `CLAUDE_HOOK_MONITOR_TOKEN` (required): Bearer token for authentication with the monitoring service

Both environment variables must be set for the plugin to function. The plugin will not operate without both the monitoring URL and authentication token.

## Usage

The hook handler is designed to be used as a Claude hook. It reads tool input from stdin and forwards it to the configured monitoring service.

### Required Setup
Both environment variables must be configured before running the hook handler:

```bash
export CLAUDE_HOOK_MONITOR_URL="https://your-service.com/api/hooks"
export CLAUDE_HOOK_MONITOR_TOKEN="your-token"
./sig-agent-skills/sig_agent_hook_handler.py
```

The plugin will send all tool input data to the specified monitoring URL with the provided authentication token.

### Data Format

The plugin sends the following JSON payload to the monitoring URL:

```json
{
  "hook_stdin": "<raw tool input from Claude>",
  "hook_timestamp": "2024-01-01T12:00:00.000Z"
}
```

The plugin does not save data locally - all tool input is forwarded directly to the monitoring service.

## Requirements

- Python 3.6+
- `requests` library (install with `pip install requests`)

## Error Handling

The plugin includes comprehensive error handling:

- **Network Errors**: If the remote monitoring service is unavailable, the plugin will log the error to stderr
- **Authentication Errors**: Invalid tokens or authentication failures are logged to stderr
- **Timeout Handling**: Requests to the monitoring service timeout after 30 seconds
- **Configuration Errors**: Missing required environment variables are handled gracefully

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure the hook handler script is executable:
   ```bash
   chmod +x sig-agent-skills/sig_agent_hook_handler.py
   ```

2. **Missing Environment Variables**: Ensure both `CLAUDE_HOOK_MONITOR_URL` and `CLAUDE_HOOK_MONITOR_TOKEN` are set:
   ```bash
   echo $CLAUDE_HOOK_MONITOR_URL
   echo $CLAUDE_HOOK_MONITOR_TOKEN
   ```

3. **Network Connectivity**: If remote monitoring fails, check:
   - Network connectivity to the monitoring URL
   - Valid authentication token
   - Correct URL format

4. **Missing Dependencies**: Install required Python packages:
   ```bash
   pip install requests
   ```

### Logs

- **Error Logs**: Check stderr output for error messages and debugging information
- **Monitoring Service**: Check your monitoring service logs for received data

## Security Considerations

- **Token Security**: Store authentication tokens securely and avoid hardcoding them in scripts
- **Data Privacy**: Ensure the monitoring service complies with your organization's data privacy requirements
- **Network Security**: Use HTTPS for the monitoring URL to encrypt data in transit
- **Data Transmission**: All data is transmitted over the network; ensure secure transmission protocols

## License

MIT License.