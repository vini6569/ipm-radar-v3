# ============================================================
# MONITOR LIVE - IPM RADAR V5.0
# ANÁLISE DE GOL + SINAL DE ACOMPANHAMENTO
# ============================================================

import time
from odds_api import (
    buscar_jogos_ao_vivo_por_ids,
    buscar_odds_multiplos,
    extrair_mercados,
)
from telegram import enviar_mensagem


INTERVALO_LIVE = 60

# ------------------------------------------------------------
# HISTÓRICO DOS JOGOS
# ------------------------------------------------------------

HISTORICO_LIVE = {}


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
# REGISTRO DA LEITURA LIVE
# ============================================================

def registrar_leitura(dados):
    event_id = str(dados["event_id"])

    jogo = obter_jogo(event_id)

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

    # Mantém somente as últimas 30 leituras
    jogo["historico"] = jogo["historico"][-30:]

    jogo["ultima_leitura"] = leitura

    return leitura


# ============================================================
# FAIXA DE ODDS
# ============================================================

def faixa_odd(odd):

    odd = numero(odd)

    if odd < 1.40:
        return "<1.40"

    if odd < 1.70:
        return "1.40-1.69"

    if odd < 2.00:
        return "1.70-1.99"

    if odd < 2.50:
        return "2.00-2.49"

    if odd < 3.00:
        return "2.50-2.99"

    if odd < 4.00:
        return "3.00-3.99"

    return "4.00+"


# ============================================================
# MOVIMENTAÇÃO DA ODD
# ============================================================

def obter_leitura_anterior(jogo, minutos=5):

    historico = jogo.get("historico", [])

    if len(historico) < 2:
        return None

    atual = historico[-1]
    limite = atual["timestamp"] - (minutos * 60)

    candidatos = [
        item
        for item in historico[:-1]
        if item["timestamp"] <= limite
    ]

    if not candidatos:
        return None

    return candidatos[-1]


def calcular_variacao(base, atual):

    base = numero(base)
    atual = numero(atual)

    if base <= 0 or atual <= 0:
        return 0.0

    return ((atual - base) / base) * 100


# ============================================================
# VARIÁVEIS DE GOL
# ============================================================

def calcular_variaveis_gol(jogo):

    atual = jogo["ultima_leitura"]

    anterior_5 = obter_leitura_anterior(jogo, 5)

    if anterior_5:

        variacao_casa = calcular_variacao(
            anterior_5["odd_casa"],
            atual["odd_casa"]
        )

        variacao_x = calcular_variacao(
            anterior_5["odd_empate"],
            atual["odd_empate"]
        )

        variacao_visitante = calcular_variacao(
            anterior_5["odd_visitante"],
            atual["odd_visitante"]
        )

    else:

        variacao_casa = 0.0
        variacao_x = 0.0
        variacao_visitante = 0.0

    return {
        "minuto": atual["minuto"],
        "gols": atual["gols"],

        "odd_casa": atual["odd_casa"],
        "odd_empate": atual["odd_empate"],
        "odd_visitante": atual["odd_visitante"],

        "faixa_casa": faixa_odd(
            atual["odd_casa"]
        ),

        "faixa_visitante": faixa_odd(
            atual["odd_visitante"]
        ),

        "variacao_casa_5m": variacao_casa,
        "variacao_x_5m": variacao_x,
        "variacao_visitante_5m": variacao_visitante,

        "escanteios": atual["escanteios"],
        "finalizacoes": atual["finalizacoes"],
        "ataques_perigosos": atual["ataques_perigosos"],
        "cartoes": atual["cartoes"],
    }


# ============================================================
# DETECÇÃO DE GOL
# ============================================================

def detectar_gol(jogo):

    atual = jogo["ultima_leitura"]

    gols_atual = atual["gols"]

    gols_anterior = jogo.get(
        "gol_anterior",
        gols_atual
    )

    jogo["gol_anterior"] = gols_atual

    return gols_atual > gols_anterior


# ============================================================
# ANÁLISE DO PADRÃO
# ============================================================

def analisar_padrao_gol(jogo):

    v = calcular_variaveis_gol(jogo)

    minuto = v["minuto"]
    gols = v["gols"]

    # --------------------------------------------------------
    # Não gerar sinal depois de gol
    # --------------------------------------------------------

    if gols > 0:
        return {
            "sinal": False,
            "motivo": "JOGO JA POSSUI GOL"
        }

    # --------------------------------------------------------
    # Nosso primeiro estudo:
    # pelo menos uma das pontas em odd >= 2.00
    # --------------------------------------------------------

    odd_2_plus = (
        v["odd_casa"] >= 2.00
        or
        v["odd_visitante"] >= 2.00
    )

    if not odd_2_plus:
        return {
            "sinal": False,
            "motivo": "ODDS DAS PONTAS ABAIXO DE 2.00"
        }

    # --------------------------------------------------------
    # Faixa de observação
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Variável de pressão
    # --------------------------------------------------------

    pressao = (
        v["escanteios"]
        + v["finalizacoes"]
        + v["ataques_perigosos"]
    )

    # --------------------------------------------------------
    # PRIMEIRA VERSÃO DO PADRÃO
    # --------------------------------------------------------

    condicao_odd = odd_2_plus

    condicao_pressao = pressao > 0

    if condicao_odd and condicao_pressao:

        return {
            "sinal": True,
            "motivo": "ODD_2_PLUS + VARIAVEL_DE_PRESSAO"
        }

    return {
        "sinal": False,
        "motivo": "PADRAO AINDA NAO CONFIRMADO"
    }


