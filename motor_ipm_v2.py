# ============================================================
# MOTOR IPM V2
# IPM RADAR V3
# COMPARACAO REAL DE ODDS ENTRE CONSULTAS
# ============================================================

_odds_anteriores = {}


# ============================================================
# CONVERTER ODD
# ============================================================

def _converter_odd(valor):

    try:

        valor = float(valor)

        if valor <= 0:
            return None

        return valor

    except (TypeError, ValueError):

        return None


# ============================================================
# VARIACAO DA ODD
# ============================================================

def calcular_variacao_odd(
    odd_anterior,
    odd_atual
):

    anterior = _converter_odd(odd_anterior)
    atual = _converter_odd(odd_atual)

    if anterior is None or atual is None:
        return 0.0

    return (
        (atual - anterior)
        / anterior
    ) * 100.0


# ============================================================
# FORCA DO MOVIMENTO
# ============================================================

def classificar_forca(variacao_odd):

    try:

        valor = abs(float(variacao_odd))

    except (TypeError, ValueError):

        return "ESTAVEL"

    if valor >= 10:
        return "MUITO FORTE"

    elif valor >= 5:
        return "FORTE"

    elif valor >= 2:
        return "MODERADO"

    elif valor >= 0.5:
        return "FRACO"

    return "ESTAVEL"


# ============================================================
# CALCULO DO IPM
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

        # ----------------------------------------------------
        # MOVIMENTO DA ODD
        # MAXIMO = 60
        # ----------------------------------------------------

        movimento = min(
            abs(float(variacao_odd)) * 5.0,
            60.0
        )

        # ----------------------------------------------------
        # GOLS
        # MAXIMO = 10
        # ----------------------------------------------------

        confirmacao_gols = min(
            max(int(gols), 0) * 5.0,
            10.0
        )

        # ----------------------------------------------------
        # ESCANTEIOS
        # MAXIMO = 10
        # ----------------------------------------------------

        confirmacao_escanteios = min(
            max(int(escanteios), 0) * 1.5,
            10.0
        )

        # ----------------------------------------------------
        # FINALIZACOES
        # MAXIMO = 10
        # ----------------------------------------------------

        confirmacao_finalizacoes = min(
            max(int(finalizacoes), 0) * 0.5,
            10.0
        )

        # ----------------------------------------------------
        # ATAQUES PERIGOSOS
        # MAXIMO = 10
        # ----------------------------------------------------

        confirmacao_ataques = min(
            max(int(ataques_perigosos), 0) * 0.2,
            10.0
        )

        # ----------------------------------------------------
        # IPM FINAL
        # ----------------------------------------------------

        ipm = (
            movimento
            + confirmacao_gols
            + confirmacao_escanteios
            + confirmacao_finalizacoes
            + confirmacao_ataques
        )

        ipm = max(
            0.0,
            min(ipm, 100.0)
        )

        return {

            "ipm": round(ipm, 2),

            "variacao_odd": round(
                float(variacao_odd),
                2
            ),

            "forca": classificar_forca(
                variacao_odd
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
# ANALISE DIRETA
# ============================================================

def analisar_ipm(
    odd_anterior,
    odd_atual,
    minuto=0,
    gols=0,
    escanteios=0,
    finalizacoes=0,
    ataques_perigosos=0
):

    variacao = calcular_variacao_odd(
        odd_anterior,
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

    resultado["odd_anterior"] = odd_anterior
    resultado["odd_atual"] = odd_atual
    resultado["primeira_consulta"] = False

    return resultado


# ============================================================
# ANALISE COM MEMORIA
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
            "chave_jogo e obrigatoria"
        )

    chave = str(chave_jogo)

    atual = _converter_odd(
        odd_atual
    )

    # --------------------------------------------------------
    # ODD INVALIDA
    # --------------------------------------------------------

    if atual is None:

        resultado = calcular_ipm(
            0.0,
            minuto,
            gols,
            escanteios,
            finalizacoes,
            ataques_perigosos
        )

        resultado["odd_anterior"] = None
        resultado["odd_atual"] = odd_atual
        resultado["primeira_consulta"] = False
        resultado["erro"] = "odd_atual_invalida"

        return resultado

    # --------------------------------------------------------
    # BUSCA ODD ANTERIOR
    # --------------------------------------------------------

    anterior = _odds_anteriores.get(
        chave
    )

    # ========================================================
    # PRIMEIRA CONSULTA
    # ========================================================

    if anterior is None:

        resultado = calcular_ipm(
            0.0,
            minuto,
            gols,
            escanteios,
            finalizacoes,
            ataques_perigosos
        )

        resultado["odd_anterior"] = None
        resultado["odd_atual"] = atual
        resultado["primeira_consulta"] = True

        print(
            f"🆕 PRIMEIRA ODD | "
            f"Jogo {chave} | "
            f"Odd {atual}"
        )

    # ========================================================
    # CONSULTAS SEGUINTES
    # ========================================================

    else:

        variacao = calcular_variacao_odd(
            anterior,
            atual
        )

        resultado = calcular_ipm(
            variacao,
            minuto,
            gols,
            escanteios,
            finalizacoes,
            ataques_perigosos
        )

        resultado["odd_anterior"] = anterior
        resultado["odd_atual"] = atual
        resultado["primeira_consulta"] = False

        print(
            f"📊 COMPARACAO | "
            f"Jogo {chave} | "
            f"Anterior {anterior} | "
            f"Atual {atual} | "
            f"Variacao {variacao:.2f}%"
        )

    # --------------------------------------------------------
    # SALVA A ODD ATUAL
    # --------------------------------------------------------

    _odds_anteriores[chave] = atual

    return resultado


# ============================================================
# LIMPAR MEMORIA DE UM JOGO
# ============================================================

def limpar_memoria_jogo(chave_jogo):

    _odds_anteriores.pop(
        str(chave_jogo),
        None
    )


# ============================================================
# LIMPAR TODA MEMORIA
# ============================================================

def limpar_memoria():

    _odds_anteriores.clear()


# ============================================================
# FORMATAR RADAR
# ============================================================

def formatar_radar(
    jogo,
    resultado
):

    try:

        if not isinstance(jogo, dict):
            jogo = {}

        if not isinstance(resultado, dict):
            return None

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

        odd_anterior = resultado.get(
            "odd_anterior"
        )

        odd_atual = resultado.get(
            "odd_atual"
        )

        primeira = resultado.get(
            "primeira_consulta",
            False
        )

        if primeira:

            movimento_texto = "AGUARDANDO COMPARACAO"

        else:

            movimento_texto = (
                f"{variacao:.2f}%"
            )

        texto = (

            "\n"
            "============================================================\n"
            "📡 IPM RADAR V3\n"
            "============================================================\n"

            f"⚽ {casa} x {fora}\n"

            f"⏱️ Minuto: {minuto}\n"

            f"💰 Odd anterior: {odd_anterior}\n"

            f"💰 Odd atual: {odd_atual}\n"

            f"📈 Variacao da odd: "
            f"{movimento_texto}\n"

            f"🔥 Forca: {forca}\n"

            f"🎯 IPM: {ipm:.2f}/100\n"

            f"⚽ Gols: {gols}\n"

            f"🚩 Escanteios: {escanteios}\n"

            f"🥅 Finalizacoes: {finalizacoes}\n"

            f"⚡ Ataques perigosos: {ataques}\n"

            "============================================================"
        )

        return texto

    except Exception as erro:

        return (
            "📊 IPM: erro ao formatar radar: "
            f"{erro}"
        )
