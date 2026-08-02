# Precommiteu public regulation context - EU Data Act
Included regulations: EU Data Act (Regulation on harmonised rules on fair access to and use of data), CELEX 32023R2854.

Compact, developer-oriented SUMMARIES of code-relevant EU Data Act articles - NOT the legal text. Used to (a) retrieve the probable article area for a scanner finding and (b) show a short "why this matters" snippet in PR comments. For the authoritative wording, follow the EUR-Lex link rendered with each finding.

# EU Data Act (Regulation on harmonised rules on fair access to and use of data)

## eu_data_act_art3
Reference: EU DATA ACT Art. 3
Title: Obligation to make product data and related service data accessible to the user
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: Connected products and related services must give users their data by default: easy, secure, free, machine-readable, direct where feasible. Before contract, buyers must learn what data is generated, where and how long it is stored, and how to access or erase it.
Developer impact: Build direct export endpoints in structured JSON/CSV with full metadata, and render pre-contract disclosures covering data type, volume, retention and erasure.
Code smells: device data exported as proprietary binary instead of JSON/CSV; export strips calibration/timestamp metadata; checkout omits data/retention disclosures; data only via support email; erasure endpoint behind an admin flag
Related: eu_data_act_art4, eu_data_act_art5

## eu_data_act_art4
Reference: EU DATA ACT Art. 4
Title: The rights and obligations of users and data holders with regard to access, use and making available product data and related service data
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: Where users cannot pull data off the device, the holder must serve it on simple request: same quality, free, machine-readable, real-time where feasible. No dark patterns, excess ID checks or hoarded access logs; trade secrets tagged; non-personal data used only under contract.
Developer impact: Implement request-based access APIs with streaming, purge access logs after fulfilment, tag trade-secret fields, and keep export UIs neutral.
Code smells: access API returns 48h batches when realtime is feasible; access logs never purged; export buried in nested menus; government ID demanded for a simple pull; device data forwarded to marketing webhooks
Related: eu_data_act_art3, eu_data_act_art5, eu_data_act_art8, eu_data_act_art11

## eu_data_act_art5
Reference: EU DATA ACT Art. 5
Title: Right of the user to share data with third parties
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: On request, the holder must hand data to the user's chosen third party - same quality, machine-readable, real-time where feasible, free to the user. Gatekeepers (designated big-tech platforms) are ineligible, personal data needs a valid legal basis, and access logs must stay short-lived.
Developer impact: Build sharing APIs with a gatekeeper denylist, legal-basis/consent checks before personal data leaves, realtime streams where feasible, and short-lived logs.
Code smells: sharing endpoint has no gatekeeper denylist; personal data shared without a legal-basis/consent check; third-party access logs kept forever; daily batches where realtime is feasible; profiling third parties' usage without permission
Related: eu_data_act_art4, eu_data_act_art6, eu_data_act_art8, eu_data_act_art9

## eu_data_act_art6
Reference: EU DATA ACT Art. 6
Title: Obligations of third parties receiving data at the request of the user
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: A third party receiving data at the user's request may process it only for the agreed purpose and must erase it when no longer needed. It must not profile beyond the requested service, pass data to gatekeepers, build a competing product, or steer users manipulatively.
Developer impact: Add TTL/deletion jobs for received data, scope processing to the agreed purpose, block gatekeeper forwarding, and keep revoke controls visible.
Code smells: received data persisted with no TTL or purge job; ML profiling added when user asked only for alerts; webhook forwards data to a gatekeeper ad API; data copied into a competing-product repo; revoke-access button hidden or invisible
Related: eu_data_act_art5

## eu_data_act_art8
Reference: EU DATA ACT Art. 8
Title: Conditions under which data holders make data available to data recipients
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: Data made available to a recipient must flow on fair, reasonable, non-discriminatory and transparent terms. Verify the user's request before transmitting, treat comparable recipients equally, and keep trade secrets out of shared payloads.
Developer impact: Verify a user-request token before any transfer, apply uniform rate limits and quality across recipients, and filter trade-secret fields.
Code smells: partner export runs without a verified user_consent/request id; third parties throttled while own subsidiary is unlimited; lower resolution served to independent recipients; trade-secret fields left in shared JSON; default cron pushes data with no user request
Related: eu_data_act_art5, eu_data_act_art9

