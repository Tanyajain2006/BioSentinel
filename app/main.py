from fastapi import FastAPI

app = FastAPI(
    title="BioSentinel",
    description="Self-Correcting Agentic Graph Retrieval for Hallucination-Free Clinical Reasoning.",
    version="0.1.0",
)


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "service": "BioSentinel",
        "version": "0.1.0",
    }
