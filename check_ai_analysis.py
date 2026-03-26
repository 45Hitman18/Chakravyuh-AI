#!/usr/bin/env python
"""
Check if AI analysis is being rendered
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

def check_ai_analysis():
    """Check AI analysis section"""
    
    client = Client()
    
    # Get or create and authenticate user
    user, created = User.objects.get_or_create(
        username='ai_check_user',
        defaults={'email': 'ai@test.com', 'role': 'law_enforcement'}
    )
    
    if created:
        user.set_password('ai123')
        user.save()
    
    client.login(username='ai_check_user', password='ai123')
    
    # Get test call
    call = CallRecord.objects.filter(caller_number='555-0001').first()
    if not call:
        print("No test call found!")
        return
    
    print(f"Checking AI analysis for call: {call.id}\n")
    
    # Check the database
    print("="*60)
    print("DATABASE CHECK")
    print("="*60)
    print(f"Has audio: {hasattr(call, 'audio')}")
    print(f"Has ai_analysis: {hasattr(call, 'ai_analysis')}")
    
    if hasattr(call, 'ai_analysis'):
        analysis = call.ai_analysis
        print(f"AI Analysis exists: YES")
        print(f"  - Status: {analysis.status}")
        print(f"  - Type: {analysis.analysis_type}")
        print(f"  - Results: {analysis.results}")
        print(f"  - Transcript in results: {'raw_transcript' in analysis.results or 'transcript_display' in analysis.results}")
        if 'raw_transcript' in analysis.results or 'transcript_display' in analysis.results:
            preview_text = analysis.results.get('transcript_display') or analysis.results.get('raw_transcript', '')
            print(f"  - Transcript length: {len(preview_text)}")
            print(f"  - Transcript content: {preview_text[:100]}")
    
    # Now check the template rendering
    print("\n" + "="*60)
    print("TEMPLATE RENDERING CHECK")
    print("="*60)
    
    response = client.get(f'/calls/{call.id}/')
    content = response.content.decode()
    
    # Check for AI Analysis section header
    if 'AI Analysis' in content:
        print("✓ 'AI Analysis' section found")
    else:
        print("✗ 'AI Analysis' section NOT found")
    
    # Check for specific sections
    if 'Transcript Preview' in content:
        print("✓ 'Transcript Preview' found")
    else:
        print("✗ 'Transcript Preview' NOT found")
    
    if 'Scam Keywords Found' in content:
        print("✓ 'Scam Keywords Found' section found")
    else:
        print("✗ 'Scam Keywords Found' section NOT found")
    
    # Try to find the actual transcript text
    if call.ai_analysis and (call.ai_analysis.results.get('raw_transcript') or call.ai_analysis.results.get('transcript_display')):
        transcript_text = call.ai_analysis.results.get('transcript_display') or call.ai_analysis.results.get('raw_transcript', '')
        if transcript_text in content:
            print(f"✓ Transcript text appears in rendered HTML")
            # Find where it appears
            pos = content.find(transcript_text)
            print(f"  - Found at position: {pos}")
            print(f"  - Context: ...{content[max(0, pos-100):pos+100]}...")
        else:
            print(f"✗ Transcript text NOT in rendered HTML")
            print(f"  - Text we're looking for: {transcript_text}")

if __name__ == '__main__':
    check_ai_analysis()
