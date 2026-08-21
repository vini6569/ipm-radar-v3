import time
import os
import threading

from config import NOME_BOT, VERSAO

from odds_api import (
    buscar_jogos_ao_vivo,
    buscar_odds_multiplos,
    extrair_mercados
)

from historico import quantidade_jogos

from http.server import HTTPServer, BaseHTTPRequestHandler


# ============================================================
# SERVIDOR DE SAÚDE
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-type",
            "text/plain"
        )

        self.end_headers()

        self.wfile.write(
            b"IPM RADAR V3 ONLINE"
        )

    def log_message(self, format, *args):
        return


def iniciar_servidor():

    porta = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    servidor = HTTPServer(
        ("0.0.0.0", porta),
        HealthHandler
    )

    servidor.serve_forever()


# ============================================================
# MOSTRAR ODDS
# ============================================================

def mostrar_odds(jogo):

    # ========================================================
    # TOTAL GOALS
    # ========================================================

    print()
    print("TOTAL GOALS")

    gols = jogo.get(
        "gols",
        []
    )

    if gols:

        for odd in gols:

            linha = odd.get(
                "linha"
            )

            over = odd.get(
                "over"
            )

            under = odd.get(
                "under"
            )

            print(
                f"  Linha {linha} | "
                f"Over: {over} | "
                f"Under: {under}"
            )

    else:

        print(
            "  Sem odds de Total Goals."
        )


    # ========================================================
    # ASIAN HANDICAP
    # ========================================================

    print()
    print("ASIAN HANDICAP")

    handicap = jogo.get(
        "handicap",
        []
    )

    if handicap:

        for odd in handicap:

            linha = odd.get(
                "linha"
            )

            home = odd.get(
                "home"
            )

            away = odd.get(
                "away"
            )

            print(
                f"  Linha {linha} | "
                f"Casa: {home} | "
                f"Fora: {away}"
            )

    else:

        print(
            "  Sem odds de Asian Handicap."
        )


# ============================================================
# INICIAR RADAR
# ============================================================

def iniciar():

    print("=" * 60)
    print(NOME_BOT)
    print("VERSÃO:", VERSAO)
    print("=" * 60)

    print(
        "IPM-RADAR-V3 iniciado."
    )

    print(
        "Histórico registrado:",
        quantidade_jogos()
    )

    print()


    # ========================================================
    # LOOP PRINCIPAL
    # ========================================================

    while True:

        try:

            # =================================================
            # 1. BUSCAR JOGOS AO VIVO
            # =================================================

            jogos = buscar_jogos_ao_vivo()

            print(
                "Jogos ao vivo encontrados:",
                len(jogos)
            )


            # =================================================
            # 2. BUSCAR ODDS DOS JOGOS
            # =================================================

            odds_eventos = []

            if jogos:

                odds_eventos = (
                    buscar_odds_multiplos(
                        jogos
                    )
                )

            print(
                "Eventos com odds recebidos:",
                len(odds_eventos)
            )


            # =================================================
            # 3. ORGANIZAR ODDS POR ID
            # =================================================

            odds_por_id = {}

            for odds_evento in odds_eventos:

                if not isinstance(
                    odds_evento,
                    dict
                ):
                    continue

                evento_id = odds_evento.get(
                    "id"
                )

                if evento_id:

                    odds_por_id[
                        str(evento_id)
                    ] = odds_evento


            # =================================================
            # 4. PROCESSAR CADA JOGO
            # =================================================

            for jogo in jogos:

                if not isinstance(
                    jogo,
                    dict
                ):
                    continue


                print("-" * 60)


                # =============================================
                # INFORMAÇÕES DO JOGO
                # =============================================

                print(
                    jogo.get("home"),
                    "x",
                    jogo.get("away")
                )

                print(
                    "ID:",
                    jogo.get("id")
                )

                print(
                    "PLACAR:",
                    jogo.get("scores")
                )


                # =============================================
                # PROCURAR ODDS DESTE JOGO
                # =============================================

                jogo_id = jogo.get(
                    "id"
                )

                odds_evento = odds_por_id.get(
                    str(jogo_id)
                )


                if odds_evento:

                    mercados = (
                        extrair_mercados(
                            odds_evento
                        )
                    )

                    # Coloca os mercados dentro
                    # do jogo para o mostrar_odds()
                    jogo["gols"] = mercados.get(
                        "gols",
                        []
                    )

                    jogo["handicap"] = mercados.get(
                        "handicap",
                        []
                    )

                    jogo["resultado"] = mercados.get(
                        "resultado",
                        []
                    )

                else:

                    jogo["gols"] = []
                    jogo["handicap"] = []
                    jogo["resultado"] = []

                    print(
                        "Nenhuma resposta de odds "
                        "encontrada para este ID."
                    )


                # =============================================
                # MOSTRAR ODDS
                # =============================================

                mostrar_odds(
                    jogo
                )


            # =================================================
            # AGUARDAR PRÓXIMA CONSULTA
            # =================================================

            print()
            print(
                "Nova consulta em 60 segundos..."
            )

            time.sleep(60)


        except Exception as erro:

            print()
            print(
                "ERRO NO RADAR:"
            )

            print(
                type(erro).__name__
            )

            print(
                erro
            )

            print()

            time.sleep(30)


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    threading.Thread(
        target=iniciar_servidor,
        daemon=True
    ).start()

    iniciar()
