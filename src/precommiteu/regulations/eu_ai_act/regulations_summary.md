# Precommiteu public regulation context - EU AI ACT
Included regulations: EU AI ACT (EU Artificial Intelligence Act), CELEX 32024R1689.

Compact, developer-oriented SUMMARIES of code-relevant EU AI Act articles - NOT the
legal text. Used to (a) retrieve the probable article area for a scanner finding
and (b) show a short "why this matters" snippet in PR comments. For the
authoritative wording, follow the EUR-Lex link rendered with each finding.

# EU AI ACT (EU Artificial Intelligence Act)

Scope and evidence: code smells below are investigation leads, not automatic violations. Establish the applicable actor, activity, conditions and exceptions from the supplied context; missing information in one excerpt is not proof of a system-wide omission.

Applicability: Apply the actor, system class and activity required by the particular article. Generic ML, a CE-related filename, or a sandbox name alone does not establish high-risk status, systemic-risk GPAI or a regulatory sandbox. Do not infer a missing system-wide control from one file.

## eu_ai_act_art5
Reference: EU AI ACT Art. 5
Title: Prohibited AI practices
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Bans certain AI uses outright: emotion recognition at work or school, social scoring, untargeted face-image scraping for recognition databases, biometric categorisation by sensitive traits, manipulation or exploitation, and crime prediction based only on profiling. No safeguard makes these lawful - the code path itself must not run.
Developer impact: Remove or hard-block code that runs emotion inference on employees or students, bulk-scrapes faces, computes social scores, or infers sensitive traits from biometric data.
Code smells: emotion model wired to a workplace or classroom camera feed; scraper bulk-downloading face images into a matching database; score ranking people by social behaviour gating services
Related: eu_ai_act_art10, eu_ai_act_art50

## eu_ai_act_art9
Reference: EU AI ACT Art. 9
Title: Risk management system
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: High-risk AI systems need a documented, continuously updated risk management process: identify foreseeable risks, estimate them under intended use and misuse, test the system against defined metrics and thresholds, and apply targeted mitigations before release.
Developer impact: Wire risk-assessment jobs, threshold-gated test suites, and mitigation steps into the ML pipeline and make release gates depend on them.
Code smells: deploy step skipping the risk-assessment job; acceptance threshold loosened or disabled to force a release; safety guardrail commented out
Related: eu_ai_act_art15, eu_ai_act_art17, eu_ai_act_art72

## eu_ai_act_art10
Reference: EU AI ACT Art. 10
Title: Data and data governance
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Training, validation and test datasets for high-risk AI need governance: documented origin and purpose, bias examination and mitigation, and relevance/representativeness checks. Special-category data used for bias correction needs strict access controls, pseudonymisation, and deletion once no longer needed.
Developer impact: Add bias-detection steps, provenance metadata, pseudonymisation, access controls, and automated deletion of sensitive fields to training pipelines.
Code smells: training pipeline ingesting health/ethnicity fields with no pseudonymisation; bias-check step removed or skipped; special-category rows kept after bias correction with no deletion job; dataset loaded without origin/provenance metadata
Related: eu_ai_act_art5, eu_ai_act_art9, eu_ai_act_art59

## eu_ai_act_art11
Reference: EU AI ACT Art. 11
Title: Technical documentation
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Technical documentation for a high-risk AI system must exist before it goes on the market and be kept up to date. It must contain the mandated minimum elements (system description, intended purpose, metrics, design choices) so authorities can assess compliance.
Developer impact: Automate model-card and documentation generation in CI, track model metadata (version, purpose, metrics), and regenerate docs on every model update.
Code smells: model-card generation step skipped or disabled at release; model metadata fields (version, intended purpose, metrics) written empty; documentation not regenerated after a model update
Related: eu_ai_act_art13, eu_ai_act_art18, eu_ai_act_art47

## eu_ai_act_art12
Reference: EU AI ACT Art. 12
Title: Record-keeping
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: High-risk AI systems need automatic event logging supporting traceability, risk identification, post-market monitoring and deployer monitoring. The additional start/end, reference-database, matched-input and verifier-identity fields in 12(3) apply only to Annex III 1(a) remote biometric identification.
Developer impact: Establish high-risk status and logging context. Article 12 concerns logging capability and applicable content, not a universal biometric log schema.
Code smells: Required high-risk event logging is explicitly disabled; an applicable remote-biometric-identification log schema discards a required 12(3) field.
Related: eu_ai_act_art19, eu_ai_act_art21, eu_ai_act_art26
Conditions and exceptions: A non-biometric system is criticised for lacking biometric-specific fields; logging could occur in an unseen component; logs exist and the allegation concerns retention (art19/art26).

