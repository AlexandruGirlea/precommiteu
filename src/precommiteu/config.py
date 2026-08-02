from __future__ import annotations

MODELS_DIR_ENV = "PRECOMMITEU_MODELS_DIR"

CHARS_PER_TOKEN = 3.7
CHUNK_TARGET_MIN_TOKENS = 3500
CHUNK_TARGET_MAX_TOKENS = 6000

# Hard ceiling for any single SLM user message (enriched code view plus
# candidate findings). Matches the model's supported input window:
# enrichment may grow the code view, never past this.
USER_MESSAGE_TOKEN_BUDGET = 8000
CANDIDATE_FINDINGS_TOKEN_BUDGET = 500

MODEL_TEMPERATURE = 0.0
MODEL_MAX_TOKENS = 8192
MODEL_REQUEST_TIMEOUT_S = 600.0
MODEL_REQUEST_RETRIES = 2

SERVER_HEALTH_TIMEOUT_S = 90.0
SERVER_HEALTH_POLL_INTERVAL_S = 0.5
SERVER_TERMINATE_GRACE_S = 5.0
SERVER_PORT_RETRY_LIMIT = 5

DEFAULT_MAX_ITERATIONS = 12
DEFAULT_WALL_SECONDS_PER_FILE = 90.0
ENRICHMENT_DEPTH_CAP = 1
MAX_SIBLING_STEMS = 200

BM25_K1 = 1.5
BM25_B = 0.75
RETRIEVAL_TOP_K = 12
RETRIEVAL_DESCRIPTION_WEIGHT = 0.5

# Promotion gate - calibrated offline against labeled evaluation data.
# Values above 1.0 disable promotion (annotation-only mode).
PROMOTE_CONFIDENCE = 0.85
PROMOTE_SIMILARITY = 0.10
