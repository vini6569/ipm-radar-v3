# ============================================================
# CONFIG - IPM RADAR V5.0
# BASE: 3 ODDS (CASA / EMPATE / VISITANTE)
# TRAJETÓRIA + REFERÊNCIA MINUTO 45
# ============================================================

import os
from datetime import datetime, time
from zoneinfo import ZoneInfo


# ------------------------------------------------------------
# IDENTIFICAÇÃO
# ------------------------------------------------------------

NOME_BOT = os.getenv("NOME_BOT", "IPM RADAR V5.0")
VERSAO = "5.0"


# ------------------------------------------------------------
# ODDS API
# ------------------------------------------------------------

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

TIMEOUT_REQUISICAO = int(
    os.getenv("TIMEOUT_REQUISICAO", "20")
)


# ------------------------------------------------------------
# RADAR
# ------------------------------------------------------------

# Leitura a cada 5 minutos.
INTERVALO_RADAR = int(
    os.getenv("INTERVALO_RADAR", "300")
)

MAX_JOGOS_RADAR = int(
    os.getenv("MAX_JOGOS_RADAR", "30")
)

MAX_EVENTOS_POR_CONSULTA = min(
    int(os.getenv("MAX_EVENTOS_POR_CONSULTA", "30")),
    30
)


# ------------------------------------------------------------
# IPM
# ------------------------------------------------------------

IPM_MINIMO_OBSERVACAO = float(
    os.getenv("IPM_MINIMO_OBSERVACAO", "20")
)

IPM_MINIMO_FORTE = float(
    os.getenv("IPM_MINIMO_FORTE", "40")
)

IPM_MINIMO_MUITO_FORTE = float(
    os.getenv("IPM_MINIMO_MUITO_FORTE", "60")
)

VARIACAO_MINIMA_ODD = float(
    os.getenv("VARIACAO_MINIMA_ODD", "0.5")
)


# ------------------------------------------------------------
# ENTRADA
# ------------------------------------------------------------

# Não vamos mais limitar a entrada somente aos primeiros 5 minutos.
# O radar vai acompanhar a trajetória até o minuto 45.

MINUTO_MINIMO_ENTRADA = int(
    os.getenv("MINUTO_MINIMO_ENTRADA", "1")
)

MINUTO_MAXIMO_ENTRADA = int(
    os.getenv("MINUTO_MAXIMO_ENTRADA", "45")
)

IPM_MINIMO_ENTRADA = float(
    os.getenv("IPM_MINIMO_ENTRADA", "40")
)

MAX_ENTRADAS_POR_JOGO = int(
    os.getenv("MAX_ENTRADAS_POR_JOGO", "1")
)


# ------------------------------------------------------------
# REFERÊNCIA MINUTO 45
# ------------------------------------------------------------

MINUTO_REFERENCIA = int(
    os.getenv("MINUTO_REFERENCIA", "45")
)

# Faixa de tolerância para observar a região do minuto 45.
# Exemplo: 43, 44, 45, 46 e 47.
JANELA_MINUTO_45 = int(
    os.getenv("JANELA_MINUTO_45", "2")
)

# IPM usado como referência para alerta.
IPM_ALERTA = float(
    os.getenv("IPM_ALERTA", "45")
)

IPM_ALERTA_FORTE = float(
    os.getenv("IPM_ALERTA_FORTE", "50")
)

IPM_ALERTA_MUITO_FORTE = float(
    os.getenv("IPM_ALERTA_MUITO_FORTE", "60")
)


# ------------------------------------------------------------
# TRAJETÓRIA DAS 3 ODDS
# ------------------------------------------------------------

# Quantidade máxima de pontos guardados por jogo.
MAX_PONTOS_TRAJETORIA = int(
    os.getenv("MAX_PONTOS_TRAJETORIA", "100")
)

# Mínima mudança percentual para considerar
# que houve movimentação relevante.
VARIACAO_MINIMA_TRAJETORIA = float(
    os.getenv("VARIACAO_MINIMA_TRAJETORIA", "0.20")
)


# ------------------------------------------------------------
# PRÉ-LIVE
# ------------------------------------------------------------

PRE_LIVE_JANELA_MINUTOS = int(
    os.getenv("PRE_LIVE_JANELA_MINUTOS", "15")
)


# ------------------------------------------------------------
# FUSO / HORÁRIO DE FUNCIONAMENTO
# ------------------------------------------------------------

FUSO_HORARIO = ZoneInfo(
    os.getenv(
        "FUSO_HORARIO",
        "America/Sao_Paulo"
    )
)

HORA_INICIO = time(6, 0)
HORA_FIM = time(0, 0)


# ------------------------------------------------------------
# API KEY
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# HORÁRIO
# ------------------------------------------------------------

def horario_atual():
    return datetime.now(FUSO_HORARIO)


def horario_ativo():
    agora = horario_atual().time()

    if HORA_INICIO < HORA_FIM:
        return HORA_INICIO <= agora < HORA_FIM

    return (
        agora >= HORA_INICIO
        or agora < HORA_FIM
)
