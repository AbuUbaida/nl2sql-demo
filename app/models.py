from app.pipeline import PipelineResult
from pydantic import BaseModel, ConfigDict, Field

class QueryRequest(BaseModel):
    """
    What the caller sends.
    """
    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="A plain-English question about the fuel transaction data.",
    )
    table: str = Field(
        default="july_transactions_2026",
        description="Which table to answer against. Only one table exists today.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "Top 5 towns by total fuel spend",
                "table": "july_transactions_2026",
            }
        }
    )


class QueryResponse(BaseModel):
    question: str = Field(description="The question, echoed back.")
    answerable: bool = Field(
        description="False when the question cannot be answered from this data."
    )
    sql: str | None = Field(
        default=None,
        description="The generated PostgreSQL query. Null when not answerable.",
    )
    explanation: str = Field(
        default="",
        description="One plain-English sentence describing the query, or why it was refused.",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Interpretive choices the system made. Review these if a result looks wrong.",
    )
    confidence: str = Field(
        default="medium",
        description="One of: high, medium, low.",
    )
    refusal_reason: str | None = Field(
        default=None,
        description="Machine-readable refusal code. Null when answerable.",
    )
    error: str | None = Field(
        default=None,
        description="Set only when something went wrong. Null on success and on refusal.",
    )
    latency_ms: int = Field(description="End-to-end time in milliseconds.")
    cost_usd: float = Field(description="Cost of this request in US dollars.")
    model: str = Field(description="Which Claude model answered.")
    prompt_version: str = Field(description="Which prompt version was used.")


    @classmethod
    def from_pipeline_result(cls, result: PipelineResult) -> "QueryResponse":
        """
        Convert the internal result into the public response.
        """
        return cls(
            question=result.question,
            answerable=result.answerable,
            sql=result.sql,
            explanation=result.explanation,
            assumptions=result.assumptions,
            confidence=result.confidence,
            refusal_reason=result.refusal_reason,
            error=result.error,
            latency_ms=result.latency_ms,
            cost_usd=result.cost_usd,
            model=result.model,
            prompt_version=result.prompt_version,
        )


class ExamplesResponse(BaseModel):
    """Returned by GET /examples."""
 
    examples: list[str] = Field(description="Questions known to work well.")