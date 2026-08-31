from dataclasses import asdict
from datetime import datetime, timezone
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from app.models import ExamplesResponse, QueryRequest, QueryResponse
from app.pipeline import PipelineResult, answer_question
from app.schema_reader import get_table_schema
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.prompt_builder import PROMPT_VERSION
from app.db import check_connection


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("nl2sql")

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "requests.jsonl"
DEFAULT_TABLE = "july_transactions_2026"


def write_request_log(result: PipelineResult) -> None:
    """
    Append the full result to logs/requests.jsonl, one JSON object per line.
    """
    try:
        LOG_DIR.mkdir(exist_ok=True)
        record = asdict(result)
        record["logged_at"] = datetime.now(timezone.utc).isoformat()
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        logger.exception("Could not write request log")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts, and once when it stops."""
    logger.info("Starting up")
    logger.info("Model: %s   Prompt: %s", settings.claude_model, PROMPT_VERSION)

    if check_connection():
        logger.info("Database: connected")
    else:
        logger.error("Database: NOT reachable - /health will report this")

    try:
        schema = get_table_schema(DEFAULT_TABLE)
        logger.info(
            "Schema cached: %s (%s columns, %s rows)",
            schema.name,
            len(schema.columns),
            f"{schema.row_count:,}",
        )
    except Exception:
        logger.exception("Could not warm the schema cache")

    yield

    logger.info("Shutting down")


app = FastAPI(
    title="Fuel Data Query Service",
    description=(
        "Converts plain-English questions about July 2026 fuel transaction "
        "data into PostgreSQL queries.\n\n"
        "**This build generates SQL only. Query execution is not enabled.** "
    ),
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/query", response_model=QueryResponse, tags=["query"])
def query(request: QueryRequest) -> QueryResponse:
    """
    Turn a plain-English question into a PostgreSQL query.
    Returns 200 for both successful generation and a correct refusal.
    """
    result = answer_question(request.question, request.table)
 
    # One grep-able line per request.
    logger.info(
        "q=%r answerable=%s confidence=%s tokens=%s/%s cost=$%.4f latency=%sms%s",
        request.question,
        result.answerable,
        result.confidence,
        result.input_tokens,
        result.output_tokens,
        result.cost_usd,
        result.latency_ms,
        f" ERROR={result.error}" if result.error else "",
    )
 
    write_request_log(result)
 
    return QueryResponse.from_pipeline_result(result)


@app.get("/examples", response_model=ExamplesResponse, tags=["query"])
def examples() -> ExamplesResponse:
    """
    Questions known to work well.
    """
    return ExamplesResponse(
        examples=[
            "Total fuel used in Nishtar Town",
            "Top 5 towns by total fuel spend",
            "What was the average price per litre?",
            "How much fuel did the dumpers use?",
            "Which vehicle type spent the most on fuel?",
            "How much fuel was used between 5 and 12 July?",
            "Which filling station was used most often?",
            "Show me the busiest day by number of transactions",
            "How many transactions failed?",          # refuses
            "Which driver covered the most kilometres?",  # refuses
        ]
    )