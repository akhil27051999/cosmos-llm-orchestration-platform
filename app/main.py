from fastapi import FastAPI

app = FastAPI(title="cosmos", description="API for the cosmos project")

@app.get("/health")
def health_check():
    return {"status": "ok"}