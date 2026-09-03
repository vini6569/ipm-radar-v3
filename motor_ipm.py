# ============================================================
# MOTOR IPM - RADAR V5.1
# CASA + EMPATE + VISITANTE
# PRE-LIVE COMPLETO + TRAJETÓRIA + REFERÊNCIA 45' + MEMÓRIA
# ============================================================

from datetime import datetime


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


def _variacao_percentual(inicial, atual):
    inicial = _numero(inicial)
    atual = _numero(atual)

    if inicial <= 0 or atual <= 0:
        return 0.0

    return ((atual - inicial) / inicial) * 100.0


def _movimento_odd(anterior, atual):
    anterior = _numero(anterior)
    atual = _numero(atual)

    if anterior <= 0 or atual <= 0:
        return 0.0

    return ((atual - anterior) / anterior) * 100.0


def _variacao_10min(historico, minuto, odd_atual):
    """
    Calcula a variação percentual da odd do empate
    comparando com a odd registrada aproximadamente
    10 minutos antes.
    """

    odd_atual = _numero(odd_atual)
    minuto = _inteiro(minuto)

    if odd_atual <= 0 or minuto < 10:
        return 0.0

    minuto_referencia = minuto - 10
    registro_10min = None

    for registro in reversed(historico):
        minuto_registro = _inteiro(
            registro.get("minuto"),
            -1
        )

        if minuto_registro <= minuto_referencia:
            registro_10min = registro
            break

    if not registro_10min:
        return 0.0

    odd_10min = _numero(
        registro_10min.get("odd_empate")
    )

    if odd_10min <= 0:
        return 0.0

    return (
        (odd_atual - odd_10min)
        / odd_10min
    ) * 100.0


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

    if odd_empate <= 0:
        return 0.0

    if odd_casa <= 0 or odd_visitante <= 0:
        return odd_empate

    p_casa = 1.0 / odd_casa
    p_empate = 1.0 / odd_empate
    p_visitante = 1.0 / odd_visitante

    soma = p_casa + p_empate + p_visitante

    if soma <= 0:
        return odd_empate

    p_empate_normalizada = p_empate / soma
    fator_tempo = min(max(minuto / 45.0, 0.0), 1.0)

    alvo = (
        p_empate_normalizada * (1.0 - fator_tempo)
        + p_empate * fator_tempo
    )

    if alvo <= 0:
        return odd_empate

    return max(1.01, min(50.0, 1.0 / alvo))


def _calcular_ipm(
    odd_casa_inicial,
    odd_empate_inicial,
    odd_visitante_inicial,
    odd_casa,
    odd_empate,
    odd_visitante,
    minuto,
):
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

    movimento_lados = (
        abs(var_casa) * 0.40
        + abs(var_visitante) * 0.40
    )
    movimento_empate = abs(var_empate) * 0.20

    ipm = (movimento_lados + movimento_empate) * 10.0

    minuto = _numero(minuto)
    if minuto > 0:
        fator = min(minuto / 45.0, 1.0)
        ipm *= 0.75 + (0.25 * fator)

    return max(0.0, min(ipm, 100.0))


