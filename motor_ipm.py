# ============================================================
# MOTOR IPM - RADAR V4.4
# CASA + EMPATE + VISITANTE
# TRAJETÓRIA + PROJEÇÃO 45' + IPM
# ============================================================

from datetime import datetime


# ------------------------------------------------------------
# MEMÓRIA DOS JOGOS
# ------------------------------------------------------------

_MEMORIA = {}


def _numero(valor, padrao=0.0):
    try:
        if valor in (None, ""):
            return padrao
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def _inteiro(valor, padrao=0):
    try:
        if valor in (None, ""):
            return padrao
        return int(float(valor))
    except (TypeError, ValueError):
        return padrao


# ------------------------------------------------------------
# MEMÓRIA
# ------------------------------------------------------------

def _obter_memoria(event_id):
    chave = str(event_id)

    if chave not in _MEMORIA:
        _MEMORIA[chave] = {
            "historico": [],
            "odd_casa_inicial": None,
            "odd_empate_inicial": None,
            "odd_visitante_inicial": None,
            "ultima_odd_casa": None,
            "ultima_odd_empate": None,
            "ultima_odd_visitante": None,
            "ultimo_minuto": 0,
        }

    return _MEMORIA[chave]


# ------------------------------------------------------------
# PERCENTUAL DE VARIAÇÃO
# ------------------------------------------------------------

def _variacao_percentual(inicial, atual):
    inicial = _numero(inicial)
    atual = _numero(atual)

    if inicial <= 0 or atual <= 0:
        return 0.0

    return ((atual - inicial) / inicial) * 100.0


# ------------------------------------------------------------
# MOVIMENTO DA ODD
# ------------------------------------------------------------

def _movimento_odd(anterior, atual):
    anterior = _numero(anterior)
    atual = _numero(atual)

    if anterior <= 0 or atual <= 0:
        return 0.0

    return ((atual - anterior) / anterior) * 100.0


# ------------------------------------------------------------
# PROJEÇÃO DA ODD DE EMPATE PARA 45'
#
# A ideia é observar:
#
# CASA ↓ + VISITANTE ↓
#        ↓
#   pressão sobre o empate
#
# CASA ↑ + VISITANTE ↑
#        ↓
#   cenário diferente
#
# A projeção usa as três odds, mas dá maior peso
# às odds Casa e Visitante.
# ------------------------------------------------------------

def _calcular_referencia_45(
    odd_casa,
    odd_empate,
    odd_visitante,
    minuto,
):
    odd_casa = _numero(odd_casa)
    odd_empate = _numero(odd_empate)
    odd_visitante = _numero(odd_visitante)
    minuto = _numero(minuto)

    if odd_casa <= 0 or odd_visitante <= 0:
        return 0.0

    if minuto <= 0:
        return odd_empate

    # Normalização simples das probabilidades implícitas.
    p_casa = 1.0 / odd_casa
    p_empate = 1.0 / odd_empate if odd_empate > 0 else 0.0
    p_visitante = 1.0 / odd_visitante

    soma = p_casa + p_empate + p_visitante

    if soma <= 0:
        return odd_empate

    p_casa /= soma
    p_empate /= soma
    p_visitante /= soma

    # Quanto mais próximo dos 45', maior o peso da leitura atual.
    fator_tempo = min(max(minuto / 45.0, 0.0), 1.0)

    # Referência estrutural usando Casa + Visitante.
    soma_lados = p_casa + p_visitante

    if soma_lados <= 0:
        return odd_empate

    # A participação relativa do empate.
    participacao_empate = p_empate / soma

    # Ajuste progressivo até o intervalo dos 45'.
    alvo_probabilidade = (
        participacao_empate * (1.0 - fator_tempo)
        + (p_empate * fator_tempo)
    )

    if alvo_probabilidade <= 0:
        return odd_empate

    odd_projetada = 1.0 / alvo_probabilidade

    # Evita valores absurdos.
    if odd_projetada < 1.01:
        odd_projetada = 1.01

    if odd_projetada > 50:
        odd_projetada = 50.0

    return odd_projetada


