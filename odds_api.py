# ============================================================
# MOTOR IPM - V5
# BASE: CASA + EMPATE + VISITANTE
# ============================================================

import json
import math
from pathlib import Path


ARQUIVO_MEMORIA = Path("ipm_memoria.json")

_memoria = {}


# ============================================================
# UTILITÁRIOS
# ============================================================

def _float(valor, padrao=0.0):
    try:
        if valor in (None, ""):
            return padrao
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def _int(valor, padrao=0):
    try:
        if valor in (None, ""):
            return padrao
        return int(float(valor))
    except (TypeError, ValueError):
        return padrao


def _limitar(valor, minimo=0.0, maximo=100.0):
    return max(minimo, min(maximo, float(valor)))


def _variacao_percentual(inicial, atual):
    inicial = _float(inicial)
    atual = _float(atual)

    if inicial <= 0 or atual <= 0:
        return 0.0

    return ((atual / inicial) - 1.0) * 100.0


# ============================================================
# MEMÓRIA
# ============================================================

def carregar_memoria():
    global _memoria

    try:
        if not ARQUIVO_MEMORIA.exists():
            _memoria = {}
            return

        with ARQUIVO_MEMORIA.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        _memoria = dados if isinstance(dados, dict) else {}

        print("🧠 Memória IPM carregada:", len(_memoria), "jogos")

    except Exception as erro:
        print(
            "⚠️ ERRO AO CARREGAR MEMÓRIA IPM:",
            type(erro).__name__,
            erro,
        )
        _memoria = {}


def salvar_memoria():
    try:
        temporario = ARQUIVO_MEMORIA.with_suffix(".tmp")

        with temporario.open("w", encoding="utf-8") as arquivo:
            json.dump(
                _memoria,
                arquivo,
                ensure_ascii=False,
                indent=2,
            )

        temporario.replace(ARQUIVO_MEMORIA)

    except Exception as erro:
        print(
            "⚠️ ERRO AO SALVAR MEMÓRIA IPM:",
            type(erro).__name__,
            erro,
        )


def _obter_memoria(event_id):
    chave = str(event_id)

    if chave not in _memoria:
        _memoria[chave] = {
            "historico": [],
            "odd_casa_inicial": 0.0,
            "odd_empate_inicial": 0.0,
            "odd_visitante_inicial": 0.0,
            "ultimo_minuto": 0,
        }

    return _memoria[chave]


# ============================================================
# PROBABILIDADES DAS 3 ODDS
# ============================================================

def calcular_probabilidades(odd_casa, odd_empate, odd_visitante):
    odd_casa = _float(odd_casa)
    odd_empate = _float(odd_empate)
    odd_visitante = _float(odd_visitante)

    if (
        odd_casa <= 1.0
        or odd_empate <= 1.0
        or odd_visitante <= 1.0
    ):
        return {
            "prob_casa": 0.0,
            "prob_empate": 0.0,
            "prob_visitante": 0.0,
            "overround": 0.0,
        }

    p_casa = 1.0 / odd_casa
    p_empate = 1.0 / odd_empate
    p_visitante = 1.0 / odd_visitante

    soma = p_casa + p_empate + p_visitante

    if soma <= 0:
        return {
            "prob_casa": 0.0,
            "prob_empate": 0.0,
            "prob_visitante": 0.0,
            "overround": 0.0,
        }

    return {
        "prob_casa": (p_casa / soma) * 100.0,
        "prob_empate": (p_empate / soma) * 100.0,
        "prob_visitante": (p_visitante / soma) * 100.0,
        "overround": (soma - 1.0) * 100.0,
    }


# ============================================================
# REFERÊNCIA MATEMÁTICA DO EMPATE
# ============================================================

def calcular_referencia_empate_45(
    odd_casa,
    odd_visitante,
):
    """
    Estima uma referência matemática para a odd do empate
    aos 45 minutos utilizando somente CASA e VISITANTE.

    A ideia central:

        força_casa + força_visitante
        --------------------------------
        determina o espaço disponível para o empate.

    Quanto mais equilibradas as duas forças,
    maior a sustentação matemática do empate.
    """

    odd_casa = _float(odd_casa)
    odd_visitante = _float(odd_visitante)

    if odd_casa <= 1.0 or odd_visitante <= 1.0:
        return 0.0

    p_casa = 1.0 / odd_casa
    p_visitante = 1.0 / odd_visitante

    soma = p_casa + p_visitante

    if soma <= 0:
        return 0.0

    # Equilíbrio entre casa e visitante.
    equilibrio = 1.0 - abs(p_casa - p_visitante) / soma

    equilibrio = _limitar(equilibrio, 0.0, 1.0)

    # Probabilidade-base do empate.
    #
    # O valor 0.25 representa uma referência inicial.
    # O equilíbrio aumenta a sustentação do empate.
    prob_empate = 0.25 + (equilibrio * 0.10)

    prob_empate = _limitar(prob_empate, 0.15, 0.35)

    odd_referencia = 1.0 / prob_empate

    return round(odd_referencia, 3)


