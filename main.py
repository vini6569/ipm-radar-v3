# ============================================================
# MAIN - IPM RADAR V4.2
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
# CONFIG TELEGRAM / CONTROLE
# ============================================================

PORTA_SAUDE = int(os.environ.get("PORT", "10000"))

ARQUIVO_CONTROLE = Path(
    os.getenv("ARQUIVO_CONTROLE", "ipm_controle.json")
)

TELEGRAM_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN", ""
).strip()

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID", ""
).strip()

IPM_MINIMO_ENTRADA = float(
    os.getenv("IPM_MINIMO_ENTRADA", "40")
)

MINUTO_MINIMO_ENTRADA = int(
    os.getenv("MINUTO_MINIMO_ENTRADA", "1")
)

MINUTO_MAXIMO_ENTRADA = int(
    os.getenv("MINUTO_MAXIMO_ENTRADA", "5")
)

MAX_ENTRADAS_POR_JOGO = int(
    os.getenv("MAX_ENTRADAS_POR_JOGO", "1")
)

INTERVALO_ENTRE_ENTRADAS = int(
    os.getenv("INTERVALO_ENTRE_ENTRADAS", "5")
)

_controle_jogos = {}
_lock = threading.Lock()


# ============================================================
# TELEGRAM
# ============================================================

