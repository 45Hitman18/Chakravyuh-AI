"""
Comprehensive unit tests for the Analysis pipeline and models.
Tests cover AI analysis, scam probability scoring, and data models.
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.client import Client
from django.urls import reverse

from calls.models import CallRecord, AudioUpload
from analysis.models import AIAnalysisResult, ScamProbabilityScore
from analysis.pipeline import analyze_transcript
from reports.models import Report
from django.core.files.uploadedfile import SimpleUploadedFile as SUF

import uuid
import hashlib
from datetime import timedelta
import json

User = get_user_model()


class AIAnalysisModelTests(TestCase):
    """Tests for AIAnalysisResult model"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='admin'
        )
        
        self.call_record = CallRecord.objects.create(
            caller_number='+1-800-555-0100',
            recipient_number='+1-800-555-0101',
            call_start_time=timezone.now(),
            call_end_time=timezone.now() + timedelta(minutes=5),
            status='completed',
            recorded_by=self.user
        )
        
        # Create a dummy audio upload
        audio_content = b'fake audio data'
        audio_file = SUF(name='test.wav', content=audio_content, content_type='audio/wav')
        checksum = hashlib.sha256(audio_content).hexdigest()
        self.audio_upload = AudioUpload.objects.create(
            call_record=self.call_record,
            uploaded_by=self.user,
            audio_file=audio_file,
            file_size=len(audio_content),
            format='wav',
            checksum=checksum,
            duration=timedelta(minutes=5)
        )

    def test_create_analysis(self):
        """Test creating an analysis record"""
        analysis = AIAnalysisResult.objects.create(
            call_record=self.call_record,
            audio_upload=self.audio_upload,
            analysis_type='comprehensive',
            status='pending',
            requested_by=self.user
        )
        
        self.assertEqual(analysis.call_record, self.call_record)
        self.assertEqual(analysis.status, 'pending')
        self.assertEqual(analysis.analysis_type, 'comprehensive')
        self.assertIsNotNone(analysis.created_at)

    def test_analysis_status_transitions(self):
        """Test valid analysis status transitions"""
        analysis = AIAnalysisResult.objects.create(
            call_record=self.call_record,
            audio_upload=self.audio_upload,
            status='pending',
            requested_by=self.user,
            analysis_type='comprehensive'
        )
        
        # Update status
        analysis.status = 'processing'
        analysis.save()
        analysis.refresh_from_db()
        self.assertEqual(analysis.status, 'processing')
        
        # Mark as completed
        analysis.status = 'completed'
        analysis.completed_at = timezone.now()
        analysis.save()
        analysis.refresh_from_db()
        self.assertEqual(analysis.status, 'completed')
        self.assertIsNotNone(analysis.completed_at)

    def test_analysis_confidence_score(self):
        """Test confidence score validation"""
        analysis = AIAnalysisResult.objects.create(
            call_record=self.call_record,
            audio_upload=self.audio_upload,
            status='completed',
            requested_by=self.user,
            analysis_type='comprehensive',
            confidence_score=0.95
        )
        
        self.assertEqual(analysis.confidence_score, 0.95)
        self.assertGreaterEqual(analysis.confidence_score, 0)
        self.assertLessEqual(analysis.confidence_score, 1)


