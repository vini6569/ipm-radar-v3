# ============================================================
# MAIN - IPM RADAR V5.0
# 3 ODDS + TRAJETÓRIA + IPM + REFERÊNCIA 45'
# ============================================================

import json
import os
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from config import (
    NOME_BOT,
    VERSAO,
    INTERVALO_RADAR,
    MAX_JOGOS_RADAR,
    IPM_MINIMO_OBSERVACAO,
    IPM_MINIMO_FORTE,
    IPM_MINIMO_MUITO_FORTE,
    VARIACAO_MINIMA_ODD,
    MINUTO_MINIMO_ENTRADA,
    MINUTO_MAXIMO_ENTRADA,
    IPM_MINIMO_ENTRADA,
    MAX_ENTRADAS_POR_JOGO,
    horario_ativo,
    horario_atual,
)

from odds_api import (
    buscar_jogos_ao_vivo,
    buscar_jogos_pre_live,
    buscar_odds_multiplos,
    extrair_mercados,
)

from motor_ipm import (
    analisar_ipm_com_memoria,
    formatar_radar,
    jogo_finalizado,
    resultado_empate,
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

PORTA_SAUDE = int(
    os.environ.get("PORT", "10000")
)

ARQUIVO_CONTROLE = Path(
    os.getenv("ARQUIVO_CONTROLE", "ipm_controle.json")
)

TELEGRAM_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN", ""
).strip()

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID", ""
).strip()


# ============================================================
# MEMÓRIA
# ============================================================

_controle_jogos = {}
_lock = threading.Lock()


# ============================================================
# TELEGRAM
# ============================================================

def enviar_telegram(texto):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ℹ️ Telegram não configurado.")
        return False

    try:
        url = (
            f"https://api.telegram.org/"
            f"bot{TELEGRAM_TOKEN}/sendMessage"
        )

        dados = urllib.parse.urlencode({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": texto,
        }).encode("utf-8")

        requisicao = urllib.request.Request(
            url,
            data=dados,
            method="POST",
        )

        with urllib.request.urlopen(
            requisicao,
            timeout=15
        ) as resposta:

            return 200 <= resposta.status < 300

    except Exception as erro:
        print(
            "❌ ERRO TELEGRAM:",
            type(erro).__name__,
            erro,
        )
        return False


# ============================================================
# CONTROLE
# ============================================================

def salvar_controle():
    try:
        temporario = ARQUIVO_CONTROLE.with_suffix(".tmp")

        with temporario.open(
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                _controle_jogos,
                arquivo,
                ensure_ascii=False,
                indent=2,
            )

        temporario.replace(
            ARQUIVO_CONTROLE
        )

    except Exception as erro:
        print(
            "❌ ERRO AO SALVAR CONTROLE:",
            type(erro).__name__,
            erro,
        )


def carregar_controle():
    global _controle_jogos

    try:
        if not ARQUIVO_CONTROLE.exists():
            return

        with ARQUIVO_CONTROLE.open(
            "r",
            encoding="utf-8"
        ) as arquivo:

            dados = json.load(arquivo)

        if isinstance(dados, dict):
            _controle_jogos = dados

            print(
                "💾 Controle carregado:",
                len(_controle_jogos),
                "jogos",
            )

    except Exception as erro:
        print(
            "⚠️ ERRO AO CARREGAR CONTROLE:",
            type(erro).__name__,
            erro,
        )


def obter_controle(event_id):

    chave = str(event_id)

    with _lock:

        return _controle_jogos.setdefault(
            chave,
            {
                "odd_pre_live_home": None,
                "odd_pre_live_draw": None,
                "odd_pre_live_away": None,

                "ultima_odd_home": None,
                "ultima_odd_draw": None,
                "ultima_odd_away": None,

                "trajetoria": [],

                "entradas": [],
                "entrada_ativa": False,

                "alerta_45_enviado": False,
                "alerta_ipm_enviado": False,

                "finalizado": False,
                "resultado": None,
            },
        )


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classificar_sinal(ipm):

    try:
        valor = float(ipm)
    except (TypeError, ValueError):
        valor = 0.0

    if valor >= IPM_MINIMO_MUITO_FORTE:
        return "SINAL MUITO FORTE"

    if valor >= IPM_MINIMO_FORTE:
        return "SINAL FORTE"

    if valor >= IPM_MINIMO_OBSERVACAO:
        return "OBSERVAR"

    return "SEM SINAL"


