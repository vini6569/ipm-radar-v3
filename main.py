# ============================================================
# MAIN - IPM RADAR V5.1
# CASA + EMPATE + VISITANTE
# PRE-LIVE COMPLETO + TRAJETORIA + REFERENCIA 45' + MEMORIA
# PAINEL PARAMETRIZADO DE PRÉ-ENTRADA
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
    IPM_MINIMO_ENTRADA,
    MINUTO_MINIMO_ENTRADA,
    MINUTO_MAXIMO_ENTRADA,
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
    avaliar_entrada,
    jogo_finalizado,
    resultado_empate,
)


# ============================================================
# PAINEL DE AJUSTE - ALTERE SOMENTE AQUI
# ============================================================
#
# Estes parametros controlam APENAS os sinais de observacao.
# A entrada oficial continua usando a logica do motor_ipm.py.
#
# PRÉ-ENTRADA:
#   A partir de PRE_ENTRADA_MINUTO, compara a variacao
#   PRE-LIVE -> ATUAL da odd do empate.
#
#   POSITIVO: var_pre >= PRE_ENTRADA_POSITIVO
#   NEGATIVO: var_pre <= -PRE_ENTRADA_NEGATIVO
#
# Exemplo atual: +20% / -20%.
# Para testar +15% / -15%, altere somente os dois valores.
# Para testar +30% / -30%, altere somente os dois valores.
#
# MIN 45!!!!!:
#   BASE = probabilidade implicita de referencia do empate.
#   POSITIVO = pontos percentuais acima da BASE.
#   NEGATIVO = pontos percentuais abaixo da BASE.
# ============================================================

PRE_ENTRADA_ATIVADA = True
PRE_ENTRADA_MINUTO = 10
PRE_ENTRADA_POSITIVO = 20.0
PRE_ENTRADA_NEGATIVO = 20.0

MIN45_PROB_BASE = 40.0
MIN45_AJUSTE_POSITIVO = 20.0
MIN45_AJUSTE_NEGATIVO = 20.0

MIN45_LIMITE_POSITIVO = MIN45_PROB_BASE + MIN45_AJUSTE_POSITIVO
MIN45_LIMITE_NEGATIVO = max(
    0.0,
    MIN45_PROB_BASE - MIN45_AJUSTE_NEGATIVO,
)


PORTA_SAUDE = int(os.environ.get("PORT", "10000"))

ARQUIVO_CONTROLE = Path(
    os.getenv("ARQUIVO_CONTROLE", "ipm_controle.json")
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

_lock = threading.Lock()
_controle_jogos = {}


# ============================================================
# TELEGRAM
# ============================================================

def enviar_telegram(texto):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("INFO: Telegram nao configurado; mensagem ficou no log.")
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

        with urllib.request.urlopen(requisicao, timeout=15) as resposta:
            retorno = resposta.read().decode("utf-8", errors="replace")
            print("TELEGRAM:", retorno)
            return 200 <= resposta.status < 300

    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode("utf-8", errors="replace")
        print("ERRO TELEGRAM:", erro.code, detalhe)
        return False

    except Exception as erro:
        print("ERRO TELEGRAM:", type(erro).__name__, erro)
        return False


# ============================================================
# CONTROLE PERSISTENTE
# ============================================================

def salvar_controle():
    try:
        temporario = ARQUIVO_CONTROLE.with_suffix(".tmp")

        with temporario.open("w", encoding="utf-8") as arquivo:
            with _lock:
                json.dump(
                    _controle_jogos,
                    arquivo,
                    ensure_ascii=False,
                    indent=2,
                )

        temporario.replace(ARQUIVO_CONTROLE)

    except Exception as erro:
        print(
            "ERRO AO SALVAR CONTROLE:",
            type(erro).__name__,
            erro,
        )


def carregar_controle():
    global _controle_jogos

    try:
        if not ARQUIVO_CONTROLE.exists():
            print("INFO: Arquivo de controle ainda nao existe.")
            return

        with ARQUIVO_CONTROLE.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)

        if isinstance(dados, dict):
            _controle_jogos = dados

        print("Controle carregado:", len(_controle_jogos), "jogos")

    except Exception as erro:
        print(
            "ERRO AO CARREGAR CONTROLE:",
            type(erro).__name__,
            erro,
        )


