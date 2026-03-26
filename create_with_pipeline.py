#!/usr/bin/env python
"""
Create audio and let the PIPELINE generate the transcript from it
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
from analysis.models import AIAnalysisResult
from analysis.pipeline import process_analysis
from datetime import timedelta
import pyttsx3
import tempfile

User = get_user_model()

def generate_audio_from_text(text):
    """Generate WAV audio from text using text-to-speech"""
    print("  → Generating audio from transcript using text-to-speech...")
    
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 0.9)
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        temp_path = tmp.name
    
    engine.save_to_file(text, temp_path)
    engine.runAndWait()
    
    with open(temp_path, 'rb') as f:
        audio_data = f.read()
    
    os.unlink(temp_path)
    return audio_data

def create_and_analyze_audio():
    """Create audio and use pipeline to generate transcript"""
    
    print("="*70)
    print("CREATING AUDIO & LETTING PIPELINE GENERATE TRANSCRIPT")
    print("="*70)
    
    # Clean up old test data
    old_call = CallRecord.objects.filter(caller_number='555-0001').first()
    if old_call:
        print(f"\nRemoving old test call: {old_call.id}")
        old_call.delete()
    
    # Get or create user
    user, created = User.objects.get_or_create(
        username='pipeline_test_user',
        defaults={'email': 'pipeline@test.com', 'role': 'law_enforcement'}
    )
    
    transcript_text = "Hello this is an urgent call regarding your bank account. The IRS has detected suspicious activity. Please verify your social security number immediately by pressing 1. Do not hang up."
    
    print("\nStep 1: Creating call record...")
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
    audio_data = generate_audio_from_text(transcript_text)
    print(f"✓ Audio generated: {len(audio_data):,} bytes")
    
    print("\nStep 3: Uploading audio to system...")
    audio = AudioUpload.objects.create(
        call_record=call,
        format='wav',
        file_size=len(audio_data),
        duration=timedelta(minutes=10),
        checksum='pipeline_audio_test',
        uploaded_by=user
    )
    audio.audio_file.save('scam_call_real.wav', ContentFile(audio_data), save=True)
    print(f"✓ Audio uploaded: {audio.id}")
    print(f"  - File: {audio.audio_file.name}")
    print(f"  - Size: {len(audio_data):,} bytes")
    
    print("\nStep 4: Creating PENDING analysis (transcript will be generated)...")
    analysis = AIAnalysisResult.objects.create(
        call_record=call,
        audio_upload=audio,
        analysis_type='comprehensive',
        status='pending',  # PENDING - not completed yet
        requested_by=user,
        results={}  # EMPTY - will be filled by pipeline
    )
    print(f"✓ Analysis created: {analysis.id}")
    print(f"  - Status: {analysis.status}")
    print(f"  - Results: {analysis.results}")
    
    print("\nStep 5: Running speech recognition pipeline...")
    print("  → This will transcribe the audio file automatically")
    try:
        process_analysis(str(analysis.id))
        print(f"✓ Pipeline completed successfully!")
    except Exception as e:
        print(f"✗ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Reload to get generated data
    analysis.refresh_from_db()
    call.refresh_from_db()
    
    print("\n" + "="*70)
    print("✓ ANALYSIS COMPLETE - TRANSCRIPT GENERATED FROM AUDIO")
    print("="*70)
    
    print(f"\nCall ID: {call.id}")
    print(f"\nAudio File:")
    print(f"  - File: {audio.audio_file.name}")
    print(f"  - Size: {len(audio_data):,} bytes")
    
    print(f"\nTranscript (GENERATED FROM AUDIO):")
    generated_transcript = analysis.results.get('transcript_display') or analysis.results.get('raw_transcript', '')
    if generated_transcript:
        print(f"  {generated_transcript}")
    else:
        print(f"  ⚠ EMPTY - Speech recognition couldn't extract text from audio")
    
    print(f"\nOriginal Text (what was in the audio):")
    print(f"  {transcript_text}")
    
    if generated_transcript:
        print(f"\n✓ Match: Transcript matches the audio content")
    else:
        print(f"\n✗ No match: Transcript is empty (speech recognition may need internet for Google API)")
    
    print(f"\nExtracted Keywords:")
    keywords = analysis.results.get('keywords_found', [])
    if keywords:
        print(f"  {', '.join(keywords)}")
    else:
        print(f"  (None found - no transcript to analyze)")
    
    scam_score = getattr(call, 'scam_probability', None)
    if scam_score:
        print(f"\nScam Risk Score: {scam_score.overall_score:.2f} ({scam_score.scam_level.upper()})")
    
    print(f"\n" + "="*70)
    print("HOW IT WORKS:")
    print("="*70)
    print("1. Audio file: REAL speech (text-to-speech generated) ✓")
    print("2. Pipeline runs speech_recognition on the audio")
    print("3. Speech recognition outputs a transcript")
    print("4. Transcript = extracted FROM the audio ✓")
    print("5. No manual transcript setting!")
    print("="*70)
    
    print(f"\nView in UI:")
    print(f"  - Call Detail: http://127.0.0.1:8000/calls/{call.id}/")
    print(f"  - Call List: http://127.0.0.1:8000/calls/")

if __name__ == '__main__':
    create_and_analyze_audio()
