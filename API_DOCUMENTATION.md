# Chakravyuh API Documentation

## Overview
Complete API reference for the Chakravyuh scam detection platform. All endpoints require authentication unless noted.

## Authentication

### Login
```
POST /accounts/login/
Content-Type: application/x-www-form-urlencoded

email=user@example.com&password=yourpassword

Response (302 redirect to dashboard on success)
```

### Register
```
POST /accounts/register/
Content-Type: application/x-www-form-urlencoded

email=newuser@example.com&password=secure123&first_name=John&last_name=Doe

Response (302 redirect to login on success)
```

### Setup 2FA
```
POST /accounts/setup_otp/
Content-Type: application/x-www-form-urlencoded

(requires authentication)

Response: 200 OK with QR code
```

### OTP Login
```
POST /accounts/otp_login/
Content-Type: application/x-www-form-urlencoded

email=user@example.com&otp_token=123456

Response: 302 redirect to dashboard
```

---

## Calls Management

### List Calls
```
GET /calls/?status=completed&caller=555&page=1
Authorization: Cookie (session auth)

Query Parameters:
  - status: pending|completed|failed
  - caller: phone number fragment
  - recipient: phone number fragment
  - date_from: YYYY-MM-DD
  - date_to: YYYY-MM-DD
  - page: pagination number

Response: 200 OK with paginated call list
```

### Create Call
```
POST /calls/create/
Content-Type: application/x-www-form-urlencoded

caller_number=+1-800-555-0100&recipient_number=+1-800-555-0101&call_start_time=2026-02-03T10:00&status=completed

Response: 302 redirect to call detail
```

### Get Call Details
```
GET /calls/{call_id}/

Response: 200 OK
{
  "id": "uuid",
  "caller_number": "+1-800-555-0100",
  "recipient_number": "+1-800-555-0101",
  "call_start_time": "2026-02-03T10:00:00Z",
  "call_end_time": "2026-02-03T10:05:00Z",
  "status": "completed",
  "audio": {...},
  "ai_analysis": {...},
  "scam_score": {...},
  "reports": [...]
}
```

### Upload Audio
```
POST /calls/{call_id}/upload-audio/
Content-Type: multipart/form-data

audio_file: <binary audio data>
format: mp3|wav|flac|aac|ogg|m4a

Response: 302 redirect to call detail

Rate Limit: 10 uploads per hour per user
```

### Call Statistics
```
GET /calls/statistics/

Response: 200 OK
{
  "total_calls": 1234,
  "calls_today": 45,
  "suspicious_calls": 123,
  "status_stats": {
    "completed": 1000,
    "pending": 200,
    "failed": 34
  },
  "recent_calls": [...]
}
```

---

## Analysis

### List Analyses
```
GET /analysis/?status=completed&confidence_min=0.7&page=1

Query Parameters:
  - analysis_type: comprehensive|voice|content
  - status: pending|processing|completed|failed
  - confidence_min: 0-1 (minimum confidence score)
  - date_from: YYYY-MM-DD
  - date_to: YYYY-MM-DD
  - page: pagination number

Response: 200 OK with analysis list
```

### Get Analysis Details
```
GET /analysis/{analysis_id}/

Response: 200 OK
{
  "id": "uuid",
  "call_record": {...},
  "status": "completed",
  "analysis_type": "comprehensive",
  "confidence_score": 0.95,
  "transcript": "...",
  "created_at": "2026-02-03T10:00:00Z",
  "completed_at": "2026-02-03T10:05:00Z",
  "scam_probability": {
    "overall_score": 0.85,
    "scam_level": "high",
    "voice_pattern_score": 0.80,
    "speech_content_score": 0.90,
    "urgency_indicators": ["time_pressure", "account_threat"]
  }
}
```

### Request Analysis
```
POST /analysis/request/{call_id}/

Body: application/x-www-form-urlencoded
(empty or optional parameters)

Response: 302 redirect to analysis detail
```

### Get Scam Scores
```
GET /analysis/scores/?scam_level=high&page=1

Query Parameters:
  - scam_level: low|medium|high|critical
  - page: pagination number

Response: 200 OK with scam score list
```

