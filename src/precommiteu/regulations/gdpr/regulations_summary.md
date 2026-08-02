# Precommiteu public regulation context - GDPR
Included regulations: GDPR (General Data Protection Regulation), CELEX 32016R0679.

Compact, developer-oriented SUMMARIES of code-relevant GDPR articles - NOT the
legal text. Used to (a) retrieve the probable article area for a scanner finding
and (b) show a short "why this matters" snippet in PR comments. For the
authoritative wording, follow the EUR-Lex link rendered with each finding.

# GDPR (General Data Protection Regulation)

## gdpr_art5
Reference: GDPR Art. 5
Title: Principles relating to processing of personal data
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Defines the core rules for handling personal data: process it lawfully and transparently, collect only what you need for a stated purpose, keep it accurate, delete it once it's no longer needed, and secure it. You must be able to prove you comply.
Developer impact: Implement data retention/TTL policies, encryption in transit and at rest, data minimization, and field-level access controls.
Code smells: fetching full records when one field is needed; stored data with no TTL or deletion job; PII sent over unencrypted HTTP; PII logged in plaintext logs; repurposing data for ML/ads without checks
Related: gdpr_art89

## gdpr_art6
Reference: GDPR Art. 6
Title: Lawfulness of processing
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Every processing operation needs a valid legal basis (consent, contract, legal obligation, vital/public interest, or legitimate interest). Reusing data for a new purpose requires re-checking compatibility and adding safeguards like encryption or pseudonymisation.
Developer impact: Gate processing behind consent/legal-basis checks and apply pseudonymisation when repurposing data.
Code smells: processing without checking consent flag; marketing opt-in defaulted to true; raw data exported to ML without filtering; missing pseudonymisation on secondary use; tracking cookie set before consent
Related: gdpr_art9, gdpr_art10, gdpr_art23

## gdpr_art7
Reference: GDPR Art. 7
Title: Conditions for consent
Regulation: GDPR
Source CELEX: 32016R0679

Summary: If you rely on consent, you must prove it was given, keep it separate from other terms, and make withdrawal as easy as opting in. Consent isn't valid if a service is wrongly made conditional on it.
Developer impact: Record consent with audit metadata, unbundle consent UI, and provide an easy withdrawal endpoint.
Code smells: consent checkbox pre-checked by default; consent stored without timestamp/version; bundled accept-all terms field; withdraw harder than opt-in; withdrawal not propagated to jobs/cache

## gdpr_art8
Reference: GDPR Art. 8
Title: Conditions applicable to child's consent in relation to information society services
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Online services for children need a verified parent/guardian's consent when the child is under 16 (or the national floor, down to 13). You must make reasonable efforts to verify that parental authorization.
Developer impact: Add age verification and parental-consent workflows that block processing of under-age data until a guardian authorizes it.
Code smells: hardcoded default age bypassing checks; no parental consent verification flow; tracking SDK init for minors pre-consent; missing age gate on data collection; no guardian authorization token stored
Related: gdpr_art6

## gdpr_art9
Reference: GDPR Art. 9
Title: Processing of special categories of personal data
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Processing sensitive data (health, biometrics, race, religion, sexual orientation, political/union views, genetics) is banned unless a strict exception applies, such as explicit consent. Such data needs extra protection.
Developer impact: Enforce explicit-consent checks, encryption, and strict access controls before storing or processing sensitive fields.
Code smells: sensitive data stored in plaintext; biometrics collected without explicit consent; inferring race/religion/orientation from data; sensitive fields lacking access controls; special-category data in unencrypted cache
Related: gdpr_art89

## gdpr_art10
Reference: GDPR Art. 10
Title: Processing of personal data relating to criminal convictions and offences
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Criminal conviction and offence data may only be processed under official authority or where law authorizes it with safeguards. It demands strong access controls and security.
Developer impact: Apply strict RBAC, encryption, and minimal data models whenever handling criminal-record fields.
Code smells: criminal record on unauthenticated endpoint; conviction flags in plaintext column; criminal data without RBAC; background-check results in debug logs; conviction data sent over unencrypted HTTP
Related: gdpr_art6