## eu_ai_act_art13
Reference: EU AI ACT Art. 13
Title: Transparency and provision of information to deployers
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: High-risk AI systems must be transparent enough for deployers to interpret and use the output correctly, and must ship with digital instructions for use covering provider contacts, accuracy metrics, limitations, and explainability capabilities.
Developer impact: Expose confidence scores, accuracy metrics, limitations metadata, and instructions for use to deployers through the API or UI, and keep them populated.
Code smells: API response stripping confidence_score before returning a prediction; instructions or limitations metadata hardcoded empty; accuracy metrics removed from the system-info endpoint
Related: eu_ai_act_art11, eu_ai_act_art50, eu_ai_act_art86

## eu_ai_act_art14
Reference: EU AI ACT Art. 14
Title: Human oversight
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: High-risk AI systems must be designed so humans can effectively oversee them: monitor operation, interpret output, decide not to use it, override or reverse a decision, and stop the system safely. Biometric identification matches need verification by at least two qualified people.
Developer impact: Build override endpoints, safe-halt/stop controls, human-review queues, monitoring dashboards, and multi-person verification workflows into decision paths.
Code smells: human_override flag hardcoded false; stop/halt endpoint removed; decision auto-executed with no review queue; biometric match auto-confirmed without two-person verification
Related: eu_ai_act_art20, eu_ai_act_art26, eu_ai_act_art86

## eu_ai_act_art15
Reference: EU AI ACT Art. 15
Title: Accuracy, robustness and cybersecurity
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: High-risk AI systems must stay accurate, resilient and secure across their lifecycle: handle errors and faults with fail-safes or redundancy, prevent biased feedback loops in continuous learning, and resist data poisoning, adversarial inputs, and model attacks.
Developer impact: Add fallbacks and fail-safe branches around model calls, filter self-generated outputs from retraining, validate and sanitise inference inputs, and protect model endpoints.
Code smells: model exception swallowed with no fallback path; system retraining on its own outputs with no feedback-loop filter; inference API without input validation or sanitisation; model endpoint exposed without authentication or rate limit
Related: eu_ai_act_art9, eu_ai_act_art55

## eu_ai_act_art16
Reference: EU AI ACT Art. 16
Title: Obligations of providers of high-risk AI systems
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Providers must keep their high-risk systems compliant end to end: show their name and contact on the system, run a quality management system, keep documentation and logs, pass conformity assessment, affix CE marking, register the system, and meet interface accessibility requirements.
Developer impact: Display provider identity in the product, and implement accessibility features (screen-reader support, text alternatives to colour, text-to-speech) in high-risk UIs.
Code smells: UI conveying decision state by colour only with no text alternative; aria-label or alt text removed from result components; provider name/contact fields blank in the about screen; accessibility mode feature-flagged off
Related: eu_ai_act_art17, eu_ai_act_art18, eu_ai_act_art20, eu_ai_act_art47, eu_ai_act_art48, eu_ai_act_art49

## eu_ai_act_art17
Reference: EU AI ACT Art. 17
Title: Quality management system
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Providers of high-risk AI need a documented quality management system: design control, test and validation procedures run at set frequencies, data-management procedures (labelling, storage, retention), change management, post-market monitoring, and incident-reporting procedures.
Developer impact: Encode QMS procedures in the pipeline - mandatory validation stages, change-control records for model modifications, and configured data-management steps.
Code smells: CI release gate skipping the mandated validation procedure; model change deployed without a change-control record; QMS config keys left null; data-management step (labelling, storage, retention) removed from pipeline config
Related: eu_ai_act_art9, eu_ai_act_art10, eu_ai_act_art72, eu_ai_act_art73

## eu_ai_act_art18
Reference: EU AI ACT Art. 18
Title: Documentation keeping
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Providers must keep the technical documentation, quality-management documentation, notified-body decisions, and the EU declaration of conformity at the disposal of authorities for 10 years after the system is placed on the market.
Developer impact: Configure document stores and lifecycle rules with a 10-year retention floor and guard deletion jobs so compliance artifacts cannot be purged early.
Code smells: lifecycle rule expiring the tech-doc or declaration bucket before 10 years; cleanup cron deleting compliance documents; retention_years set to a small value on the documentation store
Related: eu_ai_act_art11, eu_ai_act_art19, eu_ai_act_art23, eu_ai_act_art47

