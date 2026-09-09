# ============================================================
# SCANNER PRÉ-LIVE - IPM RADAR V5.0
# ============================================================
#
# Função:
#   - Buscar jogos futuros
#   - Organizar por período
#   - Obter odds 1X2
#   - Calcular P(X)
#   - Calcular P(X) normalizada
#   - Calcular Q
#   - Calcular R
#   - Medir equilíbrio / desequilíbrio
#   - Preparar jogos para o RADAR
#
# NÃO gera entrada.
# NÃO realiza apostas.
# NÃO altera o IPM LIVE.
#
# ============================================================

from datetime import datetime, time

from config import (
    FUSO_HORARIO,
    MAX_EVENTOS_POR_CONSULTA,
    PRE_LIVE_JANELA_MINUTOS,
    Q_MIN,
    Q_MAX,
)

from odds_api import (
    buscar_jogos_pre_live,
    buscar_odds_multiplos,
    extrair_mercados,
)


# ============================================================
# CONVERSÃO NUMÉRICA
# ============================================================

def _numero(valor, padrao=0.0):

    try:

        if valor in (None, ""):
            return padrao

        return float(valor)

    except (TypeError, ValueError):

        return padrao


# ============================================================
# PROBABILIDADE IMPLÍCITA
# ============================================================

def probabilidade_implicita(odd):

    odd = _numero(odd)

    if odd <= 0:
        return 0.0

    return 100.0 / odd


# ============================================================
# PROBABILIDADE NORMALIZADA
# ============================================================

def probabilidade_normalizada(
    odd_casa,
    odd_empate,
    odd_visitante,
):

    pc = probabilidade_implicita(
        odd_casa
    )

    px = probabilidade_implicita(
        odd_empate
    )

    pv = probabilidade_implicita(
        odd_visitante
    )

    total = (
        pc
        + px
        + pv
    )

    if total <= 0:
        return 0.0

    return (
        px / total
    ) * 100.0


# ============================================================
# Q PRÉ-LIVE
# ============================================================
#
# Q = 2 × (W1 × W2) / (W1 + W2)
#
# Mede a região conjunta das duas pontas.
# ============================================================

def calcular_q(
    odd_casa,
    odd_visitante,
):

    casa = _numero(
        odd_casa
    )

    visitante = _numero(
        odd_visitante
    )

    if casa <= 0 or visitante <= 0:
        return 0.0

    soma = (
        casa
        + visitante
    )

    if soma <= 0:
        return 0.0

    return (
        2.0
        * casa
        * visitante
        / soma
    )


# ============================================================
# R PRÉ-LIVE
# ============================================================
#
# R = maior odd / menor odd
#
# R = 1.00
#     equilíbrio máximo
#
# Quanto maior R:
#     maior desequilíbrio.
# ============================================================

def calcular_r(
    odd_casa,
    odd_visitante,
):

    casa = _numero(
        odd_casa
    )

    visitante = _numero(
        odd_visitante
    )

    if casa <= 0 or visitante <= 0:
        return 0.0

    menor = min(
        casa,
        visitante,
    )

    maior = max(
        casa,
        visitante,
    )

    if menor <= 0:
        return 0.0

    return (
        maior
        / menor
    )


# ============================================================
# CLASSIFICAÇÃO DO EQUILÍBRIO
# ============================================================

def classificar_equilibrio(r):

    r = _numero(r)

    if r <= 0:
        return "SEM_DADOS"

    if r <= 1.20:
        return "EQUILÍBRIO MUITO ALTO"

    if r <= 1.50:
        return "EQUILÍBRIO ALTO"

    if r <= 1.80:
        return "EQUILÍBRIO MODERADO"

    if r <= 2.20:
        return "DESEQUILÍBRIO"

    return "DESEQUILÍBRIO ALTO"


# ============================================================
# GRAU DE EQUILÍBRIO
# ============================================================
#
# Não é uma probabilidade.
#
# É apenas um índice interno para facilitar
# a leitura do laboratório.
#
# R = 1.00 → 100
# R maior → índice menor
#
# ============================================================

def calcular_indice_equilibrio(r):

    r = _numero(r)

    if r <= 0:
        return 0.0

    indice = (
        100.0 / r
    )

    return round(
        indice,
        2
    )


# ============================================================
# DIREÇÃO DA HIPÓTESE
# ============================================================

def classificar_padrao(r):

    r = _numero(r)

    if r <= 0:
        return "SEM_DADOS"

    if r <= 1.80:
        return "PADRÃO_EMPATE"

    return "PADRÃO_GOL"


