---
title: Regulation packs
nav_order: 5
---

# Regulation packs

precommitEU ships one knowledge pack plus one detector adapter per regulation.
A single run scans your code against one, several, or all of them.

Eight EU regulations are covered by six packs, because CRA, DMA and NIS2 share
one adapter.

## Available packs

| `--regulations` value | Regulation | Applies since | Scan with it when your code |
|---|---|---|---|
| `gdpr` *(default)* | General Data Protection Regulation, [Regulation (EU) 2016/679](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32016R0679) | 25 May 2018 | touches personal data: user records, auth, profiles, logging, exports, analytics |
| `eu_ai_act` | Artificial Intelligence Act, [Regulation (EU) 2024/1689](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689) | 2 Aug 2026 (phased) | builds, serves or calls AI models; automated decisions, biometrics |
| `eu_data_act` | Data Act, [Regulation (EU) 2023/2854](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R2854) | 12 Sep 2025 | is a connected or IoT product, or does data sharing, access requests, cloud switching |
| `dora` | Digital Operational Resilience Act, [Regulation (EU) 2022/2554](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R2554) | 17 Jan 2025 | belongs to a financial entity: payments, trading, ICT risk, incident reporting |
| `dsa` | Digital Services Act, [Regulation (EU) 2022/2065](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R2065) | 17 Feb 2024 | runs a platform with user content: moderation, recommenders, ads |
| `cra_dma_nis2` | Three regulations in one adapter, see below | | |

`cra_dma_nis2` bundles three related acts:

| Regulation | Applies since | Scan with it when your code |
|---|---|---|
| **CRA**, Cyber Resilience Act, [Regulation (EU) 2024/2847](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R2847) | 11 Dec 2027 (reporting duties 11 Sep 2026) | ships a product with digital elements: vulnerability handling, secure updates, SBOM |
| **DMA**, Digital Markets Act, [Regulation (EU) 2022/1925](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022R1925) | 2 May 2023 | belongs to a designated gatekeeper: interoperability, self-preferencing, data reuse |
| **NIS2**, Network and Information Systems Directive 2, [Directive (EU) 2022/2555](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32022L2555) | via national law, due 17 Oct 2024 | runs an essential or important entity in one of 18 critical sectors: risk management, incident reporting |

## Dates worth knowing

Everything above except NIS2 is a **Regulation**: it applies directly and
identically in every member state from its date, with no national step. NIS2 is
a **Directive**, so it binds each member state to legislate rather than
applying on its own. What you comply with is your country's implementing act.
Transposition was due 17 October 2024; most states have legislated, a few are
still behind, so the detail varies by country.

The AI Act applies in stages: prohibitions and AI-literacy duties since
2 February 2025, general-purpose AI model obligations since 2 August 2025, most
remaining provisions from 2 August 2026, and Article 6(1) high-risk duties from
2 August 2027.

## Choosing the right packs

`gdpr` is the sensible default for almost any product repo. The other five are
opt-in when your sector or feature set matches.

**Use each pack only where its regulation applies.** Every adapter is trained
and evaluated on code its own regulation governs. Pointed at a codebase outside
that scope it produces unreliable output, flagging code that is not a violation
under that regulation. Scanning with all six is not more thorough, only
noisier.

## Running several in one scan

```bash
precommiteu scan src/                                    # gdpr, the default
precommiteu scan src/ --regulations gdpr,eu_ai_act,dora  # several
```

```python
from precommiteu import scan_paths

result = scan_paths(["src/"], regulations=("gdpr", "eu_ai_act", "dora"))
```

How it behaves:

- Pass a comma-separated list to `--regulations`, or a tuple to `regulations=`
  in the library. Order is preserved.
- The base model, used by the orchestrator and validator, starts **once** and
  is shared. For each regulation the scanner swaps only the **detector** to
  that regulation's LoRA adapter, resolved as
  `<models-dir>/<regulation>/detector-adapter.gguf`.
- Regulations are scanned **sequentially**, and every finding is tagged with
  its `regulation`. Reports are written incrementally, so interrupting a run
  keeps the results from regulations already completed.
- A regulation with no adapter under the models directory still runs, in
  degraded mode with the detector on the base model. A warning is logged.
- `--detector-adapter` pins one specific adapter, so it is valid only with a
  **single** regulation. Combining it with several is an error (exit 2).

## Related

- [CLI reference](cli.md) for `--regulations` and model selection flags
- [Installation](install.md) for downloading only the packs you need
- [Examples](examples.md) for worked multi-regulation scans
