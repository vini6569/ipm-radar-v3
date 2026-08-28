# ============================================================
# CONFIG - IPM RADAR V4.3
# ============================================================

import os
from datetime import datetime, time
from zoneinfo import ZoneInfo

NOME_BOT = os.getenv("NOME_BOT", "IPM RADAR V4.3")
VERSAO = "4.3"

BASE_URL = os.getenv("ODDS_API_BASE_URL", "https://api.odds-api.io/v3").rstrip("/")
BOOKMAKER = os.getenv("ODDS_BOOKMAKER", "Bet365")
SPORT = os.getenv("ODDS_SPORT", "football")

# 300 s = uma leitura a cada 5 minutos.
INTERVALO_RADAR = int(os.getenv("INTERVALO_RADAR", "300"))
MAX_JOGOS_RADAR = int(os.getenv("MAX_JOGOS_RADAR", "10"))
MAX_EVENTOS_POR_CONSULTA = min(int(os.getenv("MAX_EVENTOS_POR_CONSULTA", "10")), 10)

TIMEOUT_REQUISICAO = int(os.getenv("TIMEOUT_REQUISICAO", "20"))

IPM_MINIMO_OBSERVACAO = float(os.getenv("IPM_MINIMO_OBSERVACAO", "20"))
IPM_MINIMO_FORTE = float(os.getenv("IPM_MINIMO_FORTE", "40"))
IPM_MINIMO_MUITO_FORTE = float(os.getenv("IPM_MINIMO_MUITO_FORTE", "60"))
VARIACAO_MINIMA_ODD = float(os.getenv("VARIACAO_MINIMA_ODD", "0.5"))

# Entrada: primeiros 5 minutos, mas a referência é a odd pré-live.
MINUTO_MINIMO_ENTRADA = int(os.getenv("MINUTO_MINIMO_ENTRADA", "1"))
MINUTO_MAXIMO_ENTRADA = int(os.getenv("MINUTO_MAXIMO_ENTRADA", "5"))
IPM_MINIMO_ENTRADA = float(os.getenv("IPM_MINIMO_ENTRADA", "40"))

# Quantidade de sinais por jogo.
MAX_ENTRADAS_POR_JOGO = int(os.getenv("MAX_ENTRADAS_POR_JOGO", "1"))

# Janela usada para procurar partidas que ainda não começaram.
PRE_LIVE_JANELA_MINUTOS = int(os.getenv("PRE_LIVE_JANELA_MINUTOS", "15"))

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
    agora = horario_atual().time()
    if HORA_INICIO < HORA_FIM:
        return HORA_INICIO <= agora < HORA_FIM
    return agora >= HORA_INICIO or agora < HORA_FIM
