# Precommiteu public regulation context - CRA + DMA + NIS2
Included regulations: CRA (Cyber Resilience Act), CELEX 32024R2847; DMA (Digital Markets Act), CELEX 32022R1925; NIS2 (Network and Information Security Directive), CELEX 32022L2555.

Compact, developer-oriented SUMMARIES of code-relevant CRA, DMA and NIS2
articles - NOT the legal text. Used to (a) retrieve the probable article area
for a scanner finding and (b) show a short "why this matters" snippet in PR
comments. For the authoritative wording, follow the EUR-Lex link rendered with
each finding.

# Cyber Resilience Act (CRA)

Scope and evidence: code smells below are investigation leads, not automatic violations. Establish the applicable actor, activity, conditions and exceptions from the supplied context; missing information in one excerpt is not proof of a system-wide omission.

Applicability: CRA product/manufacturer and steward duties, DMA designated-gatekeeper/service duties, and NIS2 covered-entity obligations have different scope and applicability. Generic service, product, CSIRT or maintainer names alone prove none of these. Check sector-specific exclusions and applicable timing; do not turn an unknown actor into a confirmed regulated actor.

## cra_art4
Reference: CRA Art. 4
Title: Free movement
Regulation: CRA
Source CELEX: 32024R2847

Summary: Unfinished or prototype software may only be made available for a limited testing period, and it must carry a visible sign that it does not comply with the CRA and is not for market use. Without that disclosure and time limit, the exemption does not apply.
Developer impact: Render a visible "non-compliant / for testing only" banner in beta and prototype builds, and enforce time-limited access (expiry dates, trial windows) on test distributions.
Code smells: beta or prototype build distributed with no non-compliance banner; test access with expires_at=null or no trial end; pre-release page missing "not for market" text; testing disclaimer hidden or removed before release
Related: cra_art6, cra_art30

## cra_art6
Reference: CRA Art. 6
Title: Requirements for products with digital elements
Regulation: CRA
Source CELEX: 32024R2847

Summary: A product with digital elements may only be sold if it meets the essential cybersecurity requirements: secure default configuration, protection of data, access control, and a secure update mechanism. Manufacturer vulnerability-handling processes must also comply.
Developer impact: Ship secure defaults (no default passwords, debug off), encrypt data in transit and at rest, gate admin functions behind authentication, and deliver signed updates over secure channels.
Code smells: hardcoded default credentials like admin/admin; update fetched over http:// with no signature check; verify=False on a product network call; DEBUG=True or open debug port in a release build; unauthenticated admin or telemetry endpoint shipped
Related: cra_art13, nis2_art21

## cra_art13
Reference: CRA Art. 13
Title: Obligations of manufacturers
Regulation: CRA
Source CELEX: 32024R2847

Summary: Manufacturers must run a documented cybersecurity risk assessment, handle vulnerabilities for a support period (normally at least five years), produce a Software Bill of Materials, tell users the end-of-support date, and ship security updates separately, promptly and free of charge.
Developer impact: Generate an SBOM (CycloneDX/SPDX) in the build pipeline, surface the end-of-support date in the UI or docs, and keep a security-update channel separate from feature updates.
Code smells: SBOM generation step removed or disabled in CI; end_of_support date never shown to users; security patch bundled into a paid or feature release; support_period shorter than required; update channel deleted while the product is still supported
Related: cra_art6, cra_art14, cra_art31

## cra_art14
Reference: CRA Art. 14
Title: Reporting obligations of manufacturers
Regulation: CRA
Source CELEX: 32024R2847

Summary: A manufacturer learning of an actively exploited vulnerability or a severe incident in its product must notify the CSIRT (national Computer Security Incident Response Team) and ENISA (the EU cybersecurity agency) via the single reporting platform: early warning in 24 hours, fuller notification in 72, final report 14 days after a fix (one month for severe incidents). Affected users must be told the issue and corrective measures.
Developer impact: Automate report submission on the 24h/72h/14d deadlines with machine-readable payloads (product, exploit, mitigations) and user-facing advisories.
Code smells: report deadline constant above 24 or 72 hours; exploited-vuln branch never calling the reporting API; payload missing exploit or mitigation fields; advisory generation disabled; incident final-report deadline above one month
Related: cra_art24, nis2_art23

## cra_art23
Reference: CRA Art. 23
Title: Identification of economic operators
Regulation: CRA
Source CELEX: 32024R2847

