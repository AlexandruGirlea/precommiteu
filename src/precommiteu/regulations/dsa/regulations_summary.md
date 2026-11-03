# Precommiteu public regulation context - DSA
Included regulations: DSA (Digital Services Act), CELEX 32022R2065.

Compact, developer-oriented SUMMARIES of code-relevant DSA articles - NOT the
legal text. Used to (a) retrieve the probable article area for a scanner finding
and (b) show a short "why this matters" snippet in PR comments. For the
authoritative wording, follow the EUR-Lex link rendered with each finding.

# DSA (Digital Services Act)

Scope and evidence: code smells below are investigation leads, not automatic violations. Establish the applicable actor, activity, conditions and exceptions from the supplied context; missing information in one excerpt is not proof of a system-wide omission.

Applicability: Distinguish intermediary, hosting, online-platform, marketplace and designated VLOP/VLOSE duties. Articles 15(2), 19 and 29 provide micro/small-enterprise exemptions with specified exceptions. Do not assume designation or a service tier from a recommender/ad feature. Article 8 imposes no general proactive-monitoring obligation; establish each specific duty before confirming an omission.

## dsa_art4
Reference: DSA Art. 4
Title: ‘Mere conduit’
Regulation: DSA
Source CELEX: 32022R2065

Summary: A network transit service (ISP, relay, proxy, VPN, messaging gateway) is not liable for the traffic it carries - but only if it does not start the transmission, pick the receiver, or select or modify the content. Transit copies may be kept only briefly and only to complete the transmission.
Developer impact: Keep relay/proxy code pass-through: no payload rewriting or injection, no algorithmic receiver selection, and purge transit buffers right after delivery.
Code smells: middleware rewrites URLs or injects banners into relayed traffic; relay picks recipients algorithmically; transit packets persisted to a permanent store; full packet captures retained indefinitely; gateway appends data to messages in transit
Related: dsa_art5, dsa_art6

## dsa_art5
Reference: DSA Art. 5
Title: ‘Caching’
Regulation: DSA
Source CELEX: 32022R2065

Summary: A caching layer (CDN, edge cache, reverse proxy) that temporarily stores content to speed up onward delivery is not liable for it - if it does not modify the cached content, follows industry caching rules like Cache-Control headers, and quickly removes cached copies once the original is taken down.
Developer impact: Honor Cache-Control/no-store/max-age directives, never alter cached bodies, and wire takedown webhooks to immediate cache-invalidation endpoints.
Code smells: cache ignores Cache-Control or no-store; cached responses modified or headers stripped; no purge_cache/invalidate endpoint; takedown webhook does not invalidate cached copies; content cached past the upstream max-age
Related: dsa_art4, dsa_art6

## dsa_art6
Reference: DSA Art. 6
Title: Hosting
Regulation: DSA
Source CELEX: 32022R2065

Summary: A service storing user-provided content is not liable for it as long as it removes or disables access to illegal content quickly once it knows about it. A marketplace loses this protection when its UI makes a third-party seller's product look like the platform's own offer.
Developer impact: Build takedown APIs and removal flags into every user-content store, and always render the third-party seller's identity on listings.
Code smells: user-content table without takedown/is_hidden flag; uploads in immutable storage with no delete path; no API to disable access to flagged content; CDN copy survives an admin takedown; listing UI hides the real seller behind the platform brand
Related: dsa_art4, dsa_art5, dsa_art16, dsa_art17

## dsa_art9
Reference: DSA Art. 9
Title: Orders to act against illegal content
Regulation: DSA
Source CELEX: 32022R2065

Summary: When an authority orders the platform to act against specific illegal content, it must tell that authority without undue delay whether and when it acted. The order's details - legal basis, statement of reasons, exact URLs, redress information - must also reach the affected user.
Developer impact: Record when effect was given, report back to the issuing authority, and notify the affected user with reasons and redress.
Code smells: takedown executed with no callback to the authority; effect-given timestamp not captured; user notice missing statement_of_reasons or redress link; territorial_scope field absent from the order model; no user notification event on order-driven removal
Related: dsa_art10, dsa_art17

