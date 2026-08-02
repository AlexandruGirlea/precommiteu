# Third-party notices

precommitEU is released under the Apache License 2.0 (see LICENSE). It is
built on and used alongside third-party libraries, model weights, tooling and
public reference material, each under its own license. None of them are
vendored here: they are installed, downloaded or referenced separately.

If something is used without correct attribution, please open an issue.

| Component | Author | License | How it is used |
|---|---|---|---|
| [Qwen 2.5 Coder 7B Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) | Alibaba Cloud / Qwen team | Apache-2.0 | Base weights. Delivered separately in the model bundle as `base.gguf`, not in this repository or the Python package. |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | ggml-org and contributors | MIT | Provides the `llama-server` binary the scanner drives. Installed by the user, never bundled. |
| [pydantic](https://github.com/pydantic/pydantic) | Samuel Colvin and contributors | MIT | Declared Python dependency, installed from PyPI. |
| [huggingface_hub](https://github.com/huggingface/huggingface_hub) | Hugging Face and contributors | Apache-2.0 | Provides the `hf` command used to download the model bundle. |
| [jekyll-theme-cayman](https://github.com/pages-themes/cayman) | Jason Long | CC0-1.0 | Theme for the documentation site, resolved by GitHub Pages at build time. |

The per-regulation LoRA detector adapters in the model bundle are built on the
Qwen weights above and are released under the Apache License 2.0. The bundle
carries its own copy of the license and this attribution.

## EU legal source material

The regulation packs reference EU legislation published on EUR-Lex. Article
identifiers and titles come from the official texts; the summaries and
detection material are the project's own work and are not the legal text.

Source: [EUR-Lex](https://eur-lex.europa.eu), (c) European Union, 1998-2026.
Reuse is authorised under Commission Decision 2011/833/EU subject to
acknowledgement of the source. This notice, the CELEX identifiers in each pack
and the EUR-Lex links emitted in reports serve as that acknowledgement. The
authoritative text of any regulation is the one published on EUR-Lex.

## Disclaimer

precommitEU is provided as is, without warranty or condition of any kind, as
set out in sections 7 and 8 of the Apache License 2.0. It produces a
compliance signal, not legal advice, and does not replace legal analysis. The
author is not a lawyer and accepts no liability for any outcome arising from
its use. See [LICENSE](LICENSE) and the disclaimer in [README.md](README.md).
