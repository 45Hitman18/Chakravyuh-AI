#!/usr/bin/env python
"""
Check what HTML is being rendered for audio and transcript
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

def check_detail_page_html():
    """Check the HTML rendered on detail page"""
    
    client = Client()
    
    # Get or create and authenticate user
    user, created = User.objects.get_or_create(
        username='html_check_user',
        defaults={'email': 'check@test.com', 'role': 'law_enforcement'}
    )
    
    if created:
        user.set_password('check123')
        user.save()
    
    # Try login
    login_success = client.login(username='html_check_user', password='check123')
    print(f"Login: {login_success}\n")
    
    # Get test call
    call = CallRecord.objects.filter(caller_number='555-0001').first()
    if not call:
        print("No test call found!")
        return
    
    print(f"Checking call: {call.id}\n")
    
    # Load detail page
    response = client.get(f'/calls/{call.id}/')
    content = response.content.decode()
    
    # Check for audio
    print("="*60)
    print("AUDIO SECTION CHECK")
    print("="*60)
    
    if '<audio' in content:
        print("✓ <audio> tag found")
        # Find and print audio section
        start = content.find('<audio')
        if start > 0:
            end = content.find('</audio>', start) + len('</audio>')
            audio_html = content[start:end]
            print(f"\nAudio HTML:\n{audio_html}\n")
    else:
        print("✗ <audio> tag NOT found")
    
    if 'id="callAudio"' in content:
        print("✓ Audio has ID 'callAudio'")
    else:
        print("✗ Audio ID 'callAudio' NOT found")
    
    if 'id="audioSection"' in content:
        print("✓ Audio section has ID 'audioSection'")
    else:
        print("✗ Audio section ID NOT found")
    
    # Check for transcript
    print("\n" + "="*60)
    print("TRANSCRIPT SECTION CHECK")
    print("="*60)
    
    if 'id="transcriptContent"' in content:
        print("✓ Transcript content ID found")
        # Find transcript content
        start = content.find('id="transcriptContent"')
        if start > 0:
            # Extract a snippet
            snippet_start = max(0, start - 100)
            snippet_end = min(len(content), start + 300)
            snippet = content[snippet_start:snippet_end]
            print(f"\nTranscript snippet:\n...{snippet}...\n")
    else:
        print("✗ Transcript content ID NOT found")
    
    if 'Transcript Preview' in content:
        print("✓ 'Transcript Preview' text found")
    else:
        print("✗ 'Transcript Preview' text NOT found")
    
    if 'id="transcriptSection"' in content:
        print("✓ Transcript section ID found")
    else:
        print("✗ Transcript section ID NOT found")
    
    # Check for keywords
    print("\n" + "="*60)
    print("KEYWORDS CHECK")
    print("="*60)
    
    keywords_to_find = ['urgent', 'bank', 'irs', 'suspicious']
    for keyword in keywords_to_find:
        if keyword in content.lower():
            print(f"✓ Keyword '{keyword}' found in page")
        else:
            print(f"✗ Keyword '{keyword}' NOT found")
    
    print("\n" + "="*60)
    print("DATA PRESENT IN PAGE")
    print("="*60)
    print(f"Page length: {len(content)} characters")
    print(f"Scam score mentions: {content.count('0.85')}")
    print(f"'HIGH' risk level: {content.count('HIGH')}")

if __name__ == '__main__':
    check_detail_page_html()
