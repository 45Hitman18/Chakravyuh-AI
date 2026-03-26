#!/usr/bin/env python
"""
Create PROPER test data where transcript is generated from audio
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

def create_realistic_test_data():
    """Create test data that uses the real transcription pipeline"""
    
    print("Creating REALISTIC test data...\n")
    
    # Clean up old test data
    CallRecord.objects.filter(caller_number='555-0099').delete()
    
    # Get or create user
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'email': 'test@test.com', 'role': 'law_enforcement'}
    )
    
    # Create call record
    call = CallRecord.objects.create(
        caller_number='555-0099',
        recipient_number='555-1000',
        call_start_time=timezone.now() - timedelta(hours=2),
        call_end_time=timezone.now() - timedelta(minutes=110),
        duration=timedelta(minutes=120),
        status='completed',
        recorded_by=user
    )
    print(f"✓ Created call: {call.id}")
    
    # Create a realistic WAV file
    # This is a minimal WAV header with some audio data
    wav_data = create_minimal_wav()
    
    # Create audio upload
    audio = AudioUpload.objects.create(
        call_record=call,
        format='wav',
        file_size=len(wav_data),
        duration=timedelta(minutes=2),
        checksum='realistic_test_audio',
        uploaded_by=user
    )
    audio.audio_file.save('realistic_test_audio.wav', ContentFile(wav_data), save=True)
    print(f"✓ Created audio: {audio.id}")
    print(f"  - File size: {len(wav_data)} bytes")
    
    # Create AI analysis
    analysis = AIAnalysisResult.objects.create(
        call_record=call,
        audio_upload=audio,
        analysis_type='comprehensive',
        status='pending',
        requested_by=user,
    )
    print(f"✓ Created analysis: {analysis.id}")
    
    # Now process the analysis - this will use the mock transcriber
    # since we don't have real speech_recognition with audio
    print(f"\n→ Processing analysis (this will generate transcript from audio mock)...")
    try:
        process_analysis(str(analysis.id))
        print(f"✓ Analysis completed successfully!")
    except Exception as e:
        print(f"✗ Analysis failed: {e}")
        return None
    
    # Reload to get updated data
    analysis.refresh_from_db()
    call.refresh_from_db()
    
    # Display results
    print(f"\n" + "="*60)
    print("TEST DATA CREATED SUCCESSFULLY")
    print("="*60)
    print(f"\nCall ID: {call.id}")
    print(f"\nGenerated Transcript:")
    print(f"  {analysis.results.get('transcript_display') or analysis.results.get('raw_transcript', 'NO TRANSCRIPT')}")
    print(f"\nExtracted Keywords:")
    print(f"  {', '.join(analysis.results.get('keywords_found', []))}")
    print(f"\nDetected Patterns:")
    print(f"  {', '.join(analysis.results.get('patterns_found', []))}")
    
    # Check if scam score was created
    scam_score = getattr(call, 'scam_probability', None)
    if scam_score:
        print(f"\nScam Risk Score: {scam_score.overall_score:.2f}")
        print(f"Risk Level: {scam_score.scam_level.upper()}")
    
    print(f"\n" + "="*60)
    print(f"View at: http://127.0.0.1:8000/calls/{call.id}/")
    print("="*60)
    
    return call

def create_minimal_wav():
    """Create a minimal but valid WAV file"""
    # WAV header structure
    sample_rate = 16000  # 16 kHz
    num_channels = 1     # Mono
    bytes_per_sample = 2 # 16-bit
    duration_seconds = 5 # 5 seconds
    
    num_samples = sample_rate * duration_seconds
    data_size = num_samples * num_channels * bytes_per_sample
    
    # WAV header
    header = bytearray()
    
    # RIFF header
    header.extend(b'RIFF')
    header.extend((36 + data_size).to_bytes(4, byteorder='little'))
    header.extend(b'WAVE')
    
    # fmt subchunk
    header.extend(b'fmt ')
    header.extend((16).to_bytes(4, byteorder='little'))  # Subchunk size
    header.extend((1).to_bytes(2, byteorder='little'))   # Audio format (PCM)
    header.extend(num_channels.to_bytes(2, byteorder='little'))
    header.extend(sample_rate.to_bytes(4, byteorder='little'))
    header.extend((sample_rate * num_channels * bytes_per_sample).to_bytes(4, byteorder='little'))  # Byte rate
    header.extend((num_channels * bytes_per_sample).to_bytes(2, byteorder='little'))  # Block align
    header.extend((16).to_bytes(2, byteorder='little'))  # Bits per sample
    
    # data subchunk
    header.extend(b'data')
    header.extend(data_size.to_bytes(4, byteorder='little'))
    
    # Add some mock audio data (simple sine wave pattern to simulate audio)
    import struct
    audio_data = bytearray()
    for i in range(num_samples):
        # Create a simple pattern (not real speech, but valid audio)
        sample = int(32767 * 0.3 * (i % 100) / 100)
        audio_data.extend(struct.pack('<h', sample))
    
    return bytes(header) + bytes(audio_data)

if __name__ == '__main__':
    call = create_realistic_test_data()
    if call:
        print(f"\n✓ Success! You can now view the call in the UI")
    else:
        print(f"\n✗ Failed to create test data")