## gdpr_art11
Reference: GDPR Art. 11
Title: Processing which does not require identification
Regulation: GDPR
Source CELEX: 32016R0679

Summary: If you don't need to identify a person for your purpose, you must not collect extra identifying data just to satisfy GDPR. For such anonymous data, access/erasure rights apply only if the user supplies info enabling identification.
Developer impact: Don't force identifiers (email, ID) in DSAR flows or schemas when a session token or anonymous data suffices.
Code smells: requiring email when session ID suffices; adding identifiers to anonymous telemetry; DSAR API errors instead of session prompt; mandatory account for opt-out request; storing identifiers just in case for DSARs
Related: gdpr_art15, gdpr_art16, gdpr_art17, gdpr_art18, gdpr_art19, gdpr_art20

## gdpr_art12
Reference: GDPR Art. 12
Title: Transparent information, communication and modalities for the exercise of the rights of the data subject
Regulation: GDPR
Source CELEX: 32016R0679

Summary: You must handle data-subject requests in clear language, for free, and respond within one month (extendable to three). Allow electronic submission, reply electronically, explain refusals, and only charge/refuse for excessive requests.
Developer impact: Build DSR workflows with a 30-day SLA, electronic intake/output, machine-readable privacy icons, and failure notifications.
Code smells: DSR job exceeding 30-day deadline; request failures silently swallowed; privacy notice not accessible via URL; payment gate on data access request; no rate limiting to flag excessive requests
Related: gdpr_art11, gdpr_art13, gdpr_art14, gdpr_art15, gdpr_art16, gdpr_art17

## gdpr_art13
Reference: GDPR Art. 13
Title: Information to be provided where personal data are collected from the data subject
Regulation: GDPR
Source CELEX: 32016R0679

Summary: When you collect data directly from a user, you must disclose at that moment who the controller/DPO is, the purposes and legal basis, recipients, retention period, their rights, and any automated decision-making logic.
Developer impact: Render mandatory privacy disclosures in collection forms/UIs and API responses at the point of data capture.
Code smells: form missing privacy notice/DPO contact; no retention period or recipients disclosed; automated decision-making logic not explained; missing right-to-withdraw/erase disclosure; no legal-basis disclosure on collection
Related: gdpr_art6, gdpr_art9, gdpr_art22, gdpr_art46, gdpr_art47, gdpr_art49

## gdpr_art14
Reference: GDPR Art. 14
Title: Information to be provided where personal data have not been obtained from the data subject
Regulation: GDPR
Source CELEX: 32016R0679

Summary: When you ingest personal data from a third party (not the user directly), you must inform the data subject of the controller, purposes, data categories, recipients, retention, their rights, and the data's source. This must happen within one month, or at first contact/disclosure, whichever is sooner.
Developer impact: Build automated notification workflows (email/SMS templates with timing triggers) that fire when data is acquired from external sources.
Code smells: ingest third-party data without notification job; first-contact email/SMS omits source disclosure; no scheduled privacy notice within 30-day deadline; notification payload missing rights/retention/transfer info; import script lacks Art.14 notice queue
Related: gdpr_art6, gdpr_art9, gdpr_art22, gdpr_art46, gdpr_art47, gdpr_art49

## gdpr_art15
Reference: GDPR Art. 15
Title: Right of access by the data subject
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Users can request confirmation that their data is processed plus a copy of it, along with metadata: purposes, categories, recipients, retention, source, rights, and any automated-decision logic. Provide the copy in a commonly used electronic format and don't expose other people's data.
Developer impact: Implement a Subject Access Request export API/UI that returns the user's data plus required processing metadata in a standard format like JSON/CSV.
Code smells: SAR export hardcodes automated-decision flag to false; export omits retention/recipients/source metadata; data dump in proprietary binary not JSON/CSV; export leaks third parties' personal data; incomplete copy not aggregated across stores
Related: gdpr_art22, gdpr_art46

