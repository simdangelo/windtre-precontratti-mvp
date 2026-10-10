# TODO.md — Production-Grade Industrialization Roadmap

This document serves as our concrete engineering checklist for industrializing the **WINDTRE Sintesi & Trasparenze Automation** platform. It outlines our architectural gaps, code standards improvements, and the transition from local development mocks to the actual GCP serverless target architecture.

## 📊 1. Data Validation & Bootstrapping: Auto-completing Offers from Trasparenza Sheets
Before executing heavy pipeline operations, implement mechanisms to bootstrap, pre-populate, and validate `offers` table records directly from existing Tariff Transparency spreadsheets.

- [ ] **Audit and Complete `offers` Database Schema Fields:**
  * Perform an audit of all technical and regulatory parameters declared in the AGCOM templates (e.g., maximum download/upload speeds, guaranteed minimum speeds, cellular data caps, voice minutes, SMS limits, and EU roaming data caps).
  * Expand the SQLAlchemy models and Cloud Spanner DDL `offers` table definition to include dedicated, strongly-typed columns (fields) for these attributes rather than letting them remain unmodeled or embedded inside raw JSON structures.
- [ ] **Develop Tariff Transparency Spreadsheet Parser:** nice to have
  * Build a parsing engine (`app/services/trasparenza_parser.py`) utilizing `openpyxl` to read raw cell coordinates from the standardized AGCOM Tariff Transparency templates.
  * Extract core metadata fields dynamically, such as:
    * Commercial Name (Nome Commerciale)
    * Technology Type (Tipologia della tecnologia)
    * Base Price / Monthly Fee (Canone Mensile)
    * Unique PO Identifiers (Codice PO for Very Mobile)
    * One-off activation prices (for existing, native new, and port-in customers)
- [ ] **Interactive Offer Bootstrapping API:**  nice to have
  * Expose a route `POST /api/offers/bootstrap-from-trasparenza` accepting an uploaded Excel `.xlsx` file, parsing its parameters, and returning a pre-populated, draft `Offer` schema payload.
  * This enables operators to instantly seed new database records with zero manual entry errors.
- [ ] **Cross-Document Consistency Validation:**  nice to have
  * Construct validation 
   confirming that data fields in the `offers` database match the parameters declared in the uploaded spreadsheet before an offer transitions to `APERTA` state or compiles any PDFs.

---

## 🏛️ 2. Database Layer: Transition to Real GCP Cloud Spanner
Our current implementation uses local SQLite database engines. We must transition to the Google Cloud Spanner PostgreSQL-dialect target architecture.

- [ ] **Configure Spanner PostgreSQL Dialect Connection:**
  * Implement connection strings using the `spanner+spanner` or standard SQLAlchemy dialect for Cloud Spanner:
    ```
    google+spanner://plat-project/spanner-instance/pre-contratti-db
    ```
- [ ] **Spanner Connection Pool Optimization:**
  * Configure SQLAlchemy pool sizes (`pool_size`, `max_overflow`, and timeout parameters) to handle high-concurrency worker threads without exhausting Spanner sessions.
- [ ] **Transaction Retry State Machine:**
  * Cloud Spanner transactions can be aborted by the database due to lock conflicts. Implement decorator-based retry logic using the Spanner-native transaction retry protocols to automatically replay aborted transactions.
