"""NeuroLearning Engine — FastAPI application entry point."""

from fastapi import FastAPI

from app.api.routes import loop, session, state, vocab
from app import ui

app = FastAPI(
    title="NeuroLearning Engine",
    description=(
        "Evidence-based language acquisition engine. "
        "Learning items are sensors for collecting skill acquisition evidence. "
        "AI evaluates observations; the engine updates P(skill acquired | evidence)."
    ),
    version="0.1.0",
)

app.include_router(ui.router)
app.include_router(session.router)
app.include_router(loop.router)
app.include_router(state.router)
app.include_router(vocab.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