## dsa_art10
Reference: DSA Art. 10
Title: Orders to provide information
Regulation: DSA
Source CELEX: 32022R2065

Summary: When an authority orders the platform to hand over information about specific users, it must confirm receipt and report what effect it gave. The affected user must be informed, including the statement of reasons and the redress options available.
Developer impact: Add receipt acknowledgment and effect-given reporting to legal-request handlers, plus a user notification carrying the order's reasons and redress options.
Code smells: law-enforcement portal fulfils data requests with no receipt acknowledgment; affected user never notified of the disclosure; user notice omits redress options; generic hardcoded message instead of the order's statement of reasons; no record of when effect was given
Related: dsa_art9, dsa_art18

## dsa_art11
Reference: DSA Art. 11
Title: Points of contact for Member States’ authorities, the Commission and the Board
Regulation: DSA
Source CELEX: 32022R2065

Summary: Every intermediary service must designate a single point of contact that authorities, the European Commission and the Board (the EU body of national digital-services regulators) can reach directly by electronic means. The contact details and the languages it accepts must be public, easy to find and current.
Developer impact: Expose the regulatory contact and its supported languages on a public, unauthenticated page or endpoint and keep it current.
Code smells: regulator contact page behind a login wall; contact component missing supported-languages data; only a postal address with no electronic channel; authority inquiries forced through a consumer chatbot; legal-notice template omits the point-of-contact fields
Related: dsa_art12, dsa_art13

## dsa_art12
Reference: DSA Art. 12
Title: Points of contact for recipients of the service
Regulation: DSA
Source CELEX: 32022R2065

Summary: Users must get a single point of contact they can reach quickly, electronically, and in a user-friendly way. Users choose how they communicate, and the channel cannot be purely automated - a human option is required. The contact info must be public and easy to find.
Developer impact: Provide a public contact channel with a non-automated (human) option and let users pick the communication method.
Code smells: support flow offers only a chatbot or FAQ widget with no human fallback; contact details hidden behind authenticated routes; contact info only inside a downloadable PDF; phone-tree API mandatory before showing an email; direct contact email removed from the public footer
Related: dsa_art11, dsa_art13

## dsa_art13
Reference: DSA Art. 13
Title: Legal representatives
Regulation: DSA
Source CELEX: 32022R2065

Summary: A provider with no EU establishment but offering services in the EU must appoint an EU legal representative. The representative's name, postal address, email and phone number must be reported to the regulator and kept public, easily accessible, accurate and current.
Developer impact: Publish the legal representative's full contact details (name, address, email, phone) on a public page or API and keep them updated.
Code smells: legal_representative fields missing from the public contact page; legal-representative endpoint returns 403 for unauthenticated calls; outdated rep email hardcoded in static HTML; rep details buried in a deeply nested accordion; postal address omitted from the public notice component
Related: dsa_art11, dsa_art12

## dsa_art14
Reference: DSA Art. 14
Title: Terms and conditions
Regulation: DSA
Source CELEX: 32022R2065

Summary: Terms and conditions must explain all content restrictions, the moderation tools used (algorithmic and human) and the complaint procedure, in plain language and a public machine-readable format. Users must be told of significant changes, and services aimed at minors must explain conditions in a way minors understand.
Developer impact: Serve T&C in a machine-readable format, trigger notifications on significant changes, and provide minor-friendly and localized versions.
Code smells: T&C only as PDF/image with no machine-readable endpoint; moderation rules updated without notifying users; minors shown the adult legalese; T&C hardcoded in one language; automated moderation not disclosed in the T&C schema
Related: dsa_art25, dsa_art27

## dsa_art15
Reference: DSA Art. 15
Title: Transparency reporting obligations for providers of intermediary services
Regulation: DSA
Source CELEX: 32022R2065

