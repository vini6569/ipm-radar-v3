# ============================================================
# MOTOR IPM - RADAR V5.1 CORRIGIDO
# CASA + EMPATE + VISITANTE
# PRE-LIVE + TRAJETÓRIA + REFERÊNCIA 45' + MEMÓRIA
# SINAL PRÉ-ENTRADA: +/- 20% EM 10 MINUTOS
# ============================================================

from datetime import datetime
import time

_MEMORIA = {}
LIMITE_PRE_ENTRADA = 20.0


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


def classificar_faixa_odd(odd):
    odd = _numero(odd)
    if odd <= 0:
        return "SEM_ODD"
    if odd < 1.60:
        return "1.40-1.59"
    if odd < 2.00:
        return "1.60-1.99"
    if odd < 2.50:
        return "2.00-2.49"
    if odd < 3.00:
        return "2.50-2.99"
    return "3.00+"


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


# ============================================================
# CORREÇÃO PRINCIPAL: VAR10 POR TEMPO REAL
# ============================================================
# Não dependemos do minuto da partida para encontrar a leitura
# de 10 minutos atrás. Cada leitura recebe timestamp real.
# Isso evita VAR10=0 quando a API entrega minuto 0/repetido.
# ============================================================

def _variacao_10min(historico, minuto, odd_atual):
    odd_atual = _numero(odd_atual)
    if odd_atual <= 0 or not historico:
        return 0.0

    agora = time.time()
    alvo = agora - 600.0
    melhor = None

    for registro in historico:
        if not isinstance(registro, dict):
            continue
        odd_ref = _numero(registro.get("odd_empate"))
        timestamp = _numero(registro.get("timestamp"))
        if odd_ref <= 0 or timestamp <= 0:
            continue

        distancia = abs(timestamp - alvo)
        if melhor is None or distancia < melhor[0]:
            melhor = (distancia, odd_ref)

    if melhor is None:
        return 0.0

    # Aceita somente uma referência razoavelmente próxima dos 10 min.
    if melhor[0] > 90.0:
        return 0.0

    odd_10min = melhor[1]
    return ((odd_atual - odd_10min) / odd_10min) * 100.0


def _calcular_referencia_45(odd_casa, odd_empate, odd_visitante, minuto):
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

    p_x = p_empate / soma
    fator = min(max(minuto / 45.0, 0.0), 1.0)
    alvo = p_x * (1.0 - fator) + p_empate * fator
    if alvo <= 0:
        return odd_empate
    return max(1.01, min(50.0, 1.0 / alvo))