- [ ] **Spanner-PG SQLAlchemy compatibility audit:**
  * Eliminate any custom SQLite-specific or standard PostgreSQL-specific dialect calls (e.g. SQLite's auto-increment, Postgres custom functions) that are not natively supported by Spanner's PG-dialect connector.

---

## 🪣 3. Storage Layer: Real Google Cloud Storage (GCS) Integration
Currently, templates are loaded from local folders and generated PDFs are saved locally. This must be migrated to secure GCP buckets.

- [ ] **Template Fetching Pipeline:**
  * Implement service utilities (`app/services/gcs.py`) using `google-cloud-storage` client libraries to download master `.docx` and `.xlsx` templates dynamically from GCS into ephemeral memory or temporary local run paths (`/tmp`).
- [ ] **Secure Output Writing:**
  * Stream generated outputs directly to private GCS buckets under segregated prefixes (e.g., `gs://w3-precontratti-private/[segment_id]/[offer_id]/`).
- [ ] **Private Network Direct File Streaming:**
  * Since the application operates entirely within a secure corporate intranet/VPN (not exposed to the open internet), avoid the overhead of GCS Signed URLs.
  * Implement authenticated file streaming in the FastAPI controllers using the GCS storage client, reading binary blobs from private buckets and returning them directly via FastAPI `StreamingResponse` or `Response` with proper media type headers.

---

## 📨 4. Queue Layer: Actual GCP Cloud Tasks Orchestration
We currently run local background processes or immediate compile loops. To ensure reliability, we must execute tasks asynchronously via Cloud Tasks.

- [ ] **Implement Task Publisher Service:**
  * Build the client-side task enqueuer in `app/services/tasks.py` utilizing the `google-cloud-tasks` SDK.
  * Construct full HTTP target task requests routing payloads to our decoupled document compilation workers:
    ```python
    # Construct task request payload
    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": "https://worker-run-url/tasks/compile",
            "oidc_token": {"service_account_email": "synthesis-worker-sa@..."},
            "body": json.dumps({"offer_id": str(offer_id)}).encode()
        }
    }
    ```
- [ ] **Worker Verification & Headers:**
  * Implement bearer token decoding on the worker endpoints to confirm requests originate exclusively from the authorized Cloud Tasks service account.

---

## 🔐 5. Identity & SSO Security Layer: Production OIDC Authentication
Our routes currently rely on mock users or stubs. We need a secure, production-grade identity pipeline.

- [ ] **Real JWT Token Verification (JWKS):**
  * Integrate Google OpenID Connect (OIDC).
  * Use python libraries (like `python-jose` or `PyJWT`) to dynamically fetch public JWK certs, verify signatures, assert expiration limits, and decode active user properties.
- [ ] **Directory Group Membership Assertion:**
  * In the dependency injection pipeline (`get_current_active_user`), extract the user's corporate groups (e.g., `g-very-mobile`) and dynamically map them to active commercial segment authorization lists.
- [ ] **Segment-Level Row-Level Security (RLS) Enforcement:**
  * Guarantee that every DB transaction (single selects, bulk updates, deletions) appends strict segment isolation queries based on the OIDC token state to prevent cross-segment access.

---

## 📈 6. Monitoring, Logging, and Auditing
We must move away from standard print statements to structured cloud telemetry.

- [ ] **Structured JSON Logging:**
  * Integrate `google-cloud-logging` to write structured, machine-readable JSON logs directly to Stackdriver, enabling proper searchability by severity, request-ids, or offer IDs.
- [ ] **Detailed Lifecycle Audit Logs:**
  * Save structured records of every action (creation, metadata modification, bulk update, PDF compile success/fail) in the Spanner database histories, logging the author's email, exact timestamp, and modified state transition parameters.
- [ ] **Cloud Trace Context Propagation:**
  * Propagate global tracing IDs (such as `x-cloud-trace-context`) across the Frontend, API Router, Cloud Tasks queues, and Synthesis Worker to easily trace distributed latency bottlenecks.

---

## 🧪 7. Testing, CI/CD, and Environment Standardization

- [ ] **Environment Parameter Standardization:**
  * Replace custom environment parsing with **Pydantic BaseSettings** to define a schema-enforced environment configuration layer (Local, Dev, UAT, Production).
- [ ] **Hermetic Integration Tests:**
  * Add isolated integration tests using a local Cloud Spanner emulator and local MinIO/GCS mock environments to test raw transactions and storage operations.
- [ ] **Target Architecture CI/CD Pipelines:**
  * Construct GitHub Actions or Google Cloud Build configurations to execute automated validation checks, build secure Docker containers, deploy services to Cloud Run, and apply Cloud Spanner DDL updates.