## eu_data_act_art9
Reference: EU DATA ACT Art. 9
Title: Compensation for making data available
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: Compensation for B2B data sharing must be non-discriminatory and reasonable; for small and medium-sized enterprises (SMEs) and not-for-profit research recipients it must not exceed the direct costs of making data available. Holders must show how the price was calculated.
Developer impact: Implement cost-only price caps keyed on is_sme/is_non_profit flags, and expose the calculation basis (volume, format, storage) in invoices and billing APIs.
Code smells: flat fee with no SME/non-profit cost-cap branch; user model lacks is_sme/is_non_profit flag; invoice omits volume/format/storage breakdown; profit margin applied to non-profit research orgs; billing webhook missing calculation metadata
Related: eu_data_act_art8, eu_data_act_art29, eu_data_act_art34

## eu_data_act_art11
Reference: EU DATA ACT Art. 11
Title: Technical protection measures on the unauthorised use or disclosure of data
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: Holders may use technical protection measures (encryption, smart contracts) against unauthorised use - but never to block access users and recipients are entitled to. Recipients must not strip or circumvent protections; unlawfully shared data must be erasable on request.
Developer impact: Ensure DRM/keys never lock owners out of their own data, never bypass a source's protections, and support cascading erasure of wrongly shared data.
Code smells: DRM blocks the owner's raw export; provider-held key blocks users' own exports; pipeline strips protection headers from telemetry; aggregator circumvents source rate limits; no cascade-delete across replicas
Related: eu_data_act_art4, eu_data_act_art5, eu_data_act_art6, eu_data_act_art8

## eu_data_act_art14
Reference: EU DATA ACT Art. 14
Title: Obligation to make data available on the basis of an exceptional need
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: When a public body, the European Commission or the European Central Bank (ECB) demonstrates an exceptional need, holders must supply the requested data together with the metadata needed to interpret and use it. Exports must match the request, not a degraded version.
Developer impact: Build authority-request export pipelines preserving interpretative metadata (calibration, timestamps, dictionaries) and the requested granularity.
Code smells: authority export strips sensor calibration metadata; data dictionary omitted; raw data aggregated into daily averages against the request; timestamps truncated in payload; GPS exported without timestamp/status metadata
Related: eu_data_act_art17, eu_data_act_art18, eu_data_act_art19

## eu_data_act_art17
Reference: EU DATA ACT Art. 17
Title: Requests for data to be made available
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: A public body's request must specify the data and metadata needed, purpose, legal provision, deadlines, expected erasure date, and onward recipients. Personal data may be requested only in pseudonymised form, and only when non-personal data is insufficient; requests must be published online unless publication would create a security risk.
Developer impact: Generate request payloads with all mandatory fields, default to pseudonymised data, and notify authorities and holders on delegation.
Code smells: request JSON missing expected_erasure_date or purpose; no requires_pseudonymisation default; missing DPA notification when personal data requested; requests auto-published without a risk check; delegation without notifying the holder
Related: eu_data_act_art14, eu_data_act_art18, eu_data_act_art19

## eu_data_act_art18
Reference: EU DATA ACT Art. 18
Title: Compliance with requests for data
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: A data holder answering a public body's request must do so without undue delay - and where personal data is involved, pseudonymise or anonymise it first, in line with the measures stated in the request.
Developer impact: Add an anonymisation/pseudonymisation step to every authority-request export, covering names, national IDs and IBANs.
Code smells: tax records exported with raw national IDs; passenger manifest keeps full names and contacts; batch job sends IBANs unmasked; telemetry export retains drivers' home GPS routes; export SQL has no masking step
Related: eu_data_act_art14, eu_data_act_art17, eu_data_act_art19

## eu_data_act_art19
Reference: EU DATA ACT Art. 19
Title: Obligations of public sector bodies, the Commission, the European Central Bank and Union bodies
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: After receiving exceptional-need data, the public body must protect it: restrict access to what the task needs, keep it secure, respect trade secrets, erase it when no longer needed, and tell the holder it was erased.
Developer impact: Store received datasets with TTLs and scoped access, transfer over TLS, tag trade-secret metadata, and notify the holder on deletion.
Code smells: received dataset stored with no TTL or deletion job; deletion runs without notifying the data holder; payload missing the trade-secret flag; data transmitted over plain HTTP; read access not scoped to the reporting module
Related: eu_data_act_art14, eu_data_act_art17, eu_data_act_art21

## eu_data_act_art21
Reference: EU DATA ACT Art. 21
Title: Sharing of data obtained in the context of an exceptional need with research organisations or statistical bodies
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: A public body may pass exceptional-need data to research or statistical bodies, but must notify the holder stating who receives it, why, for how long, and under what protection measures. Researchers may keep the data at most six months after the body erases its copy.
Developer impact: Wire a holder-notification webhook with mandatory fields into research-sharing flows and enforce the 6-month post-erasure cap.
Code smells: research share skips the holder notification; payload missing purpose_of_transmission or contact details; missing protection-measures field; research retention 12 months instead of max 6 post-erasure; no TTL on shared research datasets
Related: eu_data_act_art17, eu_data_act_art19

