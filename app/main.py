from fastapi import FastAPI

app = FastAPI(title="Cosmos", description="API for the cosmos project", version="0.1.0")

@app.get("/health")
def health_check():
    return {"status": "ok"}