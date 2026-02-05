"""
OpenClaw Integration - Manages OpenClaw container deployments.

This module handles:
1. Generating OpenClaw configuration files
2. Spinning up OpenClaw Docker containers per workspace
3. Configuring channels (Telegram, Slack, etc.)
4. Communicating with OpenClaw Gateway API
"""
import os
import json
import docker
import logging
import requests
import subprocess
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

# OpenClaw Docker image
OPENCLAW_IMAGE = os.getenv('OPENCLAW_IMAGE', 'openclaw/openclaw:latest')

# Base port for OpenClaw instances (each workspace gets base_port + workspace_id)
OPENCLAW_BASE_PORT = int(os.getenv('OPENCLAW_BASE_PORT', 19000))

# Data directory for OpenClaw workspaces
OPENCLAW_DATA_DIR = Path(os.getenv('OPENCLAW_DATA_DIR', '/var/lib/openclaw-dashboard'))


def get_workspace_data_dir(workspace_id: int) -> Path:
    """Get the data directory for a specific workspace."""
    data_dir = OPENCLAW_DATA_DIR / f"workspace_{workspace_id}"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_workspace_port(workspace_id: int) -> int:
    """Get the assigned port for a workspace's OpenClaw instance."""
    return OPENCLAW_BASE_PORT + workspace_id


def generate_openclaw_config(workspace) -> dict:
    """
    Generate openclaw.json configuration for a workspace.

    Maps dashboard workspace settings to OpenClaw config format.
    """
    # Determine the model provider and model name
    model = workspace.selected_model
    if model.startswith('claude'):
        provider = 'anthropic'
        model_name = f"anthropic/{model}"
    else:
        provider = 'openai'
        model_name = f"openai/{model}"

    config = {
        "agent": {
            "model": model_name,
            "maxTokens": workspace.max_tokens,
            "temperature": getattr(workspace, 'temperature', 0.7),
        },
        "gateway": {
            "port": get_workspace_port(workspace.id),
            "host": "0.0.0.0",
        },
        "channels": {},
        "agents": {
            "defaults": {
                "sandbox": {
                    "mode": "always" if workspace.sandbox_mode else "never",
                }
            }
        }
    }

    # Configure channels
    for channel in workspace.channels.filter(is_active=True):
        if channel.channel_type == 'telegram':
            config["channels"]["telegram"] = {
                "enabled": True,
                "dm": {
                    "policy": "open" if not channel.allowlist else "allowlist",
                    "allowlist": channel.allowlist or [],
                },
                "groups": {
                    "enabled": channel.respond_to_groups,
                }
            }
        elif channel.channel_type == 'slack':
            config["channels"]["slack"] = {
                "enabled": True,
                "dm": {
                    "policy": "open" if not channel.allowlist else "allowlist",
                },
            }
        elif channel.channel_type == 'discord':
            config["channels"]["discord"] = {
                "enabled": True,
            }

    return config


def generate_soul_prompt(workspace) -> str:
    """
    Generate SOUL.md content for the agent's personality/behavior.

    This is the system prompt that defines how the agent behaves.
    """
    soul = f"""# {workspace.agent_name or 'Assistant'}

{workspace.agent_description or 'A helpful AI assistant.'}

## Personality & Behavior

{workspace.system_prompt or 'You are a helpful AI assistant. Be friendly, accurate, and concise.'}

## Welcome Message

When a user first messages you, greet them with:
"{workspace.welcome_message or 'Hello! How can I help you today?'}"
"""

    # Add knowledge base content if available
    knowledge_entries = workspace.knowledge_base.filter(is_active=True)
    if knowledge_entries.exists():
        soul += "\n\n## Knowledge Base\n\n"
        soul += "Use the following information to answer user questions:\n\n"

        for entry in knowledge_entries:
            if entry.resource_type == 'faq':
                soul += f"**Q: {entry.question}**\n"
                soul += f"A: {entry.answer}\n\n"
            elif entry.content:
                soul += f"### {entry.name}\n"
                soul += f"{entry.content}\n\n"

    return soul


