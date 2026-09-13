# ============================================================
# MAIN - IPM RADAR V5.1
# PRÉ-LIVE + LIVE
# ============================================================

import os
import time
import threading

from http.server import BaseHTTPRequestHandler, HTTPServer

from config import horario_ativo
from scanner_pre_live import escanear_pre_live
from monitor_live import processar_live


INTERVALO = int(
    os.getenv("INTERVALO_RADAR", "60")
)

# IDs selecionados pelo pré-live
JOGOS_MONITORADOS = {}


# ============================================================
# SERVIDOR DE SAÚDE
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )

        self.end_headers()

        self.wfile.write(
            b"IPM RADAR V5.1 OK"
        )

    def log_message(self, *args):
        return


def iniciar_servidor():

    porta = int(
        os.getenv("PORT", "10000")
    )

    servidor = HTTPServer(
        ("0.0.0.0", porta),
        HealthHandler
    )

    threading.Thread(
        target=servidor.serve_forever,
        daemon=True
    ).start()

    print(
        f"SERVIDOR DE SAUDE | PORTA={porta}"
    )


# ============================================================
# PRÉ-LIVE
# ============================================================

def executar_pre_live():

    try:

        resultados = (
            escanear_pre_live()
            or []
        )

    except Exception as erro:

        print(
            "ERRO PRÉ-LIVE:",
            type(erro).__name__,
            erro
        )

        return

    if not resultados:

        print(
            "PRÉ-LIVE | Nenhum jogo aprovado."
        )

        return

    for jogo in resultados:

        event_id = jogo.get("event_id")

        if event_id is None:
            continue

        event_id = str(event_id)

        JOGOS_MONITORADOS[
            event_id
        ] = jogo

    print(
        f"PRÉ-LIVE | "
        f"{len(resultados)} jogos selecionados | "
        f"RADAR={len(JOGOS_MONITORADOS)}"
    )


# ============================================================
# LIVE
# ============================================================

def executar_live():

    if not JOGOS_MONITORADOS:

        print(
            "LIVE | Nenhum jogo no radar."
        )

        return

    ids = list(
        JOGOS_MONITORADOS.keys()
    )

    try:

        processar_live(
            ids
        )

    except Exception as erro:

        print(
            "ERRO LIVE:",
            type(erro).__name__,
            erro
        )


# ============================================================
# LOOP
# ============================================================

def loop():

    print()
    print("=" * 60)
    print("IPM RADAR V5.1 INICIADO")
    print("=" * 60)

    while True:

        inicio = time.time()

        try:

            if horario_ativo():

                executar_pre_live()

                executar_live()

            else:

                print(
                    "RADAR | Período de pausa."
                )

        except Exception as erro:

            print(
                "ERRO NO LOOP:",
                type(erro).__name__,
                erro
            )

        duracao = (
            time.time()
            - inicio
        )

        espera = max(
            1,
            INTERVALO - duracao
        )

        print(
            f"CICLO | {duracao:.1f}s | "
            f"PRÓXIMO={espera:.0f}s"
        )

        time.sleep(
            espera
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    iniciar_servidor()

    loop()