## eu_data_act_art23
Reference: EU DATA ACT Art. 23
Title: Removing obstacles to effective switching
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: Cloud/edge providers must remove contractual, commercial, technical and organisational obstacles to switching providers or moving on-premises. Customers must be able to port exportable data and digital assets without lock-in.
Developer impact: Provide documented bulk export in standard formats, avoid punitive rate limits or provider-revoked keys, and never destroy data early on termination.
Code smells: export serialises to an undocumented proprietary format; punitive rate limits on bulk export; export encrypted with a provider key revoked at termination; termination deletes records before the portability job ends; no bulk export path, forcing UI scraping
Related: eu_data_act_art25, eu_data_act_art26, eu_data_act_art27, eu_data_act_art29, eu_data_act_art30

## eu_data_act_art25
Reference: EU DATA ACT Art. 25
Title: Contractual terms concerning switching
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: The switching contract must guarantee a maximum two-month notice period, a transition of at most 30 days with continuity, a retrieval window of at least 30 days after that transition, and full erasure only once retrieval ends. All portable data and asset categories must be listed.
Developer impact: Encode the 30-day retrieval window and 2-month notice cap in termination logic, schedule erasure only after retrieval, and export every category.
Code smells: termination deletes data immediately, no 30-day retrieval window; retrieval_days set below 30; no scheduled erasure job after the window expires; export omits whole digital-asset categories; switch data sent over unencrypted HTTP
Related: eu_data_act_art23, eu_data_act_art26, eu_data_act_art29

## eu_data_act_art26
Reference: EU DATA ACT Art. 26
Title: Information obligation of providers of data processing services
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: Providers must inform customers about switching: available procedures, supported export formats, known restrictions, and a reference to a live online register of all exportable data structures and formats.
Developer impact: Serve a live machine-readable register of exportable data structures and surface switching procedures and format limits in the UI and docs.
Code smells: static PDF instead of a live export-format register endpoint; /api/v1/export-schemas returns 404; export docs missing data-structure definitions; volume limits absent from the porting UI; switching procedure only via support tickets
Related: eu_data_act_art23, eu_data_act_art25, eu_data_act_art30

## eu_data_act_art27
Reference: EU DATA ACT Art. 27
Title: Obligation of good faith
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: All parties must act in good faith to make switching effective: transfer data in a timely way and keep the service running during the migration. Artificial throttling, lossy pipelines and exports that take the live service down all break this duty.
Developer impact: Make export pipelines non-blocking and paginated, avoid artificial bandwidth caps, and add retry/dead-letter handling so migrations lose nothing.
Code smells: export throttled to 10Kbps in the gateway config; synchronous full-table dump times out the live portal; webhook silently drops payloads on slow destinations; unpaginated query crashes the backend mid-migration; export pipeline lacks retry or dead-letter handling
Related: eu_data_act_art23, eu_data_act_art25, eu_data_act_art30

## eu_data_act_art28
Reference: EU DATA ACT Art. 28
Title: Contractual transparency obligations on international access and transfer
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: Providers must publish on their websites - and keep current - where their ICT infrastructure sits by jurisdiction, plus measures guarding against unlawful third-country governmental access to non-personal data. Contracts must reference these disclosures.
Developer impact: Maintain accurate jurisdiction and safeguard pages, and inject the required URLs into generated contracts and terms screens.
Code smells: legal footer omits data-jurisdiction disclosures; generated agreement lacks the transfer-safeguards URL; infrastructure-location link missing from terms; safeguards route broken or unlinked; foreign-access measures not described anywhere
Related: eu_data_act_art32

## eu_data_act_art29
Reference: EU DATA ACT Art. 29
Title: Gradual withdrawal of switching charges
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: Switching charges are being phased out: from 11 January 2024 they may only cover direct switching costs, and from 12 January 2027 they are banned. Fees, early-termination penalties and complexity must be disclosed pre-contract and on a public page.
Developer impact: Date-gate billing to zero switching charges after 2027-01-12 and cap earlier ones at direct cost; add pre-contract fee disclosures and a public fees page.
Code smells: switching fee charged with no 2027-01-12 cut-off check; flat 500-euro fee instead of computed direct costs; checkout missing the fee/penalty disclosure; no public switching-fees page; extraction invoices still generated after the deadline
Related: eu_data_act_art23, eu_data_act_art25, eu_data_act_art31