def setup_workspace_files(workspace) -> Path:
    """
    Create the configuration files for an OpenClaw workspace.

    Returns the path to the workspace data directory.
    """
    data_dir = get_workspace_data_dir(workspace.id)

    # Create directory structure
    config_dir = data_dir / ".openclaw"
    config_dir.mkdir(parents=True, exist_ok=True)

    workspace_dir = data_dir / ".openclaw" / "workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    credentials_dir = data_dir / ".openclaw" / "credentials"
    credentials_dir.mkdir(parents=True, exist_ok=True)

    # Generate and write openclaw.json
    config = generate_openclaw_config(workspace)
    config_file = config_dir / "openclaw.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    # Generate and write SOUL.md
    soul_content = generate_soul_prompt(workspace)
    soul_file = workspace_dir / "SOUL.md"
    with open(soul_file, 'w') as f:
        f.write(soul_content)

    # Write .env file with API keys
    env_content = ""
    if workspace.owner.anthropic_api_key:
        env_content += f"ANTHROPIC_API_KEY={workspace.owner.anthropic_api_key}\n"
    if workspace.owner.openai_api_key:
        env_content += f"OPENAI_API_KEY={workspace.owner.openai_api_key}\n"

    env_file = config_dir / ".env"
    with open(env_file, 'w') as f:
        f.write(env_content)

    # Write channel credentials
    for channel in workspace.channels.filter(is_active=True):
        if channel.channel_type == 'telegram' and channel.credentials.get('bot_token'):
            telegram_creds = credentials_dir / "telegram.json"
            with open(telegram_creds, 'w') as f:
                json.dump({
                    "bot_token": channel.credentials['bot_token']
                }, f)

        elif channel.channel_type == 'slack' and channel.credentials.get('bot_token'):
            slack_creds = credentials_dir / "slack.json"
            with open(slack_creds, 'w') as f:
                json.dump({
                    "bot_token": channel.credentials['bot_token'],
                    "app_token": channel.credentials.get('app_token', ''),
                }, f)

    logger.info(f"Created OpenClaw config files for workspace {workspace.id} at {data_dir}")
    return data_dir


def deploy_openclaw_container(workspace) -> str:
    """
    Deploy an OpenClaw Docker container for a workspace.

    Returns the container ID.
    """
    client = docker.from_env()

    # Setup configuration files
    data_dir = setup_workspace_files(workspace)
    port = get_workspace_port(workspace.id)

    container_name = f"openclaw-workspace-{workspace.id}"

    # Stop existing container if any
    try:
        existing = client.containers.get(container_name)
        existing.stop()
        existing.remove()
        logger.info(f"Removed existing container: {container_name}")
    except docker.errors.NotFound:
        pass

    # Environment variables
    environment = {
        "OPENCLAW_SKIP_ONBOARD": "true",  # Skip interactive onboarding
        "OPENCLAW_GATEWAY_PORT": str(port),
    }

    # Add API keys
    if workspace.owner.anthropic_api_key:
        environment["ANTHROPIC_API_KEY"] = workspace.owner.anthropic_api_key
    if workspace.owner.openai_api_key:
        environment["OPENAI_API_KEY"] = workspace.owner.openai_api_key

    # Volume mounts
    volumes = {
        str(data_dir / ".openclaw"): {
            "bind": "/home/node/.openclaw",
            "mode": "rw"
        },
    }

    # Port mapping
    ports = {
        f"{port}/tcp": port
    }

    try:
        # Pull latest image if not present
        try:
            client.images.get(OPENCLAW_IMAGE)
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling OpenClaw image: {OPENCLAW_IMAGE}")
            client.images.pull(OPENCLAW_IMAGE)

        # Create and start container
        container = client.containers.run(
            OPENCLAW_IMAGE,
            name=container_name,
            environment=environment,
            volumes=volumes,
            ports=ports,
            detach=True,
            restart_policy={"Name": "unless-stopped"},
            # Run the gateway
            command=["openclaw", "gateway", "--port", str(port)],
        )

        logger.info(f"Started OpenClaw container: {container.id} on port {port}")
        return container.id

    except Exception as e:
        logger.error(f"Failed to deploy OpenClaw container: {e}")
        raise


