# ============================================================
# MOTOR IPM - V2
# INDICE DE PRESSAO DE MOVIMENTACAO
# IPM-RADAR-V3
#
# VERSAO NOVA - ORIGINAL PRESERVADO
#
# Objetivo:
# - Comparar ODD ANTERIOR x ODD ATUAL
# - Calcular a variacao percentual
# - Transformar a movimentacao em pontos de IPM
# - Usar os eventos da partida como confirmacao
#
# IMPORTANTE:
# Este modulo NAO realiza apostas.
# Apenas analisa dados.
#
# ATENCAO:
# O motor matematico NAO consegue descobrir sozinho a odd
# anterior se o main.py continuar enviando a mesma odd como
# "inicial" a cada consulta.
#
# Para detectar movimentacao entre consultas, o chamador precisa
# fornecer a ODD ANTERIOR real ou utilizar a funcao com memoria
# deste arquivo.
# ============================================================


# ============================================================
# MEMORIA DE ODDS
# ============================================================

# Guarda a ultima odd conhecida por jogo.
# Esta memoria existe somente durante a execucao do processo.
_odds_anteriores = {}


# ============================================================
# CONVERTER ODD COM SEGURANCA
# ============================================================

def _converter_odd(valor):
    """
    Converte uma odd para float com seguranca.
    Retorna None quando o valor nao e valido.
    """

    try:
        resultado = float(valor)

        if resultado <= 0:
            return None

        return resultado

    except (TypeError, ValueError):
        return None


# ============================================================
# CALCULAR VARIACAO DA ODD
# ============================================================

def calcular_variacao_odd(
    odd_anterior,
    odd_atual
):
    """
    Calcula a variacao percentual entre a ODD ANTERIOR
    e a ODD ATUAL.

    Exemplo:

    Odd anterior = 2.00
    Odd atual    = 1.80

    Resultado = -10.00%

    IMPORTANTE:
    Aqui nao existe mais o conceito matematico de
    "odd inicial" para detectar movimento.

    O objetivo do radar e detectar:
        consulta anterior -> consulta atual
    """

    anterior = _converter_odd(odd_anterior)
    atual = _converter_odd(odd_atual)

    if anterior is None or atual is None:
        return 0.0

    variacao = (
        (atual - anterior)
        / anterior
    ) * 100.0

    return variacao


# ============================================================
# CLASSIFICAR FORCA DA MOVIMENTACAO
# ============================================================