### API: Check Analysis Status
```
GET /analysis/api/status/{analysis_id}/
Accept: application/json

Response: 200 OK (JSON)
{
  "id": "uuid",
  "status": "completed",
  "status_display": "Completed",
  "confidence_score": 0.95,
  "scam_score": 0.85,
  "scam_level": "High Risk",
  "completed_at": "2026-02-03T10:05:00Z"
}

Rate Limit: 100 requests per hour
```

---

## Reports

### List Reports
```
GET /reports/?status=approved&page=1

Query Parameters:
  - status: submitted|under_review|approved|rejected|escalated
  - priority: low|medium|high|critical
  - report_type: scam|fraud|harassment
  - page: pagination number

Response: 200 OK with report list
```

### Create Report
```
POST /reports/create/
Content-Type: application/x-www-form-urlencoded

title=Suspected Scam&report_type=scam&description=...&incident_date=2026-02-03T10:00&call_record={call_id}&ai_analysis={analysis_id}

Response: 302 redirect to report detail
```

### Get Report Details
```
GET /reports/{report_id}/

Response: 200 OK
{
  "id": "uuid",
  "title": "Suspected Scam",
  "report_type": "scam",
  "description": "...",
  "status": "submitted",
  "call_record": {...},
  "ai_analysis": {...},
  "submitted_by": {...},
  "reviewed_by": null,
  "escalated_to": null,
  "created_at": "2026-02-03T10:00:00Z"
}
```

### Admin: Review Report
```
POST /reports/{report_id}/review/
Content-Type: application/x-www-form-urlencoded

status=approved|rejected&notes=Reason for decision

Response: 302 redirect to report detail

Authorization: Admin role required
```

### Law Enforcement: Escalate Report
```
POST /reports/{report_id}/escalate/
Content-Type: application/x-www-form-urlencoded

status=escalated&priority=high&notes=Notes for LE

Response: 302 redirect to report detail

Authorization: Law Enforcement role required
```

---

## Honeypot

### Dashboard
```
GET /honeypot/

Response: 200 OK (HTML)
- Active sessions count
- Recent interactions
- Top scammers by risk
- System statistics

Authorization: Login required
```

### List Honeypot Sessions
```
GET /honeypot/sessions/?status=active&search=keyword&page=1

Query Parameters:
  - status: active|completed|terminated
  - search: search in session name, phone, description
  - page: pagination number

Response: 200 OK with session list
```

### Create Honeypot Session
```
POST /honeypot/sessions/create/
Content-Type: application/x-www-form-urlencoded

session_name=Test Session&phone_number=+1-800-HONEYPOT&description=...&personality_name=John&personality_age=35&personality_occupation=Engineer&personality_location=New York&max_conversation_length=10&resistance_threshold=0.3&enable_auto_termination=true&scam_type_focus=romance_scam

Response: 302 redirect to session detail
```

### Get Session Details
```
GET /honeypot/sessions/{session_id}/

Response: 200 OK
{
  "id": "uuid",
  "session_name": "Test Session",
  "phone_number": "+1-800-HONEYPOT",
  "status": "active",
  "created_by": {...},
  "start_time": "2026-02-03T10:00:00Z",
  "total_calls_received": 15,
  "interactions": [...]
}
```

### API: Process Call
```
POST /honeypot/api/sessions/{session_id}/process/
Content-Type: application/json
Authorization: Bearer <token> or Cookie (session auth)

{
  "message": "You need to verify your account immediately!",
  "caller_number": "+1-555-1234567",
  "context": {
    "call_duration": 120,
    "sentiment": "urgent"
  }
}

Response: 200 OK (JSON)
{
  "success": true,
  "response": "I understand your concern. Let me help you...",
  "terminate": false,
  "interaction_id": "uuid",
  "state": "INFORMATION_GATHERING",
  "turn_count": 3
}

Rate Limit: 100 requests per hour
```

### API: Check Session Status
```
GET /honeypot/api/sessions/{session_id}/status/
Accept: application/json

Response: 200 OK (JSON)
{
  "id": "uuid",
  "status": "active",
  "total_calls": 15,
  "suspicious_calls": 8,
  "recent_interactions": [
    {
      "id": "uuid",
      "scammer": "+1-555-1234567",
      "status": "completed",
      "start_time": "2026-02-03T10:00:00Z",
      "success_rating": 0.85
    }
  ]
}
```