Summary: Economic operators must be able to identify their supplying economic operator and, where available, downstream economic operators by name/address for market-surveillance authorities, for ten years after the respective receipt or supply.
Developer impact: Article 23 concerns manufacturers, authorised representatives, importers and distributors in the supply chain, not a universal duty to retain consumer identities for ten years.
Code smells: An applicable supply-chain record is deliberately stripped of required available identification or purged before the ten-year period.
Related: nis2_art27
Conditions and exceptions: The records concern consumers rather than economic operators; downstream identification is unavailable; only generic customer/order data or an unrelated retention job is shown.

## cra_art24
Reference: CRA Art. 24
Title: Obligations of open-source software stewards
Regulation: CRA
Source CELEX: 32024R2847

Summary: An open-source software steward is a non-manufacturer legal person sustainably supporting qualifying open-source products intended for commercial activity. Article 24 requires a verifiable cybersecurity policy and authority cooperation, with Article 14 reporting duties limited by its involvement and development-infrastructure scope.
Developer impact: Do not infer legal role from a filename. Manufacturer lifecycle/reporting duties are art13/art14; steward reporting under 24(3) depends on the specified involvement or infrastructure.
Code smells: An established steward explicitly disables its required policy or applicable reporting for actively exploited vulnerabilities or severe development-infrastructure incidents.
Related: cra_art14, nis2_art30
Conditions and exceptions: Only a maintainer field, SECURITY.md file, open-source dependency or foundation-like name suggests stewardship; the actor is a manufacturer; the incident or reporting scope is not established.

## cra_art28
Reference: CRA Art. 28
Title: EU declaration of conformity
Regulation: CRA
Source CELEX: 32024R2847

Summary: The manufacturer must draw up an EU declaration of conformity stating the product meets the essential cybersecurity requirements, keep it updated, and ship it with the product in the required model structure and languages. One declaration covers all applicable EU acts.
Developer impact: Add release steps that generate the declaration in the mandated structure, bundle it with the shipped artifact, and regenerate it whenever the product or its conformity status changes.
Code smells: declaration generation skipped in the release script; conformity document not bundled into the artifact; declaration version pinned while the product version moves; required declaration fields left empty; language variants dropped from packaging
Related: cra_art30, cra_art31

## cra_art30
Reference: CRA Art. 30
Title: Rules and conditions for affixing the CE marking
Regulation: CRA
Source CELEX: 32024R2847

Summary: CE marking must be visible, legible and indelible before market placement. For software it may be on the declaration of conformity or an easily/directly accessible accompanying website; below 5 mm is permitted when still visible and legible.
Developer impact: Inspect the permitted marking location. A CLI need not render the mark itself; a URL alone proves neither compliant content nor missing marking. Declaration content is art28.
Code smells: An applicable CE mark is explicitly hidden, illegible or placed behind an inaccessible page; the required Module H notified-body identifier is removed.
Related: cra_art4, cra_art28
Conditions and exceptions: Software directs users to an accessible declaration or accompanying website carrying the mark; small size alone is the allegation; a linked page is unseen, so absence of its marking cannot be established.

## cra_art31
Reference: CRA Art. 31
Title: Technical documentation
Regulation: CRA
Source CELEX: 32024R2847

Summary: Technical documentation proving compliance must exist before the product is placed on the market and contain all required elements, including design, development and vulnerability-handling information. It must stay updated at least through the support period.
Developer impact: Configure CI/CD to auto-generate and attach compliance artifacts - architecture details, SBOM references, vulnerability-handling descriptions - refreshed on every release.
Code smells: docs generation step disabled in the pipeline; documentation frozen at an old version while code ships; SBOM or architecture artifact missing from the docs bundle; docs update job deleted during the support period
Related: cra_art13, cra_art28

# Digital Markets Act (DMA)

## dma_art5
Reference: DMA Art. 5
Title: Obligations for gatekeepers
Regulation: DMA
Source CELEX: 32022R1925

Summary: A gatekeeper may not use third-party data for its own ads, combine or cross-use personal data across its services, or auto sign-in users to merge data, without specific consent; after refusal it may re-ask at most once a year. It must give advertisers and publishers daily price/fee transparency and not force its own identity or payment services.
Developer impact: Gate cross-service merges and ads targeting behind consent checks, enforce a one-year re-prompt cooldown, and expose daily ad price report APIs.
Code smells: merge_profiles or cross-service join with no consent flag check; consent re-prompt with cooldown_days=30; ads pipeline reading third-party data without consent; advertiser price report endpoint removed or aggregated away
Related: dma_art6, dma_art13

