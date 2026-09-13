# ============================================================
# MAIN - IPM RADAR V5.2
# PRÉ-LIVE + CONTROLE DE COTA DA API
# ============================================================

import os
import time
import threading

from datetime import datetime, date

from http.server import BaseHTTPRequestHandler, HTTPServer

from config import (
    horario_ativo,
    FUSO_HORARIO,
    HORA_INICIO,
    HORA_FIM,
)

from scanner_pre_live import escanear_pre_live

# LIVE permanece preparado para compatibilidade.
# Atualmente o odds_api.py V5.2 está com LIVE desativado.
from monitor_live import processar_live

from odds_api import REQUISICOES_REALIZADAS


# ============================================================
# CONFIGURAÇÃO
# ============================================================

LIMITE_DIARIO_API = int(
    os.getenv(
        "LIMITE_DIARIO_API",
        "500",
    )
)

INTERVALO_MINIMO = int(
    os.getenv(
        "INTERVALO_MINIMO_RADAR",
        "60",
    )
)

INTERVALO_MAXIMO = int(
    os.getenv(
        "INTERVALO_MAXIMO_RADAR",
        "900",
    )
)


# ============================================================
# ESTADO
# ============================================================

JOGOS_MONITORADOS = {}

DATA_CONTROLE = None
REQUISICOES_INICIO_DIA = 0


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
            b"IPM RADAR V5.2 OK"
        )

    def log_message(self, *args):
        return


def iniciar_servidor():

    porta = int(
        os.getenv(
            "PORT",
            "10000"
        )
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
# CONTROLE DIÁRIO DA API
# ============================================================

def inicializar_controle_diario():

    global DATA_CONTROLE
    global REQUISICOES_INICIO_DIA

    hoje = datetime.now(
        FUSO_HORARIO
    ).date()

    if DATA_CONTROLE != hoje:

        DATA_CONTROLE = hoje

        REQUISICOES_INICIO_DIA = (
            REQUISICOES_REALIZADAS
        )

        print()
        print(
            "🧮 CONTROLE API | NOVO DIA"
        )

        print(
            f"📅 Data: {hoje}"
        )

        print(
            f"📡 Limite diário: "
            f"{LIMITE_DIARIO_API}"
        )


def requisicoes_do_dia():

    inicializar_controle_diario()

    return max(
        0,
        REQUISICOES_REALIZADAS
        - REQUISICOES_INICIO_DIA
    )


def requisicoes_restantes():

    return max(
        0,
        LIMITE_DIARIO_API
        - requisicoes_do_dia()
    )


# ============================================================
# PRÓXIMO CICLO
# ============================================================

def calcular_intervalo():

    restantes = requisicoes_restantes()

    if restantes <= 0:

        return INTERVALO_MAXIMO

    agora = datetime.now(
        FUSO_HORARIO
    )

    hoje = agora.date()

    # --------------------------------------------------------
    # Fim da janela ativa
    # --------------------------------------------------------

    if HORA_FIM == HORA_INICIO:

        fim = datetime.combine(
            hoje,
            HORA_INICIO,
            tzinfo=FUSO_HORARIO
        )

        # Se HORA_FIM == 00:00,
        # considera meia-noite do dia seguinte.
        if fim <= agora:

            fim = fim.replace(
                day=fim.day
            )

            fim = (
                fim
                + __import__("datetime")
                .timedelta(days=1)
            )

    elif HORA_INICIO < HORA_FIM:

        fim = datetime.combine(
            hoje,
            HORA_FIM,
            tzinfo=FUSO_HORARIO
        )

        if fim <= agora:

            return INTERVALO_MINIMO

    else:

        # Janela atravessando meia-noite
        if agora.time() >= HORA_INICIO:

            fim = datetime.combine(
                hoje,
                HORA_FIM,
                tzinfo=FUSO_HORARIO
            )

            fim += __import__("datetime").timedelta(
                days=1
            )

        else:

            fim = datetime.combine(
                hoje,
                HORA_FIM,
                tzinfo=FUSO_HORARIO
            )

    segundos_restantes = max(
        60,
        (
            fim - agora
        ).total_seconds()
    )

    # --------------------------------------------------------
    # Distribui a cota restante.
    #
    # Reservamos pelo menos 1 requisição
    # para cada ciclo.
    # --------------------------------------------------------

    ciclos_estimados = max(
        1,
        restantes
    )

    intervalo = (
        segundos_restantes
        / ciclos_estimados
    )

    intervalo = max(
        INTERVALO_MINIMO,
        intervalo
    )

    intervalo = min(
        INTERVALO_MAXIMO,
        intervalo
    )

    return int(
        intervalo
    )


# ============================================================
# PRÉ-LIVE
# ============================================================

def executar_pre_live():

    restantes_antes = (
        requisicoes_restantes()
    )

    if restantes_antes <= 0:

        print(
            "⛔ API | COTA DIÁRIA ATINGIDA"
        )

        return

    inicio_api = (
        REQUISICOES_REALIZADAS
    )

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

    usadas = (
        REQUISICOES_REALIZADAS
        - inicio_api
    )

    restantes_depois = (
        requisicoes_restantes()
    )

    print(
        f"📡 API | USADAS NO CICLO={usadas} | "
        f"USADAS HOJE={requisicoes_do_dia()} | "
        f"RESTANTES={restantes_depois}"
    )

    if not resultados:

        print(
            "PRÉ-LIVE | Nenhum jogo aprovado."
        )

        return

    for jogo in resultados:

        event_id = jogo.get(
            "event_id"
        )

        if event_id is None:
            continue

        event_id = str(
            event_id
        )

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
    print("IPM RADAR V5.2 INICIADO")
    print("=" * 60)

    inicializar_controle_diario()

    while True:

        inicio = time.time()

        try:

            inicializar_controle_diario()

            restantes = (
                requisicoes_restantes()
            )

            if not horario_ativo():

                print(
                    "RADAR | Período de pausa."
                )

            elif restantes <= 0:

                print(
                    "⛔ RADAR | "
                    "500 REQUISIÇÕES DIÁRIAS ATINGIDAS."
                )

            else:

                print()
                print(
                    "============================================================"
                )

                print(
                    f"📡 API | "
                    f"USADAS={requisicoes_do_dia()} | "
                    f"RESTANTES={restantes}"
                )

                executar_pre_live()

                # ------------------------------------------------
                # LIVE
                # ------------------------------------------------
                #
                # O odds_api V5.2 atualmente mantém LIVE
                # desativado. Deixamos o bloco preparado.
                #
                # ------------------------------------------------

                if (
                    requisicoes_restantes()
                    > 0
                ):

                    executar_live()

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

        espera = calcular_intervalo()

        espera = max(
            1,
            espera - duracao
        )

        print(
            f"CICLO | {duracao:.1f}s | "
            f"API HOJE={requisicoes_do_dia()} | "
            f"RESTANTES={requisicoes_restantes()} | "
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
