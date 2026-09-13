# ============================================================
# LIVE - IPM RADAR V5.2
# PREVISÃO ANTECIPADA DE GOL
# ============================================================

import time

from odds_api_live import (
    buscar_jogos_ao_vivo_por_ids,
    buscar_odds_multiplos,
    extrair_mercados,
)

from telegram import enviar_mensagem


INTERVALO_LIVE = 60

# Histórico por jogo
HISTORICO = {}

# Evita repetir sinal
SINAL_ENVIADO = {}


# ============================================================
# UTILITÁRIOS
# ============================================================

def numero(valor, padrao=0.0):

    try:

        if valor in (None, ""):
            return padrao

        return float(valor)

    except (TypeError, ValueError):

        return padrao


def obter_jogo(event_id):

    event_id = str(event_id)

    return HISTORICO.setdefault(
        event_id,
        {
            "leituras": [],
            "ultimo_gol": 0,
        }
    )


# ============================================================
# REGISTRAR LEITURA
# ============================================================

def registrar_leitura(event_id, dados):

    jogo = obter_jogo(event_id)

    leitura = {
        "timestamp": time.time(),

        "minuto": dados["minuto"],
        "gols": dados["gols"],

        "odd_casa": dados["odd_casa"],
        "odd_x": dados["odd_x"],
        "odd_fora": dados["odd_fora"],

        "finalizacoes": dados["finalizacoes"],
        "ataques": dados["ataques"],
        "escanteios": dados["escanteios"],
        "cartoes": dados["cartoes"],
    }

    jogo["leituras"].append(leitura)

    # Mantém histórico compacto
    jogo["leituras"] = jogo["leituras"][-30:]

    return leitura


# ============================================================
# LEITURA ANTERIOR
# ============================================================

def leitura_anterior(jogo, minutos):

    historico = jogo["leituras"]

    if len(historico) < 2:
        return None

    atual = historico[-1]

    limite = (
        atual["timestamp"]
        - minutos * 60
    )

    candidatos = [

        x for x in historico[:-1]

        if x["timestamp"] <= limite

    ]

    if not candidatos:
        return None

    return candidatos[-1]


# ============================================================
# VARIAÇÃO
# ============================================================

def variacao(base, atual):

    base = numero(base)
    atual = numero(atual)

    if base <= 0 or atual <= 0:
        return 0.0

    return (
        (atual - base)
        / base
    ) * 100


# ============================================================
# MOVIMENTAÇÃO
# ============================================================

def calcular_movimento(jogo):

    atual = jogo["leituras"][-1]

    antigo = leitura_anterior(
        jogo,
        10
    )

    if not antigo:

        return {
            "casa": 0.0,
            "x": 0.0,
            "fora": 0.0,
        }

    return {

        "casa": variacao(
            antigo["odd_casa"],
            atual["odd_casa"]
        ),

        "x": variacao(
            antigo["odd_x"],
            atual["odd_x"]
        ),

        "fora": variacao(
            antigo["odd_fora"],
            atual["odd_fora"]
        ),
    }


# ============================================================
# PRESSÃO
# ============================================================

def calcular_pressao(dados):

    return (
        numero(dados["finalizacoes"])
        +
        numero(dados["ataques"])
        +
        numero(dados["escanteios"])
    )


# ============================================================
# GOL DETECTADO
# ============================================================

def gol_detectado(jogo):

    atual = jogo["leituras"][-1]

    gols = atual["gols"]

    anterior = jogo["ultimo_gol"]

    jogo["ultimo_gol"] = gols

    return gols > anterior


# ============================================================
# MOTOR DE PREVISÃO
# ============================================================

def analisar_gol(jogo):

    atual = jogo["leituras"][-1]

    minuto = atual["minuto"]
    gols = atual["gols"]

    # --------------------------------------------------------
    # Não trabalhar após gol
    # --------------------------------------------------------

    if gols > 0:

        return {
            "sinal": False,
            "score": 0,
            "motivo": "JA HOUVE GOL",
        }

    # --------------------------------------------------------
    # Janela de observação
    # --------------------------------------------------------

    if minuto < 10:

        return {
            "sinal": False,
            "score": 0,
            "motivo": "MUITO CEDO",
        }

    if minuto > 80:

        return {
            "sinal": False,
            "score": 0,
            "motivo": "FORA DA JANELA",
        }

    movimento = calcular_movimento(
        jogo
    )

    pressao = calcular_pressao(
        atual
    )

    score = 0
    fatores = []

    # --------------------------------------------------------
    # MOVIMENTO DAS ODDS
    # --------------------------------------------------------

    movimentos = [

        movimento["casa"],
        movimento["fora"]

    ]

    # queda forte em uma das pontas
    if min(movimentos) <= -5:

        score += 2

        fatores.append(
            "ODD PONTA -5%"
        )

    # queda moderada
    elif min(movimentos) <= -3:

        score += 1

        fatores.append(
            "ODD PONTA -3%"
        )

    # --------------------------------------------------------
    # MOVIMENTO DO EMPATE
    # --------------------------------------------------------

    if movimento["x"] >= 3:

        score += 1

        fatores.append(
            "X SUBINDO"
        )

    # --------------------------------------------------------
    # PRESSÃO
    # --------------------------------------------------------

    if pressao >= 10:

        score += 2

        fatores.append(
            "PRESSAO ALTA"
        )

    elif pressao >= 5:

        score += 1

        fatores.append(
            "PRESSAO"
        )

    # --------------------------------------------------------
    # CONFIRMAÇÃO
    # --------------------------------------------------------

    if score >= 4:

        return {
            "sinal": True,
            "score": score,
            "motivo": " + ".join(fatores),
        }

    return {
        "sinal": False,
        "score": score,
        "motivo": "SEM CONFIRMACAO",
    }