## dma_art6
Reference: DMA Art. 6
Title: Obligations for gatekeepers susceptible of being further specified under Article 8
Regulation: DMA
Source CELEX: 32022R1925

Summary: Gatekeepers must let users easily uninstall apps and change defaults via choice screens, not use business users' non-public data to compete, not self-prefer in rankings, and provide real-time data portability and interoperability with OS features.
Developer impact: Implement choice screens without pre-selected gatekeeper options, enable uninstall of non-essential apps, keep rankings free of own-brand boosts, and ship real-time portability endpoints.
Code smells: uninstall disabled for a non-essential gatekeeper app; ranking score with a hardcoded own_brand boost; choice screen pre-selecting the gatekeeper default; portability export rate-limited, stale or missing fields
Related: dma_art5, dma_art7, dma_art13

## dma_art7
Reference: DMA Art. 7
Title: Obligation for gatekeepers on interoperability of number-independent interpersonal communications services
Regulation: DMA
Source CELEX: 32022R1925

Summary: Gatekeeper messengers must offer other providers free interoperability interfaces covering messaging, file sharing and eventually calls, preserve security - including end-to-end encryption - across the bridge, and collect only data strictly necessary for interoperability.
Developer impact: Build interop/federation APIs that keep messages end-to-end encrypted across the bridge, collect only the minimum fields, and keep use opt-in.
Code smells: message bridge decrypting and relaying plaintext; e2ee=False on the interoperability path; interop API harvesting contact or profile fields beyond necessity; federation requests fee-gated or rejected by default
Related: dma_art5, dma_art6

## dma_art13
Reference: DMA Art. 13
Title: Anti-circumvention
Regulation: DMA
Source CELEX: 32022R1925

Summary: Gatekeepers may not undermine their DMA obligations through technical design or interface tricks (dark patterns). Where consent is needed, business users must be able to obtain it directly - no harder than the gatekeeper's own flow - or receive duly anonymized data when consent is absent.
Developer impact: Remove UI friction asymmetries (equal-weight accept/decline), expose consent-collection APIs for business users, and anonymize any data shared without consent.
Code smells: decline button hidden, shrunk or behind extra steps versus accept; pre-checked consent box in a gatekeeper flow; nagging re-prompt loop after refusal; business-user consent API harder than the gatekeeper's own flow; non-consented data exported without anonymization
Related: dma_art5, dma_art6

## dma_art15
Reference: DMA Art. 15
Title: Obligation of an audit
Regulation: DMA
Source CELEX: 32022R1925

Summary: A gatekeeper must submit an independently audited description of its consumer-profiling techniques to the Commission and publish an overview of that audited description. Both the description and the public overview must be updated at least annually.
Developer impact: Keep a public profiling-audit overview page live and accurate, wire an at-least-annual update job, and reflect all production profiling techniques in the audit artifacts.
Code smells: public audit overview page removed or returning 404; overview last_updated older than one year; new profiling pipeline shipped without updating the audit description; overview excluding active profiling techniques; transparency page behind authentication
Related: dma_art5, dma_art54

## dma_art43
Reference: DMA Art. 43
Title: Reporting of breaches and protection of reporting persons
Regulation: DMA
Source CELEX: 32022R1925

Summary: People who report breaches of the DMA are protected under the EU whistleblower rules. In practice that means reporting channels must be secure and confidential, keep the reporter's identity protected, support follow-up, and shield reporters from retaliation.
Developer impact: Implement breach-reporting endpoints with encryption at rest, strict access control, an anonymous submission option, and no identity leakage into logs or downstream systems.
Code smells: breach report endpoint logging reporter email or IP; reports stored unencrypted or readable by broad roles; anonymous submission option removed; reporter identity forwarded to the team being reported
Related: nis2_art30

## dma_art54
Reference: DMA Art. 54
Title: Entry into force and application
Regulation: DMA
Source CELEX: 32022R1925

Summary: This scanner ID carries the DMA Annex active-user methodology linked to Article 3(2)(b); Article 54 itself concerns application dates. Count unique active end users monthly and business users yearly for each relevant core platform service, avoiding within-service device/platform duplication.
Developer impact: Deduplicate within each relevant service, not across all services. Preserve the existing scanner ID for compatibility; describe the Annex methodology rather than attributing its counting rules to Article 54 itself.
Code smells: Regulatory counts double-count the same users across devices within one service, count events instead of users, or split one service by domain/geography to distort the relevant count.
Related: dma_art15
Conditions and exceptions: The same person is counted separately for distinct core platform services; the metric is internal analytics rather than designation reporting; the alleged counting error depends on an unestablished service boundary.

