"""
AI Honeypot Agent System

This module implements an intelligent AI agent that simulates scam victims
to engage scammers, extract information, and safely terminate conversations.
"""

import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from django.utils import timezone
from django.conf import settings
from .models import HoneypotSession, ScammerProfile, HoneypotInteraction

logger = logging.getLogger(__name__)

class ConversationState(Enum):
    """States for the honeypot conversation"""
    INITIAL_GREETING = "initial_greeting"
    BUILDING_TRUST = "building_trust"
    INFORMATION_GATHERING = "information_gathering"
    RESISTANCE_BUILDING = "resistance_building"
    EXTRACTION_PHASE = "extraction_phase"
    TERMINATION_PHASE = "termination_phase"
    COMPLETED = "completed"

class ScamType(Enum):
    """Types of scams the agent can handle"""
    TECH_SUPPORT = "tech_support"
    LOTTERY_WINNING = "lottery_winning"
    BANK_ACCOUNT = "bank_account"
    INVESTMENT = "investment"
    ROMANCE = "romance"
    GOVERNMENT_IMPERSONATION = "government_impersonation"
    PACKAGE_DELIVERY = "package_delivery"
    INSURANCE_CLAIM = "insurance_claim"
    GENERIC = "generic"

class HoneypotAIAgent:
    """
    Intelligent AI agent for honeypot operations
    """

    def __init__(self, session: HoneypotSession):
        self.session = session
        self.state = ConversationState.INITIAL_GREETING
        self.scam_type = ScamType.GENERIC
        self.conversation_history = []
        self.extracted_info = {
            'phone_numbers': [],
            'payment_details': [],
            'scam_scripts': [],
            'personal_info': [],
            'threats': [],
            'urgency_indicators': [],
            'intents': [],
            'keywords': [],
            'pressure_tactics': []
        }
        self.trust_level = 0.0
        self.resistance_level = 0.0
        self.max_conversation_length = 50  # Maximum turns before termination
        self.turn_count = 0

        # Load personality configuration
        self.personality = self._load_personality()

    def _load_personality(self) -> Dict:
        """Load personality configuration for the honeypot"""
        return {
            'name': 'Sarah Johnson',
            'age': 68,
            'occupation': 'Retired Teacher',
            'location': 'Springfield, IL',
            'personality_traits': ['cautious', 'friendly', 'concerned', 'traditional'],
            'vulnerabilities': ['technologically_challenged', 'lonely', 'trusting_of_authority'],
            'resistance_triggers': ['money_requests', 'personal_info_requests', 'urgent_demands']
        }

    def process_incoming_message(self, message: str, call_context: Dict = None) -> Tuple[str, bool]:
        """
        Process an incoming message from the scammer and generate a response

        Args:
            message: The scammer's message
            call_context: Additional context about the call

        Returns:
            Tuple of (response_text, should_terminate)
        """
        self.turn_count += 1
        self.conversation_history.append({
            'timestamp': timezone.now(),
            'direction': 'incoming',
            'message': message,
            'context': call_context or {}
        })

        # Analyze the incoming message
        analysis = self._analyze_message(message)

        # Update state based on analysis
        self._update_conversation_state(analysis)

        # Extract information
        self._extract_information(message, analysis)

        # Check termination conditions
        if self._should_terminate():
            response = self._generate_termination_response()
            self.state = ConversationState.COMPLETED
            return response, True

        # Generate response based on current state
        response = self._generate_response(analysis)

        self.conversation_history.append({
            'timestamp': timezone.now(),
            'direction': 'outgoing',
            'message': response,
            'state': self.state.value
        })

        return response, False

    def _analyze_message(self, message: str) -> Dict:
        """Analyze the incoming message for intent, sentiment, and key elements"""
        analysis = {
            'sentiment': self._analyze_sentiment(message),
            'intent': self._classify_intent(message),
            'urgency_level': self._detect_urgency(message),
            'scam_indicators': self._detect_scam_indicators(message),
            'information_requests': self._detect_information_requests(message),
            'threats': self._detect_threats(message),
            'keywords': self._extract_keywords(message)
        }

        # Update scam type classification
        self._update_scam_type_classification(analysis)

        return analysis

    def _analyze_sentiment(self, message: str) -> str:
        """Simple sentiment analysis"""
        positive_words = ['help', 'assist', 'support', 'good', 'great', 'wonderful', 'pleased']
        negative_words = ['urgent', 'problem', 'issue', 'trouble', 'worried', 'concerned', 'scared']
        threat_words = ['arrest', 'jail', 'police', 'court', 'legal', 'lawsuit']

        message_lower = message.lower()

        if any(word in message_lower for word in threat_words):
            return 'threatening'
        elif any(word in message_lower for word in negative_words):
            return 'concerned'
        elif any(word in message_lower for word in positive_words):
            return 'helpful'
        else:
            return 'neutral'

    def _classify_intent(self, message: str) -> str:
        """Classify the scammer's intent"""
        message_lower = message.lower()

        if re.search(r'\b(bank|account|transfer|wire|money|payment)\b', message_lower):
            return 'financial_request'
        elif re.search(r'\b(prize|lottery|winner|won|jackpot)\b', message_lower):
            return 'prize_notification'
        elif re.search(r'\b(tech|computer|virus|hack|support|fix)\b', message_lower):
            return 'tech_support'
        elif re.search(r'\b(police|irs|fbi|government|arrest|jail)\b', message_lower):
            return 'authority_impersonation'
        elif re.search(r'\b(information|details|name|address|ssn|social)\b', message_lower):
            return 'information_gathering'
        elif re.search(r'\b(urgent|immediately|now|quick|fast|rush)\b', message_lower):
            return 'creating_urgency'
        else:
            return 'general_conversation'

    def _detect_urgency(self, message: str) -> float:
        """Detect urgency level (0-1)"""
        urgency_indicators = [
            'urgent', 'immediately', 'right now', 'asap', 'emergency',
            'quickly', 'fast', 'rush', 'deadline', 'time sensitive',
            'important', 'critical', 'serious', 'act now'
        ]

        message_lower = message.lower()
        count = sum(1 for word in urgency_indicators if word in message_lower)

        return min(count / 3, 1.0)  # Normalize

    def _detect_scam_indicators(self, message: str) -> List[str]:
        """Detect common scam indicators"""
        indicators = []

        # Financial requests
        if re.search(r'\b(send|transfer|wire|pay|money|fee|charge)\b', message.lower()):
            indicators.append('financial_request')

        # Authority impersonation
        if re.search(r'\b(police|irs|fbi|government|agent|officer)\b', message.lower()):
            indicators.append('authority_impersonation')

        # Prize/lottery scams
        if re.search(r'\b(prize|lottery|winner|won|jackpot|inheritance)\b', message.lower()):
            indicators.append('prize_scam')

        # Tech support scams
        if re.search(r'\b(virus|hack|infection|support|tech|fix|remote)\b', message.lower()):
            indicators.append('tech_support_scam')

        # Urgency creation
        if self._detect_urgency(message) > 0.5:
            indicators.append('high_urgency')

        return indicators

    def _detect_information_requests(self, message: str) -> List[str]:
        """Detect requests for personal information"""
        requests = []

        if re.search(r'\b(name|full name|first name|last name)\b', message.lower()):
            requests.append('name')

        if re.search(r'\b(address|home address|location|where do you live)\b', message.lower()):
            requests.append('address')

        if re.search(r'\b(phone|telephone|number|contact)\b', message.lower()):
            requests.append('phone')

        if re.search(r'\b(email|e-mail|mail)\b', message.lower()):
            requests.append('email')

        if re.search(r'\b(bank|account|account number|routing|checking|savings)\b', message.lower()):
            requests.append('bank_info')

        if re.search(r'\b(ssn|social security|social|security number)\b', message.lower()):
            requests.append('ssn')

        return requests

    def _detect_threats(self, message: str) -> List[str]:
        """Detect threats or coercive language"""
        threats = []

        threat_patterns = [
            r'\b(arrest|jail|prison|court|lawsuit|legal action)\b',
            r'\b(warrant|subpoena|investigation)\b',
            r'\b(confiscate|seize|take away|lose)\b',
            r'\b(danger|risk|harm|hurt)\b',
            r'\b(must|have to|required|mandatory)\b'
        ]

        message_lower = message.lower()
        for pattern in threat_patterns:
            if re.search(pattern, message_lower):
                threats.append(re.findall(pattern, message_lower)[0])

        return threats

    def _extract_keywords(self, message: str) -> List[str]:
        """Extract important keywords"""
        # Simple keyword extraction - could be enhanced with NLP
        words = re.findall(r'\b\w+\b', message.lower())
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}

        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        return list(set(keywords))[:10]  # Return unique keywords, max 10

    def _update_scam_type_classification(self, analysis: Dict):
        """Update the scam type based on message analysis"""
        indicators = analysis.get('scam_indicators', [])

        if 'tech_support_scam' in indicators:
            self.scam_type = ScamType.TECH_SUPPORT
        elif 'prize_scam' in indicators:
            self.scam_type = ScamType.LOTTERY_WINNING
        elif 'authority_impersonation' in indicators:
            self.scam_type = ScamType.GOVERNMENT_IMPERSONATION
        elif 'financial_request' in indicators:
            self.scam_type = ScamType.BANK_ACCOUNT

    def _update_conversation_state(self, analysis: Dict):
        """Update the conversation state based on analysis"""
        current_intent = analysis.get('intent')
        urgency = analysis.get('urgency_level', 0)
        info_requests = analysis.get('information_requests', [])
        threats = analysis.get('threats', [])

        # State transition logic
        if self.state == ConversationState.INITIAL_GREETING:
            if current_intent in ['financial_request', 'information_gathering']:
                self.state = ConversationState.INFORMATION_GATHERING
            else:
                self.state = ConversationState.BUILDING_TRUST

        elif self.state == ConversationState.BUILDING_TRUST:
            if info_requests or current_intent == 'information_gathering':
                self.state = ConversationState.INFORMATION_GATHERING
            elif urgency > 0.7 or threats:
                self.state = ConversationState.RESISTANCE_BUILDING

        elif self.state == ConversationState.INFORMATION_GATHERING:
            if urgency > 0.8 or len(threats) > 2:
                self.state = ConversationState.EXTRACTION_PHASE
            elif self.resistance_level > 0.6:
                self.state = ConversationState.RESISTANCE_BUILDING

        elif self.state == ConversationState.RESISTANCE_BUILDING:
            if self.turn_count > self.max_conversation_length * 0.7:
                self.state = ConversationState.TERMINATION_PHASE

        elif self.state == ConversationState.EXTRACTION_PHASE:
            if self.turn_count > self.max_conversation_length * 0.8:
                self.state = ConversationState.TERMINATION_PHASE

    def _extract_information(self, message: str, analysis: Dict):
        """Extract and store information from the message"""
        # Extract phone numbers
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        phones = re.findall(phone_pattern, message)
        self.extracted_info['phone_numbers'].extend(phones)

        # Extract payment details
        payment_keywords = ['bitcoin', 'btc', 'paypal', 'venmo', 'cash app', 'zelle', 'wire transfer']
        if any(keyword in message.lower() for keyword in payment_keywords):
            self.extracted_info['payment_details'].append(message.strip())

        # Store scam scripts/snippets
        if len(message.strip()) > 20:  # Only store substantial messages
            self.extracted_info['scam_scripts'].append({
                'message': message.strip(),
                'turn': self.turn_count,
                'intent': analysis.get('intent'),
                'timestamp': timezone.now()
            })

        # Extract personal info requests
        info_requests = analysis.get('information_requests', [])
        self.extracted_info['personal_info'].extend(info_requests)

        # Store intents
        intent = analysis.get('intent')
        if intent and intent not in self.extracted_info['intents']:
            self.extracted_info['intents'].append(intent)

        # Store keywords
        for keyword in analysis.get('keywords', []):
            if keyword not in self.extracted_info['keywords']:
                self.extracted_info['keywords'].append(keyword)

        # Store threats
        threats = analysis.get('threats', [])
        if threats:
            self.extracted_info['threats'].append({
                'threats': threats,
                'message': message.strip(),
                'turn': self.turn_count
            })

        # Store urgency indicators
        urgency = analysis.get('urgency_level', 0)
        if urgency > 0.5:
            self.extracted_info['urgency_indicators'].append({
                'level': urgency,
                'message': message.strip(),
                'turn': self.turn_count
            })

        # Track pressure tactics
        if urgency > 0.5 or threats:
            tactic = 'urgency' if urgency > 0.5 else 'threats'
            if tactic not in self.extracted_info['pressure_tactics']:
                self.extracted_info['pressure_tactics'].append(tactic)

    def _should_terminate(self) -> bool:
        """Determine if the conversation should be terminated"""
        reasons = []

        # Maximum conversation length
        if self.turn_count >= self.max_conversation_length:
            reasons.append('max_length')

        # High resistance level
        if self.resistance_level > 0.8:
            reasons.append('high_resistance')

        # Successful information extraction
        if len(self.extracted_info['phone_numbers']) >= 3:
            reasons.append('sufficient_info')

        # Direct threats or coercion
        recent_messages = self.conversation_history[-3:]
        for msg in recent_messages:
            if msg['direction'] == 'incoming':
                threats = self._detect_threats(msg['message'])
                if len(threats) >= 2:
                    reasons.append('threats')

        # Scam type identified and pattern established
        if self.scam_type != ScamType.GENERIC and self.turn_count >= 10:
            reasons.append('pattern_established')

        return len(reasons) > 0

    def _generate_response(self, analysis: Dict) -> str:
        """Generate an appropriate response based on current state and analysis"""
        responses = {
            ConversationState.INITIAL_GREETING: self._get_greeting_responses(),
            ConversationState.BUILDING_TRUST: self._get_trust_building_responses(),
            ConversationState.INFORMATION_GATHERING: self._get_info_gathering_responses(),
            ConversationState.RESISTANCE_BUILDING: self._get_resistance_responses(),
            ConversationState.EXTRACTION_PHASE: self._get_extraction_responses(),
            ConversationState.TERMINATION_PHASE: self._get_termination_responses()
        }

        state_responses = responses.get(self.state, self._get_default_responses())

        # Select response based on analysis
        intent = analysis.get('intent')
        urgency = analysis.get('urgency_level', 0)

        # Prioritize responses based on intent and urgency
        if intent == 'financial_request' and urgency > 0.5:
            return self._get_resistance_responses()[0]  # Strong resistance
        elif intent == 'information_gathering':
            return self._get_info_gathering_responses()[0]  # Hesitant cooperation
        elif urgency > 0.7:
            return self._get_resistance_responses()[1]  # Question urgency

        # Random selection from appropriate responses
        import random
        return random.choice(state_responses)

    def _get_greeting_responses(self) -> List[str]:
        """Responses for initial greeting phase"""
        return [
            "Hello? Who is this?",
            "Yes, this is Sarah speaking. May I ask who's calling?",
            "Hello there. How can I help you today?",
            "Yes, speaking. What is this regarding?"
        ]

    def _get_trust_building_responses(self) -> List[str]:
        """Responses for building trust"""
        return [
            "I see. Could you tell me more about this?",
            "That sounds concerning. What should I do?",
            "I'm not sure I understand. Can you explain that again?",
            "Okay, I'm listening. Please continue."
        ]

    def _get_info_gathering_responses(self) -> List[str]:
        """Responses during information gathering phase"""
        return [
            "I'm not sure about giving out that information...",
            "Let me think about this for a moment.",
            "That sounds important. Could you hold on while I get my things?",
            "I need to be careful about this. Can you verify who you are?"
        ]

    def _get_resistance_responses(self) -> List[str]:
        """Responses showing resistance"""
        return [
            "I'm really not comfortable with this. I think I should call someone else.",
            "This seems very urgent. Are you sure this is legitimate?",
            "I don't think I should be doing this over the phone. Let me call you back.",
            "I'm getting confused. Maybe I should speak to my son/daughter about this.",
            "This doesn't sound right to me. I think I'll contact the proper authorities."
        ]

    def _get_extraction_responses(self) -> List[str]:
        """Responses during extraction phase - keep them engaged"""
        return [
            "I need to write this down. Can you repeat that?",
            "Let me make sure I have this correct...",
            "That's a lot of information. Can you go over that again?",
            "I want to make sure I understand. You're saying..."
        ]

    def _get_termination_responses(self) -> List[str]:
        """Responses for terminating the conversation"""
        return [
            "I think I need to go now. Goodbye.",
            "This is too much for me. I'm hanging up.",
            "I don't feel comfortable continuing this conversation.",
            "I need to speak with someone else about this. Goodbye."
        ]

    def _get_default_responses(self) -> List[str]:
        """Default fallback responses"""
        return [
            "I'm not sure what to say.",
            "Can you repeat that?",
            "I need a moment to think about this."
        ]

    def _generate_termination_response(self) -> str:
        """Generate a final termination response"""
        responses = [
            "I think I've heard enough. This conversation is over.",
            "I'm going to hang up now and contact the authorities.",
            "This doesn't feel right. Goodbye.",
            "I don't want to continue this conversation. Farewell.",
            "I've decided this isn't for me. Take care."
        ]

        import random
        return random.choice(responses)

    def get_conversation_summary(self) -> Dict:
        """Get a summary of the conversation and extracted information"""
        return {
            'session_id': str(self.session.id),
            'scam_type': self.scam_type.value,
            'conversation_length': self.turn_count,
            'final_state': self.state.value,
            'extracted_info': self.extracted_info,
            'trust_level': self.trust_level,
            'resistance_level': self.resistance_level,
            'conversation_history': self.conversation_history,
            'termination_reason': self._get_termination_reason()
        }

    def _get_termination_reason(self) -> str:
        """Determine the reason for termination"""
        if self.turn_count >= self.max_conversation_length:
            return 'max_length_reached'
        elif self.resistance_level > 0.8:
            return 'high_resistance'
        elif len(self.extracted_info['phone_numbers']) >= 3:
            return 'sufficient_information'
        elif self.scam_type != ScamType.GENERIC:
            return 'pattern_identified'
        else:
            return 'unknown'

    def save_interaction(self, scammer_number: str, call_record=None):
        """Save the interaction data to the database"""
        try:
            # Create or update scammer profile
            scammer, created = ScammerProfile.objects.get_or_create(
                phone_number=scammer_number,
                defaults={
                    'created_by': self.session.created_by,
                    'scam_types': [self.scam_type.value],
                    'total_calls_made': 1
                }
            )

            if not created:
                # Update existing profile
                if self.scam_type.value not in scammer.scam_types:
                    scammer.scam_types.append(self.scam_type.value)
                scammer.total_calls_made += 1
                scammer.last_seen = timezone.now()
                scammer.save()

            # Build transcript
            transcript = []
            for entry in self.conversation_history:
                direction = entry.get('direction')
                sender = 'scammer' if direction == 'incoming' else 'agent'
                transcript.append({
                    'timestamp': entry.get('timestamp').isoformat() if entry.get('timestamp') else None,
                    'sender': sender,
                    'message': entry.get('message')
                })

            start_time = self.conversation_history[0].get('timestamp') if self.conversation_history else timezone.now()
            end_time = timezone.now()

            # Create interaction record
            interaction = HoneypotInteraction.objects.create(
                honeypot_session=self.session,
                scammer_profile=scammer,
                scammer_number=scammer_number,
                status='completed' if self.state == ConversationState.COMPLETED else 'active',
                end_time=end_time,
                duration=end_time - start_time,
                conversation_transcript=transcript,
                extracted_information=self.extracted_info,
                scam_type_identified=self.scam_type.value,
                success_rating=self._calculate_success_rating(),
                ai_agent_state=self.state.value,
                turn_count=self.turn_count
            )

            # Update session statistics
            self.session.total_calls_received += 1
            if self.scam_type != ScamType.GENERIC:
                self.session.suspicious_calls_count += 1
            self.session.save()

            # Optional auto-report creation
            auto_report = self.session.configuration.get('auto_report', True)
            if auto_report:
                try:
                    from reports.models import Report
                    from django.utils import timezone as dj_timezone

                    priority = 'medium'
                    if self.extracted_info.get('threats') or self.extracted_info.get('pressure_tactics'):
                        priority = 'high'

                    Report.objects.create(
                        title=f"Honeypot interaction: {scammer_number}",
                        report_type='honeypot_interaction',
                        status='submitted',
                        description="Honeypot captured scammer interaction with extracted indicators.",
                        incident_date=dj_timezone.now(),
                        scammer_profile=scammer,
                        honeypot_session=self.session,
                        created_by=self.session.created_by,
                        priority=priority,
                        tags=['honeypot', self.scam_type.value],
                        public_summary=f"Indicators: {', '.join(self.extracted_info.get('pressure_tactics', [])) or 'none'}"
                    )
                except Exception as report_error:
                    logger.warning(f"Failed to auto-create report: {report_error}")

            logger.info(f"Honeypot interaction saved for session {self.session.id}")
            return interaction

        except Exception as e:
            logger.error(f"Failed to save honeypot interaction: {str(e)}")
            return None

    def _calculate_success_rating(self) -> float:
        """Calculate success rating for the interaction (0-1)"""
        rating = 0.0

        # Information extraction success
        info_score = min(len(self.extracted_info['phone_numbers']) * 0.2 +
                        len(self.extracted_info['payment_details']) * 0.3 +
                        len(self.extracted_info['scam_scripts']) * 0.1, 0.5)

        # Scam identification success
        scam_score = 0.3 if self.scam_type != ScamType.GENERIC else 0.0

        # Conversation engagement success
        engagement_score = min(self.turn_count / self.max_conversation_length, 0.2)

        rating = info_score + scam_score + engagement_score
        return min(rating, 1.0)