class ScamProbabilityTests(TestCase):
    """Tests for ScamProbabilityScore model"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.call_record = CallRecord.objects.create(
            caller_number='+1-800-555-0100',
            recipient_number='+1-800-555-0101',
            call_start_time=timezone.now(),
            status='completed',
            recorded_by=self.user
        )
        
        # Create a dummy audio upload
        audio_content = b'fake audio data'
        audio_file = SUF(name='test.wav', content=audio_content, content_type='audio/wav')
        checksum = hashlib.sha256(audio_content).hexdigest()
        self.audio_upload = AudioUpload.objects.create(
            call_record=self.call_record,
            uploaded_by=self.user,
            audio_file=audio_file,
            file_size=len(audio_content),
            format='wav',
            checksum=checksum,
            duration=timedelta(minutes=5)
        )
        
        self.analysis = AIAnalysisResult.objects.create(
            call_record=self.call_record,
            audio_upload=self.audio_upload,
            status='completed',
            requested_by=self.user,
            analysis_type='comprehensive'
        )

    def test_create_scam_probability_low(self):
        """Test creating low-risk scam probability"""
        score = ScamProbabilityScore.objects.create(
            ai_analysis=self.analysis,
            call_record=self.call_record,
            overall_score=0.2,
            scam_level='low'
        )
        
        self.assertEqual(score.overall_score, 0.2)
        self.assertEqual(score.scam_level, 'low')
        self.assertEqual(score.get_scam_level_display(), 'Low Risk')

    def test_create_scam_probability_high(self):
        """Test creating high-risk scam probability"""
        score = ScamProbabilityScore.objects.create(
            ai_analysis=self.analysis,
            call_record=self.call_record,
            overall_score=0.85,
            scam_level='high'
        )
        
        self.assertEqual(score.overall_score, 0.85)
        self.assertEqual(score.scam_level, 'high')

    def test_create_scam_probability_critical(self):
        """Test creating critical-risk scam probability"""
        score = ScamProbabilityScore.objects.create(
            ai_analysis=self.analysis,
            call_record=self.call_record,
            overall_score=0.95,
            scam_level='critical',
            keywords_matched=['urgent', 'confirm', 'password'],
            patterns_detected=['time_pressure', 'account_threat', 'immediate_action']
        )
        
        self.assertEqual(score.overall_score, 0.95)
        self.assertEqual(score.scam_level, 'critical')
        self.assertIn('time_pressure', score.patterns_detected)

    def test_scam_probability_relationships(self):
        """Test scam probability relationships"""
        score = ScamProbabilityScore.objects.create(
            ai_analysis=self.analysis,
            call_record=self.call_record,
            overall_score=0.75,
            scam_level='high'
        )
        
        self.assertEqual(score.ai_analysis, self.analysis)
        self.assertEqual(score.call_record, self.call_record)


class AnalysisPipelineTests(TestCase):
    """Tests for analysis pipeline functions"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_analyze_transcript_safe(self):
        """Test transcript analysis for safe call"""
        transcript = "Hi, this is John from your bank. Just confirming your recent transaction."
        
        results = analyze_transcript(transcript)
        
        self.assertIsInstance(results, dict)
        self.assertIn('keywords_matched', results)
        self.assertIn('patterns_detected', results)
        self.assertIn('text_score', results)

    def test_analyze_transcript_suspicious(self):
        """Test transcript analysis for suspicious call"""
        transcript = "You need to verify your account immediately! Click the link now before we close it."
        
        results = analyze_transcript(transcript)
        
        # Should detect some risk indicators
        self.assertIsInstance(results, dict)
        self.assertGreater(results.get('text_score', 0), 0)

    def test_analyze_transcript_critical(self):
        """Test transcript analysis for critical call"""
        transcript = """
        Your bank account has been compromised! We need your credit card number and PIN immediately.
        If you don't act now, we will freeze your account and all your money will be seized.
        This is urgent! Give me your details right now or it will be too late!
        """
        
        results = analyze_transcript(transcript)
        
        # Should detect some risk indicators
        self.assertIsInstance(results, dict)
        self.assertGreater(results.get('text_score', 0), 0)


