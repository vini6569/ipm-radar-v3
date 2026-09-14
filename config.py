import os
from datetime import timezone
from zoneinfo import ZoneInfo

FUSO_HORARIO = ZoneInfo(os.getenv("FUSO_HORARIO", "America/Sao_Paulo"))
BASE_URL = os.getenv("BASE_URL", "https://api.football-data-api.com")
SPORT = os.getenv("SPORT", "soccer")
BOOKMAKER = os.getenv("BOOKMAKER", "Bet365")
MAX_EVENTOS_POR_CONSULTA = int(os.getenv("MAX_EVENTOS_POR_CONSULTA", "20"))
TIMEOUT_REQUISICAO = int(os.getenv("TIMEOUT_REQUISICAO", "20"))
PRE_LIVE_JANELA_MINUTOS = int(os.getenv("PRE_LIVE_JANELA_MINUTOS", "180"))
Q_MIN = float(os.getenv("Q_PRE_LIVE_MINIMO", "2.00"))
Q_MAX = float(os.getenv("Q_PRE_LIVE_MAXIMO", "3.00"))
LIMITE_API_DIARIO = int(os.getenv("LIMITE_API_DIARIO", "500"))

def obter_api_key():
    key = os.getenv("API_KEY") or os.getenv("ODDS_API_KEY")
    if not key:
        raise RuntimeError("API_KEY/ODDS_API_KEY não configurada.")
    return key
