# ============================================================
# MAIN - IPM RADAR | PRÉ-LIVE + MONITORAMENTO
# ============================================================

import os
import time
from datetime import datetime, timezone

from config import horario_ativo

from scanner_pre_live import escanear_pre_live

from odds_api import (
    buscar_jogos_ao_vivo_por_ids,
    buscar_odds_multiplos,
    extrair_mercados,
)

from telegram import enviar_mensagem


# ============================================================
# CONFIGURAÇÕES
# ============================================================

INTERVALO_RADAR = int(
    os.getenv(
        "INTERVALO_RADAR",
        "300",
    )
)

Q_MIN = float(
    os.getenv(
        "Q_PRE_LIVE_MINIMO",
        "2.30",
    )
)

Q_MAX = float(
    os.getenv(
        "Q_PRE_LIVE_MAXIMO",
        "3.00",
    )
)

VARIACAO_MINIMA = float(
    os.getenv(
        "PRE_ENTRADA_VARIACAO",
        "20.0",
    )
)

JANELA_VARIACAO_MINUTOS = 10

CONFIRMACAO_MINUTOS = 5

TELEGRAM_MAX_CARACTERES = 3800


# ============================================================
# MEMÓRIA
# ============================================================

ULTIMA_LISTA = None

JOGOS_MONITORADOS = {}

SINAIS_PRE_ENTRADA = {}


# ============================================================
# FILTRAR Q
# ============================================================

def filtrar_por_q(resultados):

    aprovados = []

    for jogo in resultados:

        try:

            q = float(
                jogo.get(
                    "odd_pre_live",
                    jogo.get("q", 0),
                )
                or 0
            )

        except (TypeError, ValueError):

            continue

        if Q_MIN <= q <= Q_MAX:
            aprovados.append(jogo)

    return aprovados


# ============================================================
# REGISTRAR JOGOS PRÉ-LIVE
# ============================================================

def registrar_jogos_monitorados(jogos):

    agora = time.time()

    for jogo in jogos:

        event_id = jogo.get("event_id")

        if event_id is None:
            continue

        event_id = str(event_id)

        if event_id not in JOGOS_MONITORADOS:

            JOGOS_MONITORADOS[event_id] = {
                "event_id": event_id,
                "casa": jogo.get(
                    "casa",
                    "Casa",
                ),
                "fora": jogo.get(
                    "fora",
                    "Fora",
                ),
                "q": float(
                    jogo.get(
                        "q",
                        0,
                    )
                    or 0
                ),
                "odd_pre_live": float(
                    jogo.get(
                        "odd_empate",
                        0,
                    )
                    or 0
                ),
                "criado_em": agora,
                "historico": [],
                "primeiro_sinal": None,
                "confirmado": False,
            }


# ============================================================
# REGISTRAR ODD X
# ============================================================

def registrar_odd_x(event_id, odd_x):

    if odd_x <= 0:
        return

    jogo = JOGOS_MONITORADOS.get(
        str(event_id)
    )

    if not jogo:
        return

    agora = time.time()

    jogo["historico"].append(
        {
            "timestamp": agora,
            "odd_x": odd_x,
        }
    )

    limite = (
        agora
        - (
            JANELA_VARIACAO_MINUTOS
            * 60
        )
    )

    jogo["historico"] = [
        ponto
        for ponto in jogo["historico"]
        if ponto["timestamp"] >= limite
    ]


# ============================================================
# ENCONTRAR ODD DE 10 MINUTOS
# ============================================================

def obter_odd_base_10_min(event_id):

    jogo = JOGOS_MONITORADOS.get(
        str(event_id)
    )

    if not jogo:
        return 0.0

    historico = jogo.get(
        "historico",
        [],
    )

    if len(historico) < 2:
        return 0.0

    agora = time.time()

    alvo = (
        agora
        - (
            JANELA_VARIACAO_MINUTOS
            * 60
        )
    )

    melhor = None

    for ponto in historico:

        distancia = abs(
            ponto["timestamp"]
            - alvo
        )

        if melhor is None:
            melhor = (
                distancia,
                ponto,
            )

        elif distancia < melhor[0]:
            melhor = (
                distancia,
                ponto,
            )

    if melhor is None:
        return 0.0

    return float(
        melhor[1]["odd_x"]
    )


# ============================================================
# CALCULAR VARIAÇÃO
# ============================================================

def calcular_variacao(
    odd_base,
    odd_atual,
):

    if (
        odd_base <= 0
        or odd_atual <= 0
    ):
        return 0.0

    return (
        (
            odd_atual
            - odd_base
        )
        / odd_base
    ) * 100.0


# ============================================================
# DIREÇÃO
# ============================================================