## gdpr_art16
Reference: GDPR Art. 16
Title: Right to rectification
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Users have the right to correct inaccurate personal data and complete incomplete data without undue delay, including via a supplementary statement. Your system must let them update their records.
Developer impact: Provide update/PATCH endpoints and editable UI so users can correct or complete their personal data, propagating fixes downstream.
Code smells: no PUT/PATCH on user profile endpoint; immutable store with no correction event; update silently drops supplementary fields; UI shows data but offers no edit form; corrections not propagated downstream; stale cache not invalidated on update

## gdpr_art17
Reference: GDPR Art. 17
Title: Right to erasure ('right to be forgotten')
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Users can demand deletion of their personal data without undue delay on grounds like consent withdrawal or data no longer needed; you must erase it across all systems. If the data was made public, take reasonable steps to tell other controllers to delete copies/links. Some legal-obligation/public-interest exceptions apply.
Developer impact: Build deletion workflows with cascading deletes and downstream/third-party erasure propagation that fully remove or anonymize user records.
Code smells: soft-delete flag leaves PII in tables/logs; deletion not cascaded to NoSQL/secondary store; no webhook to propagate erasure to third parties; cache retains PII with no TTL after delete; search index not scrubbed on deletion
Related: gdpr_art6, gdpr_art8, gdpr_art9, gdpr_art21, gdpr_art89

## gdpr_art18
Reference: GDPR Art. 18
Title: Right to restriction of processing
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Users can require you to halt active processing (analytics, sharing, automated decisions) while still storing the data, e.g. while accuracy is disputed. Restricted data may then only be stored or processed with consent or for legal claims. Notify the user before lifting any restriction.
Developer impact: Implement a restriction state flag plus access controls that stop all processing except storage, and notify before lifting it.
Code smells: batch/ML job ignores processing_restricted flag; restricted records still queried by analytics; third-party sync ignores RESTRICTED status; marketing scheduler skips restriction flag; restriction lifted with no pre-notification
Related: gdpr_art21

## gdpr_art19
Reference: GDPR Art. 19
Title: Notification obligation regarding rectification or erasure of personal data or restriction of processing
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Whenever you rectify, erase, or restrict data, you must communicate that change to every recipient you previously disclosed the data to, unless impossible or disproportionate. On request, tell the user who those recipients were.
Developer impact: Implement event-driven webhooks/API integrations that propagate corrections, deletions, and restrictions to downstream recipients, and track sharing history.
Code smells: delete/update not emitted to external recipient API; correction not pushed to downstream system; restriction flag not forwarded to partners; no tombstone event to downstream consumers; no record of recipients data was shared with
Related: gdpr_art16, gdpr_art17, gdpr_art18

## gdpr_art20
Reference: GDPR Art. 20
Title: Right to data portability
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Where processing is consent- or contract-based and automated, users can receive the data they provided in a structured, commonly used, machine-readable format and have it transmitted to another controller, directly where feasible. Don't hinder the transfer or harm others' rights.
Developer impact: Build a data export feature that emits structured machine-readable output (JSON/CSV) and optionally an API for direct controller-to-controller transfer.
Code smells: export as flattened PDF not structured JSON/CSV; export omits user-provided data; proprietary/encrypted format unparseable by others; no API for direct transfer to another provider; manual copy-paste instead of bulk download
Related: gdpr_art6, gdpr_art9, gdpr_art17

## gdpr_art21
Reference: GDPR Art. 21
Title: Right to object
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Users can object at any time to processing based on legitimate interest or public task, including profiling; you must stop unless overriding grounds exist. For direct marketing, objection is absolute and must be honored. Flag this right at first contact and allow automated objection (e.g. GPC). Per the linked ePrivacy Directive, electronic direct marketing needs prior consent and an easy opt-out.
Developer impact: Implement opt-out toggles/endpoints and flags that immediately halt marketing and profiling, and honor automated objection signals.
Code smells: profiling ignores has_objected flag; marketing batch job skips marketing_opt_out filter; ignores GPC/automated objection HTTP headers; no UI toggle/API to object to processing; export to marketing tool includes objected users
Related: gdpr_art6, gdpr_art89