## eu_data_act_art30
Reference: EU DATA ACT Art. 30
Title: Technical aspects of switching
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: Switching must work technically: open interfaces, free of charge, exporting all exportable data in a structured, commonly used, machine-readable format, following harmonised standards where they exist.
Developer impact: Expose open, documented export APIs (REST/GraphQL) and produce structured JSON/CSV exports that keep relational keys and follow published standards.
Code smells: switch export emits flattened PDFs instead of JSON/CSV; undocumented proprietary binary format; portability endpoint limited to 1 request per hour; no open API, migration needs manual DB dumps; export drops relational keys like customer/order IDs
Related: eu_data_act_art23, eu_data_act_art26, eu_data_act_art33, eu_data_act_art34

## eu_data_act_art31
Reference: EU DATA ACT Art. 31
Title: Specific regime for certain data processing services
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: Custom-built single-customer services and non-production test/evaluation services escape some switching obligations - but the provider must say, before contract, exactly which do not apply.
Developer impact: Render the exemption notice in onboarding, checkout and API provisioning flows for trial, sandbox, beta and custom-built services.
Code smells: sandbox provisioning shows no exemption disclosure; trial signup reuses standard ToS without non-production clauses; exemption modal bypassed for custom-built dashboards; beta checkout omits the which-obligations-do-not-apply text; exemption notice missing from the provisioning API
Related: eu_data_act_art23, eu_data_act_art29, eu_data_act_art30

## eu_data_act_art32
Reference: EU DATA ACT Art. 32
Title: International governmental access and transfer
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: Providers must use technical, organisational and legal measures to block international governmental access to EU-held non-personal data where it conflicts with EU or national law. If a third-country request must be honoured, release the minimum and notify the customer where allowed.
Developer impact: Scope foreign-authority exports to minimum fields, keep non-EU replication behind EU-held keys, and notify the customer before fulfilment.
Code smells: full transaction history dumped to a non-EU authority; bucket auto-replicates to a non-EU region without EU-held keys; third-country transfer fires with no customer notification; request answered beyond the asked timeframe; no geo-restriction on admin access
Related: eu_data_act_art28

## eu_data_act_art33
Reference: EU DATA ACT Art. 33
Title: Essential requirements regarding interoperability of data, of data sharing mechanisms and services, as well as of common European data spaces
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: Datasets offered in common European data spaces must be interoperable: machine-readable descriptions of content, quality, licensing and methodology, public documentation of structures and vocabularies, and automated access via APIs or bulk download.
Developer impact: Publish machine-readable dataset metadata and OpenAPI specs, embed licence and use-restriction fields in payloads, and provide automated access.
Code smells: dataset API lacks methodology/quality metadata; no public OpenAPI spec; licence and use restrictions only in a PDF; manual CSV the only access path; proprietary binary pushed into a data space
Related: eu_data_act_art30, eu_data_act_art34

## eu_data_act_art34
Reference: EU DATA ACT Art. 34
Title: Interoperability for the purposes of in-parallel use of data processing services
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: Providers must let customers use several data processing services in parallel (multi-cloud): open interfaces and the same export duties apply, and in-parallel egress charges must not exceed costs actually incurred.
Developer impact: Offer standard parallel-sync endpoints, never discriminate against competitor destinations, and bill egress at incurred cost only.
Code smells: egress billing multiplier exceeds actual transit cost; flat arbitrary egress fee for parallel routing; sync to a second provider deliberately throttled; webhooks drop payloads to competing platforms; no standard REST/gRPC endpoints, forcing screen-scraping
Related: eu_data_act_art23, eu_data_act_art30, eu_data_act_art33

## eu_data_act_art36
Reference: EU DATA ACT Art. 36
Title: Essential requirements regarding smart contracts for executing data sharing agreements
Regulation: EU DATA ACT
Source CELEX: 32023R2854

Summary: Smart contracts executing data sharing agreements need rigorous access control, robustness against manipulation, a safe termination mechanism, and archiving of transaction data, logic and code when wound down. Vendors must assess conformity and issue an EU declaration of conformity.
Developer impact: Add access-control modifiers, pause/termination functions, and state-change events enabling off-chain archiving to every data-sharing contract.
Code smells: contract lacks a Pausable/circuit-breaker; state-changing function without onlyOwner/role modifier; no events emitted for off-chain archiving; no termination function for accidental executions; contract deactivated without archiving final state
Related: eu_data_act_art11, eu_data_act_art33