# ============================================================
# PROJEÇÃO PARA O MINUTO 45
# ============================================================

def projetar_empate_45(
    minuto,
    odd_casa,
    odd_empate,
    odd_visitante,
):
    """
    Calcula a distância entre a odd atual do empate
    e a referência matemática projetada para 45'.

    Também considera a evolução temporal.
    """

    minuto = _int(minuto)

    odd_casa = _float(odd_casa)
    odd_empate = _float(odd_empate)
    odd_visitante = _float(odd_visitante)

    referencia = calcular_referencia_empate_45(
        odd_casa,
        odd_visitante,
    )

    if referencia <= 0 or odd_empate <= 0:
        return {
            "odd_empate_45": 0.0,
            "distancia_45": 0.0,
            "proximidade_45": 0.0,
        }

    distancia = _variacao_percentual(
        referencia,
        odd_empate,
    )

    # Quanto menor a distância absoluta,
    # mais próximo o mercado está da referência.
    proximidade = max(
        0.0,
        100.0 - abs(distancia),
    )

    return {
        "odd_empate_45": referencia,
        "distancia_45": distancia,
        "proximidade_45": _limitar(proximidade),
    }


# ============================================================
# TRAJETÓRIA
# ============================================================

def calcular_trajetoria(
    odd_casa_inicial,
    odd_empate_inicial,
    odd_visitante_inicial,
    odd_casa,
    odd_empate,
    odd_visitante,
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

    return {
        "variacao_casa": var_casa,
        "variacao_empate": var_empate,
        "variacao_visitante": var_visitante,
    }


# ============================================================
# IPM
# ============================================================

def calcular_ipm(
    odd_casa_inicial,
    odd_empate_inicial,
    odd_visitante_inicial,
    odd_casa,
    odd_empate,
    odd_visitante,
    minuto,
):
    """
    IPM baseado somente na movimentação das três odds.

    Componentes:

    1. equilíbrio Casa x Visitante;
    2. movimento da odd do empate;
    3. proximidade da referência dos 45';
    4. coerência das três trajetórias.
    """

    probs = calcular_probabilidades(
        odd_casa,
        odd_empate,
        odd_visitante,
    )

    prob_casa = probs["prob_casa"]
    prob_empate = probs["prob_empate"]
    prob_visitante = probs["prob_visitante"]

    # --------------------------------------------------------
    # 1. EQUILÍBRIO CASA x VISITANTE
    # --------------------------------------------------------

    soma_cv = prob_casa + prob_visitante

    if soma_cv > 0:
        equilibrio = 1.0 - (
            abs(prob_casa - prob_visitante) / soma_cv
        )
    else:
        equilibrio = 0.0

    equilibrio = _limitar(equilibrio, 0.0, 1.0)

    pontos_equilibrio = equilibrio * 35.0

    # --------------------------------------------------------
    # 2. MOVIMENTO DA ODD DO EMPATE
    # --------------------------------------------------------

    movimento_empate = abs(
        _variacao_percentual(
            odd_empate_inicial,
            odd_empate,
        )
    )

    pontos_movimento = min(
        movimento_empate * 4.0,
        25.0,
    )

    # --------------------------------------------------------
    # 3. PROXIMIDADE DA REFERÊNCIA 45'
    # --------------------------------------------------------

    projecao = projetar_empate_45(
        minuto,
        odd_casa,
        odd_empate,
        odd_visitante,
    )

    proximidade = projecao["proximidade_45"]

    pontos_45 = proximidade * 0.30

    # --------------------------------------------------------
    # 4. COERÊNCIA
    # --------------------------------------------------------

    var_casa = _variacao_percentual(
        odd_casa_inicial,
        odd_casa,
    )

    var_visitante = _variacao_percentual(
        odd_visitante_inicial,
        odd_visitante,
    )

    # Se as duas pontas caminham em direções diferentes,
    # o jogo está ficando mais equilibrado.
    if var_casa * var_visitante < 0:
        coerencia = 1.0
    else:
        coerencia = 0.5

    pontos_coerencia = coerencia * 15.0

    # --------------------------------------------------------
    # IPM FINAL
    # --------------------------------------------------------

    ipm = (
        pontos_equilibrio
        + pontos_movimento
        + pontos_45
        + pontos_coerencia
    )

    # Pequeno ajuste temporal:
    # antes de 15' não deixamos o IPM atingir o máximo
    # somente por uma oscilação inicial.
    minuto = max(0, minuto)

    if minuto < 10:
        ipm *= 0.65
    elif minuto < 20:
        ipm *= 0.80
    elif minuto < 30:
        ipm *= 0.90

    ipm = _limitar(ipm)

    return round(ipm, 2)


# ============================================================
# ANÁLISE PRINCIPAL
# ============================================================

def analisar_ipm_com_memoria(
    event_id,
    odd_atual,
    minuto,
    gols=0,
    escanteios=0,
    finalizacoes=0,
    ataques_perigosos=0,
    odd_pre_live=None,
    odd_casa=None,
    odd_visitante=None,
):
    """
    Compatível com o main atual.

    O main antigo envia apenas odd_atual.
    A nova versão precisa receber também CASA e VISITANTE.

    Portanto, quando esses valores forem fornecidos,
    a análise completa será feita.
    """

    memoria = _obter_memoria(event_id)

    minuto = _int(minuto)

    # --------------------------------------------------------
    # COMPATIBILIDADE
    # --------------------------------------------------------

    if odd_empate_valido(odd_atual):
        odd_empate = _float(odd_atual)
    else:
        odd_empate = 0.0

    odd_casa = _float(odd_casa)
    odd_visitante = _float(odd_visitante)

    # --------------------------------------------------------
    # PRIMEIRA LEITURA
    # --------------------------------------------------------

    if (
        memoria["odd_casa_inicial"] <= 0
        and odd_casa > 0
    ):
        memoria["odd_casa_inicial"] = odd_casa

    if (
        memoria["odd_empate_inicial"] <= 0
        and odd_empate > 0
    ):
        memoria["odd_empate_inicial"] = odd_empate

    if (
        memoria["odd_visitante_inicial"] <= 0
        and odd_visitante > 0
    ):
        memoria["odd_visitante_inicial"] = odd_visitante

    casa_ini = memoria["odd_casa_inicial"]
    empate_ini = memoria["odd_empate_inicial"]
    visitante_ini = memoria["odd_visitante_inicial"]

    # --------------------------------------------------------
    # TRAJETÓRIA
    # --------------------------------------------------------

    if casa_ini > 0 and visitante_ini > 0:
        trajetoria = calcular_trajetoria(
            casa_ini,
            empate_ini,
            visitante_ini,
            odd_casa,
            odd_empate,
            odd_visitante,
        )
    else:
        trajetoria = {
            "variacao_casa": 0.0,
            "variacao_empate": 0.0,
            "variacao_visitante": 0.0,
        }

    # --------------------------------------------------------
    # REFERÊNCIA 45'
    # --------------------------------------------------------

    projecao = projetar_empate_45(
        minuto,
        odd_casa,
        odd_empate,
        odd_visitante,
    )

    # --------------------------------------------------------
    # IPM
    # --------------------------------------------------------

    if (
        odd_casa > 0
        and odd_empate > 0
        and odd_visitante > 0
        and casa_ini > 0
        and empate_ini > 0
        and visitante_ini > 0
    ):
        ipm = calcular_ipm(
            casa_ini,
            empate_ini,
            visitante_ini,
            odd_casa,
            odd_empate,
            odd_visitante,
            minuto,
        )
    else:
        ipm = 0.0

    # --------------------------------------------------------
    # HISTÓRICO
    # --------------------------------------------------------

    ponto = {
        "minuto": minuto,
        "odd_casa": odd_casa,
        "odd_empate": odd_empate,
        "odd_visitante": odd_visitante,
        "ipm": ipm,
        "odd_empate_45": projecao["odd_empate_45"],
        "distancia_45": projecao["distancia_45"],
    }

    historico = memoria["historico"]

    historico.append(ponto)

    # Mantém apenas as últimas 200 leituras.
    memoria["historico"] = historico[-200:]

    memoria["ultimo_minuto"] = minuto

    salvar_memoria()

    # --------------------------------------------------------
    # RESULTADO
    # --------------------------------------------------------

    return {
        "ipm": ipm,

        "minuto": minuto,
        "gols": _int(gols),

        "odd_casa": odd_casa,
        "odd_empate": odd_empate,
        "odd_visitante": odd_visitante,

        "odd_atual": odd_empate,

        "odd_pre_live": _float(
            odd_pre_live or empate_ini
        ),

        "variacao_casa": trajetoria["variacao_casa"],
        "variacao_empate": trajetoria["variacao_empate"],
        "variacao_visitante": trajetoria["variacao_visitante"],

        "variacao_pre_live": _variacao_percentual(
            odd_pre_live or empate_ini,
            odd_empate,
        ),

        "variacao_ciclo": 0.0,

        "odd_empate_45": projecao["odd_empate_45"],
        "distancia_45": projecao["distancia_45"],
        "proximidade_45": projecao["proximidade_45"],

        "historico": memoria["historico"],

        "escanteios": 0,
        "finalizacoes": 0,
        "ataques_perigosos": 0,
    }


def odd_empate_valido(valor):
    return _float(valor) > 1.0


# ============================================================
# ENTRADA
# ============================================================

def avaliar_entrada(
    resultado,
    minuto,
    ipm_minimo,
    variacao_minima_odd,
    minuto_minimo,
    minuto_maximo,
):
    ipm = _float(resultado.get("ipm"))

    if minuto < minuto_minimo:
        return False

    if minuto > minuto_maximo:
        return False

    if ipm < ipm_minimo:
        return False

    return True


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classificar_ipm(ipm):
    ipm = _float(ipm)

    if ipm >= 70:
        return "EXPLOSIVO"

    if ipm >= 50:
        return "MUITO FORTE"

    if ipm >= 40:
        return "FORTE"

    if ipm >= 25:
        return "MÉDIO"

    if ipm >= 10:
        return "FRACO"

    return "RUÍDO"


# ============================================================
# RADAR
# ============================================================

def formatar_radar(jogo, resultado, mercados=None):

    casa = jogo.get("home") or jogo.get("homeTeam") or "Casa"
    visitante = jogo.get("away") or jogo.get("awayTeam") or "Visitante"

    minuto = resultado.get("minuto", 0)

    odd_casa = _float(resultado.get("odd_casa"))
    odd_empate = _float(resultado.get("odd_empate"))
    odd_visitante = _float(resultado.get("odd_visitante"))

    ipm = _float(resultado.get("ipm"))

    odd_45 = _float(
        resultado.get("odd_empate_45")
    )

    distancia = _float(
        resultado.get("distancia_45")
    )

    proximidade = _float(
        resultado.get("proximidade_45")
    )

    classe = classificar_ipm(ipm)

    return (
        "\n"
        + "=" * 72
        + "\n"
        + f"⚽ {casa} x {visitante}\n"
        + f"⏱️ Minuto: {minuto}'\n"
        + "\n"
        + "💰 ODDS\n"
        + f"🏠 Casa:       {odd_casa:.2f}\n"
        + f"🤝 Empate:     {odd_empate:.2f}\n"
        + f"✈️ Visitante:  {odd_visitante:.2f}\n"
        + "\n"
        + "📈 TRAJETÓRIA\n"
        + f"🏠 Casa:       {resultado.get('variacao_casa', 0):+.2f}%\n"
        + f"🤝 Empate:     {resultado.get('variacao_empate', 0):+.2f}%\n"
        + f"✈️ Visitante:  {resultado.get('variacao_visitante', 0):+.2f}%\n"
        + "\n"
        + "🎯 REFERÊNCIA 45'\n"
        + f"🤝 Odd projetada: {odd_45:.3f}\n"
        + f"📐 Distância:     {distancia:+.2f}%\n"
        + f"📊 Proximidade:   {proximidade:.2f}%\n"
        + "\n"
        + f"🔥 IPM: {ipm:.2f}/100\n"
        + f"🚦 {classe}\n"
        + "=" * 72
    )


# ============================================================
# FINALIZAÇÃO
# ============================================================

def jogo_finalizado(jogo):
    status = str(
        jogo.get("status")
        or jogo.get("state")
        or ""
    ).lower()

    return any(
        termo in status
        for termo in (
            "finished",
            "final",
            "ended",
            "ft",
            "complete",
        )
    )


def resultado_empate(jogo, mercados=None):
    scores = jogo.get("scores")

    if isinstance(scores, dict):
        casa = scores.get("home")
        visitante = scores.get("away")

        if casa is not None and visitante is not None:
            return _int(casa) == _int(visitante)

    home_score = jogo.get("homeScore")
    away_score = jogo.get("awayScore")

    if home_score is not None and away_score is not None:
        return _int(home_score) == _int(away_score)

    return None


# ============================================================
# INICIALIZAÇÃO
# ============================================================

carregar_memoria()
