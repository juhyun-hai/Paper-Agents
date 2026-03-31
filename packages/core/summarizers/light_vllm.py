"""
Light summarization using vLLM via OpenAI-compatible API.

Connects to a running vLLM server and generates structured summaries
matching the CLAUDE.md schema.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger(__name__)


def get_vllm_config() -> tuple[str, str]:
    """
    Get vLLM configuration from environment.

    Returns:
        Tuple of (base_url, model_name)

    Raises:
        ValueError: If required config is missing
    """
    base_url = os.getenv("VLLM_BASE_URL")
    model = os.getenv("VLLM_MODEL")

    if not base_url:
        raise ValueError(
            "VLLM_BASE_URL not set. Please set it in .env file. "
            "Example: VLLM_BASE_URL=http://localhost:8000/v1"
        )

    if not model:
        raise ValueError(
            "VLLM_MODEL not set. Please set it in .env file. "
            "Example: VLLM_MODEL=meta-llama/Llama-3.1-8B-Instruct"
        )

    return base_url, model


def summarize_light_vllm(
    title: str, abstract: str, categories: List[str]
) -> Dict[str, Any]:
    """
    Generate a light summary using vLLM.

    Args:
        title: Paper title
        abstract: Paper abstract
        categories: List of arXiv categories

    Returns:
        Summary dictionary matching CLAUDE.md schema

    Raises:
        RuntimeError: If vLLM API call fails or JSON parsing fails after retry
    """
    base_url, model = get_vllm_config()

    # Build prompt
    prompt = _build_prompt(title, abstract, categories)

    # First attempt
    try:
        response_text = _call_vllm_api(base_url, model, prompt)
        summary = _parse_json_response(response_text)
        logger.debug(f"Successfully generated summary for: {title[:50]}...")
        return summary

    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse failed on first attempt: {e}. Retrying with fix prompt...")

        # Retry with fix prompt
        try:
            fix_prompt = _build_fix_prompt(response_text)
            fixed_response = _call_vllm_api(base_url, model, fix_prompt)
            summary = _parse_json_response(fixed_response)
            logger.info("Successfully fixed JSON on retry")
            return summary

        except json.JSONDecodeError as e2:
            logger.error(f"JSON parse failed after retry: {e2}")
            logger.error(f"Original response: {response_text[:500]}")
            logger.error(f"Fixed response: {fixed_response[:500]}")
            raise RuntimeError(
                f"Failed to parse JSON response after retry: {e2}"
            ) from e2


def _build_prompt(title: str, abstract: str, categories: List[str]) -> str:
    """
    Build the summarization prompt.

    The prompt must force strict JSON output with no fabricated numbers.
    """
    categories_str = ", ".join(categories)

    prompt = f"""You are a scientific paper summarization system. Generate a structured summary for the following paper.

**CRITICAL RULES:**
1. Output ONLY valid JSON matching the exact schema below. No extra text before or after.
2. NEVER fabricate experimental numbers, metrics, or results.
3. If information is not explicitly stated in the abstract, use "unknown" or empty arrays.
4. Base your summary ONLY on the title and abstract provided.

**Paper Information:**
Title: {title}
Abstract: {abstract}
Categories: {categories_str}

**Required JSON Schema:**
{{
  "one_liner": "Brief one-sentence summary of the paper",
  "problem": "What problem does this paper address?",
  "method": "What method or approach is proposed?",
  "model_info": {{
    "backbone": "Model architecture if mentioned, else unknown",
    "foundation_model": "Base model if mentioned, else unknown",
    "parameters": "Model size if mentioned, else unknown",
    "training_objective": "Training objective if mentioned, else unknown"
  }},
  "datasets": [
    {{"name": "Dataset name", "task": "Task type"}}
  ],
  "metrics": ["metric1", "metric2"],
  "results": [
    {{"metric": "metric name", "value": "exact value from abstract", "setting": "evaluation setting"}}
  ],
  "compute": {{
    "gpus": "GPU info if mentioned, else unknown",
    "steps": "Training steps if mentioned, else unknown",
    "batch_size": "Batch size if mentioned, else unknown",
    "training_time": "Training time if mentioned, else unknown"
  }},
  "limitations": "Limitations mentioned in abstract, else unknown",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "relevance_tags": {json.dumps(categories)}
}}

Generate the JSON summary now. Output ONLY the JSON object, nothing else:"""

    return prompt


def _build_fix_prompt(broken_json: str) -> str:
    """
    Build a prompt to fix broken JSON.

    Args:
        broken_json: The malformed JSON response

    Returns:
        Fix prompt string
    """
    prompt = f"""The following JSON is malformed. Fix it and return ONLY valid JSON with no extra text.

If there is any text before or after the JSON object, remove it.
Ensure all strings are properly quoted and all brackets are balanced.

Malformed JSON:
{broken_json}

Fixed JSON (output ONLY the JSON object):"""

    return prompt


def _call_vllm_api(
    base_url: str,
    model: str,
    prompt: str,
    temperature: float = 0.0,
    max_tokens: int = 700,
    timeout: tuple = (5, 300),
) -> str:
    """
    Call vLLM API using OpenAI-compatible format.

    Args:
        base_url: vLLM base URL (e.g., http://localhost:8000/v1)
        model: Model name
        prompt: Input prompt
        temperature: Sampling temperature (0 = deterministic)
        max_tokens: Maximum tokens to generate
        timeout: Tuple of (connect_timeout, read_timeout) in seconds.
                 Default: (5, 300) = 5s connect, 5min generation

    Returns:
        Generated text response

    Raises:
        RuntimeError: If API call fails
    """
    endpoint = f"{base_url.rstrip('/')}/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    headers = {
        "Content-Type": "application/json",
    }

    try:
        logger.debug(f"Calling vLLM API: {endpoint}")
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()

        response_json = response.json()

        # Extract text from OpenAI-compatible response
        if "choices" not in response_json or len(response_json["choices"]) == 0:
            raise RuntimeError(f"Invalid response format: {response_json}")

        content = response_json["choices"][0]["message"]["content"]
        return content

    except requests.exceptions.Timeout:
        timeout_msg = f"connect={timeout[0]}s, read={timeout[1]}s" if isinstance(timeout, tuple) else f"{timeout}s"
        raise RuntimeError(f"vLLM API timeout ({timeout_msg})")

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"vLLM API request failed: {e}") from e

    except KeyError as e:
        raise RuntimeError(f"Unexpected response format: {e}") from e


def _parse_json_response(response_text: str) -> Dict[str, Any]:
    """
    Parse JSON from response text.

    Attempts to extract JSON even if there's extra text around it.

    Args:
        response_text: Raw response text

    Returns:
        Parsed JSON dictionary

    Raises:
        json.JSONDecodeError: If parsing fails
    """
    # Try direct parse first
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from text (find first { to last })
    start = response_text.find("{")
    end = response_text.rfind("}") + 1

    if start == -1 or end == 0:
        raise json.JSONDecodeError(
            "No JSON object found in response",
            response_text,
            0
        )

    json_str = response_text[start:end]
    return json.loads(json_str)


def get_token_count_estimate(response_text: str) -> int:
    """
    Estimate token count from response.

    Simple heuristic: ~4 characters per token.

    Args:
        response_text: Generated text

    Returns:
        Estimated token count
    """
    return len(response_text) // 4
