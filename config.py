# ============================================================
# CONFIG - IPM RADAR V4.1
# ============================================================

import os
from datetime import datetime, time
from zoneinfo import ZoneInfo


# ============================================================
# IDENTIDADE
# ============================================================

NOME_BOT = os.getenv(
    "NOME_BOT",
    "IPM RADAR V4.1"
)

VERSAO = "4.1"


# ============================================================
# ODDS API
# ============================================================

BASE_URL = os.getenv(
    "ODDS_API_BASE_URL",
    "https://api.odds-api.io/v3"
).rstrip("/")

BOOKMAKER = os.getenv(
    "ODDS_BOOKMAKER",
    "Bet365"
)

SPORT = os.getenv(
    "ODDS_SPORT",
    "football"
)


# ============================================================
# RADAR
# ============================================================

# 300 segundos = 5 minutos
# Mantido propositalmente para controlar o consumo da API.

INTERVALO_RADAR = int(
    os.getenv(
        "INTERVALO_RADAR",
        "300"
    )
)

MAX_JOGOS_RADAR = int(
    os.getenv(
        "MAX_JOGOS_RADAR",
        "10"
    )
)

# A Odds-API.io permite até 10 eventos no /odds/multi.
MAX_EVENTOS_POR_CONSULTA = min(
    int(
        os.getenv(
            "MAX_EVENTOS_POR_CONSULTA",
            "10"
        )
    ),
    10
)


# ============================================================
# REQUISIÇÃO
# ============================================================

TIMEOUT_REQUISICAO = int(
    os.getenv(
        "TIMEOUT_REQUISICAO",
        "20"
    )
)


# ============================================================
# FILTROS IPM
# ============================================================

IPM_MINIMO_OBSERVACAO = float(
    os.getenv(
        "IPM_MINIMO_OBSERVACAO",
        "20"
    )
)

IPM_MINIMO_FORTE = float(
    os.getenv(
        "IPM_MINIMO_FORTE",
        "40"
    )
)

IPM_MINIMO_MUITO_FORTE = float(
    os.getenv(
        "IPM_MINIMO_MUITO_FORTE",
        "60"
    )
)

VARIACAO_MINIMA_ODD = float(
    os.getenv(
        "VARIACAO_MINIMA_ODD",
        "0.5"
    )
)


# ============================================================
# HORÁRIO
# ============================================================

FUSO_HORARIO = ZoneInfo(
    os.getenv(
        "FUSO_HORARIO",
        "America/Sao_Paulo"
    )
)

HORA_INICIO = time(
    6,
    0
)

HORA_FIM = time(
    0,
    0
)


# ============================================================
# API KEY
# ============================================================

def obter_api_key():

    key = os.getenv(
        "ODDS_API_KEY",
        ""
    ).strip()

    if not key:

        raise RuntimeError(
            "ODDS_API_KEY não configurada no Render."
        )

    return key


# ============================================================
# HORÁRIO ATUAL
# ============================================================

def horario_atual():

    return datetime.now(
        FUSO_HORARIO
    )


# ============================================================
# RADAR ATIVO
# ============================================================

def horario_ativo():

    agora = horario_atual().time()

    # Janela normal:
    # 06:00 até 00:00

    if HORA_INICIO < HORA_FIM:

        return (
            HORA_INICIO
            <= agora
            < HORA_FIM
        )

    # Quando o fim é meia-noite,
    # a janela atravessa a virada do dia.

    return (
        agora >= HORA_INICIO
        or agora < HORA_FIM
)