def obter_controle(event_id):
    chave = str(event_id)

    with _lock:
        controle = _controle_jogos.setdefault(
            chave,
            {
                "odd_pre_live": None,
                "odd_casa_pre_live": None,
                "odd_visitante_pre_live": None,
                "pre_live_capturada_em": None,
                "pre_live_fallback": False,
                "entradas": [],
                "entrada_ativa": False,
                "padrao_mantido": False,
                "finalizado": False,
                "resultado": None,
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
                "min45_avaliado": False,
                "min45_minuto": None,
                "min45_odd": None,
                "min45_probabilidade": None,
                "min45_ipm": None,
                "min45_sinal": None,
                "pre_entrada_enviada": False,
                "pre_entrada_minuto": None,
                "pre_entrada_variacao": None,
                "pre_entrada_sinal": None,
            },
        )

        # Compatibilidade com controles antigos.
        defaults = {
            "odd_pre_live": None,
            "odd_casa_pre_live": None,
            "odd_visitante_pre_live": None,
            "pre_live_capturada_em": None,
            "pre_live_fallback": False,
            "entradas": [],
            "entrada_ativa": False,
            "padrao_mantido": False,
            "finalizado": False,
            "resultado": None,
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
            "min45_avaliado": False,
            "min45_minuto": None,
            "min45_odd": None,
            "min45_probabilidade": None,
            "min45_ipm": None,
            "min45_sinal": None,
            "pre_entrada_enviada": False,
            "pre_entrada_minuto": None,
            "pre_entrada_variacao": None,
            "pre_entrada_sinal": None,
        }

        for chave_padrao, valor_padrao in defaults.items():
            controle.setdefault(chave_padrao, valor_padrao)

        if not isinstance(controle.get("entradas"), list):
            controle["entradas"] = []

        if not isinstance(controle.get("trajetoria"), list):
            controle["trajetoria"] = []

    return controle


# ============================================================
# SINAL IPM
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
# SERVIDOR DE SAUDE
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            agora = horario_atual()

            corpo = (
                f"{NOME_BOT} ONLINE | "
                f"Brasil: {agora.strftime('%d/%m/%Y %H:%M:%S')} | "
                f"Versao: {VERSAO}"
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
            "Servidor de saude iniciado na porta",
            PORTA_SAUDE,
        )

        servidor.serve_forever()

    except Exception as erro:
        print(
            "ERRO SERVIDOR DE SAUDE:",
            type(erro).__name__,
            erro,
        )


# ============================================================
# PRE-LIVE - CASA / EMPATE / VISITANTE
# ============================================================

def capturar_referencia_pre_live():
    try:
        jogos = buscar_jogos_pre_live() or []
        if not jogos:
            return

        odds = buscar_odds_multiplos(jogos) or []

        for jogo in jogos:
            if not isinstance(jogo, dict) or jogo.get("id") is None:
                continue

            mercados = extrair_mercados(jogo, odds) or {}

            odd_casa = float(
                mercados.get("odd_casa", 0.0) or 0.0
            )
            odd_empate = float(
                mercados.get("odd_draw", 0.0)
                or mercados.get("odd_empate", 0.0)
                or 0.0
            )
            odd_visitante = float(
                mercados.get("odd_visitante", 0.0) or 0.0
            )

            if odd_casa <= 0 and odd_empate <= 0 and odd_visitante <= 0:
                continue

            controle = obter_controle(jogo["id"])
            alterou = False

            if not controle.get("odd_casa_pre_live") and odd_casa > 0:
                controle["odd_casa_pre_live"] = odd_casa
                alterou = True

            if not controle.get("odd_pre_live") and odd_empate > 0:
                controle["odd_pre_live"] = odd_empate
                alterou = True

            if (
                not controle.get("odd_visitante_pre_live")
                and odd_visitante > 0
            ):
                controle["odd_visitante_pre_live"] = odd_visitante
                alterou = True

            if alterou and not controle.get("pre_live_capturada_em"):
                controle["pre_live_capturada_em"] = (
                    horario_atual().isoformat()
                )
                controle["pre_live_fallback"] = False

                print(
                    "PRE-LIVE | "
                    f"{jogo.get('home', '')} x "
                    f"{jogo.get('away', '')} | "
                    f"CASA={controle.get('odd_casa_pre_live')} | "
                    f"EMPATE={controle.get('odd_pre_live')} | "
                    f"VISITANTE={controle.get('odd_visitante_pre_live')}"
                )

        salvar_controle()

    except Exception as erro:
        print(
            "ERRO CAPTURA PRE-LIVE:",
            type(erro).__name__,
            erro,
        )


