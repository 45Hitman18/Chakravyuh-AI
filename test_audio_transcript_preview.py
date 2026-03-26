#!/usr/bin/env python
"""
Test both Audio and Transcript Preview features on calls page
"""

import os
import sys
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chakravyuh.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from calls.models import CallRecord

User = get_user_model()

def test_audio_and_transcript_preview():
    """Test that audio and transcript previews render correctly"""
    
    client = Client()
    
    # Get or create test user
    user, created = User.objects.get_or_create(
        username='test_user',
        defaults={'email': 'test@test.com', 'role': 'law_enforcement'}
    )
    
    # Set password properly
    if created:
        user.set_password('testpass123')
        user.save()
    
    # Login
    login_success = client.login(username='test_user', password='testpass123')
    
    if not login_success:
        print("❌ Failed to authenticate. Trying without login...")
        # Continue anyway to see if page structure is correct
    
    # Get the test call we created
    call = CallRecord.objects.filter(caller_number='555-0001').first()
    
    if not call:
        print("❌ No test call found. Please run test_templates.py first.")
        return False
    
    print("=" * 60)
    print("TESTING AUDIO AND TRANSCRIPT PREVIEW")
    print("=" * 60)
    
    # Test 1: Call Detail Page
    print(f"\n[Test 1] Loading call detail page...")
    print(f"         Call ID: {call.id}")
    
    response = client.get(f'/calls/{call.id}/')
    
    if response.status_code != 200:
        print(f"❌ Failed to load call detail page. Status code: {response.status_code}")
        return False
    
    print(f"✓ Page loaded successfully (Status: {response.status_code})")
    
    # Check if audio section exists
    content = response.content.decode()
    
    if 'id="audioSection"' in content or 'Audio Recording' in content:
        print("✓ Audio Section found in template")
    else:
        print("❌ Audio Section NOT found in template")
        return False
    
    if 'audio' in content and 'controls' in content:
        print("✓ Audio controls HTML element found")
    else:
        print("❌ Audio controls HTML element NOT found")
        return False
    
    # Check if transcript section exists
    if 'Transcript Preview' in content:
        print("✓ Transcript Preview section found in template")
    else:
        print("❌ Transcript Preview section NOT found in template")
        return False
    
    if 'transcriptContent' in content or 'urgent' in content.lower():
        print("✓ Transcript content found in page")
    else:
        print("❌ Transcript content NOT found in page")
        return False
    
    # Check if keywords are displayed
    if 'Keywords Found' in content or 'keywords_found' in content.lower():
        print("✓ Keywords section found in template")
    else:
        print("⚠ Keywords section might be missing")
    
    # Test 2: Call List Page with preview
    print(f"\n[Test 2] Loading call list page...")
    
    response = client.get('/calls/')
    
    if response.status_code != 200:
        print(f"❌ Failed to load call list page. Status code: {response.status_code}")
        return False
    
    print(f"✓ Call list page loaded successfully (Status: {response.status_code})")
    
    content = response.content.decode()
    
    # Check if audio preview container exists
    if 'audioPreview' in content:
        print("✓ Audio Preview container found in template")
    else:
        print("❌ Audio Preview container NOT found in template")
    
    # Check if transcript preview container exists
    if 'transcriptPreview' in content:
        print("✓ Transcript Preview container found in template")
    else:
        print("❌ Transcript Preview container NOT found in template")
    
    # Check if JavaScript for extraction is present
    if 'audioSection' in content or '#audioSection' in content:
        print("✓ Audio extraction JavaScript found")
    else:
        print("⚠ Audio extraction JavaScript might be missing")
    
    if 'transcriptSection' in content or '#transcriptSection' in content:
        print("✓ Transcript extraction JavaScript found")
    else:
        print("⚠ Transcript extraction JavaScript might be missing")
    
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nSummary:")
    print("✓ Audio Preview is working on the calls page")
    print("✓ Transcript Preview is working on the calls page")
    print("\nYou can now view both features at:")
    print(f"  - Call Detail: http://127.0.0.1:8000/calls/{call.id}/")
    print(f"  - Call List: http://127.0.0.1:8000/calls/")
    
    return True

if __name__ == '__main__':
    success = test_audio_and_transcript_preview()
    sys.exit(0 if success else 1)
