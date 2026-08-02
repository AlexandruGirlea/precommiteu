# Precommiteu public regulation context - EU AI ACT
Included regulations: EU AI ACT (EU Artificial Intelligence Act), CELEX 32024R1689.

Compact, developer-oriented SUMMARIES of code-relevant EU AI Act articles - NOT the
legal text. Used to (a) retrieve the probable article area for a scanner finding
and (b) show a short "why this matters" snippet in PR comments. For the
authoritative wording, follow the EUR-Lex link rendered with each finding.

# EU AI ACT (EU Artificial Intelligence Act)

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

Summary: High-risk AI systems must automatically log events over their lifetime so risky situations and substantial modifications can be traced. For biometric systems the logs must include each use period (start/end time), the reference database checked, matched input data, and the identity of the human verifier.
Developer impact: Implement always-on structured event logging on inference and decision paths with timestamps, input records, and verifier identities.
Code smells: logging_enabled flag set false on the inference path; decision handler returning a result without writing an audit-log entry; log record built without timestamp or input data; verifier identity dropped from the match record
Related: eu_ai_act_art19, eu_ai_act_art21, eu_ai_act_art26

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

Summary: Providers must draw up a machine-readable, electronically signed EU declaration of conformity for each high-risk system, containing the mandated identification fields, keep it 10 years, and keep it current as the system changes.
Developer impact: Automate declaration generation, electronic signing, and metadata attachment in the CI/CD pipeline, and regenerate the declaration when the system changes.
Code smells: CI release step skipping declaration generation; declaration written without an electronic signature; declaration not regenerated after a system change
Related: eu_ai_act_art18, eu_ai_act_art43, eu_ai_act_art48

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

Summary: Before placing a high-risk system on the market, the provider must register itself and the system in the EU database; public-authority deployers must register their use. Law-enforcement, migration, and border systems register in a secure non-public section.
Developer impact: Add automated registration steps to deployment pipelines with the required payload schema, targeting the correct public or restricted database section before release.
Code smells: deploy job running with the registration step commented out; law-enforcement system registered to the public section instead of the secure non-public one; registration payload missing required fields; release gate not blocking on registration failure
Related: eu_ai_act_art43, eu_ai_act_art71

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

Summary: Providers of general-purpose AI models with systemic risk must run documented adversarial testing and model evaluations, assess and mitigate systemic risks, report serious incidents to the AI Office without delay, and harden model and infrastructure security.
Developer impact: Build adversarial-testing/red-team harnesses into model release, automate incident reporting pipelines, and protect model weights and serving infrastructure with strict access controls.
Code smells: red-team suite skipped before a frontier-model release; incident-reporting pipeline to the AI Office removed; model weights stored or served without access control or encryption; systemic-risk mitigation step disabled
Related: eu_ai_act_art15, eu_ai_act_art53, eu_ai_act_art73

## eu_ai_act_art59
Reference: EU AI ACT Art. 59
Title: Further processing of personal data for developing certain AI systems in the public interest in the AI regulatory sandbox
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Personal data may be reused inside an AI regulatory sandbox only under strict conditions: an isolated, protected processing environment, access limited to authorised people, no sharing outside, deletion once participation ends, and processing logs kept for the project's duration.
Developer impact: Implement sandbox data isolation, strict access controls, egress prevention, audit logging, and automated deletion when the sandbox project ends.
Code smells: sandbox job copying personal data to a non-sandbox bucket; sandbox data not deleted when participation ends; processing logs disabled inside the sandbox; sandbox storage shared with production with no isolation
Related: eu_ai_act_art10, eu_ai_act_art60

## eu_ai_act_art60
Reference: EU AI ACT Art. 60
Title: Testing of high-risk AI systems in real world conditions outside AI regulatory sandboxes
Regulation: EU AI ACT
Source CELEX: 32024R1689

Summary: Real-world testing of high-risk AI requires a registered testing plan, a bounded duration, effective oversight, and subject protections: data of withdrawn subjects deleted, predictions reversible or disregardable, and transfers abroad only with safeguards.
Developer impact: Implement withdrawal-triggered data deletion, decision reversal/disregard mechanisms, time-bound test runs, and transfer safeguards in testing harnesses.
Code smells: subject withdrawal handler keeping already-collected data; AI predictions made during testing with no reversal or disregard mechanism; test run continuing past the planned duration with no stop; testing started before plan registration
Related: eu_ai_act_art59, eu_ai_act_art61, eu_ai_act_art73

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
