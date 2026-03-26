from django.db import models
from django.conf import settings
import uuid

class HoneypotSession(models.Model):
    SESSION_STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('terminated', 'Terminated'),
        ('timeout', 'Timeout'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_name = models.CharField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=SESSION_STATUS_CHOICES, default='active')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_honeypots')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_honeypots')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_calls_received = models.PositiveIntegerField(default=0)
    suspicious_calls_count = models.PositiveIntegerField(default=0)
    configuration = models.JSONField(default=dict)  # Honeypot settings and rules
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['status', 'phone_number']),
            models.Index(fields=['created_by', 'status']),
        ]

    def __str__(self):
        return f"Honeypot: {self.session_name} ({self.phone_number})"

class ScammerProfile(models.Model):
    PROFILE_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('banned', 'Banned'),
        ('under_investigation', 'Under Investigation'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    aliases = models.JSONField(default=list)  # Alternative names used
    scam_types = models.JSONField(default=list)  # Types of scams associated
    risk_score = models.FloatField(default=0.0)  # Aggregated risk score
    total_calls_made = models.PositiveIntegerField(default=0)
    successful_scams = models.PositiveIntegerField(default=0)
    reported_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=PROFILE_STATUS_CHOICES, default='active')
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    location_data = models.JSONField(default=dict)  # Geographic information
    associated_numbers = models.JSONField(default=list)  # Related phone numbers
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_scammer_profiles')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='updated_scammer_profiles')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-risk_score', '-last_seen']
        indexes = [
            models.Index(fields=['phone_number', 'status']),
            models.Index(fields=['risk_score', 'status']),
            models.Index(fields=['last_seen']),
        ]

    def __str__(self):
        return f"Scammer: {self.phone_number} - Risk: {self.risk_score:.2f}"

    def update_risk_score(self):
        """Calculate and update the risk score based on various factors"""
        base_score = 0.0

        # Factor in successful scams
        if self.total_calls_made > 0:
            success_rate = self.successful_scams / self.total_calls_made
            base_score += success_rate * 0.4

        # Factor in reports
        report_factor = min(self.reported_count / 10, 1.0)  # Cap at 10 reports
        base_score += report_factor * 0.3

        # Factor in scam types (more types = higher risk)
        scam_type_factor = min(len(self.scam_types) / 5, 1.0)  # Cap at 5 types
        base_score += scam_type_factor * 0.3

        self.risk_score = min(base_score, 1.0)  # Cap at 1.0
        self.save(update_fields=['risk_score', 'updated_at'])

class HoneypotInteraction(models.Model):
    INTERACTION_STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('terminated', 'Terminated'),
        ('timeout', 'Timeout'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    honeypot_session = models.ForeignKey(HoneypotSession, on_delete=models.CASCADE, related_name='interactions')
    scammer_profile = models.ForeignKey(ScammerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='interactions')
    scammer_number = models.CharField(max_length=20, db_index=True)
    status = models.CharField(max_length=20, choices=INTERACTION_STATUS_CHOICES, default='active')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    conversation_transcript = models.JSONField(default=list)  # List of message exchanges
    extracted_information = models.JSONField(default=dict)  # Extracted phone numbers, payment details, etc.
    scam_type_identified = models.CharField(max_length=50, null=True, blank=True)
    success_rating = models.FloatField(default=0.0)  # How successful the honeypot was (0-1)
    ai_agent_state = models.CharField(max_length=50, null=True, blank=True)  # Current AI state
    turn_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['honeypot_session', 'status']),
            models.Index(fields=['scammer_number', 'start_time']),
            models.Index(fields=['status', 'start_time']),
        ]

    def __str__(self):
        return f"Interaction: {self.scammer_number} -> {self.honeypot_session.phone_number}"

    def get_conversation_transcript(self):
        """Return formatted conversation transcript"""
        return self.conversation_transcript

    def get_extracted_phone_numbers(self):
        """Return list of extracted phone numbers"""
        return self.extracted_information.get('phone_numbers', [])

    def get_extracted_payment_details(self):
        """Return list of extracted payment details"""
        return self.extracted_information.get('payment_details', [])

    def add_message(self, sender, message, timestamp=None):
        """Add a message to the conversation transcript"""
        if timestamp is None:
            from django.utils import timezone
            timestamp = timezone.now()

        message_entry = {
            'timestamp': timestamp.isoformat(),
            'sender': sender,  # 'scammer' or 'agent'
            'message': message
        }

        self.conversation_transcript.append(message_entry)
        self.turn_count += 1
        self.save(update_fields=['conversation_transcript', 'turn_count', 'updated_at'])

    def update_extracted_info(self, info_type, data):
        """Update extracted information"""
        if info_type not in self.extracted_information:
            self.extracted_information[info_type] = []

        if data not in self.extracted_information[info_type]:
            self.extracted_information[info_type].append(data)
            self.save(update_fields=['extracted_information', 'updated_at'])
