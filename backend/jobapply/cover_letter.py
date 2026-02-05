"""
AI-powered cover letter generation using Claude or Ollama.
Falls back to Ollama (local LLM) when no Anthropic API key is available.
"""
import logging
import os

logger = logging.getLogger(__name__)

COVER_LETTER_SYSTEM = """You write concise, professional cover letters.
No fluff. Match the candidate's specific skills to the job requirements.
2-3 paragraphs max. Sound human, not AI-generated.
Do NOT include placeholder brackets like [Company] - use the actual values provided.
Do NOT include a header/address block - just the letter body."""


def _build_prompt(resume_text: str, job_title: str, company: str, job_description: str) -> str:
    return f"""Write a cover letter for this job application.

CANDIDATE RESUME:
{resume_text[:3000]}

JOB POSTING:
Title: {job_title}
Company: {company}
Description: {job_description[:2000]}

Focus on matching the candidate's specific technical skills and experience to this role.
Mention relevant projects and achievements that demonstrate fit.
Keep it under 300 words."""


def generate_cover_letter_text(
    resume_text: str,
    job_title: str,
    company: str,
    job_description: str,
    api_key: str = '',
) -> str:
    """
    Generate a tailored cover letter.
    Uses Claude API if api_key is provided, otherwise falls back to Ollama.
    """
    prompt = _build_prompt(resume_text, job_title, company, job_description)

    if api_key:
        return _generate_with_claude(prompt, api_key)
    else:
        return _generate_with_ollama(prompt)


def _generate_with_claude(prompt: str, api_key: str) -> str:
    """Generate cover letter using Claude API."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=COVER_LETTER_SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def _generate_with_ollama(prompt: str) -> str:
    """Generate cover letter using Ollama local LLM."""
    import requests

    ollama_url = os.environ.get('OLLAMA_URL', 'http://host.docker.internal:11434')
    model = os.environ.get('OLLAMA_MODEL', 'llama3.1:8b')

    logger.info(f"Generating cover letter with Ollama ({model}) at {ollama_url}")

    response = requests.post(
        f'{ollama_url}/api/generate',
        json={
            'model': model,
            'prompt': f"{COVER_LETTER_SYSTEM}\n\n{prompt}",
            'stream': False,
            'options': {
                'temperature': 0.7,
                'num_predict': 1024,
            },
        },
        timeout=300,
    )
    response.raise_for_status()
    result = response.json()
    return result.get('response', '').strip()
