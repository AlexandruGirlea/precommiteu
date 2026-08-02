from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from precommiteu.config import (
    MODEL_MAX_TOKENS,
    MODEL_REQUEST_RETRIES,
    MODEL_REQUEST_TIMEOUT_S,
    MODEL_TEMPERATURE,
)
from precommiteu.llama_server import LOOPBACK_OPENER, ServerHandle

_RETRYABLE_STATUS = frozenset({408, 409, 429, 500, 502, 503, 504})


class ModelResponseTruncated(RuntimeError):
    pass


@dataclass(frozen=True)
class ChatResponse:
    content: str


class LocalChatModel:
    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
        grammar: str | None,
        timeout_s: float,
        retries: int,
    ) -> None:
        self._endpoint = endpoint
        self._api_key = api_key
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._grammar = grammar
        self._timeout_s = timeout_s
        self._retries = retries

    def invoke(
        self, messages: list[Any], timeout_s: float | None = None
    ) -> ChatResponse:
        body: dict[str, Any] = {
            "model": "precommiteu-local",
            "messages": [_as_message_dict(m) for m in messages],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        if self._grammar:
            body["grammar"] = self._grammar
        request = urllib.request.Request(
            self._endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
        )
        # timeout_s is the caller's remaining wall budget; retries included.
        deadline = (
            None
            if timeout_s is None
            else time.monotonic() + max(1.0, timeout_s)
        )
        last_error: Exception | None = None
        for attempt in range(self._retries + 1):
            per_attempt = self._timeout_s
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                per_attempt = min(self._timeout_s, remaining)
            try:
                with LOOPBACK_OPENER.open(
                    request, timeout=per_attempt
                ) as resp:
                    payload = json.loads(
                        resp.read().decode("utf-8", errors="replace")
                    )
                choice = payload["choices"][0]
                content = choice["message"]["content"] or ""
                if choice.get("finish_reason") == "length":
                    raise ModelResponseTruncated(
                        "model output hit the token limit before completing; "
                        "treating this chunk as not analyzed"
                    )
                return ChatResponse(content=content)
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in _RETRYABLE_STATUS:
                    raise
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = exc
            if attempt < self._retries:
                time.sleep(min(0.5 * 2**attempt, 8.0))
        raise RuntimeError(
            f"model request failed after {self._retries + 1} attempts"
        ) from last_error


def _as_message_dict(message: Any) -> dict[str, str]:
    if isinstance(message, dict):
        return message
    if isinstance(message, ChatResponse):
        return {"role": "assistant", "content": message.content}
    return {"role": "user", "content": str(message)}


def build_chat_model(
    handle: ServerHandle,
    *,
    temperature: float = MODEL_TEMPERATURE,
    max_tokens: int = MODEL_MAX_TOKENS,
    grammar: str | None = None,
    request_timeout: float = MODEL_REQUEST_TIMEOUT_S,
) -> LocalChatModel:
    return LocalChatModel(
        endpoint=f"{handle.url}/chat/completions",
        api_key=handle.api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        grammar=grammar,
        timeout_s=request_timeout,
        retries=MODEL_REQUEST_RETRIES,
    )
