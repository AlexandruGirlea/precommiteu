# Precommiteu public regulation context - DORA
Included regulations: DORA (Digital Operational Resilience Act), CELEX 32022R2554.

Compact, developer-oriented SUMMARIES of code-relevant DORA articles - NOT the
legal text. Used to (a) retrieve the probable article area for a scanner finding
and (b) show a short "why this matters" snippet in PR comments. For the
authoritative wording, follow the EUR-Lex link rendered with each finding.

# DORA (Digital Operational Resilience Act)

Scope and evidence: code smells below are investigation leads, not automatic violations. Establish the applicable actor, activity, conditions and exceptions from the supplied context; missing information in one excerpt is not proof of a system-wide omission.

Applicability: Establish a covered financial entity and the applicable duty for every article, including backups and recovery. A retail/health application or payment-like variable alone does not establish DORA scope. A microenterprise is not automatically an Article 16 entity; duties and individual exemptions must be checked separately.

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

Summary: Financial entities need appropriate backup and restoration arrangements, secure restoration systems, recovery objectives tied to function criticality and necessary integrity checks/reconciliation after recovery, including reconstruction from external stakeholders (12(7)).
Developer impact: Establish financial-entity scope for every backup finding. CSD transaction recovery is art61; CCP recovery of all transactions at disruption is addressed by 12(3). No keyword automatically establishes an architectural failure.
Code smells: A supplied recovery path explicitly bypasses required integrity/reconciliation checks before returning restored data to service; a demonstrated backup or restoration control defeats confidentiality, integrity or recoverability.
Related: dora_art11, dora_art61
Conditions and exceptions: Verification occurs in a shown recovery component; an unseen helper may perform it; a shared VPC/account/region or absent encryption/versioning keyword alone is offered as proof that required segregation/security is absent.

## dora_art14
Reference: DORA Art. 14
Title: Communication
Regulation: DORA
Source CELEX: 32022R2554

Summary: Financial entities need crisis-communication plans enabling responsible disclosure as appropriate, differentiated communication to response staff and staff who need informing, and an assigned public/media communication function.
Developer impact: Article 14 addresses crisis-communication planning; Article 19(3) addresses client notification for major incidents affecting their financial interests.
Code smells: The actual crisis-communication configuration explicitly disables the required communication arrangements or collapses the required staff roles.
Related: dora_art17, dora_art19
Conditions and exceptions: The claim demands public disclosure of every incident; the defect is notification of a particular major incident to affected clients (art19(3)) or the internal incident record (art17).

## dora_art16
Reference: DORA Art. 16
Title: Simplified ICT risk management framework
Regulation: DORA
Source CELEX: 32022R2554

Summary: The simplified framework replaces Articles 5-15 only for the specified small non-interconnected investment firms, exempt payment/e-money or qualifying CRD institutions, and small occupational retirement institutions. Microenterprise status alone does not establish eligibility.
Developer impact: Establish the legal category, then the defect. Incident, testing and third-party duties outside Articles 5-15 need their own scope/exemption assessment; Article 16 does not replace them all.
Code smells: An entity established to fall under Article 16 bypasses one of its applicable protection, monitoring, continuity, backup or testing requirements.
Related: dora_art6, dora_art9, dora_art10, dora_art12
Conditions and exceptions: Only microenterprise, small_firm or an unrelated exempt token appears; the actor is not in the specified class; the allegation concerns a duty outside the Articles 5-15 replacement.

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

Summary: Financial entities report major ICT-related incidents to the competent authority. Under 19(3), a major incident affecting clients' financial interests also requires prompt client information about the incident and mitigation; potentially affected clients receive appropriate protection advice for significant cyber threats.
Developer impact: Assess authority and client branches separately under art19; crisis-communication planning is art14. Article 19(4)(c) distinguishes final actual-impact figures from earlier estimates; 19(5) permits outsourced reporting without removing responsibility.
Code smells: An established applicable authority or client notification is explicitly disabled or unjustifiably delayed; required information is knowingly withheld from the applicable reporting stage.
Related: dora_art14, dora_art17, dora_art18
Conditions and exceptions: The major-incident or significant-threat trigger is not established; the allegation rests only on estimates in an initial report, lack of a particular function name, or an unseen reporting component; classification itself is the defect (art18).

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

Summary: Article 61 amends CSDR operational-risk rules for central securities depositories, including recovery of all transactions and participants' positions at disruption so settlement can complete on schedule.
Developer impact: Trace persistence, acknowledgement and replay together. An in-memory collection or asynchronous replication alone does not establish unrecoverable CSD state.
Code smells: A demonstrated CSD recovery design irretrievably loses acknowledged transactions or participant positions needed at disruption; restoration cannot reconstruct them from the established durable sources.
Related: dora_art11, dora_art12
Conditions and exceptions: An in-memory queue/cache is rebuilt from a durable journal or store; durable recovery sources are outside the excerpt; only generic settlement/payment words establish the supposed CSD role; a central counterparty duty belongs under art12(3).
