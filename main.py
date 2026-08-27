# ============================================================
# MAIN - IPM RADAR V4.1
# ============================================================

import os
import time
import threading

from http.server import (
    HTTPServer,
    BaseHTTPRequestHandler,
)


from config import (
    NOME_BOT,
    VERSAO,
    INTERVALO_RADAR,
    MAX_JOGOS_RADAR,
    IPM_MINIMO_OBSERVACAO,
    IPM_MINIMO_FORTE,
    IPM_MINIMO_MUITO_FORTE,
    VARIACAO_MINIMA_ODD,
    horario_ativo,
    horario_atual,
)


from odds_api import (
    buscar_jogos_ao_vivo,
    buscar_odds_multiplos,
    extrair_mercados,
)


from motor_ipm import (
    analisar_ipm_com_memoria,
    formatar_radar,
)


# ============================================================
# PORTA DO RENDER
# ============================================================

PORTA_SAUDE = int(
    os.environ.get(
        "PORT",
        "10000"
    )
)


# ============================================================
# SERVIDOR DE SAÚDE
# ============================================================

class HealthHandler(
    BaseHTTPRequestHandler
):

    def do_GET(
        self
    ):

        try:

            agora = horario_atual()

            corpo = (
                f"{NOME_BOT} ONLINE | "
                f"Brasil: "
                f"{agora.strftime('%d/%m/%Y %H:%M:%S')} | "
                f"Versão: {VERSAO}"
            ).encode(
                "utf-8"
            )

            self.send_response(
                200
            )

            self.send_header(
                "Content-Type",
                "text/plain; "
                "charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(
                    len(corpo)
                )
            )

            self.end_headers()

            self.wfile.write(
                corpo
            )

        except Exception:

            try:

                self.send_response(
                    500
                )

                self.end_headers()

            except Exception:

                pass


    def log_message(
        self,
        format,
        *args
    ):

        return


# ============================================================
# INICIAR SERVIDOR
# ============================================================

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
            "🌐 Servidor de saúde iniciado "
            f"na porta {PORTA_SAUDE}"
        )

        servidor.serve_forever()

    except Exception as erro:

        print(
            "❌ ERRO NO SERVIDOR DE SAÚDE:",
            type(erro).__name__,
            erro
        )


# ============================================================
# CLASSIFICAR SINAL
# ============================================================

def classificar_sinal(
    ipm
):

    try:

        valor = float(
            ipm
        )

    except (
        TypeError,
        ValueError
    ):

        valor = 0.0


    if valor >= IPM_MINIMO_MUITO_FORTE:

        return "SINAL MUITO FORTE"


    if valor >= IPM_MINIMO_FORTE:

        return "SINAL FORTE"


    if valor >= IPM_MINIMO_OBSERVACAO:

        return "OBSERVAR"


    return "SEM SINAL"


# ============================================================
# MOSTRAR MERCADOS
# ============================================================

def _mostrar_mercados(
    mercados
):

    if not isinstance(
        mercados,
        dict
    ):

        return


    todos = mercados.get(
        "todos",
        []
    )

    ht = mercados.get(
        "odds_ht",
        []
    )

    corners = mercados.get(
        "odds_corners",
        []
    )

    cards = mercados.get(
        "odds_cards",
        []
    )

    ft = mercados.get(
        "odds_ft",
        []
    )


    print()

    print(
        "📦 TODOS OS MERCADOS:",
        len(todos)
    )

    print(
        "📊 MERCADOS FT:",
        len(ft)
    )

    print(
        "⏱️ MERCADOS HT:",
        len(ht)
    )

    print(
        "🚩 MERCADOS ESCANTEIOS:",
        len(corners)
    )

    print(
        "🟨 MERCADOS CARTÕES:",
        len(cards)
    )


    # ========================================================
    # HT
    # ========================================================

    if ht:

        print()

        print(
            "⏱️ DETALHES DOS MERCADOS HT:"
        )

        for mercado in ht:

            print(
                "   ",
                mercado.get(
                    "name"
                ),
                ":",
                mercado.get(
                    "odds"
                )
            )


    # ========================================================
    # ESCANTEIOS
    # ========================================================

    if corners:

        print()

        print(
            "🚩 DETALHES DOS MERCADOS "
            "DE ESCANTEIOS:"
        )

        for mercado in corners:

            print(
                "   ",
                mercado.get(
                    "name"
                ),
                ":",
                mercado.get(
                    "odds"
                )
            )


    # ========================================================
    # CARTÕES
    # ========================================================

    if cards:

        print()

        print(
            "🟨 DETALHES DOS MERCADOS "
            "DE CARTÕES:"
        )

        for mercado in cards:

            print(
                "   ",
                mercado.get(
                    "name"
                ),
                ":",
                mercado.get(
                    "odds"
                )
            )


# ============================================================
# EXECUTAR UMA CONSULTA
# ============================================================