# ------------------------------------------------------------
# IPM
#
# O IPM NÃO É UMA PROBABILIDADE DE GOL.
# É UM ÍNDICE EXPERIMENTAL DE MOVIMENTAÇÃO.
#
# Quanto maior:
# maior a alteração observada nas odds.
# ------------------------------------------------------------

def _calcular_ipm(
    odd_casa_inicial,
    odd_empate_inicial,
    odd_visitante_inicial,
    odd_casa,
    odd_empate,
    odd_visitante,
    minuto,
):
    minuto = _numero(minuto)

    var_casa = _variacao_percentual(
        odd_casa_inicial,
        odd_casa,
    )

    var_empate = _variacao_percentual(
        odd_empate_inicial,
        odd_empate,
    )

    var_visitante = _variacao_percentual(
        odd_visitante_inicial,
        odd_visitante,
    )

    # Peso maior para Casa e Visitante.
    movimento_lados = (
        abs(var_casa) * 0.40
        +
        abs(var_visitante) * 0.40
    )

    movimento_empate = abs(var_empate) * 0.20

    ipm_bruto = movimento_lados + movimento_empate

    # Normalização para facilitar leitura.
    ipm = ipm_bruto * 10.0

    # Pequeno ajuste temporal.
    if minuto > 0:
        fator = min(minuto / 45.0, 1.0)
        ipm = ipm * (0.75 + (0.25 * fator))

    return max(0.0, min(ipm, 100.0))


# ------------------------------------------------------------
# ANÁLISE PRINCIPAL
# ------------------------------------------------------------

