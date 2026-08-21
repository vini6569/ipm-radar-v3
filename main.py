import time
import os
import threading

from config import (
    NOME_BOT,
    VERSAO,
    COLETA_SEGUNDOS,
    MAX_JOGOS_RADAR,
)
from odds_api import (
    buscar_jogos_ao_vivo,
    buscar_odds_multiplos,
    extrair_mercados,
)
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


def obter_id(evento):
    """Retorna o ID do evento como string para comparação segura."""
    if not isinstance(evento, dict):
        return None

    evento_id = evento.get("id")

    if evento_id is None:
        return None

    return str(evento_id)


def anexar_odds(jogos):
    """
    Busca as odds dos eventos encontrados e anexa os mercados
    diretamente em cada jogo.

    Antes, o main.py apenas buscava os jogos ao vivo e tentava
    ler jogo['gols'] e jogo['handicap'], mas esses campos nunca
    eram preenchidos.
    """

    if not jogos:
        return jogos

    try:
        respostas_odds = buscar_odds_multiplos(jogos)

    except Exception as erro:
        print("ERRO AO BUSCAR ODDS:")
        print(type(erro).__name__)
        print(erro)
        return jogos

    odds_por_id = {}

    for resposta in respostas_odds:

        if not isinstance(resposta, dict):
            continue

        evento_id = obter_id(resposta)

        if evento_id is None:
            continue

        odds_por_id[evento_id] = resposta

    for jogo in jogos:

        evento_id = obter_id(jogo)

        # Garante que os campos existam mesmo sem odds.
        jogo["resultado"] = []
        jogo["gols"] = []
        jogo["handicap"] = []

        if evento_id is None:
            continue

        resposta_odds = odds_por_id.get(evento_id)

        if not resposta_odds:
            continue

        mercados = extrair_mercados(resposta_odds)

        if not isinstance(mercados, dict):
            continue

        jogo["resultado"] = mercados.get("resultado", [])
        jogo["gols"] = mercados.get("gols", [])
        jogo["handicap"] = mercados.get("handicap", [])

    return jogos


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

            # 1. Busca os jogos ao vivo.
            jogos = buscar_jogos_ao_vivo()

            # Limita a quantidade processada pelo Radar.
            jogos = jogos[:MAX_JOGOS_RADAR]

            print("Jogos ao vivo encontrados:", len(jogos))

            # 2. Busca as odds dos mesmos jogos.
            jogos = anexar_odds(jogos)

            # 3. Exibe os jogos já com os mercados anexados.
            for jogo in jogos:

                print("-" * 60)

                print(
                    jogo.get("home"),
                    "x",
                    jogo.get("away")
                )

                print("ID:", jogo.get("id"))
                print("PLACAR:", jogo.get("scores"))

                mostrar_odds(jogo)

            print()
            print(
                f"Nova consulta em {COLETA_SEGUNDOS} segundos..."
            )

            time.sleep(COLETA_SEGUNDOS)

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
    
