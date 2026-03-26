#!/usr/bin/env python
"""
Debug script to check what's being rendered on the calls page
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

def debug_calls_page():
    """Debug what's shown on calls page"""
    
    client = Client()
    
    # Get or create and authenticate user
    user, created = User.objects.get_or_create(
        username='debug_user',
        defaults={'email': 'debug@test.com', 'role': 'law_enforcement'}
    )
    
    if created:
        user.set_password('debug123')
        user.save()
    
    # Try login
    login_success = client.login(username='debug_user', password='debug123')
    print(f"Login success: {login_success}")
    
    # Check call count
    call_count = CallRecord.objects.count()
    print(f"\nTotal calls in DB: {call_count}")
    
    # Check our test call
    test_call = CallRecord.objects.filter(caller_number='555-0001').first()
    if test_call:
        print(f"Test call found: {test_call.id}")
        print(f"  - Has audio: {hasattr(test_call, 'audio')}")
        print(f"  - Has analysis: {hasattr(test_call, 'ai_analysis')}")
        if hasattr(test_call, 'ai_analysis'):
            print(f"  - Analysis status: {test_call.ai_analysis.status}")
    else:
        print("Test call NOT found")
    
    # Load calls list page
    print(f"\nLoading calls list page...")
    response = client.get('/calls/')
    
    print(f"Response status: {response.status_code}")
    
    # Check if calls table has rows
    content = response.content.decode()
    
    tbody_count = content.count('<tbody')
    print(f"Tbody elements found: {tbody_count}")
    
    # Count table rows with actual call data
    tr_count = content.count('onclick="selectCall(')
    print(f"Clickable call rows found: {tr_count}")
    
    # Check for our test call
    if '555-0001' in content:
        print(f"✓ Test call (555-0001) IS visible in table")
    else:
        print(f"✗ Test call (555-0001) NOT visible in table")
    
    # Check for audio/transcript preview sections
    if 'audioPreview' in content:
        print(f"✓ audioPreview container found")
    else:
        print(f"✗ audioPreview container NOT found")
    
    if 'transcriptPreview' in content:
        print(f"✓ transcriptPreview container found")
    else:
        print(f"✗ transcriptPreview container NOT found")
    
    print("\n" + "="*60)
    print("If you see:")
    print("✗ Test call NOT visible - check permissions")
    print("✗ audioPreview container NOT found - template issue")
    print("✗ transcriptPreview container NOT found - template issue")
    print("="*60)

if __name__ == '__main__':
    debug_calls_page()
