import time
import os
import threading

from config import NOME_BOT, VERSAO
from odds_api import buscar_jogos_ao_vivo
from historico import quantidade_jogos
from http.server import HTTPServer, BaseHTTPRequestHandler


class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"IPM RADAR V3 ONLINE")

    def log_message(self, format, *args):
        return


def iniciar_servidor():

    porta = int(os.environ.get("PORT", 10000))

    servidor = HTTPServer(
        ("0.0.0.0", porta),
        HealthHandler
    )

    servidor.serve_forever()


def mostrar_odds(jogo):

    # ==============================
    # TOTAL GOALS
    # ==============================

    print()
    print("TOTAL GOALS")

    gols = jogo.get("gols", [])

    if gols:
        for odd in gols:
            linha = odd.get("linha")
            over = odd.get("over")
            under = odd.get("under")

            print(
                f"  Linha {linha} | "
                f"Over: {over} | "
                f"Under: {under}"
            )
    else:
        print("  Sem odds de Total Goals.")

    # ==============================
    # ASIAN HANDICAP
    # ==============================

    print()
    print("ASIAN HANDICAP")

    handicap = jogo.get("handicap", [])

    if handicap:
        for odd in handicap:
            linha = odd.get("linha")
            home = odd.get("home")
            away = odd.get("away")

            print(
                f"  Linha {linha} | "
                f"Casa: {home} | "
                f"Fora: {away}"
            )
    else:
        print("  Sem odds de Asian Handicap.")


def iniciar():

    print("=" * 60)
    print(NOME_BOT)
    print("VERSÃO:", VERSAO)
    print("=" * 60)

    print("IPM-RADAR-V3 iniciado.")
    print("Histórico registrado:", quantidade_jogos())
    print()

    while True:

        try:

            jogos = buscar_jogos_ao_vivo()

            print("Jogos ao vivo encontrados:", len(jogos))

            for jogo in jogos:

                print("-" * 60)

                print(
                    jogo.get("home"),
                    "x",
                    jogo.get("away")
                )

                print("ID:", jogo.get("id"))
                print("PLACAR:", jogo.get("scores"))

                # Mostra as odds para análise do IPM
                mostrar_odds(jogo)

            print()
            print("Nova consulta em 60 segundos...")

            time.sleep(60)

        except Exception as erro:

            print("ERRO NO RADAR:")
            print(type(erro).__name__)
            print(erro)

            time.sleep(30)


if __name__ == "__main__":

    threading.Thread(
        target=iniciar_servidor,
        daemon=True
    ).start()

    iniciar()
    