## eu_ai_act_art19
Reference: EU AI ACT Art. 19
Title: Automatically generated logs
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Providers must keep the logs automatically generated by their high-risk AI systems, to the extent the logs are under their control, for a period appropriate to the system's purpose and at least six months.
Developer impact: Configure log retention, TTL indexes, and rotation policies on AI event logs with a six-month minimum floor.
Code smells: log_retention_days set to 30 on AI decision logs; TTL index on the event-log collection under ~180 days; rotation policy deleting AI logs after weeks; purge job truncating audit logs monthly
Related: eu_ai_act_art12, eu_ai_act_art18, eu_ai_act_art26

## eu_ai_act_art20
Reference: EU AI ACT Art. 20
Title: Corrective actions and duty of information
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: When a provider learns a marketed high-risk system is non-conforming, it must immediately correct, withdraw, disable, or recall it, and inform distributors, deployers, and importers. If the system presents a risk, it must investigate and inform the market surveillance authorities.
Developer impact: Implement kill switches or feature flags that can disable a deployed system, plus automated notification flows to downstream parties and authorities.
Code smells: non-conformity detected but no disable/rollback call; recall flow not notifying deployers or distributors; kill switch removed or hardcoded off
Related: eu_ai_act_art24, eu_ai_act_art26, eu_ai_act_art46, eu_ai_act_art73

## eu_ai_act_art21
Reference: EU AI ACT Art. 21
Title: Cooperation with competent authorities
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: On a reasoned (justified) request from a competent authority (the national regulator), providers must hand over all information and documentation proving the high-risk system's conformity, and give access to the automatically generated logs under their control. Information obtained is handled under confidentiality rules.
Developer impact: Build log-export and documentation-access mechanisms that can serve an authority request securely and completely.
Code smells: authority-request handler returning 501 or unimplemented; log-export endpoint deleted; export payload omitting the automatically generated logs; authority access grant missing the conformity documentation
Related: eu_ai_act_art12, eu_ai_act_art74, eu_ai_act_art78

## eu_ai_act_art23
Reference: EU AI ACT Art. 23
Title: Obligations of importers
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Importers must verify, before market placement, that conformity assessment ran, technical documentation exists, and the system bears CE marking with its declaration. They must show their name and contact on the system or its documentation and keep a copy of conformity documents for 10 years.
Developer impact: Display importer contact details in the product UI or digital docs, gate market placement on conformity checks, and retain conformity documents for 10 years.
Code smells: importer name/contact fields empty in product UI or docs; import pipeline listing a system without verifying CE marking or declaration; importer conformity-document store purged before 10 years; falsified-documentation check skipped
Related: eu_ai_act_art16, eu_ai_act_art18, eu_ai_act_art24

## eu_ai_act_art24
Reference: EU AI ACT Art. 24
Title: Obligations of distributors
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Distributors (including software marketplaces) must verify CE marking, the declaration of conformity, and instructions for use before listing a high-risk system. If a system is non-conforming or risky, they must withhold or recall it and inform the provider, importer, and authorities.
Developer impact: Add ingestion gates to marketplace listing flows that verify compliance artifacts, plus suspend/recall mechanisms and notification workflows for non-compliant listings.
Code smells: listing ingestion gate skipping the CE/declaration check; non-compliance report received but listing left live; suspend_listing handler stubbed out; no provider or authority notification on a detected risk
Related: eu_ai_act_art20, eu_ai_act_art23, eu_ai_act_art48

## eu_ai_act_art26
Reference: EU AI ACT Art. 26
Title: Obligations of deployers of high-risk AI systems
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Deployers must use high-risk systems per the instructions: assign competent human oversight, validate input data, monitor operation, keep logs at least six months, suspend use and inform the provider and authority on risk, and inform affected workers and persons.
Developer impact: Implement deployer-side log retention (six-month floor), input-data validation, monitoring with alerting, suspend-on-risk hooks, and disclosure notices to affected people.
Code smells: deployer config setting AI log retention to 30 days; inference inputs forwarded with no validation check; risk detected without suspend or provider notice; rejected biometric authorisation data not deleted
Related: eu_ai_act_art12, eu_ai_act_art14, eu_ai_act_art19, eu_ai_act_art73, eu_ai_act_art86

