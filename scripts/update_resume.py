"""Update resume with file, email, phone, LinkedIn, GitHub."""
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from jobapply.models import Resume

r = Resume.objects.filter(is_primary=True).first()
if r:
    # Update file path
    r.file = 'resumes/bilal_hussain_resume.pdf'

    # Update parsed data
    data = r.parsed_data or {}
    data['name'] = 'Bilal Hussain'
    data['email'] = 'bilalhussain.v1@gmail.com'
    data['phone'] = '4379071483'
    data['location'] = 'Toronto, Ontario'
    data['linkedin'] = 'https://linkedin.com/in/bilalhussain'
    data['github'] = 'https://github.com/bilalhussainx'

    # Try to extract text from PDF
    try:
        file_path = '/app/media/resumes/bilal_hussain_resume.pdf'
        if os.path.exists(file_path):
            from jobapply.resume_parser import extract_text
            with open(file_path, 'rb') as f:
                text = extract_text(f, 'pdf')
            r.extracted_text = text
            print(f"Extracted {len(text)} chars from PDF")
    except Exception as e:
        print(f"PDF extraction note: {e}")

    r.parsed_data = data
    r.save()
    print(f"Resume updated successfully")
    print(f"  Name: {data['name']}")
    print(f"  Email: {data['email']}")
    print(f"  Phone: {data['phone']}")
    print(f"  Location: {data['location']}")
    print(f"  LinkedIn: {data['linkedin']}")
    print(f"  GitHub: {data['github']}")
    print(f"  File: {r.file}")
else:
    print("No primary resume found")
