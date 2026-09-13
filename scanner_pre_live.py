# ============================================================
# SCANNER PRÉ-LIVE - IPM RADAR V5.2
# Q + ESTRUTURA + MERCADOS DE GOL
# ============================================================
#
# Função:
#   - Buscar jogos futuros
#   - Filtrar pela janela pré-live
#   - Obter odds 1X2
#   - Calcular P(X)
#   - Calcular P(X) normalizada
#   - Calcular Q
#   - Calcular R
#   - Medir equilíbrio / desequilíbrio
#   - Analisar Over/Under
#   - Analisar BTTS
#   - Classificar estrutura pré-live para GOL
#   - Preparar jogos para o RADAR
#
# NÃO gera entrada.
# NÃO realiza apostas.
# NÃO altera o LIVE.
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
# PROBABILIDADE IMPLÍCITA
# ============================================================

def probabilidade_implicita(odd):

    odd = numero(odd)

    if odd <= 0:
        return 0.0

    return 100.0 / odd


# ============================================================
# PROBABILIDADE NORMALIZADA DO X
# ============================================================

def probabilidade_normalizada(
    odd_casa,
    odd_empate,
    odd_visitante,
):

    pc = probabilidade_implicita(odd_casa)
    px = probabilidade_implicita(odd_empate)
    pv = probabilidade_implicita(odd_visitante)

    total = pc + px + pv

    if total <= 0:
        return 0.0

    return (px / total) * 100.0


# ============================================================
# Q
# ============================================================
#
# Q = 2 × (Casa × Visitante) / (Casa + Visitante)
#
# ESTUDO:
# Q MÍNIMO = 2.00
# Q MÁXIMO = 3.50
#
# ============================================================

def calcular_q(
    odd_casa,
    odd_visitante,
):

    casa = numero(odd_casa)
    visitante = numero(odd_visitante)

    if casa <= 0 or visitante <= 0:
        return 0.0

    soma = casa + visitante

    if soma <= 0:
        return 0.0

    return (
        2.0
        * casa
        * visitante
        / soma
    )


# ============================================================
# R
# ============================================================

def calcular_r(
    odd_casa,
    odd_visitante,
):

    casa = numero(odd_casa)
    visitante = numero(odd_visitante)

    if casa <= 0 or visitante <= 0:
        return 0.0

    menor = min(casa, visitante)
    maior = max(casa, visitante)

    if menor <= 0:
        return 0.0

    return maior / menor


# ============================================================
# CLASSIFICAÇÃO DO EQUILÍBRIO
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


# ============================================================
# ÍNDICE DE EQUILÍBRIO
# ============================================================

def calcular_indice_equilibrio(r):

    r = numero(r)

    if r <= 0:
        return 0.0

    return round(
        100.0 / r,
        2
    )


# ============================================================
# PADRÃO ESTRUTURAL
# ============================================================

def classificar_padrao(r):

    r = numero(r)

    if r <= 0:
        return "SEM_DADOS"

    if r <= 1.80:
        return "PADRÃO_EMPATE"

    return "PADRÃO_GOL"


# ============================================================
# PERÍODO
# ============================================================

def identificar_periodo(dt):

    hora = dt.time()

    if time(6, 0) <= hora < time(12, 0):
        return "06:00 - 12:00"

    if time(12, 0) <= hora < time(18, 0):
        return "12:00 - 18:00"

    if time(18, 0) <= hora or hora < time(0, 0):
        return "18:00 - 00:00"

    return "FORA_DA_JANELA"


# ============================================================
# HORÁRIO
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
            texto.replace("Z", "+00:00")
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
# ANÁLISE DO MERCADO DE GOLS
# ============================================================

