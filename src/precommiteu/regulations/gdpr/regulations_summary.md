# Precommiteu public regulation context - GDPR
Included regulations: GDPR (General Data Protection Regulation), CELEX 32016R0679.

Compact, developer-oriented SUMMARIES of code-relevant GDPR articles - NOT the
legal text. Used to (a) retrieve the probable article area for a scanner finding
and (b) show a short "why this matters" snippet in PR comments. For the
authoritative wording, follow the EUR-Lex link rendered with each finding.

# GDPR (General Data Protection Regulation)

Scope and evidence: code smells below are investigation leads, not automatic violations. Establish the applicable actor, activity, conditions and exceptions from the supplied context; missing information in one excerpt is not proof of a system-wide omission.

Applicability: Personal data includes identifiers that can reasonably be linked to people. Hashing/tokenisation may be pseudonymisation, not anonymisation. A personal-data breach requires destruction, loss, alteration, unauthorised disclosure or access; a blocked attempt alone is not a breach.

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

Summary: Personal-data processing needs an Article 6(1) lawful basis; consent is one option, alongside contract necessity, legal obligation, vital interests, public tasks and legitimate interests subject to their conditions.
Developer impact: Article 6 concerns lawfulness; Article 7 concerns valid consent and withdrawal. Further-use compatibility under 6(4) weighs purpose, collection context, data, consequences and safeguards; encryption is not a universal prerequisite.
Code smells: A consent-based operation proceeds after refusal or withdrawal with no other established basis; an established purpose restriction is bypassed for incompatible further processing.
Related: gdpr_art9, gdpr_art10, gdpr_art23
Conditions and exceptions: The claim rests only on an absent consent or legal_basis variable; another applicable lawful basis supports the operation; processing necessity or purpose compatibility is unresolved.

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

Summary: Article 8 concerns consent-based information-society services offered directly to children: parental authorisation is needed below the applicable Member-State age, between 13 and 16.
Developer impact: Establish the service, consent basis and applicable age before confirming a child-consent defect; not every operation involving a child requires parental consent.
Code smells: An established child-consent flow bypasses parental authorisation below the applicable age or substitutes a false adult age to avoid it.
Related: gdpr_art6
Conditions and exceptions: Processing uses an applicable non-consent basis; a threshold of 13-15 is criticised without establishing national law; an age field alone is shown.

## gdpr_art9
Reference: GDPR Art. 9
Title: Processing of special categories of personal data
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Special-category processing needs an Article 9(2) condition as well as an Article 6 basis. Conditions include explicit consent, employment/social law, vital interests, qualifying nonprofit activities, manifestly public data, legal claims, substantial public interest, professional care, public health and research, each subject to its statutory safeguards.
Developer impact: Article 9 addresses permission to process special categories, including biometrics used for unique identification. A healthcare setting alone proves neither an exception nor its absence; security defects remain assessable under art32.
Code smells: A consent-dependent special-category operation bypasses explicit consent with no other established 9(2) condition; a legally limited sensitive-data purpose is visibly exceeded.
Related: gdpr_art89
Conditions and exceptions: Another applicable 9(2) condition and its safeguards support the processing; the only allegation concerns transport, storage or access security (art32); an ordinary photograph is treated as identification biometrics without that purpose.

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

Summary: Privacy information and rights communications must be concise, transparent, intelligible and accessible. Respond without undue delay and within one calendar month; a necessary extension of up to two further months requires notice and reasons within the first month.
Developer impact: Article 12 concerns communication and request handling; art15 concerns access content and art20 qualifying portability. Neither a file extension nor a particular UI technology proves unintelligibility.
Code smells: A rights workflow explicitly exceeds the applicable deadline without an extension; ordinary requests face an unjustified fee; refusal omits reasons or complaint/remedy information; privacy communication is demonstrably unintelligible or inaccessible.
Related: gdpr_art11, gdpr_art13, gdpr_art14, gdpr_art15, gdpr_art16, gdpr_art17
Conditions and exceptions: A justified extension is notified on time; a fee/refusal meets the manifestly unfounded or excessive request conditions; a reasonable fee covers further copies under art15(3); only a binary format or a 31-day calendar month is cited.

## gdpr_art13
Reference: GDPR Art. 13
Title: Information to be provided where personal data are collected from the data subject
Regulation: GDPR
Source CELEX: 32016R0679

Summary: At direct collection, provide applicable Article 13 information, including controller details, purposes and legal basis, rights, retention and relevant recipients, transfers and automated decisions. Information may be layered.
Developer impact: Read the relevant notice before claiming an omission. A link does not prove that the full policy is compliant, and an incomplete excerpt does not prove that it is deficient; indirect collection is art14.
Code smells: The supplied collection flow explicitly withholds required information across the available notice layers; an applicable disclosure is removed or falsified before it reaches the person.
Related: gdpr_art6, gdpr_art9, gdpr_art22, gdpr_art46, gdpr_art47, gdpr_art49
Conditions and exceptions: The allegation infers missing information solely from a short notice linked to an unseen full policy, a backend handler, or missing DPO details without an applicable DPO; the person already has the information under 13(4).