## eu_ai_act_art43
Reference: EU AI ACT Art. 43
Title: Conformity assessment
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: High-risk AI systems must pass a conformity assessment before market placement, and again after any substantial modification. Continuously learning systems must stay within the pre-determined bounds covered in the technical documentation; beyond them the change is substantial.
Developer impact: Implement drift detection, pre-determined-bounds enforcement, and deployment gates that block or flag model changes exceeding the assessed envelope.
Code smells: continuous-learning loop retraining and deploying with the bounds check disabled; drift-detector alert ignored at the deploy gate; model change beyond approved bounds auto-released without a reassessment flag
Related: eu_ai_act_art46, eu_ai_act_art47, eu_ai_act_art49

## eu_ai_act_art46
Reference: EU AI ACT Art. 46
Title: Derogation from conformity assessment procedure
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Authorities can authorise deploying a high-risk system before conformity assessment for exceptional public-security or safety reasons, for a limited period. If the emergency authorisation is refused, use must stop immediately and all outputs must be discarded at once.
Developer impact: Give emergency-deployed systems an immediate-stop hook and a complete output-deletion routine triggered when authorisation is refused.
Code smells: authorisation-refused branch stopping the system but keeping generated outputs; emergency deployment with no stop hook; outputs and results not purged when authorisation is denied; discard_outputs call commented out
Related: eu_ai_act_art20, eu_ai_act_art43

## eu_ai_act_art47
Reference: EU AI ACT Art. 47
Title: EU declaration of conformity
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Providers must draw up a written machine-readable EU declaration of conformity identifying the high-risk system, containing Annex V information, signed physically or electronically, and kept up to date as appropriate.
Developer impact: Article 47 concerns the declaration; art48 concerns CE marking and art18 document retention. Missing electronic-signature code is not proof of an unsigned declaration.
Code smells: An applicable declaration is explicitly omitted, unsigned by either valid method, missing required content, or knowingly left outdated for the identified system.
Related: eu_ai_act_art18, eu_ai_act_art43, eu_ai_act_art48
Conditions and exceptions: The only allegation is a missing digital signature where a physical signature is established; signature implementation or declaration contents are outside the excerpt.

## eu_ai_act_art48
Reference: EU AI ACT Art. 48
Title: CE marking
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: High-risk AI systems must carry a visible, legible CE marking; digitally provided systems must expose a digital CE marking reachable from the interface or machine-readable code. Where a notified body was involved, its identification number must accompany the marking.
Developer impact: Render the CE marking in the application UI or expose it via a machine-readable endpoint, including the notified-body identification number.
Code smells: CE marking component removed from the UI or about page; CE info endpoint returning empty; marking rendered hidden or behind authentication; notified_body_id dropped from the marking payload
Related: eu_ai_act_art23, eu_ai_act_art24, eu_ai_act_art47

## eu_ai_act_art49
Reference: EU AI ACT Art. 49
Title: Registration
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Article 49 governs registration of the specified Annex III systems and public-authority deployers before placing on the market, putting into service or use, with the applicable public or non-public section. Annex III point 2 systems register nationally under 49(5).
Developer impact: Distinguish registration duty/timing from payload content. Do not infer EU-database registration duties from a registration function name or a vehicle type-approval process.
Code smells: An established EU AI Act registration obligation is bypassed, deferred beyond its trigger, or directed to the wrong access section.
Related: eu_ai_act_art43, eu_ai_act_art71
Conditions and exceptions: The allegation concerns only missing payload fields (art71); the registry is an unrelated national or sectoral registry; the system or actor is outside the applicable registration duty.

## eu_ai_act_art50
Reference: EU AI ACT Art. 50
Title: Transparency obligations for providers and deployers of certain AI systems
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: People must be told when they interact with an AI system. Synthetic audio, image, video, and text outputs must carry a machine-readable AI-generated mark; deepfakes must be visibly disclosed. Disclosures must be clear at first interaction and accessible.
Developer impact: Add AI-interaction banners to chat UIs, machine-readable watermarks (e.g. content credentials) on generated media and text, and accessible deepfake labels.
Code smells: chat UI with the AI-disclosure banner removed or flagged off; generator output path skipping or stripping the watermark step; deepfake render path with no visible label
Related: eu_ai_act_art5, eu_ai_act_art13, eu_ai_act_art86