def analisar_gols(mercados):

    over_linha = numero(
        mercados.get("over_linha")
    )

    under_linha = numero(
        mercados.get("under_linha")
    )

    odd_over = numero(
        mercados.get("odd_over")
    )

    odd_under = numero(
        mercados.get("odd_under")
    )

    odd_btts_sim = numero(
        mercados.get("odd_btts_sim")
    )

    odd_btts_nao = numero(
        mercados.get("odd_btts_nao")
    )

    # --------------------------------------------------------
    # PROBABILIDADES
    # --------------------------------------------------------

    prob_over = probabilidade_implicita(
        odd_over
    )

    prob_under = probabilidade_implicita(
        odd_under
    )

    prob_btts_sim = probabilidade_implicita(
        odd_btts_sim
    )

    prob_btts_nao = probabilidade_implicita(
        odd_btts_nao
    )

    # --------------------------------------------------------
    # DISPONIBILIDADE
    # --------------------------------------------------------

    over_disponivel = (
        odd_over > 0
        and odd_under > 0
    )

    btts_disponivel = (
        odd_btts_sim > 0
        and odd_btts_nao > 0
    )

    # --------------------------------------------------------
    # FORÇA DO OVER
    # --------------------------------------------------------

    if over_disponivel:

        if (
            prob_over >= 60
            and odd_over <= 1.70
        ):
            over_status = "OVER FORTE"

        elif (
            prob_over >= 55
            and odd_over <= 1.85
        ):
            over_status = "OVER FAVORÁVEL"

        elif (
            prob_over >= 50
            and odd_over <= 2.00
        ):
            over_status = "OVER MODERADO"

        else:
            over_status = "OVER NEUTRO"

    else:
        over_status = "SEM TOTALS"

    # --------------------------------------------------------
    # FORÇA DO BTTS
    # --------------------------------------------------------

    if btts_disponivel:

        if (
            prob_btts_sim >= 60
            and odd_btts_sim <= 1.70
        ):
            btts_status = "BTTS FORTE"

        elif (
            prob_btts_sim >= 55
            and odd_btts_sim <= 1.85
        ):
            btts_status = "BTTS FAVORÁVEL"

        elif (
            prob_btts_sim >= 50
            and odd_btts_sim <= 2.00
        ):
            btts_status = "BTTS MODERADO"

        else:
            btts_status = "BTTS NEUTRO"

    else:
        btts_status = "SEM BTTS"

    # --------------------------------------------------------
    # ÍNDICE INTERNO DE GOL
    # --------------------------------------------------------

    pontos = 0

    if over_status == "OVER FORTE":
        pontos += 2

    elif over_status in (
        "OVER FAVORÁVEL",
        "OVER MODERADO",
    ):
        pontos += 1

    if btts_status == "BTTS FORTE":
        pontos += 2

    elif btts_status in (
        "BTTS FAVORÁVEL",
        "BTTS MODERADO",
    ):
        pontos += 1

    # --------------------------------------------------------
    # CLASSIFICAÇÃO FINAL
    # --------------------------------------------------------

    if pontos >= 4:

        estrutura_gol = (
            "ESTRUTURA MUITO FAVORÁVEL A GOLS"
        )

    elif pontos >= 3:

        estrutura_gol = (
            "ESTRUTURA FAVORÁVEL A GOLS"
        )

    elif pontos >= 2:

        estrutura_gol = (
            "ESTRUTURA MODERADA PARA GOLS"
        )

    elif pontos == 1:

        estrutura_gol = (
            "ESTRUTURA FRACA PARA GOLS"
        )

    else:

        estrutura_gol = (
            "SEM CONFIRMAÇÃO PRÉ-LIVE"
        )

    return {

        "over_linha": over_linha,
        "under_linha": under_linha,

        "odd_over": odd_over,
        "odd_under": odd_under,

        "prob_over": prob_over,
        "prob_under": prob_under,

        "odd_btts_sim": odd_btts_sim,
        "odd_btts_nao": odd_btts_nao,

        "prob_btts_sim": prob_btts_sim,
        "prob_btts_nao": prob_btts_nao,

        "over_status": over_status,
        "btts_status": btts_status,

        "pontos_gol": pontos,

        "estrutura_gol": estrutura_gol,

        "mercado_gol_disponivel": (
            over_disponivel
            or btts_disponivel
        ),
    }


# ============================================================
# SCANNER
# ============================================================

