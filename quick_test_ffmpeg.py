#!/usr/bin/env python
"""Quick test to verify FFmpeg is accessible and audio processing works"""

import os
import sys
import shutil
import glob

# Check FFmpeg availability
ffmpeg_path = shutil.which('ffmpeg')
print(f"ffmpeg in PATH: {ffmpeg_path}")

if not ffmpeg_path:
    local_app_data = os.environ.get('LOCALAPPDATA')
    if local_app_data:
        candidates = glob.glob(os.path.join(
            local_app_data,
            'Microsoft',
            'WinGet',
            'Packages',
            'Gyan.FFmpeg_*',
            'ffmpeg-*-full_build',
            'bin',
            'ffmpeg.exe'
        ))
        if candidates:
            ffmpeg_path = candidates[0]
            print(f"ffmpeg found in WinGet: {ffmpeg_path}")

if not ffmpeg_path:
    print("ERROR: ffmpeg not found!")
    sys.exit(1)

# Test pydub with explicit ffmpeg configuration
from pydub import AudioSegment
AudioSegment.converter = ffmpeg_path
AudioSegment.ffmpeg = ffmpeg_path

# Find an audio file to test
audio_files = glob.glob(os.path.join('media/call_recordings/*.mp3'))
if audio_files:
    test_file = audio_files[0]
    print(f"\nTesting with: {test_file}")
    try:
        audio = AudioSegment.from_file(test_file)
        print(f"✓ Successfully loaded audio: {len(audio)}ms ({len(audio)/1000:.2f}s)")
        
        # Test conversion
        audio_mono = audio.set_channels(1).set_frame_rate(16000)
        print(f"✓ Successfully converted to mono 16kHz")
        print(f"✓ Duration: {len(audio_mono)/1000:.2f}s")
    except Exception as e:
        print(f"✗ Error processing audio: {e}")
        import traceback
        traceback.print_exc()
else:
    print("No audio files found to test")