## gdpr_art22
Reference: GDPR Art. 22
Title: Automated individual decision-making, including profiling
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Users have the right not to be subject to decisions made solely by automated processing (including profiling) that significantly affect them, unless contract-necessary, legally authorized, or consented. Even then you must allow human review, contesting, and input. Such decisions must not use special-category data without explicit consent/safeguards.
Developer impact: Add human-review fallbacks, appeal/contest endpoints, consent verification, and exclude sensitive-category data from automated decision models.
Code smells: auto-reject/ban with no manual review endpoint; automated decision lacks appeal/contest mechanism; model uses special-category data without consent check; no human-override state in decision flow; no logged decision logic for human auditor
Related: gdpr_art9

## gdpr_art24
Reference: GDPR Art. 24
Title: Responsibility of the controller
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Controllers must put in place technical and organizational measures to ensure processing follows GDPR and to prove it. Measures must be risk-proportionate and reviewed/updated over time; data-protection policies and certifications help demonstrate compliance.
Developer impact: Maintain controller-accountability controls that show who owns processing decisions, which safeguards apply, and when those safeguards are reviewed or updated. Do not use this article as a catch-all for ordinary security, minimization, retention, or logging defects.
Code smells: no owner or policy reference for a processing workflow; privacy-impact override approvals are not recorded; safeguards are disabled globally with no review trail; no evidence that controller measures are periodically reviewed; accountability metadata is missing from high-risk processing changes
Related: gdpr_art40, gdpr_art42

## gdpr_art25
Reference: GDPR Art. 25
Title: Data protection by design and by default
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Build privacy in from the design stage using measures like pseudonymization and data minimization. By default, only data necessary for each purpose should be collected, processed, stored, and exposed, and personal data must not be made accessible to others without user action.
Developer impact: Default to private settings, minimize collected fields, pseudonymize, and enforce automatic retention limits in code.
Code smells: default visibility set to public not private; indefinite retention, no TTL by data category; marketing/consent flag defaults to true; SELECT * pulls unneeded sensitive columns; raw identifiers stored without pseudonymization
Related: gdpr_art42

## gdpr_art26
Reference: GDPR Art. 26
Title: Joint controllers
Regulation: GDPR
Source CELEX: 32016R0679

Summary: When two or more controllers jointly decide why and how data is processed, they must agree and document their respective responsibilities, especially for data-subject rights and required disclosures. The essence of that arrangement must be shown to users, who can exercise rights against any controller.
Developer impact: Surface joint-controller arrangements in the UI and accept/process rights requests no matter which controller the user contacts.
Code smells: rights request rejected and redirected to partner; missing joint-controller disclosure in UI; consent withdrawal not propagated to co-controller; DSAR dropped when data jointly controlled; deletion request not synced between partners
Related: gdpr_art13, gdpr_art14

## gdpr_art28
Reference: GDPR Art. 28
Title: Processor
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Processors may only act on the controller's documented instructions under a binding contract, must keep data confidential and secure, and must not add sub-processors without authorization. They must help the controller with data-subject rights, delete or return data at contract end, and support audits.
Developer impact: Implement controller-scoped config, tenant isolation, deletion/export APIs, sub-processor checks, and audit logging.
Code smells: third-party data transfer ignores controller config flags; no tenant data-deletion endpoint at contract end; shared table without strict tenant ID isolation; no audit log for staff access to PII; hardcoded data residency region with no transfer check
Related: gdpr_art32, gdpr_art33, gdpr_art34, gdpr_art35, gdpr_art36, gdpr_art40

## gdpr_art29
Reference: GDPR Art. 29
Title: Processing under the authority of the controller or processor
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Anyone with access to personal data under a controller or processor may only process it on the controller's instructions, unless required by law. This means processing must be gated by the controller's explicit configuration rather than initiated independently.
Developer impact: Gate all processing behind the controller's explicit instructions/config flags; never process or share data autonomously.
Code smells: cross-tenant aggregation without per-tenant opt-in; data forwarded to third party ignoring tenant config; prod data copied to staging without instruction; secondary processing added without controller config; full payload logged beyond authorized metadata