# ============================================================
# PRÉ-LIVE
# ============================================================

def capturar_referencia_pre_live():

    jogos = buscar_jogos_pre_live() or []

    if not jogos:
        return

    odds = buscar_odds_multiplos(jogos) or []

    for jogo in jogos:

        if (
            not isinstance(jogo, dict)
            or jogo.get("id") is None
        ):
            continue

        mercados = extrair_mercados(
            jogo,
            odds
        ) or {}

        odd_home = float(
            mercados.get("odd_home", 0.0) or 0.0
        )

        odd_draw = float(
            mercados.get("odd_draw", 0.0) or 0.0
        )

        odd_away = float(
            mercados.get("odd_away", 0.0) or 0.0
        )

        if not (
            odd_home > 0
            and odd_draw > 0
            and odd_away > 0
        ):
            continue

        controle = obter_controle(
            jogo["id"]
        )

        if not controle.get(
            "odd_pre_live_home"
        ):

            controle["odd_pre_live_home"] = odd_home
            controle["odd_pre_live_draw"] = odd_draw
            controle["odd_pre_live_away"] = odd_away

            controle[
                "pre_live_capturada_em"
            ] = horario_atual().isoformat()

            print(
                f"🟣 PRÉ-LIVE | "
                f"{jogo.get('home')} x "
                f"{jogo.get('away')} | "
                f"CASA={odd_home} | "
                f"EMPATE={odd_draw} | "
                f"FORA={odd_away}"
            )

    salvar_controle()


# ============================================================
# TRAJETÓRIA
# ============================================================

def registrar_trajetoria(
    controle,
    minuto,
    odd_home,
    odd_draw,
    odd_away,
    ipm,
):

    ponto = {
        "hora": horario_atual().isoformat(),
        "minuto": int(minuto),
        "odd_home": float(odd_home),
        "odd_draw": float(odd_draw),
        "odd_away": float(odd_away),
        "ipm": float(ipm),
    }

    controle.setdefault(
        "trajetoria",
        []
    )

    controle["trajetoria"].append(
        ponto
    )

    # Mantém somente os pontos mais recentes.
    if len(controle["trajetoria"]) > 100:
        controle["trajetoria"] = (
            controle["trajetoria"][-100:]
        )


# ============================================================
# ALERTA DE IPM
# ============================================================

def verificar_alerta_ipm(
    jogo,
    resultado,
    controle,
):

    ipm = float(
        resultado.get("ipm", 0)
        or 0
    )

    minuto = int(
        resultado.get("minuto", 0)
        or 0
    )

    if (
        minuto < MINUTO_MINIMO_ENTRADA
        or minuto > MINUTO_MAXIMO_ENTRADA
    ):
        return

    if (
        ipm < IPM_MINIMO_ENTRADA
        or controle.get("alerta_ipm_enviado")
    ):
        return

    controle[
        "alerta_ipm_enviado"
    ] = True

    enviar_telegram(
        "🚨 IPM RADAR — ALERTA\n\n"
        f"⚽ {jogo.get('home', 'Casa')} x "
        f"{jogo.get('away', 'Fora')}\n"
        f"⏱️ Minuto: {minuto}'\n"
        f"🎯 IPM: {ipm:.2f}\n"
        f"📌 {classificar_sinal(ipm)}\n\n"
        "📊 Acompanhar trajetória das 3 odds."
    )


# ============================================================
# PROCESSAMENTO
# ============================================================

