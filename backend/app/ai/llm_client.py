"""
Unified LLM client for OpenAI and Anthropic APIs.
"""

import json
import os
from typing import List, Dict, Any, Optional, Union
from abc import ABC, abstractmethod

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from ..core.config import settings


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from messages."""
        pass

    @abstractmethod
    async def generate_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Dict[str, Any],
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """Generate structured output matching schema."""
        pass


class OpenAIClient(LLMClient):
    """OpenAI client implementation."""

    def __init__(self, api_key: Optional[str] = None):
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package not installed")

        self.client = openai.AsyncOpenAI(
            api_key=api_key or settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        )
        self.model = "gpt-4o"  # Use latest GPT-4 model

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from messages."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")

    async def generate_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Dict[str, Any],
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """Generate structured output matching schema."""
        # Add schema instruction to messages
        schema_prompt = f"""
        Please respond with valid JSON that matches this exact schema:
        {json.dumps(schema, indent=2)}

        Ensure all required fields are present and data types are correct.
        """

        structured_messages = messages + [
            {"role": "system", "content": schema_prompt}
        ]

        response_text = await self.generate(
            structured_messages,
            temperature=temperature,
            max_tokens=3000
        )

        try:
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                return json.loads(json_text)
            else:
                # Fallback: try to parse entire response
                return json.loads(response_text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse structured response: {e}\nResponse: {response_text}")


class AnthropicClient(LLMClient):
    """Anthropic client implementation."""

    def __init__(self, api_key: Optional[str] = None):
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic package not installed")

        self.client = anthropic.AsyncAnthropic(
            api_key=api_key or settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        )
        self.model = "claude-3-5-sonnet-20241022"  # Use latest Claude model

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate text from messages."""
        try:
            # Separate system message if present
            system_message = None
            chat_messages = []

            for msg in messages:
                if msg["role"] == "system":
                    system_message = msg["content"]
                else:
                    chat_messages.append(msg)

            response = await self.client.messages.create(
                model=self.model,
                system=system_message,
                messages=chat_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {e}")

    async def generate_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Dict[str, Any],
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """Generate structured output matching schema."""
        # Add schema instruction to messages
        schema_prompt = f"""
        You must respond with valid JSON that matches this exact schema:
        {json.dumps(schema, indent=2)}

        Requirements:
        - Response must be valid JSON only
        - Include all required fields
        - Use correct data types
        - No additional text outside JSON
        """

        structured_messages = [
            {"role": "system", "content": schema_prompt}
        ] + messages

        response_text = await self.generate(
            structured_messages,
            temperature=temperature,
            max_tokens=3000
        )

        try:
            # Claude usually returns clean JSON
            return json.loads(response_text.strip())
        except json.JSONDecodeError as e:
            # Try to extract JSON
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                return json.loads(json_text)
            else:
                raise ValueError(f"Failed to parse structured response: {e}\nResponse: {response_text}")


class MockLLMClient(LLMClient):
    """Mock LLM client for testing without API keys."""

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """Generate mock text response."""
        # Extract key context from messages
        user_content = ""
        for msg in messages:
            if msg["role"] == "user":
                user_content += msg["content"] + " "

        # Generate contextual mock responses
        if "compare" in user_content.lower():
            return """
            Based on the analysis of the selected papers, here are the key insights:

            **Common Themes:**
            - Advanced neural architectures for improved performance
            - Focus on efficiency and scalability
            - Novel attention mechanisms and transformer variants

            **Key Differences:**
            - Different application domains (vision, NLP, multimodal)
            - Varying approaches to optimization and compression
            - Distinct evaluation methodologies

            **Complementary Aspects:**
            - Architectural innovations can be combined across domains
            - Optimization techniques are broadly applicable
            - Evaluation frameworks provide comprehensive assessment
            """
        elif "question" in user_content.lower():
            return """
            Based on the paper analysis, here are promising research directions:

            1. **What are the scalability limitations of current approaches?**
               - Rationale: Existing methods show promise but face computational constraints
               - Difficulty: Medium
               - Impact: High potential for practical deployment

            2. **How can these techniques be adapted for edge computing?**
               - Rationale: Growing need for efficient on-device inference
               - Difficulty: High
               - Impact: Significant for mobile applications

            3. **What novel evaluation metrics could better capture performance?**
               - Rationale: Current metrics may not reflect real-world performance
               - Difficulty: Low to Medium
               - Impact: Improved benchmarking standards
            """
        else:
            return "This is a mock response for research analysis. The analysis covers key insights, methodological approaches, and research opportunities based on the provided papers and context."

    async def generate_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Dict[str, Any],
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """Generate mock structured response."""
        # Check schema for comparison response
        if "comparison" in str(schema).lower():
            return {
                "comparison": [
                    {
                        "arxiv_id": "example-001",
                        "title": "Example Paper 1",
                        "authors": ["Author A", "Author B"],
                        "strengths": ["Novel approach", "Strong empirical results"],
                        "limitations": ["Limited evaluation", "Computational complexity"],
                        "novelty_aspects": ["New architecture design", "Improved optimization"],
                        "relevance_to_user": "Highly relevant for the research direction",
                        "priority": "high"
                    }
                ],
                "common_themes": ["Efficiency improvements", "Novel architectures"],
                "key_differences": ["Application domains", "Evaluation methodologies"],
                "complementary_aspects": ["Can be combined for better performance"],
                "conflicting_findings": [],
                "comparison_matrix": {},
                "focus_aspects": ["method", "results"]
            }
        # Check schema for questions response
        elif "questions" in str(schema).lower():
            return {
                "questions": [
                    {
                        "question": "How can current methods be improved for better scalability?",
                        "type": "gap",
                        "confidence": 0.8,
                        "novelty_score": 0.7,
                        "difficulty": "medium",
                        "evidence": "Based on analysis of computational limitations",
                        "related_papers": ["Paper 1", "Paper 2"],
                        "suggested_approaches": ["Distributed computing", "Model compression"],
                        "potential_impact": "High impact on practical deployment"
                    }
                ],
                "most_promising_direction": "Scalable and efficient implementations",
                "research_landscape_summary": "Active field with multiple promising approaches",
                "knowledge_gaps_identified": ["Scalability analysis", "Real-world evaluation"]
            }
        else:
            return {"result": "Mock structured response", "status": "success"}


def get_llm_client(provider: str = "openai") -> LLMClient:
    """Get LLM client instance."""
    if provider == "openai":
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI package not available")
        return OpenAIClient()
    elif provider == "anthropic":
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Anthropic package not available")
        return AnthropicClient()
    elif provider == "mock":
        return MockLLMClient()
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def get_available_providers() -> List[str]:
    """Get list of available LLM providers."""
    providers = []
    if OPENAI_AVAILABLE and (settings.openai_api_key or os.getenv("OPENAI_API_KEY")):
        providers.append("openai")
    if ANTHROPIC_AVAILABLE and (settings.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")):
        providers.append("anthropic")

    # Always include mock as fallback
    providers.append("mock")
    return providers


async def get_default_client() -> LLMClient:
    """Get default LLM client based on available providers."""
    providers = get_available_providers()

    if not providers:
        raise RuntimeError("No LLM providers available. Please set API keys.")

    # Prefer real providers over mock
    if "anthropic" in providers and "anthropic" != "mock":
        return get_llm_client("anthropic")
    elif "openai" in providers and "openai" != "mock":
        return get_llm_client("openai")
    else:
        # Fallback to mock
        return get_llm_client("mock")