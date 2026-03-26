#!/usr/bin/env python
"""Quick test of upload endpoint"""

import os
import sys
import django
import requests
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chakravyuh.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from calls.models import CallRecord, AudioUpload
from analysis.models import AIAnalysisResult
import tempfile

User = get_user_model()

# Create test user if needed
user, _ = User.objects.get_or_create(
    username='testcall',
    defaults={'email': 'test@example.com', 'password': 'testpass', 'role': 'user'}
)

# Create Django test client
client = Client()

# Login
login_ok = client.login(username='testcall', password='testpass')
if not login_ok:
    # Try to set password first
    user.set_password('testpass')
    user.save()
    login_ok = client.login(username='testcall', password='testpass')
    
print(f"Login successful: {login_ok}")

# Create a minimal WAV file
with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
    # Write minimal WAV header
    tmp.write(b'RIFF\x00\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data')
    tmp.write(b'\x00' * 1000)  # 1000 bytes of silence
    temp_path = tmp.name

try:
    # Prepare upload data
    with open(temp_path, 'rb') as f:
        upload_data = {
            'caller_number': '+1234567890',
            'recipient_number': '+9876543210',
            'audio_file': f
        }
        
        # Send POST request to upload endpoint
        response = client.post('/dashboard/upload-audio/', upload_data, follow=False)
        
    print(f"\nUpload Response Status: {response.status_code}")
    print(f"Response Data: {response.json() if response.status_code in [200, 201] else response.content}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            analysis_id = data.get('analysis_id')
            print(f"\nAnalysis ID: {analysis_id}")
            
            # Check analysis status
            status_response = client.get(f'/dashboard/analysis-status/{analysis_id}/', follow=False)
            print(f"\nStatus Response: {status_response.json()}")
            
finally:
    os.unlink(temp_path)
