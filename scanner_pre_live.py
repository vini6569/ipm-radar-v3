# ============================================================
# PRE-LIVE - IPM RADAR V5.2
# SOMENTE SELEÇÃO PRÉ-LIVE
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
# PROBABILIDADES
# ============================================================

def probabilidade(odd):
    odd = numero(odd)

    if odd <= 0:
        return 0.0

    return 100.0 / odd


def probabilidade_normalizada(
    odd_casa,
    odd_empate,
    odd_visitante,
):
    pc = probabilidade(odd_casa)
    px = probabilidade(odd_empate)
    pv = probabilidade(odd_visitante)

    total = pc + px + pv

    if total <= 0:
        return 0.0

    return (px / total) * 100.0


# ============================================================
# Q
# ============================================================

def calcular_q(odd_casa, odd_visitante):
    casa = numero(odd_casa)
    fora = numero(odd_visitante)

    if casa <= 0 or fora <= 0:
        return 0.0

    return (
        2.0 * casa * fora
        / (casa + fora)
    )


# ============================================================
# R
# ============================================================

def calcular_r(odd_casa, odd_visitante):
    casa = numero(odd_casa)
    fora = numero(odd_visitante)

    if casa <= 0 or fora <= 0:
        return 0.0

    return max(casa, fora) / min(casa, fora)


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classificar_equilibrio(r):
    r = numero(r)

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


def indice_equilibrio(r):
    r = numero(r)

    if r <= 0:
        return 0.0

    return round(100.0 / r, 2)


def classificar_padrao(r):
    r = numero(r)

    if r <= 0:
        return "SEM_DADOS"

    return (
        "PADRÃO_EMPATE"
        if r <= 1.80
        else "PADRÃO_GOL"
    )


# ============================================================
# DATA / HORÁRIO
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
        dt = datetime.fromisoformat(
            str(valor).replace("Z", "+00:00")
        )

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=FUSO_HORARIO)

        return dt.astimezone(FUSO_HORARIO)

    except Exception:
        return None


def periodo(dt):
    hora = dt.time()

    if time(6, 0) <= hora < time(12, 0):
        return "06:00 - 12:00"

    if time(12, 0) <= hora < time(18, 0):
        return "12:00 - 18:00"

    if hora >= time(18, 0):
        return "18:00 - 00:00"

    return "FORA_DA_JANELA"


# ============================================================
# SCANNER
# ============================================================

def escanear_pre_live():

    print("\n" + "=" * 60)
    print("🧪 IPM RADAR | PRÉ-LIVE")
    print(
        f"⏱️ Janela: {PRE_LIVE_JANELA_MINUTOS} min"
    )
    print(
        f"📐 Q: {Q_MIN:.2f} → {Q_MAX:.2f}"
    )
    print("=" * 60)

    try:
        jogos = buscar_jogos_pre_live() or []
    except Exception as erro:
        print(
            "❌ ERRO JOGOS:",
            type(erro).__name__,
            erro,
        )
        return []

    if not jogos:
        print("PRÉ-LIVE | Nenhum jogo encontrado.")
        return []

    jogos = jogos[:MAX_EVENTOS_POR_CONSULTA]

    try:
        odds = buscar_odds_multiplos(jogos) or []
    except Exception as erro:
        print(
            "❌ ERRO ODDS:",
            type(erro).__name__,
            erro,
        )
        return []

    resultados = []

    for jogo in jogos:

        if not isinstance(jogo, dict):
            continue

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

        casa_odd = numero(
            mercados.get("odd_casa")
        )

        empate_odd = numero(
            mercados.get("odd_empate")
        )

        fora_odd = numero(
            mercados.get("odd_visitante")
        )

        # ----------------------------------------------------
        # 1X2 OBRIGATÓRIO
        # ----------------------------------------------------

        if (
            casa_odd <= 0
            or empate_odd <= 0
            or fora_odd <= 0
        ):
            continue

        dt = converter_horario(jogo)

        if dt is None:
            continue

        periodo_jogo = periodo(dt)

        if periodo_jogo == "FORA_DA_JANELA":
            continue

        # ----------------------------------------------------
        # Q
        # ----------------------------------------------------

        q = calcular_q(
            casa_odd,
            fora_odd,
        )

        if not Q_MIN <= q <= Q_MAX:
            continue

        # ----------------------------------------------------
        # R
        # ----------------------------------------------------

        r = calcular_r(
            casa_odd,
            fora_odd,
        )

        if r <= 0:
            continue

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
        # RESULTADO
        # ----------------------------------------------------

        resultados.append({

            "event_id": str(event_id),

            "data": dt.strftime("%d/%m/%Y"),

            "horario": dt.strftime("%H:%M"),

            "timestamp": dt.timestamp(),

            "periodo": periodo_jogo,

            "casa": casa,

            "fora": fora,

            "odd_casa": casa_odd,

            "odd_empate": empate_odd,

            "odd_visitante": fora_odd,

            "odd_pre_live": q,

            "q": q,

            "r": r,

            "probabilidade_x":
                probabilidade(empate_odd),

            "probabilidade_x_normalizada":
                probabilidade_normalizada(
                    casa_odd,
                    empate_odd,
                    fora_odd,
                ),

            "equilibrio":
                classificar_equilibrio(r),

            "indice_equilibrio":
                indice_equilibrio(r),

            "padrao":
                classificar_padrao(r),

            "radar": True,
        })

    # ========================================================
    # ORDENAÇÃO
    # ========================================================

    resultados.sort(
        key=lambda x: (
            x["timestamp"],
            -x["r"],
        )
    )

    # ========================================================
    # LOG
    # ========================================================

    print(
        f"PRÉ-LIVE | Jogos encontrados: {len(jogos)}"
    )

    print(
        f"PRÉ-LIVE | Jogos aprovados: {len(resultados)}"
    )

    for jogo in resultados:

        print(
            f"RADAR | "
            f"{jogo['horario']} | "
            f"{jogo['casa']} x {jogo['fora']} | "
            f"Q={jogo['q']:.2f} | "
            f"R={jogo['r']:.2f} | "
            f"{jogo['equilibrio']} | "
            f"{jogo['padrao']}"
        )

    return resultados


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    dados = escanear_pre_live()

    print(
        f"\nTOTAL PRÉ-LIVE: {len(dados)}"
        )