def executar_consulta():

    agora = horario_atual()

    print()

    print(
        "=" * 70
    )

    print(
        "📡 IPM RADAR V4.1 |",
        agora.strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    )

    print(
        "=" * 70
    )


    try:

        # ====================================================
        # JOGOS
        # ====================================================

        jogos = (
            buscar_jogos_ao_vivo()
            or []
        )

        print()

        print(
            "JOGOS AO VIVO ENCONTRADOS:",
            len(jogos)
        )


        if not jogos:

            print(
                "ℹ️ Nenhum jogo ao vivo "
                "encontrado neste ciclo."
            )

            return


        # ====================================================
        # LIMITA JOGOS
        # ====================================================

        jogos = jogos[
            :MAX_JOGOS_RADAR
        ]


        print(
            "JOGOS SELECIONADOS PARA O RADAR:",
            len(jogos)
        )


        # ====================================================
        # ODDS
        # ====================================================

        odds = (
            buscar_odds_multiplos(
                jogos
            )
            or []
        )


        print()

        print(
            "EVENTOS COM ODDS RECEBIDOS:",
            len(odds)
        )


        # ====================================================
        # ANALISAR CADA JOGO
        # ====================================================

        for jogo in jogos:

            try:

                if not isinstance(
                    jogo,
                    dict
                ):

                    continue


                # ============================================
                # EXTRAÇÃO
                # ============================================

                mercados = (
                    extrair_mercados(
                        jogo,
                        odds
                    )
                    or {}
                )


                event_id = jogo.get(
                    "id"
                )


                # ============================================
                # ODD DO EMPATE
                # ============================================

                odd_atual = mercados.get(
                    "odd_atual",
                    0.0
                )


                # ============================================
                # MOTOR IPM
                # ============================================

                resultado = (
                    analisar_ipm_com_memoria(
                        event_id,

                        odd_atual,

                        mercados.get(
                            "minuto",
                            0
                        ),

                        mercados.get(
                            "gols",
                            0
                        ),

                        mercados.get(
                            "escanteios",
                            0
                        ),

                        mercados.get(
                            "finalizacoes",
                            0
                        ),

                        mercados.get(
                            "ataques_perigosos",
                            0
                        ),
                    )
                )


                # ============================================
                # RADAR
                # ============================================

                print(
                    formatar_radar(
                        jogo,
                        resultado,
                        mercados
                    )
                )


                # ============================================
                # SINAL
                # ============================================

                ipm = resultado.get(
                    "ipm",
                    0
                )

                variacao = resultado.get(
                    "variacao_odd",
                    0
                )


                filtro_odd = (
                    abs(
                        float(
                            variacao
                        )
                    )
                    >=
                    VARIACAO_MINIMA_ODD
                )


                print()

                print(
                    "🚦 SINAL:",
                    classificar_sinal(
                        ipm
                    )
                )

                print(
                    "💰 FILTRO ODD:",
                    filtro_odd
                )


                # ============================================
                # MERCADOS
                # ============================================

                _mostrar_mercados(
                    mercados
                )


            except Exception as erro_jogo:

                print()

                print(
                    "❌ ERRO AO ANALISAR JOGO:",
                    type(
                        erro_jogo
                    ).__name__,
                    erro_jogo
                )

                # Um jogo com problema
                # não derruba o radar inteiro.

                continue


    except Exception as erro:

        print()

        print(
            "❌ ERRO NO CICLO:",
            type(
                erro
            ).__name__,
            erro
        )


# ============================================================
# LOOP PRINCIPAL
# ============================================================

def loop_consulta():

    print()

    print(
        "=" * 70
    )

    print(
        f"🚀 {NOME_BOT} | "
        f"VERSÃO {VERSAO}"
    )

    print(
        "Janela: 06:00 até 00:00"
    )

    print(
        f"Intervalo: "
        f"{INTERVALO_RADAR} segundos"
    )

    print(
        "Máximo de jogos:",
        MAX_JOGOS_RADAR
    )

    print(
        "Máximo de eventos por "
        "consulta:",
        "10"
    )

    print(
        "Fluxo:"
    )

    print(
        "jogos → odds → "
        "todos → FT/HT/"
        "escanteios/cartões → IPM"
    )

    print(
        "Proteção:"
    )

    print(
        "erros isolados não "
        "derrubam o ciclo"
    )

    print(
        "=" * 70
    )


    while True:

        inicio_ciclo = time.time()

        try:

            agora = horario_atual()

            print()

            print(
                "🕒 Horário Brasil:",
                agora.strftime(
                    "%d/%m/%Y %H:%M:%S"
                )
            )


            if horario_ativo():

                executar_consulta()

            else:

                print(
                    "⏸️ Radar em período "
                    "de pausa."
                )


        except Exception as erro:

            print(
                "❌ ERRO NO LOOP:",
                type(
                    erro
                ).__name__,
                erro
            )


        # ====================================================
        # MANTÉM 300 SEGUNDOS ENTRE CICLOS
        # ====================================================

        tempo_decorrido = (
            time.time()
            - inicio_ciclo
        )

        espera = max(
            1,
            int(
                INTERVALO_RADAR
                - tempo_decorrido
            )
        )


        print()

        print(
            f"⏳ Nova consulta em "
            f"{espera} segundos..."
        )


        time.sleep(
            espera
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    threading.Thread(
        target=iniciar_servidor_saude,
        daemon=True
    ).start()

    loop_consulta()
