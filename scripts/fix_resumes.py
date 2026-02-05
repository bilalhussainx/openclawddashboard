"""Fix all resumes to have correct file, email, phone data."""
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from jobapply.models import Resume

for r in Resume.objects.filter(is_primary=True):
    data = r.parsed_data or {}
    data['name'] = 'Bilal Hussain'
    data['email'] = 'bilalhussain.v1@gmail.com'
    data['phone'] = '4379071483'
    data['location'] = 'Toronto, Ontario'
    data['linkedin'] = 'https://linkedin.com/in/bilalhussain'
    data['github'] = 'https://github.com/bilalhussainx'
    r.parsed_data = data
    r.file = 'resumes/bilal_hussain_resume.pdf'
    r.save()
    print(f"Updated Resume ID={r.id} for user_id={r.user_id}: email={data['email']}, file={r.file.name}")

print("Done - all primary resumes updated")