def analisar_ipm_com_memoria(
    chave_jogo,
    odd_atual,
    minuto=0,
    gols=0,
    escanteios=0,
    cartoes=0,
    finalizacoes=0,
    ataques_perigosos=0,
    odd_pre_live=None,
    odd_casa=None,
    odd_visitante=None,
    odd_casa_pre_live=None,
    odd_visitante_pre_live=None,
    **kwargs,
):
    if chave_jogo is None:
        raise ValueError("chave_jogo é obrigatória")

    memoria = _obter_memoria(chave_jogo)

    minuto = _inteiro(minuto)
    gols = _inteiro(gols)

    odd_empate = _numero(odd_atual)
    odd_casa = _numero(odd_casa)
    odd_visitante = _numero(odd_visitante)

    pre_live = _numero(odd_pre_live)
    pre_live_casa = _numero(odd_casa_pre_live)
    pre_live_visitante = _numero(odd_visitante_pre_live)

    # A referência inicial agora prioriza as odds pré-live dos
    # três mercados. Se não houver pré-live, usa o primeiro valor live.
    if memoria["odd_casa_inicial"] is None:
        if pre_live_casa > 0:
            memoria["odd_casa_inicial"] = pre_live_casa
        elif odd_casa > 0:
            memoria["odd_casa_inicial"] = odd_casa

    if memoria["odd_empate_inicial"] is None:
        if pre_live > 0:
            memoria["odd_empate_inicial"] = pre_live
        elif odd_empate > 0:
            memoria["odd_empate_inicial"] = odd_empate

    if memoria["odd_visitante_inicial"] is None:
        if pre_live_visitante > 0:
            memoria["odd_visitante_inicial"] = pre_live_visitante
        elif odd_visitante > 0:
            memoria["odd_visitante_inicial"] = odd_visitante

    odd_casa_ini = _numero(memoria["odd_casa_inicial"])
    odd_empate_ini = _numero(memoria["odd_empate_inicial"])
    odd_visitante_ini = _numero(memoria["odd_visitante_inicial"])

    var_casa = _variacao_percentual(odd_casa_ini, odd_casa)
    var_empate = _variacao_percentual(odd_empate_ini, odd_empate)
    var_visitante = _variacao_percentual(
        odd_visitante_ini,
        odd_visitante,
    )

    var_ciclo = _movimento_odd(
        memoria["ultima_odd_empate"],
        odd_empate,
    )
        var_10min = _variacao_10min(
        memoria["historico"],
        minuto,
        odd_empate,
        )

    odd_45 = _calcular_referencia_45(
        odd_casa,
        odd_empate,
        odd_visitante,
        minuto,
    )

    diferenca_45 = 0.0
    if odd_empate > 0 and odd_45 > 0:
        diferenca_45 = (
            (odd_empate - odd_45) / odd_45
        ) * 100.0

    ipm = _calcular_ipm(
        odd_casa_ini,
        odd_empate_ini,
        odd_visitante_ini,
        odd_casa,
        odd_empate,
        odd_visitante,
        minuto,
    )
    # ========================================================
    # Q - QUOCIENTE DE MOVIMENTAÇÃO DA ODD DO EMPATE
    # ========================================================
    q = 0.0

    if odd_empate_ini > 0 and odd_empate > 0:
        q = odd_empate / odd_empate_ini
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
        "var_10min": var_10min,
        "gols": gols,
    }

    memoria["historico"].append(registro)
    memoria["historico"] = memoria["historico"][-100:]

    memoria["ultima_odd_casa"] = odd_casa
    memoria["ultima_odd_empate"] = odd_empate
    memoria["ultima_odd_visitante"] = odd_visitante
    memoria["ultimo_minuto"] = minuto

    referencia_pre = pre_live if pre_live > 0 else odd_empate_ini

    return {
        "event_id": chave_jogo,
        "minuto": minuto,
        "gols": gols,
        "escanteios": _inteiro(escanteios),
        "cartoes": _inteiro(cartoes),
        "finalizacoes": _inteiro(finalizacoes),
        "ataques_perigosos": _inteiro(ataques_perigosos),

        "odd_casa": odd_casa,
        "odd_atual": odd_empate,
        "odd_empate": odd_empate,
        "odd_visitante": odd_visitante,

        "odd_pre_live": referencia_pre,
        "odd_casa_pre_live": (
            pre_live_casa if pre_live_casa > 0 else odd_casa_ini
        ),
        "odd_visitante_pre_live": (
            pre_live_visitante
            if pre_live_visitante > 0
            else odd_visitante_ini
        ),

        "odd_casa_inicial": odd_casa_ini,
        "odd_empate_inicial": odd_empate_ini,
        "odd_visitante_inicial": odd_visitante_ini,

        "variacao_casa": var_casa,
        "variacao_pre_live": _variacao_percentual(
            referencia_pre,
            odd_empate,
        ),
        "variacao_empate": var_empate,
        "variacao_visitante": var_visitante,
        "variacao_odd": var_ciclo,
        "variacao_ciclo": var_ciclo,
        "q": q,
        "odd_45": odd_45,
        "diferenca_45": diferenca_45,
        "ipm": ipm,
        "historico_odds": memoria["historico"],
    }


