# Precommiteu public regulation context - DORA
Included regulations: DORA (Digital Operational Resilience Act), CELEX 32022R2554.

Compact, developer-oriented SUMMARIES of code-relevant DORA articles - NOT the
legal text. Used to (a) retrieve the probable article area for a scanner finding
and (b) show a short "why this matters" snippet in PR comments. For the
authoritative wording, follow the EUR-Lex link rendered with each finding.

# DORA (Digital Operational Resilience Act)

## dora_art6
Reference: DORA Art. 6
Title: ICT risk management framework
Regulation: DORA
Source CELEX: 32022R2554

Summary: Financial firms must run a documented ICT (information and communication technology - i.e. IT systems and software) risk management framework. It must protect all software, hardware, and data from damage and unauthorized access, detect incidents, and keep risk information current for regulators. Risk oversight stays independent from development.
Developer impact: Tag and protect assets in IaC, emit availability/risk KPIs, turn scan findings into tracked remediation tickets, and keep risk-register entries complete.
Code smells: IaC provisions databases without encryption/backup/ownership metadata; vuln-scan findings exported but no remediation ticket created; risk_register entry written with empty owner/deadline fields; no KPI/KRI (key performance/risk indicator) emitted for availability or privileged-access changes; CI deploys with unscanned secrets
Related: dora_art8, dora_art9, dora_art10, dora_art11

## dora_art7
Reference: DORA Art. 7
Title: ICT systems, protocols and tools
Regulation: DORA
Source CELEX: 32022R2554

Summary: ICT systems must be reliable, kept updated, and sized to handle peak order, message, and transaction volumes. They must keep working under stressed market conditions and adverse situations. Capacity and resilience are legal requirements, not just ops concerns.
Developer impact: Add rate limiting, backpressure, autoscaling, and streaming for large batches; run load tests for peak volumes; keep runtimes and dependencies on supported versions.
Code smells: ingestion API with rate_limit=None; hardcoded pool_size/max_connections with no autoscaling path; batch job loads a full table into memory via fetchall(); single unpartitioned consumer for market-data traffic; runtime image pinned to an unsupported version with no CI check
Related: dora_art10, dora_art11

## dora_art8
Reference: DORA Art. 8
Title: Identification
Regulation: DORA
Source CELEX: 32022R2554

Summary: Firms must identify and document every ICT asset: its business function, owner, criticality, configuration, and dependencies, including remote sites and third-party links. Inventories must be refreshed continuously, and every major infrastructure change needs a risk assessment.
Developer impact: Tag every IaC resource with function/owner/criticality, declare third-party API dependencies in manifests, and trigger a risk assessment on major infra changes.
Code smells: Terraform resource without asset/owner/criticality tags; service-registry entry with owner=null; new external API added without a manifest/inventory entry; deploy pipeline skips the risk-assessment step on a major change; dependency map missing remote-site or hardware assets
Related: dora_art6, dora_art28

## dora_art9
Reference: DORA Art. 9
Title: Protection and prevention
Regulation: DORA
Source CELEX: 32022R2554

Summary: Firms must continuously protect ICT systems with security tooling. Data must stay available, authentic, intact, and confidential at rest, in use, and in transit. That means encryption, strong authentication, least-privilege access, and automated network isolation.
Developer impact: Enforce TLS with certificate verification, encrypt data at rest, require MFA on privileged access, scope roles tightly, rotate keys, and automate isolation of compromised assets.
Code smells: customer data sent over http:// or with verify=False; payment tokens stored unencrypted; admin login with mfa_enabled=False; endpoint open to any authenticated user with no role check; security group open to 0.0.0.0/0; unmanaged local keys with rotation disabled
Related: dora_art6, dora_art10, dora_art45

## dora_art10
Reference: DORA Art. 10
Title: Detection
Regulation: DORA
Source CELEX: 32022R2554

Summary: Firms must promptly detect anomalous activity, network performance problems, and ICT incidents. Detection needs alert thresholds and automatic alerts to response staff, plus monitoring of user activity. Data reporting providers must also check trade reports for completeness and errors.
Developer impact: Wire alert thresholds on metrics, alert on anomalies and user-activity spikes, never swallow exceptions silently, and validate trade reports with re-transmission requests.
Code smells: alerts_enabled=False on a production service; except: pass with no anomaly counter or alert; metrics collected but no alert_threshold defined; failed-auth or transaction spikes unmonitored; trade-report ingestion with no completeness or omission check
Related: dora_art17, dora_art25

## dora_art11
Reference: DORA Art. 11
Title: Response and recovery
Regulation: DORA
Source CELEX: 32022R2554