def identificar_direcao(
    variacao,
):

    if variacao >= VARIACAO_MINIMA:
        return "POSITIVO"

    if variacao <= -VARIACAO_MINIMA:
        return "NEGATIVO"

    return None


# ============================================================
# PRIMEIRO SINAL
# ============================================================

def verificar_primeiro_sinal(
    event_id,
    minuto,
    odd_x,
):

    jogo = JOGOS_MONITORADOS.get(
        str(event_id)
    )

    if not jogo:
        return

    if jogo["primeiro_sinal"] is not None:
        return

    odd_base = obter_odd_base_10_min(
        event_id
    )

    if odd_base <= 0:
        return

    variacao = calcular_variacao(
        odd_base,
        odd_x,
    )

    direcao = identificar_direcao(
        variacao
    )

    if direcao is None:
        return

    jogo["primeiro_sinal"] = {
        "timestamp": time.time(),
        "minuto": minuto,
        "odd_base": odd_base,
        "odd_x": odd_x,
        "variacao": variacao,
        "direcao": direcao,
    }

    print(
        "🚨 PRIMEIRO SINAL | "
        f"{jogo['casa']} x "
        f"{jogo['fora']} | "
        f"{direcao} | "
        f"{variacao:+.2f}%"
    )


# ============================================================
# CONFIRMAÇÃO APÓS 5 MINUTOS
# ============================================================

def verificar_confirmacao(
    event_id,
    minuto,
    odd_x,
):

    jogo = JOGOS_MONITORADOS.get(
        str(event_id)
    )

    if not jogo:
        return None

    sinal = jogo.get(
        "primeiro_sinal"
    )

    if not sinal:
        return None

    if jogo.get("confirmado"):
        return None

    agora = time.time()

    passado = (
        agora
        - sinal["timestamp"]
    )

    if passado < (
        CONFIRMACAO_MINUTOS * 60
    ):
        return None

    variacao = calcular_variacao(
        sinal["odd_base"],
        odd_x,
    )

    direcao_atual = identificar_direcao(
        variacao
    )

    if direcao_atual != sinal["direcao"]:

        print(
            "❌ SINAL NÃO CONFIRMADO | "
            f"{jogo['casa']} x "
            f"{jogo['fora']} | "
            f"direção mudou."
        )

        jogo["primeiro_sinal"] = None

        return None

    jogo["confirmado"] = True

    resultado = {
        "event_id": event_id,
        "casa": jogo["casa"],
        "fora": jogo["fora"],
        "minuto": minuto,
        "direcao": direcao_atual,
        "variacao_inicial": sinal[
            "variacao"
        ],
        "variacao_confirmada": variacao,
        "odd_x": odd_x,
    }

    print(
        "🚨 PRÉ-ENTRADA CONFIRMADA | "
        f"{jogo['casa']} x "
        f"{jogo['fora']} | "
        f"{direcao_atual}"
    )

    return resultado


# ============================================================
# PROCESSAR LIVE
# ============================================================

def processar_live():

    ids = list(
        JOGOS_MONITORADOS.keys()
    )

    if not ids:
        return

    jogos_live = (
        buscar_jogos_ao_vivo_por_ids(
            ids
        )
        or []
    )

    if not jogos_live:
        return

    odds = (
        buscar_odds_multiplos(
            jogos_live
        )
        or []
    )

    for jogo in jogos_live:

        event_id = jogo.get("id")

        if event_id is None:
            continue

        mercados = (
            extrair_mercados(
                jogo,
                odds,
            )
            or {}
        )

        odd_x = float(
            mercados.get(
                "odd_empate",
                0,
            )
            or 0
        )

        if odd_x <= 0:
            continue

        minuto = int(
            mercados.get(
                "minuto",
                0,
            )
            or 0
        )

        registrar_odd_x(
            event_id,
            odd_x
        )

        verificar_primeiro_sinal(
            event_id,
            minuto,
            odd_x,
        )

        confirmacao = (
            verificar_confirmacao(
                event_id,
                minuto,
                odd_x,
            )
        )

        if confirmacao:

            enviar_mensagem(
                formatar_pre_entrada(
                    confirmacao
                )
            )


# ============================================================
# MENSAGEM DA PRÉ-ENTRADA
# ============================================================

def formatar_pre_entrada(
    dados
):

    return (
        "🚨 PRÉ-ENTRADA CONFIRMADA\n"
        "\n"
        f"⚽ {dados['casa']} x "
        f"{dados['fora']}\n"
        f"⏱️ Minuto: "
        f"{dados['minuto']}'\n"
        "\n"
        "📊 MONITORAMENTO DA ODD X\n"
        f"📉 Primeiro sinal: "
        f"{dados['variacao_inicial']:+.2f}%\n"
        f"📈 Confirmação: "
        f"{dados['variacao_confirmada']:+.2f}%\n"
        f"🎯 Odd X atual: "
        f"{dados['odd_x']:.2f}\n"
        f"🚦 Direção: "
        f"{dados['direcao']}\n"
        "\n"
        "🧪 LABORATÓRIO IPM\n"
        "⚠️ Sinal estatístico para "
        "observação. Não realiza apostas."
    )


