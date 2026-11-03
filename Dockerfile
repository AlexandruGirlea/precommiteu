FROM python:3.13-slim-trixie

LABEL org.opencontainers.image.source=https://github.com/AlexandruGirlea/precommiteu

ARG LLAMA_BUILD=b10158
ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && git config --system --add safe.directory '*'

RUN mkdir /opt/llama \
    && curl -fsSL "https://github.com/ggml-org/llama.cpp/releases/download/${LLAMA_BUILD}/llama-${LLAMA_BUILD}-bin-ubuntu-$([ "$TARGETARCH" = arm64 ] && echo arm64 || echo x64).tar.gz" \
    | tar -xz -C /opt/llama --strip-components=1

COPY . /tmp/precommiteu
RUN pip install --no-cache-dir /tmp/precommiteu "huggingface_hub[cli]" \
    && rm -rf /tmp/precommiteu

ENV PATH=/opt/llama:$PATH \
    PRECOMMITEU_MODELS_DIR=/models
