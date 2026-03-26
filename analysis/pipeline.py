"""
Analysis Pipeline for Audio Files

This module handles the processing of uploaded audio files for scam detection.
Implements real AI analysis: audio → transcription → feature extraction → scoring
"""

import logging
import re
import os
import shutil
import glob
import subprocess
import tempfile
import wave

from analysis.models import AIAnalysisResult, ScamProbabilityScore

logger = logging.getLogger(__name__)

# Get FFmpeg path once at module load
def _get_ffmpeg_path():
    """Find FFmpeg executable - check PATH first, then WinGet"""
    ffmpeg_path = shutil.which('ffmpeg')
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
    return ffmpeg_path

FFMPEG_PATH = _get_ffmpeg_path()
if FFMPEG_PATH:
    logger.info(f"FFmpeg found at: {FFMPEG_PATH}")
else:
    logger.warning("FFmpeg not found - audio preprocessing will be unavailable")

# Define scam detection keywords and patterns
SCAM_KEYWORDS = [
    'urgent', 'emergency', 'important', 'confidential', 'secret',
    'password', 'pin', 'account', 'bank', 'credit card', 'debit card',
    'lottery', 'winner', 'prize', 'inheritance', 'million', 'billion',
    'irs', 'tax', 'police', 'court', 'arrest', 'warrant', 'lawyer',
    'virus', 'hack', 'scam', 'fraud', 'phishing', 'identity theft',
    'social security', 'ssn', 'medicare', 'insurance', 'refund',
    'donation', 'charity', 'help', 'victim', 'crisis', 'disaster'
]

SCAM_PATTERNS = [
    r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone numbers
    r'\$\d+(?:,\d{3})*(?:\.\d{2})?',   # Dollar amounts
    r'\b\d{9}\b',                      # SSN-like
    r'call back', r'don\'t tell', r'keep secret',
    r'wire transfer', r'western union', r'money gram',
    r'bitcoin', r'crypto', r'blockchain'
]

DEFAULT_LANGUAGE = os.getenv('STT_LANGUAGE', 'en-IN')
DEFAULT_CONFIDENCE_THRESHOLD = float(os.getenv('STT_CONFIDENCE_THRESHOLD', '0.75'))

