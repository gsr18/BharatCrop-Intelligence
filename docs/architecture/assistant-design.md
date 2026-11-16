# BharatCrop Intelligence: Grounded Assistant Design

**Status:** Proposed; no assistant, retrieval index, AI provider, or grounding workflow was found in the repository audit. Provider selection and all model claims remain open.

## Scope and non-goals

MVP assistant provides basic agricultural Q&A grounded in a curated, versioned corpus. It is not unrestricted web search, a substitute for an agricultural expert, a diagnosis/guarantee, or a channel for unsupported predictive-risk warnings. It must not use exploratory risk indicators as validated future risk.

## Knowledge-source lifecycle

1. **Propose:** Authorized curator registers source owner/publisher, canonical reference, language, date/version, intended subject/geography, provenance, and terms/license evidence.
2. **Review:** Human reviewer verifies authority, currency, applicability, rights to ingest/quote/redistribute, language quality, and conflicts. The source remains unavailable to retrieval until approved.
3. **Ingest safely:** Quarantine content; validate format, size, checksum and source identity; scan/process in an isolated environment; extract text and metadata; reject executable content and unsupported files.
4. **Version:** Assign immutable document version and content checksum; store publication/effective dates, language, jurisdiction, subject scope, attribution requirements, review actor/time, and expiry/review date.
5. **Index:** Chunk with stable document/version and passage references. Retrieval index entries inherit access, language, geography, and effective-date constraints. Index builds are reproducible and traceable to source versions.
6. **Evaluate and publish:** Run retrieval, citation, language, safety, and unsupported-question checks. Require authorized review and an explicit publish transition. Keep draft/rejected/expired/withdrawn versions out of public retrieval.
7. **Monitor and withdraw:** Track source updates, stale/expired material, user reports, conflicting guidance, and retrieval failures. Withdrawal blocks future retrieval promptly and leaves a minimal audit trail under retention policy.

No repository source or notebook artifact is automatically an approved assistant source. Research files, model outputs, and user-uploaded documents are not authoritative by default.

## Proposed request pipeline

1. Authenticate the user; verify conversation ownership and current case/resource authorization.
2. Validate message size, language, abuse/rate policy, and whether requested assistance is in scope.
3. Minimize query context. Do not include name, contact, exact farm coordinates, or case details unless strictly necessary, authorized, and approved for the selected provider.
4. Retrieve relevant passages only from currently approved corpus versions; apply language, geography, date, and access filters.
5. If retrieval is insufficient, contradictory, stale, or outside supported coverage, abstain or ask a safe clarifying question instead of improvising.
6. Generate a concise answer using constrained instructions that require claims to be grounded in retrieved passages, preserve source limitations, and avoid pretending to be a clinician/agronomist where expertise is needed.
7. Validate every citation against retrieved passages and document versions. A citation must support its associated claim; an identifier that merely exists is not enough.
8. Apply policy checks for unsupported claims, dangerous instructions, personal data leakage, and prohibited risk warnings.
9. Return answer, citations, language, status (`answered`, `abstained`, `referred`, or `unavailable`), relevant limitations, and timestamp. Store minimal conversation records under an approved retention policy.
10. Offer expert referral for unresolved questions where available. Creating/sharing a farmer-specific case requires a distinct explicit authorization flow.

## Citations and evidence behavior

- Each factual agricultural answer must cite approved source title, publisher/owner, version/date or effective period, and a stable passage/reference sufficient to trace the claim.
- Citation validation is a release-critical requirement. Do not fabricate citations, imply a source says more than it does, or cite search-result snippets without an approved source record.
- Preserve source disagreement and uncertainty; present date/geography limitations. Prefer an explicit “not enough verified information” over interpolation.
- For unavailable/unsupported local coverage, say that coverage is unavailable. Do not convert missing information into zero risk or a confident India-wide statement.
- If a question concerns current advisories, weather forecasts, pesticide dosage, safety-sensitive activity, or other time-critical material, answer only when the approved corpus contains current, applicable evidence and policy permits it; otherwise abstain or refer.
- Generated answers must not cite the existing exploratory risk indicators as validated forecasts or farmer-facing warnings.

## Hindi and English

- Respect the conversation's selected Hindi or English language; allow explicit switch. Detecting language may suggest but must not silently override user choice.
- Retrieve same-language sources where possible. If only a source in the other language is approved, disclose source language and apply reviewed translation; retain original title/attribution.
- Evaluate agricultural terminology, script, numerals/units, tone, readability, and citation alignment with fluent human reviewers.
- If the system cannot reliably answer in the requested language, disclose that limitation in that language, provide a source-language citation only if useful, or abstain. Do not silently switch to English.
- Store preferred language per product requirements but avoid inferring sensitive attributes from language choice.

## Prompt injection and untrusted documents

- User messages, retrieved documents, uploaded materials, OCR text, metadata, and external responses are untrusted data. They cannot change system policy, permissions, source approval, tool access, or output constraints.
- Separate instruction channels from quoted/retrieved content; delimit passages and state that embedded instructions must be treated as content, not commands.
- Do not execute document instructions, arbitrary code, links, or tools based on retrieved text. Retrieval does not grant data access.
- Use allowlisted retrieval only; do not add unrestricted URL browsing or arbitrary fetching. Validate source and document identity before indexing and at answer time.
- Apply output validation and citation checks; test direct and indirect injection, hidden text/OCR, multilingual injection, poisoned metadata, conflicting sources, and attempts to reveal other users' data or system prompts.
- Never pass secrets, tokens, hidden chain-of-thought, or unrelated conversation history to model providers or users.

## Privacy and AI-provider selection

Before selecting a provider, compare data retention/training defaults, opt-out and contractual controls, region/subprocessors, security certifications and evidence, encryption, deletion, auditability, prompt/data ownership, availability, latency, cost, Hindi/English quality, model changes, safety controls, and exit/portability.

Do not send direct identifiers or exact farm locations by default. Use a coarse, non-identifying location only if necessary to retrieve relevant evidence and the user has authorized the purpose. Obtain legal/privacy approval for provider terms and cross-border processing. Configure provider data-retention/training controls contractually where available; do not assume an API is private by default.

## Evaluation and launch gates

Build a versioned evaluation set from approved sources and expert-authored questions; avoid copying private farmer conversations without separate reviewed consent/basis. Include:

- **Grounding:** claim-level support, factual correctness, contradiction handling, freshness, and supported versus unsupported geography.
- **Citations:** citation existence, version validity, relevance, coverage of material claims, attribution correctness, and resistance to fabricated references.
- **Abstention:** questions with no source, stale/conflicting sources, out-of-scope requests, missing location/context, and time-sensitive requests.
- **Language:** Hindi and English answer quality, terminology, script/number/unit rendering, language consistency, reading level, and citation comprehension.
- **Safety/privacy:** injection attempts, requests for private data, excessive collection, expert-access confusion, high-stakes advice, and misuse as a validated future-risk predictor.
- **Retrieval:** recall/relevance for supported questions, metadata filter correctness, withdrawn/expired source exclusion, and version traceability.
- **Operational:** latency, provider failure, rate limiting, data minimization, deletion, and audit behavior.

Set acceptance thresholds, test ownership, and regression policy before implementation. Require human expert review of the test set and high-impact answer classes; numerical thresholds are not invented here. Any failure of citation support, privacy, access control, or safe abstention blocks release.

## Current evidence and unknowns

The repository audit found no retrieval corpus, citations, assistant service, provider configuration, or evaluation. No assistant behavior, provider, answer quality, privacy property, or working integration is claimed by this design.
