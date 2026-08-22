import os
from datetime import datetime
from zoneinfo import ZoneInfo

# ============================================================
# IPM-RADAR-V3 - CONFIGURAÇÃO CENTRAL
# ROBÔ 2 - RADAR DE MOVIMENTAÇÃO / IPM
# ============================================================
# ATIVO: 06:00 até 00:00
# PAUSA: 00:00 até 06:00
# CONSULTA: 300 segundos (5 minutos)
# ============================================================

NOME_BOT = "IPM-RADAR-V3"
VERSAO = "3.1.0"

MODO_PRODUCAO = os.getenv("MODO_PRODUCAO", "false").lower() == "true"

# FUSO HORÁRIO
FUSO_HORARIO = os.getenv("FUSO_HORARIO", "America/Sao_Paulo")

HORA_INICIO = 6
MINUTO_INICIO = 0
HORA_FIM = 0
MINUTO_FIM = 0


def horario_ativo():
    agora = datetime.now(ZoneInfo(FUSO_HORARIO))
    minutos_atual = agora.hour * 60 + agora.minute
    inicio = HORA_INICIO * 60 + MINUTO_INICIO
    fim = HORA_FIM * 60 + MINUTO_FIM

    if fim == 0:
        return minutos_atual >= inicio

    return inicio <= minutos_atual < fim


def horario_atual():
    return datetime.now(ZoneInfo(FUSO_HORARIO))


# TELEGRAM
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()


# API-FOOTBALL
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY", "").strip()
API_FOOTBALL_KEY_2 = os.getenv("API_FOOTBALL_KEY_2", "").strip()
API_FOOTBALL_URL = "https://v3.football.api-sports.io"


# SPORTS GAME ODDS
SPORTSGAMEODDS_API_KEY = os.getenv("SPORTSGAMEODDS_API_KEY", "").strip()
SPORTSGAMEODDS_URL = "https://api.sportsgameodds.com/v2"


# THE ODDS API
THE_ODDS_API_KEY = os.getenv("ODDS_API_KEY", "").strip()
THE_ODDS_API_URL = "https://api.the-odds-api.com/v4"


# ODDS-API.IO
ODDS_API_IO_KEY = os.getenv("ODDS_API_IO_KEY", "").strip()
ODDS_API_IO_URL = "https://api.odds-api.io/v3"


# AISCORE
AISCORE_URL = "https://www.aiscore.com/br/live"


# FONTES HABILITADAS
USAR_API_FOOTBALL = os.getenv("USAR_API_FOOTBALL", "true").lower() == "true"
USAR_THE_ODDS_API = os.getenv("USAR_THE_ODDS_API", "true").lower() == "true"
USAR_ODDS_API_IO = os.getenv("USAR_ODDS_API_IO", "true").lower() == "true"
USAR_SPORTSGAMEODDS = os.getenv("USAR_SPORTSGAMEODDS", "true").lower() == "true"
USAR_AISCORE = os.getenv("USAR_AISCORE", "true").lower() == "true"


# COLETA
INTERVALO_COLETA = int(os.getenv("INTERVALO_COLETA", "300"))
INTERVALO_RADAR = int(os.getenv("INTERVALO_RADAR", "300"))
MAX_JOGOS_RADAR = int(os.getenv("MAX_JOGOS_RADAR", "10"))


# HISTÓRICO
DATABASE_FILE = os.getenv("DATABASE_FILE", "radar_ipm.db")
HISTORICO_MAXIMO = int(os.getenv("HISTORICO_MAXIMO", "1000"))


# IPM
IPM_MINIMO_OBSERVACAO = float(os.getenv("IPM_MINIMO_OBSERVACAO", "50"))
IPM_MINIMO_FORTE = float(os.getenv("IPM_MINIMO_FORTE", "65"))
IPM_MINIMO_MUITO_FORTE = float(os.getenv("IPM_MINIMO_MUITO_FORTE", "80"))


# MOVIMENTAÇÃO DE ODDS
VARIACAO_MINIMA_ODD = float(os.getenv("VARIACAO_MINIMA_ODD", "0.5"))


# SEGURANÇA - ROBÔ 2 NÃO REALIZA APOSTAS
PERMITIR_APOSTAS = False
PERMITIR_LOGIN_CASA = False
PERMITIR_OPERACAO_AUTOMATICA = False


# LOG
NIVEL_LOG = os.getenv("NIVEL_LOG", "INFO")


def fonte_disponivel(nome):
    fontes = {
        "api_football": bool(API_FOOTBALL_KEY or API_FOOTBALL_KEY_2),
        "the_odds_api": bool(THE_ODDS_API_KEY),
        "odds_api_io": bool(ODDS_API_IO_KEY),
        "sports_game_odds": bool(SPORTSGAMEODDS_API_KEY),
        "aiscore": USAR_AISCORE,
    }
    return fontes.get(nome, False)


def mostrar_configuracao():
    print("=" * 60)
    print(NOME_BOT)
    print("VERSÃO:", VERSAO)
    print("=" * 60)

    print("Fuso horário:", FUSO_HORARIO)
    print("Horário atual:", horario_atual().strftime("%d/%m/%Y %H:%M:%S"))
    print("Radar ativo agora:", horario_ativo())
    print("-" * 60)

    print("Horário de funcionamento: 06:00 até 00:00")
    print("Horário de pausa: 00:00 até 06:00")
    print("Intervalo coleta:", INTERVALO_COLETA, "segundos")
    print("Intervalo radar:", INTERVALO_RADAR, "segundos")
    print("Máximo de jogos:", MAX_JOGOS_RADAR)
    print("-" * 60)

    print("API-Football:", fonte_disponivel("api_football"))
    print("The Odds API:", fonte_disponivel("the_odds_api"))
    print("Odds-API.io:", fonte_disponivel("odds_api_io"))
    print("Sports Game Odds:", fonte_disponivel("sports_game_odds"))
    print("AiScore:", fonte_disponivel("aiscore"))
    print("-" * 60)

    print("IPM observação:", IPM_MINIMO_OBSERVACAO)
    print("IPM forte:", IPM_MINIMO_FORTE)
    print("IPM muito forte:", IPM_MINIMO_MUITO_FORTE)
    print("Variação mínima odd:", VARIACAO_MINIMA_ODD, "%")
    print("-" * 60)

    print("APOSTAS AUTOMÁTICAS: DESATIVADAS")
    print("LOGIN EM CASA DE APOSTA: DESATIVADO")
    print("=" * 60)


if __name__ == "__main__":
    mostrar_configuracao()
    