def avaliar_entrada(
    resultado,
    minuto,
    ipm_minimo,
    variacao_minima,
    minuto_minimo,
    minuto_maximo,
):
    minuto = _inteiro(minuto, -1)

    if minuto < minuto_minimo or minuto > minuto_maximo:
        return False

    ipm = _numero(resultado.get("ipm"))
    variacao = abs(_numero(resultado.get("variacao_pre_live")))

    if ipm < _numero(ipm_minimo):
        return False

    if variacao < _numero(variacao_minima):
        return False

    return True


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
        or status.startswith("finished")
        or status.startswith("ended")
    )


def resultado_empate(jogo, mercados=None):
    if not isinstance(jogo, dict):
        return None

    for chave in ("scores", "score", "result"):
        valor = jogo.get(chave)

        if isinstance(valor, dict):
            casa = valor.get("home", valor.get("homeScore"))
            fora = valor.get("away", valor.get("awayScore"))

            if casa is not None and fora is not None:
                return _inteiro(casa) == _inteiro(fora)

        elif isinstance(valor, list) and len(valor) >= 2:
            return _inteiro(valor[0]) == _inteiro(valor[1])

    casa = jogo.get("homeScore")
    fora = jogo.get("awayScore")

    if casa is not None and fora is not None:
        return _inteiro(casa) == _inteiro(fora)

    return None


def formatar_radar(jogo, resultado, mercados=None):
    if not isinstance(jogo, dict):
        jogo = {}

    if not isinstance(resultado, dict):
        resultado = {}

    casa = jogo.get("home") or jogo.get("homeTeam") or "Casa"
    fora = jogo.get("away") or jogo.get("awayTeam") or "Fora"

    minuto = _inteiro(resultado.get("minuto"))
    placar_casa = 0
    placar_fora = 0

    scores = jogo.get("scores")
    if isinstance(scores, dict):
        placar_casa = _inteiro(scores.get("home"))
        placar_fora = _inteiro(scores.get("away"))
    else:
        placar_casa = _inteiro(jogo.get("homeScore"))
        placar_fora = _inteiro(jogo.get("awayScore"))

    return (
        "\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚽ {casa} x {fora}\n"
        f"⏱️ Minuto: {minuto}'\n"
        f"📊 Placar: {placar_casa} x {placar_fora}\n"
        "\n"
        "💰 ODDS\n"
        f"🏠 Casa:      {_numero(resultado.get('odd_casa')):.2f} "
        f"({_numero(resultado.get('variacao_casa')):+.2f}%)\n"
        f"🤝 Empate:    {_numero(resultado.get('odd_empate')):.2f} "
        f"({_numero(resultado.get('variacao_empate')):+.2f}%)\n"
        f"🚌 Visitante: {_numero(resultado.get('odd_visitante')):.2f} "
        f"({_numero(resultado.get('variacao_visitante')):+.2f}%)\n"
        "\n"
        f"🤝 Empate:    {_numero(resultado.get('odd_empate')):.2f} "
        f"({_numero(resultado.get('variacao_empate')):+.2f}%)\n"
        f"🚌 Visitante: {_numero(resultado.get('odd_visitante')):.2f} "
        f"({_numero(resultado.get('variacao_visitante')):+.2f}%)\n"
        "\n"
        f"🧪 Q: {_numero(resultado.get('q')):.2f}\n"
        "\n"
        "🎯 REFERÊNCIA 45'\n"
        f"🤝 Odd projetada: {_numero(resultado.get('odd_45')):.2f}\n"
        f"📐 Diferença atual: "
        f"{_numero(resultado.get('diferenca_45')):+.2f}%\n"
        "\n"
        f"📈 IPM: {_numero(resultado.get('ipm')):.2f}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


def limpar_memoria():
    _MEMORIA.clear()
