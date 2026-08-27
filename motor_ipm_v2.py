# ============================================================
# MOTOR IPM - IPM RADAR V4.1
# ============================================================

_odds_anteriores = {}


# ============================================================
# CONVERTER ODD
# ============================================================

def _converter_odd(
    valor
):

    try:

        numero = float(
            valor
        )

        if numero > 0:

            return numero

        return None

    except (
        TypeError,
        ValueError
    ):

        return None


# ============================================================
# VARIAÇÃO DA ODD
# ============================================================

def calcular_variacao_odd(
    odd_anterior,
    odd_atual
):

    anterior = _converter_odd(
        odd_anterior
    )

    atual = _converter_odd(
        odd_atual
    )

    if (
        anterior is None
        or atual is None
    ):

        return 0.0

    return (
        (
            atual
            - anterior
        )
        / anterior
    ) * 100.0


# ============================================================
# CLASSIFICA FORÇA
# ============================================================

def classificar_forca(
    variacao_odd
):

    try:

        valor = abs(
            float(
                variacao_odd
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return "ESTAVEL"

    if valor >= 10:

        return "MUITO FORTE"

    if valor >= 5:

        return "FORTE"

    if valor >= 2:

        return "MODERADO"

    if valor >= 0.5:

        return "FRACO"

    return "ESTAVEL"


# ============================================================
# CALCULAR IPM
# ============================================================

def calcular_ipm(
    variacao_odd,
    minuto=0,
    gols=0,
    escanteios=0,
    finalizacoes=0,
    ataques_perigosos=0
):

    try:

        variacao = float(
            variacao_odd
        )

        minuto = max(
            int(minuto),
            0
        )

        gols = max(
            int(gols),
            0
        )

        escanteios = max(
            int(escanteios),
            0
        )

        finalizacoes = max(
            int(finalizacoes),
            0
        )

        ataques_perigosos = max(
            int(ataques_perigosos),
            0
        )


        # ====================================================
        # MOVIMENTO DA ODD
        # ====================================================

        movimento = min(
            abs(
                variacao
            ) * 5.0,
            60.0
        )


        # ====================================================
        # CONFIRMAÇÕES
        # ====================================================

        confirmacao_gols = min(
            gols * 5.0,
            10.0
        )

        confirmacao_escanteios = min(
            escanteios * 1.5,
            10.0
        )

        confirmacao_finalizacoes = min(
            finalizacoes * 0.5,
            10.0
        )

        confirmacao_ataques = min(
            ataques_perigosos * 0.2,
            10.0
        )


        # ====================================================
        # IPM
        # ====================================================

        ipm = (
            movimento
            + confirmacao_gols
            + confirmacao_escanteios
            + confirmacao_finalizacoes
            + confirmacao_ataques
        )

        ipm = min(
            max(
                ipm,
                0.0
            ),
            100.0
        )


        return {

            "ipm": round(
                ipm,
                2
            ),

            "variacao_odd": round(
                variacao,
                2
            ),

            "forca": classificar_forca(
                variacao
            ),

            "movimento": round(
                movimento,
                2
            ),

            "confirmacao_gols": round(
                confirmacao_gols,
                2
            ),

            "confirmacao_escanteios": round(
                confirmacao_escanteios,
                2
            ),

            "confirmacao_finalizacoes": round(
                confirmacao_finalizacoes,
                2
            ),

            "confirmacao_ataques": round(
                confirmacao_ataques,
                2
            ),

            "minuto": minuto,

            "gols": gols,

            "escanteios": escanteios,

            "finalizacoes": finalizacoes,

            "ataques_perigosos":
                ataques_perigosos,
        }


    except Exception as erro:

        return {

            "ipm": 0.0,

            "variacao_odd": 0.0,

            "forca": "ESTAVEL",

            "movimento": 0.0,

            "confirmacao_gols": 0.0,

            "confirmacao_escanteios": 0.0,

            "confirmacao_finalizacoes": 0.0,

            "confirmacao_ataques": 0.0,

            "minuto": minuto,

            "gols": gols,

            "escanteios": escanteios,

            "finalizacoes": finalizacoes,

            "ataques_perigosos":
                ataques_perigosos,

            "erro": str(
                erro
            ),
        }


# ============================================================
# ANALISAR IPM COM MEMÓRIA
# ============================================================

def analisar_ipm_com_memoria(
    chave_jogo,
    odd_atual,
    minuto=0,
    gols=0,
    escanteios=0,
    finalizacoes=0,
    ataques_perigosos=0
):

    if chave_jogo is None:

        raise ValueError(
            "chave_jogo é obrigatória"
        )

    chave = str(
        chave_jogo
    )

    atual = _converter_odd(
        odd_atual
    )

    # ========================================================
    # ODD INVÁLIDA
    # ========================================================

    if atual is None:

        resultado = calcular_ipm(
            0.0,
            minuto,
            gols,
            escanteios,
            finalizacoes,
            ataques_perigosos
        )

        resultado.update({

            "odd_anterior": None,

            "odd_atual": odd_atual,

            "primeira_consulta": False,

            "erro":
                "odd_atual_invalida",
        })

        return resultado


    # ========================================================
    # ODD ANTERIOR
    # ========================================================

    anterior = _odds_anteriores.get(
        chave
    )


    # ========================================================
    # PRIMEIRA CONSULTA
    # ========================================================

    if anterior is None:

        variacao = 0.0

    else:

        variacao = calcular_variacao_odd(
            anterior,
            atual
        )


    # ========================================================
    # CALCULA IPM
    # ========================================================

    resultado = calcular_ipm(
        variacao,
        minuto,
        gols,
        escanteios,
        finalizacoes,
        ataques_perigosos
    )


    # ========================================================
    # INFORMAÇÕES DA MEMÓRIA
    # ========================================================

    resultado.update({

        "odd_anterior":
            anterior,

        "odd_atual":
            atual,

        "primeira_consulta":
            anterior is None,
    })


    # ========================================================
    # SALVA NOVA ODD
    # ========================================================

    _odds_anteriores[
        chave
    ] = atual

    return resultado


# ============================================================
# LIMPAR MEMÓRIA
# ============================================================

def limpar_memoria():

    _odds_anteriores.clear()


# ============================================================
# FORMATAR RADAR
# ============================================================

def formatar_radar(
    jogo,
    resultado,
    mercados=None
):

    if not isinstance(
        jogo,
        dict
    ):

        jogo = {}

    if not isinstance(
        resultado,
        dict
    ):

        resultado = {}


    casa = (
        jogo.get("home")
        or "Casa"
    )

    fora = (
        jogo.get("away")
        or "Fora"
    )


    primeira = resultado.get(
        "primeira_consulta",
        False
    )

    variacao = resultado.get(
        "variacao_odd",
        0.0
    )


    texto_variacao = (

        "AGUARDANDO COMPARAÇÃO"

        if primeira

        else
        f"{variacao:+.2f}%"
    )


    linhas = [

        "",

        "=" * 70,

        "📡 IPM RADAR V4.1",

        "=" * 70,

        f"⚽ {casa} x {fora}",

        (
            f"⏱️ Minuto: "
            f"{resultado.get('minuto', 0)}"
        ),

        (
            f"📊 Placar: "
            f"{resultado.get('gols', 0)} gols"
        ),

        (
            f"💰 Odd empate anterior: "
            f"{resultado.get('odd_anterior')}"
        ),

        (
            f"💰 Odd empate atual: "
            f"{resultado.get('odd_atual')}"
        ),

        (
            f"📈 Variação: "
            f"{texto_variacao}"
        ),

        (
            f"🔥 Força: "
            f"{resultado.get('forca', 'ESTAVEL')}"
        ),

        (
            f"🎯 IPM: "
            f"{resultado.get('ipm', 0):.2f}/100"
        ),

        (
            f"⚽ Gols: "
            f"{resultado.get('gols', 0)}"
        ),

        (
            f"🚩 Escanteios: "
            f"{resultado.get('escanteios', 0)}"
        ),

        (
            f"🥅 Finalizações: "
            f"{resultado.get('finalizacoes', 0)}"
        ),

        (
            f"⚡ Ataques perigosos: "
            f"{resultado.get('ataques_perigosos', 0)}"
        ),
    ]


    if isinstance(
        mercados,
        dict
    ):

        linhas.extend([

            (
                "📦 Todos os mercados: "
                f"{len(mercados.get('todos', []))}"
            ),

            (
                "📊 Mercados FT: "
                f"{len(mercados.get('odds_ft', []))}"
            ),

            (
                "⏱️ Mercados HT: "
                f"{len(mercados.get('odds_ht', []))}"
            ),

            (
                "🚩 Mercados escanteios: "
                f"{len(mercados.get('odds_corners', []))}"
            ),

            (
                "🟨 Mercados cartões: "
                f"{len(mercados.get('odds_cards', []))}"
            ),
        ])


    linhas.append(
        "=" * 70
    )

    return "\n".join(
        linhas
        )
