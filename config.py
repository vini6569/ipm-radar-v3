# ============================================================
# CONFIG - IPM RADAR V5.2
# ============================================================

import os
from datetime import time
from zoneinfo import ZoneInfo


# ============================================================
# GERAL
# ============================================================

FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")

BASE_URL = os.getenv(
    "ODDS_API_BASE_URL",
    "https://api.sportsgameodds.com"
).rstrip("/")

SPORT = os.getenv(
    "ODDS_API_SPORT",
    "soccer"
)

BOOKMAKER = os.getenv(
    "ODDS_API_BOOKMAKER",
    "bet365"
)


# ============================================================
# API
# ============================================================

MAX_EVENTOS_POR_CONSULTA = int(
    os.getenv(
        "MAX_EVENTOS_POR_CONSULTA",
        "20"
    )
)

TIMEOUT_REQUISICAO = int(
    os.getenv(
        "TIMEOUT_REQUISICAO",
        "20"
    )
)

LIMITE_API_DIARIO = int(
    os.getenv(
        "LIMITE_API_DIARIO",
        "500"
    )
)


# ============================================================
# PRÉ-LIVE
# ============================================================

PRE_LIVE_JANELA_MINUTOS = int(
    os.getenv(
        "PRE_LIVE_JANELA_MINUTOS",
        "180"
    )
)


# ============================================================
# Q
# ============================================================

Q_MIN = 2.00
Q_MAX = 3.00


# ============================================================
# API KEY
# ============================================================

def obter_api_key():

    chave = os.getenv(
        "ODDS_API_KEY",
        ""
    ).strip()

    if not chave:
        raise RuntimeError(
            "ODDS_API_KEY não configurada."
        )

    return chave


# ============================================================
# HORÁRIO ATIVO
# ============================================================

def horario_ativo(dt=None):

    if dt is None:
        return True

    hora = dt.astimezone(
        FUSO_HORARIO
    ).time()

    return (
        time(6, 0) <= hora < time(24, 0)
    )
