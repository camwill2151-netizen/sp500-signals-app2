from fastapi import FastAPI

app = FastAPI(title="SP500 Signals API")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "SP500 Signals API running"}
