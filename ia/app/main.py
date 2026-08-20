from fastapi import FastAPI

app = FastAPI(title="ChargeGrid-Manager IA")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
