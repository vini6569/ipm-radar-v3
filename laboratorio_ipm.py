# ============================================================
# LABORATÓRIO IPM
# PRÉ-ENTRADA + ODD X REAL + MIN 45
# ============================================================

# ============================================================
# PAINEL DE PARÂMETROS
# ALTERAR SOMENTE AQUI
# ============================================================

LAB_ATIVO = True

# ------------------------------------------------------------
# PRÉ-ENTRADA
# ------------------------------------------------------------

LAB_PRE_ENTRADA_ATIVADA = True

# Janela de comparação da odd
LAB_JANELA_MINUTOS = 10

# Limites independentes
LAB_VARIACAO_POSITIVA = 20.0
LAB_VARIACAO_NEGATIVA = 20.0

# ------------------------------------------------------------
# ODD X REAL - √5
# Fórmula:
# √(Odd Casa × Odd Visitante)
# ------------------------------------------------------------

LAB_ODD_REAL_ATIVADA = True

# ------------------------------------------------------------
# MIN 45
# ------------------------------------------------------------

LAB_MIN45_ATIVADO = True
LAB_MIN45_PROB_BASE = 40.0


def parametros_laboratorio():
    return {
        "ativo": LAB_ATIVO,
        "pre_entrada": LAB_PRE_ENTRADA_ATIVADA,
        "janela_minutos": LAB_JANELA_MINUTOS,
        "variacao_positiva": LAB_VARIACAO_POSITIVA,
        "variacao_negativa": LAB_VARIACAO_NEGATIVA,
        "odd_real": LAB_ODD_REAL_ATIVADA,
        "min45": LAB_MIN45_ATIVADO,
        "min45_prob_base": LAB_MIN45_PROB_BASE,
    }

# ============================================================
# BLOCO 2 - ODD DE EMPATE REAL - RAIZ DE 5
# ============================================================

import math


def calcular_odd_real_sqrt5(odd_casa, odd_visitante):
    try:
        casa = float(odd_casa)
        visitante = float(odd_visitante)

        if casa <= 0 or visitante <= 0:
            return 0.0

        return math.sqrt(casa * visitante)

    except (TypeError, ValueError):
        return 0.0


def analisar_sqrt5(odd_casa, odd_empate, odd_visitante):
    odd_real = calcular_odd_real_sqrt5(
        odd_casa,
        odd_visitante,
    )

    try:
        odd_empate = float(odd_empate)
    except (TypeError, ValueError):
        odd_empate = 0.0

    if odd_real <= 0 or odd_empate <= 0:
        diferenca = 0.0
    else:
        diferenca = (
            (odd_empate - odd_real)
            / odd_real
        ) * 100.0

    return {
        "odd_real_sqrt5": odd_real,
        "odd_empate": odd_empate,
        "diferenca_sqrt5": diferenca,
    }

# ============================================================
# BLOCO 3 - DIAGNÓSTICO DA ODD X
# ============================================================

