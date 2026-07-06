from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SP500 Signals API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "SP500 Signals API running"}

@app.get("/signals")
def signals():
    now = datetime.now(timezone.utc).isoformat()
    data = [
        {"symbol": "AAPL", "action": "BUY", "score": 0.82, "price": 214.18, "timestamp": now},
        {"symbol": "MSFT", "action": "HOLD", "score": 0.56, "price": 498.72, "timestamp": now},
        {"symbol": "NVDA", "action": "BUY", "score": 0.91, "price": 141.07, "timestamp": now},
        {"symbol": "AMZN", "action": "SELL", "score": 0.31, "price": 205.44, "timestamp": now},
        {"symbol": "GOOGL", "action": "HOLD", "score": 0.49, "price": 187.63, "timestamp": now},
    ]
    return {"count": len(data), "signals": data, "generated_at": now}
