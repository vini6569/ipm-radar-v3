# ============================================================
# MAIN - IPM RADAR | PRÉ-LIVE + MONITORAMENTO
# ============================================================

import os
import time

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

# Janela utilizada para comparação da Odd X.
JANELA_VARIACAO_MINUTOS = 10

# Tempo entre primeiro sinal e confirmação.
CONFIRMACAO_MINUTOS = 5

# Mantemos memória um pouco maior que 10 minutos
# para garantir que a referência de 10 minutos
# não seja apagada antes da comparação.
MEMORIA_ODD_MINUTOS = 15

TELEGRAM_MAX_CARACTERES = 3800


# ============================================================
# MEMÓRIA
# ============================================================

ULTIMA_LISTA = None

JOGOS_MONITORADOS = {}

SINAIS_PRE_ENTRADA = {}


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


def calcular_valores_equilibrio(r):

    """
    R = maior odd / menor odd.

    Equilíbrio:
        100 / R

    Desequilíbrio:
        100 - equilíbrio

    É um índice estrutural das duas pontas.
    NÃO é probabilidade de empate.
    NÃO é probabilidade de gol.
    """

    r = numero(r)

    if r <= 0:
        return 0.0, 0.0

    equilibrio = 100.0 / r

    desequilibrio = 100.0 - equilibrio

    return (
        round(equilibrio, 2),
        round(desequilibrio, 2),
    )


def obter_equilibrio_jogo(jogo):

    r = numero(
        jogo.get(
            "r",
            0,
        )
    )

    equilibrio = numero(
        jogo.get(
            "equilibrio_percentual",
            0,
        )
    )

    desequilibrio = numero(
        jogo.get(
            "desequilibrio_percentual",
            0,
        )
    )

    if equilibrio <= 0 and desequilibrio <= 0:

        equilibrio, desequilibrio = (
            calcular_valores_equilibrio(r)
        )

    return (
        equilibrio,
        desequilibrio,
    )


# ============================================================
# FILTRAR Q
# ============================================================

