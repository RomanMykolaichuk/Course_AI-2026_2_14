from fastapi import FastAPI

app = FastAPI(
    title="Ukraine Air Strike Analytics API",
    version="0.1.0",
    description="Educational API for retrospective analytics and ML demonstrations.",
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