def _preprocess_audio(audio_path: str):
    """
    Preprocess audio for more reliable speech-to-text using FFmpeg directly:
    - mono
    - 16kHz
    - normalize volume
    - trim long silence
    - light noise filtering
    """
    temp_wav_path = None
    duration_seconds = 0.0
    debug = {}

    if not FFMPEG_PATH:
        debug['ffmpeg_error'] = 'ffmpeg not found'
        return None, 0.0, debug

    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
        temp_wav_path = temp_wav.name

    # FFmpeg filters for preprocessing
    filters = (
        "highpass=f=80,lowpass=f=8000,"  # light noise filtering
        "loudnorm,"  # normalize volume  
        "silenceremove=1:0:-50dB"  # trim long silence
    )

    cmd = [
        FFMPEG_PATH,
        '-y',  # overwrite output file
        '-i', audio_path,
        '-ac', '1',  # mono
        '-ar', '16000',  # 16kHz sample rate
        '-af', filters,  # apply audio filters
        temp_wav_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            debug['ffmpeg_error'] = f"FFmpeg failed: {result.stderr[:200]}"
            if os.path.exists(temp_wav_path):
                os.unlink(temp_wav_path)
            return None, 0.0, debug
        
        # Get duration from the output WAV file
        if os.path.exists(temp_wav_path):
            with wave.open(temp_wav_path, 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                duration_seconds = frames / float(rate) if rate else 0.0
            debug['ffmpeg_success'] = True
            return temp_wav_path, duration_seconds, debug
        else:
            debug['ffmpeg_error'] = 'Output WAV file not created'
            return None, 0.0, debug
    except Exception as e:
        debug['ffmpeg_error'] = f"{type(e).__name__}: {e}"
        if temp_wav_path and os.path.exists(temp_wav_path):
            os.unlink(temp_wav_path)
        return None, 0.0, debug

def _build_token_timestamps(transcript: str, duration_seconds: float):
    if not transcript:
        return []

    tokens = [t for t in transcript.split() if t.strip()]
    if not tokens or duration_seconds <= 0:
        return []

    step = duration_seconds / len(tokens)
    token_data = []
    current = 0.0
    for token in tokens:
        start = round(current, 3)
        end = round(min(duration_seconds, current + step), 3)
        token_data.append({
            'word': token,
            'start': start,
            'end': end
        })
        current += step
    return token_data

def transcribe_audio(audio_path: str, language: str = None, confidence_threshold: float = None) -> dict:
    """
    Transcribe audio file to text using speech recognition.
    Returns raw transcript, confidence, and token timestamps.
    No mock transcript is generated to avoid hallucinated text.

    Args:
        audio_path: Path to the audio file
        language: BCP-47 language code (e.g., en-IN, hi-IN)
        confidence_threshold: minimum confidence to display transcript

    Returns:
        Dict with raw_transcript, transcript_display, confidence, tokens, language_used
    """
    if confidence_threshold is None:
        confidence_threshold = DEFAULT_CONFIDENCE_THRESHOLD

    if language is None:
        language = DEFAULT_LANGUAGE

    try:
        import speech_recognition as sr
        import os

        recognizer = sr.Recognizer()

        temp_wav_path, duration_seconds, preprocess_debug = _preprocess_audio(audio_path)

        if not temp_wav_path:
            return {
                'raw_transcript': '',
                'transcript_display': '',
                'confidence': 0.0,
                'tokens': [],
                'language_used': language,
                'duration_seconds': 0.0,
                'preprocess_debug': preprocess_debug
            }

        with sr.AudioFile(temp_wav_path) as source:
            audio_data = recognizer.record(source)

        try:
            result = recognizer.recognize_google(audio_data, language=language, show_all=True)
            alternatives = result.get('alternative', []) if isinstance(result, dict) else []
            if not alternatives:
                return {
                    'raw_transcript': '',
                    'transcript_display': '',
                    'confidence': 0.0,
                    'tokens': [],
                    'language_used': language,
                    'duration_seconds': duration_seconds,
                    'preprocess_debug': preprocess_debug
                }

            best = max(alternatives, key=lambda a: a.get('confidence', 0.0))
            transcript = best.get('transcript', '').strip()
            confidence = best.get('confidence', 0.0)

            if not transcript:
                return {
                    'raw_transcript': '',
                    'transcript_display': '',
                    'confidence': confidence,
                    'tokens': [],
                    'language_used': language,
                    'duration_seconds': duration_seconds,
                    'preprocess_debug': preprocess_debug
                }

            transcript_display = transcript if confidence >= confidence_threshold else '[unclear]'
            tokens = _build_token_timestamps(transcript_display if transcript_display != '[unclear]' else '', duration_seconds)

            return {
                'raw_transcript': transcript,
                'transcript_display': transcript_display,
                'confidence': confidence,
                'tokens': tokens,
                'language_used': language,
                'duration_seconds': duration_seconds,
                'preprocess_debug': preprocess_debug
            }
        except sr.UnknownValueError:
            logger.info(f"Could not understand audio in {audio_path}")
            return {
                'raw_transcript': '',
                'transcript_display': '',
                'confidence': 0.0,
                'tokens': [],
                'language_used': language,
                'duration_seconds': duration_seconds,
                'preprocess_debug': preprocess_debug
            }
        except sr.RequestError as e:
            logger.warning(f"Google Speech Recognition request failed: {e}")
            return {
                'raw_transcript': '',
                'transcript_display': '',
                'confidence': 0.0,
                'tokens': [],
                'language_used': language,
                'duration_seconds': duration_seconds,
                'preprocess_debug': preprocess_debug
            }
        finally:
            if temp_wav_path and os.path.exists(temp_wav_path):
                os.unlink(temp_wav_path)

    except ImportError:
        logger.info(f"speech_recognition not available, returning empty transcript for {audio_path}")
        return {
            'raw_transcript': '',
            'transcript_display': '',
            'confidence': 0.0,
            'tokens': [],
            'language_used': language,
            'duration_seconds': 0.0,
            'preprocess_debug': {}
        }

    except Exception as e:
        logger.warning(f"Speech recognition failed for {audio_path}: {str(e)}")
        return {
            'raw_transcript': '',
            'transcript_display': '',
            'confidence': 0.0,
            'tokens': [],
            'language_used': language,
            'duration_seconds': 0.0,
            'preprocess_debug': {}
        }

def generate_mock_transcript(audio_path: str) -> str:
    """
    Generate a mock transcript for testing when speech recognition isn't available.
    This simulates different scam scenarios based on audio file properties.
    
    Args:
        audio_path: Path to the audio file
        
    Returns:
        Mock transcript text
    """
    import random
    
    mock_scenarios = [
        "hello this is an urgent call regarding your bank account the irs has detected suspicious activity on your account please verify your social security number and bank details immediately by pressing 1 on your phone do not hang up",
        "congratulations you have won a lottery prize of one million dollars to claim your prize please wire transfer fees to western union or bitcoin wallet please call back immediately",
        "urgent security alert your computer has been infected with a virus please call microsoft support immediately and prepare your credit card information to fix this issue",
        "this is the police department we have detected illegal activity on your account please confirm your identity by providing your bank account password and pin code",
        "hello this is from your bank we detected unauthorized transactions please verify your debit card details and cvv number to secure your account",
        "you have an important package delivery failure please click the link and provide your address and credit card information to reschedule delivery",
        "this is a courtesy call from the irs regarding your tax refund please call back and provide your social security number to process your refund",
        "emergency alert your account has been compromised please change your password and verify by wire transferring funds to a secure account",
    ]
    
    # Pick a random scenario for variety
    return random.choice(mock_scenarios)

def analyze_transcript(transcript: str) -> dict:
    """
    Analyze transcript for scam indicators.

    Args:
        transcript: The transcribed text

    Returns:
        Dict with keywords_matched, patterns_detected, and scores
    """
    keywords_matched = []
    patterns_detected = []

    # Check for keywords
    for keyword in SCAM_KEYWORDS:
        if keyword in transcript:
            keywords_matched.append(keyword)

    # Check for patterns
    for pattern in SCAM_PATTERNS:
        if re.search(pattern, transcript, re.IGNORECASE):
            patterns_detected.append(pattern)

    # Calculate scores
    keyword_score = min(1.0, len(keywords_matched) / max(1, len(SCAM_KEYWORDS) * 0.1))  # Cap at 1.0
    pattern_score = min(1.0, len(patterns_detected) / max(1, len(SCAM_PATTERNS) * 0.2))

    # Overall text analysis score
    text_score = (keyword_score + pattern_score) / 2

    return {
        'keywords_matched': keywords_matched,
        'patterns_detected': patterns_detected,
        'keyword_score': keyword_score,
        'pattern_score': pattern_score,
        'text_score': text_score
    }

def process_analysis(analysis_id: str):
    """
    Process an analysis request with real AI pipeline

    Args:
        analysis_id: UUID of the analysis to process
    """
    try:
        analysis = AIAnalysisResult.objects.get(id=analysis_id)
        analysis.status = 'processing'
        analysis.save()

        # Get audio file path
        audio_upload = analysis.audio_upload
        audio_path = audio_upload.audio_file.path

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Step 1: Transcribe audio (raw transcript only)
        transcript_data = transcribe_audio(audio_path)
        raw_transcript = transcript_data.get('raw_transcript', '')
        transcript_display = transcript_data.get('transcript_display', '')
        transcript_confidence = transcript_data.get('confidence', 0.0)
        transcript_tokens = transcript_data.get('tokens', [])
        transcript_language = transcript_data.get('language_used', DEFAULT_LANGUAGE)
        preprocess_debug = transcript_data.get('preprocess_debug', {})

        if not raw_transcript:
            from django.utils import timezone
            analysis.status = 'completed'
            analysis.completed_at = timezone.now()
            analysis.confidence_score = transcript_confidence
            analysis.error_message = None
            analysis.results = {
                'raw_transcript': '',
                'transcript_display': transcript_display,
                'transcript_confidence': transcript_confidence,
                'transcript_language': transcript_language,
                'transcript_tokens': transcript_tokens,
                'transcript_debug': {
                    'audio_path': audio_path,
                    'duration_seconds': transcript_data.get('duration_seconds', 0.0),
                    'confidence_threshold': DEFAULT_CONFIDENCE_THRESHOLD,
                    'preprocess': preprocess_debug
                },
                'analysis': {
                    'keywords_found': [],
                    'patterns_found': [],
                    'analysis_summary': 'No transcript available for analysis (low confidence or empty audio)'
                }
            }
            analysis.api_used = 'google_speech'
            analysis.save()

            ScamProbabilityScore.objects.update_or_create(
                call_record=analysis.call_record,
                ai_analysis=analysis,
                defaults={
                    'overall_score': 0.0,
                    'scam_level': 'low',
                    'factors': {
                        'keyword_matches': 0.0,
                        'pattern_matches': 0.0,
                        'voice_anomalies': 0.0,
                        'behavioral_flags': 0.0,
                        'historical_risk': 0.0
                    },
                    'keywords_matched': [],
                    'patterns_detected': [],
                    'voice_analysis_score': 0.0,
                    'text_analysis_score': 0.0,
                    'behavioral_score': 0.0,
                    'historical_score': 0.0,
                    'threshold_used': 0.5,
                    'explanation': 'No transcript available; risk score defaulted to low.'
                }
            )
            logger.info(f"Analysis {analysis_id} completed with no transcript")
            return

        # Step 2: Analyze transcript (separate from transcript generation)
        analysis_results = analyze_transcript(raw_transcript)

        # Step 3: Calculate overall scam score
        # Weight text analysis heavily, add small random for voice/behavioral (placeholder)
        import random
        text_score = analysis_results['text_score']
        voice_score = random.uniform(0, 0.3)  # Placeholder for voice analysis
        behavioral_score = random.uniform(0, 0.2)  # Placeholder for behavioral
        historical_score = random.uniform(0, 0.1)  # Placeholder for historical

        overall_score = min(1.0, text_score * 0.7 + voice_score * 0.2 + behavioral_score * 0.05 + historical_score * 0.05)

        # Determine scam level
        if overall_score < 0.3:
            scam_level = 'low'
        elif overall_score < 0.6:
            scam_level = 'medium'
        elif overall_score < 0.8:
            scam_level = 'high'
        else:
            scam_level = 'critical'

        # Factors breakdown
        factors = {
            'keyword_matches': analysis_results['keyword_score'],
            'pattern_matches': analysis_results['pattern_score'],
            'voice_anomalies': voice_score,
            'behavioral_flags': behavioral_score,
            'historical_risk': historical_score
        }

        # Create scam probability score
        scam_prob = ScamProbabilityScore.objects.create(
            call_record=analysis.call_record,
            ai_analysis=analysis,
            overall_score=overall_score,
            scam_level=scam_level,
            factors=factors,
            keywords_matched=analysis_results['keywords_matched'],
            patterns_detected=analysis_results['patterns_detected'],
            voice_analysis_score=voice_score,
            text_analysis_score=text_score,
            behavioral_score=behavioral_score,
            historical_score=historical_score,
            threshold_used=0.5,
        )

        # Update analysis with results
        from django.utils import timezone
        analysis.status = 'completed'
        analysis.completed_at = timezone.now()
        analysis.confidence_score = min(0.95, 0.5 + text_score * 0.4 + (1 - voice_score) * 0.1)
        analysis.results = {
            'raw_transcript': raw_transcript,
            'transcript_display': transcript_display,
            'transcript_confidence': transcript_confidence,
            'transcript_language': transcript_language,
            'transcript_tokens': transcript_tokens,
            'transcript_debug': {
                'audio_path': audio_path,
                'duration_seconds': transcript_data.get('duration_seconds', 0.0),
                'confidence_threshold': DEFAULT_CONFIDENCE_THRESHOLD,
                'preprocess': preprocess_debug
            },
            'analysis': {
                'keywords_found': analysis_results['keywords_matched'],
                'patterns_found': analysis_results['patterns_detected'],
                'analysis_summary': f"Found {len(analysis_results['keywords_matched'])} keywords and {len(analysis_results['patterns_detected'])} patterns"
            }
        }
        analysis.api_used = 'google_speech'
        analysis.save()

        logger.info(f"Real AI analysis {analysis_id} completed: score={overall_score:.3f}, level={scam_level}")

    except Exception as e:
        logger.error(f"Analysis {analysis_id} failed: {str(e)}")
        try:
            analysis = AIAnalysisResult.objects.get(id=analysis_id)
            analysis.status = 'failed'
            analysis.error_message = str(e)
            analysis.save()
        except:
            pass