def enviar_telegram(texto):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ℹ️ Telegram não configurado; mensagem ficou apenas no log.")
        return False

    try:
        url = (
            f"https://api.telegram.org/bot"
            f"{TELEGRAM_TOKEN}/sendMessage"
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
            ok = 200 <= resposta.status < 300

        if not ok:
            print("❌ Telegram respondeu com status:", resposta.status)

        return ok

    except Exception as erro:
        print(
            "❌ ERRO TELEGRAM:",
            type(erro).__name__,
            erro,
        )
        return False


# ============================================================
# CONTROLE PERSISTENTE
# ============================================================

def salvar_controle():
    try:
        temporario = ARQUIVO_CONTROLE.with_suffix(".tmp")

        with temporario.open("w", encoding="utf-8") as arquivo:
            json.dump(
                _controle_jogos,
                arquivo,
                ensure_ascii=False,
                indent=2,
            )

        temporario.replace(ARQUIVO_CONTROLE)

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


# ============================================================
# SERVIDOR DE SAÚDE
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            agora = horario_atual()

            corpo = (
                f"{NOME_BOT} ONLINE | "
                f"Brasil: {agora.strftime('%d/%m/%Y %H:%M:%S')} | "
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

    def log_message(self, format, *args):
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
# SINAL
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
# CONTROLE DE CADA JOGO
# ============================================================

def obter_controle(event_id):
    chave = str(event_id)

    with _lock:
        return _controle_jogos.setdefault(
            chave,
            {
                "entradas": [],
                "entrada_ativa": False,
                "padrao_mantido": False,
                "finalizado": False,
                "resultado": None,
            },
        )


# ============================================================
# PROCESSAR JOGO
# ============================================================

def processar_jogo(jogo, mercados, resultado):
    event_id = jogo.get("id")

    if event_id is None:
        return

    controle = obter_controle(event_id)
    minuto = int(resultado.get("minuto", 0) or 0)
    ipm = float(resultado.get("ipm", 0) or 0)
    variacao = abs(float(resultado.get("variacao_odd", 0) or 0))

    # --------------------------------------------------------
    # SE O JOGO JÁ ESTÁ FINALIZADO, FECHA O RESULTADO.
    # --------------------------------------------------------

    if not controle["finalizado"] and jogo_finalizado(jogo):
        empate = resultado_empate(jogo, mercados)

        if empate is not None:
            controle["finalizado"] = True
            controle["resultado"] = (
                "VERDE" if empate else "VERMELHO"
            )
            controle["entrada_ativa"] = False

            for entrada in controle["entradas"]:
                entrada["status"] = controle["resultado"]

            placar = "placar não disponível"
            try:
                # O formatador já tenta extrair o placar.
                texto_radar = formatar_radar(
                    jogo,
                    resultado,
                    mercados,
                )
                for linha in texto_radar.splitlines():
                    if linha.startswith("📊 Placar:"):
                        placar = linha.replace("📊 Placar:", "").strip()
                        break
            except Exception:
                pass

            enviar_telegram(
                (
                    f"{'🟢' if empate else '🔴'} RESULTADO FINAL\n\n"
                    f"⚽ {jogo.get('home', 'Casa')} x "
                    f"{jogo.get('away', 'Fora')}\n"
                    f"📊 Placar: {placar}\n"
                    f"📌 {'EMPATE' if empate else 'NÃO EMPATE'}"
                )
            )

            salvar_controle()

        return

    # --------------------------------------------------------
    # PADRÃO DEPOIS DA ENTRADA
    # --------------------------------------------------------

    if controle["entradas"]:
        controle["padrao_mantido"] = (
            ipm >= IPM_MINIMO_ENTRADA
            and variacao >= VARIACAO_MINIMA_ODD
        )

    # --------------------------------------------------------
    # PRIMEIRA ENTRADA
    # --------------------------------------------------------

    pode_entrar = avaliar_entrada(
        resultado,
        minuto,
        IPM_MINIMO_ENTRADA,
        VARIACAO_MINIMA_ODD,
        MINUTO_MINIMO_ENTRADA,
        MINUTO_MAXIMO_ENTRADA,
    )

    if (
        not controle["finalizado"]
        and not controle["entradas"]
        and pode_entrar
    ):
        entrada = {
            "numero": 1,
            "minuto": minuto,
            "odd": resultado.get("odd_atual"),
            "ipm": resultado.get("ipm"),
            "variacao_odd": resultado.get("variacao_odd"),
            "status": "ATIVA",
        }

        controle["entradas"].append(entrada)
        controle["entrada_ativa"] = True
        controle["padrao_mantido"] = True

        enviar_telegram(
            (
                "🚨 ENTRADA EMPATE\n\n"
                f"⚽ {jogo.get('home', 'Casa')} x "
                f"{jogo.get('away', 'Fora')}\n"
                f"⏱️ Minuto: {minuto}'\n"
                f"💰 Odd empate: {resultado.get('odd_atual')}\n"
                f"📈 Variação: {float(resultado.get('variacao_odd', 0)):+.2f}%\n"
                f"🎯 IPM: {ipm:.2f}\n"
                "🟢 PADRÃO CONFIRMADO"
            )
        )

    # --------------------------------------------------------
    # NOVA ENTRADA: DESATIVADA POR PADRÃO (MAX = 1).
    # --------------------------------------------------------

    if (
        not controle["finalizado"]
        and controle["entradas"]
        and controle["padrao_mantido"]
        and len(controle["entradas"]) < MAX_ENTRADAS_POR_JOGO
        and pode_entrar
    ):
        ultima = controle["entradas"][-1]
        ultimo_minuto = int(ultima.get("minuto", 0))

        if minuto - ultimo_minuto >= INTERVALO_ENTRE_ENTRADAS:
            numero = len(controle["entradas"]) + 1

            controle["entradas"].append(
                {
                    "numero": numero,
                    "minuto": minuto,
                    "odd": resultado.get("odd_atual"),
                    "ipm": resultado.get("ipm"),
                    "variacao_odd": resultado.get("variacao_odd"),
                    "status": "ATIVA",
                }
            )

            enviar_telegram(
                (
                    "🔁 NOVA ENTRADA EMPATE\n"
                    f"⚽ {jogo.get('home', 'Casa')} x "
                    f"{jogo.get('away', 'Fora')}\n"
                    f"⏱️ Minuto: {minuto}'\n"
                    f"💰 Odd empate: {resultado.get('odd_atual')}\n"
                    f"🎯 IPM: {ipm:.2f}"
                )
            )

    salvar_controle()


# ============================================================
# CONSULTA
# ============================================================

def executar_consulta():
    print()
    print("=" * 70)
    print(
        "📡 IPM RADAR V4.2 |",
        horario_atual().strftime("%d/%m/%Y %H:%M:%S"),
    )
    print("=" * 70)

    try:
        jogos = buscar_jogos_ao_vivo() or []

        print("JOGOS AO VIVO ENCONTRADOS:", len(jogos))

        if not jogos:
            print("ℹ️ Nenhum jogo ao vivo encontrado neste ciclo.")
            return

        jogos = jogos[:MAX_JOGOS_RADAR]
        print("JOGOS SELECIONADOS:", len(jogos))

        odds = buscar_odds_multiplos(jogos) or []
        print("EVENTOS COM ODDS RECEBIDOS:", len(odds))

        for jogo in jogos:
            try:
                if not isinstance(jogo, dict):
                    continue

                event_id = jogo.get("id")
                if event_id is None:
                    continue

                mercados = extrair_mercados(jogo, odds) or {}

                resultado = analisar_ipm_com_memoria(
                    event_id,
                    mercados.get("odd_atual", 0.0),
                    mercados.get("minuto", 0),
                    mercados.get("gols", 0),
                    mercados.get("escanteios", 0),
                    mercados.get("finalizacoes", 0),
                    mercados.get("ataques_perigosos", 0),
                )

                print(formatar_radar(jogo, resultado, mercados))

                print("🚦 SINAL:", classificar_sinal(resultado.get("ipm", 0)))
                print(
                    "💰 FILTRO ODD:",
                    abs(float(resultado.get("variacao_odd", 0))) >= VARIACAO_MINIMA_ODD,
                )

                processar_jogo(jogo, mercados, resultado)

            except Exception as erro_jogo:
                print(
                    "❌ ERRO AO ANALISAR JOGO:",
                    type(erro_jogo).__name__,
                    erro_jogo,
                )
                continue

    except Exception as erro:
        print(
            "❌ ERRO NO CICLO:",
            type(erro).__name__,
            erro,
        )


# ============================================================
# LOOP
# ============================================================

def loop_consulta():
    carregar_controle()

    print("=" * 70)
    print(f"🚀 {NOME_BOT} | VERSÃO {VERSAO}")
    print("Protocolo: referência → comparação → entrada → resultado")
    print(f"Intervalo: {INTERVALO_RADAR} segundos")
    print(f"Máximo de jogos: {MAX_JOGOS_RADAR}")
    print(f"IPM mínimo entrada: {IPM_MINIMO_ENTRADA}")
    print(
        f"Janela entrada: {MINUTO_MINIMO_ENTRADA}–"
        f"{MINUTO_MAXIMO_ENTRADA} minutos"
    )
    print("Qualquer empate será considerado VERDE.")
    print("=" * 70)

    while True:
        inicio = time.time()

        try:
            if horario_ativo():
                executar_consulta()
            else:
                print("⏸️ Radar em período de pausa.")

        except Exception as erro:
            print(
                "❌ ERRO NO LOOP:",
                type(erro).__name__,
                erro,
            )

        tempo_decorrido = time.time() - inicio
        espera = max(
            1,
            int(INTERVALO_RADAR - tempo_decorrido),
        )

        print(f"⏳ Nova consulta em {espera} segundos...")
        time.sleep(espera)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    threading.Thread(
        target=iniciar_servidor_saude,
        daemon=True,
    ).start()

    loop_consulta()
    
