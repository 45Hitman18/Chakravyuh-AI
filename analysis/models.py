from django.db import models
from django.conf import settings
import uuid

class AIAnalysisResult(models.Model):
    ANALYSIS_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout'),
    ]

    ANALYSIS_TYPE_CHOICES = [
        ('speech_to_text', 'Speech to Text'),
        ('sentiment_analysis', 'Sentiment Analysis'),
        ('keyword_extraction', 'Keyword Extraction'),
        ('scam_detection', 'Scam Detection'),
        ('voice_biometrics', 'Voice Biometrics'),
        ('language_detection', 'Language Detection'),
        ('comprehensive', 'Comprehensive Analysis'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call_record = models.OneToOneField('calls.CallRecord', on_delete=models.CASCADE, related_name='ai_analysis')
    audio_upload = models.OneToOneField('calls.AudioUpload', on_delete=models.CASCADE, related_name='ai_analysis')
    analysis_type = models.CharField(max_length=20, choices=ANALYSIS_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=ANALYSIS_STATUS_CHOICES, default='pending')
    confidence_score = models.FloatField(null=True, blank=True)  # Overall confidence (0-1)
    processing_time = models.DurationField(null=True, blank=True)
    results = models.JSONField(default=dict)  # AI analysis results
    raw_output = models.TextField(blank=True, null=True)  # Raw AI model output
    error_message = models.TextField(blank=True, null=True)
    model_version = models.CharField(max_length=50, blank=True, null=True)
    api_used = models.CharField(max_length=100, blank=True, null=True)  # Which AI service/API was used
    cost = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)  # API cost if applicable
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='ai_analysis_requests')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'analysis_type', 'created_at']),
            models.Index(fields=['call_record', 'status']),
            models.Index(fields=['confidence_score']),
        ]

    def __str__(self):
        return f"AI Analysis for call {self.call_record.id} - {self.analysis_type} ({self.status})"

    def get_transcript(self):
        """Extract transcript from results if available"""
        return self.results.get('raw_transcript', '')

    def get_keywords(self):
        """Extract keywords from results if available"""
        analysis_results = self.results.get('analysis', {})
        return analysis_results.get('keywords_found', [])

    def get_sentiment(self):
        """Extract sentiment analysis from results if available"""
        analysis_results = self.results.get('analysis', {})
        return analysis_results.get('sentiment', {})

class ScamProbabilityScore(models.Model):
    SCAM_LEVEL_CHOICES = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    call_record = models.OneToOneField('calls.CallRecord', on_delete=models.CASCADE, related_name='scam_probability')
    ai_analysis = models.OneToOneField(AIAnalysisResult, on_delete=models.CASCADE, related_name='scam_probability')
    overall_score = models.FloatField()  # 0-1 probability score
    scam_level = models.CharField(max_length=10, choices=SCAM_LEVEL_CHOICES)
    factors = models.JSONField(default=dict)  # Breakdown of scoring factors
    keywords_matched = models.JSONField(default=list)  # Scam-related keywords found
    patterns_detected = models.JSONField(default=list)  # Scam patterns identified
    voice_analysis_score = models.FloatField(null=True, blank=True)  # Voice stress/anomaly score
    text_analysis_score = models.FloatField(null=True, blank=True)  # Text content analysis score
    behavioral_score = models.FloatField(null=True, blank=True)  # Call behavior analysis score
    historical_score = models.FloatField(null=True, blank=True)  # Based on caller history
    threshold_used = models.FloatField(default=0.5)  # Threshold for classification
    false_positive_probability = models.FloatField(null=True, blank=True)
    explanation = models.TextField(blank=True, null=True)  # Human-readable explanation
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='scam_reviews')
    review_notes = models.TextField(blank=True, null=True)
    is_manually_overridden = models.BooleanField(default=False)
    original_score = models.FloatField(null=True, blank=True)  # Before manual override
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-overall_score', '-created_at']
        indexes = [
            models.Index(fields=['overall_score', 'scam_level']),
            models.Index(fields=['call_record', 'overall_score']),
            models.Index(fields=['scam_level', 'created_at']),
        ]

    def __str__(self):
        return f"Scam Score: {self.overall_score:.3f} ({self.scam_level}) for call {self.call_record.id}"

    def calculate_scam_level(self):
        """Calculate scam level based on overall score"""
        if self.overall_score >= 0.8:
            return 'critical'
        elif self.overall_score >= 0.6:
            return 'high'
        elif self.overall_score >= 0.4:
            return 'medium'
        else:
            return 'low'

    def save(self, *args, **kwargs):
        if not self.scam_level:
            self.scam_level = self.calculate_scam_level()
        super().save(*args, **kwargs)

    def get_top_factors(self, limit=5):
        """Get top contributing factors to the scam score"""
        factors = self.factors.items()
        sorted_factors = sorted(factors, key=lambda x: x[1], reverse=True)
        return sorted_factors[:limit]
