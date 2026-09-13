# ============================================================
# MONITOR LIVE - IPM RADAR V5.1
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
# UTILIDADES
# ============================================================

def numero(valor, padrao=0.0):

    try:

        if valor in (None, ""):
            return padrao

        return float(valor)

    except (TypeError, ValueError):

        return padrao


def obter_jogo(event_id):

    return HISTORICO_LIVE.setdefault(
        str(event_id),
        {
            "event_id": str(event_id),
            "historico": [],
            "ultima_leitura": None,
            "gol_anterior": 0,
            "sinal_enviado": False,
        }
    )


# ============================================================
# HISTÓRICO
# ============================================================

def registrar_leitura(jogo, dados):

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
        jogo["historico"][-30:]
    )

    jogo["ultima_leitura"] = leitura

    return leitura


def obter_leitura_anterior(
    jogo,
    minutos=5
):

    historico = jogo.get(
        "historico",
        []
    )

    if len(historico) < 2:
        return None

    atual = historico[-1]

    limite = (
        atual["timestamp"]
        - minutos * 60
    )

    anteriores = [
        item
        for item in historico[:-1]
        if item["timestamp"] <= limite
    ]

    if not anteriores:
        return None

    return anteriores[-1]


# ============================================================
# MOVIMENTAÇÃO
# ============================================================

def calcular_variacao(
    base,
    atual
):

    base = numero(base)
    atual = numero(atual)

    if base <= 0 or atual <= 0:
        return 0.0

    return (
        (atual - base)
        / base
    ) * 100


def calcular_variaveis(jogo):

    atual = jogo["ultima_leitura"]

    anterior = obter_leitura_anterior(
        jogo,
        5
    )

    if anterior:

        var_casa = calcular_variacao(
            anterior["odd_casa"],
            atual["odd_casa"]
        )

        var_x = calcular_variacao(
            anterior["odd_empate"],
            atual["odd_empate"]
        )

        var_visitante = calcular_variacao(
            anterior["odd_visitante"],
            atual["odd_visitante"]
        )

    else:

        var_casa = 0.0
        var_x = 0.0
        var_visitante = 0.0

    return {
        "minuto": atual["minuto"],
        "gols": atual["gols"],

        "odd_casa": atual["odd_casa"],
        "odd_empate": atual["odd_empate"],
        "odd_visitante": atual["odd_visitante"],

        "variacao_casa_5m": var_casa,
        "variacao_x_5m": var_x,
        "variacao_visitante_5m": var_visitante,

        "escanteios": atual["escanteios"],
        "finalizacoes": atual["finalizacoes"],
        "ataques_perigosos":
            atual["ataques_perigosos"],
        "cartoes": atual["cartoes"],
    }


# ============================================================
# GOL
# ============================================================

def detectar_gol(jogo):

    atual = jogo["ultima_leitura"]

    gols = atual["gols"]

    anterior = jogo.get(
        "gol_anterior",
        gols
    )

    jogo["gol_anterior"] = gols

    return gols > anterior


# ============================================================
# ANÁLISE
# ============================================================

def analisar_padrao(jogo):

    v = calcular_variaveis(jogo)

    minuto = v["minuto"]
    gols = v["gols"]

    if gols > 0:

        return {
            "sinal": False,
            "motivo": "JOGO JA POSSUI GOL"
        }

    if (
        v["odd_casa"] < 2.00
        and
        v["odd_visitante"] < 2.00
    ):

        return {
            "sinal": False,
            "motivo": "ODDS DAS PONTAS ABAIXO DE 2.00"
        }

    if minuto < 10:

        return {
            "sinal": False,
            "motivo": "AINDA MUITO CEDO"
        }

    if minuto > 80:

        return {
            "sinal": False,
            "motivo": "FORA DA JANELA PRINCIPAL"
        }

    pressao = (
        v["escanteios"]
        + v["finalizacoes"]
        + v["ataques_perigosos"]
    )

    if pressao > 0:

        return {
            "sinal": True,
            "motivo":
                "ODD_2_PLUS + VARIAVEL_DE_PRESSAO"
        }

    return {
        "sinal": False,
        "motivo": "PADRAO AINDA NAO CONFIRMADO"
    }


# ============================================================
# MENSAGEM
# ============================================================

