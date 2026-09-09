# ============================================================
# SCANNER PRÉ-LIVE - IPM RADAR
# ============================================================
#
# Função:
#   - Buscar jogos futuros
#   - Organizar por período do dia
#   - Obter odds 1X2
#   - Calcular probabilidade implícita do empate
#   - Calcular probabilidade normalizada do empate
#   - Calcular Q pré-live
#   - Calcular R pré-live
#   - Filtrar pela combinação Q + R validada
#   - Preparar a lista para OBSERVAÇÃO
#
# NÃO gera entrada.
# NÃO altera o IPM LIVE.
#
# ============================================================
# CÁLCULO VALIDADO
# ============================================================
#
# Q = 2 × (W1 × W2) / (W1 + W2)
#
# R = max(W1, W2) / min(W1, W2)
#
# Faixa validada:
#
# Q = 2.80 até 2.90
# R = 1.00 até 1.80
#
# ============================================================

from datetime import datetime, time

from config import (
    FUSO_HORARIO,
    MAX_EVENTOS_POR_CONSULTA,
    PRE_LIVE_JANELA_MINUTOS,
)

from odds_api import (
    buscar_jogos_pre_live,
    buscar_odds_multiplos,
    extrair_mercados,
)


# ============================================================
# CONFIGURAÇÃO DO CÁLCULO VALIDADO
# ============================================================

Q_VALIDADO_MIN = 2.80
Q_VALIDADO_MAX = 2.90

R_VALIDADO_MIN = 1.00
R_VALIDADO_MAX = 1.80


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

    """
    Calcula a probabilidade implícita
    da odd decimal.

    Exemplo:

        odd 2.50 = 40%
    """

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

    """
    Remove matematicamente o overround
    usando a soma das probabilidades implícitas.

    Retorna a probabilidade normalizada
    do empate.
    """

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
# CÁLCULO DO Q — VALIDADO
# ============================================================

def calcular_q(
    odd_casa,
    odd_visitante,
):

    """
    Calcula o Q validado.

    Fórmula:

        Q = 2 × (W1 × W2) / (W1 + W2)

    Onde:

        W1 = odd da vitória da casa
        W2 = odd da vitória do visitante

    """

    odd_casa = _numero(
        odd_casa
    )

    odd_visitante = _numero(
        odd_visitante
    )

    if (
        odd_casa <= 0
        or odd_visitante <= 0
    ):
        return 0.0

    soma = (
        odd_casa
        + odd_visitante
    )

    if soma <= 0:
        return 0.0

    q = (
        2.0
        * odd_casa
        * odd_visitante
    ) / soma

    return q


# ============================================================
# CÁLCULO DO R — VALIDADO
# ============================================================

def calcular_r(
    odd_casa,
    odd_visitante,
):

    """
    Calcula o R validado.

    Fórmula:

        R = max(W1, W2) / min(W1, W2)

    O cálculo mede a relação entre
    a maior e a menor odd das duas pontas.

    """

    odd_casa = _numero(
        odd_casa
    )

    odd_visitante = _numero(
        odd_visitante
    )

    if (
        odd_casa <= 0
        or odd_visitante <= 0
    ):
        return 0.0

    menor = min(
        odd_casa,
        odd_visitante,
    )

    maior = max(
        odd_casa,
        odd_visitante,
    )

    if menor <= 0:
        return 0.0

    return maior / menor


# ============================================================
# VERIFICAR CÁLCULO VALIDADO
# ============================================================

def caracteriza_calculo_validado(
    q,
    r,
):

    """
    Verifica se o jogo atende
    simultaneamente às duas condições:

        Q = 2.80 até 2.90

        R = 1.00 até 1.80
    """

    if q < Q_VALIDADO_MIN:
        return False

    if q > Q_VALIDADO_MAX:
        return False

    if r < R_VALIDADO_MIN:
        return False

    if r > R_VALIDADO_MAX:
        return False

    return True


# ============================================================
# PERÍODO DO DIA
# ============================================================

