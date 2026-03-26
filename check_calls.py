#!/usr/bin/env python
"""Check status of all pending calls"""

import os
import sys
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chakravyuh.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from calls.models import CallRecord
from analysis.models import AIAnalysisResult, ScamProbabilityScore

print("=" * 70)
print("CHECKING ALL CALLS AND THEIR ANALYSIS STATUS")
print("=" * 70)

calls = CallRecord.objects.all().order_by('-created_at')
pending_count = 0
completed_count = 0
failed_count = 0

for call in calls:
    try:
        analysis = call.ai_analysis
        caller = call.caller_number or "unknown"
        status = analysis.status
        
        if status == 'pending':
            pending_count += 1
            indicator = "⏳"
        elif status == 'completed':
            completed_count += 1
            indicator = "✓"
        elif status == 'failed':
            failed_count += 1
            indicator = "✗"
        else:
            indicator = "?"
            
        print(f"\n{indicator} Call ID: {str(call.id)[:12]}...")
        print(f"   Caller: {caller}")
        print(f"   Analysis Status: {status}")
        
        if analysis.error_message:
            print(f"   Error: {analysis.error_message[:80]}")
        
        try:
            scam = analysis.scam_probability
            print(f"   Risk: {scam.scam_level} ({scam.overall_score:.3f})")
        except:
            if status == 'completed':
                print(f"   ✗ ERROR: Completed but no ScamProbabilityScore!")
            
    except Exception as e:
        print(f"\n✗ Call ID: {str(call.id)[:12]}... - NO ANALYSIS")
        print(f"   Error: {e}")

print("\n" + "=" * 70)
print(f"SUMMARY: {completed_count} Completed | {pending_count} Pending | {failed_count} Failed")
print("=" * 70)
