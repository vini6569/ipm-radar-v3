# ============================================================
# IPM RADAR - LIVE
# SOMENTE MONITORAMENTO LIVE
# ============================================================

import os
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from config import horario_ativo

from scanner_pre_live import escanear_pre_live

from odds_api import (
    buscar_jogos_ao_vivo_por_ids,
    buscar_odds_multiplos,
    extrair_mercados,
)

from telegram import enviar_mensagem

from motor_ipm import (
    analisar_ipm_com_memoria,
    avaliar_pre_entrada,
    jogo_finalizado,
    formatar_radar,
)


INTERVALO = int(
    os.getenv("INTERVALO_LIVE", "60")
)


JOGOS = {}

ULTIMO_SINAL = {}


# ============================================================
# HEALTH
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
            b"IPM RADAR LIVE OK"
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
        f"LIVE | HEALTH ATIVO | PORTA={porta}"
    )


# ============================================================
# CONVERSÃO
# ============================================================

def numero(valor, padrao=0.0):

    try:

        if valor in (None, ""):
            return padrao

        return float(valor)

    except (TypeError, ValueError):

        return padrao


# ============================================================
# REGISTRAR JOGOS
# ============================================================

def registrar():

    try:

        resultados = escanear_pre_live() or []

    except Exception as erro:

        print(
            "LIVE | ERRO BUSCANDO RADAR:",
            erro
        )

        return

    for jogo in resultados:

        event_id = jogo.get("event_id")

        if event_id is None:
            continue

        event_id = str(event_id)

        JOGOS.setdefault(

            event_id,

            {

                "event_id": event_id,

                "casa": jogo.get(
                    "casa",
                    "Casa"
                ),

                "fora": jogo.get(
                    "fora",
                    "Fora"
                ),

                "odd_casa": numero(
                    jogo.get("odd_casa")
                ),

                "odd_empate": numero(
                    jogo.get("odd_empate")
                ),

                "odd_visitante": numero(
                    jogo.get("odd_visitante")
                ),

                "odd_pre_live": numero(
                    jogo.get(
                        "odd_pre_live",
                        jogo.get("q")
                    )
                ),

            }

        )


# ============================================================
# MOTOR
# ============================================================

def processar(

    event_id,
    monitorado,
    jogo,
    mercados

):

    if not jogo:
        return

    odd_x = numero(
        mercados.get(
            "odd_empate",
            mercados.get(
                "odd_draw",
                0
            )
        )
    )

    if odd_x <= 0:

        print(
            f"LIVE | ODD X INVALIDA | ID={event_id}"
        )

        return

    minuto = int(
        numero(
            mercados.get(
                "minuto",
                jogo.get(
                    "minute",
                    jogo.get(
                        "elapsed",
                        0
                    )
                )
            )
        )
    )

    gols = int(
        numero(
            mercados.get(
                "gols",
                jogo.get(
                    "goals",
                    0
                )
            )
        )
    )

    escanteios = int(
        numero(
            mercados.get(
                "escanteios",
                jogo.get(
                    "corners",
                    0
                )
            )
        )
    )

    cartoes = int(
        numero(
            mercados.get(
                "cartoes",
                jogo.get(
                    "cards",
                    0
                )
            )
        )
    )

    finalizacoes = int(
        numero(
            mercados.get(
                "finalizacoes",
                jogo.get(
                    "shots",
                    0
                )
            )
        )
    )

    ataques = int(
        numero(
            mercados.get(
                "ataques_perigosos",
                jogo.get(
                    "dangerous_attacks",
                    0
                )
            )
        )
    )

    resultado = analisar_ipm_com_memoria(

        chave_jogo=event_id,

        odd_atual=odd_x,

        minuto=minuto,

        gols=gols,

        escanteios=escanteios,

        cartoes=cartoes,

        finalizacoes=finalizacoes,

        ataques_perigosos=ataques,

        odd_pre_live=numero(
            monitorado.get(
                "odd_pre_live"
            )
        ),

        odd_casa=numero(
            mercados.get(
                "odd_casa",
                mercados.get("home")
            )
        ),

        odd_visitante=numero(
            mercados.get(
                "odd_visitante",
                mercados.get("away")
            )
        ),

        odd_casa_pre_live=numero(
            monitorado.get(
                "odd_casa"
            )
        ),

        odd_visitante_pre_live=numero(
            monitorado.get(
                "odd_visitante"
            )
        ),

    )

    var10 = numero(
        resultado.get("var_10min")
    )

    sinal = resultado.get(
        "sinal_pre_entrada",
        "NEUTRO"
    )

    print(

        f"LIVE | "
        f"{monitorado['casa']} x "
        f"{monitorado['fora']} | "

        f"{minuto}' | "

        f"X={odd_x:.2f} | "

        f"VAR10={var10:+.2f}% | "

        f"SINAL={sinal}"

    )

    # --------------------------------------------------------
    # ALERTA
    # --------------------------------------------------------

    if avaliar_pre_entrada(resultado):

        ultimo = ULTIMO_SINAL.get(
            event_id
        )

        if sinal != ultimo:

            mensagem = formatar_radar(
                {
                    "event_id": event_id,
                    "home": monitorado["casa"],
                    "away": monitorado["fora"],
                    "odd_empate": odd_x,
                    "odd_pre_live": monitorado[
                        "odd_pre_live"
                    ],
                },

                resultado,

                mercados
            )

            if mensagem:

                if enviar_mensagem(
                    mensagem
                ):

                    ULTIMO_SINAL[
                        event_id
                    ] = sinal

                    print(
                        f"🚨 LIVE | ALERTA ENVIADO | "
                        f"{event_id}"
                    )

    else:

        ULTIMO_SINAL[
            event_id
        ] = "NEUTRO"