def escanear_pre_live():

    print()
    print("=" * 72)
    print("🧪 SCANNER PRÉ-LIVE | IPM RADAR V5.2")
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
        "⚽ ANÁLISE: TOTALS + BTTS"
    )

    # --------------------------------------------------------
    # JOGOS
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
    # ODDS
    # --------------------------------------------------------

    try:

        odds = (
            buscar_odds_multiplos(jogos)
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
    # PROCESSAMENTO
    # --------------------------------------------------------

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

        odd_casa = numero(
            mercados.get("odd_casa")
        )

        odd_empate = numero(
            mercados.get("odd_empate")
        )

        odd_visitante = numero(
            mercados.get("odd_visitante")
        )

        # ----------------------------------------------------
        # ODDS 1X2
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

        dt = converter_horario(jogo)

        if dt is None:
            continue

        periodo = identificar_periodo(dt)

        if periodo == "FORA_DA_JANELA":
            continue

        # ----------------------------------------------------
        # Q
        # ----------------------------------------------------

        q = calcular_q(
            odd_casa,
            odd_visitante,
        )

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

        equilibrio = classificar_equilibrio(r)

        indice_equilibrio = (
            calcular_indice_equilibrio(r)
        )

        padrao = classificar_padrao(r)

        # ----------------------------------------------------
        # X
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # GOLS
        # ----------------------------------------------------

        gols = analisar_gols(mercados)

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

            "event_id": str(event_id),

            "data": dt.strftime("%d/%m/%Y"),

            "horario": dt.strftime("%H:%M"),

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

            "equilibrio": equilibrio,

            "indice_equilibrio":
                indice_equilibrio,

            "padrao": padrao,

            # ------------------------------------------------
            # MERCADO DE GOLS
            # ------------------------------------------------

            "over_linha":
                gols["over_linha"],

            "under_linha":
                gols["under_linha"],

            "odd_over":
                gols["odd_over"],

            "odd_under":
                gols["odd_under"],

            "prob_over":
                gols["prob_over"],

            "prob_under":
                gols["prob_under"],

            "odd_btts_sim":
                gols["odd_btts_sim"],

            "odd_btts_nao":
                gols["odd_btts_nao"],

            "prob_btts_sim":
                gols["prob_btts_sim"],

            "prob_btts_nao":
                gols["prob_btts_nao"],

            "over_status":
                gols["over_status"],

            "btts_status":
                gols["btts_status"],

            "pontos_gol":
                gols["pontos_gol"],

            "estrutura_gol":
                gols["estrutura_gol"],

            "mercado_gol_disponivel":
                gols["mercado_gol_disponivel"],

            "radar": True,
        }

        resultados.append(registro)

    # --------------------------------------------------------
    # ORDENAÇÃO
    # --------------------------------------------------------

    resultados.sort(
        key=lambda x: (
            -x["pontos_gol"],
            -x["q"],
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
            f"OVER={jogo['odd_over']:.2f} | "
            f"BTTS={jogo['odd_btts_sim']:.2f} | "
            f"{jogo['estrutura_gol']}"
        )

    return resultados

# ============================================================
# EXIBIÇÃO
# ============================================================

def exibir_scanner(resultados):

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
            f"📐 Q: {jogo['q']:.2f}"
        )

        print(
            f"📊 R: {jogo['r']:.2f}"
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
            f"🎯 P(X): "
            f"{jogo['probabilidade_x']:.2f}% | "
            f"P(X) N: "
            f"{jogo['probabilidade_x_normalizada']:.2f}%"
        )

        print()

        print("⚽ MERCADO DE GOLS")

        if jogo["odd_over"] > 0:

            print(
                f"📈 Over "
                f"{jogo['over_linha']:.2f}: "
                f"{jogo['odd_over']:.2f} | "
                f"P={jogo['prob_over']:.2f}%"
            )

            print(
                f"📉 Under "
                f"{jogo['under_linha']:.2f}: "
                f"{jogo['odd_under']:.2f} | "
                f"P={jogo['prob_under']:.2f}%"
            )

            print(
                f"🧪 Status: "
                f"{jogo['over_status']}"
            )

        else:

            print(
                "📈 Totals: NÃO DISPONÍVEL"
            )

        if jogo["odd_btts_sim"] > 0:

            print(
                f"⚽ BTTS SIM: "
                f"{jogo['odd_btts_sim']:.2f} | "
                f"P={jogo['prob_btts_sim']:.2f}%"
            )

            print(
                f"🚫 BTTS NÃO: "
                f"{jogo['odd_btts_nao']:.2f} | "
                f"P={jogo['prob_btts_nao']:.2f}%"
            )

            print(
                f"🧪 Status: "
                f"{jogo['btts_status']}"
            )

        else:

            print(
                "⚽ BTTS: NÃO DISPONÍVEL"
            )

        print()

        print(
            f"🔥 Pontos de gol: "
            f"{jogo['pontos_gol']}"
        )

        print(
            f"🎯 Estrutura: "
            f"{jogo['estrutura_gol']}"
        )

        print(
            "------------------------------------------------------------"
        )


# ============================================================
# TESTE DIRETO
# ============================================================

if __name__ == "__main__":

    resultados = escanear_pre_live()

    exibir_scanner(resultados)