Summary: At least yearly the provider must publish a machine-readable transparency report on its content moderation: authority orders per Member State and content type, notices received, actions taken, automated versus human decisions, and median response times, logged in enough detail to compute them all.
Developer impact: Log moderation events with timestamp, category, origin and automated flag, and publish aggregated machine-readable reports.
Code smells: transparency report only a static PDF; moderation log missing the automated-vs-manual flag; received-at timestamp not stored, median times uncomputable; notices not categorised by illegality type; trusted_flagger origin flag absent from the report schema
Related: dsa_art24, dsa_art42

## dsa_art16
Reference: DSA Art. 16
Title: Notice and action mechanisms
Regulation: DSA
Source CELEX: 32022R2065

Summary: Hosting services must enable sufficiently precise and substantiated electronic notices of illegal content. Where electronic contact details are supplied, acknowledge receipt and tell the notifier the decision and redress possibilities; disclose automated processing used for the decision.
Developer impact: The notifier/reporter receives art16 communications; the person whose content or account was restricted receives art17 reasons. Establish the addressee rather than routing every decision email to art17.
Code smells: The completed notice mechanism prevents required information being supplied; an outcome message to the reporter explicitly omits applicable redress information or conceals automated decision-making.
Related: dsa_art17, dsa_art20, dsa_art22
Conditions and exceptions: No electronic contact is available for the alleged missing reply; the claim demands mandatory identity for the qualifying child-sexual-abuse/exploitation notices; a required input is enabled as an optional field rather than forced.

## dsa_art17
Reference: DSA Art. 17
Title: Statement of reasons
Regulation: DSA
Source CELEX: 32022R2065

Summary: Hosting services give affected recipients clear and specific reasons for restrictions based on illegality or incompatibility with terms, including applicable facts, grounds, automation and redress information. The duty covers visibility and monetisation restrictions as well as removal/suspension.
Developer impact: Check 17(2) and 17(5) exceptions before demanding notice. Explaining a moderation decision is distinct from the later internal complaint process (art20).
Code smells: An applicable restriction notice explicitly discards its grounds, scope/duration or redress information; the established notification flow is disabled.
Related: dsa_art9, dsa_art16, dsa_art20
Conditions and exceptions: Electronic contact details are unknown; the content is established to be deceptive high-volume commercial content; the action follows an Article 9 order; the message is to the notifier (art16). A generic spam label alone does not establish the commercial-content exception.

## dsa_art18
Reference: DSA Art. 18
Title: Notification of suspicions of criminal offences
Regulation: DSA
Source CELEX: 32022R2065

Summary: If a hosting provider learns of information suggesting a criminal offence threatening someone's life or safety, it must promptly inform law enforcement of the Member State concerned and hand over all relevant information. If the Member State is unknown, it notifies the state where it is established, or Europol, or both.
Developer impact: Build a real-time alert workflow that detects life/safety threats, routes by Member State, falls back to Europol, and packages all relevant evidence.
Code smells: threat alerts queued for weekly manual review; one hardcoded law-enforcement email for all countries; no Member-State routing logic; evidence/chat logs dropped from the report payload; threat signals handled only as a spam flag
Related: dsa_art10

## dsa_art20
Reference: DSA Art. 20
Title: Internal complaint-handling system
Regulation: DSA
Source CELEX: 32022R2065

Summary: Online platforms must give users at least six months to complain, electronically and free of charge, against moderation decisions (removal, suspension, demonetisation, termination). Complaints must be handled diligently and not by automated means alone, and decisions reversed when shown unjustified.
Developer impact: Implement a free electronic appeal flow with a six-month window, a human-review queue, and automated decision and redress notifications.
Code smells: complaint window hardcoded below six months; appeals auto-rejected with no human reviewer queue; fee charged before lodging a complaint; original content purged so appeals cannot be substantiated; complaint decision email missing out-of-court options
Related: dsa_art16, dsa_art17, dsa_art21, dsa_art23, dsa_art86

