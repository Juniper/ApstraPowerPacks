# Apstra Task Audit Trail

A service that captures and stores Apstra API task history with extended retention and forwarding capabilities.

## Features

- Polls Apstra API every 60 seconds for task history
- Stores up to 1500 task entries (configurable)
- Forwards events via SNMP traps or webhooks
- Includes CLI interface for log viewing
- Runs as a single Docker container

## Quick Start

```bash
# Build the Docker container
docker build -t apstra-task-audit .

# Run the container
docker run -d \
    --name apstra-task-audit \
    -e APSTRA_API_URL=<your-api-url> \
    -e APSTRA_AUTH_TOKEN=<your-token> \
    apstra-task-audit
```

## Development Setup

1. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the application:
- Copy `config/default_config.yml` to `config/config.yml`
- Update configuration values as needed

4. Run the application:
```bash
python3 -m src.main
```