def formatar_sinal(
    jogo,
    v,
    analise
):

    return (
        "🚨 SINAL DE GOL — ACOMPANHAR\n\n"

        f"⚽ {jogo['casa']} x {jogo['fora']}\n"
        f"⏱️ Minuto: {v['minuto']}'\n"
        f"📊 Gols: {v['gols']}\n\n"

        "📈 ODDS\n"
        f"🏠 Casa: {v['odd_casa']:.2f}\n"
        f"🤝 X: {v['odd_empate']:.2f}\n"
        f"🚌 Visitante: {v['odd_visitante']:.2f}\n\n"

        "📉 MOVIMENTAÇÃO 5 MIN\n"
        f"Casa: {v['variacao_casa_5m']:+.2f}%\n"
        f"X: {v['variacao_x_5m']:+.2f}%\n"
        f"Visitante: "
        f"{v['variacao_visitante_5m']:+.2f}%\n\n"

        "🔥 VARIÁVEIS\n"
        f"Finalizações: {v['finalizacoes']}\n"
        f"Ataques perigosos: "
        f"{v['ataques_perigosos']}\n"
        f"Escanteios: {v['escanteios']}\n"
        f"Cartões: {v['cartoes']}\n\n"

        f"🧪 Padrão: {analise['motivo']}\n\n"

        "👁️ ENTRADA PARA ACOMPANHAMENTO\n"
        "⚠️ Sinal estatístico — "
        "não realiza aposta automaticamente."
    )


# ============================================================
# PROCESSAR LIVE
# ============================================================

def processar_live(ids):

    if not ids:

        print(
            "LIVE | Nenhum ID para monitorar."
        )

        return

    print(
        f"LIVE | Monitorando {len(ids)} jogos."
    )

    try:

        jogos_live = (
            buscar_jogos_ao_vivo_por_ids(ids)
            or []
        )

    except Exception as erro:

        print(
            "LIVE | Erro:",
            type(erro).__name__,
            erro
        )

        return

    if not jogos_live:

        print(
            "LIVE | Nenhum jogo retornado."
        )

        return

    try:

        odds = (
            buscar_odds_multiplos(
                jogos_live
            )
            or []
        )

    except Exception as erro:

        print(
            "LIVE | Erro nas odds:",
            type(erro).__name__,
            erro
        )

        return

    if not odds:

        print(
            "LIVE | Nenhuma odd recebida."
        )

        return

    for evento in jogos_live:

        if not isinstance(
            evento,
            dict
        ):
            continue

        event_id = evento.get("id")

        if event_id is None:
            continue

        event_id = str(event_id)

        try:

            mercados = (
                extrair_mercados(
                    evento,
                    odds
                )
                or {}
            )

        except Exception as erro:

            print(
                f"LIVE | Mercado inválido "
                f"ID={event_id}: {erro}"
            )

            continue

        if not mercados:
            continue

        dados = {

            "event_id": event_id,

            "casa": evento.get(
                "home",
                "Casa"
            ),

            "fora": evento.get(
                "away",
                "Fora"
            ),

            "minuto": int(
                numero(
                    mercados.get(
                        "minuto",
                        evento.get(
                            "minute",
                            0
                        )
                    )
                )
            ),

            "placar": mercados.get(
                "gols",
                0
            ),

            "gols": int(
                numero(
                    mercados.get(
                        "gols",
                        0
                    )
                )
            ),

            "odd_casa": numero(
                mercados.get(
                    "odd_casa"
                )
            ),

            "odd_empate": numero(
                mercados.get(
                    "odd_empate"
                )
            ),

            "odd_visitante": numero(
                mercados.get(
                    "odd_visitante"
                )
            ),

            "escanteios": int(
                numero(
                    mercados.get(
                        "escanteios"
                    )
                )
            ),

            "finalizacoes": int(
                numero(
                    mercados.get(
                        "finalizacoes"
                    )
                )
            ),

            "ataques_perigosos": int(
                numero(
                    mercados.get(
                        "ataques_perigosos"
                    )
                )
            ),

            "cartoes": int(
                numero(
                    mercados.get(
                        "cartoes"
                    )
                )
            ),
        }

        if (
            dados["odd_empate"] <= 0
        ):
            continue

        jogo = obter_jogo(
            event_id
        )

        registrar_leitura(
            jogo,
            dados
        )

        print(
            f"LIVE | "
            f"{dados['minuto']}' | "
            f"{dados['casa']} x "
            f"{dados['fora']} | "
            f"X={dados['odd_empate']:.2f} | "
            f"GOLS={dados['gols']}"
        )

        if detectar_gol(jogo):

            print(
                f"⚽ GOL DETECTADO | "
                f"ID={event_id}"
            )

            continue

        analise = analisar_padrao(
            jogo
        )

        if not analise["sinal"]:
            continue

        if jogo.get(
            "sinal_enviado",
            False
        ):
            continue

        variaveis = calcular_variaveis(
            jogo
        )

        mensagem = formatar_sinal(
            dados,
            variaveis,
            analise
        )

        try:

            enviado = enviar_mensagem(
                mensagem
            )

        except Exception as erro:

            print(
                f"LIVE | Erro Telegram "
                f"ID={event_id}: {erro}"
            )

            enviado = False

        if enviado:

            jogo["sinal_enviado"] = True

            print(
                f"🚨 SINAL ENVIADO | "
                f"ID={event_id}"
            )
