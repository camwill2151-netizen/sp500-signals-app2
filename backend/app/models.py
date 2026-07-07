from pydantic import BaseModel
from typing import Optional

class StockSignal(BaseModel):
    rank: Optional[int] = None
    ticker: str
    company: Optional[str] = None
    sector: Optional[str] = None
    signal: str
    final_score: float
    fundamental_score: float
    technical_score: float
    sentiment_score: float
    pe_ratio: Optional[float] = None
    eps_growth: Optional[float] = None
    roe: Optional[float] = None
    rsi_14: Optional[float] = None
    macd: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    sentiment_polarity: Optional[float] = None
