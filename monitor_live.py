# ============================================================
# LIVE - IPM RADAR V5.2
# SOMENTE MONITORAMENTO LIVE
# ============================================================

import time

from odds_api import (
    buscar_jogos_ao_vivo_por_ids,
    buscar_odds_multiplos,
    extrair_mercados,
)

from telegram import enviar_mensagem


INTERVALO_LIVE = 60

HISTORICO_LIVE = {}


# ============================================================
# CONVERSÃO
# ============================================================

def numero(valor, padrao=0.0):
    try:
        if valor in (None, ""):
            return padrao
        return float(valor)
    except (TypeError, ValueError):
        return padrao


# ============================================================
# MEMÓRIA DO JOGO
# ============================================================

def obter_jogo(event_id, casa="", fora=""):

    event_id = str(event_id)

    return HISTORICO_LIVE.setdefault(
        event_id,
        {
            "event_id": event_id,
            "casa": casa,
            "fora": fora,
            "historico": [],
            "ultima_leitura": None,
            "gol_anterior": 0,
            "sinal_enviado": False,
        },
    )


# ============================================================
# REGISTRAR LEITURA
# ============================================================

def registrar_leitura(dados):

    jogo = obter_jogo(
        dados["event_id"],
        dados["casa"],
        dados["fora"],
    )

    leitura = {
        "timestamp": time.time(),
        "minuto": dados["minuto"],
        "placar": dados["placar"],
        "gols": dados["gols"],
        "odd_casa": dados["odd_casa"],
        "odd_empate": dados["odd_empate"],
        "odd_visitante": dados["odd_visitante"],
        "escanteios": dados["escanteios"],
        "finalizacoes": dados["finalizacoes"],
        "ataques_perigosos": dados["ataques_perigosos"],
        "cartoes": dados["cartoes"],
    }

    jogo["historico"].append(leitura)

    jogo["historico"] = (
        jogo["histor