def stop_openclaw_container(workspace) -> bool:
    """Stop and remove an OpenClaw container for a workspace."""
    client = docker.from_env()
    container_name = f"openclaw-workspace-{workspace.id}"

    try:
        container = client.containers.get(container_name)
        container.stop(timeout=10)
        container.remove()
        logger.info(f"Stopped and removed container: {container_name}")
        return True
    except docker.errors.NotFound:
        logger.warning(f"Container not found: {container_name}")
        return False
    except Exception as e:
        logger.error(f"Failed to stop container: {e}")
        raise


def get_container_status(workspace) -> dict:
    """Get the status of an OpenClaw container."""
    client = docker.from_env()
    container_name = f"openclaw-workspace-{workspace.id}"

    try:
        container = client.containers.get(container_name)
        return {
            "status": container.status,
            "running": container.status == "running",
            "container_id": container.id,
            "ports": container.ports,
        }
    except docker.errors.NotFound:
        return {
            "status": "not_found",
            "running": False,
            "container_id": None,
        }


def get_container_logs(workspace, lines: int = 100) -> str:
    """Get logs from an OpenClaw container."""
    client = docker.from_env()
    container_name = f"openclaw-workspace-{workspace.id}"

    try:
        container = client.containers.get(container_name)
        logs = container.logs(tail=lines, timestamps=True)
        return logs.decode('utf-8')
    except docker.errors.NotFound:
        return "Container not found"
    except Exception as e:
        return f"Error getting logs: {e}"


def configure_channel(workspace, channel_type: str, credentials: dict) -> bool:
    """
    Configure a channel on a running OpenClaw instance.

    Uses the OpenClaw CLI to add channel credentials.
    """
    client = docker.from_env()
    container_name = f"openclaw-workspace-{workspace.id}"

    try:
        container = client.containers.get(container_name)

        if channel_type == 'telegram':
            token = credentials.get('bot_token')
            if not token:
                raise ValueError("Telegram bot_token is required")

            # Run openclaw CLI to add Telegram channel
            result = container.exec_run(
                ["openclaw", "channels", "add", "--channel", "telegram", "--token", token]
            )
            logger.info(f"Configured Telegram channel: {result.output.decode()}")

        elif channel_type == 'discord':
            token = credentials.get('bot_token')
            if not token:
                raise ValueError("Discord bot_token is required")

            result = container.exec_run(
                ["openclaw", "channels", "add", "--channel", "discord", "--token", token]
            )
            logger.info(f"Configured Discord channel: {result.output.decode()}")

        return True

    except docker.errors.NotFound:
        logger.error(f"Container not found: {container_name}")
        return False
    except Exception as e:
        logger.error(f"Failed to configure channel: {e}")
        return False


def send_message_via_gateway(workspace, message: str, session_id: str = "main") -> dict:
    """
    Send a message to an OpenClaw instance via the Gateway WebSocket API.

    This can be used for testing or automated messages.
    """
    import websocket

    port = get_workspace_port(workspace.id)
    ws_url = f"ws://localhost:{port}/ws"

    try:
        ws = websocket.create_connection(ws_url, timeout=10)

        # Send message
        payload = {
            "type": "sessions_send",
            "session_id": session_id,
            "message": message,
        }
        ws.send(json.dumps(payload))

        # Wait for response
        response = ws.recv()
        ws.close()

        return json.loads(response)

    except Exception as e:
        logger.error(f"Failed to send message via Gateway: {e}")
        return {"error": str(e)}
