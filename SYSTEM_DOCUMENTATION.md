# Chakravyuh - Scam Detection Platform
## System Architecture & Documentation

### Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Data Flow](#data-flow)
4. [User Roles](#user-roles)
5. [Core Modules](#core-modules)
6. [Installation & Setup](#installation--setup)
7. [API Endpoints](#api-endpoints)
8. [Database Schema](#database-schema)
9. [Security Features](#security-features)
10. [Deployment Guide](#deployment-guide)

---

## Project Overview

**Chakravyuh** is an enterprise-grade cybersecurity platform for detecting and analyzing telephone scams. It combines AI-powered audio analysis, honeypot simulation, and collaborative reporting to combat scam fraud.

### Key Features
- **Real-time Scam Detection**: AI analysis of call recordings
- **Honeypot System**: Automated scammer engagement and profiling
- **Multi-role Dashboard**: User, Admin, and Law Enforcement views
- **Report Workflow**: User submission → Admin review → Law Enforcement escalation
- **Audit Logging**: Complete system action tracking
- **Notification System**: Real-time alerts for high-risk detection

### Technology Stack
- **Framework**: Django 6.0.1
- **Database**: SQLite (development), PostgreSQL (production)
- **Authentication**: Custom User model with 2FA (django-otp)
- **Audio Processing**: SpeechRecognition 3.10.0, pydub 0.25.1
- **Frontend**: Bootstrap 5, Chart.js for analytics
- **Caching**: Django LocMemCache (development)

---

## System Architecture

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INTERFACE LAYER                        │
│  ┌──────────────┬──────────────┬──────────────────────────────┐ │
│  │ User Portal  │ Admin Panel  │ Law Enforcement Dashboard    │ │
│  └──────────────┴──────────────┴──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER (Django)                   │
│  ┌─────────┬─────────┬──────────┬──────────┬──────────────────┐ │
│  │ Accounts│  Calls  │ Analysis │ Reports  │ Honeypot/Logs    │ │
│  └─────────┴─────────┴──────────┴──────────┴──────────────────┘ │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Services Layer                                              │ │
│  │  - AI Analysis Pipeline  - Report Workflow                  │ │
│  │  - Honeypot AI Agent     - Notification Manager              │ │
│  │  - Cache Utils          - Rate Limiting                      │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                   DATA & CACHE LAYER                            │
│  ┌──────────────┬──────────────────┬──────────────────────────┐ │
│  │ Django ORM   │ SQLite Database  │ LocMemCache             │ │
│  └──────────────┴──────────────────┴──────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Module Organization

**accounts/**
- Custom User model with role-based access (user, admin, law_enforcement)
- 2FA setup and OTP validation
- Permission decorators

**calls/**
- Call record creation and management
- Audio upload with validation
- Call statistics and filtering

**analysis/**
- AI analysis pipeline and transcription
- Scam probability scoring
- Cache utilities and optimization

**honeypot/**
- Honeypot session management
- AI agent for scammer engagement
- Scammer profile tracking
- Interaction extraction

**reports/**
- Report submission by users
- Admin review workflow
- Law enforcement escalation
- Evidence file management

**logs/**
- Audit logging of all actions
- System event tracking
- User activity monitoring

**notifications/**
- Notification model and manager
- User delivery preferences
- System alert triggers

---

## Data Flow

### 1. Call Upload & Analysis Flow
```
User Upload Audio
    ↓
[Audio Validation] (format, size, security checks)
    ↓
[Audio Processing] (convert to compatible format)
    ↓
[Transcription] (SpeechRecognition)
    ↓
[Scam Analysis] (keyword matching, pattern detection)
    ↓
[Probability Calculation] (voice + text analysis)
    ↓
[Store Results] (AIAnalysisResult + ScamProbabilityScore)
    ↓
[Create Notification] (if high-risk detected)
```

### 2. Honeypot Interaction Flow
```
Scammer Calls → [HoneypotSession]
    ↓
[AI Agent Processing]
    ├─ Sentiment Analysis
    ├─ Intent Detection
    ├─ Keyword Extraction
    └─ Pattern Matching
    ↓
[Save Interaction] (HoneypotInteraction record)
    ↓
[Extract Data]
    ├─ Phone Numbers
    ├─ Payment Details
    ├─ Scam Scripts
    └─ Urgency Indicators
    ↓
[Create Report] (if auto_report enabled)
    ↓
[Update Scammer Profile] (risk scoring)
```

### 3. Report Workflow
```
User Creates Report
    ↓ (status: submitted)
[Admin Dashboard Review]
    ├─ under_review
    ├─ approved ──→ [Auto-notify LE]
    └─ rejected
    ↓
[Law Enforcement Access]
    ├─ View Details
    ├─ Update Status
    └─ Attach Evidence
    ↓
(escalated)
```

---

## User Roles

### 1. **User** (Regular Users)
- **Permissions**:
  - Upload call recordings
  - Request AI analysis
  - View their own analysis results
  - Submit reports
  - Track report status
  - Access personal dashboard
  - Receive notifications

- **Restrictions**:
  - Cannot view other users' data
  - Cannot approve reports
  - Cannot access honeypot system

### 2. **Admin** (Platform Administrators)
- **Permissions**:
  - All user permissions
  - View all reports
  - Review and approve/reject reports
  - Access admin dashboard
  - View system statistics
  - Manage honeypot sessions
  - View audit logs

- **Restrictions**:
  - Cannot escalate to law enforcement (separate role)

### 3. **Law Enforcement**
- **Permissions**:
  - All admin permissions
  - View escalated reports
  - Access honeypot intelligence
  - View scammer profiles
  - Generate intelligence reports
  - Track high-risk scammers
  - Access system-wide analytics

---

## Core Modules

### **accounts/**
Core authentication and user management.

**Models**:
- `User` - Custom user model with role field

**Views**:
- `register_view` - User registration
- `login_view` - Authentication
- `setup_otp_view` - 2FA setup
- `otp_login_view` - OTP verification

**Utilities**:
- `admin_required` - Decorator for admin-only views
- `law_enforcement_required` - LE-only access
- `PermissionDenied` - Custom 403 handler

### **calls/**
Call record and audio management.

**Models**:
- `CallRecord` - Call metadata
- `AudioUpload` - Audio file storage

**Views**:
- `call_list_view` - List with filtering/pagination
- `call_detail_view` - View call details
- `upload_audio_view` - Upload audio file
- `call_statistics_view` - Analytics

**Forms**:
- `AudioUploadForm` - File validation (size, format, security)
- `CallRecordForm` - Metadata validation

### **analysis/**
AI-powered scam detection.

**Models**:
- `AIAnalysisResult` - Analysis records
- `ScamProbabilityScore` - Risk scoring

**Pipeline**:
- `transcribe_audio()` - SpeechRecognition
- `analyze_transcript()` - Keyword matching
- `calculate_scam_probability()` - Risk calculation

**Cache Utils**:
- `cache_analysis_stats()` - Cache statistics
- `cache_dashboard_stats()` - Dashboard caching
- `invalidate_*_cache()` - Manual invalidation

### **honeypot/**
Automated scammer engagement.

**Models**:
- `HoneypotSession` - Session configuration
- `HoneypotInteraction` - Conversation records
- `ScammerProfile` - Scammer tracking

**AI Agent**:
- Conversation state machine
- Sentiment/intent detection
- Data extraction
- Urgency analysis

**Views**:
- Session management (create, edit, detail)
- Interaction viewing
- Scammer profile tracking
- Intelligence reports

### **reports/**
Report submission and escalation.

**Models**:
- `Report` - Report records
- `EvidenceFile` - Evidence attachment

**Workflow**:
- User creation
- Admin review/approval
- LE escalation
- Status tracking

**Views**:
- `report_create_view` - User submission
- `report_review_view` - Admin approval
- `report_escalate_view` - LE escalation

### **logs/**
Audit and system logging.

**Models**:
- `AuditLog` - User action logging
- `SystemLog` - System events

**Signals**:
- Track logins, uploads, analysis, reports
- Automatic logging via Django signals

**Views**:
- Audit log list (filterable)
- System log list (paginated)

### **notifications/**
Real-time alert system.

**Models**:
- `Notification` - Alert records
- `NotificationSettings` - User preferences

**Manager**:
- Centralized notification creation
- Multi-delivery support (email, in-app)

**Triggers**:
- High-risk analysis detected
- Honeypot engagement
- Report escalation
- System alerts

---

## Installation & Setup

### 1. Environment Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate      # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser --email admin@example.com
```

### 3. Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### 4. Run Development Server
```bash
python manage.py runserver
```

### 5. Run Tests
```bash
# All tests
python manage.py test

# Specific app
python manage.py test analysis.tests

# Verbose output
python manage.py test -v 2
```

---

## API Endpoints

### Authentication
- `POST /accounts/login/` - User login
- `POST /accounts/register/` - User registration
- `POST /accounts/setup_otp/` - 2FA setup
- `POST /accounts/otp_login/` - OTP verification
- `GET /accounts/logout/` - Logout

### Calls
- `GET /calls/` - List calls
- `POST /calls/create/` - Create call
- `GET /calls/<uuid:call_id>/` - View call
- `POST /calls/<uuid:call_id>/upload-audio/` - Upload audio
- `GET /calls/statistics/` - Call statistics

### Analysis
- `GET /analysis/` - List analyses
- `GET /analysis/<uuid:analysis_id>/` - View analysis
- `POST /analysis/request/<uuid:call_id>/` - Request analysis
- `GET /analysis/scores/` - View scam scores
- `GET /analysis/api/status/<uuid:analysis_id>/` - Check status (JSON)

### Reports
- `GET /reports/` - List reports
- `POST /reports/create/` - Submit report
- `GET /reports/<uuid:report_id>/` - View report
- `POST /reports/<uuid:report_id>/review/` - Admin review
- `POST /reports/<uuid:report_id>/escalate/` - LE escalation

### Honeypot
- `GET /honeypot/` - Dashboard
- `GET /honeypot/sessions/` - List sessions
- `POST /honeypot/sessions/create/` - Create session
- `GET /honeypot/scammers/` - Scammer profiles
- `POST /honeypot/api/sessions/<uuid:session_id>/process/` - Process message

### Logs
- `GET /logs/` - Audit logs
- `GET /logs/system/` - System logs

### Notifications
- `GET /notifications/` - List notifications
- `POST /notifications/mark-read/<uuid:notification_id>/` - Mark read
- `POST /notifications/mark-all-read/` - Mark all read

---

## Database Schema

### Key Tables

**users_user**
```
├─ id (UUID)
├─ email (unique)
├─ password_hash
├─ role (user/admin/law_enforcement)
├─ is_active
├─ created_at
└─ last_login
```

**calls_callrecord**
```
├─ id (UUID)
├─ caller_number
├─ recipient_number
├─ call_start_time
├─ call_end_time
├─ status (pending/completed/failed)
├─ recorded_by (FK User)
└─ created_at
```

**analysis_aianalysisresult**
```
├─ id (UUID)
├─ call_record (FK CallRecord)
├─ audio_upload (FK AudioUpload)
├─ status (pending/processing/completed/failed)
├─ analysis_type
├─ requested_by (FK User)
├─ confidence_score (0-1)
├─ created_at
└─ completed_at
```

**analysis_scamprobabilityscore**
```
├─ id (UUID)
├─ analysis (FK AIAnalysisResult)
├─ call_record (FK CallRecord)
├─ overall_score (0-1)
├─ scam_level (low/medium/high/critical)
├─ voice_pattern_score
├─ speech_content_score
├─ urgency_indicators (JSON array)
└─ created_at
```

**reports_report**
```
├─ id (UUID)
├─ title
├─ report_type (scam/fraud/harassment)
├─ description
├─ status (submitted/under_review/approved/rejected/escalated)
├─ call_record (FK CallRecord)
├─ ai_analysis (FK AIAnalysisResult)
├─ submitted_by (FK User)
├─ reviewed_by (FK User)
├─ escalated_to (FK User)
├─ incident_date
├─ created_at
└─ updated_at
```

---

## Security Features

### 1. Authentication & Authorization
- ✅ Custom User model with email-based auth
- ✅ Password hashing with Django's PBKDF2
- ✅ 2FA with django-otp (TOTP)
- ✅ Role-based access control (RBAC)
- ✅ Permission decorators on sensitive views

### 2. Data Protection
- ✅ CSRF middleware on all POST requests
- ✅ XSS prevention with Django templating
- ✅ SQL injection prevention (ORM)
- ✅ Input validation on all forms
- ✅ File upload security (type, size, content validation)

### 3. Rate Limiting
- ✅ Upload rate limit (10 per hour per user)
- ✅ API rate limit (100 requests per hour)
- ✅ Login attempt limiting (5 attempts per 15 min)
- ✅ Global rate limit (1000 requests per hour)

### 4. Audit & Logging
- ✅ Complete audit trail via Django signals
- ✅ User action logging (login, upload, analysis, report)
- ✅ System event tracking
- ✅ Severity levels for log filtering

### 5. HTTPS & Headers
- ✅ SECURE_BROWSER_XSS_FILTER
- ✅ SECURE_CONTENT_TYPE_NOSNIFF
- ✅ X_FRAME_OPTIONS = 'DENY'
- ✅ HSTS enabled (production)

---

## Deployment Guide

### Production Checklist
- [ ] Set `DEBUG = False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Use environment variables for secrets
- [ ] Configure PostgreSQL (not SQLite)
- [ ] Set up proper logging
- [ ] Enable HTTPS/SSL
- [ ] Configure static file serving (CDN)
- [ ] Set up monitoring/alerts
- [ ] Configure email backend
- [ ] Test backup/restore procedures

### Environment Variables
```bash
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:pass@host/dbname
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
CMD gunicorn chakravyuh.wsgi:application --bind 0.0.0.0:8000
```

---

## Support & Maintenance

For issues, refer to:
- Django Documentation: https://docs.djangoproject.com
- SpeechRecognition: https://github.com/Uberi/speech_recognition
- django-otp: https://django-otp.readthedocs.io

Last Updated: February 2026
Version: 1.0