## eu_ai_act_art53
Reference: EU AI ACT Art. 53
Title: Obligations for providers of general-purpose AI models
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Providers of general-purpose AI models must maintain technical documentation of training and evaluation, inform integrating providers, respect copyright reservations (text-and-data-mining opt-outs), and publish a summary of training content.
Developer impact: Honor robots.txt and TDM/noai opt-out signals in training crawlers, and auto-generate model documentation and training-content summaries from the training pipeline.
Code smells: scraper fetching content with the robots.txt check skipped or ignore_robots set true; noai or tdm-reservation header read then discarded; training-content summary generation removed; downstream model documentation endpoint empty
Related: eu_ai_act_art10, eu_ai_act_art11, eu_ai_act_art55

## eu_ai_act_art55
Reference: EU AI ACT Art. 55
Title: Obligations of providers of general-purpose AI models with systemic risk
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Article 55 adds evaluation, systemic-risk mitigation, serious-incident reporting and adequate cybersecurity duties for GPAI models with systemic risk under Article 51; ordinary GPAI status alone does not establish systemic risk.
Developer impact: Assess security against the actual risks and safeguards. TLS/authentication are relevant evidence, not blanket immunity; high-risk-system security and reporting use art15/art73.
Code smells: An applicable systemic-risk evaluation or incident-reporting step is explicitly disabled; the source establishes a material weakness in protection of model weights or infrastructure.
Related: eu_ai_act_art15, eu_ai_act_art53, eu_ai_act_art73
Conditions and exceptions: Systemic-risk status is unknown; the allegation relies solely on a model being called frontier or general purpose, or on absent rate limiting despite visible TLS and authentication without a demonstrated residual defect.

## eu_ai_act_art59
Reference: EU AI ACT Art. 59
Title: Further processing of personal data for developing certain AI systems in the public interest in the AI regulatory sandbox
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Article 59 permits specified further processing of personal data in an AI regulatory sandbox only under its cumulative conditions, including isolation, controlled access, restricted onward use and documented processing. Personal data is deleted when participation or its retention period ends; processing logs remain for the participation duration unless law provides otherwise.
Developer impact: Distinguish personal-data deletion from processing-log retention. Ordinary training is art10 where applicable; real-world testing outside regulatory sandboxes is art60.
Code smells: An established Article 59 sandbox flow bypasses required isolation, exports sandbox-created personal data outside the permitted conditions, or explicitly retains personal data beyond the applicable end trigger.
Related: eu_ai_act_art10, eu_ai_act_art60
Conditions and exceptions: Only a directory or variable named sandbox is shown; the setting is ordinary development/testing rather than a competent-authority AI regulatory sandbox; applicability of this further-processing regime is unknown.

## eu_ai_act_art60
Reference: EU AI ACT Art. 60
Title: Testing of high-risk AI systems in real world conditions outside AI regulatory sandboxes
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: For applicable real-world testing outside regulatory sandboxes, participants may withdraw without detriment and may request immediate permanent deletion of their personal data. Withdrawal stops participation but does not undo activities already carried out; predictions must be reversible or disregarded.
Developer impact: Separate withdrawal from the erasure request in 60(5). Consent capture is art61; regulatory-sandbox processing is art59.
Code smells: A withdrawal is ignored or penalised; an explicit erasure request results only in a soft-delete while the personal data remains available; required prediction reversal is disabled.
Related: eu_ai_act_art59, eu_ai_act_art61, eu_ai_act_art73
Conditions and exceptions: The only allegation is retention after withdrawal without an erasure request; the context is an ordinary pilot without an established Article 60 testing duty; a different applicable legal requirement governs the alleged defect.

## eu_ai_act_art61
Reference: EU AI ACT Art. 61
Title: Informed consent to participate in testing in real world conditions outside AI regulatory sandboxes
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Test subjects must give informed consent before real-world testing, after being told the test's nature, conditions and duration, the right to refuse or withdraw, how to request decision reversal, and the test ID and provider contacts. Consent must be dated, documented, and a copy given to the subject.
Developer impact: Build consent-collection UIs, persist dated consent records, generate consent document copies, and expose withdrawal and reversal-request endpoints.
Code smells: subject enrolled in a test with the consent check skipped or defaulted true; consent stored without a date or document copy; consent UI omitting the right to withdraw or the test ID; withdrawal endpoint missing
Related: eu_ai_act_art60