## gdpr_art14
Reference: GDPR Art. 14
Title: Information to be provided where personal data have not been obtained from the data subject
Regulation: GDPR
Source CELEX: 32016R0679

Summary: For personal data obtained indirectly, provide the applicable information, including categories and source, within a reasonable period no longer than one month, or earlier at first communication or disclosure as required by 14(3).
Developer impact: Distinguish indirect from direct collection (art13); check timing and the actual exception conditions before treating the absence of a notification call as a violation.
Code smells: An applicable notice is explicitly disabled or scheduled beyond its legal trigger; the source or another required item is removed from the completed notice.
Related: gdpr_art6, gdpr_art9, gdpr_art22, gdpr_art46, gdpr_art47, gdpr_art49
Conditions and exceptions: An Article 14(5) exception is established: already informed, qualifying impossibility/disproportionate effort with safeguards, legally prescribed obtaining/disclosure with protections, or regulated professional secrecy. A research label or public notice alone does not establish an exception.

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

Summary: Restriction applies to contested accuracy during verification, unlawful processing where erasure is opposed, data needed for legal claims after the controller no longer needs it, and an objection pending verification.
Developer impact: Trace the meaning of accuracy-contested, objection-pending and legal-claim-hold flags; field names alone do not establish a restriction. Article 18 limits processing rather than requiring erasure.
Code smells: An established restriction is bypassed for analytics, marketing, sharing or another processing purpose outside the permitted exceptions; restriction is lifted without the required prior notice.
Related: gdpr_art21
Conditions and exceptions: Only storage is involved; processing has consent or serves legal claims, another person's rights, or important Union/Member-State public interest; the flag refers to an unrelated commercial dispute.

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

Summary: Article 22 concerns decisions based solely on automated processing that produce legal or similarly significant effects, subject to the contract-necessity, legal-authorisation and explicit-consent exceptions and their safeguards.
Developer impact: Assess effect, automation and exceptions, not token pairs. A review token alone proves no meaningful oversight, and missing explanation logs alone do not establish an Article 22 breach.
Code smells: An established significant automated decision bypasses applicable safeguards; a required meaningful human intervention or contest route is explicitly disabled.
Related: gdpr_art9
Conditions and exceptions: The effect is not legally or similarly significant; meaningful human decision-making is established; an applicable exception and safeguards cover the decision; a token such as auto_block or pricing_tier is the sole premise.

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

Summary: A processor or person acting under the controller or processor's authority may process personal data only on the controller's instructions, unless Union or Member-State law requires otherwise.
Developer impact: Prove processing beyond instructions for art29. Contract terms belong to art28 and security defects to art32; ordinary automation is not autonomous unauthorised processing.
Code smells: An established instruction or purpose restriction is visibly bypassed by an operator, processor or job.
Conditions and exceptions: The only premise is that a cron job, script or log call lacks a policy_check variable; instructions are unknown or the operation follows established instructions; a statutory requirement applies.

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

Summary: Controllers and processors must implement security appropriate to the risk, considering the state of the art, cost, context and processing. This includes special-category and national-identifier data; it is not a universal per-field encryption rule.
Developer impact: Validate the candidate's security allegation and trace its data and safeguards. Lawfulness of special-category processing is art9; art87 adds national-identifier conditions rather than replacing art32.
Code smells: A traced personal-data or credential operation disables a material transport/access control, uses demonstrably unsuitable credential protection, or exposes data to unauthorised readers through logs or other sinks.
Related: gdpr_art40, gdpr_art42
Conditions and exceptions: Only a data-field/logging token or missing wrapper implementation is shown; deployment security is unknown; an internal identifier is logged without evidence of inappropriate access or excess; an algorithm is used for a non-security checksum.

## gdpr_art33
Reference: GDPR Art. 33
Title: Notification of a personal data breach to the supervisory authority
Regulation: GDPR
Source CELEX: 32016R0679

Summary: After awareness of an actual personal-data breach, a controller notifies the authority without undue delay and, where feasible, within 72 hours unless risk to rights and freedoms is unlikely. A processor notifies its controller without undue delay; Article 33(2) sets no separate 72-hour processor deadline.
Developer impact: Article 33 covers controller-to-authority and processor-to-controller notification plus breach documentation under 33(5); user communication is art34. Abbreviated field names and an in-memory work queue alone prove no omission.
Code smells: An applicable notification is explicitly suppressed or unjustifiably delayed; a completed breach report omits required available information without phased follow-up; breach documentation discards facts, effects or remedial action.
Related: gdpr_art55
Conditions and exceptions: Only a blocked attempt or potential exposure is established; the actor or notification trigger is unknown; authority notification is exempt because risk is unlikely; required information follows in justified phases. Trace populated fields and queue consumers before declaring documentation or delivery absent.

## gdpr_art34
Reference: GDPR Art. 34
Title: Communication of a personal data breach to the data subject
Regulation: GDPR
Source CELEX: 32016R0679

