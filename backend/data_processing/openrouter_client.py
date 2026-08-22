from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

API_BASE = "https://openrouter.ai/api/v1"
DEFAULT_EMBEDDING_MODEL = "openai/text-embedding-3-small"
DEFAULT_LLM_MODEL = "google/gemma-4-31b-it:free"
DEFAULT_LLM_FALLBACK_MODELS = (
    "google/gemma-4-26b-a4b-it:free",
    "z-ai/glm-5.2:free",
    "cohere/north-mini-code:free",
    "nvidia/nemotron-3.5-lightning:free",
    "openrouter/free",
)
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

_DOTENV_LOADED = False


@dataclass(slots=True)
class OpenRouterError(RuntimeError):
    status_code: int | None
    payload: dict[str, Any] | None


def _load_dotenv() -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return

    if ENV_PATH.exists():
        for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)

    _DOTENV_LOADED = True


def get_env(name: str, default: str | None = None) -> str | None:
    _load_dotenv()
    return os.getenv(name, default)


def get_openrouter_api_key() -> str:
    api_key = get_env("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. Set it in the environment or in .env."
        )
    return api_key


def _request_json(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    url = f"{API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {get_openrouter_api_key()}",
        "Content-Type": "application/json",
    }
    request = urllib.request.Request(
        url=url,
        method=method,
        headers=headers,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body) if body else None
        except json.JSONDecodeError:
            payload = {"error": {"message": body or exc.reason}}
        raise OpenRouterError(exc.code, payload) from exc


def _stream_jsonl(path: str, payload: dict[str, Any]) -> Iterator[dict[str, Any]]:
    url = f"{API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {get_openrouter_api_key()}",
        "Content-Type": "application/json",
    }
    request = urllib.request.Request(
        url=url,
        method="POST",
        headers=headers,
        data=json.dumps(payload).encode("utf-8"),
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data:"):
                    continue
                data = line.removeprefix("data:").strip()
                if data == "[DONE]":
                    break
                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    continue
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            error_payload = json.loads(body) if body else None
        except json.JSONDecodeError:
            error_payload = {"error": {"message": body or exc.reason}}
        raise OpenRouterError(exc.code, error_payload) from exc


def _batched(values: Sequence[str], batch_size: int) -> Iterable[list[str]]:
    for start in range(0, len(values), batch_size):
        yield list(values[start : start + batch_size])


def embed_texts(
    texts: Sequence[str],
    *,
    model: str = DEFAULT_EMBEDDING_MODEL,
    dimensions: int | None = None,
    batch_size: int = 32,
) -> list[list[float]]:
    """Return one embedding per text using OpenRouter's embeddings endpoint."""

    items = list(texts)
    if not items:
        return []

    embeddings: list[list[float]] = []
    for batch in _batched(items, batch_size):
        payload: dict[str, Any] = {"model": model, "input": batch if len(batch) > 1 else batch[0]}
        if dimensions is not None:
            payload["dimensions"] = dimensions

        try:
            response = _request_json("POST", "/embeddings", payload)
            batch_embeddings = [item["embedding"] for item in response.get("data", [])]
            if len(batch_embeddings) != len(batch):
                raise RuntimeError(
                    f"Expected {len(batch)} embeddings, got {len(batch_embeddings)}."
                )
            embeddings.extend(batch_embeddings)
        except OpenRouterError:
            if len(batch) == 1:
                raise
            for text in batch:
                single = embed_texts([text], model=model, dimensions=dimensions, batch_size=1)
                embeddings.extend(single)

    return embeddings


def chat_completion(
    messages: Sequence[dict[str, Any]],
    *,
    model: str = DEFAULT_LLM_MODEL,
    fallback_models: Sequence[str] = DEFAULT_LLM_FALLBACK_MODELS,
    temperature: float = 0.2,
    max_tokens: int = 700,
) -> str:
    errors: list[BaseException] = []
    models = [model, *fallback_models]
    for selected_model in dict.fromkeys(models):
        payload = {
            "model": selected_model,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            response = _request_json("POST", "/chat/completions", payload)
            choices = response.get("choices") or []
            if not choices:
                raise RuntimeError(f"OpenRouter returned no choices for {selected_model}.")
            message = choices[0].get("message") or {}
            content = message.get("content")
            if not content:
                raise RuntimeError(f"OpenRouter returned an empty chat message for {selected_model}.")
            return str(content)
        except (OpenRouterError, RuntimeError) as exc:
            errors.append(exc)

    if errors:
        raise errors[-1]
    raise RuntimeError("No OpenRouter chat models configured.")


def chat_completion_stream(
    messages: Sequence[dict[str, Any]],
    *,
    model: str = DEFAULT_LLM_MODEL,
    fallback_models: Sequence[str] = DEFAULT_LLM_FALLBACK_MODELS,
    temperature: float = 0.2,
    max_tokens: int = 700,
) -> Iterator[str]:
    errors: list[BaseException] = []
    models = [model, *fallback_models]
    for selected_model in dict.fromkeys(models):
        payload = {
            "model": selected_model,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        try:
            had_content = False
            for event in _stream_jsonl("/chat/completions", payload):
                choices = event.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                content = delta.get("content")
                if content:
                    had_content = True
                    yield str(content)
            if had_content:
                return
            raise RuntimeError(f"OpenRouter streamed no content for {selected_model}.")
        except (OpenRouterError, RuntimeError) as exc:
            errors.append(exc)

    if errors:
        raise errors[-1]
    raise RuntimeError("No OpenRouter chat models configured.")
