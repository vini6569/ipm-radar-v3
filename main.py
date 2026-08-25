# ============================================================
# MAIN - IPM RADAR V3 - TESTE DE COMPARACAO
# ============================================================

import os
import time
import threading
from datetime import datetime, time as horario
from zoneinfo import ZoneInfo
from http.server import HTTPServer, BaseHTTPRequestHandler

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
PORTA_SAUDE = int(os.environ.get("PORT", "10000"))

FUSO_BRASIL = ZoneInfo("America/Sao_Paulo")

HORA_INICIO = horario(6, 0)
HORA_FIM = horario(0, 0)


# ============================================================
# SERVIDOR DE SAUDE
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        agora = datetime.now(FUSO_BRASIL)

        resposta = (
            "IPM RADAR V3 TESTE ONLINE | "
            f"Brasil: {agora.strftime('%d/%m/%Y %H:%M:%S')}"
        ).encode("utf-8")

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
# HORARIO BRASIL
# ============================================================

def horario_brasil():

    return datetime.now(FUSO_BRASIL)


# ============================================================
# RADAR ATIVO
# ============================================================

def radar_ativo():

    agora = horario_brasil().time()

    if HORA_INICIO <= agora:

        return True

    return False


# ============================================================
# CONSULTA
# ============================================================

def executar_consulta():

    agora = horario_brasil()

    print()
    print("=" * 60)
    print(
        "📡 RADAR TESTE |",
        agora.strftime("%d/%m/%Y %H:%M:%S")
    )
    print("=" * 60)

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

            print("Nenhum jogo ao vivo encontrado.")
            return

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
        # ANALISAR CADA JOGO
        # ====================================================

        for jogo in jogos:

            try:

                mercados = extrair_mercados(
                    jogo,
                    odds
                )

                if mercados is None:
                    mercados = {}

                # =================================================
                # DADOS DAS ODDS
                # =================================================

                odd_atual = mercados.get(
                    "odd_atual",
                    0
                )

                event_id = jogo.get(
                    "id"
                )

                # =================================================
                # DADOS DO EVENTO
                # =================================================

                minuto = mercados.get(
                    "minuto",
                    0
                )

                gols = mercados.get(
                    "gols",
                    0
                )

                # =================================================
                # ESTATISTICAS REAIS
                # =================================================

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
                        "Erro ao extrair estatísticas:",
                        erro_estatisticas
                    )

                    escanteios = 0
                    finalizacoes = 0
                    ataques_perigosos = 0


                # =================================================
                # DIAGNOSTICO DA COMPARACAO
                # =================================================

                print()
                print("-" * 60)
                print("🔎 TESTE DE COMPARACAO DE ODDS")
                print("EVENT ID:", event_id)
                print("ODD ATUAL RECEBIDA:", odd_atual)

                # =================================================
                # MOTOR IPM V2 COM MEMORIA
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

                print(
                    "ODD ANTERIOR:",
                    resultado.get("odd_anterior")
                )

                print(
                    "ODD ATUAL:",
                    resultado.get("odd_atual")
                )

                print(
                    "VARIACAO:",
                    resultado.get("variacao_odd"),
                    "%"
                )

                print(
                    "MOVIMENTO:",
                    resultado.get("movimento")
                )

                print(
                    "IPM:",
                    resultado.get("ipm")
                )

                print("-" * 60)


                # =================================================
                # EXIBICAO DO RADAR
                # =================================================

                try:

                    texto = formatar_radar(
                        jogo,
                        resultado
                    )

                    if texto:
                        print(texto)

                except Exception as erro_formatacao:

                    print(
                        "Erro ao formatar radar:",
                        erro_formatacao
                    )

                    print(
                        "📊 IPM:",
                        resultado
                    )

            except Exception as erro:

                print(
                    "Erro ao analisar jogo:",
                    erro
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
    print("=" * 60)
    print("🚀 IPM RADAR V3 - TESTE")
    print("=" * 60)
    print("Fuso horário: America/Sao_Paulo")
    print("Horário ativo: 06:00 até 00:00")
    print("Intervalo: 300 segundos")
    print("Motor: motor_ipm_v2.py")
    print("Comparação: ODD ANTERIOR x ODD ATUAL")
    print("=" * 60)

    while True:

        agora = horario_brasil()

        print()
        print(
            "🕒 Horário Brasil:",
            agora.strftime("%d/%m/%Y %H:%M:%S")
        )

        if radar_ativo():

            executar_consulta()

        else:

            print(
                "⏸️ Radar em período de pausa."
            )

            print(
                "Horário ativo: 06:00 até 00:00"
            )

        print()

        print(
            "⏳ Nova consulta em 300 segundos..."
        )

        time.sleep(
            INTERVALO_CONSULTA
        )


# ============================================================
# INICIO
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("IPM RADAR V3 - TESTE")
    print("Inicializando...")
    print("=" * 60)

    thread_saude = threading.Thread(
        target=iniciar_servidor_saude,
        daemon=True
    )

    thread_saude.start()

    loop_consulta()
                
