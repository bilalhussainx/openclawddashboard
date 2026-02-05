"""
Job Auto-Apply API views.
"""
from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class LargeResultsPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 500

from .models import Resume, JobPreferences, JobListing, JobApplication, DailyApplicationSummary
from .serializers import (
    ResumeSerializer, JobPreferencesSerializer, JobListingSerializer,
    JobApplicationSerializer, DailyApplicationSummarySerializer,
)


class ResumeViewSet(viewsets.ModelViewSet):
    serializer_class = ResumeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Resume.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        file = self.request.FILES.get('file')
        file_type = 'pdf'
        if file and file.name:
            file_type = file.name.rsplit('.', 1)[-1].lower()
        serializer.save(user=self.request.user, file_type=file_type)

    @action(detail=True, methods=['post'])
    def parse(self, request, pk=None):
        """Re-parse resume with Claude to extract structured data."""
        resume = self.get_object()
        api_key = request.user.anthropic_api_key
        if not api_key:
            return Response({'error': 'Anthropic API key required'}, status=400)

        from .resume_parser import extract_text, parse_resume_with_claude

        try:
            resume.file.open('rb')
            resume.extracted_text = extract_text(resume.file, resume.file_type)
            resume.parsed_data = parse_resume_with_claude(resume.extracted_text, api_key)
            resume.save()
            return Response(ResumeSerializer(resume).data)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        """Set this resume as the primary resume."""
        resume = self.get_object()
        Resume.objects.filter(user=request.user).update(is_primary=False)
        resume.is_primary = True
        resume.save()
        return Response(ResumeSerializer(resume).data)


class JobPreferencesView(generics.RetrieveUpdateAPIView):
    serializer_class = JobPreferencesSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj, _ = JobPreferences.objects.get_or_create(user=self.request.user)
        return obj


class JobListingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = JobListingSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = LargeResultsPagination

    def get_queryset(self):
        qs = JobListing.objects.filter(user=self.request.user, dismissed=False)
        min_score = self.request.query_params.get('min_score')
        if min_score:
            qs = qs.filter(match_score__gte=int(min_score))
        source = self.request.query_params.get('source')
        if source:
            # Support comma-separated source filter (e.g., "hn_hiring,remoteok")
            sources = [s.strip() for s in source.split(',') if s.strip()]
            if len(sources) == 1:
                qs = qs.filter(source_board=sources[0])
            elif sources:
                qs = qs.filter(source_board__in=sources)
        hours = self.request.query_params.get('hours')
        if hours:
            cutoff = timezone.now() - timedelta(hours=int(hours))
            qs = qs.filter(discovered_at__gte=cutoff)
        return qs

    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """Queue this listing for application."""
        listing = self.get_object()
        resume = Resume.objects.filter(user=request.user, is_primary=True).first()
        app, created = JobApplication.objects.get_or_create(
            user=request.user,
            listing=listing,
            defaults={'resume': resume, 'status': 'queued'}
        )
        if not created:
            return Response({'error': 'Already applied or queued'}, status=400)

        # Trigger cover letter generation + apply
        from .tasks import process_application
        process_application.delay(app.id)

        return Response(JobApplicationSerializer(app).data, status=201)

    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        """Dismiss this listing."""
        listing = self.get_object()
        listing.dismissed = True
        listing.save()
        return Response({'status': 'dismissed'})

    @action(detail=False, methods=['post'])
    def search_now(self, request):
        """Trigger an immediate job search."""
        from .tasks import discover_jobs
        discover_jobs.delay(request.user.id)
        return Response({'status': 'search_started'})

    @action(detail=False, methods=['post'])
    def search_startups(self, request):
        """Trigger job search on startup boards only (HN, RemoteOK)."""
        from .tasks import discover_jobs
        from .startup_scrapers import STARTUP_BOARD_NAMES
        discover_jobs.delay(request.user.id, boards_override=list(STARTUP_BOARD_NAMES))
        return Response({'status': 'startup_search_started'})


class JobApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = JobApplicationSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        qs = JobApplication.objects.filter(user=self.request.user)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.select_related('listing')

    @action(detail=True, methods=['post'])
    def regenerate_cover(self, request, pk=None):
        """Regenerate cover letter for this application."""
        app = self.get_object()
        from .tasks import generate_cover_letter
        generate_cover_letter.delay(app.id)
        return Response({'status': 'regenerating'})

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed application."""
        app = self.get_object()
        if app.status != 'failed':
            return Response({'error': 'Can only retry failed applications'}, status=400)
        app.status = 'queued'
        app.retry_count += 1
        app.error_message = ''
        app.save()
        from .tasks import process_application
        process_application.delay(app.id)
        return Response(JobApplicationSerializer(app).data)


class DashboardView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        apps = JobApplication.objects.filter(user=user)
        listings = JobListing.objects.filter(user=user, dismissed=False)

        data = {
            'total_listings': listings.count(),
            'total_applications': apps.count(),
            'applied_count': apps.filter(status='applied').count(),
            'interview_count': apps.filter(status='interview').count(),
            'failed_count': apps.filter(status='failed').count(),
            'avg_match_score': listings.aggregate(avg=Avg('match_score'))['avg'] or 0,
            'recent_listings': JobListingSerializer(listings[:10], many=True).data,
            'recent_applications': JobApplicationSerializer(
                apps.select_related('listing')[:10], many=True
            ).data,
        }
        return Response(data)
