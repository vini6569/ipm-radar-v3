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

from motor_ipm import (
    calcular_variacao_odd,
    classificar_forca
)

from http.server import HTTPServer, BaseHTTPRequestHandler


# ============================================================
# MEMÓRIA DAS ODDS
# ============================================================
#
# Guarda a última odd conhecida de cada mercado.
#
# Estrutura:
#
# memoria_odds[
#     evento_id,
#     mercado,
#     linha
# ]
#
# = odd anterior
#
# ============================================================

memoria_odds = {}


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
# MEMÓRIA DE UMA ODD
# ============================================================

def processar_movimentacao(
    evento_id,
    mercado,
    linha,
    odd_atual
):

    try:

        odd_atual = float(
            odd_atual
        )

    except (
        TypeError,
        ValueError
    ):

        return None


    if odd_atual <= 0:

        return None


    chave = (
        str(evento_id),
        str(mercado),
        str(linha)
    )


    # ========================================================
    # PRIMEIRA VEZ QUE VEMOS ESTA ODD
    # ========================================================

    if chave not in memoria_odds:

        memoria_odds[chave] = odd_atual

        print(
            f"  NOVA ODD | "
            f"{mercado} | "
            f"Linha: {linha} | "
            f"Odd: {odd_atual:.2f}"
        )

        return None


    # ========================================================
    # ODD ANTERIOR
    # ========================================================

    odd_anterior = memoria_odds[
        chave
    ]


    # ========================================================
    # ATUALIZAR MEMÓRIA
    # ========================================================

    memoria_odds[
        chave
    ] = odd_atual


    # ========================================================
    # CALCULAR VARIAÇÃO
    # ========================================================

    variacao = calcular_variacao_odd(
        odd_anterior,
        odd_atual
    )


    forca = classificar_forca(
        variacao
    )


    # ========================================================
    # MOSTRAR MOVIMENTAÇÃO
    # ========================================================

    print(
        f"  MOVIMENTO | "
        f"{mercado} | "
        f"Linha: {linha} | "
        f"{odd_anterior:.2f} "
        f"→ "
        f"{odd_atual:.2f} | "
        f"{variacao:+.2f}% | "
        f"{forca}"
    )


    return {

        "mercado": mercado,

        "linha": linha,

        "odd_anterior": odd_anterior,

        "odd_atual": odd_atual,

        "variacao_pct": round(
            variacao,
            2
        ),

        "forca": forca

    }


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


    # ========================================================
    # RESULTADO 1X2
    # ========================================================

    print()
    print("RESULTADO 1X2")

    resultado = jogo.get(
        "resultado",
        []
    )

    if resultado:

        for odd in resultado:

            print(
                f"  Casa: {odd.get('home')} | "
                f"Empate: {odd.get('draw')} | "
                f"Fora: {odd.get('away')}"
            )

    else:

        print(
            "  Sem odds de Resultado."
        )


# ============================================================
# ANALISAR MOVIMENTAÇÃO DO JOGO
# ============================================================

def analisar_movimentacao(jogo):

    evento_id = jogo.get(
        "id"
    )

    if not evento_id:

        return


    print()
    print(
        "MOVIMENTAÇÃO DE ODDS"
    )


    # ========================================================
    # TOTAL GOALS
    # ========================================================

    for odd in jogo.get(
        "gols",
        []
    ):

        linha = odd.get(
            "linha"
        )

        over = odd.get(
            "over"
        )

        under = odd.get(
            "under"
        )


        processar_movimentacao(
            evento_id,
            "OVER",
            linha,
            over
        )


        processar_movimentacao(
            evento_id,
            "UNDER",
            linha,
            under
        )


    # ========================================================
    # ASIAN HANDICAP
    # ========================================================

    for odd in jogo.get(
        "handicap",
        []
    ):

        linha = odd.get(
            "linha"
        )

        home = odd.get(
            "home"
        )

        away = odd.get(
            "away"
        )


        processar_movimentacao(
            evento_id,
            "HANDICAP_HOME",
            linha,
            home
        )


        processar_movimentacao(
            evento_id,
            "HANDICAP_AWAY",
            linha,
            away
        )


    # ========================================================
    # RESULTADO 1X2
    # ========================================================

    for odd in jogo.get(
        "resultado",
        []
    ):

        processar_movimentacao(
            evento_id,
            "HOME",
            "1X2",
            odd.get("home")
        )


        processar_movimentacao(
            evento_id,
            "DRAW",
            "1X2",
            odd.get("draw")
        )


        processar_movimentacao(
            evento_id,
            "AWAY",
            "1X2",
            odd.get("away")
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


                # =============================================
                # ANALISAR MOVIMENTAÇÃO
                # =============================================

                analisar_movimentacao(
                    jogo
                )


            # =================================================
            # DIAGNÓSTICO DA MEMÓRIA
            # =================================================

            print()
            print(
                "ODDS NA MEMÓRIA:",
                len(memoria_odds)
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
