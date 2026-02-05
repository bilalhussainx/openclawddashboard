import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from jobapply.models import Resume
from django.contrib.auth import get_user_model
User = get_user_model()

for u in User.objects.all():
    print(f"User ID={u.id} email={u.email}")
    for r in Resume.objects.filter(user=u):
        fname = r.file.name if r.file else 'EMPTY'
        email = r.parsed_data.get('email', 'N/A') if r.parsed_data else 'N/A'
        print(f"  Resume ID={r.id} primary={r.is_primary} file={fname} email={email}")
    if not Resume.objects.filter(user=u).exists():
        print("  (no resumes)")
