# ============================================================
# MAIN - IPM RADAR V4
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

PORTA_SAUDE = int(
    os.environ.get(
        "PORT",
        "10000"
    )
)

class HealthHandler(
    BaseHTTPRequestHandler
):
    def do_GET(self):
        agora = horario_atual()

        corpo = (
            f"{NOME_BOT} ONLINE | "
            f"Brasil: "
            f"{agora.strftime('%d/%m/%Y %H:%M:%S')}"
        ).encode("utf-8")

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(corpo))
        )

        self.end_headers()

        self.wfile.write(
            corpo
        )

    def log_message(
        self,
        format,
        *args
    ):
        return

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
            "Servidor de saúde iniciado "
            f"na porta {PORTA_SAUDE}"
        )

        servidor.serve_forever()

    except Exception as erro:
        print(
            "Erro no servidor de saúde:",
            erro
        )

def classificar_sinal(ipm):
    if ipm >= IPM_MINIMO_MUITO_FORTE:
        return "SINAL MUITO FORTE"

    if ipm >= IPM_MINIMO_FORTE:
        return "SINAL FORTE"

    if ipm >= IPM_MINIMO_OBSERVACAO:
        return "OBSERVAR"

    return "SEM SINAL"

def _mostrar_mercados(mercados):
    # Proteção explícita contra o erro que apareceu no Render:
    # KeyError: 'todos'
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

    print(
        "📦 TODOS OS MERCADOS RECEBIDOS:",
        len(todos)
    )

    if ht:
        print(
            "⏱️ MERCADOS HT:"
        )

        for mercado in ht:
            print(
                "   ",
                mercado.get("name"),
                ":",
                mercado.get("odds")
            )

    if corners:
        print(
            "🚩 MERCADOS ESCANTEIOS:"
        )

        for mercado in corners:
            print(
                "   ",
                mercado.get("name"),
                ":",
                mercado.get("odds")
            )

    if cards:
        print(
            "🟨 MERCADOS CARTÕES:"
        )

        for mercado in cards:
            print(
                "   ",
                mercado.get("name"),
                ":",
                mercado.get("odds")
            )

def executar_consulta():
    agora = horario_atual()

    print()
    print("=" * 70)
    print(
        "📡 IPM RADAR V4 |",
        agora.strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    )
    print("=" * 70)

    try:
        jogos = (
            buscar_jogos_ao_vivo()
            or []
        )

        print(
            "JOGOS AO VIVO ENCONTRADOS:",
            len(jogos)
        )

        if not jogos:
            return

        jogos = jogos[
            :MAX_JOGOS_RADAR
        ]

        odds = (
            buscar_odds_multiplos(
                jogos
            )
            or []
        )

        print(
            "EVENTOS COM ODDS RECEBIDOS:",
            len(odds)
        )

        for jogo in jogos:
            try:
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

                odd_atual = mercados.get(
                    "odd_atual",
                    0.0
                )

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

                print(
                    formatar_radar(
                        jogo,
                        resultado,
                        mercados
                    )
                )

                print(
                    "SINAL:",
                    classificar_sinal(
                        resultado.get(
                            "ipm",
                            0
                        )
                    ),
                    "| FILTRO ODD:",
                    abs(
                        resultado.get(
                            "variacao_odd",
                            0
                        )
                    ) >= VARIACAO_MINIMA_ODD,
                )

                _mostrar_mercados(
                    mercados
                )

            except Exception as erro_jogo:
                print(
                    "❌ ERRO AO ANALISAR JOGO:",
                    type(erro_jogo).__name__,
                    erro_jogo
                )

    except Exception as erro:
        print(
            "❌ ERRO NO CICLO:",
            type(erro).__name__,
            erro
        )

def loop_consulta():
    print("=" * 70)
    print(
        f"🚀 {NOME_BOT} | "
        f"VERSÃO {VERSAO}"
    )
    print(
        "Janela: 06:00 até 00:00 | "
        f"Intervalo: {INTERVALO_RADAR}s"
    )
    print(
        "Fluxo: jogos → odds → "
        "TODOS/HT → IPM"
    )
    print(
        "Proteção: acesso seguro "
        "aos mercados com .get()"
    )
    print("=" * 70)

    while True:
        try:
            agora = horario_atual()

            print(
                "\n🕒 Horário Brasil:",
                agora.strftime(
                    "%d/%m/%Y %H:%M:%S"
                )
            )

            if horario_ativo():
                executar_consulta()
            else:
                print(
                    "⏸️ Radar em período de pausa."
                )

        except Exception as erro:
            print(
                "❌ ERRO NO LOOP:",
                type(erro).__name__,
                erro
            )

        print(
            f"⏳ Nova consulta em "
            f"{INTERVALO_RADAR} segundos..."
        )

        time.sleep(
            INTERVALO_RADAR
        )

if __name__ == "__main__":
    threading.Thread(
        target=iniciar_servidor_saude,
        daemon=True
    ).start()

    loop_consulta()
    
