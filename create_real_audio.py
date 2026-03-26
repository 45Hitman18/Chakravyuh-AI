#!/usr/bin/env python
"""
Create REAL audio matching the transcript using text-to-speech
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
from django.core.files.base import ContentFile
from calls.models import CallRecord, AudioUpload
from analysis.models import AIAnalysisResult, ScamProbabilityScore
from analysis.pipeline import process_analysis
from datetime import timedelta

User = get_user_model()

def generate_audio_from_text(text):
    """Generate WAV audio from text using text-to-speech"""
    import pyttsx3
    import tempfile
    
    print("  Generating audio from transcript using text-to-speech...")
    
    # Initialize engine
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)  # Slower speech like a scam call
    engine.setProperty('volume', 0.9)
    
    # Create temp file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        temp_path = tmp.name
    
    # Save to file
    engine.save_to_file(text, temp_path)
    engine.runAndWait()
    
    # Read the generated audio
    with open(temp_path, 'rb') as f:
        audio_data = f.read()
    
    # Clean up
    os.unlink(temp_path)
    
    return audio_data

def create_real_audio_test():
    """Create test data with REAL audio that matches the transcript"""
    
    print("Creating test data with REAL audio...\n")
    
    # Clean up old test data
    old_call = CallRecord.objects.filter(caller_number='555-0001').first()
    if old_call:
        print(f"Removing old test call: {old_call.id}")
        old_call.delete()
    
    # Get or create user
    user, created = User.objects.get_or_create(
        username='audio_test_user',
        defaults={'email': 'audio@test.com', 'role': 'law_enforcement'}
    )
    
    transcript_text = "Hello this is an urgent call regarding your bank account. The IRS has detected suspicious activity. Please verify your social security number immediately by pressing 1. Do not hang up."
    
    print("Step 1: Creating call record...")
    call = CallRecord.objects.create(
        caller_number='555-0001',
        recipient_number='555-0002',
        call_start_time=timezone.now() - timedelta(hours=1),
        call_end_time=timezone.now() - timedelta(minutes=50),
        duration=timedelta(minutes=10),
        status='completed',
        recorded_by=user
    )
    print(f"✓ Call created: {call.id}")
    
    print("\nStep 2: Generating REAL audio from transcript...")
    try:
        audio_data = generate_audio_from_text(transcript_text)
        print(f"✓ Audio generated: {len(audio_data)} bytes")
    except Exception as e:
        print(f"✗ Audio generation failed: {e}")
        print("  Falling back to empty audio...")
        audio_data = b'RIFF' + b'\x00' * 1000
    
    print("\nStep 3: Creating audio upload...")
    audio = AudioUpload.objects.create(
        call_record=call,
        format='wav',
        file_size=len(audio_data),
        duration=timedelta(minutes=10),
        checksum='real_audio_test',
        uploaded_by=user
    )
    audio.audio_file.save('real_scam_call.wav', ContentFile(audio_data), save=True)
    print(f"✓ Audio uploaded: {audio.id}")
    print(f"  - File: {audio.audio_file.name}")
    print(f"  - Size: {len(audio_data)} bytes")
    
    print("\nStep 4: Creating AI analysis with transcript...")
    analysis = AIAnalysisResult.objects.create(
        call_record=call,
        audio_upload=audio,
        analysis_type='comprehensive',
        status='completed',
        confidence_score=0.92,
        requested_by=user,
        results={
            'raw_transcript': transcript_text,
            'transcript_display': transcript_text,
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
    print(f"✓ Analysis created: {analysis.id}")
    
    print("\nStep 5: Creating scam probability score...")
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
    print(f"✓ Scam score created: {scam_score.id}")
    print(f"  - Score: {scam_score.overall_score:.2f}")
    print(f"  - Level: {scam_score.scam_level.upper()}")
    
    print("\n" + "="*70)
    print("✓ TEST DATA WITH REAL AUDIO CREATED SUCCESSFULLY!")
    print("="*70)
    print(f"\nCall ID: {call.id}")
    print(f"\nAudio File Details:")
    print(f"  - Path: /media/{audio.audio_file.name}")
    print(f"  - Size: {len(audio_data):,} bytes")
    print(f"  - Duration: {audio.duration}")
    print(f"\nTranscript (from text-to-speech):")
    print(f"  {transcript_text}")
    print(f"\nDetected Keywords: {len(analysis.results['keywords_found'])}")
    for kw in analysis.results['keywords_found']:
        print(f"  • {kw}")
    print(f"\nScam Risk: {scam_score.overall_score:.2%} ({scam_score.scam_level.upper()})")
    print(f"\nView in UI:")
    print(f"  - Call Detail: http://127.0.0.1:8000/calls/{call.id}/")
    print(f"  - Call List: http://127.0.0.1:8000/calls/")
    print("\n" + "="*70)
    print("NOW YOU CAN:")
    print("="*70)
    print("1. Go to Call List and click on the call (555-0001)")
    print("2. Audio Preview will show REAL audio with speech ✓")
    print("3. Transcript Preview will show the MATCHING text ✓")
    print("4. Both will play/display from the same call content")
    print("="*70)

if __name__ == '__main__':
    create_real_audio_test()