## dsa_art21
Reference: DSA Art. 21
Title: Out-of-court dispute settlement
Regulation: DSA
Source CELEX: 32022R2065

Summary: Applicable online platforms must make certified out-of-court dispute settlement information accessible and engage in good faith, while preserving access to court at any stage. The settlement body cannot impose a binding outcome on the parties.
Developer impact: Voluntary implementation is lawful. A successful recipient is reimbursed as required by 21(5); a losing recipient need not reimburse platform costs absent manifest bad faith, although the body may charge a nominal recipient fee.
Code smells: An applicable settlement route is deliberately hidden or unjustifiably gated; the workflow makes settlement a compulsory prerequisite to court action or waives court access; the platform charges the user its costs without the required bad-faith finding.
Related: dsa_art17, dsa_art20
Conditions and exceptions: The platform voluntarily implements a settlement outcome without restricting further legal remedies; the same dispute on the same grounds was already resolved; the alleged upload facility is a duty of the settlement body rather than the platform.

## dsa_art22
Reference: DSA Art. 22
Title: Trusted flaggers
Regulation: DSA
Source CELEX: 32022R2065

Summary: Notices submitted by designated trusted flaggers within their area of expertise must be prioritised and decided without undue delay. Platforms need technical measures that recognise trusted-flagger status in the notice intake and process those notices ahead of ordinary reports.
Developer impact: Add trusted-flagger identification to the notice intake, a priority lane in the moderation queue, and tracking of flagger submission outcomes.
Code smells: all notices in one FIFO queue regardless of flagger status; notice API lacks a trusted-flagger identity field; is_trusted metadata dropped before insertion; no fast-track or priority override in the moderation queue; no tracking of flagger accuracy
Related: dsa_art16, dsa_art23, dsa_art86

## dsa_art23
Reference: DSA Art. 23
Title: Measures and protection against misuse
Regulation: DSA
Source CELEX: 32022R2065

Summary: Platforms must suspend - for a reasonable period and only after a prior warning - users who frequently post clearly illegal content, and submitters who frequently file clearly unfounded notices or complaints. Suspension decisions must weigh absolute numbers, proportions, gravity and intent case by case.
Developer impact: Implement warning-first, time-limited suspension workflows backed by counters of violations and unfounded notices or complaints.
Code smells: immediate permanent ban with no prior warning trigger; suspension with no expiry timestamp; one rejected report disables all future submissions; no counters for unfounded-notice frequency or proportion; no case-by-case assessment fields in the suspension model
Related: dsa_art17, dsa_art20

## dsa_art24
Reference: DSA Art. 24
Title: Transparency reporting obligations for providers of online platforms
Regulation: DSA
Source CELEX: 32022R2065

Summary: On top of the base transparency reports required of all intermediaries, online platforms must report dispute-settlement outcomes and misuse suspensions, publish average monthly active EU recipients (MAU - monthly active users) six-monthly on the public interface, and submit moderation decisions to the Commission's database after stripping personal data.
Developer impact: Build six-month-average MAU pipelines, a public metric UI, and a sanitised decision export to the Commission database.
Code smells: MAU hardcoded, not computed over six months; decisions pushed to the Commission database with emails/IPs intact; public active-recipients UI missing; dispute outcomes stored unstructured; suspension counts not split by reason
Related: dsa_art15, dsa_art21, dsa_art23, dsa_art42

## dsa_art25
Reference: DSA Art. 25
Title: Online interface design and organisation
Regulation: DSA
Source CELEX: 32022R2065

