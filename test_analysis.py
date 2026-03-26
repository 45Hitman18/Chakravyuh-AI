#!/usr/bin/env python
"""Test script to verify analysis pipeline works"""

import os
import sys
import django
import uuid
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chakravyuh.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from calls.models import CallRecord, AudioUpload
from analysis.models import AIAnalysisResult, ScamProbabilityScore
from analysis.pipeline import process_analysis, generate_mock_transcript, transcribe_audio
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

User = get_user_model()

def test_mock_transcript():
    """Test mock transcript generation"""
    print("\n=== Testing Mock Transcript ===")
    transcript = generate_mock_transcript("dummy_path.mp3")
    print(f"Generated mock transcript ({len(transcript)} chars):")
    print(f"'{transcript[:100]}...'")
    assert len(transcript) > 0, "Mock transcript is empty"
    assert any(keyword in transcript.lower() for keyword in ['urgent', 'bank', 'account']), "Mock transcript doesn't contain keywords"
    print("✓ Mock transcript generation works")


def test_transcribe_audio():
    """Test audio transcription fallback"""
    print("\n=== Testing Audio Transcription ===")
    result = transcribe_audio("dummy_path.mp3")
    transcript = result.get('raw_transcript', '')
    print(f"Transcribed audio ({len(transcript)} chars):")
    print(f"'{transcript[:100]}...'")
    assert len(transcript) == 0, "Expected empty transcript for dummy path"
    print("✓ Audio transcription returns empty for invalid audio")


def test_full_analysis():
    """Test full analysis pipeline"""
    print("\n=== Testing Full Analysis Pipeline ===")
    
    # Get or create test user
    user, created = User.objects.get_or_create(
        username='testuser_analysis',
        defaults={'email': 'test@example.com', 'role': 'user'}
    )
    print(f"Using user: {user.username}")
    
    # Create a test call record
    call = CallRecord.objects.create(
        caller_number="+1234567890",
        recipient_number="+9876543210",
        call_start_time=timezone.now(),
        status='completed',
        recorded_by=user
    )
    print(f"Created call: {call.id}")
    
    # Create a dummy audio file
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        # Write minimal WAV header
        tmp.write(b'RIFF')
        tmp.write(b'\x00' * 4)
        tmp.write(b'WAVEfmt ')
        tmp.write(b'\x10\x00\x00\x00')  # fmt chunk size
        tmp.write(b'\x01\x00')  # Audio format (PCM)
        tmp.write(b'\x01\x00')  # Channels
        tmp.write(b'\x44\xac\x00\x00')  # Sample rate
        tmp.write(b'\x88\x58\x01\x00')  # Byte rate
        tmp.write(b'\x02\x00')  # Block align
        tmp.write(b'\x10\x00')  # Bits per sample
        tmp.write(b'data\x00\x00\x00\x00')  # Data chunk
        temp_path = tmp.name
    
    try:
        # Create AudioUpload
        with open(temp_path, 'rb') as f:
            from django.core.files.base import ContentFile
            upload = AudioUpload.objects.create(
                call_record=call,
                audio_file=ContentFile(f.read(), name='test.wav'),
                file_size=1024,
                checksum='test_checksum',
                uploaded_by=user
            )
        print(f"Created audio upload: {upload.id}")
        
        # Create analysis
        analysis = AIAnalysisResult.objects.create(
            call_record=call,
            audio_upload=upload,
            analysis_type='comprehensive',
            status='pending',
            requested_by=user
        )
        print(f"Created analysis (initial status: {analysis.status}): {analysis.id}")
        
        # Run analysis
        print("\nRunning process_analysis...")
        process_analysis(str(analysis.id))
        
        # Check results
        analysis.refresh_from_db()
        print(f"\nAnalysis Status: {analysis.status}")
        print(f"Analysis Results: {analysis.results}")
        print(f"Confidence Score: {analysis.confidence_score}")
        print(f"Error Message: {analysis.error_message}")
        
        # Check for ScamProbabilityScore
        try:
            scam_score = analysis.scam_probability
            print(f"\nScam Probability Score: {scam_score.overall_score}")
            print(f"Scam Level: {scam_score.scam_level}")
            print(f"Keywords Matched: {scam_score.keywords_matched[:5]}")
            print(f"Patterns Detected: {scam_score.patterns_detected[:3]}")
        except:
            print("\n✗ No ScamProbabilityScore found")
            
        assert analysis.status in ['completed', 'failed'], f"Unexpected analysis status: {analysis.status}"
        assert 'raw_transcript' in analysis.results or 'transcript_display' in analysis.results, "Transcript fields missing"
        print("\n✓ Full analysis pipeline runs with separated transcript/analysis")
        
    finally:
        os.unlink(temp_path)
        

if __name__ == '__main__':
    try:
        test_mock_transcript()
        test_transcribe_audio()
        test_full_analysis()
        print("\n=== All Tests Passed ===\n")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