# Network and Information Security Directive (NIS2)

## nis2_art21
Reference: NIS2 Art. 21
Title: Cybersecurity risk-management measures
Regulation: NIS2
Source CELEX: 32022L2555

Summary: Essential and important entities must secure the systems running their services with proportionate technical measures, minimally: incident handling, backups and disaster recovery, supply-chain security, secure development, vulnerability handling, encryption, access control, and multi-factor authentication.
Developer impact: Enforce MFA on privileged access, keep backups and recovery working, encrypt data in transit and at rest, and apply access control and secure development in the entity's own systems.
Code smells: mfa_enabled=False on an admin login path; backup cron job commented out or disabled; internal service traffic over http:// or verify=False; credentials hardcoded in entity infrastructure code
Related: cra_art6, nis2_art23

## nis2_art23
Reference: NIS2 Art. 23
Title: Reporting obligations
Regulation: NIS2
Source CELEX: 32022L2555

Summary: Covered entities report significant incidents to the CSIRT or competent authority without undue delay: early warning within 24 hours, notification within 72 hours, and later reports under 23(4). Trust-service notifications use the applicable 24-hour derogation.
Developer impact: Early warning: suspected unlawful/malicious cause or cross-border impact where applicable. Notification: initial assessment, severity/impact and available IoCs. Intermediate report on request; final report within one month, with the ongoing-incident progress/final-report exception in 23(4)(e). CRA reporting has different triggers and content.
Code smells: An established significant incident bypasses its applicable reporting deadline or knowingly strips information required and available at that stage; applicable service-recipient notices or protective advice are explicitly suppressed.
Related: cra_art14, nis2_art21, nis2_art30
Conditions and exceptions: An early warning is criticised for missing later notification/final-report fields; IoCs are unavailable; only a non-significant incident or voluntary intake is shown; the regulated-entity scope is unknown.

## nis2_art27
Reference: NIS2 Art. 27
Title: Registry of entities
Regulation: NIS2
Source CELEX: 32022L2555

Summary: DNS providers, TLD registries and domain-registration providers, cloud, data centre and managed service providers and managed security service providers, CDNs, marketplaces, search engines and social platforms must register with authorities, submitting entity name, sector, addresses, contacts, Member States served, and IP ranges. Changes must be notified within three months at most.
Developer impact: Send registration payloads with all mandatory fields including ip_ranges, and auto-notify the authority when registered data changes.
Code smells: registration payload missing ip_ranges or contact_details; change-notification deadline above three months; registry update hook removed from the address/contact change path; change detection never calling the notify API
Related: cra_art23, nis2_art28

## nis2_art28
Reference: NIS2 Art. 28
Title: Database of domain name registration data
Regulation: NIS2
Source CELEX: 32022L2555

Summary: TLD registries and registrars must keep an accurate, complete database of domain registration data - domain name, registration date, registrant name, email and phone - with published verification procedures. Non-personal data must be public; legitimate access requests answered within 72 hours.
Developer impact: Implement schemas with the mandatory fields, verify registrant contacts on intake, filter personal data out of public WHOIS/RDAP responses, and meet a 72-hour SLA on lawful access requests.
Code smells: public whois or rdap endpoint returning registrant_email or phone unfiltered; registration flow skipping contact verification; access_request SLA above 72 hours; verification stub that always returns true
Related: nis2_art27

## nis2_art30
Reference: NIS2 Art. 30
Title: Voluntary notification of relevant information
Regulation: NIS2
Source CELEX: 32022L2555

Summary: Beyond mandatory reporting, any entity may voluntarily notify CSIRTs of incidents, cyber threats and near misses. The receiving side must process these like mandatory reports while keeping the notifier's information confidential, and the report must not create extra liability for the reporter.
Developer impact: Provide encrypted intake, strict access control and data sanitization on voluntary-reporting channels, keeping reporter and report data confidential end to end.
Code smells: voluntary report intake storing submissions unencrypted; near_miss or cyber_threat channel removed; reporter identity exposed in logs or shared dashboards; threat data broadcast internally without sanitization
Related: dma_art43, nis2_art23
