# ============================================================
# MAIN - IPM RADAR V3
# TESTE DE COMPARACAO DE ODDS
# ============================================================

import os
import time
import threading

from datetime import datetime, time as horario
from zoneinfo import ZoneInfo

from http.server import (
    HTTPServer,
    BaseHTTPRequestHandler
)

from odds_api import (
    buscar_jogos_ao_vivo,
    buscar_odds_multiplos,
    extrair_mercados,
    _extrair_estatisticas
)

from motor_ipm_v2 import (
    analisar_ipm_com_memoria,
    formatar_radar
)


# ============================================================
# CONFIGURACAO
# ============================================================

INTERVALO_CONSULTA = 300

PORTA_SAUDE = int(
    os.environ.get(
        "PORT",
        "10000"
    )
)

FUSO_BRASIL = ZoneInfo(
    "America/Sao_Paulo"
)

HORA_INICIO = horario(
    6,
    0
)

HORA_FIM = horario(
    0,
    0
)


# ============================================================
# SERVIDOR DE SAUDE
# ============================================================

class HealthHandler(
    BaseHTTPRequestHandler
):

    def do_GET(self):

        agora = datetime.now(
            FUSO_BRASIL
        )

        resposta = (
            "IPM RADAR V3 ONLINE | "
            f"Brasil: "
            f"{agora.strftime('%d/%m/%Y %H:%M:%S')}"
        ).encode(
            "utf-8"
        )

        self.send_response(
            200
        )

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(resposta))
        )

        self.end_headers()

        self.wfile.write(
            resposta
        )

    def log_message(
        self,
        format,
        *args
    ):

        return


def iniciar_servidor_saude():

    try:

        servidor = HTTPServer(
            (
                "0.0.0.0",
                PORTA_SAUDE
            ),
            HealthHandler
        )

        print(
            f"Servidor de saude iniciado "
            f"na porta {PORTA_SAUDE}"
        )

        servidor.serve_forever()

    except Exception as erro:

        print(
            "❌ Erro no servidor de saude:",
            erro
        )


# ============================================================
# HORARIO BRASIL
# ============================================================

def horario_brasil():

    return datetime.now(
        FUSO_BRASIL
    )


# ============================================================
# RADAR ATIVO
# ============================================================

def radar_ativo():

    agora = horario_brasil().time()

    # 06:00 ate 23:59
    if agora >= HORA_INICIO:

        return True

    return False


# ============================================================
# CONSULTA
# ============================================================

