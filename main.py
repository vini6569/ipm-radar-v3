# ============================================================
# MAIN - IPM RADAR V4.7
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
    avaliar_entrada,
    jogo_finalizado,
    resultado_empate,
)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

PORTA_SAUDE = int(
    os.environ.get("PORT", "10000")
)

ARQUIVO_CONTROLE = Path(
    os.getenv(
        "ARQUIVO_CONTROLE",
        "ipm_controle.json",
    )
)

TELEGRAM_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "",
).strip()

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID",
    "",
).strip()

IPM_MINIMO_ENTRADA = float(
    os.getenv(
        "IPM_MINIMO_ENTRADA",
        "40",
    )
)

MINUTO_MINIMO_ENTRADA = int(
    os.getenv(
        "MINUTO_MINIMO_ENTRADA",
        "1",
    )
)

MINUTO_MAXIMO_ENTRADA = int(
    os.getenv(
        "MINUTO_MAXIMO_ENTRADA",
        "5",
    )
)

MAX_ENTRADAS_POR_JOGO = int(
    os.getenv(
        "MAX_ENTRADAS_POR_JOGO",
        "1",
    )
)


# ============================================================
# MEMÓRIA DOS JOGOS
# ============================================================

_controle_jogos = {}

_lock = threading.Lock()


# ============================================================
# TELEGRAM
# ============================================================

