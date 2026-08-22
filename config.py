# ============================================================
# IPM-RADAR-V3
# CONFIGURAÇÃO CENTRAL
# ============================================================
#
# ROBÔ 2 — RADAR DE MOVIMENTAÇÃO / IPM
#
# Horário:
#   06:00 até 00:00
#
# Pausa:
#   00:00 até 06:00
#
# Consulta:
#   300 segundos = 5 minutos
#
# IMPORTANTE:
# Nenhuma chave de API fica neste arquivo.
# As credenciais devem ficar nas Environment Variables
# do Render.
#
# ============================================================

import os


# ============================================================
# IDENTIFICAÇÃO DO PROJETO
# ============================================================

NOME_BOT = "IPM-RADAR-V3"

VERSAO = "3.1.0"

MODO_PRODUCAO = (
    os.getenv(
        "MODO_PRODUCAO",
        "false"
    ).lower() == "true"
)


# ============================================================
# FUSO HORÁRIO
# ============================================================

FUSO_HORARIO = os.getenv(
    "FUSO_HORARIO",
    "America/Sao_Paulo"
)


# ============================================================
# HORÁRIO DE FUNCIONAMENTO
# ============================================================

HORA_INICIO = int(
    os.getenv(
        "HORA_INICIO",
        "6"
    )
)

HORA_FIM = int(
    os.getenv(
        "HORA_FIM",
        "0"
    )
)


# ============================================================
# INTERVALO PRINCIPAL DO RADAR
# ============================================================
#
# 300 segundos = 5 minutos
#
# O objetivo é reduzir o consumo da API.
# ============================================================

INTERVALO_COLETA = int(
    os.getenv(
        "INTERVALO_COLETA",
        "300"
    )
)

INTERVALO_RADAR = int(
    os.getenv(
        "INTERVALO_RADAR",
        "300"
    )
)


# ============================================================
# LIMITE DE EVENTOS POR LOTE
# ============================================================
#
# A Odds-API.io /odds/multi trabalha com até 10 eventos
# por consulta.
#
# O módulo odds_api.py fará os lotes automaticamente.
# ============================================================

MAX_EVENTOS_POR_CONSULTA = int(
    os.getenv(
        "MAX_EVENTOS_POR_CONSULTA",
        "10"
    )
)


# ============================================================
# LIMITE DE JOGOS DO RADAR
# ============================================================

MAX_JOGOS_RADAR = int(
    os.getenv(
        "MAX_JOGOS_RADAR",
        "50"
    )
)


# ============================================================
# TELEGRAM
# ============================================================

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
).strip()

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID",
    ""
).strip()


# ============================================================
# API-FOOTBALL
# ============================================================

API_FOOTBALL_KEY = os.getenv(
    "API_FOOTBALL_KEY",
    ""
).strip()

API_FOOTBALL_KEY_2 = os.getenv(
    "API_FOOTBALL_KEY_2",
    ""
).strip()

API_FOOTBALL_URL = (
    "https://v3.football.api-sports.io"
)


# ============================================================
# SPORTS GAME ODDS
# ============================================================

SPORTSGAMEODDS_API_KEY = os.getenv(
    "SPORTSGAMEODDS_API_KEY",
    ""
).strip()

SPORTSGAMEODDS_URL = (
    "https://api.sportsgameodds.com/v2"
)


# ============================================================
# THE ODDS API
# ============================================================

THE_ODDS_API_KEY = os.getenv(
    "ODDS_API_KEY",
    ""
).strip()

THE_ODDS_API_URL = (
    "https://api.the-odds-api.com/v4"
)


# ============================================================
# ODDS-API.IO
# ============================================================

ODDS_API_IO_KEY = os.getenv(
    "ODDS_API_IO_KEY",
    ""
).strip()

ODDS_API_IO_URL = (
    "https://api.odds-api.io/v3"
)


# ============================================================
# AISCORE
# ============================================================

AISCORE_URL = (
    "https://www.aiscore.com/br/live"
)


# ============================================================
# FONTES HABILITADAS
# ============================================================

USAR_API_FOOTBALL = (
    os.getenv(
        "USAR_API_FOOTBALL",
        "true"
    ).lower() == "true"
)