# ============================================================
# TRAJETORIA
# ============================================================

def registrar_trajetoria(controle, resultado):
    ponto = {
        "minuto": resultado.get("minuto", 0),
        "ipm": resultado.get("ipm", 0.0),
        "odd_casa": resultado.get("odd_casa", 0.0),
        "odd_empate": resultado.get("odd_empate", 0.0),
        "odd_visitante": resultado.get("odd_visitante", 0.0),
        "variacao_casa": resultado.get("variacao_casa", 0.0),
        "variacao_empate": resultado.get("variacao_empate", 0.0),
        "variacao_visitante": resultado.get(
            "variacao_visitante", 0.0
        ),
        "variacao_pre_live": resultado.get(
            "variacao_pre_live", 0.0
        ),
        "variacao_ciclo": resultado.get("variacao_ciclo", 0.0),
        "gols": resultado.get("gols", 0),
    }

    trajetoria = controle.get("trajetoria", [])

    if not isinstance(trajetoria, list):
        trajetoria = []

    if trajetoria:
        ultimo = trajetoria[-1]

        if (
            isinstance(ultimo, dict)
            and ultimo.get("minuto") == ponto["minuto"]
        ):
            trajetoria[-1] = ponto
        else:
            trajetoria.append(ponto)
    else:
        trajetoria.append(ponto)

    controle["trajetoria"] = trajetoria[-100:]

    try:
        minuto = int(ponto["minuto"])
    except (TypeError, ValueError):
        minuto = 0

    if (
        minuto >= 45
        and not controle.get("acompanhamento_45", False)
    ):
        controle["acompanhamento_45"] = True
        controle["ipm_45"] = ponto["ipm"]
        controle["odd_45"] = ponto["odd_empate"]
        controle["variacao_pre_live_45"] = ponto["variacao_pre_live"]
        controle["variacao_ciclo_45"] = ponto["variacao_ciclo"]


# ============================================================
# MIN 45!!!!!
# ============================================================

def avaliar_min45(jogo, controle, resultado, minuto, gols, odd_empate):
    """Observacao MIN 45 do 0x0; nao altera a entrada oficial."""

    if (
        minuto < 45
        or gols != 0
        or odd_empate <= 0
        or controle.get("min45_avaliado", False)
    ):
        return

    prob_empate_45 = (1.0 / odd_empate) * 100.0

    controle["min45_avaliado"] = True
    controle["min45_minuto"] = minuto
    controle["min45_odd"] = odd_empate
    controle["min45_probabilidade"] = prob_empate_45
    controle["min45_ipm"] = float(
        resultado.get("ipm", 0) or 0
    )

    if prob_empate_45 >= MIN45_LIMITE_POSITIVO:
        controle["min45_sinal"] = (
            f"POSITIVO +{MIN45_AJUSTE_POSITIVO:.0f}%"
        )
    elif prob_empate_45 >= MIN45_PROB_BASE:
        controle["min45_sinal"] = "CONFIRMADO"
    elif prob_empate_45 <= MIN45_LIMITE_NEGATIVO:
        controle["min45_sinal"] = (
            f"NEGATIVO -{MIN45_AJUSTE_NEGATIVO:.0f}%"
        )
    else:
        controle["min45_sinal"] = (
            f"ABAIXO DE {MIN45_PROB_BASE:.0f}%"
        )

    print(
        "MIN 45!!!!! | "
        f"{jogo.get('home', 'Casa')} x "
        f"{jogo.get('away', 'Fora')} | "
        f"0x0 | MINUTO={minuto} | "
        f"ODD X={odd_empate:.3f} | "
        f"PROB X={prob_empate_45:.2f}% | "
        f"IPM={float(resultado.get('ipm', 0) or 0):.2f} | "
        f"BASE={MIN45_PROB_BASE:.0f}% | "
        f"+{MIN45_AJUSTE_POSITIVO:.0f}%/-{MIN45_AJUSTE_NEGATIVO:.0f}% | "
        f"{controle['min45_sinal']}"
    )

    salvar_controle()


