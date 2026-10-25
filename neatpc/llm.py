"""Unified LLM Provider for NeatPC.

Seamlessly bridges Google Gemini Cloud API and Local Ollama (e.g. LLaMA 3.2, Mistral)
to provide private, on-device or cloud-powered document intelligence.
"""

import os
import json
from typing import Optional, Dict, Any, List
import httpx

from .config import (
    USER_CONFIG,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OLLAMA_ENDPOINT,
    DEFAULT_OLLAMA_MODEL
)


class UnifiedLLMClient:
    """Unified client supporting both Google Gemini and Local Ollama."""

    def __init__(
        self,
        provider: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        ollama_endpoint: Optional[str] = None,
        ollama_model: Optional[str] = None
    ):
        config_provider = USER_CONFIG.get("ai_provider", "auto")
        self.provider = (provider or config_provider).lower()

        # Gemini settings
        self.gemini_key = (
            gemini_api_key
            or USER_CONFIG.get("gemini", {}).get("api_key")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        self.gemini_model = USER_CONFIG.get("gemini", {}).get("model", DEFAULT_GEMINI_MODEL)
        self.gemini_client = None

        # Ollama settings
        self.ollama_endpoint = (
            ollama_endpoint
            or USER_CONFIG.get("ollama", {}).get("endpoint", DEFAULT_OLLAMA_ENDPOINT)
        ).rstrip("/")
        self.ollama_model = (
            ollama_model
            or USER_CONFIG.get("ollama", {}).get("model", DEFAULT_OLLAMA_MODEL)
        )

        self.active_provider = self._resolve_active_provider()

    def _resolve_active_provider(self) -> str:
        """Determines whether to use Gemini, Ollama, or None."""
        if self.provider == "none":
            return "none"

        if self.provider == "gemini":
            if self._init_gemini():
                return "gemini"
            return "none"

        if self.provider == "ollama":
            if self._check_ollama():
                return "ollama"
            return "none"

        # Auto detection mode
        if self.gemini_key and self._init_gemini():
            return "gemini"

        if self._check_ollama():
            return "ollama"

        return "none"

    def _init_gemini(self) -> bool:
        """Initializes Google GenAI client."""
        if not self.gemini_key:
            return False
        try:
            from google import genai
            self.genai_client = genai.Client(api_key=self.gemini_key)
            return True
        except Exception:
            return False

    def _check_ollama(self) -> bool:
        """Checks if local Ollama server is running."""
        try:
            resp = httpx.get(f"{self.ollama_endpoint}/api/tags", timeout=1.5)
            return resp.status_code == 200
        except Exception:
            return False

    @property
    def is_available(self) -> bool:
        """Whether an AI provider is actively available."""
        return self.active_provider in ["gemini", "ollama"]

    def generate_json(self, prompt: str) -> Optional[Any]:
        """Queries the active AI provider and returns parsed JSON result."""
        if self.active_provider == "gemini" and self.genai_client:
            return self._query_gemini(prompt)
        elif self.active_provider == "ollama":
            return self._query_ollama(prompt)
        return None

    def _query_gemini(self, prompt: str) -> Optional[Any]:
        """Queries Google Gemini API with JSON enforcement."""
        from google.genai import types
        try:
            response = self.genai_client.models.generate_content(
                model=self.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            raw = response.text or "[]"
            return json.loads(raw)
        except Exception:
            return None

    def _query_ollama(self, prompt: str) -> Optional[Any]:
        """Queries local Ollama endpoint with JSON format."""
        try:
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": 0.1
                }
            }
            resp = httpx.post(
                f"{self.ollama_endpoint}/api/generate",
                json=payload,
                timeout=45.0
            )
            if resp.status_code == 200:
                result = resp.json()
                raw_response = result.get("response", "[]")
                return json.loads(raw_response)
        except Exception:
            pass
        return None