# ============================================================
# FORMATAR SINAL
# ============================================================

def formatar_sinal(
    jogo,
    variaveis,
    analise
):

    return (
        "🚨 SINAL DE GOL — ACOMPANHAR\n\n"

        f"⚽ {jogo['casa']} x {jogo['fora']}\n"
        f"⏱️ Minuto: {variaveis['minuto']}'\n"
        f"📊 Placar: {variaveis['gols']} gols\n\n"

        "📈 ODDS\n"
        f"🏠 Casa: {variaveis['odd_casa']:.2f} "
        f"({variaveis['faixa_casa']})\n"

        f"🤝 X: {variaveis['odd_empate']:.2f}\n"

        f"🚌 Visitante: {variaveis['odd_visitante']:.2f} "
        f"({variaveis['faixa_visitante']})\n\n"

        "📉 MOVIMENTAÇÃO 5 MIN\n"
        f"Casa: {variaveis['variacao_casa_5m']:+.2f}%\n"
        f"X: {variaveis['variacao_x_5m']:+.2f}%\n"
        f"Visitante: "
        f"{variaveis['variacao_visitante_5m']:+.2f}%\n\n"

        "🔥 VARIÁVEIS DE GOL\n"
        f"⚽ Finalizações: {variaveis['finalizacoes']}\n"
        f"🔥 Ataques perigosos: "
        f"{variaveis['ataques_perigosos']}\n"
        f"🚩 Escanteios: {variaveis['escanteios']}\n"
        f"🟨 Cartões: {variaveis['cartoes']}\n\n"

        f"🧪 Padrão: {analise['motivo']}\n\n"

        "👁️ ENTRADA PARA ACOMPANHAMENTO\n"
        "⚠️ Sinal estatístico — não realiza aposta automaticamente."
    )


# ============================================================
# PROCESSAMENTO LIVE
# ============================================================

def processar_live(ids):

    if not ids:
        print("LIVE | Nenhum ID para monitorar.")
        return

    print(
        f"🧪 LIVE | Monitorando {len(ids)} jogos"
    )

    jogos_live = buscar_jogos_ao_vivo_por_ids(ids)

    if not jogos_live:
        print(
            "LIVE | Nenhum dos IDs está atualmente ao vivo."
        )
        return

    odds = buscar_odds_multiplos(
        jogos_live
    )

    if not odds:
        print(
            "LIVE | Nenhuma odd recebida."
        )
        return

    for evento in jogos_live:

        event_id = str(evento["id"])

        mercados = extrair_mercados(
            evento,
            odds
        )

        if not mercados:
            continue

        jogo = obter_jogo(event_id)

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
                        0
                    )
                )
            ),

            "placar": mercados.get(
                "gols",
                0
            ),

            "gols": mercados.get(
                "gols",
                0
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

        registrar_leitura(dados)

        print(
            "LIVE | "
            f"{dados['minuto']}' | "
            f"{dados['casa']} x "
            f"{dados['fora']} | "
            f"GOLS={dados['gols']} | "
            f"CASA={dados['odd_casa']:.2f} | "
            f"X={dados['odd_empate']:.2f} | "
            f"FORA={dados['odd_visitante']:.2f} | "
            f"FINALIZACOES={dados['finalizacoes']} | "
            f"ATAQUES={dados['ataques_perigosos']}"
        )

        # ----------------------------------------------------
        # Detecta gol
        # ----------------------------------------------------

        if detectar_gol(jogo):

            print(
                "⚽ GOL DETECTADO | "
                f"{dados['casa']} x "
                f"{dados['fora']}"
            )

            # Não gerar entrada depois do gol
            continue

        # ----------------------------------------------------
        # Analisa padrão
        # ----------------------------------------------------

        analise = analisar_padrao_gol(
            jogo
        )

        if not analise["sinal"]:
            continue

        if jogo.get("sinal_enviado"):
            continue

        variaveis = calcular_variaveis_gol(
            jogo
        )

        mensagem = formatar_sinal(
            dados,
            variaveis,
            analise
        )

        if enviar_mensagem(mensagem):

            jogo["sinal_enviado"] = True

            print(
                "🚨 SINAL ENVIADO | "
                f"{dados['casa']} x "
                f"{dados['fora']}"
)
