"""
Celery tasks for OpenClaw workspace deployment and management.
"""
import json
import os
import subprocess
import logging
from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_next_available_port():
    """Find the next available port in the configured range."""
    from .models import Workspace

    used_ports = set(
        Workspace.objects.exclude(assigned_port__isnull=True)
        .values_list('assigned_port', flat=True)
    )

    for port in range(
        settings.OPENCLAW_PORT_RANGE_START,
        settings.OPENCLAW_PORT_RANGE_END
    ):
        if port not in used_ports:
            return port

    raise RuntimeError('No available ports in configured range')


def generate_openclaw_config(workspace):
    """
    Generate openclaw.json configuration for a workspace.
    Based on OpenClaw's configuration format.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    owner = workspace.owner

    # Base configuration - using OpenClaw 2026.2 config format
    model_id = f"anthropic/{workspace.selected_model}" if 'claude' in workspace.selected_model else f"openai/{workspace.selected_model}"
    config = {
        "gateway": {
            "port": workspace.assigned_port,
            "bind": "lan",  # Valid values: loopback, lan, tailnet, auto, custom
            "mode": "local",
        },
        "agents": {
            "defaults": {
                "model": {
                    "primary": model_id
                }
            }
        },
        "channels": {}
    }

    # Add channel configurations
    for channel in workspace.channels.filter(is_active=True):
        if channel.channel_type == 'telegram':
            config["channels"]["telegram"] = {
                "botToken": channel.credentials.get('bot_token', ''),
                "enabled": True,
                "allowFrom": channel.allowlist or ["*"],
            }
            if channel.respond_to_groups:
                config["channels"]["telegram"]["groups"] = {"*": {"requireMention": True}}

        elif channel.channel_type == 'slack':
            config["channels"]["slack"] = {
                "botToken": channel.credentials.get('bot_token', ''),
                "appToken": channel.credentials.get('app_token', ''),
            }
            if channel.allowlist:
                config["channels"]["slack"]["dm"] = {
                    "allowFrom": channel.allowlist
                }

        elif channel.channel_type == 'discord':
            config["channels"]["discord"] = {
                "token": channel.credentials.get('token', ''),
            }
            if channel.allowlist:
                config["channels"]["discord"]["dm"] = {
                    "allowFrom": channel.allowlist
                }

    return config


def write_skill_files(workspace, config_dir):
    """
    Write skill files to the workspace skills directory.
    Creates SKILL.md files for each installed and enabled skill.
    """
    skills_dir = os.path.join(config_dir, 'workspace', 'skills')
    os.makedirs(skills_dir, exist_ok=True)

    for installed in workspace.installed_skills.filter(is_enabled=True):
        skill = installed.skill
        skill_file = os.path.join(skills_dir, f'{skill.slug}.md')

        content = f"# {skill.name}\n\n"
        content += f"{skill.description}\n\n"

        if skill.skill_content:
            content += skill.skill_content

        with open(skill_file, 'w') as f:
            f.write(content)

        logger.info(f"Wrote skill file: {skill_file}")


def write_workspace_config(workspace, config):
    """Write the openclaw.json config and workspace files."""
    config_dir = workspace.get_config_path()
    os.makedirs(config_dir, exist_ok=True)

    # Write openclaw.json
    config_path = os.path.join(config_dir, 'openclaw.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    # Create workspace directory structure
    workspace_dir = os.path.join(config_dir, 'workspace')
    os.makedirs(workspace_dir, exist_ok=True)

    skills_dir = os.path.join(workspace_dir, 'skills')
    os.makedirs(skills_dir, exist_ok=True)

    # Write skill files
    write_skill_files(workspace, config_dir)

    # Write SOUL.md - Agent personality and instructions
    soul_content = generate_soul_md(workspace)
    soul_path = os.path.join(workspace_dir, 'SOUL.md')
    with open(soul_path, 'w') as f:
        f.write(soul_content)

    # Write .env file with API keys
    env_path = os.path.join(config_dir, '.env')
    env_content = ""
    if workspace.owner.anthropic_api_key:
        env_content += f"ANTHROPIC_API_KEY={workspace.owner.anthropic_api_key}\n"
    if workspace.owner.openai_api_key:
        env_content += f"OPENAI_API_KEY={workspace.owner.openai_api_key}\n"

    # Add skill-specific API keys from user's skill_api_keys
    skill_keys = getattr(workspace.owner, 'skill_api_keys', None) or {}
    for key_name, key_value in skill_keys.items():
        if key_value:
            env_content += f"{key_name}={key_value}\n"

    with open(env_path, 'w') as f:
        f.write(env_content)

    # Write channel credentials
    credentials_dir = os.path.join(config_dir, 'credentials')
    os.makedirs(credentials_dir, exist_ok=True)

    for channel in workspace.channels.filter(is_active=True):
        cred_file = os.path.join(credentials_dir, f'{channel.channel_type}.json')
        with open(cred_file, 'w') as f:
            json.dump(channel.credentials, f)

    # Fix permissions so OpenClaw container (node user) can read the files
    # The container runs as non-root user but celery writes as root
    try:
        os.chmod(config_path, 0o644)
        os.chmod(env_path, 0o644)
        os.chmod(config_dir, 0o755)
        os.chmod(workspace_dir, 0o755)
        os.chmod(skills_dir, 0o755)
        os.chmod(credentials_dir, 0o755)
        # Make all files in workspace dir readable
        for root, dirs, files in os.walk(config_dir):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)
            for f in files:
                os.chmod(os.path.join(root, f), 0o644)
        logger.info(f"Fixed permissions on {config_dir}")
    except Exception as e:
        logger.warning(f"Could not fix permissions: {e}")

    logger.info(f"Wrote OpenClaw config to {config_dir}")
    return config_path


def generate_soul_md(workspace):
    """
    Generate SOUL.md content - the agent's personality and instructions.
    This is what makes each OpenClaw instance unique.
    """
    agent_name = getattr(workspace, 'agent_name', 'Assistant') or 'Assistant'
    agent_desc = getattr(workspace, 'agent_description', '') or ''
    system_prompt = getattr(workspace, 'system_prompt', '') or 'You are a helpful AI assistant.'
    welcome_msg = getattr(workspace, 'welcome_message', '') or 'Hello! How can I help you today?'

    soul = f"""# {agent_name}

