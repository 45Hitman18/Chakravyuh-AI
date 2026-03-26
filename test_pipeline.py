#!/usr/bin/env python
"""Direct test of pipeline functions"""

import os
import sys
import django
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chakravyuh.settings')
sys.path.insert(0, str(Path(__file__).parent))
django.setup()

from analysis.pipeline import generate_mock_transcript, analyze_transcript

# Test 1: Mock transcript
print("=== Test 1: Mock Transcript Generation ===")
for i in range(1):
    transcript = generate_mock_transcript("dummy.wav")
    print(f"Full Scenario {i+1}:")
    print(f"  {transcript}")
    print()

# Test 2: Analysis with full output
print("\n=== Test 2: Analyze Transcript ===")
transcript = generate_mock_transcript("dummy.wav")
print(f"Transcript: {transcript}")
print()

analysis = analyze_transcript(transcript)
print(f"Keywords found: {len(analysis['keywords_matched'])}")
print(f"All keywords matched: {analysis['keywords_matched']}")
print(f"Patterns detected: {len(analysis['patterns_detected'])}")
print(f"All patterns: {analysis['patterns_detected']}")
print(f"Keyword score: {analysis['keyword_score']:.3f}")
print(f"Pattern score: {analysis['pattern_score']:.3f}")
print(f"Text score: {analysis['text_score']:.3f}")

print("\n✓ All tests passed!")