def analisar_ipm_com_memoria(
    event_id,
    odd_atual,
    minuto,
    gols,
    escanteios,
    finalizacoes,
    ataques_perigosos,
    odd_pre_live=None,
    odd_casa=None,
    odd_visitante=None,
):
    """
    Mantém a assinatura compatível com o main.py antigo.

    Os dados de escanteios, finalizações e ataques são
    deliberadamente ignorados na matemática atual.

    O radar trabalha principalmente com:

        CASA
        EMPATE
        VISITANTE
    """

    memoria = _obter_memoria(event_id)

    minuto = _inteiro(minuto)
    gols = _inteiro(gols)

    # --------------------------------------------------------
    # COMPATIBILIDADE
    #
    # O main atual passa somente odd_atual.
    # Para a nova matemática, CASA e VISITANTE precisam chegar.
    #
    # Se ainda não chegarem, usamos 0 e o IPM fica aguardando.
    # --------------------------------------------------------

    odd_empate = _numero(odd_atual)
    odd_casa = _numero(odd_casa)
    odd_visitante = _numero(odd_visitante)

    # --------------------------------------------------------
    # PRIMEIRA LEITURA
    # --------------------------------------------------------

    if (
        memoria["odd_casa_inicial"] is None
        and odd_casa > 0
    ):
        memoria["odd_casa_inicial"] = odd_casa

    if (
        memoria["odd_empate_inicial"] is None
        and odd_empate > 0
    ):
        memoria["odd_empate_inicial"] = odd_empate

    if (
        memoria["odd_visitante_inicial"] is None
        and odd_visitante > 0
    ):
        memoria["odd_visitante_inicial"] = odd_visitante

    # --------------------------------------------------------
    # REFERÊNCIA PRÉ-LIVE DO EMPATE
    # --------------------------------------------------------

    if (
        memoria["odd_empate_inicial"] is None
        and _numero(odd_pre_live) > 0
    ):
        memoria["odd_empate_inicial"] = _numero(odd_pre_live)

    # --------------------------------------------------------
    # VARIAÇÕES
    # --------------------------------------------------------

    odd_casa_ini = _numero(memoria["odd_casa_inicial"])
    odd_empate_ini = _numero(memoria["odd_empate_inicial"])
    odd_visitante_ini = _numero(memoria["odd_visitante_inicial"])

    var_casa = _variacao_percentual(
        odd_casa_ini,
        odd_casa,
    )

    var_empate = _variacao_percentual(
        odd_empate_ini,
        odd_empate,
    )

    var_visitante = _variacao_percentual(
        odd_visitante_ini,
        odd_visitante,
    )

    # --------------------------------------------------------
    # VARIAÇÃO DESDE O ÚLTIMO CICLO
    # --------------------------------------------------------

    var_ciclo = _movimento_odd(
        memoria["ultima_odd_empate"],
        odd_empate,
    )

    # --------------------------------------------------------
    # REFERÊNCIA 45'
    # --------------------------------------------------------

    odd_45 = _calcular_referencia_45(
        odd_casa,
        odd_empate,
        odd_visitante,
        minuto,
    )

    # --------------------------------------------------------
    # DIFERENÇA ENTRE EMPATE ATUAL E REFERÊNCIA 45'
    # --------------------------------------------------------

    diferenca_45 = 0.0

    if odd_empate > 0 and odd_45 > 0:
        diferenca_45 = (
            (odd_empate - odd_45)
            / odd_45
        ) * 100.0

    # --------------------------------------------------------
    # IPM
    # --------------------------------------------------------

    ipm = _calcular_ipm(
        odd_casa_ini,
        odd_empate_ini,
        odd_visitante_ini,
        odd_casa,
        odd_empate,
        odd_visitante,
        minuto,
    )

    # --------------------------------------------------------
    # TRAJETÓRIA
    # --------------------------------------------------------

    registro = {
        "hora": datetime.now().strftime("%H:%M:%S"),
        "minuto": minuto,
        "odd_casa": odd_casa,
        "odd_empate": odd_empate,
        "odd_visitante": odd_visitante,
        "variacao_casa": var_casa,
        "variacao_empate": var_empate,
        "variacao_visitante": var_visitante,
        "odd_45": odd_45,
        "diferenca_45": diferenca_45,
        "ipm": ipm,
        "gols": gols,
    }

    memoria["historico"].append(registro)

    # Mantém somente as últimas 100 leituras.
    memoria["historico"] = memoria["historico"][-100:]

    memoria["ultima_odd_casa"] = odd_casa
    memoria["ultima_odd_empate"] = odd_empate
    memoria["ultima_odd_visitante"] = odd_visitante
    memoria["ultimo_minuto"] = minuto

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    return {
        "event_id": event_id,

        "minuto": minuto,
        "gols": gols,

        # ODDS
        "odd_casa": odd_casa,
        "odd_atual": odd_empate,
        "odd_empate": odd_empate,
        "odd_visitante": odd_visitante,

        # REFERÊNCIAS
        "odd_pre_live": (
            _numero(odd_pre_live)
            if _numero(odd_pre_live) > 0
            else odd_empate_ini
        ),

        "odd_casa_inicial": odd_casa_ini,
        "odd_empate_inicial": odd_empate_ini,
        "odd_visitante_inicial": odd_visitante_ini,

        # VARIAÇÕES
        "variacao_casa": var_casa,
        "variacao_pre_live": _variacao_percentual(
            _numero(odd_pre_live)
            if _numero(odd_pre_live) > 0
            else odd_empate_ini,
            odd_empate,
        ),
        "variacao_empate": var_empate,
        "variacao_visitante": var_visitante,
        "variacao_ciclo": var_ciclo,

        # PROJEÇÃO
        "odd_45": odd_45,
        "diferenca_45": diferenca_45,

        # IPM
        "ipm": ipm,

        # TRAJETÓRIA
        "historico_odds": memoria["historico"],
    }


# ------------------------------------------------------------
# AVALIAÇÃO DE ENTRADA
#
# Mantida para não quebrar o main.py.
#
# IMPORTANTE:
# nesta fase a entrada continua sendo experimental.
# ------------------------------------------------------------