def gerar_diagnostico_sqrt5(
    odd_casa,
    odd_empate,
    odd_visitante,
):
    analise = analisar_sqrt5(
        odd_casa,
        odd_empate,
        odd_visitante,
    )

    odd_real = analise["odd_real_sqrt5"]
    odd_x = analise["odd_empate"]
    diferenca = analise["diferenca_sqrt5"]

    if odd_x <= 0 or odd_real <= 0:
        sinal = "SEM DADOS"
    elif diferenca > 0:
        sinal = "POSITIVO"
    elif diferenca < 0:
        sinal = "NEGATIVO"
    else:
        sinal = "NEUTRO"

    return {
        "

# ============================================================
# BLOCO 4 - PRÉ-ENTRADA PARAMETRIZADA
# ============================================================

def verificar_pre_entrada(
    odd_empate_anterior,
    odd_empate_atual,
    janela_minutos,
):
    try:
        anterior = float(odd_empate_anterior)
        atual = float(odd_empate_atual)
        janela = float(janela_minutos)

    except (TypeError, ValueError):
        return {
            "sinal": False,
            "direcao": None,
            "variacao": 0.0,
            "janela": 0.0,
        }

    if anterior <= 0 or atual <= 0:
        return {
            "sinal": False,
            "direcao": None,
            "variacao": 0.0,
            "janela": janela,
        }

    variacao = (
        (atual - anterior)
        / anterior
    ) * 100.0

    if variacao >= LAB_VARIACAO_POSITIVA:
        return {
            "sinal": True,
            "direcao": "POSITIVO",
            "variacao": variacao,
            "janela": janela,
        }

    if variacao <= -LAB_VARIACAO_NEGATIVA:
        return {
            "sinal": True,
            "direcao": "NEGATIVO",
            "variacao": variacao,
            "janela": janela,
        }

    return {
        "sinal": False,
        "direcao": None,
        "variacao": variacao,
        "janela": janela,
  }

# ============================================================
# BLOCO 5 - MENSAGEM DO LABORATÓRIO
# ============================================================

def formatar_mensagem_laboratorio(
    jogo,
    minuto,
    odd_casa,
    odd_empate,
    odd_visitante,
    variacao,
    direcao,
    odd_real,
    diferenca_sqrt5,
):
    casa = jogo.get("home", "Casa")
    visitante = jogo.get("away", "Visitante")

    return (
        "🧪 🚨 ENTRADA EMPATE\n\n"
        f"⚽ {casa} x {visitante}\n"
        f"⏱️ Minuto: {minuto}'\n\n"
        f"💰 Odd Casa: {float(odd_casa):.2f}\n"
        f"🤝 Odd Empate: {float(odd_empate):.2f}\n"
        f"💰 Odd Visitante: {float(odd_visitante):.2f}\n\n"
        f"📉 Variação 10': {float(variacao):+.2f}%\n"
        f"📌 Sinal: {direcao}\n\n"
        f"🎯 Odd X Real √5: {float(odd_real):.2f}\n"
        f"📐 Diferença √5: {float(diferenca_sqrt5):+.2f}%\n\n"
        "🟢 PADRÃO CONFIRMADO"
  )

# ============================================================
# BLOCO 6 - CÁLCULOS DO LABORATÓRIO
# PRÉ-ENTRADA + ODD REAL √5
# NÃO ALTERA O MOTOR PRINCIPAL
# ============================================================

import math


# ------------------------------------------------------------
# CÁLCULO DA PRÉ-ENTRADA
# ------------------------------------------------------------

def calcular_pre_entrada_laboratorio(
    odd_pre_live,
    odd_atual,
    minuto,
):
    if not LAB_ATIVO:
        return {
            "ativada": False,
            "variacao": 0.0,
            "direcao": "DESATIVADO",
        }

    try:
        minuto = int(minuto)
        odd_pre_live = float(odd_pre_live)
        odd_atual = float(odd_atual)
    except (TypeError, ValueError):
        return {
            "ativada": False,
            "variacao": 0.0,
            "direcao": "DADOS_INVALIDOS",
        }

    if odd_pre_live <= 0 or odd_atual <= 0:
        return {
            "ativada": False,
            "variacao": 0.0,
            "direcao": "SEM_ODD",
        }

    if minuto < LAB_JANELA_MINUTOS:
        return {
            "ativada": False,
            "variacao": 0.0,
            "direcao": "AGUARDANDO",
        }

    variacao = (
        (odd_atual - odd_pre_live)
        / odd_pre_live
    ) * 100.0

    if variacao >= LAB_PRE_ENTRADA_POSITIVO:
        direcao = "POSITIVO"
        ativada = True

    elif variacao <= -LAB_PRE_ENTRADA_NEGATIVO:
        direcao = "NEGATIVO"
        ativada = True

    else:
        direcao = "NEUTRO"
        ativada = False

    return {
        "ativada": ativada,
        "variacao": variacao,
        "direcao": direcao,
    }


# ------------------------------------------------------------
# ODD REAL DO EMPATE - FÓRMULA √5
#
# CASA × VISITANTE ÷ √5
# ------------------------------------------------------------

def calcular_odd_real_sqrt5(
    odd_casa,
    odd_visitante,
):
    try:
        odd_casa = float(odd_casa)
        odd_visitante = float(odd_visitante)
    except (TypeError, ValueError):
        return 0.0

    if odd_casa <= 0 or odd_visitante <= 0:
        return 0.0

    try:
        odd_real = (
            odd_casa * odd_visitante
        ) / math.sqrt(5)

        return round(odd_real, 3)

    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


# ------------------------------------------------------------
# DIFERENÇA ENTRE ODD ATUAL E ODD REAL √5
# ------------------------------------------------------------

def calcular_diferenca_sqrt5(
    odd_empate,
    odd_real,
):
    try:
        odd_empate = float(odd_empate)
        odd_real = float(odd_real)
    except (TypeError, ValueError):
        return 0.0

    if odd_real <= 0:
        return 0.0

    return (
        (odd_empate - odd_real)
        / odd_real
    ) * 100.0


# ------------------------------------------------------------
# DIAGNÓSTICO COMPLETO DO LABORATÓRIO
# ------------------------------------------------------------

def diagnosticar_laboratorio(
    odd_casa,
    odd_empate,
    odd_visitante,
    odd_pre_live,
    minuto,
):
    pre = calcular_pre_entrada_laboratorio(
        odd_pre_live,
        odd_empate,
        minuto,
    )

    odd_real = calcular_odd_real_sqrt5(
        odd_casa,
        odd_visitante,
    )

    diferenca = calcular_diferenca_sqrt5(
        odd_empate,
        odd_real,
    )

    return {
        "pre_entrada": pre,
        "odd_real_sqrt5": odd_real,
        "diferenca_sqrt5": diferenca,
    }


# ============================================================
# FIM DO BLOCO 6
# ============================================================
