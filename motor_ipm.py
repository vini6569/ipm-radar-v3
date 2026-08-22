# ============================================================
# MOTOR IPM
# INDICE DE PRESSAO DE MOVIMENTACAO
# IPM-RADAR-V3
#
# Funcao:
# Analisa movimentacao das odds e calcula o IPM.
#
# IMPORTANTE:
# Este modulo NAO realiza apostas.
# Apenas analisa dados.
# ============================================================


# ============================================================
# CALCULAR VARIACAO DA ODD
# ============================================================

def calcular_variacao_odd(
    odd_inicial,
    odd_atual
):
    """
    Calcula a variacao percentual da odd.

    Exemplo:

    Odd inicial: 2.00
    Odd atual:   1.80

    Resultado:
    -10.00%
    """

    try:

        inicial = float(
            odd_inicial
        )

        atual = float(
            odd_atual
        )

        if inicial <= 0:

            return 0.0

        variacao = (
            (atual - inicial)
            / inicial
        ) * 100.0

        return variacao

    except (
        TypeError,
        ValueError
    ):

        return 0.0


# ============================================================
# CLASSIFICAR FORCA DA MOVIMENTACAO
# ============================================================

def classificar_forca(
    variacao_pct
):
    """
    Classifica a intensidade
    da movimentacao da odd.
    """

    try:

        valor = abs(
            float(variacao_pct)
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
    """
    Calcula o IPM em escala de 0 a 100.

    A movimentacao da odd e o principal
    componente do indice.

    Os dados da partida funcionam
    como confirmacao.
    """

    try:

        movimento = min(
            abs(
                float(variacao_odd)
            ) * 5.0,
            60.0
        )

        confirmacao_gols = min(
            max(
                int(gols),
                0
            ) * 5.0,
            10.0
        )

        confirmacao_escanteios = min(
            max(
                int(escanteios),
                0
            ) * 1.5,
            10.0
        )

        confirmacao_finalizacoes = min(
            max(
                int(finalizacoes),
                0
            ) * 0.5,
            10.0
        )

        confirmacao_ataques = min(
            max(
                int(ataques_perigosos),
                0
            ) * 0.2,
            10.0
        )

        ipm = (
            movimento
            + confirmacao_gols
            + confirmacao_escanteios
            + confirmacao_finalizacoes
            + confirmacao_ataques
        )

        return round(
            min(
                ipm,
                100.0
            ),
            2
        )

    except (
        TypeError,
        ValueError
    ):

        return 0.0


# ============================================================
# ANALISAR IPM
# ============================================================

def analisar_ipm(
    odd_inicial,
    odd_atual,
    minuto=0,
    gols=0,
    escanteios=0,
    finalizacoes=0,
    ataques_perigosos=0
):
    """
    Executa a analise completa do IPM.
    """

    variacao = calcular_variacao_odd(
        odd_inicial,
        odd_atual
    )

    # ========================================================
    # DIRECAO
    # ========================================================

    if variacao < -0.05:

        direcao = "QUEDA"

    elif variacao > 0.05:

        direcao = "ALTA"

    else:

        direcao = "ESTAVEL"

    # ========================================================
    # FORCA
    # ========================================================

    forca = classificar_forca(
        variacao
    )

    # ========================================================
    # IPM
    # ========================================================

    ipm = calcular_ipm(
        variacao,
        minuto,
        gols,
        escanteios,
        finalizacoes,
        ataques_perigosos
    )

    # ========================================================
    # SINAL
    # ========================================================

    if ipm >= 80:

        sinal = "SINAL MUITO FORTE"

    elif ipm >= 65:

        sinal = "SINAL FORTE"

    elif ipm >= 50:

        sinal = "OBSERVAR"

    else:

        sinal = "SEM SINAL"

    # ========================================================
    # RESULTADO
    # ========================================================

    try:

        odd_inicial_resultado = float(
            odd_inicial
        )

    except (
        TypeError,
        ValueError
    ):

        odd_inicial_resultado = 0.0

    try:

        odd_atual_resultado = float(
            odd_atual
        )

    except (
        TypeError,
        ValueError
    ):

        odd_atual_resultado = 0.0

    return {

        "odd_inicial":
            odd_inicial_resultado,

        "odd_atual":
            odd_atual_resultado,

        "variacao_pct":
            round(
                variacao,
                2
            ),

        "direcao":
            direcao,

        "forca":
            forca,

        "ipm":
            ipm,

        "sinal":
            sinal
    }


# ============================================================
# FORMATAR RADAR
# ============================================================

def formatar_radar(
    resultado
):
    """
    Formata o resultado do IPM
    para exibicao no terminal.
    """

    if not isinstance(
        resultado,
        dict
    ):

        return (
            "\n"
            "==============================\n"
            "          RADAR IPM\n"
            "==============================\n"
            "Resultado invalido.\n"
            "==============================\n"
        )

    return (
        "\n"
        "==============================\n"
        "          RADAR IPM\n"
        "==============================\n"
        f"Odd inicial: "
        f"{resultado.get('odd_inicial', 0):.2f}\n"
        f"Odd atual: "
        f"{resultado.get('odd_atual', 0):.2f}\n"
        f"Variacao: "
        f"{resultado.get('variacao_pct', 0):.2f}%\n"
        f"Movimento: "
        f"{resultado.get('direcao', 'ESTAVEL')}\n"
        f"Forca: "
        f"{resultado.get('forca', 'ESTAVEL')}\n"
        f"IPM: "
        f"{resultado.get('ipm', 0):.0f}/100\n"
        f"Sinal: "
        f"{resultado.get('sinal', 'SEM SINAL')}\n"
        "==============================\n"
        )
