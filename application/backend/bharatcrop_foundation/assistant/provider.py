from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Protocol

import httpx


class ProviderError(Exception):
    """Base exception for LLM provider errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ProviderUnavailableError(ProviderError):
    """Raised when the LLM provider is unconfigured or unreachable."""


class ProviderTimeoutError(ProviderError):
    """Raised when the LLM request times out."""


class ProviderRateLimitError(ProviderError):
    """Raised when the LLM provider returns HTTP 429."""


class ProviderMalformedError(ProviderError):
    """Raised when the LLM provider returns an unparseable response."""


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    finish_reason: str | None = None
    raw_response: dict[str, Any] | None = None


class LLMProvider(Protocol):
    def is_available(self) -> bool: ...

    def provider_name(self) -> str: ...

    def model_name(self) -> str | None: ...

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> LLMResponse: ...


class NullLLMProvider:
    """Default provider when no LLM credentials are configured."""

    def is_available(self) -> bool:
        return False

    def provider_name(self) -> str:
        return "none"

    def model_name(self) -> str | None:
        return None

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        raise ProviderUnavailableError(
            "LLM provider credentials are not configured. AI assistant generation is disabled."
        )


class MockLLMProvider:
    """Deterministic, configurable fake provider for automated tests and local development."""

    def __init__(
        self,
        *,
        model: str = "mock-agricultural-model",
        custom_response: str | None = None,
        simulate_timeout: bool = False,
        simulate_rate_limit: bool = False,
        simulate_malformed: bool = False,
        simulate_unavailable: bool = False,
        delay_seconds: float = 0.0,
    ) -> None:
        self.model = model
        self.custom_response = custom_response
        self.simulate_timeout = simulate_timeout
        self.simulate_rate_limit = simulate_rate_limit
        self.simulate_malformed = simulate_malformed
        self.simulate_unavailable = simulate_unavailable
        self.delay_seconds = delay_seconds
        self.call_history: list[list[LLMMessage]] = []

    def is_available(self) -> bool:
        return not self.simulate_unavailable

    def provider_name(self) -> str:
        return "mock"

    def model_name(self) -> str:
        return self.model

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.1,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        self.call_history.append(messages)

        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        if self.simulate_unavailable:
            raise ProviderUnavailableError("Simulated LLM provider outage.")

        if self.simulate_timeout:
            raise ProviderTimeoutError("Simulated LLM request timeout.")

        if self.simulate_rate_limit:
            raise ProviderRateLimitError("Simulated LLM provider rate limit exceeded (429).", 429)

        if self.simulate_malformed:
            raise ProviderMalformedError("Simulated malformed LLM response payload.")

        if self.custom_response is not None:
            return LLMResponse(
                content=self.custom_response,
                model=self.model,
                prompt_tokens=50,
                completion_tokens=len(self.custom_response.split()),
                finish_reason="stop",
            )

        # Generate a default grounded response matching the user's language and content
        last_message = messages[-1].content if messages else ""
        system_prompt = messages[0].content if messages else ""

        is_hindi = any("\u0900" <= c <= "\u097f" for c in last_message + system_prompt)

        # Extract evidence text from prompt if present
        evidence_snippet = ""
        if "<evidence>" in last_message and "</evidence>" in last_message:
            start = last_message.find("<evidence>") + len("<evidence>")
            end = last_message.find("</evidence>")
            evidence_snippet = last_message[start:end].strip()

        if is_hindi:
            content = (
                f"भारतक्रॉप इंटेलिजेंस के उपलब्ध रिकॉर्ड के अनुसार, प्राप्त प्रमाण इस प्रकार हैं: "
                f"{evidence_snippet if evidence_snippet else 'विश्लेषण सफल रहा।'}"
            )
        else:
            content = (
                f"Based on BharatCrop Intelligence verified backend evidence: "
                f"{evidence_snippet if evidence_snippet else 'The query was processed successfully.'}"
            )

        return LLMResponse(
            content=content,
            model=self.model,
            prompt_tokens=len(last_message.split()),
            completion_tokens=len(content.split()),
            finish_reason="stop",
        )


class OpenAICompatibleProvider:
    """HTTP client for OpenAI-compatible REST APIs (OpenAI, Gemini, Azure, local vLLM/Ollama)."""

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 30.0,
        max_tokens: int = 1024,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_tokens = max_tokens

    def is_available(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def provider_name(self) -> str:
        return "openai_compatible"

    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.1,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        if not self.is_available():
            raise ProviderUnavailableError("API key is not configured for LLM provider.")

        url = f"{self._base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": max(0.0, min(1.0, temperature)),
            "max_tokens": max_tokens or self._max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)

            if response.status_code == 429:
                raise ProviderRateLimitError(
                    "LLM provider rate limit exceeded (429).",
                    status_code=429,
                )

            if response.status_code >= 500:
                raise ProviderUnavailableError(
                    f"LLM provider service temporarily unavailable (status {response.status_code}).",
                    status_code=response.status_code,
                )

            if response.status_code != 200:
                raise ProviderError(
                    f"LLM provider returned unexpected status {response.status_code}.",
                    status_code=response.status_code,
                )

            data = response.json()
            choices = data.get("choices")
            if not choices or not isinstance(choices, list):
                raise ProviderMalformedError("Response choices missing from provider payload.")

            choice = choices[0]
            message_obj = choice.get("message") or {}
            content = message_obj.get("content")
            if content is None:
                raise ProviderMalformedError("Response message content missing from provider payload.")

            usage = data.get("usage") or {}
            return LLMResponse(
                content=str(content),
                model=data.get("model", self._model),
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                finish_reason=choice.get("finish_reason"),
                raw_response=data,
            )

        except httpx.TimeoutException as err:
            raise ProviderTimeoutError(
                f"LLM request timed out after {self._timeout_seconds} seconds."
            ) from err
        except (httpx.RequestError, OSError) as err:
            raise ProviderUnavailableError(
                "Failed to reach LLM provider service."
            ) from err
        except (ValueError, KeyError) as err:
            raise ProviderMalformedError(
                f"Could not parse LLM provider response: {err}"
            ) from err


def create_llm_provider(
    provider_name: str,
    api_key: str | None = None,
    model: str = "gpt-4o-mini",
    base_url: str | None = None,
    timeout_seconds: float = 30.0,
    max_tokens: int = 1024,
) -> LLMProvider:
    """Factory creating an LLMProvider instance based on configuration."""
    name = (provider_name or "none").strip().casefold()

    if name in {"none", ""}:
        return NullLLMProvider()

    if name == "mock":
        return MockLLMProvider(model=model)

    if name in {"openai", "openai_compatible", "generic"}:
        if not api_key:
            return NullLLMProvider()
        return OpenAICompatibleProvider(
            api_key=api_key,
            model=model,
            base_url=base_url or "https://api.openai.com/v1",
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
        )

    # Unknown provider defaults to NullLLMProvider
    return NullLLMProvider()
