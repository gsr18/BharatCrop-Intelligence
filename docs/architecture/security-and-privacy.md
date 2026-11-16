# BharatCrop Intelligence: Security and Privacy

**Status:** Proposed requirements and review checklist; no application security controls are implemented by this document. Provider and legal choices remain open.

## Authentication provider comparison

Compare established managed solutions and standards-based providers; do not select a vendor until product/security review. Evaluate:

- Standards support and interoperability (e.g., OIDC/OAuth 2.0 as applicable), secure browser flows, token/session lifecycle, audience/issuer controls, signing-key rotation, and logout/revocation behavior.
- Account recovery, MFA/passkey support, abuse and credential-stuffing protection, verified email/phone options, accessibility, Hindi/English support, and usability on low-bandwidth/mobile devices.
- Data location, subprocessors, breach notification, retention/deletion, export, encryption, audit evidence, contractual terms, and Indian legal/privacy review.
- Role/claim integration without making the provider's user-editable profile authoritative for application permissions.
- Availability, support model, rate limits, integration effort, pricing, migration/export path, and vendor lock-in.
- Expert identity verification and administrator controls, including strong authentication and recovery safeguards.

The selected solution must not create broad expert access by virtue of successful authentication. FastAPI maps a verified identity to an application account and enforces application roles and resource permissions. Credential/token storage and exact session design are undecided.

## Authorization

- Deny by default; enforce authentication, role, ownership, case assignment, consent/authorized basis, purpose, and grant expiry/revocation in the backend for every protected operation.
- Frontend controls are presentation only. Every API access and every page of paginated results repeats the authorization check.
- Farmers may access their own account/farms/results/conversations and may authorize a scoped case share.
- Experts may access only assigned cases and the minimum resources explicitly covered by current consent or another documented authorized basis.
- Administrators do not receive blanket access to personal records. Separate operational administration from content access; require purpose, least privilege, and audited approval for exceptional access.
- Keep role assignment separate from user profile edits. Expert/admin grants require an approved verification/approval process and change audit.
- Revoke access promptly on consent revocation, expiry, case closure, assignment removal, account suspension, or role change.
- Prevent IDOR by resolving every resource from the authenticated principal's permitted scope, never by trusting owner IDs supplied by the client.

## Consent and expert access

- Collect only data necessary for a stated purpose. Consent is specific, informed, understandable in Hindi/English, unbundled where appropriate, versioned, and recorded with scope and time.
- A grant identifies grantor, grantee/role, purpose, resource scope, notice version, grant time, expiry if applicable, and revocation state.
- If an alternative legal basis is proposed, record the basis and scope only after legal review; do not label it consent or infer it.
- Require a valid grant/basis before exposing farmer-specific information to an expert. Verify it at each access; minimize case payload; audit both reads and changes.
- Provide understandable withdrawal and case access status. Withdrawal blocks future access under that grant; exceptions, statutory retention, and already-completed processing need legal advice and clear notice.
- No expert assignment or consent workflow is currently implemented in the repository.

## Data minimization, retention, and deletion

- Do not collect precise coordinates, phone/email, farm area, conversation content, or identity attributes unless a defined MVP purpose requires them.
- Separate authentication identity from business data where practical; do not store passwords or identity-provider tokens in the application database.
- Define retention by data class before launch: account/profile, farm data, consent evidence, prediction inputs/results, expert cases/reviews, assistant conversations, operational/security logs, and backups.
- Support access, correction, export, deletion, and consent withdrawal in line with applicable legal advice. Define propagation to indexes, caches, providers, replicas, and backups.
- Use encryption in transit and at rest through managed infrastructure where available; restrict database roles, keys, exports, and backups.
- Do not reuse farmer data, cases, or conversations to train or fine-tune models without a separately reviewed lawful basis and transparent controls.

## Secrets and configuration

- Store secrets only in an approved secrets-management service or protected runtime injection mechanism; never commit them, put them in browser bundles, notebook outputs, database rows, issue text, or logs.
- Separate development/staging/production identities and credentials; grant least privilege; rotate credentials and signing/encryption keys; audit access.
- Keep cryptographic keys separate from encrypted data and backups; document recovery and rotation procedures.
- The audit found no application secrets/configuration to assess; no environment variable values were read.