Summary: Firms need a tested ICT business continuity plan. Code must keep critical functions running, contain incidents quickly, activate response plans without delay, fail over to redundant capacity, and log disruption events durably for later review.
Developer impact: Implement automated failover/switchover, circuit breakers on dependency outages, containment hooks in incident automation, and durable disruption logging.
Code smells: single primary DB endpoint with no failover path; infinite retry loop with no circuit_breaker during an outage; disruption events written only to local disk; switchover for a critical service depends on manual commands only; no containment/isolation step in incident playbook automation
Related: dora_art12, dora_art14, dora_art17, dora_art61

## dora_art12
Reference: DORA Art. 12
Title: Backup policies and procedures, restoration and recovery procedures and methods
Regulation: DORA
Source CELEX: 32022R2554

Summary: Firms must back up data with scope and frequency set by criticality, and restore with minimal downtime and loss. Restore systems must be physically and logically segregated from the source. Backup and restore procedures must be tested periodically.
Developer impact: Drive backup schedules from criticality tags, restore into segregated infrastructure, encrypt and integrity-check backups, and gate backup-config changes on restore tests.
Code smells: one hardcoded daily backup schedule for all systems; restore environment in the same VPC/subnet as the primary; backups without KMS encryption, versioning, or integrity hashes; CI changes backup retention without a restore test
Related: dora_art11, dora_art61

## dora_art14
Reference: DORA Art. 14
Title: Communication
Regulation: DORA
Source CELEX: 32022R2554

Summary: Firms need crisis communication plans for major ICT incidents. Clients, counterparties, and the public must be informed through responsible disclosure. Internal alerting must separate response staff from staff who only need to be informed. One named person owns the communication role.
Developer impact: Build automated client/counterparty notification flows, a status page with a real major-incident disclosure path, and role-based alert routing with distinct recipient groups.
Code smells: major-incident branch updates an internal dashboard but never notifies clients; status_page shows only a generic message with no disclosure path; alert routing sends every incident to one channel for all staff; comms tooling has no named owner; counterparty recipient mapping missing from runbooks
Related: dora_art17, dora_art19

## dora_art16
Reference: DORA Art. 16
Title: Simplified ICT risk management framework
Regulation: DORA
Source CELEX: 32022R2554

Summary: Small exempted firms (small investment firms, exempt payment and e-money institutions, small pension providers) follow a lighter framework. They must still monitor security continuously, protect data confidentiality and integrity, detect anomalies fast, map key third-party dependencies, and keep backup and restoration working.
Developer impact: Even under the simplified regime, keep monitoring, encryption, anomaly alerts, least-privilege access, and backup/restore in place.
Code smells: exempt-entity service with health checks but no security telemetry; wallet ledger persisted without encryption or integrity checks; OAuth scopes granting broad production access; no anomaly rules for failed-auth spikes; CI promotes changes with resilience tests skipped
Related: dora_art6, dora_art9, dora_art10, dora_art12

## dora_art17
Reference: DORA Art. 17
Title: ICT-related incident management process
Regulation: DORA
Source CELEX: 32022R2554

Summary: Firms must run a defined incident management process: detect, record, classify, and follow up on every ICT incident and significant cyber threat. Root causes must be documented and fixed. Major incidents must be escalated to senior management with impact and response details.
Developer impact: Create incident-register entries from alerts, capture severity/priority/criticality and root cause, add early-warning indicators, and wire escalation paths to management.
Code smells: alert fires but no incident_register entry is created; rollback restores service without recording incident or root_cause; incident record missing severity/priority fields; cyber threat logged as a generic error with no early-warning indicator; no escalation path for major incidents
Related: dora_art10, dora_art14, dora_art18, dora_art19

## dora_art18
Reference: DORA Art. 18
Title: Classification of ICT-related incidents and cyber threats
Regulation: DORA
Source CELEX: 32022R2554

Summary: Incidents must be classified using set criteria: clients and transactions affected, downtime duration, geographic spread across Member States, data losses, criticality of services hit, and economic impact. Cyber threats are rated significant by similar criteria. These numbers decide what counts as a major incident.
Developer impact: Compute and log classification metrics - affected clients, transaction counts, downtime, member-state spread, data-loss type, and cost - directly in incident tooling.
Code smells: classifier ranks incidents by HTTP error rate alone; severity set from static labels instead of computed criteria; downtime/affected_clients fields absent or hardcoded; no member-state or geographic-spread calculation; data-loss dimensions (availability/integrity/confidentiality) never assessed
Related: dora_art17, dora_art19

## dora_art19
Reference: DORA Art. 19
Title: Reporting of major ICT-related incidents and voluntary notification of significant cyber threats
Regulation: DORA
Source CELEX: 32022R2554

