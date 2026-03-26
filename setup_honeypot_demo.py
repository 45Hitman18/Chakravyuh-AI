"""
Script to create test users and demonstrate honeypot functionality
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chakravyuh.settings')
django.setup()

from django.contrib.auth import get_user_model
from honeypot.models import HoneypotSession, ScammerProfile, HoneypotInteraction
from django.utils import timezone
from datetime import timedelta
import random

User = get_user_model()

def create_demo_users():
    """Create demo users for testing"""
    print("\n" + "=" * 60)
    print("Creating Demo Users")
    print("=" * 60)
    
    # Create law enforcement user
    le_user, created = User.objects.get_or_create(
        username='honeypot_admin',
        defaults={
            'email': 'honeypot_admin@example.com',
            'role': 'law_enforcement',
            'first_name': 'Honeypot',
            'last_name': 'Admin'
        }
    )
    if created:
        le_user.set_password('admin123')
        le_user.save()
        print(f"✓ Created Law Enforcement user: {le_user.username}")
    else:
        print(f"ℹ Law Enforcement user already exists: {le_user.username}")
    
    # Create regular user
    regular_user, created = User.objects.get_or_create(
        username='honeypot_user',
        defaults={
            'email': 'honeypot_user@example.com',
            'role': 'user',
            'first_name': 'Regular',
            'last_name': 'User'
        }
    )
    if created:
        regular_user.set_password('user123')
        regular_user.save()
        print(f"✓ Created Regular user: {regular_user.username}")
    else:
        print(f"ℹ Regular user already exists: {regular_user.username}")
    
    print("\nDemo Login Credentials:")
    print("-" * 60)
    print("Law Enforcement Account:")
    print(f"  Username: honeypot_admin")
    print(f"  Password: admin123")
    print(f"  Access: Full system access with analytics")
    print()
    print("Regular User Account:")
    print(f"  Username: honeypot_user")
    print(f"  Password: user123")
    print(f"  Access: Personal honeypot management")
    print("-" * 60)
    
    return le_user, regular_user

def create_demo_sessions(le_user, regular_user):
    """Create demo honeypot sessions"""
    print("\n" + "=" * 60)
    print("Creating Demo Honeypot Sessions")
    print("=" * 60)
    
    sessions_data = [
        {
            'name': 'Tech Support Scam Trap',
            'phone': '+1-800-HONEY-01',
            'desc': 'Simulating an elderly person with computer problems',
            'user': le_user,
            'personality': {
                'name': 'Dorothy Williams',
                'age': 72,
                'occupation': 'Retired Nurse',
                'traits': ['cautious', 'concerned', 'technologically_challenged']
            }
        },
        {
            'name': 'Bank Fraud Monitor',
            'phone': '+1-800-HONEY-02',
            'desc': 'Monitoring bank account verification scams',
            'user': le_user,
            'personality': {
                'name': 'Robert Chen',
                'age': 65,
                'occupation': 'Retired Accountant',
                'traits': ['careful', 'suspicious', 'detail_oriented']
            }
        },
        {
            'name': 'Lottery Scam Detector',
            'phone': '+1-800-HONEY-03',
            'desc': 'Catching lottery and prize scams',
            'user': regular_user,
            'personality': {
                'name': 'Mary Johnson',
                'age': 68,
                'occupation': 'Retired Teacher',
                'traits': ['friendly', 'trusting', 'hopeful']
            }
        }
    ]
    
    created_sessions = []
    for data in sessions_data:
        session, created = HoneypotSession.objects.get_or_create(
            phone_number=data['phone'],
            defaults={
                'session_name': data['name'],
                'description': data['desc'],
                'status': 'active',
                'created_by': data['user'],
                'configuration': {'personality': data['personality']},
                'total_calls_received': random.randint(5, 20),
                'suspicious_calls_count': random.randint(2, 10)
            }
        )
        if created:
            print(f"✓ Created session: {session.session_name}")
            created_sessions.append(session)
        else:
            print(f"ℹ Session already exists: {session.session_name}")
            created_sessions.append(session)
    
    return created_sessions

def create_demo_scammer_profiles(le_user):
    """Create demo scammer profiles"""
    print("\n" + "=" * 60)
    print("Creating Demo Scammer Profiles")
    print("=" * 60)
    
    scammers_data = [
        {
            'phone': '+91-98765-43210',
            'name': 'Unknown Scammer A',
            'scam_types': ['tech_support', 'investment'],
            'risk_score': 0.85,
            'location': {'state': 'Maharashtra', 'lat': 19.0760, 'lng': 72.8777}
        },
        {
            'phone': '+91-87654-32109',
            'name': 'Unknown Scammer B',
            'scam_types': ['bank_account', 'government_impersonation'],
            'risk_score': 0.72,
            'location': {'state': 'Delhi', 'lat': 28.7041, 'lng': 77.1025}
        },
        {
            'phone': '+1-555-SCAM-01',
            'name': 'Unknown Scammer C',
            'scam_types': ['lottery_winning', 'package_delivery'],
            'risk_score': 0.68,
            'location': {'state': 'Karnataka', 'lat': 12.9716, 'lng': 77.5946}
        }
    ]
    
    created_profiles = []
    for data in scammers_data:
        profile, created = ScammerProfile.objects.get_or_create(
            phone_number=data['phone'],
            defaults={
                'name': data['name'],
                'scam_types': data['scam_types'],
                'risk_score': data['risk_score'],
                'location_data': data['location'],
                'total_calls_made': random.randint(10, 50),
                'successful_scams': random.randint(2, 10),
                'reported_count': random.randint(1, 5),
                'status': 'active',
                'created_by': le_user,
                'last_seen': timezone.now() - timedelta(hours=random.randint(1, 48))
            }
        )
        if created:
            print(f"✓ Created scammer profile: {profile.phone_number} (Risk: {profile.risk_score})")
            created_profiles.append(profile)
        else:
            print(f"ℹ Scammer profile already exists: {profile.phone_number}")
            created_profiles.append(profile)
    
    return created_profiles

def create_demo_interactions(sessions, profiles):
    """Create demo interactions"""
    print("\n" + "=" * 60)
    print("Creating Demo Interactions")
    print("=" * 60)
    
    for i, (session, profile) in enumerate(zip(sessions[:2], profiles[:2])):
        interaction, created = HoneypotInteraction.objects.get_or_create(
            honeypot_session=session,
            scammer_number=profile.phone_number,
            defaults={
                'scammer_profile': profile,
                'status': 'completed',
                'start_time': timezone.now() - timedelta(hours=random.randint(2, 48)),
                'end_time': timezone.now() - timedelta(hours=random.randint(1, 24)),
                'duration': timedelta(minutes=random.randint(5, 30)),
                'scam_type_identified': profile.scam_types[0] if profile.scam_types else 'generic',
                'success_rating': random.uniform(0.6, 0.9),
                'turn_count': random.randint(10, 30),
                'conversation_transcript': [
                    {'timestamp': timezone.now().isoformat(), 'sender': 'scammer', 'message': 'Hello, this is Microsoft technical support...'},
                    {'timestamp': timezone.now().isoformat(), 'sender': 'agent', 'message': 'Oh, thank you for calling! I\'ve been having trouble with my computer.'},
                    {'timestamp': timezone.now().isoformat(), 'sender': 'scammer', 'message': 'Yes, we detected viruses on your computer. We need to fix it immediately.'},
                    {'timestamp': timezone.now().isoformat(), 'sender': 'agent', 'message': 'Oh my goodness! What should I do?'}
                ],
                'extracted_information': {
                    'phone_numbers': [profile.phone_number],
                    'urgency_indicators': ['immediately', 'urgent'],
                    'pressure_tactics': ['viruses detected', 'need to fix now']
                }
            }
        )
        if created:
            print(f"✓ Created interaction: {profile.phone_number} -> {session.session_name}")
        else:
            print(f"ℹ Interaction already exists")

def main():
    print("\n" + "=" * 60)
    print("HONEYPOT DEMO SETUP")
    print("=" * 60)
    
    # Create users
    le_user, regular_user = create_demo_users()
    
    # Create sessions
    sessions = create_demo_sessions(le_user, regular_user)
    
    # Create scammer profiles
    profiles = create_demo_scammer_profiles(le_user)
    
    # Create interactions
    create_demo_interactions(sessions, profiles)
    
    print("\n" + "=" * 60)
    print("✓ DEMO SETUP COMPLETE!")
    print("=" * 60)
    print("\nYou can now access the honeypot system at:")
    print("  http://127.0.0.1:8000/honeypot/")
    print("\nLogin with either account to explore the features:")
    print("  - Law Enforcement: honeypot_admin / admin123")
    print("  - Regular User: honeypot_user / user123")
    print("=" * 60)

if __name__ == '__main__':
    main()
