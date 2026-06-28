# Security and Compliance

**Product:** Aether Clinician -- Clinician-Facing Diagnostic CDSS with Multi-Agent Reasoning  
**Version:** 1.0.0  
**Classification:** Confidential  
**Last Updated:** 2026-06-27  
**Owner:** Documedic Engineering & Compliance  
**Applicable Jurisdictions:** India  
**Regulatory Frameworks:** Digital Personal Data Protection (DPDP) Act 2023, CDSCO Software as a Medical Device (SaMD) Framework, Telemedicine Practice Guidelines 2020

---

## Table of Contents

1. [Security Overview and Threat Model](#1-security-overview-and-threat-model)
2. [Data Privacy -- DPDP Act 2023 Compliance](#2-data-privacy--dpdp-act-2023-compliance)
3. [Encryption](#3-encryption)
4. [CDSCO SaMD Regulatory Pathway](#4-cdsco-samd-regulatory-pathway)
5. [Patient Data Handling Rules](#5-patient-data-handling-rules)
6. [Audit Trail Requirements](#6-audit-trail-requirements)
7. [India Data Residency](#7-india-data-residency)
8. [Application Security](#8-application-security)
9. [Incident Response Plan](#9-incident-response-plan)
10. [Demo Build Security Posture](#10-demo-build-security-posture)
11. [Compliance Matrix](#11-compliance-matrix)

---

## 1. Security Overview and Threat Model

### 1.1 Security Principles

Aether Clinician processes sensitive patient health information (PHI) to provide diagnostic clinical decision support. Security is designed around five principles:

| Principle | Implementation |
|---|---|
| **Defence in depth** | Multiple independent security layers -- network, application, data, audit |
| **Least privilege** | Every component operates with the minimum permissions required |
| **Data minimisation** | Only data necessary for clinical reasoning is collected or transmitted |
| **Assume breach** | Immutable audit logs, hash-chained records, and tamper-evident storage ensure forensic capability |
| **Clinician sovereignty** | The clinician is always the decision-maker; the system is advisory only |

### 1.2 Threat Model

#### 1.2.1 Assets Under Protection

| Asset | Sensitivity | Storage |
|---|---|---|
| Patient health information (PHI) | Critical | PostgreSQL (encrypted), on-device (encrypted) |
| Patient personally identifiable information (PII) | Critical | PostgreSQL (encrypted) |
| Clinician account credentials | High | PostgreSQL (bcrypt-hashed) |
| Clinical reasoning outputs | High | PostgreSQL (immutable, hash-chained) |
| Agent traces and audit logs | High | PostgreSQL (append-only) |
| Guideline corpus | Medium | PostgreSQL + Qdrant |
| Drug vocabulary and interaction data | Medium | PostgreSQL |
| System configuration and secrets | High | Environment variables, no plaintext on disk |

#### 1.2.2 Threat Actors

| Actor | Motivation | Capability |
|---|---|---|
| External attacker | Data theft, ransomware | Network-based attacks, credential stuffing |
| Malicious insider | Data exfiltration | Authenticated access, potential admin privileges |
| Compromised LLM provider | Data leakage via API | Access to data sent in API calls |
| Regulatory auditor | Compliance verification | Authorised access to audit trails |
| Automated bot | Account enumeration, scraping | High-volume automated requests |

#### 1.2.3 Attack Surface

| Surface | Threats | Mitigations |
|---|---|---|
| **Nginx ingress** | DDoS, request smuggling, TLS downgrade | Rate limiting, TLS 1.3 only, request validation |
| **API endpoints** | Injection, broken auth, IDOR | Input validation, JWT auth, RBAC, RLS |
| **Claude API calls** | PHI exposure to third party | De-identification before transmission, contractual safeguards, minimal data principle |
| **PostgreSQL** | SQL injection, unauthorised access | Parameterised queries, TDE, RLS, network isolation |
| **Redis** | Session hijacking | AUTH required, network isolation, encrypted connections |
| **File uploads** | Malware, path traversal | Type validation, size limits, sandboxed processing |
| **On-device storage** | Data theft from lost device | Encrypted IndexedDB, no plaintext PHI |
| **Docker network** | Lateral movement | Internal-only networks, no exposed ports except Nginx |

#### 1.2.4 Trust Boundaries

```
                    UNTRUSTED                         TRUST BOUNDARY                         TRUSTED
                                                           |
    Internet / Browser  ----[TLS 1.3]----  Nginx  --------|--------  FastAPI  ----  PostgreSQL
                                                           |                   ----  Redis
                                                           |                   ----  Qdrant
                                                           |
    Claude API  --------[TLS 1.3 + de-id]-----------------|  (External, semi-trusted)
```

All inter-service communication occurs on Docker internal networks. Nginx is the sole external entry point. The Claude API is treated as a semi-trusted external dependency: data sent to it is de-identified, and no patient identifiers cross that boundary.

---

## 2. Data Privacy -- DPDP Act 2023 Compliance

The Digital Personal Data Protection Act 2023 governs processing of digital personal data in India. Aether Clinician processes sensitive personal data (health data) and must comply with all applicable provisions.

### 2.1 Data Classification

| Category | Examples | DPDP Classification | Handling |
|---|---|---|---|
| **PHI** | Diagnoses, medications, lab results, conditions, allergies, clinical notes | Sensitive personal data | Encrypted at rest and in transit, per-patient isolation, consent-gated, India residency |
| **PII** | Patient name, date of birth, gender, contact information | Personal data | Encrypted at rest and in transit, consent-gated, India residency |
| **Clinician data** | Name, email, credentials, practice details | Personal data | Encrypted at rest and in transit, consent-gated |
| **Clinical outputs** | Reasoning results, suggestions, agent traces | Derived sensitive data | Immutable, hash-chained, consent-inheriting from source PHI |
| **System data** | Logs, metrics, configuration | Non-personal | Standard security controls, no PHI in system logs |
| **Drug/guideline data** | Drug vocabulary, interactions, guideline corpus | Non-personal reference | Standard security controls |

### 2.2 Consent Management

The DPDP Act requires that personal data be processed only for lawful purposes with the informed consent of the data principal (patient).

#### 2.2.1 Consent Capture

- **Per-patient consent is mandatory** before any PHI processing begins.
- Consent is captured at patient registration via a clear, plain-language consent notice.
- The consent notice specifies:
  - Purpose of data processing (clinical decision support for the treating clinician).
  - Categories of data collected (medical history, medications, lab results, conditions, allergies).
  - Data retention period.
  - Rights of the data principal.
  - Identity and contact details of the data fiduciary.
  - Right to withdraw consent.
- Consent records are stored in the `patients` table with timestamp, version of consent notice, and method of capture.
- Consent is granular: separate consent for data processing and for transmission to the LLM provider.

#### 2.2.2 Consent Withdrawal

- Patients (via their clinician) may withdraw consent at any time.
- Withdrawal triggers:
  - Cessation of active data processing for that patient.
  - Marking of all patient records for retention-policy-governed deletion.
  - Audit log entry recording the withdrawal (the audit entry itself is retained for compliance).
- Withdrawal does not affect the lawfulness of processing performed prior to withdrawal.
- Clinical suggestions already accepted by the clinician are retained in the immutable audit trail (legal obligation) but the underlying PHI is scheduled for erasure.

### 2.3 Data Principal Rights

The DPDP Act grants data principals (patients) the following rights, implemented as follows:

| Right | Implementation | API Endpoint |
|---|---|---|
| **Right to access** | Patient data export in structured format (JSON/CSV) | `GET /api/v1/export/generate` |
| **Right to correction** | Clinician-mediated correction with audit trail | `PUT /api/v1/patients/{id}`, field-level updates |
| **Right to erasure** | Soft delete with retention-policy-governed hard delete; audit entries retained | `DELETE /api/v1/patients/{id}` |
| **Right to portability** | Full patient record export including documents, encounters, reasoning history | `GET /api/v1/export/download/{id}` |
| **Right to nominate** | Clinician acts as nominated representative | Consent management interface |
| **Right to grievance redressal** | In-application grievance submission; tracked to resolution | See Section 2.6 |

#### 2.3.1 Erasure Implementation

Erasure under the DPDP Act is handled through a three-stage process:

1. **Soft delete**: Patient record is marked `deleted_at = NOW()`. All associated data (encounters, documents, medications, lab results, conditions, allergies, reasoning sessions) inherits the soft-delete flag. Data is immediately excluded from all queries and processing.
2. **Retention hold**: Soft-deleted data is retained for the regulatory retention period (see Section 2.5) to satisfy legal and clinical-record obligations.
3. **Hard delete**: After the retention period expires, data is permanently and irreversibly deleted. Cryptographic keys for per-patient encryption (see Section 3.1.2) are destroyed, rendering any residual encrypted data unrecoverable.

Immutable audit log entries (clinical_suggestions, clinician_decisions) are retained indefinitely as they constitute the medico-legal record and do not contain raw PHI after the patient encryption keys are destroyed.

### 2.4 Data Fiduciary Obligations

As a data fiduciary under the DPDP Act, Documedic must:

| Obligation | Implementation |
|---|---|
| **Appoint a Data Protection Officer (DPO)** | DPO designated with contact details published in the application |
| **Implement reasonable security safeguards** | This document; encryption, access controls, audit trails |
| **Ensure data accuracy** | Source-linked extraction with confidence scores; clinician confirmation workflow |
| **Purpose limitation** | Data processed only for clinical decision support as stated in consent notice |
| **Storage limitation** | Retention periods defined and enforced (Section 2.5) |
| **Accountability** | Audit trails, compliance reporting, incident response plan |
| **Notify breaches to the Board** | Within 72 hours of discovery (Section 9.3) |
| **Conduct Data Protection Impact Assessment** | Completed before production deployment |

### 2.5 Data Retention and Disposal

| Data Category | Retention Period | Rationale | Disposal Method |
|---|---|---|---|
| Patient PHI (active) | Duration of clinical relationship + 3 years | Indian Medical Council regulations, standard medical record retention | Crypto-shredding (key destruction) |
| Patient PHI (soft-deleted) | 3 years from deletion request | Medico-legal retention requirement | Crypto-shredding |
| Clinical suggestions and decisions | 10 years | Medico-legal record; potential litigation window | Retained in audit log; PHI de-linked after patient data erasure |
| Agent traces | 5 years | Regulatory audit, post-market surveillance | Archived, then purged |
| Audit logs | 10 years | Compliance, medico-legal | Archived to cold storage, then purged |
| Clinician account data | Duration of account + 1 year | Account recovery, dispute resolution | Hard delete |
| System logs | 90 days | Operational debugging | Automatic rotation and deletion |
| Guideline corpus versions | Indefinite | Regulatory traceability (which guideline version informed which suggestion) | Archived, never deleted |
| Session data (Redis) | 7 days (refresh token lifetime) | Authentication | Automatic TTL expiry |

#### 2.5.1 Disposal Procedures

- **Crypto-shredding**: Per-patient encryption keys are destroyed, rendering all encrypted data for that patient permanently unrecoverable. This is the primary disposal mechanism for PHI.
- **Hard delete**: Database rows are permanently removed after the retention period. Cascading deletes ensure referential integrity.
- **Secure overwrite**: File-system-level data (uploaded documents) is overwritten before unlinking.
- **Backup purge**: Backup archives containing disposed data are cycled out within the backup retention window (30 days).

### 2.6 Grievance Redressal

- A grievance officer is appointed with published contact details (name, email, postal address).
- Grievances may be submitted through the application or via email.
- Acknowledgement is sent within 48 hours.
- Resolution target: 30 days from receipt.
- Escalation path: DPO, then the Data Protection Board of India.
- All grievances are logged with timestamps, status, and resolution details.

### 2.7 Cross-Border Data Transfer -- Claude API

The DPDP Act restricts transfer of personal data to jurisdictions not approved by the Central Government. The Claude API (Anthropic) is the sole external dependency.

#### 2.7.1 Mitigation Architecture

| Control | Description |
|---|---|
| **De-identification** | PHI sent to the Claude API is de-identified: patient names, dates of birth, and direct identifiers are replaced with tokens before transmission. Clinical data (symptoms, medications, lab values) is sent without direct identifiers. |
| **Minimal data** | Only the minimum data necessary for the specific reasoning task is included in each API call. |
| **No storage request** | API calls include directives that data should not be retained beyond the processing window. Anthropic's data retention policies are reviewed and documented. |
| **Contractual safeguards** | A Data Processing Agreement (DPA) with Anthropic governs data handling, specifying: no training on customer data, defined retention limits, breach notification obligations, audit rights. |
| **Audit trail** | Every API call is logged with a hash of the payload (not the payload itself) for traceability without duplicating PHI in logs. |
| **Fallback** | If regulatory guidance prohibits transfer to Anthropic's processing jurisdiction, the architecture supports switching to an India-hosted LLM provider without application changes (LLM provider is abstracted behind `LLMProviderConfig`). |

#### 2.7.2 Data Sent to Claude API

| Data Type | Sent? | De-identified? | Purpose |
|---|---|---|---|
| Patient name | No | N/A | Never transmitted |
| Date of birth | No | N/A | Age is sent instead |
| Gender | Yes | No (non-identifying alone) | Clinical relevance |
| Symptoms / chief complaint | Yes | Yes (identifiers removed) | Diagnostic reasoning |
| Medication list | Yes | Yes | Drug interaction context |
| Lab results | Yes | Yes | Clinical interpretation |
| Medical history | Yes | Yes | Differential diagnosis |
| Allergies | Yes | Yes | Safety checking |
| Clinician identity | No | N/A | Never transmitted |
| Patient contact info | No | N/A | Never transmitted |

---

## 3. Encryption

### 3.1 Encryption at Rest

#### 3.1.1 PostgreSQL Transparent Data Encryption (TDE)

- **Algorithm**: AES-256
- **Scope**: Full database cluster encryption. All data files, WAL files, and temporary files are encrypted on disk.
- **Key management**: TDE master key stored in environment variable, injected at container startup. Never written to disk in plaintext.
- **Performance**: Hardware-accelerated AES-NI on supported processors. Negligible performance impact.

#### 3.1.2 Application-Level Encryption (Per-Patient)

Above TDE, sensitive PHI fields receive a second layer of encryption at the application level:

- **Algorithm**: AES-256-GCM (authenticated encryption with associated data).
- **Scope**: Patient name, date of birth, contact information, and document content fields.
- **Key hierarchy** (envelope encryption):
  1. **Master Key (MK)**: Stored in KMS (or environment variable in demo). Never used directly for data encryption.
  2. **Patient Data Encryption Key (PDEK)**: Unique per patient. Generated at patient creation. Encrypted (wrapped) by the MK and stored in the `patients` table.
  3. **Field encryption**: Each sensitive field is encrypted with the patient's PDEK using a unique IV (initialisation vector) per encryption operation.
- **Crypto-shredding**: Deleting a patient's PDEK renders all their encrypted data permanently unrecoverable, regardless of whether the ciphertext is physically deleted.
- **Library**: Python `cryptography` library (FIPS-validated primitives where available).

#### 3.1.3 Qdrant Vector Store

- Guideline chunks stored in Qdrant contain no PHI. Only guideline text, metadata, and embedding vectors are stored.
- The Qdrant instance runs on the same Docker internal network, not exposed externally.
- Disk-level encryption via volume encryption on the host.

### 3.2 Encryption in Transit

| Path | Protocol | Minimum Version | Certificate |
|---|---|---|---|
| Browser to Nginx | TLS | 1.3 | CA-signed certificate (Let's Encrypt or equivalent) |
| Nginx to FastAPI | Plaintext (internal Docker network) | N/A | N/A (network-isolated) |
| FastAPI to PostgreSQL | TLS | 1.2 | Self-signed (internal) |
| FastAPI to Redis | TLS | 1.2 | Self-signed (internal) |
| FastAPI to Qdrant | Plaintext (internal Docker network) | N/A | N/A (network-isolated) |
| FastAPI to Claude API | TLS | 1.3 | Anthropic's CA-signed certificate |

- **Cipher suites**: Only AEAD cipher suites permitted (e.g., TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256).
- **HSTS**: Strict-Transport-Security header with max-age=31536000, includeSubDomains.
- **Certificate pinning**: Considered for Claude API calls in production.

### 3.3 On-Device Encryption

For the offline-capable PWA:

| Layer | Mechanism |
|---|---|
| **IndexedDB** | Encrypted using the Web Crypto API. AES-256-GCM with keys derived from the user's session. |
| **Local cache** | No plaintext PHI stored in localStorage, sessionStorage, or service worker caches. |
| **Memory** | Sensitive data cleared from JavaScript memory when components unmount. |
| **Key storage** | Encryption keys stored in IndexedDB are themselves wrapped with a key derived from the authentication token. Keys are invalidated on logout. |

### 3.4 Key Management

#### 3.4.1 Key Hierarchy

```
KMS / HSM (production) or Environment Variable (demo)
    |
    +-- Master Key (MK)
          |
          +-- Patient Data Encryption Key (PDEK) [per patient, wrapped by MK]
          |       |
          |       +-- Field-level encryption (AES-256-GCM, unique IV per operation)
          |
          +-- TDE Key (managed by PostgreSQL)
          |
          +-- JWT Signing Key (HS256)
          |
          +-- Redis AUTH Password
```

#### 3.4.2 Key Lifecycle

| Event | Procedure |
|---|---|
| **Key generation** | Cryptographically secure random generation (os.urandom / secrets module) |
| **Key rotation** | MK rotation: re-wrap all PDEKs with new MK. JWT key rotation: dual-key validation during transition window. |
| **Key revocation** | Immediate effect; affected sessions invalidated. |
| **Key destruction** | Secure zeroing of memory; deletion from KMS/environment. |
| **Key backup** | Encrypted backup of MK to separate secure storage. PDEKs are recoverable from database (wrapped form). |

#### 3.4.3 Production KMS Considerations

For production deployment:
- AWS KMS (Mumbai region, ap-south-1) or Azure Key Vault (Central India) for master key management.
- Hardware Security Module (HSM) backing for the master key.
- Key access policies enforced via IAM roles with MFA.
- Key usage logging via CloudTrail / Azure Monitor.
- Annual key rotation schedule for the master key.

### 3.5 No Plaintext Keys Rule

**Absolute rule: No cryptographic key, password, or secret may exist in plaintext on disk at any time.**

| Secret Type | Storage Method |
|---|---|
| Master encryption key | KMS (production) / Environment variable (demo, injected at runtime) |
| Database password | Environment variable, injected at container startup |
| JWT signing key | Environment variable |
| Redis AUTH password | Environment variable |
| Claude API key | Environment variable |
| Patient encryption keys (PDEKs) | Encrypted (wrapped) in database |
| Clinician passwords | bcrypt-hashed (cost factor 12), never stored in reversible form |

- `.env` files are excluded from version control via `.gitignore`.
- Docker secrets or Kubernetes secrets used in production.
- No secrets in Docker images, Dockerfiles, or docker-compose files.
- CI/CD pipelines use dedicated secret management (e.g., GitHub Actions secrets).

---

## 4. CDSCO SaMD Regulatory Pathway

### 4.1 SaMD Classification

#### 4.1.1 Classification Rationale

Under the CDSCO Medical Device Rules 2017 (as amended) and the IMDRF SaMD risk framework:

| Factor | Assessment |
|---|---|
| **Intended use** | Provide diagnostic clinical decision support to primary-care clinicians |
| **State of healthcare situation** | Non-serious to serious (primary care differential diagnosis) |
| **Significance to healthcare decision** | Drives clinical management (informs treatment decisions) |
| **IMDRF risk category** | Category II-III (depending on specific use case) |
| **Expected CDSCO class** | Class B (moderate risk) to Class C (moderate-high risk) |

#### 4.1.2 Classification Justification

- **Class B** applies when the software informs clinical management for non-serious conditions (e.g., suggesting investigation for suspected vitamin deficiency).
- **Class C** applies when the software informs clinical management for serious conditions (e.g., flagging potential cardiac events).
- The system's autonomy tiers (Informational, Suggestive, Flag-for-review) are designed to keep the clinician as the decision-maker, which may support a Class B classification for the initial scope.
- Final classification is determined by CDSCO upon review of the intended-use statement and clinical evidence.

### 4.2 Registration Process Overview

| Phase | Activity | Estimated Duration |
|---|---|---|
| 1. Pre-submission | Informal consultation with CDSCO; classification confirmation | 2-3 months |
| 2. Application preparation | Compile technical file, clinical evidence, QMS documentation | 3-6 months |
| 3. Application submission | Submit Form MD-14 (Class B) or Form MD-15 (Class C) to CDSCO | 1 month |
| 4. Review | CDSCO technical review; potential queries and responses | 6-12 months |
| 5. Registration | Registration certificate issued | Upon approval |
| 6. Post-market | Ongoing surveillance, periodic reporting | Continuous |

### 4.3 Quality Management System (QMS)

A QMS aligned with ISO 13485:2016 (Medical devices -- Quality management systems) is required. The QMS covers:

| QMS Element | Implementation |
|---|---|
| **Document control** | Versioned documentation in the repository; change-controlled release process |
| **Design controls** | Requirements traceability matrix (spec to implementation to test); design reviews at phase gates |
| **Risk management** | ISO 14971:2019 risk management process; risk register maintained |
| **Software lifecycle** | IEC 62304:2006+A1:2015 (Medical device software -- Software life cycle processes) |
| **SOUP management** | All third-party dependencies catalogued with risk assessment |
| **Verification and validation** | Automated test suites; clinical validation studies |
| **CAPA (Corrective and Preventive Action)** | Issue tracking with root cause analysis; trend monitoring |
| **Management review** | Quarterly QMS review meetings |
| **Training** | Developer training on medical device software requirements |
| **Supplier management** | Anthropic (Claude API) assessed as critical supplier |

### 4.4 Clinical Validation Requirements

| Requirement | Approach |
|---|---|
| **Analytical validation** | Automated tests verifying extraction accuracy, reasoning consistency, safety checks (allergy blocking, contraindication detection) |
| **Clinical validation** | Prospective study with primary-care clinicians comparing CDSS-assisted vs. unassisted diagnostic accuracy |
| **Usability validation** | IEC 62366-1:2015 usability engineering; formative and summative usability studies |
| **Safety validation** | Systematic testing of all safety mechanisms (verifier, hard blocks, autonomy tiers, anti-automation-bias) |
| **Performance validation** | Response time, availability, and throughput under expected clinical loads |

### 4.5 Post-Market Surveillance Plan

| Activity | Frequency | Method |
|---|---|---|
| **Adverse event monitoring** | Continuous | In-application reporting mechanism; clinician feedback |
| **Complaint handling** | Continuous | Tracked complaints with CAPA integration |
| **Field Safety Corrective Actions (FSCA)** | As needed | Notification to CDSCO and affected users |
| **Periodic Safety Update Reports (PSUR)** | Annual | Aggregated safety and performance data |
| **Trend analysis** | Quarterly | Analysis of diagnostic accuracy, safety events, user feedback |
| **Literature review** | Semi-annual | Review of relevant medical literature and guideline updates |
| **Proactive risk monitoring** | Continuous | Automated monitoring of reasoning accuracy metrics, safety check triggering rates |

### 4.6 Required Artifacts and Build Integration

The build process produces, from day one, the artifacts a SaMD submission requires:

| Artifact | How the Build Produces It | Storage |
|---|---|---|
| **Clinical output traceability** | Every `ClinicalSuggestion` links to its evidence sources via `source_links` and `evidence_quality`. The reasoning session records the full agent trace. | `clinical_suggestions` table, `reasoning_sessions.agent_trace` |
| **Complete audit trail** | Immutable, hash-chained audit log captures every clinical output, every clinician decision (accept/override/defer), and every agent interaction. | `clinical_suggestions`, `clinician_decisions`, `clinical_audit_log` tables |
| **Versioned guideline corpora** | `guideline_documents` table tracks version, publication date, source authority. `guideline_chunks` links each chunk to its parent document. Embeddings are re-generated on version update. | `guideline_documents`, `guideline_chunks` tables, Qdrant |
| **Exportable validation logs** | Audit export API (`POST /api/v1/export/generate`) produces timestamped, complete exports in JSON and CSV formats. | `patient_exports` table, file storage |
| **Requirements traceability matrix** | Maintained in documentation; maps spec requirements to implementation modules to test cases. | Repository documentation |
| **Risk register** | Maintained as a living document; updated at each design review. | Repository documentation |
| **Test reports** | Automated test suites produce structured reports on every CI run. | CI/CD artifacts |
| **Software Bill of Materials (SBOM)** | Generated automatically from dependency files (pyproject.toml, package.json). | CI/CD artifacts |

### 4.7 Telemedicine Practice Guidelines (2020) Alignment

When used in a teleconsultation context, Aether Clinician complies with the Telemedicine Practice Guidelines 2020 issued by the Board of Governors (in supersession of the Medical Council of India):

| Guideline Requirement | Compliance Measure |
|---|---|
| **Registered Medical Practitioner (RMP) only** | Only clinicians (RMPs) may use the system for patient care. Demo build removes the credential gate but displays a persistent banner. Production build enforces credential verification. |
| **Patient consent for teleconsultation** | Consent capture includes teleconsultation-specific consent when applicable. |
| **Patient identification** | Patient identity verified and recorded by the treating clinician. |
| **Documentation** | Complete encounter documentation maintained in the system with full audit trail. |
| **Prescription guidelines** | The system does not generate prescriptions; it provides decision support. Prescriptions remain the clinician's responsibility via the appropriate telemedicine platform. |
| **Technology requirements** | Secure communication channels (TLS 1.3), data privacy, and auditability are built in. |
| **Record maintenance** | Minimum 3-year retention of teleconsultation records. |
| **Jurisdiction** | The system is designed for use within India; data residency enforced. |

---

## 5. Patient Data Handling Rules

### 5.1 Minimum Necessary Principle

Every data access and processing operation adheres to the minimum necessary principle:

| Context | Rule |
|---|---|
| **API responses** | Endpoints return only the fields required for the requesting view. List endpoints exclude detailed clinical data. |
| **LLM API calls** | Only the minimum clinical context required for the specific reasoning task is included. Patient identifiers are never sent. |
| **Agent processing** | Each agent in the 8-agent reasoning engine receives only the `CaseState` fields relevant to its task. |
| **Logging** | System logs never contain PHI. Clinical audit logs contain structured references (IDs), not raw PHI. |
| **Error messages** | Error responses never leak PHI or internal system details. |
| **Analytics** | Only de-identified, aggregated data used for system performance analytics. |

### 5.2 De-Identification for Analytics

When patient data is used for system analytics, performance monitoring, or quality improvement:

- **Direct identifiers removed**: Name, date of birth, contact information, and any unique identifiers.
- **Quasi-identifiers generalised**: Age rounded to 5-year bands, dates shifted, location generalised.
- **K-anonymity**: De-identified datasets maintain k >= 5 (at least 5 records share any combination of quasi-identifiers).
- **No re-identification**: Re-identification of de-identified data is prohibited by policy and technically infeasible after crypto-shredding.

### 5.3 PHI in LLM API Calls

| Aspect | Policy |
|---|---|
| **What is sent** | De-identified clinical context: symptoms, medications (generic names), lab values, medical history, allergies. Age and gender are sent. See Section 2.7.2 for the complete matrix. |
| **What is never sent** | Patient name, date of birth, contact information, clinician identity, patient identifiers, system-internal IDs. |
| **De-identification method** | Automated pre-processing pipeline strips identifiers before API call construction. Regex-based and NER-based identifier detection. |
| **Anthropic retention policy** | Anthropic does not train on API customer data. Data retention is governed by the DPA. API inputs/outputs are retained by Anthropic for a limited abuse-monitoring window, then deleted. |
| **Audit** | Each API call is logged with: timestamp, reasoning session ID, hash of the request payload, response metadata. The actual payload is not logged (to avoid PHI duplication). |
| **Fallback** | If the Claude API is unavailable, the system degrades to offline safety checks (drug interactions, allergy checks) without LLM-powered reasoning. |

### 5.4 Data Isolation

#### 5.4.1 Per-Account Isolation

- Each clinician account has access only to patients they have created.
- Row-Level Security (RLS) policies on PostgreSQL enforce that every query is scoped to the authenticated clinician's `account_id`.
- RLS policies are defined on all patient-related tables: `patients`, `encounters`, `documents`, `medication_events`, `lab_results`, `conditions`, `allergies`, `derived_markers`, `reasoning_sessions`, `clinical_suggestions`, `clinician_decisions`, `intake_questions`, `intake_answers`, `drug_safety_checks`, `patient_exports`.

#### 5.4.2 Per-Patient Isolation

- Per-patient encryption keys (PDEKs) provide cryptographic isolation: even if RLS is bypassed, data remains encrypted with a key that is only accessible to the authorised account.
- Patient data cannot be aggregated across accounts without the cooperation of each account holder.

#### 5.4.3 RLS Policy Structure

```sql
-- Example: patients table RLS
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
CREATE POLICY patients_account_isolation ON patients
    USING (account_id = current_setting('app.current_account_id')::uuid);

-- Applied consistently across all patient-related tables
-- Policies enforce: SELECT, INSERT, UPDATE, DELETE all scoped to account_id
-- Superuser/migration roles bypass RLS only during schema migrations
```

### 5.5 Access Controls (RBAC)

| Role | Permissions | Assignment |
|---|---|---|
| **Clinician** | Full CRUD on own patients; trigger reasoning; view/accept/override suggestions; export data | Default role on account creation |
| **System** | Read-only access to all data for audit export; no clinical operations | Internal service accounts |
| **Migration** | Schema changes only; no data access | CI/CD pipeline |

In the demo build, there is a single role (Clinician) since the credential wall is removed. The RBAC infrastructure is fully implemented and enforced; only the credential verification at signup is bypassed.

### 5.6 Row-Level Security in PostgreSQL

RLS is implemented as the primary data isolation mechanism:

| Table | RLS Policy | Enforcement |
|---|---|---|
| `patients` | `account_id = current_account` | All operations |
| `encounters` | Via `patient_id` join to `patients` | All operations |
| `documents` | Via `patient_id` join to `patients` | All operations |
| `medication_events` | Via `patient_id` join to `patients` | All operations |
| `lab_results` | Via `patient_id` join to `patients` | All operations |
| `conditions` | Via `patient_id` join to `patients` | All operations |
| `allergies` | Via `patient_id` join to `patients` | All operations |
| `derived_markers` | Via `patient_id` join to `patients` | All operations |
| `reasoning_sessions` | Via `encounter_id` -> `patient_id` -> `account_id` | All operations |
| `clinical_suggestions` | Via `reasoning_session_id` chain to `account_id` | SELECT only (immutable) |
| `clinician_decisions` | Via `suggestion_id` chain to `account_id` | SELECT, INSERT only (immutable) |
| `intake_questions` | Via `encounter_id` chain to `account_id` | All operations |
| `intake_answers` | Via `question_id` chain to `account_id` | All operations |
| `drug_safety_checks` | Via `encounter_id` chain to `account_id` | All operations |
| `patient_exports` | Via `patient_id` -> `account_id` | All operations |

- `pgaudit` extension is enabled to log all SQL statements for compliance auditing.
- The application database user has no SUPERUSER or BYPASSRLS privileges.

---

## 6. Audit Trail Requirements

### 6.1 Immutable ClinicalSuggestion Logging

Every clinical output generated by the reasoning engine is stored as an immutable record:

| Field | Description |
|---|---|
| `id` | UUID, primary key |
| `reasoning_session_id` | Link to the reasoning session that produced this suggestion |
| `suggestion_type` | `diagnosis`, `investigation`, `management`, `safety_flag` |
| `title` | Short title of the suggestion |
| `detail` | Full clinical detail with citations |
| `evidence_quality` | `high`, `moderate`, `low`, `very_low` |
| `confidence_score` | 0.0 to 1.0, rendered as uncertainty when low |
| `autonomy_tier` | `informational`, `suggestive`, `flag_for_review` |
| `source_links` | JSONB array of evidence source references |
| `agent_id` | Which agent produced this suggestion |
| `verification_status` | `verified`, `modified_by_verifier`, `blocked` |
| `created_at` | Timestamp, set once, never modified |

**Immutability enforcement** (three layers):

1. **Database trigger**: A `BEFORE UPDATE OR DELETE` trigger on `clinical_suggestions` raises an exception, preventing any modification or deletion.
2. **Application policy**: The repository layer exposes only `INSERT` and `SELECT` methods. No `UPDATE` or `DELETE` methods exist.
3. **Database permissions**: The application database role has only `INSERT` and `SELECT` grants on `clinical_suggestions`. No `UPDATE` or `DELETE` grants.

### 6.2 Agent Trace Preservation

Every reasoning session stores the complete agent execution trace:

```json
{
  "session_id": "uuid",
  "trigger": "manual | automatic",
  "started_at": "ISO8601",
  "completed_at": "ISO8601",
  "phases": [
    {
      "phase": "intake_analysis",
      "agent": "intake_synthesiser",
      "started_at": "ISO8601",
      "completed_at": "ISO8601",
      "inputs_hash": "sha256",
      "outputs_summary": "...",
      "tool_calls": [
        {"tool": "search_guidelines", "query": "...", "results_count": 5}
      ]
    }
  ],
  "verifier_trace": {
    "disagreements": [...],
    "resolutions": [...],
    "conservative_overrides": [...]
  },
  "safety_checks": {
    "allergy_blocks": [...],
    "contraindication_blocks": [...],
    "interaction_warnings": [...]
  }
}
```

- Agent traces are stored in the `reasoning_sessions.agent_trace` JSONB column.
- Traces include every agent's inputs (hashed), outputs, tool calls, and the verifier's complete decision log.
- No PHI is stored in agent traces; clinical data is referenced by ID.

### 6.3 Clinician Decision Logging

Every clinician interaction with a clinical suggestion is immutably recorded:

| Field | Description |
|---|---|
| `id` | UUID, primary key |
| `suggestion_id` | Link to the clinical suggestion |
| `decision` | `accepted`, `overridden`, `deferred` |
| `override_reason` | Free-text reason (required when decision = `overridden`) |
| `decided_at` | Timestamp of the decision |
| `decided_by` | Account ID of the clinician |

**Immutability enforcement**: Same three-layer approach as `clinical_suggestions` (trigger, application policy, database permissions).

**Override audit**: When a clinician overrides a suggestion (particularly a safety flag), the override reason is mandatory and the event is flagged for periodic review in compliance reporting.

### 6.4 Tamper Evidence -- Hash Chaining

Audit log entries are hash-chained to provide tamper evidence:

```
Record N:
  content_hash = SHA-256(record_data)
  chain_hash   = SHA-256(content_hash + Record[N-1].chain_hash)
```

| Property | Detail |
|---|---|
| **Algorithm** | SHA-256 |
| **Chain scope** | Per-patient chain (each patient has an independent hash chain) |
| **Genesis record** | First record in a chain uses a well-known genesis hash |
| **Verification** | `GET /api/v1/audit/patient/{id}` returns the chain; any client can verify integrity by recomputing hashes |
| **Breakage detection** | If any record is modified or deleted, all subsequent chain hashes become invalid |
| **Performance** | Hash computation is done at INSERT time; chain verification is O(n) in chain length |

### 6.5 Export Formats

Audit data is exportable in two formats:

| Format | Use Case | Contents |
|---|---|---|
| **JSON** | Machine-readable, regulatory submission, system integration | Complete structured data including agent traces, hash chains, source links |
| **CSV** | Human-readable, spreadsheet analysis, quick review | Flattened tabular data; complex fields (JSONB) serialised as strings |

Export is triggered via `POST /api/v1/export/generate` with parameters for date range, data scope, and format. The export job runs asynchronously and produces a downloadable file.

**Non-negotiable**: The download-all and audit-export functions must never fail. They are implemented with retry logic, chunked processing for large datasets, and fallback to synchronous generation if the async pipeline is unavailable.

### 6.6 Retention Periods

| Audit Data Type | Retention | Rationale |
|---|---|---|
| Clinical suggestions | 10 years | Medico-legal record |
| Clinician decisions | 10 years | Medico-legal record |
| Agent traces | 5 years | Regulatory audit, post-market surveillance |
| Hash chain records | 10 years (aligned with clinical data) | Tamper evidence for the medico-legal record |
| Access logs (pgaudit) | 1 year | Security monitoring |
| API call audit logs | 3 years | Compliance, incident investigation |

### 6.7 Compliance Reporting

| Report | Frequency | Contents |
|---|---|---|
| **Safety event summary** | Monthly | Count of allergy blocks, contraindication blocks, verifier overrides, clinician overrides of safety flags |
| **Override analysis** | Quarterly | Analysis of clinician overrides with reasons; trend identification |
| **Data access report** | Quarterly | Summary of data access patterns; anomaly detection |
| **Audit integrity check** | Monthly | Automated verification of all hash chains; report of any broken chains |
| **Regulatory submission package** | On demand | Complete audit trail for a specified patient and date range, with chain verification certificate |

---

## 7. India Data Residency

### 7.1 Infrastructure Requirements

**All patient health information (PHI) and personally identifiable information (PII) must remain within the territory of India at all times.**

| Requirement | Implementation |
|---|---|
| **Compute** | All application services (FastAPI, Nginx, Redis, Qdrant) run on infrastructure physically located in India. |
| **Database** | PostgreSQL instance hosted in India. No cross-region replication outside India. |
| **Backups** | All database backups stored in India. No backup data leaves the country. |
| **File storage** | Uploaded documents and generated exports stored on India-located storage. |
| **CDN** | Static assets (frontend bundle) may be served from a CDN with Indian edge nodes. No PHI transits the CDN. |
| **Logs** | Application and audit logs stored in India. |

### 7.2 Cloud Provider Selection

| Provider Option | Region | Services |
|---|---|---|
| **AWS** | ap-south-1 (Mumbai) | EC2, RDS (PostgreSQL), S3, KMS, CloudWatch |
| **Azure** | Central India (Pune) / South India (Chennai) | Virtual Machines, Azure Database for PostgreSQL, Blob Storage, Key Vault |
| **Google Cloud** | asia-south1 (Mumbai) / asia-south2 (Delhi) | Compute Engine, Cloud SQL (PostgreSQL), Cloud Storage, Cloud KMS |
| **Indian providers** | Various (CtrlS, Yotta, NxtGen) | Colocation / managed hosting |

Selection criteria:
- Data residency guarantees (contractual and technical).
- SOC 2 Type II and ISO 27001 certification for the India region.
- MEITY empanelment (for government health data, if applicable).
- KMS / HSM availability in the India region.
- Compliance with DPDP Act data localisation requirements as they evolve.

### 7.3 Claude API Data Processing Considerations

The Claude API is the sole exception to strict India data residency:

| Consideration | Mitigation |
|---|---|
| **Processing location** | Anthropic may process API calls outside India. Data is de-identified before transmission (see Section 2.7). |
| **Data in transit** | TLS 1.3 encryption for all API calls. |
| **Data at rest** | Anthropic retains API data only for a limited abuse-monitoring window per their DPA. No permanent storage. |
| **Contractual safeguards** | DPA specifies data handling obligations, breach notification, and audit rights. |
| **Regulatory risk** | If the DPDP Act or subsequent rules prohibit transfer of even de-identified health data, the system architecture supports migration to an India-hosted LLM (the LLM provider is abstracted behind `LLMProviderConfig`). |
| **Alternative providers** | India-hosted LLM options (e.g., Krutrim, Bhashini-integrated models, self-hosted open-source models) evaluated as contingencies. |

### 7.4 Backup and Disaster Recovery Within India

| Component | Backup Strategy | DR Strategy |
|---|---|---|
| **PostgreSQL** | Daily full backup + continuous WAL archiving. Stored in India-region object storage (e.g., S3 ap-south-1). 30-day retention. | Read replica in a second Indian availability zone. Automated failover. RPO: < 1 minute. RTO: < 15 minutes. |
| **Qdrant** | Daily snapshot. Stored in India-region object storage. | Rebuild from guideline corpus (source of truth is PostgreSQL). RTO: < 1 hour. |
| **Redis** | No backup (ephemeral session data). | Restart with empty state; users re-authenticate. |
| **File storage** | Replicated across availability zones within India. | Cross-AZ replication. |
| **Application state** | Stateless containers; no backup needed. | Redeployment from container registry. RTO: < 5 minutes. |

### 7.5 Data Sovereignty Compliance

| Measure | Description |
|---|---|
| **Infrastructure audit** | Annual audit confirming all infrastructure components are physically located in India. |
| **Network controls** | Firewall rules prevent data egress to non-Indian destinations (except the Claude API endpoint). |
| **Data flow mapping** | Documented data flow diagram showing all data paths, confirming India residency. Updated on every architecture change. |
| **Contractual requirements** | Cloud provider contracts include data residency clauses with financial penalties for violations. |
| **Monitoring** | Automated alerts if any service attempts to connect to non-approved external endpoints. |

---

## 8. Application Security

### 8.1 Authentication Security

#### 8.1.1 Password Handling

| Control | Implementation |
|---|---|
| **Hashing algorithm** | bcrypt with cost factor 12 (adaptive: increased as hardware improves) |
| **Password requirements** | Minimum 8 characters, at least one uppercase, one lowercase, one digit, one special character |
| **Brute-force protection** | Account lockout after 5 failed attempts (15-minute lockout); rate limiting on auth endpoints |
| **Password storage** | Only the bcrypt hash is stored; plaintext passwords are never logged, cached, or stored |
| **Credential stuffing** | Rate limiting per IP; CAPTCHA after repeated failures (production) |

#### 8.1.2 JWT Implementation

| Parameter | Value | Rationale |
|---|---|---|
| **Algorithm** | HS256 | Symmetric signing; sufficient for single-service architecture |
| **Access token lifetime** | 15 minutes | Limits exposure window if token is compromised |
| **Refresh token lifetime** | 7 days | Balances security with user convenience |
| **Token storage (client)** | httpOnly, Secure, SameSite=Strict cookies | Prevents XSS-based token theft |
| **Token payload** | `account_id`, `role`, `iat`, `exp` | Minimum necessary claims |
| **Token revocation** | Refresh token revocation via Redis blacklist; access tokens expire naturally | Immediate revocation capability |

#### 8.1.3 Session Management

| Control | Implementation |
|---|---|
| **Session store** | Redis with AUTH and TLS |
| **Session binding** | Sessions bound to account ID and user agent |
| **Concurrent sessions** | Limited to 5 active sessions per account |
| **Session termination** | Explicit logout invalidates refresh token; all sessions can be terminated via account settings |
| **Idle timeout** | 30-minute inactivity timeout on the frontend; triggers re-authentication |

### 8.2 Authorisation (RBAC and RLS)

See Sections 5.5 and 5.6 for detailed RBAC and RLS implementation.

Additional authorisation controls:

| Control | Implementation |
|---|---|
| **Endpoint-level** | FastAPI dependency injection validates JWT and role for every endpoint |
| **Object-level** | All data access goes through repository layer that enforces account_id scoping |
| **Function-level** | Clinical operations (trigger reasoning, record decision) require Clinician role |
| **Field-level** | Sensitive fields (encrypted PHI) are decrypted only when explicitly requested by an authorised view |

### 8.3 Input Validation and Sanitisation

| Layer | Control |
|---|---|
| **API input** | Pydantic models with strict type validation, field-length limits, and regex patterns for all endpoints |
| **File uploads** | MIME type validation (allowlist: PDF, JPEG, PNG), file size limit (10 MB), magic byte verification, filename sanitisation |
| **Database queries** | All queries use parameterised statements via SQLAlchemy ORM; no raw SQL concatenation |
| **HTML output** | React's built-in XSS protection (JSX auto-escaping); no `dangerouslySetInnerHTML` |
| **Clinical text** | Markdown rendering with sanitisation (DOMPurify); no executable content in clinical output |
| **Search/filter parameters** | Allowlisted fields only; operator validation; injection-safe query construction |

### 8.4 OWASP Top 10 Mitigations

| OWASP Risk | Mitigation |
|---|---|
| **A01: Broken Access Control** | RLS, RBAC, JWT validation on every request, object-level authorisation checks |
| **A02: Cryptographic Failures** | AES-256-GCM, TLS 1.3, bcrypt, no plaintext secrets, envelope encryption |
| **A03: Injection** | Parameterised queries (SQLAlchemy), Pydantic input validation, no eval/exec on user input |
| **A04: Insecure Design** | Threat model (Section 1.2), safety architecture (verifier, hard blocks), defence in depth |
| **A05: Security Misconfiguration** | Security headers (HSTS, CSP, X-Frame-Options), Docker hardening, no default credentials, minimal container images |
| **A06: Vulnerable Components** | Dependency scanning (Dependabot / Snyk), SBOM generation, regular update cycle |
| **A07: Authentication Failures** | bcrypt, JWT best practices, rate limiting, account lockout, session management |
| **A08: Data Integrity Failures** | Hash-chained audit logs, immutable clinical records, software supply chain security (signed commits, CI/CD pipeline integrity) |
| **A09: Logging & Monitoring Failures** | Structured logging (structlog), clinical audit log, pgaudit, Prometheus metrics, alerting |
| **A10: SSRF** | No user-controlled URL fetching; Claude API calls use hardcoded endpoints; file processing is local only |

### 8.5 File Upload Security

| Control | Detail |
|---|---|
| **Allowed types** | PDF, JPEG, PNG only (allowlist) |
| **Size limit** | 10 MB per file |
| **Validation** | MIME type check, magic byte verification, file extension check (all three must agree) |
| **Storage** | Files stored outside the web root; served via application endpoint with auth check |
| **Processing** | File processing (OCR, text extraction) runs in an isolated pipeline; no execution of uploaded content |
| **Filename** | Original filename sanitised; stored with UUID-based name |
| **Virus scanning** | ClamAV integration for production deployment |

### 8.6 API Security

| Control | Implementation |
|---|---|
| **Rate limiting** | Tiered: 60 req/min general, 10 req/min auth, 5 req/min reasoning. Per-account and per-IP. |
| **CORS** | Strict allowlist of permitted origins. No wildcard origins. Credentials mode enabled. |
| **CSRF** | SameSite=Strict cookies prevent CSRF. Double-submit cookie pattern as defence in depth. |
| **Request size** | Maximum request body size enforced at Nginx level (10 MB). |
| **Response headers** | Security headers on all responses (see Section 8.4). |
| **API versioning** | Versioned endpoints (/api/v1/); deprecation headers for sunset planning. |
| **Error responses** | Standardised error format; no stack traces or internal details in production. |
| **Timeout** | Request timeout enforced: 30s general, 120s for reasoning (LLM calls), 300s for export generation. |

### 8.7 Dependency Management and Vulnerability Scanning

| Control | Implementation |
|---|---|
| **Python dependencies** | Pinned versions in `pyproject.toml` with hash verification. Dependabot / Renovate for automated updates. |
| **Node.js dependencies** | `package-lock.json` for deterministic installs. `npm audit` in CI pipeline. |
| **Container images** | Minimal base images (python:3.12-slim, node:20-alpine). No unnecessary packages. |
| **Vulnerability scanning** | Automated scanning on every CI run (Snyk / Trivy). Critical/high vulnerabilities block deployment. |
| **SBOM** | Software Bill of Materials generated on every release for regulatory traceability. |
| **License compliance** | Automated license scanning; no GPL-incompatible dependencies in distributed components. |
| **Supply chain** | Signed commits required. CI/CD pipeline integrity verified. Container images signed. |

### 8.8 Security Headers

| Header | Value | Purpose |
|---|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `Content-Security-Policy` | Strict policy; script-src self; no unsafe-inline | Prevent XSS |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limit referrer leakage |
| `Permissions-Policy` | Disable camera, microphone, geolocation | Minimise browser API exposure |
| `Cache-Control` | `no-store` on API responses containing PHI | Prevent caching of sensitive data |

---

## 9. Incident Response Plan

### 9.1 Security Incident Classification

| Severity | Definition | Examples | Response Time |
|---|---|---|---|
| **P1 -- Critical** | Active breach with confirmed PHI exposure, or complete system compromise | Database breach, ransomware, mass PHI exfiltration | Immediate (within 1 hour) |
| **P2 -- High** | Attempted or partial breach, significant vulnerability discovered | Successful authentication bypass, SQL injection found, compromised credentials | Within 4 hours |
| **P3 -- Medium** | Vulnerability identified but not exploited, suspicious activity | Failed brute-force attempts, dependency vulnerability disclosed, anomalous access patterns | Within 24 hours |
| **P4 -- Low** | Minor security issue, informational | Misconfiguration detected, security header missing, routine scan findings | Within 1 week |

### 9.2 Response Procedures

#### Phase 1: Detection and Assessment (0-1 hours)

1. **Alert received** from monitoring (Prometheus alerts, pgaudit anomaly, rate-limit triggers) or external report.
2. **Incident commander assigned** from the on-call rotation.
3. **Initial assessment**: Determine severity, scope, affected data, and affected users.
4. **Containment decision**: Determine if immediate containment is needed (e.g., isolate affected systems, revoke compromised credentials).

#### Phase 2: Containment (1-4 hours)

1. **Short-term containment**: Isolate affected components without destroying forensic evidence.
   - Revoke compromised tokens/sessions.
   - Block suspicious IP addresses.
   - Disable compromised accounts.
   - If necessary, take affected services offline.
2. **Evidence preservation**: Snapshot affected systems, preserve logs, capture network state.
3. **Communication**: Notify internal stakeholders per the communication plan.

#### Phase 3: Eradication (4-24 hours)

1. **Root cause analysis**: Determine how the breach occurred.
2. **Vulnerability remediation**: Patch the vulnerability, update configurations, rotate affected credentials.
3. **Verification**: Confirm the attack vector is closed.

#### Phase 4: Recovery (24-72 hours)

1. **System restoration**: Restore from clean backups if necessary.
2. **Monitoring intensification**: Increase monitoring on affected systems for recurrence.
3. **Gradual service restoration**: Bring services back online with enhanced monitoring.

#### Phase 5: Post-Incident (1-2 weeks)

1. **Post-mortem report**: Detailed timeline, root cause, impact assessment, lessons learned.
2. **CAPA**: Corrective and preventive actions identified and tracked to completion.
3. **Process updates**: Update incident response procedures based on lessons learned.
4. **Regulatory reporting**: File required reports (see Section 9.3).

### 9.3 Breach Notification -- DPDP Act Requirements

The DPDP Act 2023 requires the Data Fiduciary to notify the Data Protection Board of India and affected data principals of a personal data breach.

| Requirement | Implementation |
|---|---|
| **Notification to DPB** | Within 72 hours of becoming aware of the breach. Notification includes: nature of the breach, categories of data affected, approximate number of data principals affected, likely consequences, measures taken/proposed. |
| **Notification to data principals** | Without unreasonable delay. Clear, plain-language notification describing: what happened, what data was affected, what the individual should do, what the organisation is doing. |
| **Notification method** | Email to affected clinicians (who are responsible for notifying their patients). In-application notification. Public disclosure if the breach affects a large number of data principals. |
| **Documentation** | All breach-related communications, decisions, and actions are documented in the incident log. |
| **CDSCO notification** | If the breach involves the SaMD's clinical functionality or safety, a Field Safety Notice is issued and CDSCO is notified per post-market surveillance requirements. |

### 9.4 Contact Information

| Role | Responsibility |
|---|---|
| **Incident Commander** | Overall incident coordination; designated from on-call rotation |
| **Data Protection Officer (DPO)** | DPDP Act compliance; breach notification to DPB and data principals |
| **Engineering Lead** | Technical investigation and remediation |
| **Legal Counsel** | Regulatory obligations, liability assessment |
| **Communications Lead** | External communications, user notifications |

Contact details are maintained in the internal incident response runbook (not published in this document for security reasons).

---

## 10. Demo Build Security Posture

The demo build modifies one and only one security control: the clinician credential verification gate at signup is removed, allowing anyone to create an account.

### 10.1 What Changes in Demo

| Control | Production | Demo | Rationale |
|---|---|---|---|
| **Credential verification** | Clinician credentials verified against medical registry | Removed; open signup | Lower barrier for evaluation and testing |
| **Demo banner** | Not shown | Persistent, dismissible banner: "Demo build -- decision-support only, not for real patient care" | Prevent misuse for actual clinical decisions |

### 10.2 What Does NOT Change in Demo

Every other security and safety mechanism remains fully active:

| Mechanism | Status in Demo |
|---|---|
| Encryption (at rest, in transit, on-device) | Fully active |
| RLS and RBAC | Fully active |
| JWT authentication and session management | Fully active |
| Input validation | Fully active |
| Audit logging (immutable, hash-chained) | Fully active |
| Verifier (cannot be bypassed) | Fully active |
| Allergy/contraindication hard blocks | Fully active |
| Autonomy tiers | Fully active |
| Anti-automation-bias mechanisms | Fully active |
| Conservative-output-wins rule | Fully active |
| Source citation requirements | Fully active |
| No-certainty-language rule | Fully active |
| Devil's-advocate dissent | Fully active |
| Download-all and audit-export | Fully active |
| Rate limiting | Fully active |
| Security headers | Fully active |
| PHI de-identification for LLM calls | Fully active |
| Data residency enforcement | Fully active |
| Agent trace preservation | Fully active |

### 10.3 Demo-Specific Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Non-clinicians using the system for real patient care | Persistent demo banner; terms of use prohibiting clinical use; no credential wall means no implied clinical authority |
| Higher account creation volume (no gate) | Rate limiting on signup endpoint; monitoring for abuse |
| Demo data treated as real PHI | All data created in the demo is handled with the same security controls as production data |

---

## 11. Compliance Matrix

### 11.1 DPDP Act 2023 Compliance

| Requirement | Section | Implementation | Status |
|---|---|---|---|
| Lawful purpose for processing | DPDP s.4 | Clinical decision support as stated in consent notice | Designed |
| Consent before processing | DPDP s.6 | Per-patient consent capture at registration | Designed |
| Consent withdrawal | DPDP s.6(6) | Withdrawal mechanism with cessation of processing | Designed |
| Data principal rights (access) | DPDP s.11 | Patient data export API | Implemented |
| Data principal rights (correction) | DPDP s.11 | Clinician-mediated correction with audit trail | Implemented |
| Data principal rights (erasure) | DPDP s.11 | Three-stage erasure with crypto-shredding | Designed |
| Data principal rights (portability) | DPDP s.11 | Full record export (JSON/CSV) | Implemented |
| Data principal rights (grievance) | DPDP s.11 | Grievance officer appointed; in-app submission | Designed |
| DPO appointment | DPDP s.8(1) | DPO designated | Planned |
| Reasonable security safeguards | DPDP s.8(4) | Encryption, access controls, audit trails (this document) | Implemented |
| Breach notification to Board | DPDP s.8(6) | 72-hour notification procedure | Designed |
| Breach notification to data principals | DPDP s.8(6) | Notification procedure documented | Designed |
| Data retention limitation | DPDP s.8(7) | Retention periods defined and enforced | Designed |
| Cross-border transfer restrictions | DPDP s.16 | De-identification for Claude API; India residency for all PHI | Implemented |
| Significant data fiduciary obligations | DPDP s.10 | DPIA, DPO, annual audit | Planned |
| Children's data protection | DPDP s.9 | Not applicable (clinician-facing system; no direct child data subjects) | N/A |

### 11.2 CDSCO SaMD Compliance

| Requirement | Ref | Implementation | Status |
|---|---|---|---|
| SaMD classification | MDR 2017 | Class B/C assessment documented | Designed |
| Registration application | MDR 2017 | Technical file structure defined | Planned |
| QMS (ISO 13485) | MDR 2017 | QMS framework defined | In progress |
| Software lifecycle (IEC 62304) | MDR 2017 | Development process aligned | In progress |
| Risk management (ISO 14971) | MDR 2017 | Risk register initiated | In progress |
| Clinical validation | MDR 2017 | Validation study design planned | Planned |
| Usability engineering (IEC 62366-1) | MDR 2017 | Usability study planned | Planned |
| Post-market surveillance | MDR 2017 | Surveillance plan documented | Designed |
| PSUR reporting | MDR 2017 | Annual reporting process defined | Planned |
| Traceability of clinical outputs | MDR 2017 | source_links, evidence_quality on every suggestion | Implemented |
| Audit trail including agent traces | MDR 2017 | Immutable, hash-chained audit log | Implemented |
| Versioned guideline corpora | MDR 2017 | guideline_documents with version tracking | Implemented |
| Exportable validation logs | MDR 2017 | Audit export API (JSON/CSV) | Implemented |

### 11.3 Telemedicine Practice Guidelines 2020

| Requirement | Implementation | Status |
|---|---|---|
| RMP-only use | Credential verification (production); demo banner (demo) | Designed |
| Patient consent | Teleconsultation consent capture | Designed |
| Patient identification | Clinician-verified patient identity | Implemented |
| Documentation | Complete encounter documentation with audit trail | Implemented |
| Record retention (3 years) | 3+ year retention for all clinical records | Designed |
| Data privacy | Full encryption, access controls, India residency | Implemented |

### 11.4 Security Controls

| Control | Section | Implementation | Status |
|---|---|---|---|
| Encryption at rest (TDE) | 3.1.1 | PostgreSQL TDE with AES-256 | Implemented |
| Encryption at rest (application) | 3.1.2 | AES-256-GCM per-patient encryption | Implemented |
| Encryption in transit | 3.2 | TLS 1.3 for external; TLS 1.2+ for internal | Implemented |
| On-device encryption | 3.3 | Web Crypto API, encrypted IndexedDB | Designed |
| Key management | 3.4 | Envelope encryption; KMS for production | Designed |
| No plaintext keys | 3.5 | All secrets in env vars or KMS; passwords bcrypt-hashed | Implemented |
| Authentication (bcrypt) | 8.1.1 | bcrypt cost=12 | Implemented |
| Authentication (JWT) | 8.1.2 | 15-min access, 7-day refresh, httpOnly cookies | Implemented |
| Session management | 8.1.3 | Redis-backed, bound, limited concurrent sessions | Implemented |
| RBAC | 8.2 | Role-based endpoint and object-level access | Implemented |
| RLS | 5.6 | PostgreSQL RLS on all patient-related tables | Implemented |
| Input validation | 8.3 | Pydantic models, parameterised queries, file validation | Implemented |
| OWASP Top 10 | 8.4 | All 10 risks mitigated | Implemented |
| Rate limiting | 8.6 | Tiered per-endpoint rate limits | Implemented |
| Security headers | 8.8 | HSTS, CSP, X-Frame-Options, etc. | Implemented |
| Dependency scanning | 8.7 | Automated vulnerability scanning in CI | Planned |
| Audit logging | 6 | Immutable, hash-chained, exportable | Implemented |
| Incident response | 9 | Classification, procedures, breach notification | Designed |
| India data residency | 7 | All PHI in India; Claude API de-identified | Implemented |

### 11.5 Safety Architecture Controls

| Control | Requirement Source | Implementation | Status |
|---|---|---|---|
| Verifier on every output | Spec s.9 | Mandatory verifier pass; cannot be bypassed | Implemented |
| Conservative output wins | Spec s.9 | Verifier selects conservative interpretation on disagreement | Implemented |
| Allergy hard blocks | Spec s.9 | Allergy/contraindication conflicts block output | Implemented |
| Autonomy tiers | Spec s.9 | Informational / Suggestive / Flag-for-review | Implemented |
| No certainty language | Spec s.16 | Low-confidence outputs rendered as uncertainty | Implemented |
| Clinician sign-off | Spec s.9 | Every accept/override logged immutably | Implemented |
| Anti-automation-bias | Spec s.9 | Devil's advocate, can't-miss flags, uncertainty rendering | Implemented |
| Source citation | Spec s.16 | No uncited management text; source links on every claim | Implemented |
| Demo safety banner | Spec (demo) | Persistent, dismissible banner always visible | Implemented |
| Download/export never fails | Spec s.16 | Retry logic, chunked processing, fallback | Implemented |

---

## Appendix A: Glossary

| Term | Definition |
|---|---|
| **CDSCO** | Central Drugs Standard Control Organisation -- India's national regulatory body for pharmaceuticals and medical devices |
| **CDSS** | Clinical Decision Support System |
| **Crypto-shredding** | Rendering encrypted data permanently unrecoverable by destroying the encryption key |
| **DPA** | Data Processing Agreement |
| **DPDP Act** | Digital Personal Data Protection Act 2023 (India) |
| **DPO** | Data Protection Officer |
| **IMDRF** | International Medical Device Regulators Forum |
| **KMS** | Key Management Service |
| **PDEK** | Patient Data Encryption Key |
| **PHI** | Patient Health Information |
| **PII** | Personally Identifiable Information |
| **QMS** | Quality Management System |
| **RBAC** | Role-Based Access Control |
| **RLS** | Row-Level Security |
| **RMP** | Registered Medical Practitioner |
| **SaMD** | Software as a Medical Device |
| **TDE** | Transparent Data Encryption |

## Appendix B: Document History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0.0 | 2026-06-27 | Documedic Engineering | Initial document |