Summary: Major ICT incidents must be reported to the competent authority (the national financial supervisor) using official templates: an initial notification, intermediate reports when status changes, and a final report after root cause analysis. If the reporting channel fails, an alternative means must be used. Significant cyber threats may be notified voluntarily.
Developer impact: Generate template-based payloads to authority channels, add a fallback delivery path, trigger intermediate reports on status change, and complete final reports with real figures.
Code smells: major incident opens an internal ticket but never enqueues an authority notification; free-text email built instead of the template payload; no fallback channel when the regulator API is down; final report closes with estimated impacts and incomplete root cause
Related: dora_art14, dora_art17, dora_art18

## dora_art25
Reference: DORA Art. 25
Title: Testing of ICT tools and systems
Regulation: DORA
Source CELEX: 32022R2554

Summary: Resilience testing must include vulnerability assessments and scans, open-source analyses, network security assessments, source code reviews, scenario tests, performance and end-to-end testing, and penetration tests. Operators of securities settlement and clearing systems must run vulnerability assessments before every deployment of components supporting critical functions.
Developer impact: Keep vuln scans, dependency analysis, code scans, and pre-deployment assessments as blocking steps in CI/CD pipelines.
Code smells: deploy workflow with the vulnerability-scan step removed or commented out; continue-on-error: true on a security-scan job; scan_enabled=False in pipeline config; release gate with no open-source dependency analysis; critical-function redeploy with no pre-deployment assessment
Related: dora_art9, dora_art10

## dora_art28
Reference: DORA Art. 28
Title: General principles
Regulation: DORA
Source CELEX: 32022R2554

Summary: Firms stay fully responsible when ICT services are outsourced. Every provider must be recorded and classified by whether it supports a critical or important function. Firms need exit strategies: tested ways to export data and migrate to another provider without losing integrity.
Developer impact: Record provider details in the register of information, tag dependencies by criticality, check concentration risk, and build verified exit-export jobs.
Code smells: vendor record created without critical-function classification; workload deployed to a provider with no register_of_information entry; exit export job with no integrity/completeness checks; same provider for production and DR (disaster recovery) with no concentration check; subcontractor chain not recorded
Related: dora_art8, dora_art30

## dora_art30
Reference: DORA Art. 30
Title: Key contractual provisions
Regulation: DORA
Source CELEX: 32022R2554

Summary: Contracts with ICT providers must pin down concrete technical capabilities: where data is processed and stored (with advance notice of location changes), data protection guarantees, full service-level descriptions, and access, recovery, and return of data in an accessible format if the provider fails or the contract ends.
Developer impact: Enforce allowed regions in IaC, emit SLA telemetry (uptime, latency, incident counts) with breach alerts, and provide tested export APIs returning data in JSON/CSV.
Code smells: IaC permits deployment to unapproved regions; data_location for processing/storage never recorded; no uptime/latency telemetry against SLA targets; no tested export job returning data in json/csv on termination
Related: dora_art28

## dora_art45
Reference: DORA Art. 45
Title: Information-sharing arrangements on cyber threat information and intelligence
Regulation: DORA
Source CELEX: 32022R2554

Summary: Firms may share cyber threat intelligence (indicators of compromise, tactics, techniques, alerts) inside trusted communities. The sharing must protect sensitive business information and personal data. In code that means redaction, anonymization, secure transport, and membership checks.
Developer impact: Redact or pseudonymize customer identifiers in shared IOCs, use mTLS and payload signing for threat feeds, and validate community membership before accepting or serving intel.
Code smells: STIX/TAXII payload includes raw account numbers, IBANs, or session cookies; threat feed posted over http:// with no mTLS or signing; sharing portal serves intel without membership validation; production API keys committed with detection rules; IOC packages in a public bucket
Related: dora_art9

## dora_art61
Reference: DORA Art. 61
Title: Amendments to Regulation (EU) No 909/2014
Regulation: DORA
Source CELEX: 32022R2554

Summary: This article rewrites the operational-risk rules for central securities depositories (CSDs). A CSD must recover all transactions and participant positions at the exact time of disruption so settlement completes on schedule. State must be durable before acknowledgement.
Developer impact: Persist transaction state before ack, use synchronous replication or durable checkpoints for positions, make settlement submissions idempotent, and keep replayable message logs.
Code smells: settlement instruction acknowledged before a durable write; replication_mode="async" on the settlement DB; positions computed in memory with no checkpoint; DR restores a nightly backup instead of disruption-timestamp state; non-idempotent settlement submission job; feed with no durable queue or replay offset
Related: dora_art11, dora_art12