## gdpr_art30
Reference: GDPR Art. 30
Title: Records of processing activities
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Controllers and processors must keep written records of processing: purposes, data and subject categories, recipients, cross-border transfers and safeguards, retention limits, and security measures. Required even for small orgs if processing is risky, non-occasional, or involves special/criminal data.
Developer impact: Track metadata (data category, purpose, retention, recipients, transfers) in governance/audit systems to maintain processing records.
Code smells: pipeline lacks purpose/category metadata tags; export omits recipient and cross-border transfer logs; no retention/erasure time-limit in schema; missing controller contact in processing manifest; transfer destination country not logged in audit trail
Related: gdpr_art9, gdpr_art10, gdpr_art32, gdpr_art49

## gdpr_art32
Reference: GDPR Art. 32
Title: Security of processing
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Controllers and processors must apply risk-appropriate security measures including pseudonymization, encryption, ongoing confidentiality/integrity/availability, the ability to restore data after an incident, and regular testing of those measures.
Developer impact: Encrypt data at rest and in transit, pseudonymize, enforce access controls, and ensure backups/recovery.
Code smells: PII over unencrypted HTTP between services; credit card / PII logged in plaintext; no rate limit enables brute-force data extraction; weak password hashing (MD5/SHA1) not bcrypt/Argon2; PII in cache without auth or network isolation
Related: gdpr_art40, gdpr_art42

## gdpr_art33
Reference: GDPR Art. 33
Title: Notification of a personal data breach to the supervisory authority
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Controllers must report a breach to the supervisory authority without undue delay and within 72 hours unless it poses no risk; processors must alert the controller promptly. Reports must describe the breach nature, affected categories/counts, DPO contact, likely consequences, and remedial measures, and breaches must be documented.
Developer impact: Build incident response that fires breach notifications within 72h with required fields and persistently logs breach facts.
Code smells: hardcoded delay exceeds 72-hour notification window; notification payload omits affected record count; missing DPO contact in breach alert body; breach logs in volatile cache not persisted; no timestamp of first breach detection
Related: gdpr_art55

## gdpr_art34
Reference: GDPR Art. 34
Title: Communication of a personal data breach to the data subject
Regulation: GDPR
Source CELEX: 32016R0679

Summary: When a breach is high-risk to individuals, the controller must tell affected users without undue delay in clear language, including DPO contact, likely consequences, and remedial measures. Not required if data was encrypted/unintelligible, risk was mitigated, or a public notice is used instead.
Developer impact: Implement user-facing breach notifications (with encryption checks deciding if required) using plain-language templates.
Code smells: breach email fails silently on SMTP timeout; plaintext storage voids encryption exemption; breach notice sends raw stack trace not plain language; missing DPO contact in user breach alert; user breach notification queued at low priority
Related: gdpr_art33

## gdpr_art38
Reference: GDPR Art. 38
Title: Position of the data protection officer
Regulation: GDPR
Source CELEX: 32016R0679

Summary: If your org has a Data Protection Officer (DPO), they must be looped into all data-protection decisions, given the resources and data access to do their job, act independently, and be reachable by users. Users must be able to contact the DPO about their data and rights.
Developer impact: Expose a working DPO contact channel to users and grant the DPO role read access to processing operations/logs.
Code smells: DPO contact form routed to wrong/generic inbox; no DPO contact link in privacy/data-rights UI; RBAC denies DPO role access to audit logs; DPO mailto link removed from data-export flow; DPO service account blocked from processing metrics
Related: gdpr_art39

## gdpr_art44
Reference: GDPR Art. 44
Title: General principle for transfers
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Personal data may only leave the EEA to a third country or international org if this chapter's conditions are met, including for onward re-transfers. The EU level of protection must follow the data wherever it goes.
Developer impact: Gate any cross-border data flow (API, webhook, cloud/CDN routing) behind transfer-legality checks and EEA data-residency constraints.
Code smells: hardcoded non-EEA endpoint for EU personal data; webhook forwards PII outside EEA with no safeguards; third-party SDK syncs PII to non-EEA server; backup/replication to third-country cluster; CDN edge caches personal data outside EEA

