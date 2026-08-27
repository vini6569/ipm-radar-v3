# ============================================================
# CONFIG - IPM RADAR V3
# ============================================================
import os
from datetime import datetime, time
from zoneinfo import ZoneInfo

NOME_BOT = os.getenv("NOME_BOT", "IPM RADAR V3")
VERSAO = "4.0"

BASE_URL = os.getenv("ODDS_API_BASE_URL", "https://api.odds-api.io/v3").rstrip("/")
BOOKMAKER = os.getenv("ODDS_BOOKMAKER", "Bet365")
SPORT = os.getenv("ODDS_SPORT", "football")

INTERVALO_RADAR = int(os.getenv("INTERVALO_RADAR", os.getenv("INTERVALO_SEGUNDOS", "60")))
MAX_JOGOS_RADAR = int(os.getenv("MAX_JOGOS_RADAR", "10"))
MAX_EVENTOS_POR_CONSULTA = int(os.getenv("MAX_EVENTOS_POR_CONSULTA", "10"))
TIMEOUT_REQUISICAO = int(os.getenv("TIMEOUT_REQUISICAO", "20"))

IPM_MINIMO_OBSERVACAO = float(os.getenv("IPM_MINIMO_OBSERVACAO", "20"))
IPM_MINIMO_FORTE = float(os.getenv("IPM_MINIMO_FORTE", "40"))
IPM_MINIMO_MUITO_FORTE = float(os.getenv("IPM_MINIMO_MUITO_FORTE", "60"))
VARIACAO_MINIMA_ODD = float(os.getenv("VARIACAO_MINIMA_ODD", "0.5"))

FUSO_HORARIO = ZoneInfo(os.getenv("FUSO_HORARIO", "America/Sao_Paulo"))
HORA_INICIO = time(6, 0)
HORA_FIM = time(0, 0)

def obter_api_key():
    key = os.getenv("ODDS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ODDS_API_KEY não configurada no Render.")
    return key

def horario_atual():
    return datetime.now(FUSO_HORARIO)

def horario_ativo():
    return horario_atual().time() >= HORA_INICIO
    