Summary: Applicable online platforms must not design interfaces that deceive, manipulate or materially distort recipients' free and informed decisions. Article 25(2) excludes practices covered by the Unfair Commercial Practices Directive or GDPR.
Developer impact: Evaluate the actual practice and statutory carve-out. Do not confirm an Article 25 violation simply because a consent banner or consumer cancellation flow resembles a dark-pattern example.
Code smells: A supported in-scope flow uses deceptive presentation, fabricated scarcity or materially obstructive repeated choices; the supplied behavior establishes manipulation rather than merely an interface style.
Related: dsa_art14, dsa_art26, dsa_art27
Conditions and exceptions: The practice is covered by GDPR or the Unfair Commercial Practices Directive; only a legitimate offer, ordinary confirmation or different button style is shown without the prohibited effect.

## dsa_art26
Reference: DSA Art. 26
Title: Advertising on online platforms
Regulation: DSA
Source CELEX: 32022R2065

Summary: Each ad must be identifiable in real time as an ad, showing on whose behalf it appears, who paid for it, and the main targeting parameters with a way to change them. Users need a way to declare commercial content, and ads must not be targeted by profiling on sensitive data such as health, religion, politics or sexual orientation.
Developer impact: Render ad labels, sponsor/payer fields and a why-this-ad disclosure on every ad; add a commercial-content toggle; block sensitive features in targeting models.
Code smells: sponsored item rendered with no Ad badge; sponsor_name or paid_by dropped from the ad payload; no why-am-I-seeing-this-ad link; no commercial-content toggle on uploads; health or political tags fed into ad-targeting features
Related: dsa_art25, dsa_art28, dsa_art39

## dsa_art27
Reference: DSA Art. 27
Title: Recommender system transparency
Regulation: DSA
Source CELEX: 32022R2065

Summary: Applicable online platforms explain recommender main parameters and available influence options in their terms. Where several options are available, Article 27(3) requires an accessible facility to select and modify the preferred option where recommendations appear.
Developer impact: Article 27 does not universally require multiple ranking modes. Article 38 requires a non-profiling option for designated VLOPs/VLOSEs; distinct supported obligations can coexist.
Code smells: An established user-selectable ranking option is ignored or the selection facility is obstructed; the supplied terms/disclosure flow explicitly removes required main-parameter information.
Related: dsa_art14, dsa_art38
Conditions and exceptions: The only allegation is that a single fixed ranking lacks alternative modes; only scoring computation is shown without the relevant interface or terms; the claim concerns the designated-service non-profiling obligation (art38).

## dsa_art28
Reference: DSA Art. 28
Title: Online protection of minors
Regulation: DSA
Source CELEX: 32022R2065

Summary: Applicable online platforms accessible to minors need appropriate and proportionate privacy, safety and security measures. Profiling-based advertising is prohibited when the provider knows with reasonable certainty that the recipient is a minor; Article 28(3) does not require extra personal-data collection to assess age.
Developer impact: Article 28(3) is not a ban on all age verification; its data protection must be assessed under applicable law. Lack of age certainty alone does not remove the separate 28(1) duty for services accessible to minors.
Code smells: Profiling-based advertising knowingly targets a minor or discards an established minor signal to bypass the protection.
Related: dsa_art26, dsa_art35
Conditions and exceptions: Ads are contextual rather than based on the person's profile; minority awareness is not established for the advertising claim; the sole allegation is either missing extra age-data collection or that collecting age-verification data is automatically prohibited by 28(3).

## dsa_art30
Reference: DSA Art. 30
Title: Traceability of traders
Regulation: DSA
Source CELEX: 32022R2065

Summary: Applicable marketplaces obtain and assess required trader identification before use, seek correction of deficient information and suspend where required. Trade-register details apply where the trader is registered; only 30(1)(a),(d),(e) are made public under 30(7).
Developer impact: Distinguish the trader from the product's manufacturer/importer/other economic operator. Obtain required data before platform use, but retain it securely throughout the relationship and for six months after it ends.
Code smells: A known applicable trader field is explicitly bypassed; verified deficiencies are allowed to persist without the required correction/suspension process; records are retained beyond the six-month post-contract period without the prescribed deletion.
Related: dsa_art6, dsa_art31, dsa_art32
Conditions and exceptions: The alleged missing register entry concerns an unregistered trader; a listing omits private identity-document/payment-account data that need not be public; a product economic-operator block is mistaken for the trader-onboarding record (art31).

