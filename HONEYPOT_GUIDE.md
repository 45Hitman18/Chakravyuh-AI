# Honeypot System - User Guide

## Overview

The Honeypot system is a sophisticated AI-powered tool designed to detect, engage, and gather intelligence on scammers by simulating potential victims. The system uses intelligent agents to interact with scammers, extract information, and help law enforcement track scam operations.

## Features

### 1. **Honeypot Dashboard**
   - Real-time monitoring of active sessions
   - Statistics on total interactions and scammer profiles
   - Interactive map showing scammer origins (Law Enforcement view)
   - AI learning feed tracking

### 2. **Honeypot Sessions**
   - Create and manage honeypot phone numbers
   - Configure AI personality profiles
   - Monitor session status (active, completed, terminated)
   - Track call metrics and suspicious activity

### 3. **Scammer Profiles**
   - Automatic profile creation for identified scammers
   - Risk scoring based on behavior patterns
   - Track scam types and tactics used
   - Geographic location tracking
   - Associated phone numbers and aliases

### 4. **AI Agent Capabilities**
   - **Intelligent Conversation**: Simulates realistic victim personas
   - **Information Extraction**: Identifies and records:
     - Phone numbers
     - Payment details
     - Scam scripts
     - Personal information requests
     - Threats and urgency indicators
     - Pressure tactics
   
   - **Scam Type Detection**: Recognizes:
     - Tech support scams
     - Lottery/prize scams
     - Bank account scams
     - Investment scams
     - Romance scams
     - Government impersonation
     - Package delivery scams
     - Insurance claim scams

### 5. **Reports & Analytics**
   - Generate comprehensive reports on scammer activities
   - Export data for law enforcement
   - Trend analysis and pattern recognition

## Access Levels

### Regular Users
- View their own honeypot sessions
- Create and manage honeypot configurations
- View interactions with their sessions
- Access basic scammer profiles

### Law Enforcement
- Full system access
- View all honeypot sessions and interactions
- Access complete scammer database
- Geographic heat maps
- Advanced reporting and analytics

## How to Use

### Creating a Honeypot Session

1. Navigate to `/honeypot/`
2. Click "Create New Session" or go to `/honeypot/sessions/create/`
3. Configure the session:
   - **Session Name**: Unique identifier
   - **Phone Number**: Dedicated number for the honeypot
   - **Description**: Purpose and context
   - **AI Personality**: Configure victim persona:
     - Name, age, occupation
     - Personality traits
     - Vulnerabilities
     - Resistance triggers

4. Save and activate the session

### Monitoring Interactions

1. Go to `/honeypot/sessions/`
2. Select a session to view details
3. Review:
   - Call history
   - AI-generated responses
   - Extracted scammer information
   - Risk assessments

### Viewing Scammer Profiles

1. Navigate to `/honeypot/scammers/`
2. Browse scammer profiles sorted by risk score
3. Click on a profile to see:
   - Contact history
   - Scam types used
   - Associated numbers
   - Geographic location
   - Risk score breakdown

### Generating Reports

1. Go to `/honeypot/reports/`
2. Select report parameters:
   - Date range
   - Scam types
   - Risk levels
3. Export in various formats (PDF, CSV, JSON)

## API Endpoints

### Process Call
```
POST /honeypot/api/sessions/<session_id>/process/
```
Process incoming call data and generate AI response

### Session Status
```
GET /honeypot/api/sessions/<session_id>/status/
```
Get current session status and statistics

## Configuration Options

### Personality Configuration
```json
{
  "personality": {
    "name": "Sarah Johnson",
    "age": 68,
    "occupation": "Retired Teacher",
    "location": "Springfield, IL",
    "personality_traits": ["cautious", "friendly", "concerned"],
    "vulnerabilities": ["technologically_challenged", "trusting_of_authority"],
    "resistance_triggers": ["money_requests", "urgent_demands"]
  }
}
```

### AI Behavior Settings
- **max_conversation_length**: Maximum conversation turns (default: 50)
- **trust_building_turns**: Turns spent building trust (default: 3-5)
- **information_gathering_turns**: Turns for intel extraction (default: 5-10)
- **termination_triggers**: Conditions for ending conversation
  - Repeated money requests
  - Aggressive threats
  - Maximum turns reached

## Best Practices

### For Setting Up Honeypots

1. **Choose Realistic Personas**: Use age, occupation, and traits that match common scam targets
2. **Monitor Regularly**: Check active sessions daily
3. **Update Profiles**: Keep scammer profiles current with new information
4. **Document Everything**: Add notes to sessions and profiles

### For Law Enforcement

1. **Review High-Risk Profiles**: Prioritize scammers with risk scores > 0.7
2. **Track Patterns**: Look for common numbers, scripts, or tactics
3. **Export Evidence**: Generate reports with complete interaction logs
4. **Coordinate Actions**: Share intelligence with other agencies

### Security Considerations

1. **Never Provide Real Information**: AI agents use fake data only
2. **Monitor for Escalation**: Watch for threats or dangerous behavior
3. **Legal Compliance**: Ensure operations comply with local regulations
4. **Data Protection**: Secure storage of captured scammer data

## Troubleshooting

### Session Not Receiving Calls
- Verify phone number routing is configured
- Check session status is "active"
- Review firewall/network settings

### AI Agent Not Responding
- Check configuration is complete
- Verify AI service is running
- Review logs for errors

### Missing Scammer Data
- Ensure auto-profile creation is enabled
- Check interaction recording is working
- Verify database connections

## URL Reference

| Feature | URL | Description |
|---------|-----|-------------|
| Dashboard | `/honeypot/` | Main honeypot dashboard |
| Sessions List | `/honeypot/sessions/` | View all sessions |
| Create Session | `/honeypot/sessions/create/` | Create new honeypot |
| Session Detail | `/honeypot/sessions/<id>/` | View session details |
| Scammer Profiles | `/honeypot/scammers/` | Browse scammers |
| Scammer Detail | `/honeypot/scammers/<id>/` | View scammer profile |
| Reports | `/honeypot/reports/` | Generate reports |

## Support

For technical support or questions:
- Check system logs in `/logs/`
- Review Django admin interface
- Contact system administrator

---

**Note**: The honeypot system is a law enforcement tool. Use responsibly and in accordance with local laws and regulations.