# ============================================================
# PERÍODO DO DIA
# ============================================================

def identificar_periodo(dt):

    hora = dt.time()

    if (
        time(6, 0)
        <= hora
        < time(12, 0)
    ):
        return "06:00 - 12:00"

    if (
        time(12, 0)
        <= hora
        < time(18, 0)
    ):
        return "12:00 - 18:00"

    if (
        time(18, 0)
        <= hora
        or hora < time(0, 0)
    ):
        return "18:00 - 00:00"

    return "FORA_DA_JANELA"


# ============================================================
# CONVERTER HORÁRIO
# ============================================================

def converter_horario(evento):

    valor = (
        evento.get("date")
        or evento.get("startTime")
        or evento.get("start_time")
    )

    if not valor:
        return None

    try:

        texto = str(valor)

        dt = datetime.fromisoformat(
            texto.replace(
                "Z",
                "+00:00"
            )
        )

        if dt.tzinfo is None:

            dt = dt.replace(
                tzinfo=FUSO_HORARIO
            )

        return dt.astimezone(
            FUSO_HORARIO
        )

    except Exception:

        return None


# ============================================================
# SCANNER PRÉ-LIVE
# ============================================================

def escanear_pre_live():

    print()
    print("=" * 72)
    print("🧪 SCANNER PRÉ-LIVE | IPM RADAR V5.0")
    print("=" * 72)

    print(
        f"⏱️ JANELA: "
        f"{PRE_LIVE_JANELA_MINUTOS} minutos"
    )

    print(
        f"📐 Q: "
        f"{Q_MIN:.2f} → {Q_MAX:.2f}"
    )

    print(
        "📊 R: cálculo de equilíbrio/"
        "desequilíbrio"
    )

    # --------------------------------------------------------
    # BUSCAR JOGOS
    # --------------------------------------------------------

    try:

        jogos = (
            buscar_jogos_pre_live()
            or []
        )

    except Exception as erro:

        print(
            "ERRO AO BUSCAR JOGOS:",
            type(erro).__name__,
            erro,
        )

        return []

    if not jogos:

        print(
            "Nenhum jogo pré-live encontrado."
        )

        return []

    jogos = jogos[
        :MAX_EVENTOS_POR_CONSULTA
    ]

    # --------------------------------------------------------
    # BUSCAR ODDS
    # --------------------------------------------------------

    try:

        odds = (
            buscar_odds_multiplos(
                jogos
            )
            or []
        )

    except Exception as erro:

        print(
            "ERRO AO BUSCAR ODDS:",
            type(erro).__name__,
            erro,
        )

        odds = []

    # --------------------------------------------------------
    # RESULTADOS
    # --------------------------------------------------------

    resultados = []

    for jogo in jogos:

        if not isinstance(
            jogo,
            dict
        ):
            continue

        event_id = jogo.get("id")

        if event_id is None:
            continue

        # ----------------------------------------------------
        # MERCADOS
        # ----------------------------------------------------

        mercados = (
            extrair_mercados(
                jogo,
                odds,
            )
            or {}
        )

        odd_casa = _numero(
            mercados.get(
                "odd_casa"
            )
        )

        odd_empate = _numero(
            mercados.get(
                "odd_empate"
            )
        )

        odd_visitante = _numero(
            mercados.get(
                "odd_visitante"
            )
        )

        # ----------------------------------------------------
        # ODDS OBRIGATÓRIAS
        # ----------------------------------------------------

        if (
            odd_casa <= 0
            or odd_empate <= 0
            or odd_visitante <= 0
        ):
            continue

        # ----------------------------------------------------
        # HORÁRIO
        # ----------------------------------------------------

        dt = converter_horario(
            jogo
        )

        if dt is None:
            continue

        periodo = identificar_periodo(
            dt
        )

        if periodo == "FORA_DA_JANELA":
            continue

        # ----------------------------------------------------
        # Q
        # ----------------------------------------------------

        q = calcular_q(
            odd_casa,
            odd_visitante,
        )

        # ----------------------------------------------------
        # FILTRO Q
        # ----------------------------------------------------

        if q < Q_MIN:
            continue

        if q > Q_MAX:
            continue

        # ----------------------------------------------------
        # R
        # ----------------------------------------------------

        r = calcular_r(
            odd_casa,
            odd_visitante,
        )

        if r <= 0:
            continue

        # ----------------------------------------------------
        # EQUILÍBRIO
        # ----------------------------------------------------

        equilibrio = (
            classificar_equilibrio(
                r
            )
        )

        indice_equilibrio = (
            calcular_indice_equilibrio(
                r
            )
        )

        padrao = (
            classificar_padrao(
                r
            )
        )

        # ----------------------------------------------------
        # PROBABILIDADE DO EMPATE
        # ----------------------------------------------------

        prob_x = (
            probabilidade_implicita(
                odd_empate
            )
        )

        prob_x_normalizada = (
            probabilidade_normalizada(
                odd_casa,
                odd_empate,
                odd_visitante,
            )
        )

        # ----------------------------------------------------
        # NOMES
        # ----------------------------------------------------

        casa = (
            jogo.get("home")
            or jogo.get("homeTeam")
            or "Casa"
        )

        fora = (
            jogo.get("away")
            or jogo.get("awayTeam")
            or "Fora"
        )

        # ----------------------------------------------------
        # REGISTRO
        # ----------------------------------------------------

        registro = {

            "event_id": str(
                event_id
            ),

            "data": dt.strftime(
                "%d/%m/%Y"
            ),

            "horario": dt.strftime(
                "%H:%M"
            ),

            "periodo": periodo,

            "casa": casa,

            "fora": fora,

            "odd_casa": odd_casa,

            "odd_empate": odd_empate,

            "odd_visitante": odd_visitante,

            "q": q,

            "r": r,

            "odd_pre_live": q,

            "probabilidade_x": prob_x,

            "probabilidade_x_normalizada":
                prob_x_normalizada,

            # NOVOS DADOS DO RADAR

            "equilibrio": equilibrio,

            "indice_equilibrio":
                indice_equilibrio,

            "padrao": padrao,

            "radar": True,

        }

        resultados.append(
            registro
        )

    # --------------------------------------------------------
    # ORDENAR
    # --------------------------------------------------------
    #
    # Primeiro:
    #   maior desequilíbrio
    #
    # Depois:
    #   data
    #
    # Depois:
    #   horário
    #
    # Assim conseguimos observar
    # primeiro as partidas mais desequilibradas.
    # --------------------------------------------------------

    resultados.sort(
        key=lambda x: (
            -x["r"],
            x["data"],
            x["horario"],
        )
    )

    # --------------------------------------------------------
    # LOG
    # --------------------------------------------------------

    print(
        "JOGOS PRÉ-LIVE ENCONTRADOS:",
        len(jogos),
    )

    print(
        "JOGOS DENTRO DO Q:",
        len(resultados),
    )

    print()

    for jogo in resultados:

        print(
            f"RADAR | "
            f"{jogo['horario']} | "
            f"{jogo['casa']} x "
            f"{jogo['fora']} | "
            f"Q={jogo['q']:.2f} | "
            f"R={jogo['r']:.2f} | "
            f"{jogo['equilibrio']} | "
            f"{jogo['padrao']}"
        )

    return resultados