Summary: A controller communicates a personal-data breach to affected people without undue delay when it is likely to create high risk, subject to Article 34(3). The notice needs clear language, a contact, likely consequences and mitigation information.
Developer impact: Hashing or pseudonymisation alone does not establish unintelligibility. Evaluate protection of the actual affected data; a low_risk, encrypted or public_notice flag alone neither proves nor disproves the exception.
Code smells: An established high-risk breach has its required user notice disabled or unjustifiably delayed; applicable notice content is removed; a claimed exception is contradicted by the traced safeguards.
Related: gdpr_art33
Conditions and exceptions: A breach or high-risk threshold is not established; affected data was protected so it is unintelligible to unauthorised persons; subsequent measures remove the likely high risk; disproportionate effort is addressed by equally effective public communication.

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

Summary: Chapter V governs transfers of personal data to third countries or international organisations, including onward transfers. A valid adequacy decision covering the recipient/data, appropriate safeguards or an applicable derogation may support the transfer; a foreign region alone proves no breach.
Developer impact: Map the recipient, destination and applicable transfer mechanism, including any scope limitations; a contract or adequacy mechanism need not be implemented as a runtime flag.
Code smells: an established required transfer gate deliberately bypassed; onward disclosure contrary to the applicable mechanism
Conditions and exceptions: Consider applicable Article 45 adequacy, Article 46 safeguards and Article 49 derogations; Article 48 is without prejudice to other Chapter V transfer grounds. Check actual recipients and legal arrangements, not merely region names or absent runtime flags.

## gdpr_art46
Reference: GDPR Art. 46
Title: Transfers subject to appropriate safeguards
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Without an adequacy decision, you may transfer data abroad only if appropriate safeguards exist (Standard Contractual Clauses, Binding Corporate Rules, approved codes/certifications) and users retain enforceable rights. Some routes need supervisory-authority authorization.
Developer impact: Route/block outbound cross-border transfers based on presence of a validated legal safeguard (SCC/BCR) for the destination.
Code smells: cross-border API call lacks SCC/safeguard validation; sync to non-EU bucket with no regional routing; webhook POSTs PII abroad without SCCs; third-party widget/SDK in third country gets PII; no data-residency enforcement on telemetry sink
Related: gdpr_art40, gdpr_art42, gdpr_art45, gdpr_art47, gdpr_art63, gdpr_art93
Conditions and exceptions: Consider applicable Article 45 adequacy, Article 46 safeguards and Article 49 derogations; Article 48 is without prejudice to other Chapter V transfer grounds. Check actual recipients and legal arrangements, not merely region names or absent runtime flags.

## gdpr_art48
Reference: GDPR Art. 48
Title: Transfers or disclosures not authorised by Union law
Regulation: GDPR
Source CELEX: 32016R0679

Summary: A foreign judgment or administrative decision requiring personal-data disclosure is recognised or enforceable only on the basis of an applicable international agreement, without prejudice to other Chapter V transfer grounds.
Developer impact: Validate foreign authority/legal-disclosure requests against treaty (MLAT) authorization before exporting any personal data.
Code smells: foreign-demand disclosure that demonstrably lacks an applicable lawful route; bypass of a required disclosure-authorisation check
Conditions and exceptions: Consider applicable Article 45 adequacy, Article 46 safeguards and Article 49 derogations; Article 48 is without prejudice to other Chapter V transfer grounds. Check actual recipients and legal arrangements, not merely region names or absent runtime flags.

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

Summary: National identification numbers and other identifiers of general application require appropriate safeguards; Member States may specify further processing conditions under Article 87.
Developer impact: Trace which identifier is protected: hashing an email does not protect a separate national ID. Do not infer database-at-rest protection from an application value; a proven general security defect can fall under art32.
Code smells: An established national-identifier safeguard or applicable national-law condition is visibly bypassed; the actual handling exposes the identifier in a way shown to defeat that requirement.
Conditions and exceptions: The claim assumes every unencrypted identifier, URL parameter, cache key or database column automatically violates Article 87; relevant safeguards or national conditions are unknown; the identifier is merely an internal record key.

## gdpr_art89
Reference: GDPR Art. 89
Title: Safeguards and derogations relating to processing for archiving, scientific or historical research, or statistical purposes
Regulation: GDPR
Source CELEX: 32016R0679

Summary: Processing for archiving, research, or statistics needs safeguards enforcing data minimisation, preferring pseudonymisation or full anonymisation where the purpose still works. Member State law may then derogate from certain data-subject rights (access, rectification, etc.).
Developer impact: In research/analytics/archive pipelines, pseudonymise or anonymise and minimise data before storing or modeling.
Code smells: raw identifiers (name/SSN/VIN) in research dataset; analytics pipeline pulls unmasked PII from prod; archive lacks pseudonymisation/tokenisation; no k-anonymity/differential privacy on public microdata; stats retain direct identifiers with no minimisation
Related: gdpr_art15, gdpr_art16, gdpr_art18, gdpr_art19, gdpr_art20, gdpr_art21