## dsa_art31
Reference: DSA Art. 31
Title: Compliance by design
Regulation: DSA
Source CELEX: 32022R2065

Summary: Marketplace interfaces must be designed so traders can provide the buyer-facing compliance and product-safety information required before a sale: economic-operator contact details, clear product identification, the trader's sign or trademark, and labelling/marking information. The platform must make best efforts to check it is present before listings go live.
Developer impact: Add the required trader/product fields to listing forms and validate their presence before publication.
Code smells: listing publishable without economic-operator email and phone; no field for safety labels or conformity markings; product identification optional in the publish API; no pre-publication validation gate; no scheduled checks of live listings against recall databases
Related: dsa_art30, dsa_art32

## dsa_art32
Reference: DSA Art. 32
Title: Right to information
Regulation: DSA
Source CELEX: 32022R2065

Summary: When a marketplace learns a trader sold an illegal product or service, it must inform every consumer who bought it in the previous six months - stating the product is illegal, naming the trader, giving redress options. Lacking buyers' contact details, it must instead publish the information prominently on its interface.
Developer impact: Build a recall pipeline with a six-month purchase-history query, notification templates carrying trader identity and redress, and a public-notice fallback.
Code smells: purchase lookback hardcoded to 30 days instead of six months; recall email missing the trader's identity; redress link absent from the notification; buyers without contact details silently skipped with no public notice; notice says removed without stating illegality
Related: dsa_art30, dsa_art31

## dsa_art34
Reference: DSA Art. 34
Title: Risk assessment
Regulation: DSA
Source CELEX: 32022R2065

Summary: Very large platforms must assess systemic risks from their design and algorithms - spread of illegal content, fundamental-rights impacts, civic-discourse and electoral effects, minors' protection - yearly and before launching risk-critical features. Recommender, ad and moderation systems are in scope; supporting documents are kept three years.
Developer impact: Emit telemetry and audit events from recommender, ad and moderation algorithms; retain risk-assessment records three years.
Code smells: feed-ranking algorithm with no exposure or demographic logging; ad-targeting decisions emit no audit events; bot-detection and rate-limit triggers unlogged; moderation decision metadata hard-deleted; risk-assessment records purged before three years
Related: dsa_art35, dsa_art38, dsa_art42

## dsa_art35
Reference: DSA Art. 35
Title: Mitigation of risks
Regulation: DSA
Source CELEX: 32022R2065

Summary: Very large platforms must deploy mitigation measures matched to the risks found in their yearly systemic-risk assessment: adapting interfaces, moderation and recommender systems, limiting ads, plus targeted measures like age verification, parental controls, and prominent labels on manipulated media (deepfakes) with an easy way to report it.
Developer impact: Ship the mitigations: age-verification and parental-control flows, recommender adjustments, prominent manipulated-media labels and reporting tools.
Code smells: AI-generated metadata present but no visible badge; no age-verification gate where the risk demands one; no parental-control flow; no UI to report manipulated media
Related: dsa_art28, dsa_art34, dsa_art38

## dsa_art38
Reference: DSA Art. 38
Title: Recommender systems
Regulation: DSA
Source CELEX: 32022R2065

Summary: Very large platforms must offer, for each of their recommender systems, at least one option that is not based on profiling using personal data - for example a chronological feed, top-sellers, or distance/price ranking. The non-profiled option must genuinely avoid personal data, not just hide it.
Developer impact: Implement a non-profiling ranking mode for every recommender and expose it as a selectable option in the UI.
Code smells: every feed option consumes purchase or browsing history; no chronological or generic fallback ranking; non-personalized mode still reads the user's location history; recommendation API mandates user transaction features; no UI toggle to a profile-free feed
Related: dsa_art27, dsa_art34, dsa_art35

