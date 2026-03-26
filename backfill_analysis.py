#!/usr/bin/env python
"""Create and run analysis for calls missing AI analysis records."""

import os
import sys
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chakravyuh.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from calls.models import CallRecord
from analysis.models import AIAnalysisResult
from analysis.pipeline import process_analysis

created = 0
processed = 0

for call in CallRecord.objects.all().order_by('-created_at'):
    if hasattr(call, 'ai_analysis'):
        continue
    # Only backfill if an audio upload exists
    try:
        audio = call.audio
    except Exception:
        continue

    analysis = AIAnalysisResult.objects.create(
        call_record=call,
        audio_upload=audio,
        analysis_type='comprehensive',
        status='pending',
        requested_by=call.recorded_by,
    )
    created += 1

    try:
        process_analysis(str(analysis.id))
        processed += 1
        print(f"Processed analysis for call {call.id}")
    except Exception as e:
        print(f"Failed analysis for call {call.id}: {e}")

print(f"Created {created} analyses, processed {processed}.")
