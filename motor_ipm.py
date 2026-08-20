# ============================================================
# MOTOR IPM - INDICE DE PRESSAO DE MOVIMENTACAO
# IPM-RADAR-V3
#
# Funcao:
# Calcula a movimentacao das odds e gera um indice IPM.
#
# IMPORTANTE:
# Este modulo NAO realiza apostas.
# Apenas analisa dados.
# ============================================================


def calcular_variacao_odd(odd_inicial, odd_atual):
    """
    Calcula a variacao percentual da odd.

    Exemplo:
    odd inicial = 2.00
    odd atual   = 1.80

    Resultado = -10%
    """

    try:
        inicial = float(odd_inicial)
        atual = float(odd_atual)

        if inicial <= 0:
            return 0.0

        return ((atual - inicial) / inicial) * 100.0

    except (TypeError, ValueError):
        return 0.0


def classificar_forca(variacao_pct):
    """
    Classifica a intensidade da movimentacao da odd.
    """

    valor = abs(float(variacao_pct))

    if valor >= 10:
        return "MUITO FORTE"

    if valor >= 5:
        return "FORTE"

    if valor >= 2:
        return "MODERADO"

    if valor >= 0.5:
        return "FRACO"

    return "ESTAVEL"


def calcular_ipm(
    variacao_odd,
    minuto=0,
    gols=0,
    escanteios=0,
    finalizacoes=0,
    ataques_perigosos=0
):
    """
    Calcula o IPM em uma escala de 0 a 100.

    A movimentacao da odd e o principal componente.
    Os dados da partida funcionam como confirmacao.
    """

    try:
        movimento = min(
            abs(float(variacao_odd)) * 5.0,
            60.0
        )

        confirmacao_gols = min(
            max(int(gols), 0) * 5.0,
            10.0
        )

        confirmacao_escanteios = min(
            max(int(escanteios), 0) * 1.5,
            10.0
        )

        confirmacao_finalizacoes = min(
            max(int(finalizacoes), 0) * 0.5,
            10.0
        )

        confirmacao_ataques = min(
            max(int(ataques_perigosos), 0) * 0.2,
            10.0
        )

        ipm = (
            movimento
            + confirmacao_gols
            + confirmacao_escanteios
            + confirmacao_finalizacoes
            + confirmacao_ataques
        )

        return round(min(ipm, 100.0), 2)

    except (TypeError, ValueError):
        return 0.0


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

    if variacao < -0.05:
        direcao = "QUEDA"

    elif variacao > 0.05:
        direcao = "ALTA"

    else:
        direcao = "ESTAVEL"

    forca = classificar_forca(variacao)

    ipm = calcular_ipm(
        variacao,
        minuto,
        gols,
        escanteios,
        finalizacoes,
        ataques_perigosos
    )

    if ipm >= 80:
        sinal = "SINAL MUITO FORTE"

    elif ipm >= 65:
        sinal = "SINAL FORTE"

    elif ipm >= 50:
        sinal = "OBSERVAR"

    else:
        sinal = "SEM SINAL"

    return {
        "odd_inicial": float(odd_inicial),
        "odd_atual": float(odd_atual),
        "variacao_pct": round(variacao, 2),
        "direcao": direcao,
        "forca": forca,
        "ipm": ipm,
        "sinal": sinal
    }


def formatar_radar(resultado):
    """
    Formata o resultado para exibicao.
    """

    return (
        "\n"
        "==============================\n"
        "          RADAR IPM\n"
        "==============================\n"
        f"Odd inicial: {resultado['odd_inicial']:.2f}\n"
        f"Odd atual: {resultado['odd_atual']:.2f}\n"
        f"Variacao: {resultado['variacao_pct']:.2f}%\n"
        f"Movimento: {resultado['direcao']}\n"
        f"Forca: {resultado['forca']}\n"
        f"IPM: {resultado['ipm']:.0f}/100\n"
        f"Sinal: {resultado['sinal']}\n"
        "==============================\n"
      )
