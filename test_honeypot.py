"""
Test script to verify honeypot functionality
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chakravyuh.settings')
django.setup()

from django.contrib.auth import get_user_model
from honeypot.models import HoneypotSession, ScammerProfile, HoneypotInteraction
from django.utils import timezone

User = get_user_model()

def test_honeypot():
    print("=" * 60)
    print("HONEYPOT SYSTEM TEST")
    print("=" * 60)
    
    # Check if honeypot app is installed
    print("\n1. Checking Honeypot App Installation...")
    try:
        from honeypot import views, models, forms
        print("   ✓ Honeypot app imports successful")
    except Exception as e:
        print(f"   ✗ Error importing honeypot: {e}")
        return False
    
    # Check models
    print("\n2. Checking Honeypot Models...")
    try:
        session_count = HoneypotSession.objects.count()
        profile_count = ScammerProfile.objects.count()
        interaction_count = HoneypotInteraction.objects.count()
        
        print(f"   ✓ HoneypotSession: {session_count} records")
        print(f"   ✓ ScammerProfile: {profile_count} records")
        print(f"   ✓ HoneypotInteraction: {interaction_count} records")
    except Exception as e:
        print(f"   ✗ Error accessing models: {e}")
        return False
    
    # Check if we have test users
    print("\n3. Checking Users...")
    try:
        users = User.objects.all()
        print(f"   ✓ Total users: {users.count()}")
        
        # Check for law enforcement user
        le_users = User.objects.filter(role='law_enforcement')
        if le_users.exists():
            print(f"   ✓ Law enforcement users: {le_users.count()}")
        else:
            print("   ℹ No law enforcement users found")
            
        # Check for regular users
        regular_users = User.objects.filter(role='user')
        if regular_users.exists():
            print(f"   ✓ Regular users: {regular_users.count()}")
        else:
            print("   ℹ No regular users found")
            
    except Exception as e:
        print(f"   ✗ Error checking users: {e}")
        return False
    
    # Test URL patterns
    print("\n4. Testing URL Patterns...")
    try:
        from django.urls import reverse
        
        urls_to_test = [
            'honeypot:honeypot_dashboard',
            'honeypot:honeypot_session_list',
            'honeypot:scammer_profile_list',
            'honeypot:honeypot_reports',
        ]
        
        for url_name in urls_to_test:
            try:
                url = reverse(url_name)
                print(f"   ✓ {url_name}: {url}")
            except Exception as e:
                print(f"   ✗ {url_name}: Error - {e}")
                
    except Exception as e:
        print(f"   ✗ Error testing URLs: {e}")
        return False
    
    # Test creating a test session (if user exists)
    print("\n5. Testing Honeypot Session Creation...")
    try:
        if User.objects.exists():
            user = User.objects.first()
            
            # Check if test session already exists
            test_session = HoneypotSession.objects.filter(
                session_name='Test Session'
            ).first()
            
            if not test_session:
                test_session = HoneypotSession.objects.create(
                    session_name='Test Session',
                    phone_number='+1-800-TEST-001',
                    description='Automated test session',
                    status='active',
                    created_by=user,
                    configuration={
                        'personality': {
                            'name': 'Test Persona',
                            'age': 65,
                        }
                    }
                )
                print(f"   ✓ Created test session: {test_session.id}")
            else:
                print(f"   ✓ Test session already exists: {test_session.id}")
                
        else:
            print("   ℹ No users available - skipping session creation")
            
    except Exception as e:
        print(f"   ✗ Error creating test session: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("✓ HONEYPOT SYSTEM IS WORKING!")
    print("=" * 60)
    print("\nYou can access the honeypot dashboard at:")
    print("  http://127.0.0.1:8000/honeypot/")
    print("\nMake sure you're logged in with an appropriate user account.")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    try:
        success = test_honeypot()
        if not success:
            print("\n⚠ Some tests failed. Please review the errors above.")
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