def filtrar_por_q(resultados):

    aprovados = []

    for jogo in resultados:

        q = numero(
            jogo.get(
                "odd_pre_live",
                jogo.get(
                    "q",
                    0,
                ),
            )
        )

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

                "q": numero(
                    jogo.get(
                        "q",
                        0,
                    )
                ),

                "odd_pre_live": numero(
                    jogo.get(
                        "odd_empate",
                        0,
                    )
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

    odd_x = numero(odd_x)

    if odd_x <= 0:
        return

    jogo = JOGOS_MONITORADOS.get(
        str(event_id)
    )

    if not jogo:
        return

    agora = time.time()

    ponto = {
        "timestamp": agora,
        "odd_x": odd_x,
    }

    jogo.setdefault(
        "historico",
        []
    )

    jogo["historico"].append(ponto)

    # --------------------------------------------------------
    # Mantém memória suficiente para encontrar a referência
    # de aproximadamente 10 minutos.
    # --------------------------------------------------------

    limite = (
        agora
        - (
            MEMORIA_ODD_MINUTOS
            * 60
        )
    )

    jogo["historico"] = [
        ponto
        for ponto in jogo["historico"]
        if ponto["timestamp"] >= limite
    ]


# ============================================================
# ENCONTRAR ODD DE REFERÊNCIA DE 10 MINUTOS
# ============================================================

def obter_odd_base_10_min(event_id):

    jogo = JOGOS_MONITORADOS.get(
        str(event_id)
    )

    if not jogo:
        return 0.0

    historico = jogo.get(
        "historico",
        []
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

    # --------------------------------------------------------
    # Procuramos o último ponto registrado ANTES ou no alvo
    # de 10 minutos.
    #
    # Assim não usamos uma cotação futura como referência.
    # --------------------------------------------------------

    pontos_validos = [
        ponto
        for ponto in historico
        if ponto["timestamp"] <= alvo
    ]

    if not pontos_validos:
        return 0.0

    ponto_base = max(
        pontos_validos,
        key=lambda ponto: ponto["timestamp"]
    )

    return numero(
        ponto_base["odd_x"]
    )


# ============================================================
# CALCULAR VARIAÇÃO
# ============================================================

def calcular_variacao(
    odd_base,
    odd_atual,
):

    odd_base = numero(odd_base)

    odd_atual = numero(odd_atual)

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

def identificar_direcao(variacao):

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

    # Já existe um sinal aguardando confirmação.
    if jogo.get("primeiro_sinal") is not None:
        return

    # Jogo já confirmou.
    if jogo.get("confirmado"):
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

    SINAIS_PRE_ENTRADA[str(event_id)] = (
        jogo["primeiro_sinal"]
    )

    print(
        "🚨 PRIMEIRO SINAL | "
        f"{jogo['casa']} x "
        f"{jogo['fora']} | "
        f"{direcao} | "
        f"{variacao:+.2f}% | "
        f"BASE {odd_base:.2f} → "
        f"ATUAL {odd_x:.2f}"
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
        CONFIRMACAO_MINUTOS
        * 60
    ):
        return None

    variacao = calcular_variacao(
        sinal["odd_base"],
        odd_x,
    )

    direcao_atual = identificar_direcao(
        variacao
    )

    # --------------------------------------------------------
    # Confirma somente se a direção continuar igual
    # e continuar acima do limite mínimo.
    # --------------------------------------------------------

    if direcao_atual != sinal["direcao"]:

        print(
            "❌ SINAL NÃO CONFIRMADO | "
            f"{jogo['casa']} x "
            f"{jogo['fora']} | "
            f"Direção mudou ou ficou abaixo de "
            f"{VARIACAO_MINIMA:.2f}%."
        )

        jogo["primeiro_sinal"] = None

        SINAIS_PRE_ENTRADA.pop(
            str(event_id),
            None,
        )

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

        "odd_base": sinal[
            "odd_base"
        ],

        "odd_x": odd_x,
    }

    print(
        "🚨 PRÉ-ENTRADA CONFIRMADA | "
        f"{jogo['casa']} x "
        f"{jogo['fora']} | "
        f"{direcao_atual} | "
        f"{variacao:+.2f}%"
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

        event_id = str(event_id)

        mercados = (
            extrair_mercados(
                jogo,
                odds,
            )
            or {}
        )

        odd_x = numero(
            mercados.get(
                "odd_empate",
                0,
            )
        )

        if odd_x <= 0:
            continue

        minuto = int(
            numero(
                mercados.get(
                    "minuto",
                    0,
                )
            )
        )

        # ----------------------------------------------------
        # PRIMEIRO:
        # registra a cotação atual.
        # ----------------------------------------------------

        registrar_odd_x(
            event_id,
            odd_x,
        )

        # ----------------------------------------------------
        # SEGUNDO:
        # procura um sinal de ±20% em relação
        # à referência de 10 minutos.
        # ----------------------------------------------------

        verificar_primeiro_sinal(
            event_id,
            minuto,
            odd_x,
        )

        # ----------------------------------------------------
        # TERCEIRO:
        # se houver sinal anterior, verifica a confirmação
        # depois de 5 minutos.
        # ----------------------------------------------------

        confirmacao = verificar_confirmacao(
            event_id,
            minuto,
            odd_x,
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

def formatar_pre_entrada(dados):

    odd_base = numero(
        dados.get(
            "odd_base",
            0,
        )
    )

    odd_atual = numero(
        dados.get(
            "odd_x",
            0,
        )
    )

    variacao_inicial = numero(
        dados.get(
            "variacao_inicial",
            0,
        )
    )

    variacao_confirmada = numero(
        dados.get(
            "variacao_confirmada",
            0,
        )
    )

    return (
        "🚨 PRÉ-ENTRADA CONFIRMADA\n"
        "\n"
        f"⚽ {dados['casa']} x "
        f"{dados['fora']}\n"
        f"⏱️ Minuto: "
        f"{dados['minuto']}'\n"
        "\n"
        "📊 MONITORAMENTO DA ODD X\n"
        f"💰 Odd X base (10 min): "
        f"{odd_base:.2f}\n"
        f"💰 Odd X atual: "
        f"{odd_atual:.2f}\n"
        f"📉 Primeiro sinal: "
        f"{variacao_inicial:+.2f}%\n"
        f"📈 Confirmação: "
        f"{variacao_confirmada:+.2f}%\n"
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

    print(
        "🧪 PRÉ-LIVE | IPM RADAR"
    )

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
            jogo.get("r"),
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
# FORMATAR LISTA PRÉ-LIVE
# ============================================================

def montar_mensagens(resultados):

    mensagens = []

    def novo_bloco():

        return [
            "🧪 PRÉ-LIVE — IPM RADAR",
            "",
            (
                f"📐 Q: {Q_MIN:.2f} até "
                f"{Q_MAX:.2f}"
            ),
            (
                "📊 R = desequilíbrio "
                "entre as pontas"
            ),
            "⚖️ Equilíbrio = 100 / R",
            (
                "⚠️ Desequilíbrio = "
                "100 - Equilíbrio"
            ),
            "",
        ]

    linhas = novo_bloco()

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

        odd_casa = numero(
            jogo.get(
                "odd_casa",
                0,
            )
        )

        odd_empate = numero(
            jogo.get(
                "odd_empate",
                0,
            )
        )

        odd_visitante = numero(
            jogo.get(
                "odd_visitante",
                0,
            )
        )

        q = numero(
            jogo.get(
                "q",
                0,
            )
        )

        r = numero(
            jogo.get(
                "r",
                0,
            )
        )

        prob_x = numero(
            jogo.get(
                "probabilidade_x",
                0,
            )
        )

        prob_x_normalizada = numero(
            jogo.get(
                "probabilidade_x_normalizada",
                0,
            )
        )

        equilibrio, desequilibrio = (
            obter_equilibrio_jogo(jogo)
        )

        classificacao = jogo.get(
            "equilibrio",
            "",
        )

        padrao = jogo.get(
            "padrao",
            "",
        )

        linhas.extend(
            [
                (
                    f"⚽ "
                    f"{jogo.get('horario', '--:--')} | "
                    f"{jogo.get('casa', 'Casa')} x "
                    f"{jogo.get('fora', 'Fora')}"
                ),

                (
                    f"🏠 {odd_casa:.2f} | "
                    f"🤝 X {odd_empate:.2f} | "
                    f"🚌 {odd_visitante:.2f}"
                ),

                (
                    f"📐 Q: {q:.2f}"
                ),

                (
                    f"📊 R: {r:.2f}"
                ),

                (
                    f"⚖️ Equilíbrio: "
                    f"{equilibrio:.2f}%"
                ),

                (
                    f"⚠️ Desequilíbrio: "
                    f"{desequilibrio:.2f}%"
                ),

                (
                    f"🎯 Estrutura: "
                    f"{classificacao or 'NÃO CLASSIFICADO'}"
                ),

                (
                    f"🧭 Padrão: "
                    f"{padrao or 'NÃO CLASSIFICADO'}"
                ),

                (
                    f"📊 P(X): {prob_x:.2f}% | "
                    f"P(X) N: "
                    f"{prob_x_normalizada:.2f}%"
                ),

                "",
            ]
        )

        texto = "\n".join(linhas)

        if len(texto) > TELEGRAM_MAX_CARACTERES:

            # ------------------------------------------------
            # Retira o último jogo do bloco que ultrapassou
            # o limite.
            # ------------------------------------------------

            jogo_linhas = [
                (
                    f"⚽ "
                    f"{jogo.get('horario', '--:--')} | "
                    f"{jogo.get('casa', 'Casa')} x "
                    f"{jogo.get('fora', 'Fora')}"
                ),
                (
                    f"🏠 {odd_casa:.2f} | "
                    f"🤝 X {odd_empate:.2f} | "
                    f"🚌 {odd_visitante:.2f}"
                ),
                f"📐 Q: {q:.2f}",
                f"📊 R: {r:.2f}",
                (
                    f"⚖️ Equilíbrio: "
                    f"{equilibrio:.2f}%"
                ),
                (
                    f"⚠️ Desequilíbrio: "
                    f"{desequilibrio:.2f}%"
                ),
                (
                    f"🎯 Estrutura: "
                    f"{classificacao or 'NÃO CLASSIFICADO'}"
                ),
                (
                    f"🧭 Padrão: "
                    f"{padrao or 'NÃO CLASSIFICADO'}"
                ),
                (
                    f"📊 P(X): {prob_x:.2f}% | "
                    f"P(X) N: "
                    f"{prob_x_normalizada:.2f}%"
                ),
                "",
            ]

            # Remove exatamente as linhas do jogo atual.
            linhas = linhas[
                :-len(jogo_linhas)
            ]

            if len(linhas) > 7:

                mensagens.append(
                    "\n".join(linhas)
                )

            linhas = novo_bloco()

            linhas.append(
                f"📅 {data}"
            )

            linhas.extend(
                jogo_linhas
            )

    if len(linhas) > 7:

        linhas.extend(
            [
                "────────────────────",
                (
                    f"📋 Jogos selecionados: "
                    f"{len(resultados)}"
                ),
                "",
                "🤖 IPM-RADAR-V3",
                (
                    "📚 Monitoramento estatístico "
                    "pré-live."
                ),
                (
                    "⚠️ Não realiza apostas "
                    "automaticamente."
                ),
            ]
        )

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

    print(
        f"VARIAÇÃO MÍNIMA: "
        f"{VARIACAO_MINIMA:.2f}%"
    )

    print(
        f"JANELA DE VARIAÇÃO: "
        f"{JANELA_VARIACAO_MINUTOS} minutos"
    )

    print(
        f"CONFIRMAÇÃO: "
        f"{CONFIRMACAO_MINUTOS} minutos"
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
               