def classificar_forca(
    variacao_odd
):
    """
    Classifica a intensidade da movimentacao da odd.
    """

    try:
        valor = abs(float(variacao_odd))

    except (TypeError, ValueError):
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

    Distribuicao maxima:
        Movimento da odd       = 60 pontos
        Gols                   = 10 pontos
        Escanteios             = 10 pontos
        Finalizacoes           = 10 pontos
        Ataques perigosos      = 10 pontos
                              -------------
                                100 pontos

    A movimentacao da odd continua sendo o principal componente.
    Os eventos da partida funcionam como confirmacao.
    """

    try:

        # ====================================================
        # MOVIMENTACAO DA ODD
        # MAXIMO: 60 PONTOS
        #
        # 0.5%  = 2.5 pontos
        # 1.0%  = 5 pontos
        # 2.0%  = 10 pontos
        # 5.0%  = 25 pontos
        # 10.0% = 50 pontos
        # 12.0% = 60 pontos (limite)
        # ====================================================

        movimento = min(
            abs(float(variacao_odd)) * 5.0,
            60.0
        )

        # ====================================================
        # CONFIRMACAO POR GOLS
        # MAXIMO: 10 PONTOS
        # ====================================================

        confirmacao_gols = min(
            max(int(gols), 0) * 5.0,
            10.0
        )

        # ====================================================
        # CONFIRMACAO POR ESCANTEIOS
        # MAXIMO: 10 PONTOS
        # ====================================================

        confirmacao_escanteios = min(
            max(int(escanteios), 0) * 1.5,
            10.0
        )

        # ====================================================
        # CONFIRMACAO POR FINALIZACOES
        # MAXIMO: 10 PONTOS
        # ====================================================

        confirmacao_finalizacoes = min(
            max(int(finalizacoes), 0) * 0.5,
            10.0
        )

        # ====================================================
        # CONFIRMACAO POR ATAQUES PERIGOSOS
        # MAXIMO: 10 PONTOS
        # ====================================================

        confirmacao_ataques = min(
            max(int(ataques_perigosos), 0) * 0.2,
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

        ipm = max(
            0.0,
            min(ipm, 100.0)
        )

        forca = classificar_forca(
            variacao_odd
        )

        return {
            "ipm": round(ipm, 2),

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
# ANALISAR IPM - COMPATIVEL
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
    """
    Funcao principal.

    Recebe explicitamente:
        odd_anterior
        odd_atual

    e calcula:
        variacao = (atual - anterior) / anterior * 100

    Esta funcao e compativel com a chamada posicional anterior:
        analisar_ipm(valor1, valor2, ...)

    A diferenca e conceitual:
        valor1 precisa ser a ODD ANTERIOR REAL.
    """

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

    return resultado


# ============================================================
# ANALISAR IPM COM MEMORIA AUTOMATICA
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
    """
    Versao indicada quando o sistema quer comparar
    automaticamente uma consulta com a consulta anterior.

    Funcionamento:

    1a consulta:
        nao existe odd anterior
        -> IPM de movimento = 0

    2a consulta:
        compara odd anterior x odd atual

    3a consulta:
        compara a segunda odd x terceira odd

    IMPORTANTE:
    A chave_jogo deve identificar unicamente a partida.

    Exemplo:
        chave_jogo = "12345"

    Esta funcao nao altera o restante da matematica.
    Ela apenas resolve o armazenamento da ODD anterior.
    """

    if chave_jogo is None:
        raise ValueError(
            "chave_jogo e obrigatoria para usar a memoria de odds"
        )

    atual = _converter_odd(odd_atual)

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
        resultado["erro"] = "odd_atual invalida"

        return resultado

    anterior = _odds_anteriores.get(
        str(chave_jogo)
    )

    # Primeira consulta daquela partida.
    if anterior is None:

        variacao = 0.0

        resultado = calcular_ipm(
            variacao,
            minuto,
            gols,
            escanteios,
            finalizacoes,
            ataques_perigosos
        )

        resultado["odd_anterior"] = None
        resultado["odd_atual"] = atual
        resultado["primeira_consulta"] = True

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

    # Guarda a odd atual para a proxima consulta.
    _odds_anteriores[str(chave_jogo)] = atual

    return resultado


# ============================================================
# LIMPAR MEMORIA DE UM JOGO
# ============================================================

def limpar_memoria_jogo(
    chave_jogo
):
    """
    Remove a odd armazenada de uma partida.
    """

    _odds_anteriores.pop(
        str(chave_jogo),
        None
    )


# ============================================================
# LIMPAR TODA A MEMORIA
# ============================================================

def limpar_memoria():
    """
    Limpa todas as odds armazenadas.
    """

    _odds_anteriores.clear()


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

        ipm = resultado.get("ipm", 0)
        variacao = resultado.get("variacao_odd", 0)
        forca = resultado.get("forca", "ESTAVEL")
        minuto = resultado.get("minuto", 0)
        gols = resultado.get("gols", 0)
        escanteios = resultado.get("escanteios", 0)
        finalizacoes = resultado.get("finalizacoes", 0)
        ataques = resultado.get("ataques_perigosos", 0)

        odd_anterior = resultado.get(
            "odd_anterior",
            None
        )

        odd_atual = resultado.get(
            "odd_atual",
            None
        )

        texto = (
            "\n"
            "------------------------------------------------------------\n"
            "📡 IPM RADAR V2\n"
            "------------------------------------------------------------\n"
            f"⚽ {casa} x {fora}\n"
            f"⏱️ Minuto: {minuto}\n"
            f"💰 Odd anterior: {odd_anterior}\n"
            f"💰 Odd atual: {odd_atual}\n"
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
        
