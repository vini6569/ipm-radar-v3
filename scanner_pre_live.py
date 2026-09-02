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
#   - Preparar a lista para OBSERVAÇÃO
#
# NÃO gera entrada.
# NÃO altera o IPM LIVE.
# ============================================================

from datetime import datetime, time

from config import (
    FUSO_HORARIO,
    MAX_EVENTOS_POR_CONSULTA,
)

from odds_api import (
    buscar_jogos_pre_live,
    buscar_odds_multiplos,
    extrair_mercados,
)


def _numero(valor, padrao=0.0):
    try:
        if valor in (None, ""):
            return padrao

        return float(valor)

    except (TypeError, ValueError):
        return padrao


def probabilidade_implicita(odd):
    """
    Calcula a probabilidade implícita da odd decimal.

    Exemplo:
        odd 2.50 = 40%
    """

    odd = _numero(odd)

    if odd <= 0:
        return 0.0

    return 100.0 / odd


def probabilidade_normalizada(
    odd_casa,
    odd_empate,
    odd_visitante,
):
    """
    Remove matematicamente o overround usando
    a soma das probabilidades implícitas.

    Retorna a probabilidade normalizada do empate.
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

    total = pc + px + pv

    if total <= 0:
        return 0.0

    return (
        px / total
    ) * 100.0


def identificar_periodo(dt):
    """
    Divide o dia conforme definido no projeto:

        06:00 - 12:00
        12:00 - 18:00
        18:00 - 00:00
    """

    hora = dt.time()

    if time(6, 0) <= hora < time(12, 0):
        return "06:00 - 12:00"

    if time(12, 0) <= hora < time(18, 0):
        return "12:00 - 18:00"

    if (
        time(18, 0) <= hora
        or hora < time(0, 0)
    ):
        return "18:00 - 00:00"

    return "FORA_DA_JANELA"


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


def escanear_pre_live():
    """
    Executa o Scanner Pré-Live.

    Retorna uma lista de jogos com os
    cálculos pré-live.
    """

    print()
    print("=" * 72)
    print("🧪 SCANNER PRÉ-LIVE")
    print("=" * 72)

    try:
        jogos = buscar_jogos_pre_live() or []

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

    try:

        odds = buscar_odds_multiplos(
            jogos
        ) or []

    except Exception as erro:

        print(
            "ERRO AO BUSCAR ODDS PRÉ-LIVE:",
            type(erro).__name__,
            erro,
        )

        odds = []

    resultados = []

    for jogo in jogos:

        if not isinstance(jogo, dict):
            continue

        event_id = jogo.get("id")

        if event_id is None:
            continue

        mercados = extrair_mercados(
            jogo,
            odds,
        ) or {}

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

        if odd_empate <= 0:
            continue

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

        prob_x = probabilidade_implicita(
            odd_empate
        )

        prob_x_normalizada = (
            probabilidade_normalizada(
                odd_casa,
                odd_empate,
                odd_visitante,
            )
        )

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

            "casa": (
                jogo.get("home")
                or jogo.get("homeTeam")
                or "Casa"
            ),

            "fora": (
                jogo.get("away")
                or jogo.get("awayTeam")
                or "Fora"
            ),

            "odd_casa": odd_casa,

            "odd_empate": odd_empate,

            "odd_visitante": odd_visitante,

            "probabilidade_x": prob_x,

            "probabilidade_x_normalizada":
                prob_x_normalizada,
        }

        resultados.append(
            registro
        )

    resultados.sort(
        key=lambda x: (
            x["data"],
            x["horario"],
        )
    )

    print(
        "JOGOS PRÉ-LIVE ANALISADOS:",
        len(resultados),
    )

    return resultados


def exibir_scanner(resultados):

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
            if jogo["periodo"] == periodo
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
                f"   📐 P(X): "
                f"{jogo['probabilidade_x']:.2f}% | "
                f"P(X) normalizada: "
                f"{jogo['probabilidade_x_normalizada']:.2f}%"
            )

    print()
    print(
        "════════════════════════════════════════════════════════════════"
    )


if __name__ == "__main__":

    dados = escanear_pre_live()

    exibir_scanner(
        dados
  )
