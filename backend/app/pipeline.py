import pandas as pd
from .scoring import score_fundamental, score_technical, score_sentiment, final_score, label_signal

def build_signals_df() -> pd.DataFrame:
    rows = [
        {"ticker":"AAPL","company":"Apple Inc.","sector":"Technology","pe_ratio":30.0,"eps_growth":0.10,"roe":0.45,"rsi_14":58.0,"macd":1.2,"sma_50":205.0,"sma_200":190.0,"last_close":212.0,"sentiment_polarity":0.20},
        {"ticker":"MSFT","company":"Microsoft Corp.","sector":"Technology","pe_ratio":34.0,"eps_growth":0.12,"roe":0.38,"rsi_14":55.0,"macd":0.8,"sma_50":430.0,"sma_200":405.0,"last_close":438.0,"sentiment_polarity":0.18},
        {"ticker":"NVDA","company":"NVIDIA Corp.","sector":"Technology","pe_ratio":55.0,"eps_growth":0.35,"roe":0.52,"rsi_14":67.0,"macd":2.1,"sma_50":118.0,"sma_200":98.0,"last_close":124.0,"sentiment_polarity":0.35},
        {"ticker":"AMZN","company":"Amazon.com Inc.","sector":"Consumer Discretionary","pe_ratio":42.0,"eps_growth":0.18,"roe":0.22,"rsi_14":53.0,"macd":0.5,"sma_50":182.0,"sma_200":170.0,"last_close":185.0,"sentiment_polarity":0.12},
        {"ticker":"GOOGL","company":"Alphabet Inc.","sector":"Communication Services","pe_ratio":28.0,"eps_growth":0.14,"roe":0.28,"rsi_14":51.0,"macd":0.4,"sma_50":172.0,"sma_200":160.0,"last_close":174.0,"sentiment_polarity":0.10},
        {"ticker":"META","company":"Meta Platforms Inc.","sector":"Communication Services","pe_ratio":26.0,"eps_growth":0.20,"roe":0.30,"rsi_14":57.0,"macd":0.9,"sma_50":495.0,"sma_200":455.0,"last_close":505.0,"sentiment_polarity":0.16},
        {"ticker":"TSLA","company":"Tesla Inc.","sector":"Consumer Discretionary","pe_ratio":62.0,"eps_growth":0.08,"roe":0.19,"rsi_14":49.0,"macd":-0.2,"sma_50":178.0,"sma_200":201.0,"last_close":172.0,"sentiment_polarity":0.05},
        {"ticker":"BRK-B","company":"Berkshire Hathaway Inc. Class B","sector":"Financials","pe_ratio":23.0,"eps_growth":0.09,"roe":0.14,"rsi_14":54.0,"macd":0.3,"sma_50":420.0,"sma_200":398.0,"last_close":426.0,"sentiment_polarity":0.07},
        {"ticker":"LLY","company":"Eli Lilly and Company","sector":"Health Care","pe_ratio":58.0,"eps_growth":0.28,"roe":0.62,"rsi_14":64.0,"macd":1.6,"sma_50":820.0,"sma_200":760.0,"last_close":836.0,"sentiment_polarity":0.22},
        {"ticker":"AVGO","company":"Broadcom Inc.","sector":"Information Technology","pe_ratio":33.0,"eps_growth":0.24,"roe":0.40,"rsi_14":60.0,"macd":1.1,"sma_50":1510.0,"sma_200":1395.0,"last_close":1536.0,"sentiment_polarity":0.19},
        {"ticker":"JPM","company":"JPMorgan Chase & Co.","sector":"Financials","pe_ratio":14.0,"eps_growth":0.11,"roe":0.17,"rsi_14":56.0,"macd":0.6,"sma_50":198.0,"sma_200":186.0,"last_close":202.0,"sentiment_polarity":0.11},
        {"ticker":"V","company":"Visa Inc.","sector":"Financials","pe_ratio":31.0,"eps_growth":0.13,"roe":0.46,"rsi_14":59.0,"macd":0.7,"sma_50":278.0,"sma_200":261.0,"last_close":283.0,"sentiment_polarity":0.14},
        {"ticker":"XOM","company":"Exxon Mobil Corporation","sector":"Energy","pe_ratio":13.0,"eps_growth":0.06,"roe":0.21,"rsi_14":47.0,"macd":-0.1,"sma_50":116.0,"sma_200":112.0,"last_close":114.0,"sentiment_polarity":0.03},
        {"ticker":"WMT","company":"Walmart Inc.","sector":"Consumer Staples","pe_ratio":29.0,"eps_growth":0.07,"roe":0.18,"rsi_14":52.0,"macd":0.2,"sma_50":67.0,"sma_200":63.0,"last_close":68.0,"sentiment_polarity":0.08},
        {"ticker":"UNH","company":"UnitedHealth Group Incorporated","sector":"Health Care","pe_ratio":21.0,"eps_growth":0.10,"roe":0.25,"rsi_14":50.0,"macd":0.1,"sma_50":505.0,"sma_200":493.0,"last_close":507.0,"sentiment_polarity":0.09},
        {"ticker":"MA","company":"Mastercard Incorporated","sector":"Financials","pe_ratio":35.0,"eps_growth":0.15,"roe":1.50,"rsi_14":61.0,"macd":1.0,"sma_50":462.0,"sma_200":438.0,"last_close":470.0,"sentiment_polarity":0.15},
        {"ticker":"PG","company":"Procter & Gamble Company","sector":"Consumer Staples","pe_ratio":27.0,"eps_growth":0.05,"roe":0.32,"rsi_14":48.0,"macd":-0.05,"sma_50":166.0,"sma_200":160.0,"last_close":164.0,"sentiment_polarity":0.04},
        {"ticker":"HD","company":"Home Depot, Inc.","sector":"Consumer Discretionary","pe_ratio":25.0,"eps_growth":0.09,"roe":2.20,"rsi_14":55.0,"macd":0.45,"sma_50":352.0,"sma_200":338.0,"last_close":357.0,"sentiment_polarity":0.10},
        {"ticker":"COST","company":"Costco Wholesale Corporation","sector":"Consumer Staples","pe_ratio":49.0,"eps_growth":0.12,"roe":0.29,"rsi_14":63.0,"macd":1.3,"sma_50":812.0,"sma_200":745.0,"last_close":828.0,"sentiment_polarity":0.17},
        {"ticker":"JNJ","company":"Johnson & Johnson","sector":"Health Care","pe_ratio":16.0,"eps_growth":0.04,"roe":0.24,"rsi_14":46.0,"macd":-0.15,"sma_50":151.0,"sma_200":155.0,"last_close":149.0,"sentiment_polarity":0.02}
    ]

    out = []
    for r in rows:
        f = score_fundamental(r)
        t = score_technical(r)
        s = score_sentiment(r.get("sentiment_polarity", 0.0))
        fs = final_score(f, t, s)
        out.append({
            **r,
            "fundamental_score": round(f, 2),
            "technical_score": round(t, 2),
            "sentiment_score": round(s, 2),
            "final_score": round(fs, 2),
            "signal": label_signal(fs)
        })

    return pd.DataFrame(out).sort_values("final_score", ascending=False).reset_index(drop=True)