def identificar_periodo(dt):

    """
    Divide o dia conforme definido no projeto:

        06:00 - 12:00
        12:00 - 18:00
        18:00 - 00:00
    """

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

    """
    Tenta localizar a data/hora do evento.
    """

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
                "+00:00",
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

    """
    Executa o Scanner Pré-Live.

    A janela é definida pelo CONFIG:

        PRE_LIVE_JANELA_MINUTOS

    O filtro validado utiliza:

        Q = 2.80 até 2.90

        R = 1.00 até 1.80

    Retorna uma lista de jogos
    aprovados pela combinação Q + R.
    """

    print()
    print("=" * 72)
    print("🧪 SCANNER PRÉ-LIVE")
    print("=" * 72)

    print(
        f"⏱️ JANELA: "
        f"{PRE_LIVE_JANELA_MINUTOS} minutos"
    )

    print(
        f"📐 Q VALIDADO: "
        f"{Q_VALIDADO_MIN:.2f} até "
        f"{Q_VALIDADO_MAX:.2f}"
    )

    print(
        f"📊 R VALIDADO: "
        f"{R_VALIDADO_MIN:.2f} até "
        f"{R_VALIDADO_MAX:.2f}"
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
            "ERRO AO BUSCAR JOGOS PRÉ-LIVE:",
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
            "ERRO AO BUSCAR ODDS PRÉ-LIVE:",
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
            dict,
        ):

            continue

        event_id = jogo.get(
            "id"
        )

        if event_id is None:
            continue

        # ----------------------------------------------------
        # EXTRAIR MERCADOS
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
        # SEM ODD DE EMPATE
        # ----------------------------------------------------

        if odd_empate <= 0:

            continue

        # ----------------------------------------------------
        # SEM ODDS VÁLIDAS DAS DUAS PONTAS
        # ----------------------------------------------------

        if (
            odd_casa <= 0
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
        # PROBABILIDADES
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
        # Q PRÉ-LIVE — FÓRMULA VALIDADA
        # ----------------------------------------------------

        q = calcular_q(
            odd_casa,
            odd_visitante,
        )

        # ----------------------------------------------------
        # R PRÉ-LIVE — FÓRMULA VALIDADA
        # ----------------------------------------------------

        r = calcular_r(
            odd_casa,
            odd_visitante,
        )

        # ----------------------------------------------------
        # FILTRO Q + R
        # ----------------------------------------------------

        if not caracteriza_calculo_validado(
            q,
            r,
        ):

            continue

        # ----------------------------------------------------
        # NOMES DOS TIMES
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

        }

        resultados.append(
            registro
        )

    # --------------------------------------------------------
    # ORDENAR
    # --------------------------------------------------------

    resultados.sort(
        key=lambda x: (
            x["data"],
            x["horario"],
        )
    )

    print(
        "JOGOS PRÉ-LIVE ANALISADOS:",
        len(jogos),
    )

    print(
        "JOGOS APROVADOS PELO Q + R:",
        len(resultados),
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

    periodos = (
        "06:00 - 12:00",
        "12:00 - 18:00",
        "18:00 - 00:00",
    )

    print()
    print(
        "════════════════════════════════════════════════════════════════"
    )

    for periodo in periodos:

        jogos_periodo = [

            jogo

            for jogo in resultados

            if jogo["periodo"]
            == periodo

        ]

        print()
        print(
            f"🧪 {periodo}"
        )

        print(
            "────────────────────────────────────────────────────────────────"
        )

        if not jogos_periodo:

            print(
                "Nenhum jogo."
            )

            continue

        for jogo in jogos_periodo:

            print(
                f"{jogo['horario']} | "
                f"{jogo['casa']} x "
                f"{jogo['fora']}"
            )

            print(
                f"   🏠 {jogo['odd_casa']:.2f} | "
                f"🤝 X {jogo['odd_empate']:.2f} | "
                f"🚌 {jogo['odd_visitante']:.2f}"
            )

            print(
                f"   📐 Q: "
                f"{jogo['q']:.2f}"
            )

            print(
                f"   📊 R: "
                f"{jogo['r']:.2f}"
            )

            print(
                f"   📊 P(X): "
                f"{jogo['probabilidade_x']:.2f}% | "
                f"P(X) normalizada: "
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
