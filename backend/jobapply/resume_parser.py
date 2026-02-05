"""
Resume parsing - extract text from PDF/DOCX and parse structured data with Claude.
"""
import io
import json
import logging

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_obj) -> str:
    """Extract text content from a PDF file."""
    from PyPDF2 import PdfReader

    file_obj.seek(0)
    reader = PdfReader(io.BytesIO(file_obj.read()))
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text.strip()


def extract_text_from_docx(file_obj) -> str:
    """Extract text content from a DOCX file."""
    from docx import Document

    file_obj.seek(0)
    doc = Document(io.BytesIO(file_obj.read()))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_text(file_obj, file_type: str) -> str:
    """Extract text from a resume file based on type."""
    if file_type == 'pdf':
        return extract_text_from_pdf(file_obj)
    elif file_type in ('docx', 'doc'):
        return extract_text_from_docx(file_obj)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def parse_resume_with_claude(text: str, api_key: str) -> dict:
    """Use Claude to extract structured data from resume text."""
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system="You parse resumes into structured JSON. Return ONLY valid JSON, no markdown formatting.",
        messages=[{
            "role": "user",
            "content": f"""Parse this resume into structured JSON with these exact fields:
{{
  "name": "Full Name",
  "email": "email@example.com",
  "phone": "phone number or null",
  "location": "City, State/Province",
  "summary": "1-2 sentence professional summary",
  "skills": ["skill1", "skill2", ...],
  "experience": [
    {{
      "title": "Job Title",
      "company": "Company Name",
      "dates": "Start - End",
      "description": "Brief description"
    }}
  ],
  "education": [
    {{
      "degree": "Degree Name",
      "school": "School Name",
      "year": "Graduation Year"
    }}
  ]
}}

Resume text:
{text}"""
        }]
    )

    response_text = response.content[0].text.strip()
    # Strip markdown code blocks if present
    if response_text.startswith('```'):
        lines = response_text.split('\n')
        response_text = '\n'.join(lines[1:-1])

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse Claude response as JSON: {response_text[:200]}")
        return {"raw_text": text, "parse_error": "Failed to parse structured data"}
