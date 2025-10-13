# Document Tracking System — Application Description

## Short Summary
A Flask-based workflow application for tracking official documents across offices. Users create, accept, forward, release, decline, and archive documents with end-to-end visibility and audit trails. The app includes admin approval for new accounts, role-based access, notifications, batch actions, analytics dashboards, printable reports, and modules for Leave Requests, EWP (Employee Welfare/Payroll-like) records, and Employee records. Time computations and analytics use Manila time and business-hour deltas.

---

## Detailed Description

### 1) Overview / Elevator Pitch
The Document Tracking System is a modular, role-aware web application built with Flask and SQLAlchemy to coordinate and monitor the movement of documents across departments. It provides:
- A complete document lifecycle (create → accept → forward → release/decline → archive/unarchive)
- Activity logging and notifications
- Admin analytics and reporting
- Specialized modules for Leave Requests and EWP records
- Employee directory management (admin only)
- Secure file serving and barcode management
- Batch operations and print-ready reports

Timezone and metrics are localized to Asia/Manila, and analytics focus on business-hour processing times across users and classifications.

---

### 2) Key Features

- Authentication & Admin Approval
  - Registration with admin approval workflow; only “Active” accounts can log in
  - Flask-Login session management; User status: Pending, Active, Disabled, Declined
  - Per-user permission flag for Leave module access (can_access_leave)

- Document Lifecycle
  - Create documents with barcode, classification, attachments, and routing (recipient)
  - Accept, Forward, Release, Decline with reason, Archive/Unarchive
  - Batch actions: Accept, Forward, Release, Decline multiple documents at once
  - Complete activity logging and per-document audit trail

- Activity Logging & Notifications
  - ActivityLog for document events (Created, Accepted, Forwarded, Released, Declined, Resubmitted, Archived, etc.)
  - Notifications for key events (received doc, accepted, declined, released), with mark-read/mark-all/delete-all
- SLA Monitoring
  - Background job evaluates pending SLAs for Documents, Leave Requests, and EWP records on a rolling schedule
  - Sends automated warnings to owners and escalations to admins when thresholds are breached (business-hour aware for documents)

- Leave Management
  - Create/Edit/Delete Leave requests with multiple date ranges
  - Per-range time modes: FULL_DAY, AM_HALF, PM_HALF
  - Subtype and subtype details (e.g., Sick Leave reasons, Special Leave details)
  - Status transitions (Pending, For Computation, For Signature, Released)
  - Analytics and time-to-release metrics

- EWP Records
  - Create/Edit/Update status/Delete EWP entries with amount parsing/validation
  - Status transitions similar to Leave/Docs
  - Tied to user who created it; included in Leave view tab

- Employee Records (Admin Only)
  - CRUD with search, pagination, choice lists for offices and statuses
  - Validations (unique biometric number), and protections

- Analytics & Admin Dashboard
  - Totals and status breakdowns
  - Classification and sub-classification counts
  - User processing metrics and rankings (avg handling times)
  - Daily/Monthly activity metrics and charts data
  - Document release processing times (business hours)
  - Leave performance by type and by creator

- Reporting
  - Admin-only print-ready report (HTML or plain text)
  - Select period by date range or month/year
  - Per-classification average processing times (and subtypes)
  - Rankings and user performance
  - Optional document list (capped) for the period

- Barcode & File Management
  - Barcode availability check with suggestions for conflicts
  - Secure PDF and file serving under /uploads with MIME handling and traversal prevention

- Search & Pagination
  - Dashboard search across title/office/classification/barcode
  - Segmented dashboard views (Created vs Received vs Leave)

---

### 3) Roles & Permissions

- Admin
  - Approves/declines users; toggles statuses
  - Access to Admin Dashboard and analytics
  - Full Employee management
  - Elevated permissions for editing/deleting Released items in some modules

- Standard User
  - Create, accept, forward, release, decline, archive their documents within authorization
  - Optional Leave/EWP access if can_access_leave is enabled

- Leave Module Access
  - Governed by per-user flag can_access_leave

---

### 4) Data Model Overview (SQLAlchemy)

- User
  - username, email, password_hash, is_admin, can_access_leave, status
  - Relationships: documents_created, documents_received, notifications, processing_logs
  - Active-only login logic via property override of is_active

- Document
  - title, office, classification, status
  - action_taken, attachment, remarks, barcode
  - Timestamps: timestamp (created), accepted_timestamp, forwarded_timestamp, released_timestamp
  - creator_id, recipient_id, activities, processing_logs
  - Helper: last_activity_details, restore_from_archive, to_dict()

- ActivityLog
  - timestamp, action, remarks, user_id, document_id, to_dict()
  - Indexed by document_id

- Notification
  - user_id, message, is_read, timestamp
  - Relationship: user

- ProcessingLog
  - user_id, document_id, accepted_timestamp, forwarded_timestamp
  - Per-document handling duration basis

- LeaveRequest
  - barcode, employee_name, office, leave_type, subtype, subtype_detail
  - start_date, end_date, created_timestamp, released_timestamp, status, remarks
  - created_by_user_id, date_ranges (relationship to LeaveDateRange)
  - to_dict()

- LeaveDateRange
  - leave_request_id, start_date, end_date, time_mode (FULL_DAY, AM_HALF, PM_HALF)
  - to_dict()

- EWPRecord
  - barcode, employee_name, office, amount, purpose, remarks
  - status, created_timestamp, created_by_user_id
  - to_dict()

- Utilities and Formatting
  - to_local_time(dt) and format_timestamp(ts) ensure Asia/Manila presentation
  - format_timedelta(td) normalizes durations into compact d/h/m string