## eu_ai_act_art71
Reference: EU AI ACT Art. 71
Title: EU database for high-risk AI systems listed in Annex III
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Providers and public-authority deployers must enter the mandated data into the EU database. Most entries must be publicly accessible and machine-readable; law-enforcement and real-world-testing entries stay restricted. Personal data only where strictly necessary.
Developer impact: Build registration payloads to the required schema, keep exports machine-readable, and keep restricted entries out of public sections and personal data minimised.
Code smells: registration payload built with required fields null; law-enforcement registration data written to a publicly readable store; registration export returning a non-machine-readable blob; payload including personal data beyond what is necessary
Related: eu_ai_act_art49, eu_ai_act_art74

## eu_ai_act_art72
Reference: EU AI ACT Art. 72
Title: Post-market monitoring by providers and post-market monitoring plan for high-risk AI systems
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Providers must run a documented post-market monitoring system that systematically collects and analyses performance data from deployed systems throughout their lifetime, per a monitoring plan kept in the technical documentation.
Developer impact: Implement production telemetry, performance-metric collection, and analysis pipelines for deployed models, wired to a documented monitoring plan.
Code smells: telemetry collection disabled in the production config; performance metrics collected but never stored or analysed; monitoring plan reference removed from the technical documentation; monitoring covering uptime only and not model performance
Related: eu_ai_act_art9, eu_ai_act_art26, eu_ai_act_art73

## eu_ai_act_art73
Reference: EU AI ACT Art. 73
Title: Reporting of serious incidents
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Providers must report serious incidents to the market surveillance authority: within 15 days of awareness, 10 days if a person died, and 2 days for widespread or critical-infrastructure incidents. They must investigate, preserve evidence, and not alter the system or logs in ways that hinder the investigation.
Developer impact: Implement automated incident detection and alerting, deadline-aware reporting pipelines, and log/model-state freezing during investigations.
Code smells: incident branch never calling the authority-report function; reporting deadline constant set beyond 15 days; logs or model state rotated away while an investigation is open
Related: eu_ai_act_art20, eu_ai_act_art26, eu_ai_act_art55, eu_ai_act_art72

## eu_ai_act_art74
Reference: EU AI ACT Art. 74
Title: Market surveillance and control of AI systems in the Union market
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Market surveillance authorities get full access to the documentation and to the training, validation and testing datasets of high-risk AI systems, through APIs or remote means, with security safeguards. Source code access can be required under conditions.
Developer impact: Provide secure, authenticated API or remote-access tooling that grants authorities scoped access to datasets and documentation.
Code smells: authority dataset-access endpoint unimplemented or removed; dataset access served over plain HTTP or without authentication; access scope exposing more than the training/validation/testing data requested
Related: eu_ai_act_art21, eu_ai_act_art71, eu_ai_act_art78

## eu_ai_act_art78
Reference: EU AI ACT Art. 78
Title: Confidentiality
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Anyone handling information obtained under the AI Act must protect it: safeguard intellectual property, trade secrets and source code, request only data strictly necessary for the risk assessment, apply cybersecurity measures, and delete collected data once no longer needed.
Developer impact: Encrypt stored compliance artifacts and source code, enforce clearance-based access controls, minimise data requested by compliance APIs, and schedule deletion when the purpose ends.
Code smells: obtained source code or trade secrets stored unencrypted; compliance API requesting more data than needed for the assessment; no clearance-based access control on the technical-documentation store; collected data kept after the purpose ends with no deletion job
Related: eu_ai_act_art21, eu_ai_act_art74

## eu_ai_act_art86
Reference: EU AI ACT Art. 86
Title: Right to explanation of individual decision-making
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: A person affected by a decision based on a high-risk AI system's output, with legal or similarly significant adverse effects, has the right to a clear explanation of the AI system's role and the decision's main elements.
Developer impact: Generate decision explanations (interpretability logging, feature attributions) and expose them to the affected person through a user-facing disclosure interface.
Code smells: loan/hiring/benefit endpoint returning an outcome with the explanation field empty; explanation generation feature-flagged off; explanation visible to staff only and never to the affected person
Related: eu_ai_act_art13, eu_ai_act_art14, eu_ai_act_art50
