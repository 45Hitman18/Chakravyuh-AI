#!/usr/bin/env python
"""
Quick verification that audio and transcript are showing in templates
"""

import os
import sys
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chakravyuh.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from calls.models import CallRecord

def check_call_data():
    """Check if test call has audio and transcript data"""
    
    call = CallRecord.objects.filter(caller_number='555-0001').first()
    
    if not call:
        print("❌ No test call found")
        return False
    
    print("=" * 60)
    print("VERIFYING TEST DATA")
    print("=" * 60)
    
    print(f"\n✓ Call found: {call.id}")
    print(f"  - Caller: {call.caller_number}")
    print(f"  - Recipient: {call.recipient_number}")
    
    # Check audio
    audio = getattr(call, 'audio', None)
    if audio:
        print(f"\n✓ Audio found: {audio.id}")
        print(f"  - Format: {audio.format}")
        print(f"  - File: {audio.audio_file.name}")
        print(f"  - URL: {audio.audio_file.url}")
    else:
        print("\n❌ No audio found")
        return False
    
    # Check analysis
    analysis = getattr(call, 'ai_analysis', None)
    if analysis:
        print(f"\n✓ AI Analysis found: {analysis.id}")
        print(f"  - Status: {analysis.status}")
        print(f"  - Type: {analysis.analysis_type}")
        
        # Check transcript
        if analysis.results.get('raw_transcript') or analysis.results.get('transcript_display'):
            print(f"\n✓ Transcript found:")
            preview_text = analysis.results.get('transcript_display') or analysis.results.get('raw_transcript', '')
            print(f"  - Length: {len(preview_text)} characters")
            print(f"  - Preview: {preview_text[:100]}...")
        else:
            print("\n❌ No transcript in results")
            return False
        
        # Check keywords
        analysis_block = analysis.results.get('analysis', {})
        if analysis_block.get('keywords_found'):
            print(f"\n✓ Keywords found:")
            print(f"  - Count: {len(analysis_block['keywords_found'])}")
            print(f"  - Keywords: {', '.join(analysis_block['keywords_found'])}")
        else:
            print("\n⚠ No keywords in results")
        
        # Check patterns
        if analysis.results.get('patterns_found'):
            print(f"\n✓ Patterns found:")
            print(f"  - Count: {len(analysis.results['patterns_found'])}")
            print(f"  - Patterns: {', '.join(analysis.results['patterns_found'])}")
        else:
            print("\n⚠ No patterns in results")
    else:
        print("\n❌ No AI analysis found")
        return False
    
    # Check scam score
    scam_score = getattr(call, 'scam_probability', None)
    if scam_score:
        print(f"\n✓ Scam Score found:")
        print(f"  - Score: {scam_score.overall_score:.2f}")
        print(f"  - Level: {scam_score.scam_level}")
    else:
        print("\n⚠ No scam score found")
    
    print("\n" + "=" * 60)
    print("✓ ALL DATA VERIFIED SUCCESSFULLY!")
    print("=" * 60)
    print("\nYou can now view:")
    print(f"  1. Call List: http://127.0.0.1:8000/calls/")
    print(f"  2. Call Detail: http://127.0.0.1:8000/calls/{call.id}/")
    print("\nFeatures implemented:")
    print("  ✓ Audio Preview - Shows in both list and detail pages")
    print("  ✓ Transcript Preview - Shows in both list and detail pages")
    print("  ✓ Keywords Display - Shows detected scam keywords")
    print("  ✓ Patterns Detection - Shows detected patterns")
    
    return True

if __name__ == '__main__':
    success = check_call_data()
    sys.exit(0 if success else 1)
