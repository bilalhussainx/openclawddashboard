"""
Test script for skill installation and task creation.
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from workspaces.models import Workspace, InstalledSkill
from skills.models import Skill
from automations.models import AgentTask

ws = Workspace.objects.first()
print(f"Workspace: {ws.name} (ID: {ws.id})")

# Install more skills
more_skills = ['code-executor', 'claw-shell', 'clawdbot-filesystem', 'thinking-frameworks']
for slug in more_skills:
    skill = Skill.objects.filter(slug=slug).first()
    if skill:
        installed, created = InstalledSkill.objects.get_or_create(
            workspace=ws,
            skill=skill,
            defaults={'is_enabled': True, 'install_status': 'ready'}
        )
        if created:
            print(f"Installed: {skill.name}")
        else:
            print(f"Already installed: {skill.name}")

print(f"\nTotal installed skills: {InstalledSkill.objects.filter(workspace=ws).count()}")

# Create test tasks
test_tasks = [
    {
        'name': 'Test: DuckDuckGo Search',
        'instructions': 'Search the web using DuckDuckGo for "best AI coding assistants 2026". Return the top 5 results with title, URL, and brief description. This tests the free web search skill.',
    },
    {
        'name': 'Test: Cat Facts API',
        'instructions': 'Use the cat-fact skill to get 3 random cat facts and display them with fun emojis. This tests a simple no-auth API skill.',
    },
    {
        'name': 'Test: Code Execution',
        'instructions': 'Write and execute a Python script that calculates the first 10 Fibonacci numbers and prints them. Show both the code and output.',
    },
    {
        'name': 'Test: Memory Storage',
        'instructions': 'Test the memory system: 1) Store the fact "User prefers Python", 2) Store "User interested in AI agents", 3) Retrieve and list all stored facts.',
    },
    {
        'name': 'Test: Web Research Synthesis',
        'instructions': 'Research "Claude Code features and capabilities" using web search. Provide a summary with key features, use cases, and source URLs.',
    },
]

print("\nCreating test tasks...")
for task_data in test_tasks:
    task, created = AgentTask.objects.get_or_create(
        workspace=ws,
        name=task_data['name'],
        defaults={
            'instructions': task_data['instructions'],
            'schedule': 'once',
            'status': 'pending',
        }
    )
    if created:
        print(f"  Created: {task.name} (ID: {task.id})")
    else:
        print(f"  Exists: {task.name} (ID: {task.id})")

print(f"\nTotal tasks: {AgentTask.objects.filter(workspace=ws).count()}")

# List all installed skills
print("\n=== INSTALLED SKILLS ===")
for i in InstalledSkill.objects.filter(workspace=ws):
    print(f"  - {i.skill.name} ({i.skill.slug})")