USAR_THE_ODDS_API = (
    os.getenv(
        "USAR_THE_ODDS_API",
        "true"
    ).lower() == "true"
)

USAR_ODDS_API_IO = (
    os.getenv(
        "USAR_ODDS_API_IO",
        "true"
    ).lower() == "true"
)

USAR_SPORTSGAMEODDS = (
    os.getenv(
        "USAR_SPORTSGAMEODDS",
        "true"
    ).lower() == "true"
)

USAR_AISCORE = (
    os.getenv(
        "USAR_AISCORE",
        "true"
    ).lower() == "true"
)


# ============================================================
# BOOKMAKER
# ============================================================
#
# Fonte principal de odds do Radar.
# ============================================================

BOOKMAKER_ODDS = os.getenv(
    "BOOKMAKER_ODDS",
    "Bet365"
).strip()


# ============================================================
# HISTÓRICO
# ============================================================

DATABASE_FILE = os.getenv(
    "DATABASE_FILE",
    "radar_ipm.db"
)

ARQUIVO_HISTORICO = os.getenv(
    "ARQUIVO_HISTORICO",
    "historico.json"
)

HISTORICO_MAXIMO = int(
    os.getenv(
        "HISTORICO_MAXIMO",
        "1000"
    )
)


# ============================================================
# IPM
# ============================================================

IPM_MINIMO_OBSERVACAO = float(
    os.getenv(
        "IPM_MINIMO_OBSERVACAO",
        "50"
    )
)

IPM_MINIMO_FORTE = float(
    os.getenv(
        "IPM_MINIMO_FORTE",
        "65"
    )
)

IPM_MINIMO_MUITO_FORTE = float(
    os.getenv(
        "IPM_MINIMO_MUITO_FORTE",
        "80"
    )
)


# ============================================================
# MOVIMENTAÇÃO DAS ODDS
# ============================================================

VARIACAO_MINIMA_ODD = float(
    os.getenv(
        "VARIACAO_MINIMA_ODD",
        "0.5"
    )
)


# ============================================================
# CICLO DO JOGO
# ============================================================
#
# O laboratório poderá classificar:
#
# - 2x1
# - empate
# - mais de 4 gols
# - outros resultados
#
# ============================================================

ATIVAR_CICLO_IPM = (
    os.getenv(
        "ATIVAR_CICLO_IPM",
        "true"
    ).lower() == "true"
)

REGISTRAR_TODOS_RESULTADOS = (
    os.getenv(
        "REGISTRAR_TODOS_RESULTADOS",
        "true"
    ).lower() == "true"
)


# ============================================================
# TELEGRAM — ENTRADAS
# ============================================================

ENVIAR_ENTRADAS_TELEGRAM = (
    os.getenv(
        "ENVIAR_ENTRADAS_TELEGRAM",
        "true"
    ).lower() == "true"
)


# ============================================================
# TELEGRAM — RESULTADOS
# ============================================================

ENVIAR_RESULTADOS_TELEGRAM = (
    os.getenv(
        "ENVIAR_RESULTADOS_TELEGRAM",
        "true"
    ).lower() == "true"
)


# ============================================================
# TELEGRAM — RELATÓRIO
# ============================================================

ENVIAR_RELATORIO_TELEGRAM = (
    os.getenv(
        "ENVIAR_RELATORIO_TELEGRAM",
        "true"
    ).lower() == "true"
)


# ============================================================
# RELATÓRIO PDF
# ============================================================

GERAR_RELATORIO_PDF = (
    os.getenv(
        "GERAR_RELATORIO_PDF",
        "false"
    ).lower() == "true"
)


# ============================================================
# SEGURANÇA
# ============================================================
#
# O IPM-RADAR-V3 NÃO REALIZA APOSTAS.
#
# Estas opções permanecem permanentemente desativadas.
# ============================================================

PERMITIR_APOSTAS = False

PERMITIR_LOGIN_CASA = False

PERMITIR_OPERACAO_AUTOMATICA = False


# ============================================================
# LOG
# ============================================================

NIVEL_LOG = os.getenv(
    "NIVEL_LOG",
    "INFO"
)


# ============================================================
# FUNÇÃO:
# FONTE DISPONÍVEL
# ============================================================