def _calcular_ipm(odd_casa_inicial, odd_empate_inicial,
                  odd_visitante_inicial, odd_casa, odd_empate,
                  odd_visitante, minuto):
    var_casa = _variacao_percentual(odd_casa_inicial, odd_casa)
    var_empate = _variacao_percentual(odd_empate_inicial, odd_empate)
    var_visitante = _variacao_percentual(odd_visitante_inicial, odd_visitante)

    movimento_lados = abs(var_casa) * 0.40 + abs(var_visitante) * 0.40
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
    pre_casa = _numero(odd_casa_pre_live)
    pre_visitante = _numero(odd_visitante_pre_live)

    faixa = classificar_faixa_odd(odd_empate)

    if memoria["odd_casa_inicial"] is None:
        memoria["odd_casa_inicial"] = pre_casa if pre_casa > 0 else odd_casa
    if memoria["odd_empate_inicial"] is None:
        memoria["odd_empate_inicial"] = pre_live if pre_live > 0 else odd_empate
    if memoria["odd_visitante_inicial"] is None:
        memoria["odd_visitante_inicial"] = pre_visitante if pre_visitante > 0 else odd_visitante

    odd_casa_ini = _numero(memoria["odd_casa_inicial"])
    odd_empate_ini = _numero(memoria["odd_empate_inicial"])
    odd_visitante_ini = _numero(memoria["odd_visitante_inicial"])

    var_casa = _variacao_percentual(odd_casa_ini, odd_casa)
    var_empate = _variacao_percentual(odd_empate_ini, odd_empate)
    var_visitante = _variacao_percentual(odd_visitante_ini, odd_visitante)
    var_ciclo = _movimento_odd(memoria["ultima_odd_empate"], odd_empate)

    # Calcula antes de gravar a leitura atual.
    var_10min = _variacao_10min(memoria["historico"], minuto, odd_empate)

    sinal = "NEUTRO"
    if var_10min >= LIMITE_PRE_ENTRADA:
        sinal = "ALTA_20"
    elif var_10min <= -LIMITE_PRE_ENTRADA:
        sinal = "QUEDA_20"

    odd_45 = _calcular_referencia_45(
        odd_casa, odd_empate, odd_visitante, minuto
    )
    diferenca_45 = 0.0
    if odd_empate > 0 and odd_45 > 0:
        diferenca_45 = ((odd_empate - odd_45) / odd_45) * 100.0

    ipm = _calcular_ipm(
        odd_casa_ini, odd_empate_ini, odd_visitante_ini,
        odd_casa, odd_empate, odd_visitante, minuto
    )

    q = pre_live if pre_live > 0 else odd_empate_ini
    agora = time.time()

    registro = {
        "timestamp": agora,
        "hora": datetime.now().strftime("%H:%M:%S"),
        "minuto": minuto,
        "odd_casa": odd_casa,
        "odd_empate": odd_empate,
        "odd_visitante": odd_visitante,
        "faixa_odd_x": faixa,
        "variacao_casa": var_casa,
        "variacao_empate": var_empate,
        "variacao_visitante": var_visitante,
        "odd_45": odd_45,
        "diferenca_45": diferenca_45,
        "ipm": ipm,
        "var_10min": var_10min,
        "sinal_pre_entrada": sinal,
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
        "faixa_odd_x": faixa,
        "odd_pre_live": referencia_pre,
        "odd_casa_pre_live": pre_casa if pre_casa > 0 else odd_casa_ini,
        "odd_visitante_pre_live": pre_visitante if pre_visitante > 0 else odd_visitante_ini,
        "odd_casa_inicial": odd_casa_ini,
        "odd_empate_inicial": odd_empate_ini,
        "odd_visitante_inicial": odd_visitante_ini,
        "variacao_casa": var_casa,
        "variacao_pre_live": _variacao_percentual(referencia_pre, odd_empate),
        "variacao_empate": var_empate,
        "variacao_visitante": var_visitante,
        "variacao_odd": var_ciclo,
        "variacao_ciclo": var_ciclo,
        "q": q,
        "odd_45": odd_45,
        "diferenca_45": diferenca_45,
        "ipm": ipm,
        "var_10min": var_10min,
        "sinal_pre_entrada": sinal,
        "historico_odds": memoria["historico"],
    }


def avaliar_entrada(resultado, minuto, ipm_minimo, variacao_minima,
                    minuto_minimo, minuto_maximo):
    minuto = _inteiro(minuto, -1)
    if minuto < minuto_minimo or minuto > minuto_maximo:
        return False
    if _numero(resultado.get("ipm")) < _numero(ipm_minimo):
        return False
    return abs(_numero(resultado.get("variacao_pre_live"))) >= _numero(variacao_minima)


def avaliar_pre_entrada(resultado):
    if not isinstance(resultado, dict):
        return False
    return abs(_numero(resultado.get("var_10min"))) >= LIMITE_PRE_ENTRADA


def jogo_finalizado(jogo):
    if not isinstance(jogo, dict):
        return False
    status = str(jogo.get("status") or jogo.get("state") or jogo.get("matchStatus") or "").strip().lower()
    return status in ("finished", "ft", "final", "ended", "complete", "completed") or status.startswith(("finished", "ended"))


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
    casa = jogo.get("home") or jogo.get("casa") or "Casa"
    fora = jogo.get("away") or jogo.get("fora") or "Fora"
    return (
        f"RADAR | {casa} x {fora} | "
        f"{_inteiro(resultado.get('minuto'))}' | "
        f"X={_numero(resultado.get('odd_empate')):.2f} | "
        f"VAR10={_numero(resultado.get('var_10min')):+.2f}% | "
        f"SINAL={resultado.get('sinal_pre_entrada', 'NEUTRO')} | "
        f"IPM={_numero(resultado.get('ipm')):.2f}"
    )


def limpar_memoria():
    _MEMORIA.clear()
    