{agent_desc}

## Core Instructions

{system_prompt}

## Greeting

When a user first messages you, respond with:
"{welcome_msg}"

"""

    # Add knowledge base content
    try:
        knowledge_entries = workspace.knowledge_base.filter(is_active=True)
        if knowledge_entries.exists():
            soul += "\n## Knowledge Base\n\n"
            soul += "Use this information when answering questions:\n\n"

            for entry in knowledge_entries:
                if entry.resource_type == 'faq':
                    soul += f"**Q: {entry.question}**\n"
                    soul += f"A: {entry.answer}\n\n"
                elif entry.content:
                    soul += f"### {entry.name}\n"
                    soul += f"{entry.content}\n\n"
    except Exception as e:
        logger.warning(f"Could not load knowledge base: {e}")

    # Add agent task instructions if any exist
    try:
        active_tasks = workspace.agent_tasks.filter(status__in=['pending', 'running'])
        if active_tasks.exists():
            soul += "\n## Automated Tasks\n\n"
            soul += "You have the following automated tasks to perform:\n\n"
            for task in active_tasks:
                soul += f"### {task.name}\n"
                soul += f"{task.instructions}\n\n"
    except Exception as e:
        logger.warning(f"Could not load agent tasks: {e}")

    # Add installed skills
    try:
        installed_skills = workspace.installed_skills.filter(is_enabled=True)
        if installed_skills.exists():
            soul += "\n## Installed Skills\n\n"
            soul += "You have the following skills available to help accomplish tasks:\n\n"
            for installed in installed_skills:
                skill = installed.skill
                soul += f"### {skill.name}\n"
                soul += f"{skill.description}\n\n"
                # Include skill-specific instructions if available
                if skill.skill_content:
                    soul += f"#### Usage Instructions\n"
                    soul += f"{skill.skill_content}\n\n"
    except Exception as e:
        logger.warning(f"Could not load installed skills: {e}")

    return soul


@shared_task(bind=True, max_retries=3)
def deploy_workspace(self, workspace_id):
    """
    Deploy an OpenClaw instance for a workspace.
    Uses Docker to run isolated OpenClaw containers.
    """
    from .models import Workspace
    import docker

    try:
        workspace = Workspace.objects.get(id=workspace_id)

        # Assign port if not already assigned
        if not workspace.assigned_port:
            workspace.assigned_port = get_next_available_port()
            workspace.save()

        # Generate and write configuration
        config = generate_openclaw_config(workspace)
        config_path = write_workspace_config(workspace, config)

        logger.info(f"Deploying workspace {workspace_id} on port {workspace.assigned_port}")

        # Initialize Docker client
        client = docker.from_env()

        # Stop existing container if any
        if workspace.container_id:
            try:
                old_container = client.containers.get(workspace.container_id)
                old_container.stop(timeout=10)
                old_container.remove()
            except docker.errors.NotFound:
                pass

        # Get user's API key
        api_key = workspace.owner.anthropic_api_key or workspace.owner.openai_api_key

        # Environment variables for the container
        # Use the shared volume path where celery writes the config
        workspace_config_dir = f'/openclaw-data/{workspace.id}'
        env_vars = {
            'OPENCLAW_STATE_DIR': workspace_config_dir,
            'OPENCLAW_CONFIG_PATH': f'{workspace_config_dir}/openclaw.json',
            'OPENCLAW_SKIP_ONBOARD': 'true',
        }

        if workspace.owner.anthropic_api_key:
            env_vars['ANTHROPIC_API_KEY'] = workspace.owner.anthropic_api_key
        if workspace.owner.openai_api_key:
            env_vars['OPENAI_API_KEY'] = workspace.owner.openai_api_key

        # Add Telegram token if configured
        telegram_channel = workspace.channels.filter(channel_type='telegram', is_active=True).first()
        if telegram_channel and telegram_channel.credentials.get('bot_token'):
            env_vars['TELEGRAM_BOT_TOKEN'] = telegram_channel.credentials['bot_token']

        # Run OpenClaw container with Gateway started
        # Mount the shared Docker volume where celery writes the config
        # The volume name is 'docker_openclaw_data' (created by docker-compose)
        # Start the Gateway on the assigned port so we can connect via WebSocket

        # Generate a gateway token for authentication
        import secrets
        gateway_token = secrets.token_urlsafe(32)
        env_vars['OPENCLAW_GATEWAY_TOKEN'] = gateway_token

        # Add Playwright browsers path for browser automation
        env_vars['PLAYWRIGHT_BROWSERS_PATH'] = '/home/node/.cache/ms-playwright'

        # Store token in workspace for later use
        workspace.gateway_token = gateway_token

        container = client.containers.run(
            image=settings.OPENCLAW_IMAGE,
            name=f"openclaw-workspace-{workspace.id}",
            detach=True,
            # The command needs to be passed as arguments to node dist/index.js
            command=['dist/index.js', 'gateway', '--port', str(workspace.assigned_port),
                     '--bind', 'lan', '--allow-unconfigured'],
            ports={f'{workspace.assigned_port}/tcp': workspace.assigned_port},
            volumes={
                'docker_openclaw_data': {
                    'bind': '/openclaw-data',
                    'mode': 'rw'
                }
            },
            environment=env_vars,
            restart_policy={'Name': 'unless-stopped'},
            labels={
                'openclaw.workspace_id': str(workspace.id),
                'openclaw.owner_id': str(workspace.owner.id),
            },
            # Connect to docker_default network for communication with celery
            network='docker_default',
        )

        # Update workspace with container info
        workspace.container_id = container.id
        workspace.status = Workspace.Status.RUNNING
        workspace.last_health_check = timezone.now()
        workspace.error_message = ''
        workspace.save()

        logger.info(f"Workspace {workspace_id} deployed successfully, container: {container.id}")

        return {
            'success': True,
            'container_id': container.id,
            'port': workspace.assigned_port
        }

    except Exception as e:
        logger.error(f"Failed to deploy workspace {workspace_id}: {str(e)}")

        # Update workspace status to error
        try:
            workspace = Workspace.objects.get(id=workspace_id)
            workspace.status = Workspace.Status.ERROR
            workspace.error_message = str(e)
            workspace.save()
        except Exception:
            pass

        # Retry on transient errors
        raise self.retry(exc=e, countdown=30)


@shared_task
def stop_workspace(workspace_id):
    """Stop an OpenClaw workspace container."""
    from .models import Workspace
    import docker

    try:
        workspace = Workspace.objects.get(id=workspace_id)

        if not workspace.container_id:
            workspace.status = Workspace.Status.STOPPED
            workspace.save()
            return {'success': True, 'message': 'No container to stop'}

        client = docker.from_env()

        try:
            container = client.containers.get(workspace.container_id)
            container.stop(timeout=10)
            container.remove()
        except docker.errors.NotFound:
            pass

        workspace.status = Workspace.Status.STOPPED
        workspace.container_id = ''
        workspace.save()

        logger.info(f"Workspace {workspace_id} stopped successfully")

        return {'success': True}

    except Exception as e:
        logger.error(f"Failed to stop workspace {workspace_id}: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def restart_workspace(workspace_id):
    """Restart an OpenClaw workspace (stop then deploy)."""
    stop_workspace(workspace_id)
    deploy_workspace.delay(workspace_id)


@shared_task
def update_workspace_config(workspace_id):
    """
    Update the configuration for a running workspace and restart it.
    Called when channels or settings are modified.
    """
    from .models import Workspace

    try:
        workspace = Workspace.objects.get(id=workspace_id)

        # Regenerate configuration
        config = generate_openclaw_config(workspace)
        write_workspace_config(workspace, config)

        # Restart if running
        if workspace.status == Workspace.Status.RUNNING:
            restart_workspace.delay(workspace_id)

        return {'success': True}

    except Exception as e:
        logger.error(f"Failed to update workspace config {workspace_id}: {str(e)}")
        return {'success': False, 'error': str(e)}


@shared_task
def health_check_workspaces():
    """
    Periodic task to check health of all running workspaces.
    Should be scheduled via Celery Beat.
    """
    from .models import Workspace
    import docker

    client = docker.from_env()
    running_workspaces = Workspace.objects.filter(status=Workspace.Status.RUNNING)

    for workspace in running_workspaces:
        try:
            if not workspace.container_id:
                workspace.status = Workspace.Status.ERROR
                workspace.error_message = 'Container ID missing'
                workspace.save()
                continue

            container = client.containers.get(workspace.container_id)

            if container.status == 'running':
                workspace.last_health_check = timezone.now()
                workspace.save()
            else:
                workspace.status = Workspace.Status.ERROR
                workspace.error_message = f'Container status: {container.status}'
                workspace.save()

        except docker.errors.NotFound:
            workspace.status = Workspace.Status.ERROR
            workspace.error_message = 'Container not found'
            workspace.container_id = ''
            workspace.save()
        except Exception as e:
            logger.error(f"Health check failed for workspace {workspace.id}: {str(e)}")


def get_workspace_logs(workspace_id, lines=100):
    """Get logs from a workspace container."""
    from .models import Workspace
    import docker

    try:
        workspace = Workspace.objects.get(id=workspace_id)

        if not workspace.container_id:
            return 'No container found'

        client = docker.from_env()
        container = client.containers.get(workspace.container_id)

        logs = container.logs(tail=lines, timestamps=True).decode('utf-8')
        return logs

    except Exception as e:
        logger.error(f"Failed to get logs for workspace {workspace_id}: {str(e)}")
        return f'Error fetching logs: {str(e)}'


@shared_task(bind=True, max_retries=3)
def install_skill_in_container(self, workspace_id, installed_skill_id):
    """
    Install a skill in the OpenClaw container.

    For ClawHub skills, runs: clawhub install <skill_slug>
    For custom skills, writes skill content to skills directory.
    For JobSpy skills (job-search-mcp), also installs Python dependencies.
    """
    from .models import Workspace, InstalledSkill
    import docker
    import subprocess

    try:
        workspace = Workspace.objects.get(id=workspace_id)
        installed_skill = InstalledSkill.objects.get(id=installed_skill_id)
        skill = installed_skill.skill

        # Update status to installing
        installed_skill.install_status = InstalledSkill.InstallStatus.INSTALLING
        installed_skill.save()

        logger.info(f"Installing skill {skill.name} in workspace {workspace_id}")

        # Write skill files regardless of container status
        config_dir = workspace.get_config_path()
        write_skill_files(workspace, config_dir)

        # Handle JobSpy-based skills (job-search-mcp, job-auto-apply)
        # These run in the Celery container, not OpenClaw, so we install deps here
        jobspy_skills = ['job-search-mcp', 'job-auto-apply']
        if skill.slug in jobspy_skills or (skill.clawhub_id and skill.clawhub_id in jobspy_skills):
            try:
                logger.info(f"Installing JobSpy dependencies for {skill.name}")
                # Install python-jobspy and pandas in the current environment (Celery)
                subprocess.run(
                    ['pip', 'install', 'python-jobspy', 'pandas', '-q'],
                    check=True,
                    capture_output=True
                )
                logger.info("JobSpy dependencies installed successfully")
            except subprocess.CalledProcessError as e:
                logger.warning(f"JobSpy pip install failed: {e.stderr}")
            except Exception as e:
                logger.warning(f"JobSpy install warning: {e}")

        # Handle DuckDuckGo search skill
        if skill.slug == 'duckduckgo-search' or skill.clawhub_id == 'duckduckgo-search':
            try:
                logger.info(f"Installing DuckDuckGo dependencies for {skill.name}")
                subprocess.run(
                    ['pip', 'install', 'duckduckgo-search', '-q'],
                    check=True,
                    capture_output=True
                )
                logger.info("DuckDuckGo search dependencies installed successfully")
            except subprocess.CalledProcessError as e:
                logger.warning(f"DuckDuckGo pip install failed: {e.stderr}")
            except Exception as e:
                logger.warning(f"DuckDuckGo install warning: {e}")

        # If container is running and skill has a ClawHub ID, run clawhub install
        if workspace.status == Workspace.Status.RUNNING and workspace.container_id and skill.clawhub_id:
            try:
                client = docker.from_env()
                container = client.containers.get(workspace.container_id)

                # Run clawhub install command in container
                exec_result = container.exec_run(
                    ['npx', 'clawhub', 'install', skill.clawhub_id, '--dir', '/app/skills'],
                    environment={
                        'ANTHROPIC_API_KEY': workspace.owner.anthropic_api_key or '',
                        'OPENAI_API_KEY': workspace.owner.openai_api_key or '',
                    }
                )

                if exec_result.exit_code == 0:
                    installed_skill.clawhub_installed = True
                    logger.info(f"ClawHub install successful for {skill.name}")
                else:
                    output = exec_result.output.decode('utf-8') if exec_result.output else ''
                    logger.warning(f"ClawHub install returned non-zero: {output}")
                    # Don't fail - skill files are still written

            except docker.errors.NotFound:
                logger.warning(f"Container {workspace.container_id} not found, skill files written only")
            except Exception as e:
                logger.warning(f"ClawHub install failed: {e}, skill files written only")

        # Update status to ready
        installed_skill.install_status = InstalledSkill.InstallStatus.READY
        installed_skill.install_error = ''
        installed_skill.save()

        # Regenerate SOUL.md with the new skill
        update_workspace_config.delay(workspace_id)

        logger.info(f"Skill {skill.name} installed successfully in workspace {workspace_id}")
        return {'success': True, 'skill': skill.name}

    except Exception as e:
        logger.error(f"Failed to install skill: {str(e)}")

        # Update status to error
        try:
            installed_skill = InstalledSkill.objects.get(id=installed_skill_id)
            installed_skill.install_status = InstalledSkill.InstallStatus.ERROR
            installed_skill.install_error = str(e)
            installed_skill.save()
        except Exception:
            pass

        raise self.retry(exc=e, countdown=30)


@shared_task
def sync_clawhub_skills_task():
    """
    Celery task to sync skills from ClawHub registry.
    Should be run periodically via Celery beat (e.g., daily).
    """
    from skills.clawhub_sync import sync_clawhub_skills

    logger.info("Running scheduled ClawHub skill sync")
    stats = sync_clawhub_skills()
    logger.info(f"ClawHub sync complete: {stats}")
    return stats