# ============================================================
# EXECUTAR PRÉ-LIVE
# ============================================================

def executar_pre_live():

    print()
    print("=" * 72)
    print("🧪 PRÉ-LIVE | IPM RADAR")
    print(
        f"Q: {Q_MIN:.2f} → {Q_MAX:.2f}"
    )
    print("=" * 72)

    try:

        resultados = (
            escanear_pre_live()
            or []
        )

    except Exception as erro:

        print(
            "ERRO NO SCANNER:",
            type(erro).__name__,
            erro,
        )

        return

    aprovados = filtrar_por_q(
        resultados
    )

    print(
        "JOGOS APROVADOS:",
        len(aprovados)
    )

    if not aprovados:

        print(
            "Nenhum jogo dentro da faixa Q."
        )

        return

    registrar_jogos_monitorados(
        aprovados
    )

    global ULTIMA_LISTA

    assinatura = tuple(
        (
            jogo.get("event_id"),
            jogo.get("odd_empate"),
            jogo.get("q"),
        )
        for jogo in aprovados
    )

    if assinatura == ULTIMA_LISTA:

        print(
            "Lista igual à anterior."
        )

        return

    mensagens = montar_mensagens(
        aprovados
    )

    for mensagem in mensagens:

        if enviar_mensagem(
            mensagem
        ):

            print(
                "✅ LISTA PRÉ-LIVE ENVIADA."
            )

    ULTIMA_LISTA = assinatura


# ============================================================
# FORMATAR LISTA
# ============================================================

def montar_mensagens(resultados):

    mensagens = []

    linhas = [
        "🧪 PRÉ-LIVE — IPM RADAR",
        "",
        f"📐 Q: {Q_MIN:.2f} até {Q_MAX:.2f}",
        "",
    ]

    ultimo_dia = None

    for jogo in resultados:

        data = jogo.get(
            "data",
            "",
        )

        if data != ultimo_dia:

            if ultimo_dia is not None:
                linhas.append("")

            linhas.append(
                f"📅 {data}"
            )

            ultimo_dia = data

        linhas.extend(
            [
                (
                    f"⚽ {jogo.get('horario', '--:--')} | "
                    f"{jogo.get('casa', 'Casa')} x "
                    f"{jogo.get('fora', 'Fora')}"
                ),
                (
                    f"🏠 {float(jogo.get('odd_casa', 0) or 0):.2f} | "
                    f"🤝 X {float(jogo.get('odd_empate', 0) or 0):.2f} | "
                    f"🚌 {float(jogo.get('odd_visitante', 0) or 0):.2f}"
                ),
                (
                    f"📐 Q: "
                    f"{float(jogo.get('q', 0) or 0):.2f}"
                ),
                (
                    f"📊 P(X): "
                    f"{float(jogo.get('probabilidade_x', 0) or 0):.2f}% | "
                    f"P(X) N: "
                    f"{float(jogo.get('probabilidade_x_normalizada', 0) or 0):.2f}%"
                ),
                "",
            ]
        )

        if len("\n".join(linhas)) > 3500:

            mensagens.append(
                "\n".join(linhas)
            )

            linhas = [
                "🧪 PRÉ-LIVE — IPM RADAR",
                "",
                f"📐 Q: {Q_MIN:.2f} até {Q_MAX:.2f}",
                "",
            ]

    if len(linhas) > 4:

        mensagens.append(
            "\n".join(linhas)
        )

    return mensagens


# ============================================================
# LOOP
# ============================================================

def loop_consulta():

    print(
        "🤖 IPM RADAR INICIADO"
    )

    print(
        f"Q: {Q_MIN:.2f} → {Q_MAX:.2f}"
    )

    print(
        f"INTERVALO: {INTERVALO_RADAR}s"
    )

    while True:

        inicio = time.time()

        try:

            if horario_ativo():

                executar_pre_live()

                processar_live()

            else:

                print(
                    "Radar em período de pausa."
                )

        except Exception as erro:

            print(
                "ERRO NO LOOP:",
                type(erro).__name__,
                erro,
            )

        decorrido = (
            time.time()
            - inicio
        )

        espera = max(
            1,
            INTERVALO_RADAR
            - decorrido,
        )

        print(
            f"PRÓXIMO CICLO EM "
            f"{espera:.0f}s"
        )

        time.sleep(
            espera
        )


# ============================================================
# INÍCIO
# ============================================================

if __name__ == "__main__":

    loop_consulta()