class AnalysisViewTests(TestCase):
    """Tests for analysis views"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='user'
        )
        
        self.admin = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='testpass123',
            role='admin'
        )

    def test_analysis_list_view_requires_login(self):
        """Test that analysis list requires authentication"""
        response = self.client.get(reverse('analysis:analysis_list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_analysis_list_view_authenticated(self):
        """Test analysis list view for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('analysis:analysis_list'))
        self.assertEqual(response.status_code, 200)

    def test_analysis_list_view_pagination(self):
        """Test analysis list view pagination"""
        # Create call record first
        call_record = CallRecord.objects.create(
            caller_number='+1-800-555-0100',
            recipient_number='+1-800-555-0101',
            call_start_time=timezone.now(),
            status='completed',
            recorded_by=self.user
        )
        
        # Create audio upload for call record
        audio_content = b'fake audio data'
        audio_file = SUF(name='test.wav', content=audio_content, content_type='audio/wav')
        checksum = hashlib.sha256(audio_content).hexdigest()
        audio_upload = AudioUpload.objects.create(
            call_record=call_record,
            uploaded_by=self.user,
            audio_file=audio_file,
            file_size=len(audio_content),
            format='wav',
            checksum=checksum,
            duration=timedelta(minutes=5)
        )

        
        for i in range(30):
            call = CallRecord.objects.create(
                caller_number=f'+1-800-555-0{100+i}',
                recipient_number='+1-800-555-0101',
                call_start_time=timezone.now(),
                status='completed',
                recorded_by=self.user
            )
            
            # Create audio for this call
            audio = AudioUpload.objects.create(
                call_record=call,
                uploaded_by=self.user,
                audio_file=audio_file,
                file_size=len(audio_content),
                format='wav',
                checksum=hashlib.sha256(f'data{i}'.encode()).hexdigest(),
                duration=timedelta(minutes=5)
            )
            
            AIAnalysisResult.objects.create(
                call_record=call,
                audio_upload=audio,
                status='completed',
                requested_by=self.user,
                analysis_type='comprehensive',
                confidence_score=0.5 + (i % 10) * 0.05
            )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('analysis:analysis_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue('page_obj' in response.context)
        self.assertEqual(len(response.context['page_obj']), 25)  # First page has 25 items


class CallRecordTests(TestCase):
    """Tests for CallRecord model"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_call_record(self):
        """Test creating a call record"""
        call = CallRecord.objects.create(
            caller_number='+1-800-555-0100',
            recipient_number='+1-800-555-0101',
            call_start_time=timezone.now(),
            status='completed',
            recorded_by=self.user
        )
        
        self.assertIsNotNone(call.id)
        self.assertEqual(call.caller_number, '+1-800-555-0100')
        self.assertEqual(call.status, 'completed')
        self.assertEqual(call.recorded_by, self.user)

    def test_call_record_duration(self):
        """Test call record duration calculation"""
        start_time = timezone.now()
        end_time = start_time + timedelta(minutes=5)
        
        call = CallRecord.objects.create(
            caller_number='+1-800-555-0100',
            recipient_number='+1-800-555-0101',
            call_start_time=start_time,
            call_end_time=end_time,
            status='completed',
            recorded_by=self.user
        )
        
        self.assertEqual(call.call_start_time, start_time)
        self.assertEqual(call.call_end_time, end_time)


class ReportCreationTests(TestCase):
    """Tests for report creation workflow"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='user'
        )
        
        self.admin = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='testpass123',
            role='admin'
        )
        
        self.law_enforcement = User.objects.create_user(
            username='leuser',
            email='le@example.com',
            password='testpass123',
            role='law_enforcement'
        )
        
        self.call_record = CallRecord.objects.create(
            caller_number='+1-800-555-0100',
            recipient_number='+1-800-555-0101',
            call_start_time=timezone.now(),
            status='completed',
            recorded_by=self.user
        )
        
        # Create audio upload
        audio_content = b'fake audio data'
        audio_file = SUF(name='test.wav', content=audio_content, content_type='audio/wav')
        checksum = hashlib.sha256(audio_content).hexdigest()
        self.audio_upload = AudioUpload.objects.create(
            call_record=self.call_record,
            uploaded_by=self.user,
            audio_file=audio_file,
            file_size=len(audio_content),
            format='wav',
            checksum=checksum,
            duration=timedelta(minutes=5)
        )

    def test_create_report_from_analysis(self):
        """Test creating a report from AI analysis"""
        analysis = AIAnalysisResult.objects.create(
            call_record=self.call_record,
            audio_upload=self.audio_upload,
            status='completed',
            requested_by=self.user,
            analysis_type='comprehensive',
            confidence_score=0.85
        )
        
        ScamProbabilityScore.objects.create(
            ai_analysis=analysis,
            call_record=self.call_record,
            overall_score=0.85,
            scam_level='high'
        )
        
        report = Report.objects.create(
            title='Suspected Scam Call',
            report_type='scam_call',
            description='High probability scam detected',
            incident_date=timezone.now(),
            status='submitted',
            call_record=self.call_record,
            ai_analysis=analysis,
            created_by=self.user
        )
        
        self.assertEqual(report.status, 'submitted')
        self.assertEqual(report.call_record, self.call_record)
        self.assertEqual(report.ai_analysis, analysis)

    def test_report_workflow(self):
        """Test complete report workflow"""
        report = Report.objects.create(
            title='Suspected Fraud',
            report_type='suspicious_activity',
            status='submitted',
            description='Suspicious transaction patterns detected',
            incident_date=timezone.now(),
            call_record=self.call_record,
            created_by=self.user
        )
        
        # Admin reviews
        report.status = 'under_review'
        report.assigned_to = self.admin
        report.save()
        
        # Admin approves
        report.status = 'approved'
        report.save()
        
        # Escalate to law enforcement
        report.status = 'escalated'
        report.assigned_to = self.law_enforcement
        report.save()
        
        report.refresh_from_db()
        self.assertEqual(report.status, 'escalated')
        self.assertEqual(report.assigned_to, self.law_enforcement)

