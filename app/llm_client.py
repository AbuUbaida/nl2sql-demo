from datetime import date
import json
import time
import anthropic
from dataclasses import dataclass

from app.config import settings
from app.prompt_builder import PROMPT_VERSION, build_prompt
from app.schema_reader import TableSchema


@dataclass
class LLMResponse:
    answerable: bool
    sql: str | None
    explanation: str
    assumptions: list[str]
    confidence: str
    refusal_reason: str | None
    raw_text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    model: str
    prompt_version: str

MODEL_PRICING = {
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
}

client = anthropic.Anthropic(
    api_key=settings.anthropic_api_key, 
    timeout=20.0, 
    max_retries=2)


class LLMError(Exception):
    """
    Base class for all failures in the LLM client.
    """
    pass


class LLMAPIError(LLMError):
    def __init__(message: str, status_code: int | None, attempts: int | None):
        super().__init__(message)
        status_code = status_code
        attempts = attempts


class LLMParseError(LLMError):
    def __init__(message: str, raw_text: str | None):
        super().__init__(message)
        raw_text = raw_text


class LLMTimeoutError(LLMError):
    def __init__(message: str, timeout_seconds: float | None, elapsed_ms: int | None):
        super().__init__(message)
        timeout_seconds = timeout_seconds
        elapsed_ms = elapsed_ms


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    in_rate, out_rate = MODEL_PRICING.get(model, (0.0, 0.0))
    cost = (input_tokens*in_rate + output_tokens*out_rate) / 1_000_000
    return cost


def extract_json_block(raw_text: str) -> str:
    idx_first = raw_text.find("{")
    idx_last = raw_text.rfind("}")

    if (idx_first == -1) or (idx_last == -1) or (idx_last < idx_first):
        raise LLMParseError(f"No JSON object found in model response: {raw_text[:500]}")

    return raw_text[idx_first : idx_last + 1]


def parse_response(raw_text: str) -> dict:
    json_block = extract_json_block(raw_text)
    try:
        response = json.loads(json_block)
    except Exception as exc:
        raise LLMParseError(f"Model returned invalid JSON: {exc}")

    answerable = response.get("answerable")
    if answerable not in (True, False):
        raise LLMParseError("Response is missing a valid 'answerable' field")
    if answerable == True:
        if response.get("sql") in (None, "None"):
            raise LLMParseError("Model said the question was answerable but returned no SQL")

    return {
        "answerable": answerable,
        "sql": response.get("sql"),
        "explanation": response.get("explanation", ""),
        "assumptions": response.get("assumptions", []),
        "confidence": response.get("confidence", "medium"),
        "refusal_reason": response.get("refusal_reason", None)
    }


def call_claude(system_prompt: str, user_prompt: str) -> tuple[str, int, int, int]:
    start_time = time.perf_counter()
    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        elapsed_ms = int((time.perf_counter() - start_time) * 1000)
        raw_text = next((block.text for block in response.content if block.type == "text"), "")
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
    except anthropic.APITimeoutError:
        raise LLMTimeoutError("Claude API timed out after 20 seconds")
    except anthropic.APIError as exc:
        raise LLMAPIError(f"Claude API call failed: {exc}")
    
    return (raw_text, input_tokens, output_tokens, elapsed_ms)


def generate_sql(question: str, schema: TableSchema, current_date: date | None = None) -> LLMResponse:
    system_prompt, user_prompt = build_prompt(question, schema, current_date)
    raw_text, in_tokens, out_tokens, latency_ms = call_claude(system_prompt, user_prompt)
    parsed = parse_response(raw_text)
    cost = calculate_cost(settings.claude_model, in_tokens, out_tokens)
    return LLMResponse(
        answerable=parsed["answerable"],
        sql=parsed["sql"],
        explanation=parsed["explanation"],
        assumptions=parsed["assumptions"],
        confidence=parsed["confidence"],
        refusal_reason=parsed["refusal_reason"],
        raw_text=raw_text,
        input_tokens=in_tokens,
        output_tokens=out_tokens,
        cost_usd=cost,
        latency_ms=latency_ms,
        model=settings.claude_model,
        prompt_version=PROMPT_VERSION
    )
    