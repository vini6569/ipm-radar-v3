# ============================================================
# IPM-RADAR-V3
# CONFIGURAÇÃO CENTRAL
# ============================================================
#
# IMPORTANTE:
# Nenhuma chave de API fica neste arquivo.
# Todas as credenciais serão configuradas no Render
# através de Environment Variables.
#
# ============================================================

import os


# ============================================================
# IDENTIFICAÇÃO DO PROJETO
# ============================================================

NOME_BOT = "IPM-RADAR-V3"
VERSAO = "3.0.0"

MODO_PRODUCAO = os.getenv(
    "MODO_PRODUCAO",
    "false"
).lower() == "true"


# ============================================================
# FUSO HORÁRIO
# ============================================================

FUSO_HORARIO = os.getenv(
    "FUSO_HORARIO",
    "America/Sao_Paulo"
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
#
# Será utilizada como fonte complementar.
# Não dependeremos exclusivamente dela.
#

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
#
# Fonte opcional.
# O projeto não ficará dependente dela.
#

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
#
# Fonte de odds.
# Será utilizada somente quando disponível
# para o esporte/mercado desejado.
#

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
#
# Outra fonte independente para comparação.
#

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
#
# Não tratamos AiScore como API oficial.
# Ele será considerado uma possível fonte de
# consulta/coleta pública, caso tecnicamente viável.
#

AISCORE_URL = (
    "https://www.aiscore.com/br/live"
)


# ============================================================
# FONTES HABILITADAS
# ============================================================

USAR_API_FOOTBALL = os.getenv(
    "USAR_API_FOOTBALL",
    "true"
).lower() == "true"

USAR_THE_ODDS_API = os.getenv(
    "USAR_THE_ODDS_API",
    "true"
).lower() == "true"

USAR_ODDS_API_IO = os.getenv(
    "USAR_ODDS_API_IO",
    "true"
).lower() == "true"

USAR_SPORTSGAMEODDS = os.getenv(
    "USAR_SPORTSGAMEODDS",
    "true"
).lower() == "true"

USAR_AISCORE = os.getenv(
    "USAR_AISCORE",
    "true"
).lower() == "true"


# ============================================================
# COLETA
# ============================================================

INTERVALO_COLETA = int(
    os.getenv(
        "INTERVALO_COLETA",
        "60"
    )
)

INTERVALO_RADAR = int(
    os.getenv(
        "INTERVALO_RADAR",
        "60"
    )
)

MAX_JOGOS_RADAR = int(
    os.getenv(
        "MAX_JOGOS_RADAR",
        "10"
    )
)


# ============================================================
# HISTÓRICO
# ============================================================

DATABASE_FILE = os.getenv(
    "DATABASE_FILE",
    "radar_ipm.db"
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
# MOVIMENTAÇÃO DE ODDS
# ============================================================

VARIACAO_MINIMA_ODD = float(
    os.getenv(
        "VARIACAO_MINIMA_ODD",
        "0.5"
    )
)


# ============================================================
# SEGURANÇA
# ============================================================
#
# O BOT 2 não realiza apostas.
#

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
# FUNÇÕES AUXILIARES
# ============================================================

def fonte_disponivel(nome):
    """
    Verifica se determinada fonte possui
    chave configurada.
    """

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

    return fontes.get(nome, False)


def mostrar_configuracao():
    """
    Mostra somente informações seguras.
    Nunca imprime as chaves.
    """

    print("=" * 60)
    print(NOME_BOT)
    print("VERSÃO:", VERSAO)
    print("=" * 60)

    print(
        "API-Football:",
        fonte_disponivel("api_football")
    )

    print(
        "The Odds API:",
        fonte_disponivel("the_odds_api")
    )

    print(
        "Odds-API.io:",
        fonte_disponivel("odds_api_io")
    )

    print(
        "Sports Game Odds:",
        fonte_disponivel("sports_game_odds")
    )

    print(
        "AiScore:",
        fonte_disponivel("aiscore")
    )

    print("-" * 60)

    print(
        "Intervalo coleta:",
        INTERVALO_COLETA,
        "segundos"
    )

    print(
        "Intervalo radar:",
        INTERVALO_RADAR,
        "segundos"
    )

    print(
        "Máximo de jogos:",
        MAX_JOGOS_RADAR
    )

    print(
        "IPM observação:",
        IPM_MINIMO_OBSERVACAO
    )

    print(
        "IPM forte:",
        IPM_MINIMO_FORTE
    )

    print(
        "IPM muito forte:",
        IPM_MINIMO_MUITO_FORTE
    )

    print("-" * 60)

    print(
        "APOSTAS AUTOMÁTICAS:",
        "DESATIVADAS"
    )

    print("=" * 60)


if __name__ == "__main__":
    mostrar_configuracao()
