from dataclasses import dataclass, field
import time
import logging

from app.llm_client import LLMAPIError, LLMError, LLMParseError, LLMTimeoutError, generate_sql
from app.prompt_builder import PROMPT_VERSION
from app.schema_reader import get_table_schema

logger = logging.getLogger(__name__)
 
DEFAULT_TABLE = "july_transactions_2026"


@dataclass
class PipelineResult:
    """
    Everything one question produced. This is the internal shape for debugging purpose.
    """
    question: str
    answerable: bool
    explanation: str
    confidence: str
 
    sql: str | None = None
    assumptions: list[str] = field(default_factory=list)
    refusal_reason: str | None = None
    error: str | None = None
 
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
 
    model: str = ""
    prompt_version: str = PROMPT_VERSION


def _elapsed_ms(start_time: float) -> int:
    """Milliseconds since `start_time`, as a whole number."""
    return int((time.perf_counter() - start_time) * 1000)


def _friendly_error(exc: Exception) -> str:
    """
    Turn an internal exception into something safe to show a person.
    The real exception still goes to the logs.
    """
    if isinstance(exc, LLMTimeoutError):
        return "The request took too long. Please try again."
    if isinstance(exc, LLMParseError):
        return "The system produced a malformed answer. Please try rephrasing."
    if isinstance(exc, LLMAPIError):
        return "Could not reach the language model service. Please try again."
    return "Something went wrong while processing the question."


def answer_question(question: str, table_name: str = DEFAULT_TABLE) -> PipelineResult:
    start_time = time.perf_counter()
    try:
        schema = get_table_schema(table_name)
        llm = generate_sql(question, schema)

        return PipelineResult(
            question=question,
            answerable=llm.answerable,
            sql=llm.sql,
            explanation=llm.explanation,
            assumptions=llm.assumptions,
            confidence=llm.confidence,
            refusal_reason=llm.refusal_reason,
            error=None,
            latency_ms=_elapsed_ms(start_time),
            input_tokens=llm.input_tokens,
            output_tokens=llm.output_tokens,
            cost_usd=llm.cost_usd,
            model=llm.model,
            prompt_version=llm.prompt_version,
        )
    except (LLMError, ValueError) as exc:
        # Expected failures: the model service misbehaved, or the question
        # failed a check inside the prompt builder.
        logger.warning("Pipeline failed for %r: %s", question, exc)
        return PipelineResult(
            question=question,
            answerable=False,
            explanation="",
            confidence="low",
            error=_friendly_error(exc),
            latency_ms=_elapsed_ms(start_time),
        )
    except Exception as exc:
        # Unexpected failures. Logged the full traceback.
        logger.exception("Unexpected pipeline error for %r", question)
        return PipelineResult(
            question=question,
            answerable=False,
            explanation="",
            confidence="low",
            error=_friendly_error(exc),
            latency_ms=_elapsed_ms(start_time),
        )