## dsa_art39
Reference: DSA Art. 39
Title: Additional online advertising transparency
Regulation: DSA
Source CELEX: 32022R2065

Summary: Very large platforms showing ads must run a public, searchable ad repository with multicriteria search APIs, holding each ad's content, sponsor, payer, display period and targeting/exclusion parameters until one year after last display. It must contain no recipient personal data, and ads removed as illegal must not be served with their full content from the repository.
Developer impact: Build the ad-archive API with the mandated fields, one-year retention after last display, personal-data exclusion and multicriteria search.
Code smells: paid_by missing from the ad-transparency endpoint; viewer IDs or IPs serialized into the public repository; cleanup purges ads six months after last display; archive only a static CSV with no searchable API; removed illegal ads still served with full content
Related: dsa_art24, dsa_art26

## dsa_art40
Reference: DSA Art. 40
Title: Data access and scrutiny
Regulation: DSA
Source CELEX: 32022R2065

Summary: Very large platforms must give the regulator access to the data needed to monitor compliance, explain their algorithmic systems on request, and give vetted researchers data access - including real-time where feasible - while protecting personal data, service security and trade secrets.
Developer impact: Build regulator/researcher data-access APIs with pseudonymisation, access control, token revocation and audit logging.
Code smells: researcher endpoint returns raw emails and IPs unpseudonymised; no token expiry or revocation for vetted researchers; trade-secret algorithm weights dumped into export payloads; no audit log of who accessed which dataset; real-time stream mixes private messages into research data
Related: dsa_art34, dsa_art42, dsa_art72

## dsa_art42
Reference: DSA Art. 42
Title: Transparency reporting obligations
Regulation: DSA
Source CELEX: 32022R2065

Summary: Very large platforms must publish transparency reports every six months, adding: moderation staffing per EU official language, moderator qualifications and training, accuracy indicators per language, and average monthly recipients per Member State. Confidential information may be redacted in the public version; complete reports go to the regulator.
Developer impact: Aggregate user metrics per Member State, add staffing and accuracy breakdowns, apply redaction and publish six-monthly.
Code smells: MAU computed globally with no Member-State grouping; report cadence yearly instead of six-monthly; moderator language breakdown absent; unredacted internal reports on the public portal; bot traffic not filtered from recipient counts
Related: dsa_art15, dsa_art24, dsa_art34

## dsa_art72
Reference: DSA Art. 72
Title: Monitoring actions
Regulation: DSA
Source CELEX: 32022R2065

Summary: The Commission may order a very large platform to give access to, and explanations of, its databases and algorithms, and to retain all documents needed to assess compliance. Code must support read-only regulator access and retention locks that override normal deletion schedules.
Developer impact: Implement legal-hold/retention-lock overrides on deletion jobs, read-only auditor roles, and exports that can reproduce and explain algorithm state.
Code smells: cleanup cron purges moderation logs with no legal-hold check; no read-only auditor role or endpoint for algorithm inspection; model weights overwritten so past decisions cannot be reproduced; compliance documents on auto-expiring storage; no interface to explain algorithm logic to auditors
Related: dsa_art40, dsa_art42

## dsa_art86
Reference: DSA Art. 86
Title: Representation
Regulation: DSA
Source CELEX: 32022R2065

Summary: Users can mandate a non-profit body or association to exercise their DSA rights on their behalf. Platforms need technical measures so complaints filed by such representative bodies through the internal complaint system are decided with priority and without undue delay.
Developer impact: Add representative-body identification to the complaint intake, a priority lane in complaint queues, and mandate-document upload support.
Code smells: complaint API lacks a submitter_type field for representative bodies; NGO complaints processed in the same FIFO queue as individuals; identical SLA for advocacy bodies and individuals; no upload field for mandate authorization documents; is_representative_body flag dropped before persistence
Related: dsa_art20, dsa_art22