def avaliar_entrada(
    resultado,
    minuto,
    ipm_minimo,
    variacao_minima,
    minuto_minimo,
    minuto_maximo,
):
    try:
        minuto = int(minuto)
    except (TypeError, ValueError):
        return False

    ipm = _numero(resultado.get("ipm"))

    variacao = abs(
        _numero(resultado.get("variacao_pre_live"))
    )

    if minuto < minuto_minimo:
        return False

    if minuto > minuto_maximo:
        return False

    if ipm < _numero(ipm_minimo):
        return False

    if variacao < _numero(variacao_minima):
        return False

    return True


# ------------------------------------------------------------
# JOGO FINALIZADO
# ------------------------------------------------------------

def jogo_finalizado(jogo):
    if not isinstance(jogo, dict):
        return False

    status = str(
        jogo.get("status")
        or jogo.get("state")
        or jogo.get("matchStatus")
        or ""
    ).strip().lower()

    finais = (
        "finished",
        "ft",
        "final",
        "ended",
        "complete",
        "completed",
    )

    return (
        status in finais
        or
        status.startswith("finished")
        or
        status.startswith("ended")
    )


# ------------------------------------------------------------
# RESULTADO EMPATE
# ------------------------------------------------------------

def resultado_empate(jogo, mercados=None):
    if not isinstance(jogo, dict):
        return None

    scores = jogo.get("scores")

    if isinstance(scores, dict):
        casa = scores.get("home")
        fora = scores.get("away")

        if casa is not None and fora is not None:
            return _inteiro(casa) == _inteiro(fora)

    for chave in ("score", "result"):
        valor = jogo.get(chave)

        if isinstance(valor, dict):
            casa = valor.get(
                "home",
                valor.get("homeScore")
            )

            fora = valor.get(
                "away",
                valor.get("awayScore")
            )

            if casa is not None and fora is not None:
                return _inteiro(casa) == _inteiro(fora)

        if isinstance(valor, list) and len(valor) >= 2:
            return _inteiro(valor[0]) == _inteiro(valor[1])

    casa = jogo.get("homeScore")
    fora = jogo.get("awayScore")

    if casa is not None and fora is not None:
        return _inteiro(casa) == _inteiro(fora)

    return None


# ------------------------------------------------------------
# FORMATAÇÃO DO RADAR
# ------------------------------------------------------------

def formatar_radar(jogo, resultado, mercados=None):
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

    minuto = _inteiro(resultado.get("minuto"))

    placar_casa = 0
    placar_fora = 0

    scores = jogo.get("scores")

    if isinstance(scores, dict):
        placar_casa = _inteiro(scores.get("home"))
        placar_fora = _inteiro(scores.get("away"))

    odd_casa = _numero(resultado.get("odd_casa"))
    odd_empate = _numero(resultado.get("odd_empate"))
    odd_visitante = _numero(resultado.get("odd_visitante"))

    odd_45 = _numero(resultado.get("odd_45"))
    ipm = _numero(resultado.get("ipm"))

    var_casa = _numero(resultado.get("variacao_casa"))
    var_empate = _numero(resultado.get("variacao_empate"))
    var_visitante = _numero(resultado.get("variacao_visitante"))

    diferenca_45 = _numero(
        resultado.get("diferenca_45")
    )

    return (
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚽ {casa} x {fora}\n"
        f"⏱️ Minuto: {minuto}'\n"
        f"📊 Placar: {placar_casa} x {placar_fora}\n"
        "\n"
        "💰 ODDS\n"
        f"🏠 Casa:      {odd_casa:.2f} "
        f"({var_casa:+.2f}%)\n"
        f"🤝 Empate:    {odd_empate:.2f} "
        f"({var_empate:+.2f}%)\n"
        f"🚌 Visitante: {odd_visitante:.2f} "
        f"({var_visitante:+.2f}%)\n"
        "\n"
        "🎯 REFERÊNCIA 45'\n"
        f"🤝 Odd projetada: {odd_45:.2f}\n"
        f"📐 Diferença atual: {diferenca_45:+.2f}%\n"
        "\n"
        f"📈 IPM: {ipm:.2f}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
