# ============================================================
# SCANNER PRÉ-LIVE - IPM RADAR V5.2
# Q + ESTRUTURA + MERCADOS DE GOL
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
# Q PARA ESTUDO
# ============================================================
#
# FAIXA DE ESTUDO:
#
# Q = 2.00 ATÉ 3.60
#
# O valor fica definido aqui para garantir que o scanner
# use exatamente esta faixa, independentemente do config.py.
#
# ============================================================

Q_MIN = 2.00
Q_MAX = 3.60


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


# ============================================================
# Q
# ============================================================
#
# Q = 2 × (Casa × Visitante) / (Casa + Visitante)
#
# ============================================================

def calcular_q(
    odd_casa,
    odd_visitante,
):

    casa = numero(odd_casa)
    fora = numero(odd_visitante)

    if casa <= 0 or fora <= 0:
        return 0.0

    soma = casa + fora

    if soma <= 0:
        return 0.0

    return (
        2.0
        * casa
        * fora
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
    fora = numero(odd_visitante)

    if casa <= 0 or fora <= 0:
        return 0.0

    menor = min(
        casa,
        fora,
    )

    maior = max(
        casa,
        fora,
    )

    if menor <= 0:
        return 0.0

    return maior / menor


# ============================================================
# EQUILÍBRIO
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
# PADRÃO
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

        dt = datetime.fromisoformat(
            str(valor).replace(
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
# MERCADOS DE GOL
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
    # STATUS OVER
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
    # STATUS BTTS
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
    # PONTOS
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
    # ESTRUTURA
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
# SCANNER PRÉ-LIVE
# ============================================================

def escanear_pre_live():

    print()
    print("=" * 72)
    print(
        "🧪 SCANNER PRÉ-LIVE | "
        "IPM RADAR V5.2"
    )
    print("=" * 72)

    print(
        f"⏱️ JANELA: "
        f"{PRE_LIVE_JANELA_MINUTOS} minutos"
    )

    print(
        f"📐 Q REAL DO FILTRO: "
        f"{Q_MIN:.2f} → {Q_MAX:.2f}"
    )

    print(
        "⚽ ANÁLISE: TOTALS + BTTS"
    )

    print("=" * 72)

    # ========================================================
    # BUSCAR JOGOS
    # ========================================================

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

    print(
        f"⏳ PRÉ-LIVE: {len(jogos)}"
    )

    # ========================================================
    # ODDS
    # ========================================================

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

    print(
        f"📥 ODDS RECEBIDAS: "
        f"{len(odds)}"
    )

    print()

    # ========================================================
    # PROCESSAMENTO
    # ========================================================

    resultados = []

    validos_1x2 = 0

    fora_q = 0

    q_minimo = None

    q_maximo = None

    # ========================================================
    # LOOP
    # ========================================================

    for jogo in jogos:

        if not isinstance(
            jogo,
            dict
        ):
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
            mercados.get(
                "odd_casa"
            )
        )

        odd_empate = numero(
            mercados.get(
                "odd_empate"
            )
        )

        odd_visitante = numero(
            mercados.get(
                "odd_visitante"
            )
        )

        # ----------------------------------------------------
        # 1X2
        # ----------------------------------------------------

        if (
            odd_casa <= 0
            or odd_empate <= 0
            or odd_visitante <= 0
        ):

            continue

        validos_1x2 += 1

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

        r = calcular_r(
            odd_casa,
            odd_visitante,
        )

        # ----------------------------------------------------
        # ESTATÍSTICAS DE Q
        # ----------------------------------------------------

        if q_minimo is None:

            q_minimo = q

        else:

            q_minimo = min(
                q_minimo,
                q
            )

        if q_maximo is None:

            q_maximo = q

        else:

            q_maximo = max(
                q_maximo,
                q
            )

        # ----------------------------------------------------
        # NOMES
        # ----------------------------------------------------

        casa_nome = (
            jogo.get("home")
            or jogo.get("homeTeam")
            or "Casa"
        )

        fora_nome = (
            jogo.get("away")
            or jogo.get("awayTeam")
            or "Fora"
        )

        # ----------------------------------------------------
        # DIAGNÓSTICO
        # ----------------------------------------------------

        print(
            f"🔎 Q | "
            f"{dt.strftime('%H:%M')} | "
            f"{casa_nome} x {fora_nome} | "
            f"Casa={odd_casa:.2f} | "
            f"Fora={odd_visitante:.2f} | "
            f"Q={q:.4f}"
        )

        # ----------------------------------------------------
        # FILTRO Q
        # ----------------------------------------------------

        if q < Q_MIN:

            fora_q += 1

            continue

        if q > Q_MAX:

            fora_q += 1

            continue

        # ====================================================
        # GOLS
        # ====================================================

        gols = analisar_gols(
            mercados
        )

        # ====================================================
        # X
        # ====================================================

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

        # ====================================================
        # EQUILÍBRIO
        # ====================================================

        equilibrio = (
            classificar_equilibrio(
                r
            )
        )

        indice_equilibrio = (
            100.0 / r
            if r > 0
            else 0.0
        )

        padrao = (
            classificar_padrao(
                r
            )
        )

        # ====================================================
        # REGISTRO
        # ====================================================

        resultados.append({

            "event_id":
                str(event_id),

            "data":
                dt.strftime(
                    "%d/%m/%Y"
                ),

            "horario":
                dt.strftime(
                    "%H:%M"
                ),

            "periodo":
                periodo,

            "casa":
                casa_nome,

            "fora":
                fora_nome,

            "odd_casa":
                odd_casa,

            "odd_empate":
                odd_empate,

            "odd_visitante":
                odd_visitante,

            "q":
                round(
                    q,
                    4
                ),

            "r":
                round(
                    r,
                    4
                ),

            "odd_pre_live":
                round(
                    q,
                    4
                ),

            "probabilidade_x":
                prob_x,

            "probabilidade_x_normalizada":
                prob_x_normalizada,

            "equilibrio":
                equilibrio,

            "indice_equilibrio":
                round(
                    indice_equilibrio,
                    2
                ),

            "padrao":
                padrao,

            # ------------------------------------------------
            # GOLS
            # ------------------------------------------------

            "over_linha":
                gols[
                    "over_linha"
                ],

            "under_linha":
                gols[
                    "under_linha"
                ],

            "odd_over":
                gols[
                    "odd_over"
                ],

            "odd_under":
                gols[
                    "odd_under"
                ],

            "prob_over":
                gols[
                    "prob_over"
                ],

            "prob_under":
                gols[
                    "prob_under"
                ],

            "odd_btts_sim":
                gols[
                    "odd_btts_sim"
                ],

            "odd_btts_nao":
                gols[
                    "odd_btts_nao"
                ],

            "prob_btts_sim":
                gols[
                    "prob_btts_sim"
                ],

            "prob_btts_nao":
                gols[
                    "prob_btts_nao"
                ],

            "over_status":
                gols[
                    "over_status"
                ],

            "btts_status":
                gols[
                    "btts_status"
                ],

            "pontos_gol":
                gols[
                    "pontos_gol"
                ],

            "estrutura_gol":
                gols[
                    "estrutura_gol"
                ],

            "mercado_gol_disponivel":
                gols[
                    "mercado_gol_disponivel"
                ],

            "radar":
                True,
        })

    # ========================================================
    # ORDENAÇÃO
    # ========================================================

    resultados.sort(
        key=lambda x: (
            -x["pontos_gol"],
            -x["q"],
            -x["r"],
            x["data"],
            x["horario"],
        )
    )

    # ========================================================
    # DIAGNÓSTICO FINAL
    # ========================================================

    print()

    print("=" * 72)

    print(
        "📊 DIAGNÓSTICO PRÉ-LIVE"
    )

    print("=" * 72)

    print(
        f"JOGOS RECEBIDOS: "
        f"{len(jogos)}"
    )

    print(
        f"1X2 VÁLIDO: "
        f"{validos_1x2}"
    )

    if q_minimo is not None:

        print(
            f"Q MÍNIMO ENCONTRADO: "
            f"{q_minimo:.4f}"
        )

    else:

        print(
            "Q MÍNIMO ENCONTRADO: --"
        )

    if q_maximo is not None:

        print(
            f"Q MÁXIMO ENCON