def fonte_disponivel(nome):

    fontes = {

        "api_football": bool(
            API_FOOTBALL_KEY
            or API_FOOTBALL_KEY_2
        ),

        "the_odds_api": bool(
            THE_ODDS_API_KEY
        ),

        "odds_api_io": bool(
            ODDS_API_IO_KEY
        ),

        "sports_game_odds": bool(
            SPORTSGAMEODDS_API_KEY
        ),

        "aiscore": USAR_AISCORE

    }

    return fontes.get(
        nome,
        False
    )


# ============================================================
# FUNÇÃO:
# VERIFICAR HORÁRIO
# ============================================================

def radar_ativo(hora):

    """
    Verifica se o radar deve estar funcionando.

    Padrão:

    06:00 → 00:00 = ATIVO
    00:00 → 06:00 = PAUSADO
    """

    hora = int(hora)

    # Funcionamento normal:
    # 06:00 até 23:59

    if HORA_FIM == 0:

        return (
            HORA_INICIO
            <= hora
            < 24
        )

    # Caso futuramente seja definido
    # outro horário final.

    if HORA_INICIO < HORA_FIM:

        return (
            HORA_INICIO
            <= hora
            < HORA_FIM
        )

    return (
        hora >= HORA_INICIO
        or
        hora < HORA_FIM
    )


# ============================================================
# FUNÇÃO:
# MOSTRAR CONFIGURAÇÃO
# ============================================================

def mostrar_configuracao():

    print()
    print("=" * 60)

    print(
        NOME_BOT
    )

    print(
        "VERSÃO:",
        VERSAO
    )

    print("=" * 60)

    print(
        "HORÁRIO:",
        f"{HORA_INICIO:02d}:00",
        "até",
        f"{HORA_FIM:02d}:00"
        if HORA_FIM != 0
        else "00:00"
    )

    print(
        "INTERVALO:",
        INTERVALO_COLETA,
        "segundos"
    )

    print(
        "INTERVALO RADAR:",
        INTERVALO_RADAR,
        "segundos"
    )

    print(
        "EVENTOS POR LOTE:",
        MAX_EVENTOS_POR_CONSULTA
    )

    print(
        "MÁXIMO DE JOGOS:",
        MAX_JOGOS_RADAR
    )

    print("-" * 60)

    print(
        "API-Football:",
        fonte_disponivel(
            "api_football"
        )
    )

    print(
        "The Odds API:",
        fonte_disponivel(
            "the_odds_api"
        )
    )

    print(
        "Odds-API.io:",
        fonte_disponivel(
            "odds_api_io"
        )
    )

    print(
        "Sports Game Odds:",
        fonte_disponivel(
            "sports_game_odds"
        )
    )

    print(
        "AiScore:",
        fonte_disponivel(
            "aiscore"
        )
    )

    print("-" * 60)

    print(
        "BOOKMAKER:",
        BOOKMAKER_ODDS
    )

    print(
        "CICLO IPM:",
        ATIVAR_CICLO_IPM
    )

    print(
        "ENTRADAS TELEGRAM:",
        ENVIAR_ENTRADAS_TELEGRAM
    )

    print(
        "RESULTADOS TELEGRAM:",
        ENVIAR_RESULTADOS_TELEGRAM
    )

    print(
        "RELATÓRIO TELEGRAM:",
        ENVIAR_RELATORIO_TELEGRAM
    )

    print(
        "RELATÓRIO PDF:",
        GERAR_RELATORIO_PDF
    )

    print("-" * 60)

    print(
        "IPM OBSERVAÇÃO:",
        IPM_MINIMO_OBSERVACAO
    )

    print(
        "IPM FORTE:",
        IPM_MINIMO_FORTE
    )

    print(
        "IPM MUITO FORTE:",
        IPM_MINIMO_MUITO_FORTE
    )

    print(
        "VARIAÇÃO MÍNIMA ODD:",
        VARIACAO_MINIMA_ODD
    )

    print("-" * 60)

    print(
        "APOSTAS AUTOMÁTICAS:",
        "DESATIVADAS"
    )

    print("=" * 60)


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":

    mostrar_configuracao()
