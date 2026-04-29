"""
ollama_async_client.py
======================
Unified LLM Client for Google Gemini and Local Ollama.
Supports async calls for high-throughput simulations.
"""

import os
import time
import asyncio
import json
import aiohttp
from typing import Optional, Dict, List, Any
from google import genai
from google.genai import types

# --- PROVIDER CONFIG ---
# Default to Google Gemini (Unlimited RPM on Flash 2.0 / 3.0)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL   = "models/gemini-2.0-flash" # Updated to standard model name

# Local Ollama fallback
OLLAMA_HOST  = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2:1b"

# --- RATE LIMITER ---
_RATE_LIMIT_PER_MIN = 30 # Increased for Gemini Flash
_MAX_RETRIES        = 3

class _RateLimiter:
    """Simple rate limiter to prevent API throttling."""
    def __init__(self, calls_per_min: int):
        self._interval   = 60.0 / calls_per_min
        self._async_lock = asyncio.Lock()
        self._last       = 0.0

    async def async_wait(self):
        async with self._async_lock:
            elapsed = time.monotonic() - self._last
            if elapsed < self._interval:
                await asyncio.sleep(self._interval - elapsed)
            self._last = time.monotonic()

_rate_limiter = _RateLimiter(_RATE_LIMIT_PER_MIN)

class UnifiedLLMClient:
    """Unified client for interacting with Google Gemini or Local Ollama."""
    
    def __init__(self, preferred_mode: str = "GEMINI"):
        self.mode = preferred_mode
        self.client = None
        
        if self.mode == "GEMINI" and GEMINI_API_KEY:
            try:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
                print(f"[LLM] Initialized Google Gemini ({GEMINI_MODEL})")
            except Exception as e:
                print(f"[LLM] Failed to initialize Gemini: {e}. Falling back to OLLAMA.")
                self.mode = "OLLAMA"
        
        if self.mode == "OLLAMA":
            print(f"[LLM] Initialized Local Ollama ({OLLAMA_MODEL})")

    def _strip_fences(self, text: str) -> str:
        """Removes markdown code fences from LLM response."""
        text = text.strip()
        if text.startswith("```json"): text = text[7:]
        elif text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
        return text.strip()

    async def call_async(self, prompt: str, max_tokens: int = 2000) -> Optional[Dict[str, Any]]:
        """Generic async call to the active LLM provider."""
        if self.mode == "GEMINI":
            return await self._call_gemini(prompt, max_tokens)
        else:
            return await self._call_ollama(prompt, max_tokens)

    async def _call_gemini(self, prompt: str, max_tokens: int) -> Optional[Dict[str, Any]]:
        """Specific async call for Google Gemini."""
        for attempt in range(_MAX_RETRIES + 1):
            try:
                await _rate_limiter.async_wait()
                resp = await self.client.aio.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        max_output_tokens=max_tokens,
                        temperature=0.7
                    )
                )
                return json.loads(self._strip_fences(resp.text))
            except Exception as e:
                print(f"       [GEMINI ERROR] Attempt {attempt+1}: {e}")
                if attempt < _MAX_RETRIES: await asyncio.sleep(2 ** attempt)
        return None

    async def _call_ollama(self, prompt: str, max_tokens: int) -> Optional[Dict[str, Any]]:
        """Specific async call for local Ollama."""
        url = f"{OLLAMA_HOST}/api/generate"
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        for attempt in range(_MAX_RETRIES + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, timeout=60) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            return json.loads(result.get("response", "{}"))
            except Exception as e:
                print(f"       [OLLAMA ERROR] Attempt {attempt+1}: {e}")
                if attempt < _MAX_RETRIES: await asyncio.sleep(1)
        return None

    async def call_batch_async(self, prompt: str, expected_count: int) -> Optional[List[Dict[str, Any]]]:
        """Batch call optimized for persona generation/voting."""
        results = await self.call_async(prompt, max_tokens=8192)
        
        if isinstance(results, dict) and "results" in results:
            results = results["results"]
            
        if isinstance(results, list) and len(results) == expected_count:
            return results
        
        if isinstance(results, list):
            return results
            
        return None

    def call(self, prompt: str, max_tokens: int = 2000) -> Optional[Dict[str, Any]]:
        """Sync wrapper for call_async."""
        try:
            return asyncio.run(self.call_async(prompt, max_tokens))
        except Exception as e:
            print(f"[LLM SYNC ERROR] {e}")
            return None

    def call_batch(self, prompt: str, expected_count: int) -> Optional[List[Dict[str, Any]]]:
        """Sync wrapper for call_batch_async."""
        try:
            return asyncio.run(self.call_batch_async(prompt, expected_count))
        except Exception as e:
            print(f"[LLM SYNC BATCH ERROR] {e}")
            return None

    def ping(self) -> bool:
        """Verify connectivity to the provider."""
        if self.mode == "GEMINI":
            return bool(self.client)
        return True

def get_llm_client(mode: str = "GEMINI"):
    """Factory function for the unified client."""
    return UnifiedLLMClient(mode)
