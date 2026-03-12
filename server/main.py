
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from ai_client import (
    AIClientError,
    AIConnectionError,
    AIServiceError,
    AITimeoutError,
    chat_completion,
)
from ai_prompt import build_messages
from classifier import classify, detect_language
from database import get_db, init_db
from logger import RequestLoggingMiddleware, logger
from security import InputRejectedError, RateLimitMiddleware, sanitize_input
from seed import (
    fetch_all_exams,
    fetch_reception_hours,
    fetch_room_locations,
    fetch_exams_grades,
    fetch_library_services,
    fetch_student_services,
)
from session_manager import get_session_manager


_TIMEOUT_MSG: dict[str, str] = {
    "he": (
        "מצטער/ת, השירות אינו זמין כרגע – לא התקבלה תשובה תוך 5 שניות.\n"
        "אנא נסה/י שוב בעוד מספר רגעים, או פנה/י למזכירות: 03-6789001."
    ),
    "en": (
        "Sorry, the service is currently unavailable – no response within 5 seconds.\n"
        "Please try again in a few moments, or contact the Registrar: 03-6789001."
    ),
}

_CONNECTION_MSG: dict[str, str] = {
    "he": (
        "מצטער/ת, לא ניתן להתחבר לשירות הבינה המלאכותית כרגע.\n"
        "אנא נסה/י שוב בעוד מספר רגעים, או פנה/י למזכירות: 03-6789001."
    ),
    "en": (
        "Sorry, the AI service is unreachable right now.\n"
        "Please try again in a few moments, or contact the Registrar: 03-6789001."
    ),
}

_SERVICE_MSG: dict[str, str] = {
    "he": (
        "מצטער/ת, שירות הבינה המלאכותית החזיר שגיאה.\n"
        "אנא נסה/י שוב בעוד מספר רגעים, או פנה/י למזכירות: 03-6789001."
    ),
    "en": (
        "Sorry, the AI service returned an error.\n"
        "Please try again in a few moments, or contact the Registrar: 03-6789001."
    ),
}

_GENERIC_MSG: dict[str, str] = {
    "he": "מצטער/ת, אירעה שגיאה בלתי צפויה. אנא פנה/י למזכירות: 03-6789001.",
    "en": "Sorry, an unexpected error occurred. Please contact the Registrar: 03-6789001.",
}


def _localised(msg_map: dict[str, str], question: str) -> str:
    """Pick the Hebrew or English string based on the question language."""
    return msg_map[detect_language(question)]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """
    Startup  : initialise DB tables, auto-seed mock data on first run.
    Shutdown : log a clean goodbye.
    """
    init_db()
    from seed import seed_all
    summary = seed_all()
    logger.info("Seed summary: %s", summary)
    logger.info("Smart Campus Assistant API is ready.")
    yield
    logger.info("Smart Campus Assistant API is shutting down.")


app = FastAPI(
    title="Smart Campus Assistant",
    description="AI-powered bilingual campus information assistant.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - permissive for local dev; lock down origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Per-request timing + structured logging
app.add_middleware(RequestLoggingMiddleware)

# Rate limiting: 100 requests per 60-second sliding window per IP
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)