# ============================================================
# PRÉ-ENTRADA - BLOCO ISOLADO E PARAMETRIZADO
# NÃO ALTERA A ENTRADA OFICIAL
# ============================================================

def avaliar_pre_entrada(jogo, controle, minuto, var_pre, ipm):
    if not PRE_ENTRADA_ATIVADA:
        return

    if minuto < PRE_ENTRADA_MINUTO:
        return

    if controle.get("pre_entrada_enviada", False):
        return

    try:
        variacao = float(var_pre)
    except (TypeError, ValueError):
        variacao = 0.0

    sinal = None

    if variacao >= PRE_ENTRADA_POSITIVO:
        sinal = "📈 POSITIVO"
    elif variacao <= -PRE_ENTRADA_NEGATIVO:
        sinal = "📉 NEGATIVO"

    if sinal is None:
        return

    controle["pre_entrada_enviada"] = True
    controle["pre_entrada_minuto"] = minuto
    controle["pre_entrada_variacao"] = variacao
    controle["pre_entrada_sinal"] = sinal

    texto = (
        "👀 PRÉ-ENTRADA\n\n"
        f"⚽ {jogo.get('home', 'Casa')} x "
        f"{jogo.get('away', 'Fora')}\n"
        f"⏱️ Minuto: {minuto}'\n"
        f"📊 Variação pré-live: {variacao:+.2f}%\n"
        f"🎯 IPM: {float(ipm):.2f}\n"
        f"{sinal}\n"
        f"⚙️ Parâmetro: +{PRE_ENTRADA_POSITIVO:.0f}% / "
        f"-{PRE_ENTRADA_NEGATIVO:.0f}%\n"
        "🧪 SINAL DE OBSERVAÇÃO - NÃO É ENTRADA OFICIAL"
    )

    print(texto)
    enviar_telegram(texto)
    salvar_controle()


# ============================================================
# PROCESSAR JOGO
# ============================================================

def processar_jogo(jogo, mercados, resultado):
    event_id = jogo.get("id")

    if event_id is None:
        return

    controle = obter_controle(event_id)

    try:
        minuto = int(resultado.get("minuto", 0) or 0)
    except (TypeError, ValueError):
        minuto = 0

    try:
        ipm = float(resultado.get("ipm", 0.0) or 0.0)
    except (TypeError, ValueError):
        ipm = 0.0

    try:
        var_pre = float(
            resultado.get("variacao_pre_live", 0.0) or 0.0
        )
    except (TypeError, ValueError):
        var_pre = 0.0

    try:
        var_ciclo = float(
            resultado.get("variacao_ciclo", 0.0) or 0.0
        )
    except (TypeError, ValueError):
        var_ciclo = 0.0

    # --------------------------------------------------------
    # FINALIZACAO
    # --------------------------------------------------------
    try:
        if (
            not controle.get("finalizado", False)
            and jogo_finalizado(jogo)
        ):
            empate = resultado_empate(jogo, mercados)

            if empate is not None:
                controle["finalizado"] = True
                controle["resultado"] = (
                    "VERDE" if empate else "VERMELHO"
                )
                controle["entrada_ativa"] = False

                for entrada in controle.get("entradas", []):
                    entrada["status"] = controle["resultado"]

                placar_casa = 0
                placar_fora = 0
                scores = jogo.get("scores")

                if isinstance(scores, dict):
                    placar_casa = scores.get("home", 0)
                    placar_fora = scores.get("away", 0)

                enviar_telegram(
                    (
                        f"{'🟢' if empate else '🔴'} RESULTADO FINAL\n\n"
                        f"⚽ {jogo.get('home', 'Casa')} x "
                        f"{jogo.get('away', 'Fora')}\n"
                        f"📊 Placar: {placar_casa} x {placar_fora}\n"
                        f"📌 {'EMPATE' if empate else 'NAO EMPATE'}"
                    )
                )

                salvar_controle()

            return

    except Exception as erro:
        print(
            "ERRO AO FINALIZAR JOGO:",
            type(erro).__name__,
            erro,
        )

    # --------------------------------------------------------
    # TRAJETORIA E ESTADO
    # -----------------------------------