def executar_consulta():

    agora = horario_brasil()

    print()
    print(
        "=" * 60
    )

    print(
        "📡 RADAR V3 |",
        agora.strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    )

    print(
        "=" * 60
    )

    # ========================================================
    # JOGOS AO VIVO
    # ========================================================

    print(
        "📡 Consultando jogos ao vivo..."
    )

    try:

        jogos = buscar_jogos_ao_vivo()

        if jogos is None:

            jogos = []

        print(
            "⚽ Jogos ao vivo encontrados:",
            len(jogos)
        )

        if not jogos:

            print(
                "Nenhum jogo ao vivo encontrado."
            )

            return

    except Exception as erro:

        print(
            "❌ Erro ao buscar jogos:",
            erro
        )

        return

    # ========================================================
    # ODDS
    # ========================================================

    print(
        "💰 Buscando odds..."
    )

    try:

        odds = buscar_odds_multiplos(
            jogos
        )

        if odds is None:

            odds = []

        print(
            "💰 Eventos com odds recebidos:",
            len(odds)
        )

    except Exception as erro:

        print(
            "❌ Erro ao buscar odds:",
            erro
        )

        odds = []

    # ========================================================
    # ANALISAR JOGOS
    # ========================================================

    for jogo in jogos:

        try:

            # ------------------------------------------------
            # MERCADOS
            # ------------------------------------------------

            mercados = extrair_mercados(
                jogo,
                odds
            )

            if mercados is None:

                mercados = {}

            # ------------------------------------------------
            # ID DO JOGO
            # ------------------------------------------------

            event_id = jogo.get(
                "id"
            )

            if event_id is None:

                print(
                    "⚠️ Jogo sem ID. Ignorado."
                )

                continue

            # ------------------------------------------------
            # ODD ATUAL
            # ------------------------------------------------

            odd_atual = mercados.get(
                "odd_atual"
            )

            # ------------------------------------------------
            # DADOS DO JOGO
            # ------------------------------------------------

            minuto = mercados.get(
                "minuto",
                0
            )

            gols = mercados.get(
                "gols",
                0
            )

            # ------------------------------------------------
            # ESTATISTICAS
            # ------------------------------------------------

            try:

                (
                    escanteios,
                    finalizacoes,
                    ataques_perigosos
                ) = _extrair_estatisticas(
                    jogo
                )

            except Exception as erro_estatisticas:

                print(
                    "⚠️ Erro nas estatisticas:",
                    erro_estatisticas
                )

                escanteios = 0
                finalizacoes = 0
                ataques_perigosos = 0

            # =================================================
            # CABECALHO DO TESTE
            # =================================================

            print()
            print(
                "-" * 60
            )

            print(
                "🔎 TESTE DE COMPARACAO"
            )

            print(
                "EVENT ID:",
                event_id
            )

            print(
                "ODD ATUAL RECEBIDA:",
                odd_atual
            )

            # =================================================
            # MOTOR IPM COM MEMORIA
            # =================================================

            resultado = analisar_ipm_com_memoria(

                event_id,

                odd_atual,

                minuto,

                gols,

                escanteios,

                finalizacoes,

                ataques_perigosos
            )

            # =================================================
            # DIAGNOSTICO
            # =================================================

            print(
                "ODD ANTERIOR:",
                resultado.get(
                    "odd_anterior"
                )
            )

            print(
                "ODD ATUAL:",
                resultado.get(
                    "odd_atual"
                )
            )

            print(
                "VARIACAO:",
                resultado.get(
                    "variacao_odd"
                ),
                "%"
            )

            print(
                "MOVIMENTO:",
                resultado.get(
                    "movimento"
                )
            )

            print(
                "FORCA:",
                resultado.get(
                    "forca"
                )
            )

            print(
                "IPM:",
                resultado.get(
                    "ipm"
                )
            )

            # =================================================
            # RADAR
            # =================================================

            texto = formatar_radar(
                jogo,
                resultado
            )

            if texto:

                print(
                    texto
                )

            print(
                "-" * 60
            )

        except Exception as erro_jogo:

            print(
                "❌ Erro ao analisar jogo:",
                erro_jogo
            )


# ============================================================
# LOOP
# ============================================================

def loop_consulta():

    print()
    print(
        "=" * 60
    )

    print(
        "🚀 IPM RADAR V3"
    )

    print(
        "=" * 60
    )

    print(
        "Fuso: America/Sao_Paulo"
    )

    print(
        "Horario ativo: 06:00 ate 00:00"
    )

    print(
        "Intervalo:",
        INTERVALO_CONSULTA,
        "segundos"
    )

    print(
        "Motor: motor_ipm_v2.py"
    )

    print(
        "Memoria: ODD ANTERIOR x ODD ATUAL"
    )

    print(
        "=" * 60
    )

    while True:

        agora = horario_brasil()

        print()

        print(
            "🕒 Horario Brasil:",
            agora.strftime(
                "%d/%m/%Y %H:%M:%S"
            )
        )

        if radar_ativo():

            executar_consulta()

        else:

            print(
                "⏸️ Radar em periodo de pausa."
            )

            print(
                "Horario ativo: 06:00 ate 00:00"
            )

        print()

        print(
            "⏳ Nova consulta em",
            INTERVALO_CONSULTA,
            "segundos..."
        )

        time.sleep(
            INTERVALO_CONSULTA
        )


# ============================================================
# INICIO
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "=" * 60
    )

    print(
        "IPM RADAR V3"
    )

    print(
        "Inicializando..."
    )

    print(
        "=" * 60
    )

    thread_saude = threading.Thread(

        target=iniciar_servidor_saude,

        daemon=True
    )

    thread_saude.start()

    loop_consulta()
