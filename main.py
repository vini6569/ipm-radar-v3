# ============================================================
# MAIN - IPM RADAR V3
# ============================================================

import time
import threading
from datetime import datetime, time as horario
from zoneinfo import ZoneInfo
from http.server import HTTPServer, BaseHTTPRequestHandler

from odds_api import (
    buscar_jogos_ao_vivo,
    buscar_odds_multiplos
)

from motor_ipm import (
    processar_evento
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

INTERVALO_CONSULTA = 300
PORTA_SAUDE = 10000

FUSO_BRASIL = ZoneInfo("America/Sao_Paulo")

HORA_INICIO = horario(6, 0)
HORA_FIM = horario(0, 0)


# ============================================================
# SERVIDOR DE SAÚDE
# SEM FLASK
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        agora = datetime.now(FUSO_BRASIL)

        mensagem = (
            "IPM RADAR V3 ONLINE | "
            f"Horario Brasil: {agora.strftime('%d/%m/%Y %H:%M:%S')}"
        )

        resposta = mensagem.encode("utf-8")

        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.send_header(
            "Content-Length",
            str(len(resposta))
        )
        self.end_headers()

        self.wfile.write(resposta)

    def log_message(self, format, *args):
        return


def iniciar_servidor_saude():

    try:

        servidor = HTTPServer(
            ("0.0.0.0", PORTA_SAUDE),
            HealthHandler
        )

        print(
            f"Servidor de saúde iniciado na porta {PORTA_SAUDE}"
        )

        servidor.serve_forever()

    except Exception as erro:

        print(
            "Erro no servidor de saúde:",
            erro
        )


# ============================================================
# HORÁRIO DO BRASIL
# ============================================================

def horario_brasil():

    return datetime.now(FUSO_BRASIL)


# ============================================================
# RADAR ATIVO
# ============================================================

def radar_ativo():

    agora = horario_brasil().time()

    # 06:00 até 23:59
    if agora >= HORA_INICIO:

        return True

    # 00:00 até 05:59
    return False


# ============================================================
# CONSULTA DOS JOGOS
# ============================================================

def executar_consulta():

    agora = horario_brasil()

    print()
    print("============================================================")
    print(
        "📡 RADAR ATIVO |",
        agora.strftime("%d/%m/%Y %H:%M:%S")
    )
    print("============================================================")

    print("Consultando jogos ao vivo...")

    try:

        jogos = buscar_jogos_ao_vivo()

        if jogos is None:
            jogos = []

        print(
            "Jogos ao vivo encontrados:",
            len(jogos)
        )

        if not jogos:

            print(
                "Nenhum jogo ao vivo encontrado."
            )

            return

        # ====================================================
        # BUSCAR ODDS
        # ====================================================

        print("Buscando odds...")

        try:

            odds = buscar_odds_multiplos(jogos)

        except Exception as erro:

            print(
                "Erro ao buscar odds:",
                erro
            )

            odds = []

        if odds is None:
            odds = []

        print(
            "Eventos com odds recebidos:",
            len(odds)
        )

        # ====================================================
        # MOTOR IPM
        # ====================================================

        total_processados = 0

        for evento in jogos:

            try:

                resultado = processar_evento(
                    evento,
                    odds
                )

                total_processados += 1

                if resultado is not None:

                    print(
                        "📊 IPM:",
                        resultado
                    )

            except TypeError:

                # Compatibilidade com versões
                # que usam apenas evento.

                try:

                    resultado = processar_evento(
                        evento
                    )

                    total_processados += 1

                    if resultado is not None:

                        print(
                            "📊 IPM:",
                            resultado
                        )

                except Exception as erro:

                    print(
                        "Erro ao processar evento:",
                        erro
                    )

            except Exception as erro:

                print(
                    "Erro ao processar evento:",
                    erro
                )

        print(
            "Eventos processados:",
            total_processados
        )

    except Exception as erro:

        print(
            "❌ Erro na consulta:",
            erro
        )


# ============================================================
# LOOP PRINCIPAL
# ============================================================

def loop_consulta():

    print()
    print("============================================================")
    print("🚀 IPM RADAR V3 INICIADO")
    print("============================================================")
    print("Fuso horário: America/Sao_Paulo")
    print("Horário ativo: 06:00 até 00:00")
    print("Horário de pausa: 00:00 até 06:00")
    print("Intervalo: 300 segundos")
    print("============================================================")

    while True:

        agora = horario_brasil()

        print()
        print(
            "🕒 Horário Brasil:",
            agora.strftime("%d/%m/%Y %H:%M:%S")
        )

        # ====================================================
        # VERIFICAÇÃO DO HORÁRIO
        # ====================================================

        if radar_ativo():

            executar_consulta()

        else:

            print(
                "⏸️ Radar em período de pausa."
            )

            print(
                "Horário ativo: 06:00 até 00:00"
            )

        # ====================================================
        # ESPERA
        # ====================================================

        print()
        print(
            "⏳ Nova consulta em 300 segundos..."
        )

        time.sleep(
            INTERVALO_CONSULTA
        )


# ============================================================
# INÍCIO DO PROGRAMA
# ============================================================

if __name__ == "__main__":

    print()
    print("============================================================")
    print("IPM RADAR V3")
    print("Inicializando...")
    print("============================================================")

    # Servidor de saúde
    thread_saude = threading.Thread(
        target=iniciar_servidor_saude,
        daemon=True
    )

    thread_saude.start()

    # Radar
    loop_consulta()