def enviar_telegram(texto):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(
            "ℹ️ Telegram não configurado; "
            "mensagem ficou apenas no log."
        )
        return False

    try:
        url = (
            "https://api.telegram.org/"
            f"bot{TELEGRAM_TOKEN}/sendMessage"
        )

        dados = urllib.parse.urlencode(
            {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": texto,
            }
        ).encode("utf-8")

        requisicao = urllib.request.Request(
            url,
            data=dados,
            method="POST",
        )

        with urllib.request.urlopen(
            requisicao,
            timeout=15,
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
# ARQUIVO DE CONTROLE
# ============================================================

def salvar_controle():
    try:
        temporario = ARQUIVO_CONTROLE.with_suffix(
            ".tmp"
        )

        with temporario.open(
            "w",
            encoding="utf-8",
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
            print(
                "ℹ️ Arquivo de controle ainda não existe."
            )
            return

        with ARQUIVO_CONTROLE.open(
            "r",
            encoding="utf-8",
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
                "odd_pre_live": None,
                "pre_live_capturada_em": None,
                "pre_live_fallback": False,

                "entradas": [],
                "entrada_ativa": False,
                "padrao_mantido": False,

                "finalizado": False,
                "resultado": None,

                # ============================================
                # TRAJETÓRIA ATÉ 45'
                # ============================================

                "trajetoria": [],

                "ultimo_minuto": 0,
                "ultima_odd": None,
                "ultimo_ipm": 0.0,

                "ultima_variacao_ciclo": 0.0,
                "ultima_variacao_pre_live": 0.0,

                "acompanhamento_45": False,
                "ipm_45": None,
                "odd_45": None,
                "variacao_pre_live_45": None,
                "variacao_ciclo_45": None,
            },
        )


# ============================================================
# CLASSIFICAÇÃO DO SINAL
# ============================================================

def classificar_sinal(ipm):
    try:
        valor = float(ipm)
    except (
        TypeError,
        ValueError,
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
# SERVIDOR DE SAÚDE
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

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
                "text/plain; charset=utf-8",
            )

            self.send_header(
                "Content-Length",
                str(len(corpo)),
            )

            self.end_headers()

            self.wfile.write(corpo)

        except Exception:

            try:
                self.send_response(500)
                self.end_headers()
            except Exception:
                pass

    def log_message(self, formato, *args):
        return


def iniciar_servidor_saude():
    try:

        servidor = HTTPServer(
            ("0.0.0.0", PORTA_SAUDE),
            HealthHandler,
        )

        print(
            "🌐 Servidor de saúde iniciado "
            "na porta",
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
# CAPTURA DA REFERÊNCIA PRÉ-LIVE
# ============================================================

def capturar_referencia_pre_live():

    """
    Captura e guarda a odd de empate antes
    do jogo começar.
    """

    jogos = (
        buscar_jogos_pre_live()
        or []
    )

    if not jogos:
        print(
            "ℹ️ Nenhum jogo pré-live "
            "dentro da janela."
        )
        return

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

            mercados = (
                extrair_mercados(
                    jogo,
                    odds,
                )
                or {}
            )

            odd_draw = float(
                mercados.get(
                    "odd_draw",
                    0.0,
                )
                or 0.0
            )

            if odd_draw <= 0:
                continue

            controle = obter_controle(
                jogo["id"]
            )

            if not controle.get(
                "odd_pre_live"
            ):

                controle[
                    "odd_pre_live"
                ] = odd_draw

                controle[
                    "pre_live_capturada_em"
                ] = (
                    horario_atual()
                    .isoformat()
                )

                controle[
                    "pre_live_fallback"
                ] = False

                print(
                    "🟣 PRÉ-LIVE | "
                    f"{jogo.get('home', '')} "
                    "x "
                    f"{jogo.get('away', '')} | "
                    f"odd empate = {odd_draw}"
                )

        except Exception as erro:

            print(
                "⚠️ ERRO AO CAPTURAR "
                "PRÉ-LIVE:",
                type(erro).__name__,
                erro,
            )

    salvar_controle()


# ============================================================
# TRAJETÓRIA
# ============================================================

def registrar_trajetoria(
    controle,
    resultado,
):

    try:
        minuto = int(
            resultado.get(
                "minuto",
                0,
            )
            or 0
        )
    except Exception:
        minuto = 0

    try:
        ipm = float(
            resultado.get(
                "ipm",
                0,
            )
            or 0
        )
    except Exception:
        ipm = 0.0

    try:
        var_pre = float(
            resultado.get(
                "variacao_pre_live",
                0,
            )
            or 0
        )
    except Exception:
        var_pre = 0.0

    try:
        var_ciclo = float(
            resultado.get(
                "variacao_ciclo",
                0,
            )
            or 0
        )
    except Exception:
        var_ciclo = 0.0

    ponto = {
        "minuto": minuto,
        "ipm": ipm,
        "odd_atual": resultado.get(
            "odd_atual"
        ),
        "odd_pre_live": resultado.get(
            "odd_pre_live"
        ),
        "variacao_pre_live": var_pre,
        "variacao_ciclo": var_ciclo,
        "gols": resultado.get(
            "gols",
            0,
        ),
    }

    trajetoria = controle.get(
        "trajetoria"
    )

    if not isinstance(
        trajetoria,
        list,
    ):
        trajetoria = []

    # --------------------------------------------------------
    # Atualiza o mesmo minuto em vez de duplicar
    # --------------------------------------------------------

    if trajetoria:

        ultimo = trajetoria[-1]

        if (
            isinstance(ultimo, dict)
            and ultimo.get("minuto") == minuto
        ):

            trajetoria[-1] = ponto

        else:

            trajetoria.append(
                ponto
            )

    else:

        trajetoria.append(
            ponto
        )

    controle[
        "trajetoria"
    ] = trajetoria

    # --------------------------------------------------------
    # Marco dos 45'
    # --------------------------------------------------------

    if minuto >= 45:

        controle[
            "acompanhamento_45"
        ] = True

        controle[
            "ipm_45"
        ] = ipm

        controle[
            "odd_45"
        ] = resultado.get(
            "odd_atual"
        )

        controle[
            "variacao_pre_live_45"
        ] = var_pre

        controle[
            "variacao_ciclo_45"
        ] = var_ciclo


# ============================================================
# PROCESSAMENTO DE CADA JOGO
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

    try:
        minuto = int(
            resultado.get(
                "minuto",
                0,
            )
            or 0
        )
    except Exception:
        minuto = 0

    try:
        ipm = float(
            resultado.get(
                "ipm",
                0,
            )
            or 0
        )
    except Exception:
        ipm = 0.0

    try:
        var_pre = float(
            resultado.get(
                "variacao_pre_live",
                0,
            )
            or 0
        )
    except Exception:
        var_pre = 0.0

    try:
        var_ciclo = float(
            resultado.get(
                "variacao_ciclo",
                0,
            )
            or 0
        )
    except Exception:
        var_ciclo = 0.0


    # ========================================================
    # JOGO FINALIZADO
    # ========================================================

    try:
        terminou = jogo_finalizado(
            jogo
        )
    except Exception as erro:
        print(
            "⚠️ ERRO AO VERIFICAR "
            "FINALIZAÇÃO:",
            type(erro).__name__,
            erro,
        )
        terminou = False

    if (
        not controle["finalizado"]
        and terminou
    ):

        try:

            empate = resultado_empate(
                jogo,
                mercados,
            )

        except Exception as erro:

            print(
                "⚠️ ERRO AO OBTER "
                "RESULTADO:",
                type(erro).__name__,
                erro,
            )

            empate = None

        if empate is not None:

            controle[
                "finalizado"
            ] = True

            controle[
                "resultado"
            ] = (
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

                entrada[
                    "status"
                ] = controle[
                    "resultado"
                ]

            try:

                texto = formatar_radar(
                    jogo,
                    resultado,
                    mercados,
                )

            except Exception:

                texto = ""

            placar = (
                "não disponível"
            )

            for linha in texto.splitlines():

                if linha.startswith(
                    "📊 Placar:"
                ):

                    placar = (
                        linha
                        .replace(
                            "📊 Placar:",
                            "",
                        )
                        .strip()
                    )

                    break

            enviar_telegram(
                (
                    f"{'🟢' if empate else '🔴'} "
                    "RESULTADO FINAL\n\n"
                    f"⚽ "
                    f"{jogo.get('home', 'Casa')} "
                    "x "
                    f"{jogo.get('away', 'Fora')}\n"
                    f"📊 Placar: {placar}\n"
                    f"📌 "
                    f"{'EMPATE' if empate else 'NÃO EMPATE'}"
                )
            )

            salvar_controle()

        return


    # ========================================================
    # REGISTRA TRAJETÓRIA
    # ========================================================

    registrar_trajetoria(
        controle,
        resultado,
    )


    # ========================================================
    # DADOS ATUAIS
    # ========================================================

    controle[
        "ultimo_minuto"
    ] = minuto

    controle[
        "ultima_odd"
    ] = resultado.get(
        "odd_atual"
    )

    controle[
        "ultimo_ipm"
    ] = ipm

    controle[
        "ultima_variacao_ciclo"
    ] = resultado.get(
        "variacao_ciclo"
    )

    controle[
        "ultima_variacao_pre_live"
    ] = resultado.get(
        "variacao_pre_live"
    )


    # ========================================================
    # AVALIAÇÃO DE ENTRADA
    # ========================================================

    try:

        pode_entrar = avaliar_entrada(
            resultado,
            minuto,
            IPM_MINIMO_ENTRADA,
            VARIACAO_MINIMA_ODD,
            MINUTO_MINIMO_ENTRADA,
            MINUTO_MAXIMO_ENTRADA,
        )

    except Exception as erro:

        print(
            "⚠️ ERRO AO AVALIAR "
            "ENTRADA:",
            type(erro).__name__,
            erro,
        )

        pode_entrar = False


    # ========================================================
    # ENTRADA ÚNICA
    # ========================================================

    quantidade_entradas = len(
        controle.get(
            "entradas",
            [],
        )
    )

    if (
        not controle["finalizado"]
        and quantidade_entradas
        < MAX_ENTRADAS_POR_JOGO
        and pode_entrar
    ):

        entrada = {
            "numero": quantidade_entradas + 1,
            "minuto": minuto,
            "odd": resultado.get(
                "odd_atual"
            ),
            "odd_pre_live": resultado.get(
                "odd_pre_live"
            ),
            "ipm": ipm,
            "variacao_pre_live": resultado.get(
                "variacao_pre_live"
            ),
            "variacao_ciclo": resultado.get(
                "variacao_ciclo"
            ),
            "status": "ATIVA",
        }

        controle[
            "entradas"
        ].append(
            entrada
        )

        controle[
            "entrada_ativa"
        ] = True

        controle[
            "padrao_mantido"
        ] = True


        enviar_telegram(
            (
                "🚨 ENTRADA EMPATE\n\n"
                f"⚽ "
                f"{jogo.get('home', 'Casa')} "
                "x "
                f"{jogo.get('away', 'Fora')}\n"
                f"⏱️ Minuto: {minuto}'\n"
                f"💰 Odd pré-live: "
                f"{resultado.get('odd_pre_live')}\n"
                f"💰 Odd atual: "
                f"{resultado.get('odd_atual')}\n"
                f"📉 Pré-live → atual: "
                f"{var_pre:+.2f}%\n"
                f"🔄 Último ciclo: "
                f"{var_ciclo:+.2f}%\n"
                f"🎯 IPM: {ipm:.2f}\n"
                "🟢 PADRÃO CONFIRMADO"
            )
        )


    # ========================================================
    # MARCO DOS 45'
    # ========================================================

    if minuto >= 45:

        print(
            "⏱️ MARCO 45' | "
            f"{jogo.get('home', '')} x "
            f"{jogo.get('away', '')} | "
            f"IPM={ipm:.2f} | "
            f"ODD={resultado.get('odd_atual')} | "
            f"PRÉ={var_pre:+.2f}% | "
            f"CICLO={var_ciclo:+.2f}%"
        )


    salvar_controle()


# ============================================================
# EXECUÇÃO DE UM CICLO
# ============================================================

def executar_consulta():

    print(
        "\n" + "=" * 72
    )

    print(
        "📡 IPM RADAR V4.7 | "
        + horario_atual().strftime(
            "%d/%m/%Y %H:
