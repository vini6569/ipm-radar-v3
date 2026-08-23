# ============================================================
# MOTOR IPM
# INDICE DE PRESSAO DE MOVIMENTACAO
# IPM-RADAR-V3
#
# Funcao:
# Analisa a movimentacao das odds e os dados da partida.
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

    Odd inicial = 2.00
    Odd atual   = 1.80

    Resultado = -10.00%
    """

    try:

        inicial = float(odd_inicial)
        atual = float(odd_atual)

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
    variacao_pares
):
    """
    Classifica a intensidade da movimentacao
    da odd.
    """

    try:

        valor = abs(
            float(variacao_pares)
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

        # ====================================================
        # MOVIMENTACAO DA ODD
        # MAXIMO: 60 PONTOS
        # ====================================================

        movimento = min(
            abs(
                float(variacao_odd)
            ) * 5.0,
            60.0
        )


        # ====================================================
        # CONFIRMACAO POR GOLS
        # MAXIMO: 10 PONTOS
        # ====================================================

        confirmacao_gols = min(
            max(
                int(gols),
                0
            ) * 5.0,
            10.0
        )


        # ====================================================
        # CONFIRMACAO POR ESCANTEIOS
        # MAXIMO: 10 PONTOS
        # ====================================================

        confirmacao_escanteios = min(
            max(
                int(escanteios),
                0
            ) * 1.5,
            10.0
        )


        # ====================================================
        # CONFIRMACAO POR FINALIZACOES
        # MAXIMO: 10 PONTOS
        # ====================================================

        confirmacao_finalizacoes = min(
            max(
                int(finalizacoes),
                0
            ) * 0.5,
            10.0
        )


        # ====================================================
        # CONFIRMACAO POR ATAQUES PERIGOSOS
        # MAXIMO: 10 PONTOS
        # ====================================================

        confirmacao_ataques = min(
            max(
                int(ataques_perigosos),
                0
            ) * 0.2,
            10.0
        )


        # ====================================================
        # IPM FINAL
        # ====================================================

        ipm = (
            movimento
            + confirmacao_gols
            + confirmacao_escanteios
            + confirmacao_finalizacoes
            + confirmacao_ataques
        )


        # ====================================================
        # GARANTIR ESCALA 0-100
        # ====================================================

        ipm = max(
            0.0,
            min(
                ipm,
                100.0
            )
        )


        # ====================================================
        # CLASSIFICACAO
        # ====================================================

        forca = classificar_forca(
            variacao_odd
        )


        # ====================================================
        # RETORNO
        # ====================================================

        return {

            "ipm": round(
                ipm,
                2
            ),

            "variacao_odd": round(
                float(variacao_odd),
                2
            ),

            "forca": forca,

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

            "ataques_perigosos": ataques_perigosos
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

            "ataques_perigosos": ataques_perigosos,

            "erro": str(erro)
        }


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
    Funcao principal utilizada pelo main.py.

    Recebe a odd inicial e a odd atual,
    calcula automaticamente a variacao
    e depois calcula o IPM.
    """

    variacao = calcular_variacao_odd(
        odd_inicial,
        odd_atual
    )

    resultado = calcular_ipm(
        variacao,
        minuto,
        gols,
        escanteios,
        finalizacoes,
        ataques_perigosos
    )

    # Dados adicionais
    resultado["odd_inicial"] = odd_inicial
    resultado["odd_atual"] = odd_atual

    return resultado


# ============================================================
# FORMATAR RADAR
# ============================================================

def formatar_radar(
    jogo,
    resultado
):
    """
    Formata os dados para exibicao no log.
    """

    try:

        if not isinstance(
            jogo,
            dict
        ):

            jogo = {}

        if not isinstance(
            resultado,
            dict
        ):

            return None


        # ====================================================
        # TIMES
        # ====================================================

        casa = (
            jogo.get("home")
            or jogo.get("home_team")
            or "Casa"
        )

        fora = (
            jogo.get("away")
            or jogo.get("away_team")
            or "Fora"
        )


        # ====================================================
        # DADOS IPM
        # ====================================================

        ipm = resultado.get(
            "ipm",
            0
        )

        variacao = resultado.get(
            "variacao_odd",
            0
        )

        forca = resultado.get(
            "forca",
            "ESTAVEL"
        )

        minuto = resultado.get(
            "minuto",
            0
        )

        gols = resultado.get(
            "gols",
            0
        )

        escanteios = resultado.get(
            "escanteios",
            0
        )

        finalizacoes = resultado.get(
            "finalizacoes",
            0
        )

        ataques = resultado.get(
            "ataques_perigosos",
            0
        )


        # ====================================================
        # RADAR
        # ====================================================

        texto = (
            "\n"
            "------------------------------------------------------------\n"
            "📡 IPM RADAR\n"
            "------------------------------------------------------------\n"
            f"⚽ {casa} x {fora}\n"
            f"⏱️ Minuto: {minuto}\n"
            f"📈 Variacao da odd: {variacao:.2f}%\n"
            f"🔥 Forca: {forca}\n"
            f"🎯 IPM: {ipm:.2f}/100\n"
            f"⚽ Gols: {gols}\n"
            f"🚩 Escanteios: {escanteios}\n"
            f"🥅 Finalizacoes: {finalizacoes}\n"
            f"⚡ Ataques perigosos: {ataques}\n"
            "------------------------------------------------------------"
        )

        return texto


    except Exception as erro:

        return (
            f"📊 IPM: erro ao formatar radar: {erro}"
    )