@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Remap Pydantic validation errors from HTTP 422 to HTTP 400."""
    errors = exc.errors()
    logger.warning("[validation] 400 errors: %s", errors)
    return JSONResponse(
        status_code=400,
        content={
            "detail": "Invalid request",
            "errors": [
                {
                    "field": ".".join(str(loc) for loc in e["loc"]),
                    "message": e["msg"],
                }
                for e in errors
            ],
        },
    )


@app.exception_handler(InputRejectedError)
async def input_rejected_handler(
    request: Request, exc: InputRejectedError
) -> JSONResponse:
    """
    Return HTTP 400 when sanitize_input() rejects the user's question.
    The matched_pattern is logged internally but never sent to the client.
    """
    logger.warning("[security] Input rejected — reason=%r  pattern=%r", exc.reason, exc.matched_pattern)
    return JSONResponse(
        status_code=400,
        content={"detail": exc.reason},
    )


class AskRequest(BaseModel):
    """
    Payload accepted by POST /ask.
    The field_validator strips whitespace and rejects blank questions;
    FastAPI converts the resulting ValueError to an HTTP 400 via the
    exception handler registered above.
    """
    question: str
    session_id: str

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("question must not be empty or whitespace")
        return v.strip()


class AskResponse(BaseModel):
    """
    Response returned by POST /ask.
    answer   : The assistant reply (AI-generated or managed fallback).
    category : One of: "schedule" | "general_info" | "technical_issue" | 
               "exams_and_grades" | "library_services" | "student_union_and_dorms" | "unknown"
    """
    answer: str
    category: str


@app.get("/health", tags=["ops"])
async def health_check():
    """Liveness probe for Docker / load-balancers."""
    logger.debug("Health check called")
    return {"status": "ok"}


@app.post("/ask/", response_model=AskResponse, tags=["assistant"])
async def ask(payload: AskRequest, db: Session = Depends(get_db)):
    
    question = payload.question
    session_id = payload.session_id
    logger.info("[/ask] session_id=%r  question=%r", session_id, question)

    # Sanitize — reject SQL / prompt injection attempts
    # InputRejectedError is raised here and caught by the global
    # exception handler above, returning HTTP 400 automatically.
    question = sanitize_input(question)
    logger.debug("[/ask] input passed sanitization")

    
    # Get conversation history early for context-aware classification
    session_mgr = get_session_manager()
    history = session_mgr.get_history(session_id)
    logger.debug("[/ask] conversation history length=%d", len(history))
    
    # Build a context string for classification from recent messages
    # This helps classify follow-up questions like "Where is it located?"
    classification_context = question
    if history and len(history) >= 2:
        # Get the most recent user-assistant pair for context
        recent_user_msg = next((msg["content"] for msg in reversed(history) 
                               if msg["role"] == "user"), None)
        if recent_user_msg:
            classification_context = f"{recent_user_msg} {question}"
            logger.debug("[/ask] Using context for classification: %r", classification_context[:100])

    # Classify the question (using context if available)
    classification = classify(classification_context)
    category       = classification.category
    logger.info("[/ask] category=%s", category)

    # Short-circuit for unknown / out-of-scope questions
    if classification.is_unknown:
        logger.info("[/ask] unknown -> returning fallback, skipping AI")
        # Still add to session history
        session_mgr.add_message(session_id, "user", question)
        session_mgr.add_message(session_id, "assistant", classification.fallback_message)
        return AskResponse(
            answer=classification.fallback_message,
            category=category,
        )

    # Fetch live DB context (session injected via Depends)
    exams     = fetch_all_exams(db=db)
    reception = fetch_reception_hours(db=db)
    rooms     = fetch_room_locations(db=db)
    exams_grades = fetch_exams_grades(db=db)
    library_services = fetch_library_services(db=db)
    student_services = fetch_student_services(db=db)
    logger.debug(
        "[/ask] DB rows: exams=%d  reception=%d  rooms=%d  grades=%d  library=%d  services=%d",
        len(exams), len(reception), len(rooms), len(exams_grades), len(library_services), len(student_services),
    )

    # Assemble prompt messages (now with conversation history)
    messages = build_messages(
        question,
        exams=exams,
        reception=reception,
        rooms=rooms,
        exams_grades=exams_grades,
        library_services=library_services,
        student_services=student_services,
        conversation_history=history,
    )

    # Call AI with 10-second hard timeout
    try:
        answer = await chat_completion(messages, timeout=10.0)
        logger.info("[/ask] AI answered (%d chars)", len(answer))

    except AITimeoutError:
        logger.warning("[/ask] AI timeout — question=%r", question)
        answer = _localised(_TIMEOUT_MSG, question)

    except AIConnectionError:
        logger.error("[/ask] AI connection error — question=%r", question)
        answer = _localised(_CONNECTION_MSG, question)

    except AIServiceError as exc:
        logger.error("[/ask] AI service error: %s", exc)
        answer = _localised(_SERVICE_MSG, question)

    except AIClientError as exc:
        logger.error("[/ask] Unexpected AI client error: %s", exc)
        answer = _localised(_GENERIC_MSG, question)

    # Add user question and AI answer to session history
    session_mgr.add_message(session_id, "user", question)
    session_mgr.add_message(session_id, "assistant", answer)

    # Return structured response
    return AskResponse(answer=answer, category=category)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
