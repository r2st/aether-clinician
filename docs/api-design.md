# Aether Clinician -- REST API Specification

**Version:** 1.0.0  
**Base URL:** `https://api.aetherclinician.in/api/v1`  
**Protocol:** HTTPS (TLS 1.2+)  
**Content-Type:** `application/json` (unless otherwise noted)  
**Last Updated:** 2026-06-27

---

## Table of Contents

1. [API Conventions](#1-api-conventions)
2. [Authentication Flow](#2-authentication-flow)
3. [Patients](#3-patients)
4. [Documents](#4-documents)
5. [Patient Record (Longitudinal View)](#5-patient-record-longitudinal-view)
6. [Encounters](#6-encounters)
7. [Intake / Consult](#7-intake--consult)
8. [Reasoning](#8-reasoning)
9. [Drug Safety](#9-drug-safety)
10. [Management](#10-management)
11. [Clinical Suggestions](#11-clinical-suggestions)
12. [Audit](#12-audit)
13. [Export](#13-export)
14. [Real-Time Patterns (SSE / WebSocket)](#14-real-time-patterns-sse--websocket)
15. [Rate Limiting and Throttling](#15-rate-limiting-and-throttling)
16. [File Upload Specifications](#16-file-upload-specifications)
17. [Webhook / Event Patterns](#17-webhook--event-patterns)
18. [API Versioning Strategy](#18-api-versioning-strategy)
19. [Schema Definitions](#19-schema-definitions)

---

## 1. API Conventions

### 1.1 Base URL and Versioning

All endpoints are prefixed with `/api/v1/`. The version number is part of the URL path. See [Section 18](#18-api-versioning-strategy) for the full versioning strategy.

```
https://api.aetherclinician.in/api/v1/{resource}
```

### 1.2 Authentication

All endpoints except `POST /auth/signup`, `POST /auth/login`, and `POST /auth/refresh` require a valid JWT access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Tokens are short-lived (15 minutes for access, 7 days for refresh). See [Section 2](#2-authentication-flow) for the full auth flow.

### 1.3 Request Format

- Request bodies are JSON (`Content-Type: application/json`) unless the endpoint accepts file uploads (`multipart/form-data`).
- All field names use `snake_case`.
- Boolean query parameters accept `true` / `false`.

### 1.4 Response Format

All successful responses return JSON with the following envelope for single resources:

```json
{
  "data": { ... }
}
```

For collections:

```json
{
  "data": [ ... ],
  "pagination": {
    "total": 142,
    "limit": 20,
    "offset": 0,
    "next_page_token": "eyJpZCI6..."
  }
}
```

### 1.5 Pagination

Two modes are supported. Endpoints declare which mode they use.

**Cursor-based (preferred for large or real-time datasets):**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page_token` | string | — | Opaque cursor from a previous response |
| `limit` | integer | 20 | Items per page (max 100) |

**Offset-based (for simpler datasets):**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `offset` | integer | 0 | Number of items to skip |
| `limit` | integer | 20 | Items per page (max 100) |

### 1.6 Filtering

Filters are passed as query parameters. Each endpoint documents its supported filters.

```
GET /api/v1/patients?gender=female&age_min=30&age_max=60
```

### 1.7 Sorting

```
GET /api/v1/patients?sort=created_at&order=desc
```

| Parameter | Type | Default | Values |
|-----------|------|---------|--------|
| `sort` | string | `created_at` | Endpoint-specific |
| `order` | string | `desc` | `asc`, `desc` |

### 1.8 Error Format

All errors return a consistent JSON body:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The field 'email' is required.",
    "details": {
      "field": "email",
      "constraint": "required"
    }
  }
}
```

### 1.9 HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK -- request succeeded |
| 201 | Created -- resource created |
| 204 | No Content -- successful deletion or action with no body |
| 400 | Bad Request -- malformed request body or parameters |
| 401 | Unauthorized -- missing or invalid token |
| 403 | Forbidden -- valid token but insufficient permissions |
| 404 | Not Found -- resource does not exist |
| 409 | Conflict -- duplicate resource or state conflict |
| 422 | Unprocessable Entity -- valid JSON but semantic validation failure |
| 429 | Too Many Requests -- rate limit exceeded |
| 500 | Internal Server Error |

### 1.10 Common Headers

**Request:**

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes (most) | `Bearer <access_token>` |
| `Content-Type` | Yes | `application/json` or `multipart/form-data` |
| `X-Request-ID` | No | Client-generated UUID for request tracing |
| `X-Idempotency-Key` | No | For POST requests to ensure idempotency |

**Response:**

| Header | Description |
|--------|-------------|
| `X-Request-ID` | Echoed back or server-generated |
| `X-RateLimit-Limit` | Max requests per window |
| `X-RateLimit-Remaining` | Remaining requests |
| `X-RateLimit-Reset` | Unix timestamp when window resets |
| `Retry-After` | Seconds to wait (on 429) |

### 1.11 Resource IDs

All resource IDs are UUIDv4 strings:

```
"id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

### 1.12 Timestamps

All timestamps are ISO 8601 UTC:

```
"created_at": "2026-06-27T10:30:00Z"
```

### 1.13 CORS

The API is configured with CORS for the frontend origin(s). Preflight `OPTIONS` requests are handled automatically. The `Access-Control-Allow-Credentials` header is set to `true` to support cookie-based refresh tokens if needed.

---

## 2. Authentication Flow

### 2.1 POST /auth/signup

Create a new clinician account.

**Auth required:** No

**Request:**

```json
POST /api/v1/auth/signup
Content-Type: application/json

{
  "email": "dr.sharma@clinic.in",
  "password": "SecureP@ss123",
  "full_name": "Dr. Priya Sharma",
  "medical_license_number": "KA-MCI-2019-45678",
  "specialization": "general_practice",
  "clinic_name": "Sharma Family Clinic",
  "demo_mode": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | Valid email address |
| `password` | string | Yes (unless `demo_mode`) | Min 8 chars, 1 uppercase, 1 digit, 1 special |
| `full_name` | string | Yes | Clinician's full name |
| `medical_license_number` | string | No | Medical council registration number |
| `specialization` | string | No | Enum: `general_practice`, `internal_medicine`, `pediatrics`, `family_medicine`, `other` |
| `clinic_name` | string | No | Name of the practice |
| `demo_mode` | boolean | No | If `true`, creates a demo account (no password required, seeded with sample data) |

**Response (201 Created):**

```json
{
  "data": {
    "user": {
      "id": "b7e1c2d3-f4a5-6789-0bcd-ef1234567890",
      "email": "dr.sharma@clinic.in",
      "full_name": "Dr. Priya Sharma",
      "medical_license_number": "KA-MCI-2019-45678",
      "specialization": "general_practice",
      "clinic_name": "Sharma Family Clinic",
      "is_demo": false,
      "created_at": "2026-06-27T10:30:00Z"
    },
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "dGhpcyBpcyBhIHJlZnJl...",
    "token_type": "Bearer",
    "expires_in": 900
  }
}
```

**Errors:**

| Status | Code | When |
|--------|------|------|
| 400 | `INVALID_REQUEST` | Missing required fields |
| 409 | `EMAIL_ALREADY_EXISTS` | Email already registered |
| 422 | `WEAK_PASSWORD` | Password does not meet policy |

---

### 2.2 POST /auth/login

Authenticate and receive tokens.

**Auth required:** No

**Request:**

```json
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "dr.sharma@clinic.in",
  "password": "SecureP@ss123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | Registered email |
| `password` | string | Yes | Account password |

**Demo mode login:**

```json
{
  "email": "demo@aetherclinician.in",
  "demo_mode": true
}
```

**Response (200 OK):**

```json
{
  "data": {
    "user": {
      "id": "b7e1c2d3-f4a5-6789-0bcd-ef1234567890",
      "email": "dr.sharma@clinic.in",
      "full_name": "Dr. Priya Sharma",
      "specialization": "general_practice",
      "is_demo": false,
      "last_login_at": "2026-06-27T10:30:00Z"
    },
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "dGhpcyBpcyBhIHJlZnJl...",
    "token_type": "Bearer",
    "expires_in": 900
  }
}
```

**Errors:**

| Status | Code | When |
|--------|------|------|
| 401 | `INVALID_CREDENTIALS` | Wrong email or password |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many login attempts |

---

### 2.3 POST /auth/refresh

Rotate the access token using a valid refresh token.

**Auth required:** No (but requires valid refresh token)

**Request:**

```json
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "dGhpcyBpcyBhIHJlZnJl..."
}
```

**Response (200 OK):**

```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 900
  }
}
```

**Errors:**

| Status | Code | When |
|--------|------|------|
| 401 | `INVALID_REFRESH_TOKEN` | Token expired or revoked |

---

### 2.4 POST /auth/logout

Invalidate the current session (both access and refresh tokens).

**Auth required:** Yes

**Request:**

```json
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

No request body required.

**Response (204 No Content):**

No body.

---

### 2.5 GET /auth/me

Get the current authenticated user's profile.

**Auth required:** Yes

**Request:**

```
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

**Response (200 OK):**

```json
{
  "data": {
    "id": "b7e1c2d3-f4a5-6789-0bcd-ef1234567890",
    "email": "dr.sharma@clinic.in",
    "full_name": "Dr. Priya Sharma",
    "medical_license_number": "KA-MCI-2019-45678",
    "specialization": "general_practice",
    "clinic_name": "Sharma Family Clinic",
    "is_demo": false,
    "created_at": "2026-06-27T10:30:00Z",
    "last_login_at": "2026-06-27T10:30:00Z"
  }
}
```

**Errors:**

| Status | Code | When |
|--------|------|------|
| 401 | `UNAUTHORIZED` | Invalid or expired token |

---

## 3. Patients

### 3.1 POST /patients

Create a new patient record.

**Auth required:** Yes

**Request:**

```json
POST /api/v1/patients
Content-Type: application/json

{
  "full_name": "Rajesh Kumar",
  "date_of_birth": "1985-03-15",
  "gender": "male",
  "phone": "+919876543210",
  "email": "rajesh.kumar@email.com",
  "address": {
    "line1": "42 MG Road",
    "line2": "Koramangala",
    "city": "Bangalore",
    "state": "Karnataka",
    "pincode": "560034"
  },
  "blood_group": "B+",
  "emergency_contact": {
    "name": "Anita Kumar",
    "phone": "+919876543211",
    "relationship": "spouse"
  },
  "notes": "Known diabetic, regular follow-up patient"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `full_name` | string | Yes | Patient full name |
| `date_of_birth` | string (date) | Yes | ISO 8601 date |
| `gender` | string | Yes | `male`, `female`, `other` |
| `phone` | string | No | E.164 format |
| `email` | string | No | Email address |
| `address` | Address | No | Structured address |
| `blood_group` | string | No | `A+`, `A-`, `B+`, `B-`, `AB+`, `AB-`, `O+`, `O-` |
| `emergency_contact` | EmergencyContact | No | Emergency contact info |
| `notes` | string | No | Free-text clinician notes |

**Response (201 Created):**

```json
{
  "data": {
    "id": "c3d4e5f6-a7b8-9012-cdef-345678901234",
    "full_name": "Rajesh Kumar",
    "date_of_birth": "1985-03-15",
    "age": 41,
    "gender": "male",
    "phone": "+919876543210",
    "email": "rajesh.kumar@email.com",
    "address": {
      "line1": "42 MG Road",
      "line2": "Koramangala",
      "city": "Bangalore",
      "state": "Karnataka",
      "pincode": "560034"
    },
    "blood_group": "B+",
    "emergency_contact": {
      "name": "Anita Kumar",
      "phone": "+919876543211",
      "relationship": "spouse"
    },
    "notes": "Known diabetic, regular follow-up patient",
    "created_at": "2026-06-27T10:30:00Z",
    "updated_at": "2026-06-27T10:30:00Z",
    "created_by": "b7e1c2d3-f4a5-6789-0bcd-ef1234567890"
  }
}
```

**Errors:**

| Status | Code | When |
|--------|------|------|
| 400 | `INVALID_REQUEST` | Missing required fields or invalid format |
| 409 | `PATIENT_DUPLICATE` | Duplicate patient detected (same name + DOB + phone) |
| 422 | `VALIDATION_ERROR` | Invalid field values |

---

### 3.2 GET /patients

List patients with pagination, filtering, and search.

**Auth required:** Yes

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | — | Full-text search across name, phone, email |
| `gender` | string | — | Filter by gender |
| `age_min` | integer | — | Minimum age |
| `age_max` | integer | — | Maximum age |
| `sort` | string | `created_at` | Sort field: `full_name`, `date_of_birth`, `created_at`, `updated_at` |
| `order` | string | `desc` | `asc` or `desc` |
| `limit` | integer | 20 | Max 100 |
| `offset` | integer | 0 | Offset for pagination |

**Request:**

```
GET /api/v1/patients?q=rajesh&gender=male&limit=10&sort=full_name&order=asc
Authorization: Bearer <access_token>
```

**Response (200 OK):**

```json
{
  "data": [
    {
      "id": "c3d4e5f6-a7b8-9012-cdef-345678901234",
      "full_name": "Rajesh Kumar",
      "date_of_birth": "1985-03-15",
      "age": 41,
      "gender": "male",
      "phone": "+919876543210",
      "last_visit_at": "2026-06-20T14:00:00Z",
      "created_at": "2026-06-01T10:30:00Z"
    }
  ],
  "pagination": {
    "total": 1,
    "limit": 10,
    "offset": 0
  }
}
```

---

### 3.3 GET /patients/{patient_id}

Get a single patient by ID.

**Auth required:** Yes

**Response (200 OK):** Full `Patient` object (same shape as POST response).

**Errors:**

| Status | Code | When |
|--------|------|------|
| 404 | `PATIENT_NOT_FOUND` | Patient ID does not exist |

---

### 3.4 PUT /patients/{patient_id}

Update a patient record. Supports partial updates (send only changed fields).

**Auth required:** Yes

**Request:**

```json
PUT /api/v1/patients/c3d4e5f6-a7b8-9012-cdef-345678901234
Content-Type: application/json

{
  "phone": "+919876543299",
  "notes": "Known diabetic. Started metformin 500mg BD on 2026-06-20."
}
```

**Response (200 OK):** Full updated `Patient` object.

**Errors:**

| Status | Code | When |
|--------|------|------|
| 404 | `PATIENT_NOT_FOUND` | Patient does not exist |
| 422 | `VALIDATION_ERROR` | Invalid field values |

---

### 3.5 DELETE /patients/{patient_id}

Soft-delete a patient record. The record is marked inactive but retained for audit purposes.

**Auth required:** Yes

**Response (204 No Content).**

**Errors:**

| Status | Code | When |
|--------|------|------|
| 404 | `PATIENT_NOT_FOUND` | Patient does not exist |
| 409 | `PATIENT_HAS_ACTIVE_ENCOUNTERS` | Cannot delete patient with open encounters |

---

## 4. Documents

### 4.1 POST /patients/{patient_id}/documents

Upload a clinical document for extraction.

**Auth required:** Yes

**Request:**

```
POST /api/v1/patients/c3d4e5f6-a7b8-9012-cdef-345678901234/documents
Content-Type: multipart/form-data

file: <binary>
document_type: "lab_report"
source: "upload"
notes: "Fasting blood work from June 2026"
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | binary | Yes | PDF, PNG, JPG, JPEG, HEIC |
| `document_type` | string | Yes | `lab_report`, `prescription`, `discharge_summary`, `imaging_report`, `referral_letter`, `insurance`, `other` |
| `source` | string | No | `upload`, `camera`, `scan`. Default: `upload` |
| `notes` | string | No | Clinician notes about the document |

**Response (201 Created):**

```json
{
  "data": {
    "id": "d4e5f6a7-b8c9-0123-def4-567890123456",
    "patient_id": "c3d4e5f6-a7b8-9012-cdef-345678901234",
    "document_type": "lab_report",
    "source": "upload",
    "filename": "blood_report_june2026.pdf",
    "mime_type": "application/pdf",
    "file_size_bytes": 245760,
    "notes": "Fasting blood work from June 2026",
    "extraction_status": "queued",
    "uploaded_at": "2026-06-27T10:30:00Z",
    "uploaded_by": "b7e1c2d3-f4a5-6789-0bcd-ef1234567890"
  }
}
```

**Errors:**

| Status | Code | When |
|--------|------|------|
| 400 | `INVALID_FILE_TYPE` | Unsupported file format |
| 400 | `FILE_TOO_LARGE` | Exceeds 20 MB limit |
| 404 | `PATIENT_NOT_FOUND` | Patient does not exist |
| 422 | `VALIDATION_ERROR` | Missing document_type |

---

### 4.2 GET /patients/{patient_id}/documents

List all documents for a patient.

**Auth required:** Yes

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `document_type` | string | — | Filter by type |
| `extraction_status` | string | — | `queued`, `processing`, `completed`, `failed`, `needs_review` |
| `sort` | string | `uploaded_at` | Sort field |
| `order` | string | `desc` | `asc` or `desc` |
| `limit` | integer | 20 | Max 100 |
| `offset` | integer | 0 | Offset |

**Response (200 OK):**

```json
{
  "data": [
    {
      "id": "d4e5f6a7-b8c9-0123-def4-567890123456",
      "document_type": "lab_report",
      "filename": "blood_report_june2026.pdf",
      "extraction_status": "completed",
      "uploaded_at": "2026-06-27T10:30:00Z",
      "extracted_at": "2026-06-27T10:31:15Z"
    }
  ],
  "pagination": {
    "total": 5,
    "limit": 20,
    "offset": 0
  }
}
```

---

### 4.3 GET /patients/{patient_id}/documents/{document_id}

Get document metadata and extraction status.

**Auth required:** Yes

**Response (200 OK):** Full `Document` object.

---

### 4.4 GET /patients/{patient_id}/documents/{document_id}/extraction

Get the extracted data from a processed document.

**Auth required:** Yes

**Response (200 OK):**

```json
{
  "data": {
    "document_id": "d4e5f6a7-b8c9-0123-def4-567890123456",
    "extraction_status": "completed",
    "extracted_at": "2026-06-27T10:31:15Z",
    "confidence_score": 0.92,
    "fields": [
      {
        "field_id": "f1a2b3c4-d5e6-7890-abcd-ef1234567890",
        "category": "lab_result",
        "name": "Fasting Blood Glucose",
        "value": "126",
        "unit": "mg/dL",
        "reference_range": "70-100",
        "is_abnormal": true,
        "confidence": 0.98,
        "needs_review": false,
        "source_region": {
          "page": 1,
          "x": 120,
          "y": 340,
          "width": 200,
          "height": 30
        }
      },
      {
        "field_id": "f2b3c4d5-e6f7-8901-bcde-f23456789012",
        "category": "lab_result",
        "name": "HbA1c",
        "value": "7.2",
        "unit": "%",
        "reference_range": "4.0-5.6",
        "is_abnormal": true,
        "confidence": 0.95,
        "needs_review": false,
        "source_region": {
          "page": 1,
          "x": 120,
          "y": 380,
          "width": 200,
          "height": 30
        }
      },
      {
        "field_id": "f3c4d5e6-f7a8-9012-cdef-345678901234",
        "category": "lab_result",
        "name": "Serum Creatinine",
        "value": "1.1",
        "unit": "mg/dL",
        "reference_range": "0.7-1.3",
        "is_abnormal": false,
        "confidence": 0.65,
        "needs_review": true,
        "source_region": {
          "page": 1,
          "x": 120,
          "y": 420,
          "width": 200,
          "height": 30
        }
      }
    ],
    "metadata": {
      "lab_name": "SRL Diagnostics",
      "report_date": "2026-06-25",
      "ordering_physician": "Dr. Sharma"
    }
  }
}
```

---

### 4.5 PUT /patients/{patient_id}/documents/{document_id}/extraction/fields/{field_id}

Confirm or correct a low-confidence extracted field.

**Auth required:** Yes

**Request:**

```json
PUT /api/v1/patients/{patient_id}/documents/{document_id}/extraction/fields/{field_id}
Content-Type: application/json

{
  "value": "1.1",
  "unit": "mg/dL",
  "confirmed": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `value` | string | No | Corrected value (if editing) |
| `unit` | string | No | Corrected unit (if editing) |
| `confirmed` | boolean | Yes | `true` to accept the field as-is or after edit |

**Response (200 OK):**

```json
{
  "data": {
    "field_id": "f3c4d5e6-f7a8-9012-cdef-345678901234",
    "name": "Serum Creatinine",
    "value": "1.1",
    "unit": "mg/dL",
    "confidence": 1.0,
    "needs_review": false,
    "confirmed_by": "b7e1c2d3-f4a5-6789-0bcd-ef1234567890",
    "confirmed_at": "2026-06-27T10:35:00Z"
  }
}
```

**Errors:**

| Status | Code | When |
|--------|------|------|
| 404 | `FIELD_NOT_FOUND` | Field ID does not exist |
| 409 | `FIELD_ALREADY_CONFIRMED` | Field was already confirmed |

---

### 4.6 GET /patients/{patient_id}/documents/{document_id}/extraction/stream

Server-Sent Events stream for live extraction progress.

**Auth required:** Yes (token passed as query parameter `token`)

**Request:**

```
GET /api/v1/patients/{patient_id}/documents/{document_id}/extraction/stream?token=<access_token>
Accept: text/event-stream
```

**Event stream:**

```
event: extraction_started
data: {"document_id": "d4e5f6a7...", "status": "processing", "timestamp": "2026-06-27T10:30:30Z"}

event: field_extracted
data: {"field_id": "f1a2b3c4...", "name": "Fasting Blood Glucose", "value": "126", "unit": "mg/dL", "confidence": 0.98}

event: field_extracted
data: {"field_id": "f2b3c4d5...", "name": "HbA1c", "value": "7.2", "unit": "%", "confidence": 0.95}

event: extraction_completed
data: {"document_id": "d4e5f6a7...", "status": "completed", "total_fields": 12, "needs_review_count": 2, "confidence_score": 0.92}
```

See [Section 14](#14-real-time-patterns-sse--websocket) for full SSE specification.

---

## 5. Patient Record (Longitudinal View)

### 5.1 GET /patients/{patient_id}/record

Get the assembled longitudinal patient record, aggregated from all documents and encounters.

**Auth required:** Yes

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sections` | string | all | Comma-separated: `medications`, `labs`, `conditions`, `allergies`, `vitals`, `procedures`, `immunizations` |
| `from_date` | string (date) | — | Start of date range (ISO 8601) |
| `to_date` | string (date) | — | End of date range (ISO 8601) |

**Response (200 OK):**

```json
{
  "data": {
    "patient_id": "c3d4e5f6-a7b8-9012-cdef-345678901234",
    "last_updated_at": "2026-06-27T10:31:15Z",
    "medications": {
      "active": [
        {
          "id": "med-001",
          "name": "Metformin",
          "generic_name": "metformin_hydrochloride",
          "dose": "500mg",
          "frequency": "BD",
          "route": "oral",
          "started_at": "2026-06-20",
          "prescribed_by": "Dr. Priya Sharma",
          "source_document_id": "d4e5f6a7-b8c9-0123-def4-567890123456",
          "source_encounter_id": null
        }
      ],
      "past": [
        {
          "id": "med-002",
          "name": "Amoxicillin",
          "dose": "500mg",
          "frequency": "TDS",
          "route": "oral",
          "started_at": "2026-05-01",
          "ended_at": "2026-05-07",
          "reason_for_stopping": "course_completed"
        }
      ]
    },
    "labs": [
      {
        "id": "lab-001",
        "name": "Fasting Blood Glucose",
        "value": 126,
        "unit": "mg/dL",
        "reference_range": "70-100",
        "is_abnormal": true,
        "recorded_at": "2026-06-25",
        "source_document_id": "d4e5f6a7-b8c9-0123-def4-567890123456"
      },
      {
        "id": "lab-002",
        "name": "HbA1c",
        "value": 7.2,
        "unit": "%",
        "reference_range": "4.0-5.6",
        "is_abnormal": true,
        "recorded_at": "2026-06-25",
        "source_document_id": "d4e5f6a7-b8c9-0123-def4-567890123456"
      }
    ],
    "conditions": [
      {
        "id": "cond-001",
        "name": "Type 2 Diabetes Mellitus",
        "icd10_code": "E11",
        "status": "active",
        "onset_date": "2026-06-20",
        "diagnosed_by": "Dr. Priya Sharma"
      }
    ],
    "allergies": [
      {
        "id": "allergy-001",
        "allergen": "Sulfonamides",
        "type": "drug",
        "severity": "moderate",
        "reaction": "Skin rash",
        "reported_at": "2026-06-01"
      }
    ],
    "vitals": [
      {
        "id": "vital-001",
        "recorded_at": "2026-06-27T10:00:00Z",
        "blood_pressure_systolic": 138,
        "blood_pressure_diastolic": 88,
        "heart_rate": 78,
        "temperature_celsius": 36.8,
        "respiratory_rate": 16,
        "spo2": 98,
        "weight_kg": 82,
        "height_cm": 172,
        "bmi": 27.7
      }
    ]
  }
}
```

---

### 5.2 GET /patients/{patient_id}/record/medications/timeline

Get the medication timeline for the patient showing start/stop dates, overlaps, and changes.

**Auth required:** Yes

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `from_date` | string (date) | 1 year ago | Start date |
| `to_date` | string (date) | today | End date |

**Response (200 OK):**

```json
{
  "data": {
    "patient_id": "c3d4e5f6-a7b8-9012-cdef-345678901234",
    "from_date": "2025-06-27",
    "to_date": "2026-06-27",
    "timeline": [
      {
        "medication_id": "med-001",
        "name": "Metformin 500mg BD",
        "start_date": "2026-06-20",
        "end_date": null,
        "is_active": true,
        "events": [
          {
            "type": "started",
            "date": "2026-06-20",
            "notes": "Initial prescription for T2DM"
          }
        ]
      },
      {
        "medication_id": "med-002",
        "name": "Amoxicillin 500mg TDS",
        "start_date": "2026-05-01",
        "end_date": "2026-05-07",
        "is_active": false,
        "events": [
          {
            "type": "started",
            "date": "2026-05-01",
            "notes": "URI treatment"
          },
          {
            "type": "stopped",
            "date": "2026-05-07",
            "notes": "Course completed"
          }
        ]
      }
    ]
  }
}
```

---

### 5.3 GET /patients/{patient_id}/record/labs/{marker}/trends

Get historical trend data for a specific lab marker.

**Auth required:** Yes

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `marker` | string | Lab marker slug, e.g. `fasting_blood_glucose`, `hba1c`, `serum_creatinine` |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `from_date` | string (date) | 1 year ago | Start date |
| `to_date` | string (date) | today | End date |

**Response (200 OK):**

```json
{
  "data": {
    "patient_id": "c3d4e5f6-a7b8-9012-cdef-345678901234",
    "marker": "hba1c",
    "display_name": "HbA1c",
    "unit": "%",
    "reference_range": {
      "low": 4.0,
      "high": 5.6
    },
    "data_points": [
      {
        "value": 6.8,
        "recorded_at": "2026-01-15",
        "source_document_id": "doc-001",
        "is_abnormal": true
      },
      {
        "value": 7.0,
        "recorded_at": "2026-03-20",
        "source_document_id": "doc-002",
        "is_abnormal": true
      },
      {
        "value": 7.2,
        "recorded_at": "2026-06-25",
        "source_document_id": "doc-003",
        "is_abnormal": true
      }
    ],
    "trend_direction": "worsening"
  }
}
```

**Errors:**

| Status | Code | When |
|--------|------|------|
| 404 | `PATIENT_NOT_FOUND` | Patient does not exist |
| 404 | `MARKER_NOT_FOUND` | Unrecognized lab marker slug |

---

## 6. Encounters

### 6.1 POST /patients/{patient_id}/encounters

Create a new clinical encounter.

**Auth required:** Yes

**Request:**

```json
POST /api/v1/patients/c3d4e5f6-a7b8-9012-cdef-345678901234/encounters
Content-Type: application/json

{
  "encounter_type": "outpatient",
  "chief_complaint": "Increased thirst and frequent urination for 2 weeks",
  "vitals": {
    "blood_pressure_systolic": 138,
    "blood_pressure_diastolic": 88,
    "heart_rate": 78,
    "temperature_celsius": 36.8,
    "respiratory_rate": 16,
    "spo2": 98,
    "weight_kg": 82
  },
  "notes": "Patient reports polyuria and polydipsia. No fever."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `encounter_type` | string | Yes | `outpatient`, `follow_up`, `emergency`, `telemedicine` |
| `chief_complaint` | string | No | Primary presenting complaint |
| `vitals` | Vitals | No | Vitals at time of encounter |
| `notes` | string | No | Clinician notes |

**Response (201 Created):**

```json
{
  "data": {
    "id": "enc-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "patient_id": "c3d4e5f6-a7b8-9012-cdef-345678901234",
    "encounter_type": "outpatient",
    "status": "open",
    "chief_complaint": "Increased thirst and frequent urination for 2 weeks",
    "vitals": { ... },
    "notes": "Patient reports polyuria and polydipsia. No fever.",
    "started_at": "2026-06-27T10:30:00Z",
    "ended_at": null,
    "created_by": "b7e1c2d3-f4a5-6789-0bcd-ef1234567890"
  }
}
```

---

### 6.2 GET /patients/{patient_id}/encounters

List encounters for a patient.

**Auth required:** Yes

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | string | — | `open`, `closed` |
| `encounter_type` | string | — | Filter by type |
| `from_date` | string (date) | — | Start date |
| `to_date` | string (date) | — | End date |
| `sort` | string | `started_at` | Sort field |
| `order` | string | `desc` | `asc` or `desc` |
| `limit` | integer | 20 | Max 100 |
| `offset` | integer | 0 | Offset |

**Response (200 OK):** Paginated list of `Encounter` summary objects.

---

### 6.3 GET /patients/{patient_id}/encounters/{encounter_id}

Get a single encounter with full detail.

**Auth required:** Yes

**Response (200 OK):** Full `Encounter` object.

---

### 6.4 PUT /patients/{patient_id}/encounters/{encounter_id}

Update an encounter (add notes, update vitals, change status).

**Auth required:** Yes

**Request:**

```json
PUT /api/v1/patients/{patient_id}/encounters/{encounter_id}
Content-Type: application/json

{
  "status": "closed",
  "notes": "Diagnosed with T2DM. Started metformin 500mg BD. Follow-up in 4 weeks.",
  "ended_at": "2026-06-27T11:00:00Z"
}
```

**Response (200 OK):** Updated `Encounter` object.

---

### 6.5 DELETE /patients/{patient_id}/encounters/{encounter_id}

Soft-delete an encounter. Only allowed for encounters in `open` status with no attached reasoning sessions or suggestions.

**Auth required:** Yes

**Response (204 No Content).**

**Errors:**

| Status | Code | When |
|--------|------|------|
| 409 | `ENCOUNTER_HAS_REASONING` | Cannot delete encounter with reasoning sessions |
| 409 | `ENCOUNTER_CLOSED` | Cannot delete a closed encounter |

---

## 7. Intake / Consult

The intake flow is a conversational, adaptive questioning sequence driven by the system's clinical reasoning agents. The clinician starts a consult session, submits the presenting complaint, and the system asks clarifying questions one at a time.

### 7.1 POST /patients/{patient_id}/encounters/{encounter_id}/consult

Start a new consult session for an encounter. This triggers the adaptive intake agent.

**Auth required:** Yes

**Request:**

```json
POST /api/v1/patients/{patient_id}/encounters/{encounter_id}/consult
Content-Type: application/json

{
  "presenting_complaint": "Patient complains of increased thirst and frequent urination for 2 weeks. Also reports unintentional weight loss of 3kg.",
  "mode": "guided"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `presenting_complaint` | string | Yes | Free-text complaint from clinician |
| `mode` | string | No | `guided` (default, adaptive questions) or `quick` (minimal questions) |

**Response (201 Created):**

```json
{
  "data": {
    "consult_id": "consult-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "encounter_id": "enc-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "patient_id": "c3d4e5f6-a7b8-9012-cdef-345678901234",
    "status": "in_progress",
    "presenting_complaint": "Patient complains of increased thirst and frequent urination for 2 weeks. Also reports unintentional weight loss of 3kg.",
    "mode": "guided",
    "next_question": {
      "question_id": "q-001",
      "text": "Does the patient have a family history of diabetes mellitus?",
      "question_type": "single_choice",
      "options": [
        {"value": "yes_first_degree", "label": "Yes - first degree relative (parent/sibling)"},
        {"value": "yes_second_degree", "label": "Yes - second degree relative"},
        {"value": "no", "label": "No"},
        {"value": "unknown", "label": "Unknown"}
      ],
      "clinical_context": "Family history is a major risk factor for T2DM and influences differential ranking.",
      "is_required": true
    },
    "questions_asked": 0,
    "estimated_remaining": 5,
    "started_at": "2026-06-27T10:30:00Z"
  }
}
```

---

### 7.2 POST /patients/{patient_id}/encounters/{encounter_id}/consult/{consult_id}/answers

Submit an answer to a clarifying question.

**Auth required:** Yes

**Request:**

```json
POST /api/v1/patients/{patient_id}/encounters/{encounter_id}/consult/{consult_id}/answers
Content-Type: application/json

{
  "question_id": "q-001",
  "answer": {
    "value": "yes_first_degree",
    "free_text": "Father diagnosed with T2DM at age 50"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `question_id` | string | Yes | ID of the question being answered |
| `answer.value` | string or array | Yes | Selected option value(s) or free-text |
| `answer.free_text` | string | No | Additional free-text context |

**Response (200 OK):**

```json
{
  "data": {
    "consult_id": "consult-a1b2c3d4...",
    "status": "in_progress",
    "answer_recorded": {
      "question_id": "q-001",
      "value": "yes_first_degree",
      "free_text": "Father diagnosed with T2DM at age 50"
    },
    "next_question": {
      "question_id": "q-002",
      "text": "Has the patient experienced any episodes of blurred vision?",
      "question_type": "yes_no",
      "options": [
        {"value": "yes", "label": "Yes"},
        {"value": "no", "label": "No"}
      ],
      "clinical_context": "Blurred vision can indicate hyperglycemia-related osmotic changes.",
      "is_required": true
    },
    "questions_asked": 1,
    "estimated_remaining": 4
  }
}
```

When the intake is complete, `next_question` is `null` and `status` changes to `completed`:

```json
{
  "data": {
    "consult_id": "consult-a1b2c3d4...",
    "status": "completed",
    "next_question": null,
    "questions_asked": 6,
    "estimated_remaining": 0,
    "intake_summary": {
      "presenting_complaint": "Polyuria, polydipsia, unintentional weight loss (3kg/2wk)",
      "key_positives": [
        "Family history of T2DM (father)",
        "Polyuria x 2 weeks",
        "Polydipsia x 2 weeks",
        "Unintentional weight loss 3kg"
      ],
      "key_negatives": [
        "No blurred vision",
        "No fever",
        "No dysuria"
      ],
      "risk_factors": [
        "Family history of diabetes",
        "BMI 27.7 (overweight)",
        "Age > 40"
      ]
    },
    "completed_at": "2026-06-27T10:38:00Z"
  }
}
```

---

### 7.3 GET /patients/{patient_id}/encounters/{encounter_id}/consult/{consult_id}

Get the current status of a consult session, including all questions asked and answers given.

**Auth required:** Yes

**Response (200 OK):**

```json
{
  "data": {
    "consult_id": "consult-a1b2c3d4...",
    "status": "in_progress",
    "mode": "guided",
    "presenting_complaint": "...",
    "questions_and_answers": [
      {
        "question_id": "q-001",
        "text": "Does the patient have a family history of diabetes mellitus?",
        "answer": {
          "value": "yes_first_degree",
          "free_text": "Father diagnosed with T2DM at age 50"
        },
        "answered_at": "2026-06-27T10:32:00Z"
      }
    ],
    "next_question": { ... },
    "questions_asked": 1,
    "estimated_remaining": 4,
    "started_at": "2026-06-27T10:30:00Z"
  }
}
```

---

### 7.4 POST /patients/{patient_id}/encounters/{encounter_id}/consult/{consult_id}/skip

Skip the current question.

**Auth required:** Yes

**Request:**

```json
POST /api/v1/patients/{patient_id}/encounters/{encounter_id}/consult/{consult_id}/skip
Content-Type: application/json

{
  "question_id": "q-002",
  "reason": "Patient unable to provide information"
}
```

**Response (200 OK):** Same shape as answer response with next question.

---

### 7.5 POST /patients/{patient_id}/encounters/{encounter_id}/consult/{consult_id}/complete

Force-complete the intake (skip remaining questions and proceed with available data).

**Auth required:** Yes

**Response (200 OK):** Final consult status with `intake_summary`.

---

## 8. Reasoning

The reasoning module triggers the multi-agent diagnostic reasoning engine. Agents form and revise hypotheses in real-time, visible in the "Reasoning Theatre" via SSE.

### 8.1 POST /patients/{patient_id}/encounters/{encounter_id}/reasoning

Trigger differential reasoning for a completed intake.

**Auth required:** Yes

**Request:**

```json
POST /api/v1/patients/{patient_id}/encounters/{encounter_id}/reasoning
Content-Type: application/json

{
  "consult_id": "consult-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "include_patient_record": true,
  "reasoning_depth": "standard"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `consult_id` | string | Yes | Reference to the completed consult |
| `include_patient_record` | boolean | No | Include longitudinal record context (default: `true`) |
| `reasoning_depth` | string | No | `quick` (3-5 differentials), `standard` (default, full analysis), `deep` (exhaustive, slower) |

**Response (202 Accepted):**

```json
{
  "data": {
    "reasoning_session_id": "rs-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "encounter_id": "enc-a1b2c3d4...",
    "status": "in_progress",
    "reasoning_depth": "standard",
    "started_at": "2026-06-27T10:40:00Z",
    "stream_url": "/api/v1/patients/{patient_id}/encounters/{encounter_id}/reasoning/rs-a1b2c3d4.../stream"
  }
}
```

---

### 8.2 GET /patients/{patient_id}/encounters/{encounter_id}/reasoning/{session_id}/stream

SSE stream for the Reasoning Theatre -- live agent state updates.

**Auth required:** Yes (token as query parameter)

**Request:**

```
GET /api/v1/patients/{patient_id}/encounters/{encounter_id}/reasoning/{session_id}/stream?token=<access_token>
Accept: text/event-stream
```

**Event stream:**

```
event: session_started
data: {"session_id": "rs-a1b2c3d4...", "agents": ["diagnostician", "evidence_reviewer", "safety_checker", "specialist_consultant"], "timestamp": "2026-06-27T10:40:01Z"}

event: agent_state
data: {"agent": "diagnostician", "state": "thinking", "message": "Analyzing presenting complaint and intake findings...", "timestamp": "2026-06-27T10:40:02Z"}

event: hypothesis_formed
data: {"agent": "diagnostician", "hypothesis": {"id": "hyp-001", "diagnosis": "Type 2 Diabetes Mellitus", "icd10": "E11", "confidence": 0.82, "key_evidence": ["Polyuria", "Polydipsia", "FBG 126 mg/dL", "HbA1c 7.2%", "Family history"]}, "timestamp": "2026-06-27T10:40:05Z"}

event: hypothesis_formed
data: {"agent": "diagnostician", "hypothesis": {"id": "hyp-002", "diagnosis": "Type 1 Diabetes Mellitus", "icd10": "E10", "confidence": 0.15, "key_evidence": ["Polyuria", "Polydipsia", "Weight loss"]}, "timestamp": "2026-06-27T10:40:06Z"}

event: agent_state
data: {"agent": "evidence_reviewer", "state": "reviewing", "message": "Cross-referencing hypotheses against lab results and patient history...", "timestamp": "2026-06-27T10:40:08Z"}

event: hypothesis_revised
data: {"agent": "evidence_reviewer", "hypothesis_id": "hyp-001", "previous_confidence": 0.82, "new_confidence": 0.88, "reason": "HbA1c 7.2% confirms sustained hyperglycemia. Age and BMI support T2DM over T1DM.", "timestamp": "2026-06-27T10:40:10Z"}

event: hypothesis_revised
data: {"agent": "evidence_reviewer", "hypothesis_id": "hyp-002", "previous_confidence": 0.15, "new_confidence": 0.08, "reason": "Age 41, BMI 27.7, and gradual onset argue against T1DM. No ketosis reported.", "timestamp": "2026-06-27T10:40:11Z"}

event: agent_state
data: {"agent": "safety_checker", "state": "checking", "message": "Reviewing medication safety and contraindications...", "timestamp": "2026-06-27T10:40:12Z"}

event: investigation_recommended
data: {"agent": "specialist_consultant", "investigation": {"name": "Fasting C-peptide", "reason": "To differentiate T1DM vs T2DM if clinical uncertainty remains", "priority": "recommended"}, "timestamp": "2026-06-27T10:40:14Z"}

event: session_completed
data: {"session_id": "rs-a1b2c3d4...", "status": "completed", "duration_seconds": 15, "differentials_count": 4, "timestamp": "2026-06-27T10:40:16Z"}
```

See [Section 14](#14-real-time-patterns-sse--websocket) for reconnection and error handling.

---

### 8.3 GET /patients/{patient_id}/encounters/{encounter_id}/reasoning/{session_id}

Get the status or final results of a reasoning session.

**Auth required:** Yes

**Response (200 OK) -- when completed:**

```json
{
  "data": {
    "reasoning_session_id": "rs-a1b2c3d4...",
    "encounter_id": "enc-a1b2c3d4...",
    "consult_id": "consult-a1b2c3d4...",
    "status": "completed",
    "reasoning_depth": "standard",
    "differentials": [
      {
        "rank": 1,
        "hypothesis_id": "hyp-001",
        "diagnosis": "Type 2 Diabetes Mellitus",
        "icd10_code": "E11",
        "confidence": 0.88,
        "supporting_evidence": [
          {"finding": "FBG 126 mg/dL (elevated)", "weight": "strong"},
          {"finding": "HbA1c 7.2% (elevated)", "weight": "strong"},
          {"finding": "Polyuria x 2 weeks", "weight": "moderate"},
          {"finding": "Polydipsia x 2 weeks", "weight": "moderate"},
          {"finding": "Family history - father with T2DM", "weight": "moderate"},
          {"finding": "BMI 27.7 (overweight)", "weight": "supporting"}
        ],
        "against_evidence": [],
        "clinical_reasoning": "Classic presentation of T2DM with biochemical confirmation. Two independent criteria met (FBG >= 126 and HbA1c >= 6.5%). Risk factors include family history, age > 40, and overweight BMI."
      },
      {
        "rank": 2,
        "hypothesis_id": "hyp-002",
        "diagnosis": "Type 1 Diabetes Mellitus",
        "icd10_code": "E10",
        "confidence": 0.08,
        "supporting_evidence": [
          {"finding": "Polyuria and polydipsia", "weight": "moderate"},
          {"finding": "Unintentional weight loss", "weight": "supporting"}
        ],
        "against_evidence": [
          {"finding": "Age 41 (late onset less typical)", "weight": "moderate"},
          {"finding": "Overweight BMI (atypical for T1DM)", "weight": "moderate"},
          {"finding": "No ketosis", "weight": "supporting"}
        ],
        "clinical_reasoning": "While symptoms overlap, the age of onset, BMI, and absence of ketosis argue strongly against T1DM. C-peptide testing can definitively exclude."
      }
    ],
    "recommended_investigations": [
      {
        "id": "inv-001",
        "name": "Fasting C-peptide",
        "reason": "Differentiate T1DM vs T2DM",
        "priority": "recommended",
        "urgency": "routine"
      },
      {
        "id": "inv-002",
        "name": "Lipid profile",
        "reason": "Metabolic syndrome screening in newly diagnosed T2DM",
        "priority": "recommended",
        "urgency": "routine"
      },
      {
        "id": "inv-003",
        "name": "Urine microalbumin/creatinine ratio",
        "reason": "Baseline nephropathy screening",
        "priority": "recommended",
        "urgency": "routine"
      }
    ],
    "agent_traces": {
      "diagnostician": {
        "steps": 4,
        "duration_ms": 3200,
        "hypotheses_formed": 4,
        "hypotheses_discarded": 2
      },
      "evidence_reviewer": {
        "steps": 3,
        "duration_ms": 2800,
        "revisions_made": 4
      },
      "safety_checker": {
        "steps": 2,
        "duration_ms": 1500,
        "flags_raised": 0
      },
      "specialist_consultant": {
        "steps": 2,
        "duration_ms": 2000,
        "investigations_suggested": 3
      }
    },
    "started_at": "2026-06-27T10:40:00Z",
    "completed_at": "2026-06-27T10:40:16Z",
    "duration_seconds": 16
  }
}
```

**Errors:**

| Status | Code | When |
|--------|------|------|
| 404 | `SESSION_NOT_FOUND` | Reasoning session does not exist |
| 409 | `SESSION_IN_PROGRESS` | Reasoning is still running (use SSE to follow) |

---

### 8.4 GET /patients/{patient_id}/encounters/{encounter_id}/reasoning/{session_id}/investigations

Get investigation recommendations from a completed reasoning session.

**Auth required:** Yes

**Response (200 OK):**

```json
{
  "data": {
    "reasoning_session_id": "rs-a1b2c3d4...",
    "investigations": [
      {
        "id": "inv-001",
        "name": "Fasting C-peptide",
        "reason": "Differentiate T1DM vs T2DM",
        "priority": "recommended",
        "urgency": "routine",
        "estimated_cost_inr": 800,
        "suggested_by_agent": "specialist_consultant"
      }
    ]
  }
}
```

---

## 9. Drug Safety

Drug safety checks are deterministic. The API returns hard blocks (which cannot be overridden), warnings, and informational flags.

### 9.1 POST /patients/{patient_id}/drug-safety/check

Check a proposed medication against the patient's full record (current medications, allergies, conditions, labs).

**Auth required:** Yes

**Request:**

```json
POST /api/v1/patients/c3d4e5f6.../drug-safety/check
Content-Type: application/json

{
  "medication": {
    "name": "Glimepiride",
    "generic_name": "glimepiride",
    "dose": "1mg",
    "frequency": "OD",
    "route": "oral"
  },
  "encounter_id": "enc-a1b2c3d4..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `medication.name` | string | Yes | Medication name |
| `medication.generic_name` | string | No | Generic/INN name for more precise matching |
| `medication.dose` | string | Yes | Proposed dose |
| `medication.frequency` | string | Yes | Dosing frequency |
| `medication.route` | string | No | Route of administration |
| `encounter_id` | string | No | Link to encounter for audit trail |

**Response (200 OK):**

```json
{
  "data": {
    "check_id": "dsc-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "medication": {
      "name": "Glimepiride",
      "generic_name": "glimepiride",
      "dose": "1mg",
      "frequency": "OD"
    },
    "overall_status": "warning",
    "is_blocked": false,
    "flags": [
      {
        "id": "flag-001",
        "type": "interaction",
        "severity": "warning",
        "title": "Additive hypoglycemia risk with Metformin",
        "description": "Combining glimepiride with metformin increases the risk of hypoglycemia. Monitor blood glucose closely during initiation and dose adjustments.",
        "interacting_medication": "Metformin 500mg BD",
        "evidence_level": "well_established",
        "source": "BNF, CDSCO"
      },
      {
        "id": "flag-002",
        "type": "dose_concern",
        "severity": "info",
        "title": "Starting dose appropriate",
        "description": "1mg OD is the recommended starting dose for glimepiride. Titrate based on glycemic response.",
        "source": "CDSCO prescribing information"
      }
    ],
    "checked_against": {
      "current_medications": ["Metformin 500mg BD"],
      "allergies": ["Sulfonamides"],
      "conditions": ["Type 2 Diabetes Mellitus"],
      "recent_labs": {
        "serum_creatinine": {"value": 1.1, "date": "2026-06-25"},
        "egfr": {"value": 78, "date": "2026-06-25"}
      }
    },
    "checked_at": "2026-06-27T10:45:00Z"
  }
}
```

**Example with a hard block:**

```json
{
  "data": {
    "check_id": "dsc-blocked-example",
    "medication": {
      "name": "Sulfamethoxazole",
      "generic_name": "sulfamethoxazole",
      "dose": "800mg",
      "frequency": "BD"
    },
    "overall_status": "blocked",
    "is_blocked": true,
    "flags": [
      {
        "id": "flag-block-001",
        "type": "allergy",
        "severity": "critical",
        "title": "CONTRAINDICATED: Patient allergic to Sulfonamides",
        "description": "Patient has a documented allergy to sulfonamides. Sulfamethoxazole is a sulfonamide antibiotic. This prescription is blocked and cannot be overridden.",
        "allergen": "Sulfonamides",
        "reaction": "Skin rash",
        "is_hard_block": true,
        "source": "Patient allergy record"
      }
    ],
    "checked_at": "2026-06-27T10:46:00Z"
  }
}
```

---

### 9.2 GET /patients/{patient_id}/drug-safety/flags

Get all active drug safety flags for the patient's current medications.

**Auth required:** Yes

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `severity` | string | — | Filter: `critical`, `warning`, `info` |
| `type` | string | — | Filter: `interaction`, `contraindication`, `allergy`, `dose_concern`, `renal_adjustment` |

**Response (200 OK):**

```json
{
  "data": {
    "patient_id": "c3d4e5f6...",
    "total_flags": 2,
    "flags": [
      {
        "id": "flag-active-001",
        "type": "interaction",
        "severity": "warning",
        "title": "Metformin + Glimepiride: Additive hypoglycemia risk",
        "medications_involved": ["Metformin 500mg BD", "Glimepiride 1mg OD"],
        "description": "Monitor blood glucose closely.",
        "source": "BNF"
      }
    ],
    "last_checked_at": "2026-06-27T10:45:00Z"
  }
}
```

---

## 10. Management

> **Phase 3 -- Not yet implemented.** Endpoints are defined for forward compatibility.

### 10.1 GET /patients/{patient_id}/encounters/{encounter_id}/management/{diagnosis_code}

Get guideline-cited management options for a specific diagnosis in the context of this patient.

**Auth required:** Yes

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `diagnosis_code` | string | ICD-10 code, e.g. `E11` |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `guideline_source` | string | `auto` | `api_india`, `nice`, `who`, `auto` (selects best match) |

**Response (200 OK):**

```json
{
  "data": {
    "diagnosis": {
      "code": "E11",
      "name": "Type 2 Diabetes Mellitus"
    },
    "patient_context": {
      "patient_id": "c3d4e5f6...",
      "relevant_factors": ["HbA1c 7.2%", "BMI 27.7", "Sulfonamide allergy", "No renal impairment"]
    },
    "management_options": [
      {
        "id": "mgmt-001",
        "category": "pharmacological",
        "recommendation": "Continue Metformin 500mg BD. Consider uptitration to 1000mg BD if tolerated.",
        "evidence_grade": "A",
        "guideline_source": "API India T2DM Guidelines 2024",
        "guideline_citation": "Section 4.2: First-line therapy with metformin, target HbA1c < 7%",
        "contraindications_for_patient": [],
        "patient_specific_notes": "Current dose is subtherapeutic. Uptitration recommended given HbA1c 7.2%."
      },
      {
        "id": "mgmt-002",
        "category": "pharmacological",
        "recommendation": "Add DPP-4 inhibitor (e.g., Sitagliptin 100mg OD) if metformin monotherapy insufficient after 3 months.",
        "evidence_grade": "A",
        "guideline_source": "API India T2DM Guidelines 2024",
        "guideline_citation": "Section 4.3: Second-line add-on therapy",
        "contraindications_for_patient": [],
        "patient_specific_notes": "Preferred over sulfonylurea given lower hypoglycemia risk."
      },
      {
        "id": "mgmt-003",
        "category": "lifestyle",
        "recommendation": "Medical nutrition therapy and structured exercise program. Target 5-7% weight loss.",
        "evidence_grade": "A",
        "guideline_source": "API India T2DM Guidelines 2024",
        "guideline_citation": "Section 3.1: Lifestyle modification as foundation",
        "patient_specific_notes": "BMI 27.7; weight loss to target BMI < 25 would improve glycemic control."
      }
    ],
    "monitoring_plan": {
      "hba1c": "Repeat in 3 months",
      "fasting_glucose": "Weekly self-monitoring",
      "renal_function": "Annual screening",
      "eye_exam": "Annual dilated fundoscopy"
    },
    "generated_at": "2026-06-27T10:50:00Z"
  }
}
```

**Errors:**

| Status | Code | When |
|--------|------|------|
| 404 | `DIAGNOSIS_NOT_FOUND` | Invalid ICD-10 code |
| 501 | `NOT_IMPLEMENTED` | Phase 3 feature not yet available |

---

## 11. Clinical Suggestions

Clinical suggestions are the system's outputs (differentials, drug safety flags, management recommendations). They are **immutable** -- once created, they cannot be modified or deleted. Clinician decisions are **append-only**.

### 11.1 GET /patients/{patient_id}/suggestions

List all clinical suggestions for a patient, optionally filtered by encounter.

**Auth required:** Yes

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `encounter_id` | string | — | Filter by encounter |
| `type` | string | — | `differential`, `investigation`, `drug_safety`, `management` |
| `status` | string | — | `pending`, `accepted`, `overridden`, `deferred` |
| `sort` | string | `created_at` | Sort field |
| `order` | string | `desc` | `asc` or `desc` |
| `limit` | integer | 20 | Max 100 |
| `offset` | integer | 0 | Offset |

**Response (200 OK):**

```json
{
  "data": [
    {
      "id": "sug-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "patient_id": "c3d4e5f6...",
      "encounter_id": "enc-a1b2c3d4...",
      "type": "differential",
      "title": "Type 2 Diabetes Mellitus (E11)",
      "confidence": 0.88,
      "source_session_id": "rs-a1b2c3d4...",
      "decision_status": "accepted",
      "created_at": "2026-06-27T10:40:16Z"
    },
    {
      "id": "sug-b2c3d4e5-f6a7-8901-bcde-f23456789012",
      "patient_id": "c3d4e5f6...",
      "encounter_id": "enc-a1b2c3d4...",
      "type": "investigation",
      "title": "Fasting C-peptide",
      "confidence": null,
      "source_session_id": "rs-a1b2c3d4...",
      "decision_status": "pending",
      "created_at": "2026-06-27T10:40:16Z"
    }
  ],
  "pagination": {
    "total": 8,
    "limit": 20,
    "offset": 0
  }
}
```

---

### 11.2 GET /patients/{patient_id}/suggestions/{suggestion_id}

Get a single suggestion with full detail and agent trace.

**Auth required:** Yes

**Response (200 OK):**

```json
{
  "data": {
    "id": "sug-a1b2c3d4...",
    "patient_id": "c3d4e5f6...",
    "encounter_id": "enc-a1b2c3d4...",
    "type": "differential",
    "title": "Type 2 Diabetes Mellitus",
    "icd10_code": "E11",
    "confidence": 0.88,
    "detail": {
      "supporting_evidence": [
        {"finding": "FBG 126 mg/dL", "weight": "strong"},
        {"finding": "HbA1c 7.2%", "weight": "strong"}
      ],
      "against_evidence": [],
      "clinical_reasoning": "Classic presentation with biochemical confirmation..."
    },
    "agent_trace": {
      "agents_involved": ["diagnostician", "evidence_reviewer", "safety_checker"],
      "trace_steps": [
        {
          "agent": "diagnostician",
          "action": "hypothesis_formed",
          "detail": "Initial hypothesis based on presenting complaint and labs",
          "timestamp": "2026-06-27T10:40:05Z"
        },
        {
          "agent": "evidence_reviewer",
          "action": "confidence_revised",
          "detail": "Increased confidence from 0.82 to 0.88 based on HbA1c confirmation",
          "timestamp": "2026-06-27T10:40:10Z"
        }
      ]
    },
    "decisions": [
      {
        "decision_id": "dec-001",
        "action": "accepted",
        "decided_by": "b7e1c2d3...",
        "decided_at": "2026-06-27T10:50:00Z",
        "notes": "Agree with T2DM diagnosis. Initiating management."
      }
    ],
    "source_session_id": "rs-a1b2c3d4...",
    "created_at": "2026-06-27T10:40:16Z"
  }
}
```

**Note:** There is no `PUT` or `DELETE` on suggestions. Suggestions are immutable.

---

### 11.3 POST /patients/{patient_id}/suggestions/{suggestion_id}/decisions

Record a clinician decision on a suggestion. Decisions are append-only -- a new decision does not replace the old one; it creates a new record.

**Auth required:** Yes

**Request:**

```json
POST /api/v1/patients/{patient_id}/suggestions/{suggestion_id}/decisions
Content-Type: application/json

{
  "action": "accepted",
  "notes": "Agree with T2DM diagnosis. Will initiate lifestyle modification and continue metformin.",
  "modifications": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | Yes | `accepted`, `overridden`, `deferred`, `edited` |
| `notes` | string | No | Clinician's reasoning |
| `modifications` | object | No | Required if `action` is `edited`. Contains the modified fields. |

**Example -- overriding a suggestion:**

```json
{
  "action": "overridden",
  "notes": "Patient has strong preference against insulin. Will try triple OHA therapy first.",
  "override_reason": "patient_preference"
}
```

**Example -- editing a suggestion:**

```json
{
  "action": "edited",
  "notes": "Adjusting recommended dose based on renal function.",
  "modifications": {
    "dose": "500mg",
    "frequency": "OD",
    "reason": "eGFR 45 requires dose reduction"
  }
}
```

**Response (201 Created):**

```json
{
  "data": {
    "decision_id": "dec-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "suggestion_id": "sug-a1b2c3d4...",
    "action": "accepted",
    "notes": "Agree with T2DM diagnosis. Will initiate lifestyle modification and continue metformin.",
    "modifications": null,
    "decided_by": {
      "id": "b7e1c2d3...",
      "full_name": "Dr. Priya Sharma"
    },
    "decided_at": "2026-06-27T10:50:00Z"
  }
}
```

**Errors:**

| Status | Code | When |
|--------|------|------|
| 404 | `SUGGESTION_NOT_FOUND` | Suggestion does not exist |
| 422 | `INVALID_ACTION` | Invalid action value |
| 422 | `MODIFICATIONS_REQUIRED` | Action is `edited` but no `modifications` provided |

---

## 12. Audit

Every mutating operation is logged to an immutable audit trail.

### 12.1 GET /patients/{patient_id}/audit

Get audit trail for all actions on a patient.

**Auth required:** Yes

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `action_type` | string | — | Filter: `create`, `update`, `delete`, `decision`, `reasoning`, `drug_check`, `export` |
| `from_date` | string (datetime) | — | Start of date range |
| `to_date` | string (datetime) | — | End of date range |
| `actor_id` | string | — | Filter by user who performed the action |
| `sort` | string | `timestamp` | Sort field |
| `order` | string | `desc` | `asc` or `desc` |
| `limit` | integer | 50 | Max 200 |
| `page_token` | string | — | Cursor for pagination |

**Response (200 OK):**

```json
{
  "data": [
    {
      "id": "audit-001",
      "timestamp": "2026-06-27T10:50:00Z",
      "actor": {
        "id": "b7e1c2d3...",
        "full_name": "Dr. Priya Sharma",
        "email": "dr.sharma@clinic.in"
      },
      "action_type": "decision",
      "resource_type": "clinical_suggestion",
      "resource_id": "sug-a1b2c3d4...",
      "description": "Accepted suggestion: Type 2 Diabetes Mellitus (E11)",
      "details": {
        "decision_action": "accepted",
        "suggestion_type": "differential",
        "suggestion_title": "Type 2 Diabetes Mellitus"
      },
      "ip_address": "103.21.xx.xx",
      "user_agent": "AetherClinician/1.0 (Web)"
    },
    {
      "id": "audit-002",
      "timestamp": "2026-06-27T10:40:00Z",
      "actor": {
        "id": "b7e1c2d3...",
        "full_name": "Dr. Priya Sharma"
      },
      "action_type": "reasoning",
      "resource_type": "reasoning_session",
      "resource_id": "rs-a1b2c3d4...",
      "description": "Triggered differential reasoning for encounter enc-a1b2c3d4...",
      "details": {
        "reasoning_depth": "standard",
        "consult_id": "consult-a1b2c3d4..."
      }
    }
  ],
  "pagination": {
    "limit": 50,
    "next_page_token": "eyJsYXN0X2lkIjoiYXVkaXQtMDAyIn0="
  }
}
```

---

### 12.2 GET /suggestions/{suggestion_id}/audit

Get the audit trail for a specific clinical suggestion, including all decisions.

**Auth required:** Yes

**Response (200 OK):**

```json
{
  "data": {
    "suggestion_id": "sug-a1b2c3d4...",
    "suggestion_title": "Type 2 Diabetes Mellitus (E11)",
    "suggestion_type": "differential",
    "created_at": "2026-06-27T10:40:16Z",
    "trail": [
      {
        "id": "audit-sug-001",
        "timestamp": "2026-06-27T10:40:16Z",
        "action": "suggestion_created",
        "actor": "system",
        "detail": "Generated by reasoning session rs-a1b2c3d4..., confidence 0.88"
      },
      {
        "id": "audit-sug-002",
        "timestamp": "2026-06-27T10:50:00Z",
        "action": "decision_recorded",
        "actor": {
          "id": "b7e1c2d3...",
          "full_name": "Dr. Priya Sharma"
        },
        "detail": "Accepted. Notes: Agree with T2DM diagnosis."
      }
    ]
  }
}
```

---

### 12.3 GET /audit/export

Export the audit log as a downloadable file.

**Auth required:** Yes

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `patient_id` | string | — | Filter by patient (required unless exporting all) |
| `from_date` | string (datetime) | — | Start of date range |
| `to_date` | string (datetime) | — | End of date range |
| `format` | string | `json` | `json` or `csv` |

**Response (200 OK):**

```json
{
  "data": {
    "export_id": "exp-audit-a1b2c3d4...",
    "status": "ready",
    "download_url": "/api/v1/audit/export/exp-audit-a1b2c3d4.../download",
    "format": "json",
    "record_count": 156,
    "generated_at": "2026-06-27T11:00:00Z",
    "expires_at": "2026-06-27T12:00:00Z"
  }
}
```

---

### 12.4 GET /audit/export/{export_id}/download

Download a previously generated audit export file.

**Auth required:** Yes

**Response:** Binary file download with appropriate `Content-Type` and `Content-Disposition` headers.

---

## 13. Export

### 13.1 POST /patients/{patient_id}/encounters/{encounter_id}/export

Generate a clinician summary for an encounter.

**Auth required:** Yes

**Request:**

```json
POST /api/v1/patients/{patient_id}/encounters/{encounter_id}/export
Content-Type: application/json

{
  "format": "pdf",
  "sections": ["patient_summary", "intake", "differentials", "investigations", "drug_safety", "decisions", "management"],
  "include_agent_traces": false,
  "language": "en"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `format` | string | Yes | `pdf`, `json`, or `both` |
| `sections` | array of strings | No | Which sections to include. Default: all. |
| `include_agent_traces` | boolean | No | Include detailed agent reasoning traces. Default: `false` |
| `language` | string | No | `en` (default), `hi` (Hindi) |

**Response (202 Accepted):**

```json
{
  "data": {
    "export_id": "exp-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "status": "generating",
    "format": "pdf",
    "estimated_ready_seconds": 10,
    "download_url": "/api/v1/exports/exp-a1b2c3d4.../download"
  }
}
```

---

### 13.2 GET /exports/{export_id}

Check the status of an export.

**Auth required:** Yes

**Response (200 OK):**

```json
{
  "data": {
    "export_id": "exp-a1b2c3d4...",
    "status": "ready",
    "format": "pdf",
    "file_size_bytes": 524288,
    "download_url": "/api/v1/exports/exp-a1b2c3d4.../download",
    "generated_at": "2026-06-27T11:00:10Z",
    "expires_at": "2026-06-28T11:00:10Z"
  }
}
```

---

### 13.3 GET /exports/{export_id}/download

Download the generated export file.

**Auth required:** Yes

**Response:**

- `Content-Type: application/pdf` (for PDF) or `application/json` (for JSON)
- `Content-Disposition: attachment; filename="encounter_summary_2026-06-27.pdf"`

**Errors:**

| Status | Code | When |
|--------|------|------|
| 404 | `EXPORT_NOT_FOUND` | Export does not exist |
| 409 | `EXPORT_NOT_READY` | Export is still being generated |
| 410 | `EXPORT_EXPIRED` | Export download link has expired |

---

## 14. Real-Time Patterns (SSE / WebSocket)

### 14.1 Server-Sent Events (SSE)

SSE is used for two streaming use cases:

1. **Reasoning Theatre** -- Live agent state during differential reasoning
2. **Document Extraction** -- Live extraction progress

#### Connection

SSE endpoints use the `text/event-stream` content type. Since SSE connections are HTTP GET requests and cannot include an `Authorization` header from `EventSource`, the JWT token is passed as a query parameter:

```
GET /api/v1/.../stream?token=<access_token>
Accept: text/event-stream
```

#### Event Format

All SSE events follow this structure:

```
id: <monotonic_event_id>
event: <event_type>
data: <json_payload>
retry: 3000

```

The `id` field enables automatic reconnection. The client sends `Last-Event-ID` on reconnect and receives only missed events.

#### Reasoning Theatre Events

| Event Type | Description |
|------------|-------------|
| `session_started` | Reasoning session has begun, lists participating agents |
| `agent_state` | Agent state change (`thinking`, `reviewing`, `checking`, `consulting`) |
| `hypothesis_formed` | New hypothesis created by an agent |
| `hypothesis_revised` | Existing hypothesis confidence updated |
| `hypothesis_discarded` | Hypothesis dropped below threshold |
| `investigation_recommended` | Agent recommends an investigation |
| `safety_flag` | Drug safety agent raises a flag |
| `agent_error` | An agent encountered an error (graceful degradation) |
| `session_completed` | Reasoning is complete |
| `session_failed` | Reasoning failed (includes error details) |

#### Document Extraction Events

| Event Type | Description |
|------------|-------------|
| `extraction_started` | Processing has begun |
| `page_processed` | A page of the document has been processed |
| `field_extracted` | A single field has been extracted |
| `extraction_completed` | All extraction is done |
| `extraction_failed` | Extraction failed |

#### Heartbeat

The server sends a heartbeat comment every 15 seconds to keep the connection alive:

```
: heartbeat 2026-06-27T10:40:30Z

```

#### Reconnection

- The client should implement exponential backoff on connection failure.
- The `retry` field (in milliseconds) is the recommended reconnection interval.
- On reconnect, the server replays events since `Last-Event-ID`.
- Events are retained for 30 minutes after session completion.

#### Error Events

```
event: error
data: {"code": "SESSION_TIMEOUT", "message": "Reasoning session timed out after 120 seconds"}
```

### 14.2 WebSocket (Future Consideration)

WebSocket support is reserved for future features requiring bidirectional real-time communication (e.g., collaborative consults). The current SSE-based approach is sufficient for the unidirectional streaming needs of reasoning theatre and extraction progress.

If WebSocket is added:

- Endpoint: `wss://api.aetherclinician.in/api/v1/ws`
- Auth: JWT token in the first message after connection
- Protocol: JSON messages with `type` and `payload` fields
- Heartbeat: ping/pong frames every 30 seconds

---

## 15. Rate Limiting and Throttling

### 15.1 Rate Limit Tiers

| Endpoint Category | Limit | Window | Notes |
|-------------------|-------|--------|-------|
| Auth (login/signup) | 10 requests | 15 minutes | Per IP address |
| Auth (refresh) | 30 requests | 15 minutes | Per user |
| Read endpoints (GET) | 200 requests | 1 minute | Per user |
| Write endpoints (POST/PUT/DELETE) | 60 requests | 1 minute | Per user |
| Reasoning (trigger) | 10 requests | 1 minute | Per user; expensive compute |
| Drug safety check | 30 requests | 1 minute | Per user |
| File upload | 20 requests | 1 minute | Per user |
| Export generation | 5 requests | 1 minute | Per user |
| SSE connections | 5 concurrent | — | Per user |

### 15.2 Rate Limit Headers

Every response includes rate limit headers:

```
X-RateLimit-Limit: 200
X-RateLimit-Remaining: 195
X-RateLimit-Reset: 1719483660
```

### 15.3 Rate Limit Exceeded Response

```
HTTP/1.1 429 Too Many Requests
Retry-After: 45
Content-Type: application/json

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please retry after 45 seconds.",
    "details": {
      "limit": 200,
      "window_seconds": 60,
      "retry_after_seconds": 45
    }
  }
}
```

### 15.4 Demo Mode Limits

Demo accounts have reduced limits:

| Category | Limit |
|----------|-------|
| Patients | Max 10 |
| Documents per patient | Max 5 |
| Reasoning sessions per day | Max 20 |
| File upload size | Max 5 MB |

---

## 16. File Upload Specifications

### 16.1 Supported File Types

| Type | MIME Types | Max Size |
|------|-----------|----------|
| PDF | `application/pdf` | 20 MB |
| PNG | `image/png` | 10 MB |
| JPEG | `image/jpeg` | 10 MB |
| HEIC | `image/heic`, `image/heif` | 10 MB |

### 16.2 Upload Format

Files are uploaded as `multipart/form-data`:

```
POST /api/v1/patients/{patient_id}/documents
Content-Type: multipart/form-data; boundary=----FormBoundary

------FormBoundary
Content-Disposition: form-data; name="file"; filename="blood_report.pdf"
Content-Type: application/pdf

<binary data>
------FormBoundary
Content-Disposition: form-data; name="document_type"

lab_report
------FormBoundary
Content-Disposition: form-data; name="notes"

Fasting blood work from June 2026
------FormBoundary--
```

### 16.3 Validation Rules

1. **File type validation:** Server validates the actual file content (magic bytes), not just the extension or MIME type header.
2. **File size validation:** Checked before processing begins. Rejected with `400 FILE_TOO_LARGE`.
3. **Malware scanning:** Files are scanned before processing (future implementation).
4. **Image resolution:** Camera captures are accepted at any resolution but are downsampled to 300 DPI for OCR processing.

### 16.4 Upload Progress

For large files, the client can track upload progress via standard HTTP upload progress events. Post-upload extraction progress is tracked via SSE (Section 4.6).

---

## 17. Webhook / Event Patterns

> **Future extensibility.** Webhook delivery is not implemented in v1 but the event schema is defined for forward compatibility.

### 17.1 Event Types

| Event | Trigger |
|-------|---------|
| `document.extraction.completed` | Document extraction finished |
| `reasoning.session.completed` | Reasoning session finished |
| `drug_safety.critical_flag` | Critical drug safety flag raised |
| `suggestion.created` | New clinical suggestion generated |
| `export.ready` | Export file ready for download |

### 17.2 Webhook Payload Format

```json
{
  "event_id": "evt-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "event_type": "reasoning.session.completed",
  "timestamp": "2026-06-27T10:40:16Z",
  "data": {
    "reasoning_session_id": "rs-a1b2c3d4...",
    "patient_id": "c3d4e5f6...",
    "encounter_id": "enc-a1b2c3d4...",
    "differentials_count": 4,
    "top_diagnosis": "Type 2 Diabetes Mellitus (E11)",
    "top_confidence": 0.88
  },
  "metadata": {
    "api_version": "v1",
    "delivery_attempt": 1
  }
}
```

### 17.3 Webhook Registration (Future)

```json
POST /api/v1/webhooks
Content-Type: application/json

{
  "url": "https://clinic-ehr.example.com/hooks/aether",
  "events": ["reasoning.session.completed", "drug_safety.critical_flag"],
  "secret": "whsec_...",
  "active": true
}
```

### 17.4 Webhook Delivery

- **Retry policy:** 3 attempts with exponential backoff (1s, 10s, 60s).
- **Signature:** HMAC-SHA256 of the payload using the webhook secret, sent in `X-Aether-Signature` header.
- **Timeout:** 10 seconds per delivery attempt.

---

## 18. API Versioning Strategy

### 18.1 Version in URL Path

The API version is embedded in the URL path:

```
/api/v1/patients
/api/v2/patients   (future)
```

### 18.2 Version Lifecycle

| Phase | Duration | Description |
|-------|----------|-------------|
| **Current** | — | Active development, new features added |
| **Maintained** | 12 months after successor release | Bug fixes and security patches only |
| **Deprecated** | 6 months notice | `Sunset` header added to all responses |
| **Retired** | — | Returns `410 Gone` |

### 18.3 Deprecation Headers

When a version enters the deprecated phase:

```
Sunset: Sat, 27 Jun 2028 00:00:00 GMT
Deprecation: true
Link: <https://api.aetherclinician.in/api/v2/>; rel="successor-version"
```

### 18.4 Breaking vs. Non-Breaking Changes

**Non-breaking (no version bump):**
- Adding new optional fields to request bodies
- Adding new fields to response bodies
- Adding new endpoints
- Adding new query parameters
- Adding new enum values (when clients are expected to handle unknown values)

**Breaking (requires version bump):**
- Removing or renaming fields
- Changing field types
- Changing URL paths
- Changing required fields
- Removing endpoints
- Changing authentication mechanisms

---

## 19. Schema Definitions

All schema definitions use TypeScript-style interfaces for clarity. These map directly to Pydantic models in the FastAPI backend.

### 19.1 Core Types

```typescript
// Universal ID type
type UUID = string; // UUIDv4 format: "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

// Universal timestamp
type ISOTimestamp = string; // ISO 8601 UTC: "2026-06-27T10:30:00Z"

// Universal date
type ISODate = string; // ISO 8601 date: "2026-06-27"
```

### 19.2 Error Response

```typescript
interface ErrorResponse {
  error: {
    code: string;            // Machine-readable error code
    message: string;         // Human-readable message
    details?: Record<string, any>; // Additional context
  };
}
```

### 19.3 Pagination

```typescript
interface PaginationMeta {
  total?: number;             // Total count (omitted for cursor-based)
  limit: number;
  offset?: number;            // For offset-based
  next_page_token?: string;   // For cursor-based
}

interface PaginatedResponse<T> {
  data: T[];
  pagination: PaginationMeta;
}
```

### 19.4 Auth

```typescript
interface User {
  id: UUID;
  email: string;
  full_name: string;
  medical_license_number?: string;
  specialization?: "general_practice" | "internal_medicine" | "pediatrics" | "family_medicine" | "other";
  clinic_name?: string;
  is_demo: boolean;
  created_at: ISOTimestamp;
  last_login_at?: ISOTimestamp;
}

interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: "Bearer";
  expires_in: number; // seconds
}

interface SignupRequest {
  email: string;
  password?: string; // Not required if demo_mode is true
  full_name: string;
  medical_license_number?: string;
  specialization?: string;
  clinic_name?: string;
  demo_mode?: boolean;
}

interface LoginRequest {
  email: string;
  password?: string;
  demo_mode?: boolean;
}

interface LoginResponse {
  user: User;
  access_token: string;
  refresh_token: string;
  token_type: "Bearer";
  expires_in: number;
}
```

### 19.5 Patient

```typescript
interface Address {
  line1: string;
  line2?: string;
  city: string;
  state: string;
  pincode: string;
}

interface EmergencyContact {
  name: string;
  phone: string;
  relationship: string;
}

interface Patient {
  id: UUID;
  full_name: string;
  date_of_birth: ISODate;
  age: number; // Computed
  gender: "male" | "female" | "other";
  phone?: string;
  email?: string;
  address?: Address;
  blood_group?: "A+" | "A-" | "B+" | "B-" | "AB+" | "AB-" | "O+" | "O-";
  emergency_contact?: EmergencyContact;
  notes?: string;
  created_at: ISOTimestamp;
  updated_at: ISOTimestamp;
  created_by: UUID;
}

interface PatientListItem {
  id: UUID;
  full_name: string;
  date_of_birth: ISODate;
  age: number;
  gender: string;
  phone?: string;
  last_visit_at?: ISOTimestamp;
  created_at: ISOTimestamp;
}
```

### 19.6 Document

```typescript
type DocumentType = "lab_report" | "prescription" | "discharge_summary" | "imaging_report" | "referral_letter" | "insurance" | "other";
type ExtractionStatus = "queued" | "processing" | "completed" | "failed" | "needs_review";

interface Document {
  id: UUID;
  patient_id: UUID;
  document_type: DocumentType;
  source: "upload" | "camera" | "scan";
  filename: string;
  mime_type: string;
  file_size_bytes: number;
  notes?: string;
  extraction_status: ExtractionStatus;
  uploaded_at: ISOTimestamp;
  extracted_at?: ISOTimestamp;
  uploaded_by: UUID;
}

interface SourceRegion {
  page: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

interface ExtractedField {
  field_id: UUID;
  category: "lab_result" | "medication" | "diagnosis" | "vital" | "procedure" | "allergy" | "demographic" | "other";
  name: string;
  value: string;
  unit?: string;
  reference_range?: string;
  is_abnormal?: boolean;
  confidence: number; // 0.0 to 1.0
  needs_review: boolean;
  source_region?: SourceRegion;
  confirmed_by?: UUID;
  confirmed_at?: ISOTimestamp;
}

interface ExtractionResult {
  document_id: UUID;
  extraction_status: ExtractionStatus;
  extracted_at?: ISOTimestamp;
  confidence_score: number;
  fields: ExtractedField[];
  metadata: Record<string, any>;
}
```

### 19.7 Encounter

```typescript
type EncounterType = "outpatient" | "follow_up" | "emergency" | "telemedicine";
type EncounterStatus = "open" | "closed";

interface Vitals {
  blood_pressure_systolic?: number;
  blood_pressure_diastolic?: number;
  heart_rate?: number;
  temperature_celsius?: number;
  respiratory_rate?: number;
  spo2?: number;
  weight_kg?: number;
  height_cm?: number;
  bmi?: number; // Computed if weight and height provided
}

interface Encounter {
  id: UUID;
  patient_id: UUID;
  encounter_type: EncounterType;
  status: EncounterStatus;
  chief_complaint?: string;
  vitals?: Vitals;
  notes?: string;
  started_at: ISOTimestamp;
  ended_at?: ISOTimestamp;
  created_by: UUID;
}
```

### 19.8 Consult / Intake

```typescript
type ConsultStatus = "in_progress" | "completed" | "abandoned";
type QuestionType = "yes_no" | "single_choice" | "multi_choice" | "free_text" | "numeric" | "date";

interface QuestionOption {
  value: string;
  label: string;
}

interface IntakeQuestion {
  question_id: string;
  text: string;
  question_type: QuestionType;
  options?: QuestionOption[];
  clinical_context?: string;
  is_required: boolean;
}

interface IntakeAnswer {
  value: string | string[] | number;
  free_text?: string;
}

interface QuestionAnswer {
  question_id: string;
  text: string;
  answer: IntakeAnswer;
  answered_at: ISOTimestamp;
}

interface IntakeSummary {
  presenting_complaint: string;
  key_positives: string[];
  key_negatives: string[];
  risk_factors: string[];
}

interface ConsultSession {
  consult_id: UUID;
  encounter_id: UUID;
  patient_id: UUID;
  status: ConsultStatus;
  mode: "guided" | "quick";
  presenting_complaint: string;
  questions_and_answers: QuestionAnswer[];
  next_question?: IntakeQuestion | null;
  questions_asked: number;
  estimated_remaining: number;
  intake_summary?: IntakeSummary; // Present when status is "completed"
  started_at: ISOTimestamp;
  completed_at?: ISOTimestamp;
}
```

### 19.9 Reasoning

```typescript
type ReasoningStatus = "in_progress" | "completed" | "failed" | "timed_out";
type EvidenceWeight = "strong" | "moderate" | "supporting" | "weak";
type InvestigationPriority = "essential" | "recommended" | "optional";
type InvestigationUrgency = "stat" | "urgent" | "routine";

interface EvidenceItem {
  finding: string;
  weight: EvidenceWeight;
}

interface Differential {
  rank: number;
  hypothesis_id: string;
  diagnosis: string;
  icd10_code: string;
  confidence: number;
  supporting_evidence: EvidenceItem[];
  against_evidence: EvidenceItem[];
  clinical_reasoning: string;
}

interface InvestigationRecommendation {
  id: UUID;
  name: string;
  reason: string;
  priority: InvestigationPriority;
  urgency: InvestigationUrgency;
  estimated_cost_inr?: number;
  suggested_by_agent: string;
}

interface AgentTrace {
  steps: number;
  duration_ms: number;
  [key: string]: any; // Agent-specific metrics
}

interface ReasoningSession {
  reasoning_session_id: UUID;
  encounter_id: UUID;
  consult_id: UUID;
  status: ReasoningStatus;
  reasoning_depth: "quick" | "standard" | "deep";
  differentials: Differential[];
  recommended_investigations: InvestigationRecommendation[];
  agent_traces: Record<string, AgentTrace>;
  started_at: ISOTimestamp;
  completed_at?: ISOTimestamp;
  duration_seconds?: number;
}
```

### 19.10 Drug Safety

```typescript
type SafetyFlagType = "interaction" | "contraindication" | "allergy" | "dose_concern" | "renal_adjustment" | "hepatic_adjustment" | "pregnancy" | "age_related";
type SafetyFlagSeverity = "critical" | "warning" | "info";
type OverallSafetyStatus = "clear" | "info" | "warning" | "blocked";

interface SafetyFlag {
  id: UUID;
  type: SafetyFlagType;
  severity: SafetyFlagSeverity;
  title: string;
  description: string;
  is_hard_block: boolean;
  interacting_medication?: string;
  allergen?: string;
  reaction?: string;
  evidence_level?: "well_established" | "probable" | "theoretical";
  source: string;
}

interface DrugSafetyCheckResult {
  check_id: UUID;
  medication: {
    name: string;
    generic_name?: string;
    dose: string;
    frequency: string;
    route?: string;
  };
  overall_status: OverallSafetyStatus;
  is_blocked: boolean;
  flags: SafetyFlag[];
  checked_against: {
    current_medications: string[];
    allergies: string[];
    conditions: string[];
    recent_labs: Record<string, { value: number; date: ISODate }>;
  };
  checked_at: ISOTimestamp;
}
```

### 19.11 Clinical Suggestion

```typescript
type SuggestionType = "differential" | "investigation" | "drug_safety" | "management";
type DecisionAction = "accepted" | "overridden" | "deferred" | "edited";

interface ClinicalDecision {
  decision_id: UUID;
  action: DecisionAction;
  notes?: string;
  modifications?: Record<string, any>;
  override_reason?: string;
  decided_by: {
    id: UUID;
    full_name: string;
  };
  decided_at: ISOTimestamp;
}

interface AgentTraceStep {
  agent: string;
  action: string;
  detail: string;
  timestamp: ISOTimestamp;
}

interface ClinicalSuggestion {
  id: UUID;
  patient_id: UUID;
  encounter_id: UUID;
  type: SuggestionType;
  title: string;
  icd10_code?: string;
  confidence?: number;
  detail: Record<string, any>; // Type-specific detail
  agent_trace: {
    agents_involved: string[];
    trace_steps: AgentTraceStep[];
  };
  decisions: ClinicalDecision[];
  decision_status: "pending" | DecisionAction; // Most recent decision action
  source_session_id: UUID;
  created_at: ISOTimestamp;
}
```

### 19.12 Audit

```typescript
type AuditActionType = "create" | "update" | "delete" | "decision" | "reasoning" | "drug_check" | "export" | "login" | "logout";

interface AuditEntry {
  id: UUID;
  timestamp: ISOTimestamp;
  actor: {
    id: UUID;
    full_name: string;
    email?: string;
  } | "system";
  action_type: AuditActionType;
  resource_type: string;
  resource_id: UUID;
  description: string;
  details: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
}
```

### 19.13 Export

```typescript
type ExportStatus = "generating" | "ready" | "failed" | "expired";
type ExportFormat = "pdf" | "json" | "both";

interface ExportRequest {
  format: ExportFormat;
  sections?: string[];
  include_agent_traces?: boolean;
  language?: "en" | "hi";
}

interface ExportResult {
  export_id: UUID;
  status: ExportStatus;
  format: ExportFormat;
  file_size_bytes?: number;
  download_url: string;
  generated_at?: ISOTimestamp;
  expires_at?: ISOTimestamp;
}
```

### 19.14 Patient Record (Longitudinal)

```typescript
interface Medication {
  id: UUID;
  name: string;
  generic_name?: string;
  dose: string;
  frequency: string;
  route: string;
  started_at: ISODate;
  ended_at?: ISODate;
  prescribed_by?: string;
  reason_for_stopping?: string;
  source_document_id?: UUID;
  source_encounter_id?: UUID;
}

interface LabResult {
  id: UUID;
  name: string;
  value: number;
  unit: string;
  reference_range: string;
  is_abnormal: boolean;
  recorded_at: ISODate;
  source_document_id: UUID;
}

interface Condition {
  id: UUID;
  name: string;
  icd10_code: string;
  status: "active" | "resolved" | "chronic";
  onset_date?: ISODate;
  resolved_date?: ISODate;
  diagnosed_by?: string;
}

interface Allergy {
  id: UUID;
  allergen: string;
  type: "drug" | "food" | "environmental" | "other";
  severity: "mild" | "moderate" | "severe" | "life_threatening";
  reaction: string;
  reported_at: ISODate;
}

interface VitalRecord {
  id: UUID;
  recorded_at: ISOTimestamp;
  blood_pressure_systolic?: number;
  blood_pressure_diastolic?: number;
  heart_rate?: number;
  temperature_celsius?: number;
  respiratory_rate?: number;
  spo2?: number;
  weight_kg?: number;
  height_cm?: number;
  bmi?: number;
}

interface PatientRecord {
  patient_id: UUID;
  last_updated_at: ISOTimestamp;
  medications: {
    active: Medication[];
    past: Medication[];
  };
  labs: LabResult[];
  conditions: Condition[];
  allergies: Allergy[];
  vitals: VitalRecord[];
}

interface LabTrend {
  patient_id: UUID;
  marker: string;
  display_name: string;
  unit: string;
  reference_range: {
    low: number;
    high: number;
  };
  data_points: Array<{
    value: number;
    recorded_at: ISODate;
    source_document_id: UUID;
    is_abnormal: boolean;
  }>;
  trend_direction: "improving" | "stable" | "worsening" | "insufficient_data";
}
```

### 19.15 Management (Phase 3)

```typescript
type EvidenceGrade = "A" | "B" | "C" | "D" | "expert_opinion";

interface ManagementOption {
  id: UUID;
  category: "pharmacological" | "lifestyle" | "surgical" | "referral" | "monitoring";
  recommendation: string;
  evidence_grade: EvidenceGrade;
  guideline_source: string;
  guideline_citation: string;
  contraindications_for_patient: string[];
  patient_specific_notes: string;
}

interface MonitoringPlan {
  [test_name: string]: string; // e.g., "hba1c": "Repeat in 3 months"
}

interface ManagementResponse {
  diagnosis: {
    code: string;
    name: string;
  };
  patient_context: {
    patient_id: UUID;
    relevant_factors: string[];
  };
  management_options: ManagementOption[];
  monitoring_plan: MonitoringPlan;
  generated_at: ISOTimestamp;
}
```

---

## Appendix A: Complete Endpoint Reference

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| **Auth** | | | |
| POST | `/auth/signup` | Create account | No |
| POST | `/auth/login` | Login | No |
| POST | `/auth/refresh` | Refresh token | No |
| POST | `/auth/logout` | Logout | Yes |
| GET | `/auth/me` | Get current user | Yes |
| **Patients** | | | |
| POST | `/patients` | Create patient | Yes |
| GET | `/patients` | List patients | Yes |
| GET | `/patients/{patient_id}` | Get patient | Yes |
| PUT | `/patients/{patient_id}` | Update patient | Yes |
| DELETE | `/patients/{patient_id}` | Delete patient | Yes |
| **Documents** | | | |
| POST | `/patients/{patient_id}/documents` | Upload document | Yes |
| GET | `/patients/{patient_id}/documents` | List documents | Yes |
| GET | `/patients/{patient_id}/documents/{document_id}` | Get document | Yes |
| GET | `/patients/{patient_id}/documents/{document_id}/extraction` | Get extracted data | Yes |
| PUT | `/patients/{patient_id}/documents/{document_id}/extraction/fields/{field_id}` | Confirm/edit field | Yes |
| GET | `/patients/{patient_id}/documents/{document_id}/extraction/stream` | SSE extraction progress | Yes |
| **Patient Record** | | | |
| GET | `/patients/{patient_id}/record` | Get longitudinal record | Yes |
| GET | `/patients/{patient_id}/record/medications/timeline` | Get medication timeline | Yes |
| GET | `/patients/{patient_id}/record/labs/{marker}/trends` | Get lab trends | Yes |
| **Encounters** | | | |
| POST | `/patients/{patient_id}/encounters` | Create encounter | Yes |
| GET | `/patients/{patient_id}/encounters` | List encounters | Yes |
| GET | `/patients/{patient_id}/encounters/{encounter_id}` | Get encounter | Yes |
| PUT | `/patients/{patient_id}/encounters/{encounter_id}` | Update encounter | Yes |
| DELETE | `/patients/{patient_id}/encounters/{encounter_id}` | Delete encounter | Yes |
| **Intake / Consult** | | | |
| POST | `/patients/{patient_id}/encounters/{encounter_id}/consult` | Start consult | Yes |
| POST | `.../consult/{consult_id}/answers` | Submit answer | Yes |
| GET | `.../consult/{consult_id}` | Get consult status | Yes |
| POST | `.../consult/{consult_id}/skip` | Skip question | Yes |
| POST | `.../consult/{consult_id}/complete` | Force-complete | Yes |
| **Reasoning** | | | |
| POST | `.../encounters/{encounter_id}/reasoning` | Trigger reasoning | Yes |
| GET | `.../reasoning/{session_id}/stream` | SSE reasoning theatre | Yes |
| GET | `.../reasoning/{session_id}` | Get reasoning results | Yes |
| GET | `.../reasoning/{session_id}/investigations` | Get investigations | Yes |
| **Drug Safety** | | | |
| POST | `/patients/{patient_id}/drug-safety/check` | Check drug safety | Yes |
| GET | `/patients/{patient_id}/drug-safety/flags` | Get active flags | Yes |
| **Management** | | | |
| GET | `.../management/{diagnosis_code}` | Get management options | Yes |
| **Clinical Suggestions** | | | |
| GET | `/patients/{patient_id}/suggestions` | List suggestions | Yes |
| GET | `/patients/{patient_id}/suggestions/{suggestion_id}` | Get suggestion detail | Yes |
| POST | `.../suggestions/{suggestion_id}/decisions` | Record decision | Yes |
| **Audit** | | | |
| GET | `/patients/{patient_id}/audit` | Patient audit trail | Yes |
| GET | `/suggestions/{suggestion_id}/audit` | Suggestion audit trail | Yes |
| GET | `/audit/export` | Generate audit export | Yes |
| GET | `/audit/export/{export_id}/download` | Download audit export | Yes |
| **Export** | | | |
| POST | `.../encounters/{encounter_id}/export` | Generate export | Yes |
| GET | `/exports/{export_id}` | Check export status | Yes |
| GET | `/exports/{export_id}/download` | Download export | Yes |

---

## Appendix B: Error Code Reference

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Malformed request body or missing required fields |
| `INVALID_FILE_TYPE` | 400 | Unsupported file format |
| `FILE_TOO_LARGE` | 400 | File exceeds size limit |
| `UNAUTHORIZED` | 401 | Missing or invalid access token |
| `INVALID_CREDENTIALS` | 401 | Wrong email or password |
| `INVALID_REFRESH_TOKEN` | 401 | Refresh token expired or revoked |
| `FORBIDDEN` | 403 | Valid token but insufficient permissions |
| `PATIENT_NOT_FOUND` | 404 | Patient ID does not exist |
| `DOCUMENT_NOT_FOUND` | 404 | Document ID does not exist |
| `FIELD_NOT_FOUND` | 404 | Extracted field ID does not exist |
| `ENCOUNTER_NOT_FOUND` | 404 | Encounter ID does not exist |
| `SESSION_NOT_FOUND` | 404 | Reasoning session ID does not exist |
| `SUGGESTION_NOT_FOUND` | 404 | Suggestion ID does not exist |
| `EXPORT_NOT_FOUND` | 404 | Export ID does not exist |
| `MARKER_NOT_FOUND` | 404 | Unrecognized lab marker slug |
| `DIAGNOSIS_NOT_FOUND` | 404 | Invalid ICD-10 code |
| `EMAIL_ALREADY_EXISTS` | 409 | Email already registered |
| `PATIENT_DUPLICATE` | 409 | Duplicate patient detected |
| `PATIENT_HAS_ACTIVE_ENCOUNTERS` | 409 | Cannot delete patient with open encounters |
| `ENCOUNTER_HAS_REASONING` | 409 | Cannot delete encounter with reasoning sessions |
| `ENCOUNTER_CLOSED` | 409 | Cannot delete a closed encounter |
| `FIELD_ALREADY_CONFIRMED` | 409 | Extracted field was already confirmed |
| `SESSION_IN_PROGRESS` | 409 | Reasoning session is still running |
| `EXPORT_NOT_READY` | 409 | Export is still being generated |
| `EXPORT_EXPIRED` | 410 | Export download link has expired |
| `VALIDATION_ERROR` | 422 | Valid JSON but semantic validation failure |
| `WEAK_PASSWORD` | 422 | Password does not meet strength policy |
| `INVALID_ACTION` | 422 | Invalid decision action value |
| `MODIFICATIONS_REQUIRED` | 422 | Decision action is "edited" but no modifications provided |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `NOT_IMPLEMENTED` | 501 | Phase 3 feature not yet available |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