# ============================================================
# MENSAGEM
# ============================================================

def formatar_sinal(
    dados,
    analise,
    movimento
):

    return (

        "🚨 PRÉ-SINAL DE GOL\n\n"

        f"⚽ {dados['casa']} x "
        f"{dados['fora']}\n"

        f"⏱️ {dados['minuto']}'\n"

        f"📊 Placar: "
        f"{dados['gols']}\n\n"

        "📈 MOVIMENTAÇÃO 10 MIN\n"

        f"🏠 Casa: "
        f"{movimento['casa']:+.2f}%\n"

        f"🤝 X: "
        f"{movimento['x']:+.2f}%\n"

        f"🚌 Fora: "
        f"{movimento['fora']:+.2f}%\n\n"

        "🔥 PRESSÃO\n"

        f"🎯 Finalizações: "
        f"{dados['finalizacoes']}\n"

        f"🔥 Ataques: "
        f"{dados['ataques']}\n"

        f"🚩 Escanteios: "
        f"{dados['escanteios']}\n"

        f"🟨 Cartões: "
        f"{dados['cartoes']}\n\n"

        f"🧪 SCORE: "
        f"{analise['score']}\n"

        f"📌 {analise['motivo']}\n\n"

        "👁️ PRÉ-SINAL — ACOMPANHAR\n"

        "⚠️ Não realiza aposta automaticamente."
    )


# ============================================================
# PROCESSAMENTO
# ============================================================

def processar_live(ids):

    if not ids:

        print(
            "LIVE | Nenhum jogo no radar."
        )

        return

    print(
        f"LIVE | Monitorando {len(ids)} jogos"
    )

    jogos = (
        buscar_jogos_ao_vivo_por_ids(
            ids
        )
        or []
    )

    if not jogos:

        print(
            "LIVE | Nenhum jogo ao vivo."
        )

        return

    odds = (
        buscar_odds_multiplos(
            jogos
        )
        or []
    )

    if not odds:

        print(
            "LIVE | Nenhuma odds."
        )

        return

    for evento in jogos:

        event_id = str(
            evento["id"]
        )

        mercados = (
            extrair_mercados(
                evento,
                odds
            )
            or {}
        )

        if not mercados:
            continue

        dados = {

            "casa":
                evento.get(
                    "home",
                    "Casa"
                ),

            "fora":
                evento.get(
                    "away",
                    "Fora"
                ),

            "minuto":
                int(
                    numero(
                        mercados.get(
                            "minuto"
                        )
                    )
                ),

            "gols":
                int(
                    numero(
                        mercados.get(
                            "gols"
                        )
                    )
                ),

            "odd_casa":
                numero(
                    mercados.get(
                        "odd_casa"
                    )
                ),

            "odd_x":
                numero(
                    mercados.get(
                        "odd_empate"
                    )
                ),

            "odd_fora":
                numero(
                    mercados.get(
                        "odd_visitante"
                    )
                ),

            "finalizacoes":
                int(
                    numero(
                        mercados.get(
                            "finalizacoes"
                        )
                    )
                ),

            "ataques":
                int(
                    numero(
                        mercados.get(
                            "ataques_perigosos"
                        )
                    )
                ),

            "escanteios":
                int(
                    numero(
                        mercados.get(
                            "escanteios"
                        )
                    )
                ),

            "cartoes":
                int(
                    numero(
                        mercados.get(
                            "cartoes"
                        )
                    )
                ),
        }

        jogo = obter_jogo(
            event_id
        )

        registrar_leitura(
            event_id,
            dados
        )

        # ----------------------------------------------------
        # GOL
        # ----------------------------------------------------

        if gol_detectado(jogo):

            print(
                f"⚽ GOL | "
                f"{dados['casa']} x "
                f"{dados['fora']}"
            )

            continue

        # ----------------------------------------------------
        # ANÁLISE
        # ----------------------------------------------------

        analise = analisar_gol(
            jogo
        )

        print(
            f"LIVE | "
            f"{dados['minuto']}' | "
            f"{dados['casa']} x "
            f"{dados['fora']} | "
            f"SCORE={analise['score']} | "
            f"{analise['motivo']}"
        )

        if not analise["sinal"]:
            continue

        if SINAL_ENVIADO.get(
            event_id,
            False
        ):

            continue

        movimento = calcular_movimento(
            jogo
        )

        mensagem = formatar_sinal(
            dados,
            analise,
            movimento
        )

        if enviar_mensagem(
            mensagem
        ):

            SINAL_ENVIADO[
                event_id
            ] = True

            print(
                "🚨 PRÉ-SINAL ENVIADO | "
                f"ID={event_id}"
        )