def processar_jogo(
    jogo,
    mercados,
    resultado,
):

    event_id = jogo.get("id")

    if event_id is None:
        return

    controle = obter_controle(
        event_id
    )

    minuto = int(
        resultado.get("minuto", 0)
        or 0
    )

    ipm = float(
        resultado.get("ipm", 0)
        or 0
    )

    odd_home = float(
        mercados.get("odd_home", 0)
        or 0
    )

    odd_draw = float(
        mercados.get("odd_draw", 0)
        or 0
    )

    odd_away = float(
        mercados.get("odd_away", 0)
        or 0
    )


    # --------------------------------------------------------
    # REGISTRA TRAJETÓRIA
    # --------------------------------------------------------

    if (
        odd_home > 0
        and odd_draw > 0
        and odd_away > 0
    ):

        registrar_trajetoria(
            controle,
            minuto,
            odd_home,
            odd_draw,
            odd_away,
            ipm,
        )


    # --------------------------------------------------------
    # ATUALIZA ÚLTIMA LEITURA
    # --------------------------------------------------------

    controle[
        "ultimo_minuto"
    ] = minuto

    controle[
        "ultima_odd_home"
    ] = odd_home

    controle[
        "ultima_odd_draw"
    ] = odd_draw

    controle[
        "ultima_odd_away"
    ] = odd_away

    controle[
        "ultimo_ipm"
    ] = ipm


    # --------------------------------------------------------
    # ALERTA IPM
    # --------------------------------------------------------

    verificar_alerta_ipm(
        jogo,
        resultado,
        controle,
    )


    # --------------------------------------------------------
    # FINAL DO JOGO
    # --------------------------------------------------------

    if (
        not controle.get("finalizado")
        and jogo_finalizado(jogo)
    ):

        empate = resultado_empate(
            jogo,
            mercados
        )

        if empate is not None:

            controle["finalizado"] = True

            controle["resultado"] = (
                "VERDE"
                if empate
                else "VERMELHO"
            )

            controle[
                "entrada_ativa"
            ] = False

            for entrada in controle[
                "entradas"
            ]:

                entrada["status"] = (
                    controle["resultado"]
                )

            enviar_telegram(
                f"{'🟢' if empate else '🔴'} "
                "RESULTADO FINAL\n\n"
                f"⚽ {jogo.get('home', 'Casa')} x "
                f"{jogo.get('away', 'Fora')}\n"
                f"📌 {'EMPATE' if empate else 'NÃO EMPATE'}\n"
                f"🎯 IPM final: {ipm:.2f}"
            )


    salvar_controle()


# ============================================================
# CONSULTA PRINCIPAL
# ============================================================

def executar_consulta():

    print(
        "\n" + "=" * 72
    )

    print(
        "📡 IPM RADAR V5.0 |",
        horario_atual().strftime(
            "%d/%m/%Y %H:%M:%S"
        ),
    )

    print(
        "=" * 72
    )


    # --------------------------------------------------------
    # PRÉ-LIVE
    # --------------------------------------------------------

    try:

        capturar_referencia_pre_live()

    except Exception as erro:

        print(
            "⚠️ ERRO PRÉ-LIVE:",
            type(erro).__name__,
            erro,
        )


    # --------------------------------------------------------
    # AO VIVO
    # --------------------------------------------------------

    try:

        jogos = (
            buscar_jogos_ao_vivo()
            or []
        )

        if not jogos:

            print(
                "ℹ️ Nenhum jogo ao vivo."
            )

            return

        jogos = jogos[
            :MAX_JOGOS_RADAR
        ]

        odds = (
            buscar_odds_multiplos(jogos)
            or []
        )


        for jogo in jogos:

            try:

                if (
                    not isinstance(jogo, dict)
                    or jogo.get("id") is None
                ):
                    continue

                event_id = jogo["id"]

                mercados = (
                    extrair_mercados(
                        jogo,
                        odds
                    )
                    or {}
                )

                controle = obter_controle(
                    event_id
                )


                # ------------------------------------------------
                # FALLBACK
                # ------------------------------------------------

                if not controle.get(
                    "odd_pre_live_draw"
                ):

                    home = float(
                        mercados.get(
                            "odd_home", 0
                        ) or 0
                    )

                    draw = float(
                        mercados.get(
                            "odd_draw", 0
                        ) or 0
                    )

                    away = float(
                        mercados.get(
                            "odd_away", 0
                        ) or 0
                    )

                    if (
                        home > 0
                        and draw > 0
                        and away > 0
                    ):

                        controle[
                            "odd_pre_live_home"
                        ] = home

                        controle[
                            "odd_pre_live_draw"
                        ] = draw

                        controle[
                            "odd_pre_live_away"
                        ] = away

                        controle[
                            "pre_live_fallback"
                        ] = True

                        print(
                            "⚠️ FALLBACK REFERÊNCIA | "
                            f"{jogo.get('home')} x "
                            f"{jogo.get('away')} | "
                            f"{home} / "
                            f"{draw} / "
                            f"{away}"
                        )


                # ------------------------------------------------
                # MOTOR IPM
                # ------------------------------------------------

                resultado = (
                    analisar_ipm_com_memoria(
                        event_id,
                        mercados.get(
                            "odd_draw",
                            0.0
                        ),
                        mercados.get(
                            "minuto",
                            0
                        ),
                        mercados.get(
                            "gols",
                            0
                        ),
                        0,
                        0,
                        0,
                        odd_pre_live=controle.get(
                            "odd_pre_live_draw"
                        ),
                    )
                )


                # ------------------------------------------------
                # SAÍDA
                # ------------------------------------------------

                print(
                    formatar_radar(
                        jogo,
                        resultado,
                        mercados,
                    )
                )

                print(
                    "📈 3 ODDS:",
                    f"CASA={mercados.get('odd_home', 0)} |",
                    f"EMPATE={mercados.get('odd_draw', 0)} |",
                    f"FORA={mercados.get('odd_away', 0)}"
                )

                print(
                    "🎯 IPM:",
                    f"{float(resultado.get('ipm', 0)):.2f}"
                )

                print(
                    "🚦 SINAL:",
                    classificar_sinal(
                        resultado.get(
                            "ipm", 0
                        )
                    )
                )

                processar_jogo(
                    jogo,
                    mercados,
                    resultado,
                )


            except Exception as erro_jogo:

                print(
                    "❌ ERRO AO ANALISAR JOGO:",
                    type(erro_jogo).__name__,
                    erro_jogo,
                )


    except Exception as erro:

        print(
            "❌ ERRO NO CICLO:",
            type(erro).__name__,
            erro,
        )