---

### 5) Core Workflows

- Document Flow
  1. Creator submits document specifying recipient, classification, action_taken, optional barcode/attachment
  2. Recipient Accepts or Declines (with reason)
  3. Recipient may Forward to another recipient (resets status to Pending, logs ProcessingLog)
  4. Recipient Releases (finalizes with released_timestamp)
  5. Creator/Recipient can Archive; later Unarchive sets back to Pending

- Leave Management
  - Create Leave with one or multiple date ranges; each range has its own time_mode
  - Compute parent bounds (start_date/end_date) from ranges
  - Subtypes/details captured based on selected leave_type
  - Status changes (Pending → For Computation → For Signature → Released)
  - Per-record time-to-release and overall analytics

- EWP Records
  - Create with robust decimal parsing; update status (Pending/For Computation/Released)
  - Edit/Delete with admin safeguards

- Batch Operations
  - Accept/Decline/Forward/Release multiple documents, with validations and notifications

---

### 6) Admin Dashboard & Analytics

- Metrics
  - Totals by status and classification (with subtypes: Travel Order, Salary, Voucher, etc.)
  - Released processing times (business hours)
  - Daily vs Monthly activity counts
  - User handling times (accept → forward deltas)
  - Longest pending items, created vs released daily series
  - Leave analytics: counts by type and status; performance by creator

- Rankings
  - Top and longest processing performers (avg handling times) monthly and overall

- Data Sources
  - ProcessingLog for handling durations
  - Document timestamps and classification patterns
  - LeaveRequest timestamps and types

---

### 7) Archive

- Filter by month/year or a direct date range
- Search across fields (title, office, classification, status, barcode)
- Sort by timestamp desc with pagination
- Unarchive returns item to Pending

---

### 8) Reporting

- Admin-only endpoint for print-ready report
- Output: HTML or text/plain (txt) modes
- Period selection: date range or month/year
- Content includes:
  - Summary totals
  - Per-classification and sub-class averages (business hours)
  - Monthly and overall rankings
  - User performance (created, handled, avg times)
  - Optional capped document list for the period

---

### 9) Files, Uploads, and Barcodes

- File Serving
  - /uploads/<filename> endpoint serves files securely
  - MIME controls; PDF special-cased; traversal prevention checks
  - Upload path utilities; disk paths normalized and ensured

- Barcodes
  - Availability check endpoint with suggestions (-A, -B, suffixes) on conflicts
  - Integrated into forms for better UX

---

### 10) UI and Navigation

- Pages
  - Home (Login/Register), Overview, Dashboard (Created/Received/Leave tabs)
  - Archive, Admin Dashboard, Print Report
  - Employee Records and Forms (admin only)

- Templates and Assets
  - Jinja2 templates under app/templates/
  - Static assets, seasonal themes, notification sound
  - Pagination and search patterns for list views

---

### 11) Security & Validation Highlights

- Access control guards on routes and actions
- Active-only login enforcement (User.is_active override)
- Strict admin checks for admin-only endpoints
- Form validation and server-side checks for IDs/ownership/status
- Secure filename handling and directory traversal prevention for file serving

---

### 12) Technology Stack & Deployment

- Backend: Flask, Flask-Login, SQLAlchemy, WTForms
- DB: SQLAlchemy ORM (default SQLite via instance/site.db), Alembic migrations
  - PostgreSQL notes available in docs/README_POSTGRESQL.md
- Timezone: Asia/Manila (pytz)
- Web: Jinja2 templates, static assets
- Servers: Gunicorn (gunicorn_config.py), Waitress (waitress_server.py), Nginx (deploy/nginx.conf, nginx_app.conf)
- WSGI Entry Points: wsgi.py, run.py

---

### 13) Configuration

- Environment/config files:
  - config.py, instance/site.db, migrations/
  - gunicorn_config.py, nginx_app.conf, deploy/nginx.conf
- Secrets:
  - generate_secret_key.py provided to create a SECRET_KEY value
- Uploads:
  - app/utils and routes manage upload paths; ensure upload directory exists and is writable

---

### 14) Directory Overview (selected)
- app/
  - __init__.py, routes.py, models.py, forms.py, utils.py
  - templates/ (home, dashboard, admin_dashboard, archive, overview, partials, errors, report_text)
  - static/ (styles, themes, images, sounds)
  - js/ (small utilities)
- instance/
  - site.db (default SQLite database)
- migrations/
  - Alembic migration scripts
- docs/
  - autostart_instructions.md, README_POSTGRESQL.md, UPGRADE.md, APP_DESCRIPTION.md (this file)
- deploy/
  - nginx.conf
- Servers/Entry: run.py, waitress_server.py, wsgi.py
- Other: requirements.txt, gunicorn_config.py, nginx_app.conf

---

### 15) Extensibility

- Schema management via Alembic enables safe evolution
- Blueprint modularity in routes and clear separation of models/forms/utilities
- ProcessingLog abstraction supports richer analytics
- Classification/subtype pattern allows granular reporting and future taxonomy expansion
- Dedicated modules (Leave, EWP, Employee) can be extended independently

---

### 16) Notes & Assumptions

- Business-hour deltas are computed via utility calculate_business_hours (see app/utils.py), with fallbacks if exceptions occur in analytics/reporting.
- Some modules (e.g., Leave/EWP/Employee) handle DB OperationalError/ProgrammingError gracefully if migrations have not been applied.
- Asia/Manila timezone is consistently applied for user-facing timestamps and reports.