# ============================================================
# CICLO LIVE
# ============================================================

def ciclo():

    registrar()

    ids = list(
        JOGOS.keys()
    )

    if not ids:

        print(
            "LIVE | Nenhum jogo monitorado."
        )

        return

    try:

        jogos_live = (
            buscar_jogos_ao_vivo_por_ids(
                ids
            )
            or []
        )

    except Exception as erro:

        print(
            "LIVE | ERRO API LIVE:",
            erro
        )

        return

    mapa = {

        str(j.get("id")): j

        for j in jogos_live

        if (
            isinstance(j, dict)
            and j.get("id") is not None
        )

    }

    # --------------------------------------------------------
    # FINALIZADOS
    # --------------------------------------------------------

    for event_id, jogo in list(mapa.items()):

        if jogo_finalizado(jogo):

            JOGOS.pop(
                event_id,
                None
            )

            ULTIMO_SINAL.pop(
                event_id,
                None
            )

            print(
                f"LIVE | FINALIZADO | {event_id}"
            )

    # --------------------------------------------------------
    # ODDS
    # --------------------------------------------------------

    eventos = [

        mapa[event_id]

        for event_id in JOGOS

        if event_id in mapa

    ]

    if not eventos:

        print(
            "LIVE | Nenhum jogo retornado."
        )

        return

    try:

        odds = (
            buscar_odds_multiplos(
                eventos
            )
            or []
        )

    except Exception as erro:

        print(
            "LIVE | ERRO ODDS:",
            erro
        )

        return

    # --------------------------------------------------------
    # PROCESSAR
    # --------------------------------------------------------

    leituras = 0
    sinais = 0

    for event_id, monitorado in list(
        JOGOS.items()
    ):

        jogo = mapa.get(
            event_id
        )

        if jogo is None:
            continue

        try:

            mercados = (
                extrair_mercados(
                    jogo,
                    odds
                )
                or {}
            )

            processar(
                event_id,
                monitorado,
                jogo,
                mercados
            )

            leituras += 1

        except Exception as erro:

            print(
                f"LIVE | ERRO {event_id}:",
                erro
            )

    print(

        f"LIVE | CICLO OK | "
        f"LEITURAS={leituras} | "
        f"MONITORADOS={len(JOGOS)}"

    )


# ============================================================
# LOOP
# ============================================================

def main():

    print(
        "IPM RADAR - LIVE INICIADO"
    )

    print(
        f"INTERVALO: {INTERVALO}s"
    )

    print(
        "REGRA: +/-20% EM 10 MINUTOS"
    )

    while True:

        inicio = time.time()

        try:

            if horario_ativo():
                ciclo()
            else:
                print(
                    "LIVE | Periodo de pausa."
                )

        except Exception as erro:

            print(
                "LIVE | ERRO LOOP:",
                type(erro).__name__,
                erro
            )

        espera = max(
            1,
            INTERVALO - (
                time.time() - inicio
            )
        )

        time.sleep(espera)


if __name__ == "__main__":

    iniciar_servidor()

    main()
