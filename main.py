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

                print("-" * 50)

                print(
                    jogo.get("home"),
                    "x",
                    jogo.get("away")
                )

                print("ID:", jogo.get("id"))
                print("PLACAR:", jogo.get("scores"))

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
