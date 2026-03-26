#!/usr/bin/env python
"""
Test that the call detail and call list templates render correctly
"""

import os
import sys
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chakravyuh.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from calls.models import CallRecord, AudioUpload
from analysis.models import AIAnalysisResult, ScamProbabilityScore
from django.core.files.base import ContentFile
import tempfile
from datetime import timedelta

User = get_user_model()

def create_test_data():
    """Create test data with audio and transcript"""
    
    print("Creating test data...")
    
    # Get or create user
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'email': 'test@test.com', 'role': 'law_enforcement'}
    )
    
    # Create call record
    call = CallRecord.objects.create(
        caller_number='555-0001',
        recipient_number='555-0002',
        call_start_time=timezone.now() - timedelta(hours=1),
        call_end_time=timezone.now() - timedelta(minutes=50),
        duration=timedelta(minutes=10),
        status='completed',
        recorded_by=user
    )
    print(f"Created call: {call.id}")
    
    # Create audio upload
    audio_content = b'RIFF\x00\x00\x00\x00WAVE' + b'\x00' * 1000
    audio = AudioUpload.objects.create(
        call_record=call,
        format='wav',
        file_size=len(audio_content),
        duration=timedelta(minutes=10),
        checksum='test_checksum_123',
        uploaded_by=user
    )
    audio.audio_file.save('test_audio.wav', ContentFile(audio_content), save=True)
    print(f"Created audio: {audio.id}")
    
    # Create AI analysis
    analysis = AIAnalysisResult.objects.create(
        call_record=call,
        audio_upload=audio,
        analysis_type='comprehensive',
        status='completed',
        confidence_score=0.92,
        requested_by=user,
        results={
            'raw_transcript': 'Hello this is an urgent call regarding your bank account. The IRS has detected suspicious activity. Please verify your social security number immediately by pressing 1. Do not hang up.',
            'transcript_display': 'Hello this is an urgent call regarding your bank account. The IRS has detected suspicious activity. Please verify your social security number immediately by pressing 1. Do not hang up.',
            'transcript_confidence': 0.92,
            'transcript_language': 'en-IN',
            'transcript_tokens': [],
            'analysis': {
                'keywords_found': ['urgent', 'bank account', 'irs', 'suspicious', 'social security'],
                'patterns_found': ['social security mention', 'financial institution mention'],
                'analysis_summary': 'Found 5 keywords and 2 patterns indicating potential scam activity'
            }
        }
    )
    analysis.completed_at = timezone.now() - timedelta(minutes=5)
    analysis.save()
    print(f"Created analysis: {analysis.id}")
    
    # Create scam probability score
    scam_score = ScamProbabilityScore.objects.create(
        call_record=call,
        ai_analysis=analysis,
        overall_score=0.85,
        scam_level='high',
        factors={'keyword_matches': 0.8, 'pattern_matches': 0.75},
        keywords_matched=['urgent', 'bank', 'irs', 'social security'],
        patterns_detected=['financial institution', 'identity verification'],
        explanation='High risk score due to multiple scam indicators including urgency, financial institution reference, and identity verification request.'
    )
    print(f"Created scam score: {scam_score.id}")
    
    print("\n✓ Test data created successfully!")
    print(f"Call ID: {call.id}")
    print(f"View at: http://127.0.0.1:8000/calls/{call.id}/")
    return call

if __name__ == '__main__':
    # Clean up existing test data
    CallRecord.objects.filter(caller_number='555-0001').delete()
    
    # Create new test data
    call = create_test_data()