# ============================================================
# EXIBIR SCANNER
# ============================================================

def exibir_scanner(
    resultados
):

    if not resultados:

        print(
            "Nenhum resultado para exibir."
        )

        return

    print()
    print(
        "════════════════════════════════════════════════════════════════"
    )

    for jogo in resultados:

        print()

        print(
            f"⚽ {jogo['horario']} | "
            f"{jogo['casa']} x "
            f"{jogo['fora']}"
        )

        print(
            f"🏠 {jogo['odd_casa']:.2f} | "
            f"🤝 X {jogo['odd_empate']:.2f} | "
            f"🚌 {jogo['odd_visitante']:.2f}"
        )

        print(
            f"📐 Q: "
            f"{jogo['q']:.2f}"
        )

        print(
            f"📊 R: "
            f"{jogo['r']:.2f}"
        )

        print(
            f"⚖️ Equilíbrio: "
            f"{jogo['equilibrio']}"
        )

        print(
            f"📊 Índice: "
            f"{jogo['indice_equilibrio']:.2f}"
        )

        print(
            f"🎯 Hipótese: "
            f"{jogo['padrao']}"
        )

        print(
            f"📊 P(X): "
            f"{jogo['probabilidade_x']:.2f}% | "
            f"P(X) N: "
            f"{jogo['probabilidade_x_normalizada']:.2f}%"
        )

    print()
    print(
        "════════════════════════════════════════════════════════════════"
    )


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":

    dados = escanear_pre_live()

    exibir_scanner(
        dados
)
