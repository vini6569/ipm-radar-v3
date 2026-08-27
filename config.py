import os

BASE_URL = os.getenv("ODDS_API_BASE_URL", "https://api.odds-api.io/v3").rstrip("/")
BOOKMAKER = os.getenv("ODDS_BOOKMAKER", "Bet365")
SPORT = os.getenv("ODDS_SPORT", "football")
MAX_EVENTOS_POR_CONSULTA = int(os.getenv("MAX_EVENTOS_POR_CONSULTA", "10"))
INTERVALO_SEGUNDOS = int(os.getenv("INTERVALO_SEGUNDOS", "60"))
TIMEOUT_REQUISICAO = int(os.getenv("TIMEOUT_REQUISICAO", "20"))

def obter_api_key():
    key = os.getenv("ODDS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ODDS_API_KEY não configurada no Render.")
    return key
