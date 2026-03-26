#!/usr/bin/env python
"""
Comprehensive test of the upload + analysis flow
Simulates exactly what happens when a user clicks "Upload & Analyze"
"""

import os
import sys
import django
from pathlib import Path
import tempfile
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chakravyuh.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from calls.models import CallRecord, AudioUpload
from analysis.models import AIAnalysisResult, ScamProbabilityScore
from analysis.pipeline import process_analysis
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

User = get_user_model()

def create_test_audio_file():
    """Create a minimal valid WAV file"""
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        # Write minimal WAV header
        tmp.write(b'RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data')
        tmp.write(b'\x00' * 1000)  # 1000 bytes of silence
        return tmp.name

def test_full_upload_flow():
    """Test complete upload -> analysis flow"""
    
    print("=" * 60)
    print("TESTING COMPLETE UPLOAD + ANALYSIS FLOW")
    print("=" * 60)
    
    # Step 1: Get or create test user
    print("\n[Step 1] Creating test user...")
    user, created = User.objects.get_or_create(
        username='upload_test_user',
        defaults={'email': 'upload@test.com', 'role': 'law_enforcement'}
    )
    if created:
        user.set_password('testpass')
        user.save()
        print(f"  ✓ Created new user: {user.username}")
    else:
        print(f"  ✓ Using existing user: {user.username}")
    
    # Step 2: Create call record (what upload view does)
    print("\n[Step 2] Creating CallRecord...")
    call = CallRecord.objects.create(
        caller_number="+1-800-SCAMMER",
        recipient_number="+1-617-VICTIM",
        call_start_time=timezone.now(),
        status='completed',
        recorded_by=user
    )
    print(f"  ✓ Created call: {call.id}")
    print(f"    Caller: {call.caller_number}")
    print(f"    Recipient: {call.recipient_number}")
    
    # Step 3: Create audio file and AudioUpload (what upload view does)
    print("\n[Step 3] Creating AudioUpload...")
    audio_path = create_test_audio_file()
    try:
        with open(audio_path, 'rb') as f:
            content = f.read()
            checksum = hashlib.sha256(content).hexdigest()
        
        from django.core.files.base import ContentFile
        audio_upload = AudioUpload.objects.create(
            call_record=call,
            audio_file=ContentFile(open(audio_path, 'rb').read(), name='test_upload.wav'),
            file_size=len(content),
            checksum=checksum,
            uploaded_by=user
        )
        print(f"  ✓ Created audio upload: {audio_upload.id}")
        print(f"    File size: {audio_upload.file_size} bytes")
        print(f"    Checksum: {audio_upload.checksum[:16]}...")
    finally:
        os.unlink(audio_path)
    
    # Step 4: Create AIAnalysisResult (what upload view does)
    print("\n[Step 4] Creating AIAnalysisResult...")
    analysis = AIAnalysisResult.objects.create(
        call_record=call,
        audio_upload=audio_upload,
        analysis_type='comprehensive',
        status='pending',
        requested_by=user
    )
    print(f"  ✓ Created analysis: {analysis.id}")
    print(f"    Initial status: {analysis.status}")
    
    # Step 5: Run process_analysis (what upload view does after form submission)
    print("\n[Step 5] Running process_analysis()...")
    print("  This is the core analysis pipeline...")
    start_time = time.time()
    try:
        process_analysis(str(analysis.id))
        elapsed = time.time() - start_time
        print(f"  ✓ Analysis completed in {elapsed:.2f} seconds")
    except Exception as e:
        print(f"  ✗ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 6: Check results
    print("\n[Step 6] Checking analysis results...")
    analysis.refresh_from_db()
    print(f"  Status: {analysis.status}")
    print(f"  Confidence Score: {analysis.confidence_score}")
    print(f"  Results: {analysis.results}")
    
    if analysis.status != 'completed':
        print(f"  ✗ Analysis not completed (status={analysis.status})")
        return False
    
    # Step 7: Check ScamProbabilityScore
    print("\n[Step 7] Checking ScamProbabilityScore...")
    try:
        scam_score = analysis.scam_probability
        print(f"  ✓ ScamProbabilityScore found")
        print(f"    Overall Score: {scam_score.overall_score:.3f}")
        print(f"    Scam Level: {scam_score.scam_level}")
        print(f"    Keywords Matched: {scam_score.keywords_matched}")
        print(f"    Patterns Detected: {scam_score.patterns_detected}")
    except Exception as e:
        print(f"  ✗ No ScamProbabilityScore: {e}")
        return False
    
    # Step 8: Verify what JavaScript will see (status endpoint)
    print("\n[Step 8] Simulating JavaScript poll...")
    from dashboard.views import dashboard_analysis_status
    from django.test import RequestFactory
    
    request = RequestFactory().get(f'/dashboard/analysis-status/{analysis.id}/')
    request.user = user
    
    response = dashboard_analysis_status(request, analysis.id)
    import json
    data = json.loads(response.content)
    print(f"  Status response: {data}")
    
    print("\n" + "=" * 60)
    print("✓ FULL UPLOAD + ANALYSIS FLOW SUCCESSFUL")
    print("=" * 60)
    return True

if __name__ == '__main__':
    success = test_full_upload_flow()
    sys.exit(0 if success else 1)