## gdpr_art46
Reference: GDPR Art. 46
Title: Transfers subject to appropriate safeguards
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Without an adequacy decision, you may transfer data abroad only if appropriate safeguards exist (Standard Contractual Clauses, Binding Corporate Rules, approved codes/certifications) and users retain enforceable rights. Some routes need supervisory-authority authorization.
Developer impact: Route/block outbound cross-border transfers based on presence of a validated legal safeguard (SCC/BCR) for the destination.
Code smells: cross-border API call lacks SCC/safeguard validation; sync to non-EU bucket with no regional routing; webhook POSTs PII abroad without SCCs; third-party widget/SDK in third country gets PII; no data-residency enforcement on telemetry sink
Related: gdpr_art40, gdpr_art42, gdpr_art45, gdpr_art47, gdpr_art63, gdpr_art93

## gdpr_art48
Reference: GDPR Art. 48
Title: Transfers or disclosures not authorised by Union law
Regulation: GDPR
Source CELEX: 32016R0679

Summary: A foreign court or authority order to hand over personal data is only enforceable if backed by an international agreement (e.g. an MLAT) with the EU/Member State. You can't auto-comply with third-country legal demands otherwise.
Developer impact: Validate foreign authority/legal-disclosure requests against treaty (MLAT) authorization before exporting any personal data.
Code smells: auto-fulfills foreign subpoena with no legal-basis check; no MLAT/treaty validation on disclosure request; law-enforcement portal auto-approves non-EU requests; e-discovery export skips authorization check; no jurisdiction-check middleware on data-query API

## gdpr_art49
Reference: GDPR Art. 49
Title: Derogations for specific situations
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Lacking adequacy or safeguards, a transfer is allowed only via a narrow derogation: explicit informed consent, contract necessity, legal claims, vital/public interest, or public registers. Last-resort transfers must be non-repetitive, limited in scope, documented, and notified.
Developer impact: Before fallback cross-border transfers, check explicit-consent/necessity flags, filter to the minimal data subset, and log the transfer.
Code smells: transfer skips explicit international_transfer_consent flag; bulk DB replicated abroad with no per-record consent filter; transfer not limited to necessary data subset; no audit log/justification for cross-border transfer; whole register exposed instead of scoped request
Related: gdpr_art13, gdpr_art14, gdpr_art30, gdpr_art45, gdpr_art46

## gdpr_art86
Reference: GDPR Art. 86
Title: Processing and public access to official documents
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Public bodies (or private bodies doing public-interest tasks) may disclose personal data in official documents to satisfy freedom-of-information access, but only as national/EU law permits, balancing transparency against privacy.
Developer impact: Add redaction/filtering/access controls to FOIA portals and open-data APIs so published documents don't leak PII.
Code smells: public API serves unredacted names/addresses; no middleware to strip PII before publishing; open-data export includes raw IDs/birthdates; document metadata leaks personal names; phone numbers unmasked in public transcripts

## gdpr_art87
Reference: GDPR Art. 87
Title: Processing of the national identification number
Regulation: GDPR
Source CELEX: 32016R0679

Summary: National ID numbers (or any general-purpose identifier) may only be processed under appropriate safeguards for the data subject's rights, as further specified by Member State law. Treat them as highly sensitive identifiers.
Developer impact: Encrypt, hash, or mask national ID numbers everywhere: storage, logs, URLs, and UI responses.
Code smells: national ID stored unencrypted in DB; national ID logged in plaintext; unmasked national ID in API response/HTML; national ID passed as URL query param; national ID used as primary/public user key

## gdpr_art89
Reference: GDPR Art. 89
Title: Safeguards and derogations relating to processing for archiving, scientific or historical research, or statistical purposes
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Processing for archiving, research, or statistics needs safeguards enforcing data minimisation, preferring pseudonymisation or full anonymisation where the purpose still works. Member State law may then derogate from certain data-subject rights (access, rectification, etc.).
Developer impact: In research/analytics/archive pipelines, pseudonymise or anonymise and minimise data before storing or modeling.
Code smells: raw identifiers (name/SSN/VIN) in research dataset; analytics pipeline pulls unmasked PII from prod; archive lacks pseudonymisation/tokenisation; no k-anonymity/differential privacy on public microdata; stats retain direct identifiers with no minimisation
Related: gdpr_art15, gdpr_art16, gdpr_art18, gdpr_art19, gdpr_art20, gdpr_art21