## Logging, audit, and observability

- **Prohibit logging secrets and unnecessary personal data.** Never log passwords, tokens, API keys, session cookies, full assistant prompts/responses, precise farm coordinates, full case/review text, or raw provider payloads by default.
- Use correlation IDs, action/resource identifiers, actor reference, outcome, timestamp, and safe reason codes. Avoid high-cardinality personal identifiers in metrics.
- Keep security/audit events append-only or tamper-evident with access to audit records itself audited. Define lawful purpose, access, and retention before enabling detailed audit trails.
- Sanitize untrusted strings against log injection; separate operational logs from protected business content.
- Alert on authentication abuse, unusual access/export, repeated denied access, permission changes, consent changes, provider abuse, and backup failures without leaking content.

## Abuse protection and secure operations

- Apply per-route and per-principal rate limits, request/body size limits, pagination bounds, timeouts, concurrency budgets, and safe provider quotas. Avoid limits that unfairly exclude low-bandwidth users; tune from measurements.
- Protect browser authentication flows against CSRF/session fixation and secure cookies according to the selected design; use appropriate CORS allowlists, CSP, security headers, and input/output encoding.
- Validate all input server-side; use parameterized database access; protect against SSRF by avoiding arbitrary URL retrieval and using egress allowlists for providers.
- Treat uploaded documents as untrusted; quarantine, validate type/size/checksum, scan safely, and prevent macro/script execution. Prompt injection is addressed in `assistant-design.md`.
- Pin/review dependencies, generate an SBOM, scan dependencies and container images, sign/provenance-check built artifacts, and deploy least-privilege containers without unnecessary capabilities.
- Keep health checks free of secrets and private topology. Restrict administrative APIs and require stronger authentication/review for sensitive operations.

## Backups and incident response

- Use encrypted managed PostgreSQL backups and test restore in an isolated environment before launch. Define retention, recovery point/time objectives, ownership, access control, and deletion propagation. Numerical RPO/RTO are unresolved.
- Include model/knowledge artifact versions, checksums, database state, and configuration references in recovery planning; do not restore untrusted artifacts automatically into execution.
- Establish incident severity, on-call/ownership, containment, credential/key revocation, forensic preservation, regulator/data-subject assessment, provider coordination, communications, and post-incident review.
- Maintain a breach response plan that can identify affected data categories and users without exposing sensitive data in incident tooling.
- No deployment, backup, monitoring, or incident-response system exists in the audited repository.

## Indian legal and privacy review required

The following are legal questions, not legal conclusions. Obtain qualified India-specific counsel before public launch and re-check current statutes, rules, commencement/transition provisions, regulations, and contracts:

- Applicability and obligations under India's Digital Personal Data Protection Act, 2023 and rules/notifications in force at launch, including notice, consent or other permitted basis, data-principal rights, children's data if relevant, processor/controller responsibilities, security safeguards, breach notification, retention/deletion, and cross-border transfer requirements.
- Whether any sector-specific agriculture, telecom, consumer protection, cybersecurity, government-data, or state-level requirements apply to the product, data sources, advice, or expert workflow.
- Data-source licenses, terms of service, attribution, redistribution rights, API conditions, and whether derived outputs may be exposed commercially.
- Contractual and privacy obligations for identity, hosting, PostgreSQL, weather, AI, messaging, observability, and backup providers, including subprocessors, data location, retention, model-training use, and deletion.
- Whether expert access/verification, professional advice disclaimers, liability, record retention, and dispute/redressal processes require additional controls.
- Age/guardian handling and whether children may use the service; do not assume eligibility or collect age unless needed and reviewed.

Do not treat this list as exhaustive legal advice or claim compliance from having engineering controls.

## Launch security gates

Public launch is blocked until threat modeling, privacy review, authorization testing (including cross-user and revoked-consent tests), dependency/container scanning, secret scanning, backup/restore test, incident runbook, provider contract review, and security sign-off are complete. All open provider/legal choices in `decisions/architecture-decisions.md` remain release blockers where they affect the corresponding feature.