### List Scammer Profiles
```
GET /honeypot/scammers/?risk_level=high&search=phone&page=1

Query Parameters:
  - status: active|inactive|monitored
  - risk_level: low|medium|high
  - search: phone number or name fragment
  - page: pagination number

Response: 200 OK with scammer profile list
```

---

## Logs & Audit

### Audit Logs
```
GET /logs/?action=login&user={user_id}&date_from=2026-02-01&page=1

Query Parameters:
  - action: login|upload|analysis|report_filed
  - user: user ID
  - date_from: YYYY-MM-DD
  - date_to: YYYY-MM-DD
  - page: pagination number

Response: 200 OK with audit log list
```

### System Logs
```
GET /logs/system/?severity=high&date_from=2026-02-01&page=1

Query Parameters:
  - severity: info|low|medium|high|critical
  - date_from: YYYY-MM-DD
  - date_to: YYYY-MM-DD
  - page: pagination number

Response: 200 OK with system log list

Authorization: Admin role required
```

---

## Notifications

### List Notifications
```
GET /notifications/?is_read=false&page=1

Query Parameters:
  - is_read: true|false
  - priority: low|medium|high|critical
  - type: analysis_complete|high_risk_alert|honeypot_engaged
  - page: pagination number

Response: 200 OK with notification list
```

### Mark Notification as Read
```
POST /notifications/mark-read/{notification_id}/

Response: 302 redirect back to notification list
```

### Mark All Notifications as Read
```
POST /notifications/mark-all-read/

Response: 302 redirect to notification list
```

---

## Dashboards

### User Dashboard
```
GET /dashboard/

Response: 200 OK (HTML)
- Total calls analyzed
- Total scams detected
- Suspicious alerts
- Scam trends chart
- Recent activities
- Pending analyses
```

### Admin Dashboard
```
GET /dashboard/admin/

Response: 200 OK (HTML)
- Report statistics
- Flagged numbers
- Honeypot logs
- System statistics
- Monthly trends
- Heatmap data

Authorization: Admin role required
```

### Law Enforcement Dashboard
```
GET /dashboard/law-enforcement/

Response: 200 OK (HTML)
- All active cases
- High-risk scammers
- Escalated reports
- Intelligence summary

Authorization: Law Enforcement role required
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Invalid input",
  "details": {
    "audio_file": ["File size too large"]
  }
}
```

### 403 Forbidden
```
Status: 403
(Custom 403.html page)
```

### 404 Not Found
```
Status: 404
(Custom 404.html page)
```

### 429 Too Many Requests
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 3600
}
```

### 500 Server Error
```json
{
  "error": "Internal server error",
  "request_id": "uuid"
}
```

---

## Rate Limiting

All endpoints are subject to rate limiting:

**Global Limits**:
- 1000 requests per hour per user/IP

**Endpoint Specific**:
- Upload: 10 per hour per user
- API calls: 100 per hour per user
- Login attempts: 5 per 15 minutes

**Response Headers**:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1675329600
```

---

## Pagination

Paginated responses include:
- `page_obj` context with Django paginator
- `page_obj.has_next`, `page_obj.has_previous`
- `page_obj.paginator.num_pages`
- Next/previous page links in templates

**Default Page Size**: 25 items

---

## Testing the API

### Using cURL
```bash
# Login
curl -c cookies.txt -d "email=test@example.com&password=pass" \
  http://localhost:8000/accounts/login/

# List calls
curl -b cookies.txt http://localhost:8000/calls/

# Upload audio
curl -b cookies.txt -F "audio_file=@recording.mp3" \
  http://localhost:8000/calls/call-id/upload-audio/
```

### Using Python Requests
```python
import requests

session = requests.Session()

# Login
session.post('http://localhost:8000/accounts/login/', data={
    'email': 'test@example.com',
    'password': 'password'
})

# List calls
response = session.get('http://localhost:8000/calls/')

# Upload audio
with open('recording.mp3', 'rb') as f:
    response = session.post(
        'http://localhost:8000/calls/call-id/upload-audio/',
        files={'audio_file': f}
    )
```

---

## Changelog

### v1.0 (February 2026)
- Initial release
- Complete API implementation
- Rate limiting
- Honeypot system
- Report workflow
- Audit logging
- Notification system

---

Last Updated: February 3, 2026
