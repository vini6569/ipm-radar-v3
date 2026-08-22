import time
import os
import threading
from datetime import datetime

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
# CONFIGURAÇÃO ECONÔMICA
# ============================================================

INTERVALO_CONSULTA = 300  # 5 minutos

HORA_INICIO = 6           # 06:00
HORA_FIM = 0              # 00:00


# ============================================================
# MEMÓRIA DAS ODDS
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

    print(
        f"Servidor de saúde iniciado na porta {porta}"
    )

    servidor.serve_forever()


# ============================================================
# VERIFICAR HORÁRIO DE FUNCIONAMENTO
# ============================================================

def radar_ativo():

    hora = datetime.now().hour

    # Das 06:00 até 23:59
    if HORA_INICIO <= hora < 24:
        return True

    return False


# ============================================================
# AGUARDAR HORÁRIO DE FUNCIONAMENTO
# ============================================================

def aguardar_inicio():

    while not radar_ativo():

        agora = datetime.now()

        print()
        print("=" * 60)
        print("🌙 RADAR EM PAUSA")
        print(
            "Horário atual:",
            agora.strftime("%H:%M:%S")
        )
        print("Funcionamento: 06:00 às 00:00")
        print("Nenhuma requisição será feita.")
        print("=" * 60)

        # Verifica novamente a cada 60 segundos
        time.sleep(60)


# ============================================================
# PROCESSAR MOVIMENTAÇÃO
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
    # PRIMEIRA ODD
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

    odd_anterior = memoria_odds[chave]

    # ========================================================
    # ATUALIZAR MEMÓRIA
    # ========================================================

    memoria_odds[chave] = odd_atual

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
    # MOSTRAR MOVIMENTO
    # ========================================================

    if abs(variacao) > 0:

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

    print()
    print("TOTAL GOALS")

    gols = jogo.get(
        "gols",
        []
    )

    if gols:

        for odd in gols:

            print(
                f"  Linha {odd.get('linha')} | "
                f"Over: {odd.get('over')} | "
                f"Under: {odd.get('under')}"
            )

    else:

        print(
            "  Sem odds de Total Goals."
        )

    print()
    print("ASIAN HANDICAP")

    handicap = jogo.get(
        "handicap",
        []
    )

    if handicap:

        for odd in handicap:

            print(
                f"  Linha {odd.get('linha')} | "
                f"Casa: {odd.get('home')} | "
                f"Fora: {odd.get('away')}"
            )

    else:

        print(
            "  Sem odds de Asian Handicap."
        )

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
# ANALISAR MOVIMENTAÇÃO
# ============================================================

def analisar_movimentacao(jogo):

    evento_id = jogo.get("id")

    if not evento_id:
        return

    print()
    print("MOVIMENTAÇÃO DE ODDS")

    # ========================================================
    # TOTAL GOALS
    # ========================================================

    for odd in jogo.get(
        "gols",
        []
    ):

        linha = odd.get("linha")

        processar_movimentacao(
            evento_id,
            "OVER",
            linha,
            odd.get("over")
        )

        processar_movimentacao(
            evento_id,
            "UNDER",
            linha,
            odd.get("under")
        )

    # ========================================================
    # ASIAN HANDICAP
    # ========================================================

    for odd in jogo.get(
        "handicap",
        []
    ):

        linha = odd.get("linha")

        processar_movimentacao(
            evento_id,
            "HANDICAP_HOME",
            linha,
            odd.get("home")
        )

        processar_movimentacao(
            evento_id,
            "HANDICAP_AWAY",
            linha,
            odd.get("away")
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

    print("IPM-RADAR-V3 iniciado.")
    print(
        "Histórico registrado:",
        quantidade_jogos()
    )

    print()
    print("CONFIGURAÇÃO ECONÔMICA")
    print("Intervalo:", INTERVALO_CONSULTA, "segundos")
    print("Funcionamento: 06:00 às 00:00")
    print("Pausa: 00:00 às 06:00")
    print()

    while True:

        try:

            # =================================================
            # VERIFICAR HORÁRIO
            # =================================================

            aguardar_inicio()

            agora = datetime.now()

            print()
            print("=" * 60)
            print(
                "CONSULTA IPM",
                agora.strftime("%d/%m/%Y %H:%M:%S")
            )
            print("=" * 60)

            # =================================================
            # 1. JOGOS AO VIVO
            # =================================================

            jogos = buscar_jogos_ao_vivo()

            if not isinstance(
                jogos,
                list
            ):

                jogos = []

            print(
                "Jogos ao vivo encontrados:",
                len(jogos)
            )

            # =================================================
            # 2. ODDS
            # =================================================

            odds_eventos = []

            if jogos:

                odds_eventos = (
                    buscar_odds_multiplos(
                        jogos
                    )
                )

            if not isinstance(
                odds_eventos,
                list
            ):

                odds_eventos = []

            print(
                "Eventos com odds recebidos:",
                len(odds_eventos)
            )

            # =================================================
            # 3. ORGANIZAR POR ID
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
            # 4. PROCESSAR JOGOS
            # =================================================

            for jogo in jogos:

                if not isinstance(
                    jogo,
                    dict
                ):
                    continue

                print("-" * 60)

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

                jogo_id = jogo.get("id")

                odds_evento = odds_por_id.get(
                    str(jogo_id)
                )

                if odds_evento:

                    mercados = (
                        extrair_mercados(
                            odds_evento
                        )
                    )

                    if not isinstance(
                        mercados,
                        dict
                    ):

                        mercados = {}

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

                mostrar_odds(jogo)

                analisar_movimentacao(jogo)

            # =================================================
            # DIAGNÓSTICO
            # =================================================

            print()
            print("=" * 60)
            print("DIAGNÓSTICO IPM")
            print("=" * 60)

            print(
                "Jogos nesta consulta:",
                len(jogos)
            )

            print(
                "Eventos com odds:",
                len(odds_eventos)
            )

            print(
                "Odds na memória:",
                len(memoria_odds)
            )

            print("=" * 60)

            # =================================================
            # ESPERAR 5 MINUTOS
            # =================================================

            print()
            print(
                "Próxima consulta em 5 minutos..."
            )

            time.sleep(
                INTERVALO_CONSULTA
            )

        except Exception as erro:

            print()
            print("=" * 60)
            print("ERRO NO RADAR")
            print("=" * 60)

            print(
                type(erro).__name__
            )

            print(
                erro
            )

            print("=" * 60)

            print(
                "Tentando novamente em 60 segundos..."
            )

            time.sleep(60)


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    threading.Thread(
        target=iniciar_servidor,
        daemon=True
    ).start()

    iniciar()