# ============================================================
# SERVIDOR DE SAÚDE
# ============================================================

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

        try:

            agora = horario_atual()

            corpo = (
                f"{NOME_BOT} ONLINE | "
                f"Brasil: "
                f"{agora.strftime('%d/%m/%Y %H:%M:%S')} | "
                f"Versão: {VERSAO}"
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

            self.wfile.write(corpo)

        except Exception:

            try:
                self.send_response(500)
                self.end_headers()
            except Exception:
                pass


    def log_message(
        self,
        format,
        *args
    ):
        return


def iniciar_servidor_saude():

    try:

        servidor = HTTPServer(
            ("0.0.0.0", PORTA_SAUDE),
            HealthHandler,
        )

        print(
            "🌐 Servidor de saúde iniciado na porta",
            PORTA_SAUDE,
        )

        servidor.serve_forever()

    except Exception as erro:

        print(
            "❌ ERRO SERVIDOR DE SAÚDE:",
            type(erro).__name__,
            erro,
        )


# ============================================================
# LOOP
# ============================================================

def loop_consulta():

    carregar_controle()

    print(
        "=" * 72
    )

    print(
        f"🚀 {NOME_BOT} | VERSÃO {VERSAO}"
    )

    print(
        "Protocolo:"
    )

    print(
        "3 ODDS → TRAJETÓRIA → IPM → "
        "REFERÊNCIA 45' → RESULTADO"
    )

    print(
        f"Intervalo: {INTERVALO_RADAR} segundos"
    )

    print(
        f"Máximo de jogos: {MAX_JOGOS_RADAR}"
    )

    print(
        "📊 Foco: CASA / EMPATE / VISITANTE"
    )

    print(
        "📈 Trajetória das odds ativada."
    )

    print(
        "⏱️ Acompanhamento até 45 minutos."
    )

    print(
        "📨 Telegram ativo para alertas."
    )

    print(
        "=" * 72
    )


    while True:

        inicio = time.time()

        try:

            if horario_ativo():

                executar_consulta()

            else:

                print(
                    "⏸️ Radar em período de pausa."
                )

        except Exception as erro:

            print(
                "❌ ERRO NO LOOP:",
       
