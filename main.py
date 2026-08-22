# ============================================================
# IPM-RADAR-V3
# MAIN
#
# Robô 2 - Radar de Movimentação / IPM
#
# ============================================================

import time
import threading
from datetime import datetime

import odds_api
import telegram
import historico
import motor_ipm


# ============================================================
# CONFIGURAÇÃO
# ============================================================

INTERVALO_CONSULTA = 300  # 5 minutos

HORARIO_INICIO = 6
HORARIO_FIM = 24


# ============================================================
# SERVIDOR DE SAÚDE PARA O RENDER
# ============================================================

def servidor_saude():

    try:

        from http.server import (
            BaseHTTPRequestHandler,
            HTTPServer
        )

        class Handler(BaseHTTPRequestHandler):

            def do_GET(self):

                self.send_response(200)

                self.send_header(
                    "Content-type",
                    "text/plain; charset=utf-8"
                )

                self.end_headers()

                self.wfile.write(
                    b"IPM-RADAR-V3 ONLINE"
                )

            def log_message(
                self,
                formato,
                *args
            ):

                return

        servidor = HTTPServer(
            ("0.0.0.0", 10000),
            Handler
        )

        print(
            "Servidor de saúde iniciado na porta 10000"
        )

        servidor.serve_forever()

    except Exception as erro:

        print(
            "ERRO NO SERVIDOR DE SAUDE:",
            type(erro).__name__,
            erro
        )


# ============================================================
# VERIFICAR HORÁRIO
# ============================================================

def radar_ativo():

    hora = datetime.now().hour

    if HORARIO_INICIO <= hora < HORARIO_FIM:

        return True

    return False


# ============================================================
# EXECUTAR UMA CONSULTA
# ============================================================

def executar_consulta():

    print()
    print("=" * 60)
    print(
        "RADAR IPM - NOVA CONSULTA"
    )
    print("=" * 60)

    # ========================================================
    # JOGOS AO VIVO
    # ========================================================

    print()

    jogos = odds_api.buscar_jogos_ao_vivo()

    if not jogos:

        print(
            "Nenhum jogo ao vivo encontrado."
        )

        print(
            "Eventos com odds recebidos: 0"
        )

        return

    print(
        "Jogos ao vivo encontrados:",
        len(jogos)
    )

    # ========================================================
    # ODDS
    # ========================================================

    eventos_odds = (
        odds_api.buscar_odds_multiplos(
            jogos
        )
    )

    print(
        "Eventos com odds recebidos:",
        len(eventos_odds)
    )

    # ========================================================
    # MEMÓRIA / HISTÓRICO
    # ========================================================

    print()

    print(
        "ODDS NA MEMÓRIA: 0"
    )

    print(
        "SINAIS NA MEMÓRIA: 0"
    )

    print(
        "HISTÓRICO REGISTRADO: 0"
    )

    # ========================================================
    # PROCESSAR CADA EVENTO
    # ========================================================

    for evento in eventos_odds:

        if not isinstance(
            evento,
            dict
        ):

            continue

        try:

            print()
            print(
                "-" * 60
            )

            print(
                "PROCESSANDO EVENTO:",
                evento.get("id")
            )

            print(
                "JOGO:",
                evento.get("home"),
                "x",
                evento.get("away")
            )

            # ------------------------------------------------
            # DIAGNÓSTICO DAS ODDS
            # ------------------------------------------------

            odds_api.mostrar_resumo_odds(
                evento
            )

        except Exception as erro:

            print(
                "ERRO PROCESSANDO EVENTO:"
            )

            print(
                type(erro).__name__,
                erro
            )

    print()
    print("=" * 60)
    print(
        "CONSULTA FINALIZADA"
    )
    print("=" * 60)


# ============================================================
# LOOP PRINCIPAL
# ============================================================

def iniciar_radar():

    print()
    print("=" * 60)
    print(
        "📡 IPM-RADAR-V3"
    )
    print(
        "RADAR DE MOVIMENTAÇÃO / IPM"
    )
    print("=" * 60)

    print(
        "Horário ativo:",
        "06:00 até 00:00"
    )

    print(
        "Intervalo:",
        INTERVALO_CONSULTA,
        "segundos"
    )

    print("=" * 60)

    while True:

        try:

            agora = datetime.now()

            print()
            print(
                "📡 RADAR ATIVO |",
                agora.strftime(
                    "%d/%m/%Y %H:%M:%S"
                )
            )

            # =================================================
            # HORÁRIO DE FUNCIONAMENTO
            # =================================================

            if radar_ativo():

                executar_consulta()

            else:

                print(
                    "⏸️ Radar em período de pausa."
                )

                print(
                    "Horário ativo: 06:00 até 00:00"
                )

            # =================================================
            # AGUARDAR
            # =================================================

            print()

            print(
                "⏳ Nova consulta em",
                INTERVALO_CONSULTA,
                "segundos..."
            )

            time.sleep(
                INTERVALO_CONSULTA
            )

        except KeyboardInterrupt:

            print()
            print(
                "Radar encerrado."
            )

            break

        except Exception as erro:

            print()
            print("=" * 60)
            print(
                "ERRO NO RADAR"
            )
            print("=" * 60)

            print(
                type(erro).__name__,
                erro
            )

            print("=" * 60)

            time.sleep(30)


# ============================================================
# INICIALIZAÇÃO
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Servidor de saúde
    # --------------------------------------------------------

    thread_saude = threading.Thread(
        target=servidor_saude,
        daemon=True
    )

    thread_saude.start()

    # --------------------------------------------------------
    # Radar
    # --------------------------------------------------------

    iniciar_radar()
