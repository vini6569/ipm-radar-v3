# ============================================================
# MAIN - IPM RADAR V4.3
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
    NOME_BOT, VERSAO, INTERVALO_RADAR, MAX_JOGOS_RADAR,
    IPM_MINIMO_OBSERVACAO, IPM_MINIMO_FORTE, IPM_MINIMO_MUITO_FORTE,
    VARIACAO_MINIMA_ODD, horario_ativo, horario_atual,
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

PORTA_SAUDE = int(os.environ.get("PORT", "10000"))
ARQUIVO_CONTROLE = Path(os.getenv("ARQUIVO_CONTROLE", "ipm_controle.json"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

IPM_MINIMO_ENTRADA = float(os.getenv("IPM_MINIMO_ENTRADA", "40"))
MINUTO_MINIMO_ENTRADA = int(os.getenv("MINUTO_MINIMO_ENTRADA", "1"))
MINUTO_MAXIMO_ENTRADA = int(os.getenv("MINUTO_MAXIMO_ENTRADA", "5"))
MAX_ENTRADAS_POR_JOGO = int(os.getenv("MAX_ENTRADAS_POR_JOGO", "1"))

_controle_jogos = {}
_lock = threading.Lock()

def enviar_telegram(texto):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("ℹ️ Telegram não configurado; mensagem ficou apenas no log.")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        dados = urllib.parse.urlencode({"chat_id": TELEGRAM_CHAT_ID, "text": texto}).encode("utf-8")
        requisicao = urllib.request.Request(url, data=dados, method="POST")
        with urllib.request.urlopen(requisicao, timeout=15) as resposta:
            return 200 <= resposta.status < 300
    except Exception as erro:
        print("❌ ERRO TELEGRAM:", type(erro).__name__, erro)
        return False

def salvar_controle():
    try:
        temporario = ARQUIVO_CONTROLE.with_suffix(".tmp")
        with temporario.open("w", encoding="utf-8") as arquivo:
            json.dump(_controle_jogos, arquivo, ensure_ascii=False, indent=2)
        temporario.replace(ARQUIVO_CONTROLE)
    except Exception as erro:
        print("❌ ERRO AO SALVAR CONTROLE:", type(erro).__name__, erro)

def carregar_controle():
    global _controle_jogos
    try:
        if not ARQUIVO_CONTROLE.exists():
            return
        with ARQUIVO_CONTROLE.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        if isinstance(dados, dict):
            _controle_jogos = dados
            print("💾 Controle carregado:", len(_controle_jogos), "jogos")
    except Exception as erro:
        print("⚠️ ERRO AO CARREGAR CONTROLE:", type(erro).__name__, erro)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            agora = horario_atual()
            corpo = (
                f"{NOME_BOT} ONLINE | Brasil: {agora.strftime('%d/%m/%Y %H:%M:%S')} | "
                f"Versão: {VERSAO}"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
        except Exception:
            try:
                self.send_response(500); self.end_headers()
            except Exception:
                pass
    def log_message(self, format, *args):
        return

def iniciar_servidor_saude():
    try:
        servidor = HTTPServer(("0.0.0.0", PORTA_SAUDE), HealthHandler)
        print("🌐 Servidor de saúde iniciado na porta", PORTA_SAUDE)
        servidor.serve_forever()
    except Exception as erro:
        print("❌ ERRO SERVIDOR DE SAÚDE:", type(erro).__name__, erro)

def classificar_sinal(ipm):
    try: valor = float(ipm)
    except (TypeError, ValueError): valor = 0.0
    if valor >= IPM_MINIMO_MUITO_FORTE: return "SINAL MUITO FORTE"
    if valor >= IPM_MINIMO_FORTE: return "SINAL FORTE"
    if valor >= IPM_MINIMO_OBSERVACAO: return "OBSERVAR"
    return "SEM SINAL"

def obter_controle(event_id):
    chave = str(event_id)
    with _lock:
        return _controle_jogos.setdefault(chave, {
            "odd_pre_live": None,
            "entradas": [],
            "entrada_ativa": False,
            "padrao_mantido": False,
            "finalizado": False,
            "resultado": None,
        })

def capturar_referencia_pre_live():
    """Captura e guarda a odd de empate antes do jogo começar."""
    jogos = buscar_jogos_pre_live() or []
    if not jogos:
        return

    odds = buscar_odds_multiplos(jogos) or []
    for jogo in jogos:
        if not isinstance(jogo, dict) or jogo.get("id") is None:
            continue
        mercados = extrair_mercados(jogo, odds) or {}
        odd_draw = float(mercados.get("odd_draw", 0.0) or 0.0)
        if odd_draw <= 0:
            continue

        controle = obter_controle(jogo["id"])
        if not controle.get("odd_pre_live"):
            controle["odd_pre_live"] = odd_draw
            controle["pre_live_capturada_em"] = horario_atual().isoformat()
            print(
                f"🟣 PRÉ-LIVE | {jogo.get('home')} x {jogo.get('away')} | "
                f"odd empate = {odd_draw}"
            )
    salvar_controle()

def processar_jogo(jogo, mercados, resultado):
    event_id = jogo.get("id")
    if event_id is None:
        return

    controle = obter_controle(event_id)
    minuto = int(resultado.get("minuto", 0) or 0)
    ipm = float(resultado.get("ipm", 0) or 0)
    var_pre = abs(float(resultado.get("variacao_pre_live", 0) or 0))
    var_ciclo = abs(float(resultado.get("variacao_ciclo", 0) or 0))

    if not controle["finalizado"] and jogo_finalizado(jogo):
        empate = resultado_empate(jogo, mercados)
        if empate is not None:
            controle["finalizado"] = True
            controle["resultado"] = "VERDE" if empate else "VERMELHO"
            controle["entrada_ativa"] = False
            for entrada in controle["entradas"]:
                entrada["status"] = controle["resultado"]

            texto = formatar_radar(jogo, resultado, mercados)
            placar = "não disponível"
            for linha in texto.splitlines():
                if linha.startswith("📊 Placar:"):
                    placar = linha.replace("📊 Placar:", "").strip()
                    break

            enviar_telegram(
                f"{'🟢' if empate else '🔴'} RESULTADO FINAL\n\n"
                f"⚽ {jogo.get('home', 'Casa')} x {jogo.get('away', 'Fora')}\n"
                f"📊 Placar: {placar}\n"
                f"📌 {'EMPATE' if empate else 'NÃO EMPATE'}"
            )
            salvar_controle()
        return

    # Primeiro ciclo após a captura pré-live.
    # Entrada somente entre 1 e 5 min e usando pré-live -> atual.
    pode_entrar = avaliar_entrada(
        resultado, minuto, IPM_MINIMO_ENTRADA, VARIACAO_MINIMA_ODD,
        MINUTO_MINIMO_ENTRADA, MINUTO_MAXIMO_ENTRADA,
    )

    # Depois dos 5 minutos não cria nova entrada por esta regra.
    # O radar continua analisando o movimento de cada ciclo de 300 s.
    controle["ultimo_minuto"] = minuto
    controle["ultima_odd"] = resultado.get("odd_atual")
    controle["ultima_variacao_ciclo"] = resultado.get("variacao_ciclo")
    controle["ultima_variacao_pre_live"] = resultado.get("variacao_pre_live")
    controle["ultimo_ipm"] = ipm

    if (
        not controle["finalizado"]
        and not controle["entradas"]
        and pode_entrar
    ):
        entrada = {
            "numero": 1,
            "minuto": minuto,
            "odd": resultado.get("odd_atual"),
            "odd_pre_live": resultado.get("odd_pre_live"),
            "ipm": ipm,
            "variacao_pre_live": resultado.get("variacao_pre_live"),
            "variacao_ciclo": resultado.get("variacao_ciclo"),
            "status": "ATIVA",
        }
        controle["entradas"].append(entrada)
        controle["entrada_ativa"] = True
        controle["padrao_mantido"] = True

        enviar_telegram(
            "🚨 ENTRADA EMPATE\n\n"
            f"⚽ {jogo.get('home', 'Casa')} x {jogo.get('away', 'Fora')}\n"
            f"⏱️ Minuto: {minuto}'\n"
            f"💰 Odd pré-live: {resultado.get('odd_pre_live')}\n"
            f"💰 Odd atual: {resultado.get('odd_atual')}\n"
            f"📉 Pré-live → atual: {float(resultado.get('variacao_pre_live', 0)):+.2f}%\n"
            f"🔄 Último ciclo: {float(resultado.get('variacao_ciclo', 0)):+.2f}%\n"
            f"🎯 IPM: {ipm:.2f}\n"
            "🟢 PADRÃO CONFIRMADO"
        )

    salvar_controle()

def executar_consulta():
    print("\n" + "=" * 72)
    print("📡 IPM RADAR V4.3 |", horario_atual().strftime("%d/%m/%Y %H:%M:%S"))
    print("=" * 72)

    # 1) Primeiro captura pré-live.
    try:
        capturar_referencia_pre_live()
    except Exception as erro:
        print("⚠️ ERRO PRÉ-LIVE:", type(erro).__name__, erro)

    # 2) Depois processa os jogos ao vivo.
    try:
        jogos = buscar_jogos_ao_vivo() or []
        if not jogos:
            print("ℹ️ Nenhum jogo ao vivo encontrado neste ciclo.")
            return

        jogos = jogos[:MAX_JOGOS_RADAR]
        odds = buscar_odds_multiplos(jogos) or []

        for jogo in jogos:
            try:
                if not isinstance(jogo, dict) or jogo.get("id") is None:
                    continue

                event_id = jogo["id"]
                mercados = extrair_mercados(jogo, odds) or {}
                controle = obter_controle(event_id)

                # Fallback: se não houve captura pré-live, a primeira odd
                # ao vivo vira referência inicial. O log deixa isso explícito.
                if not controle.get("odd_pre_live"):
                    odd_draw = float(mercados.get("odd_draw", 0.0) or 0.0)
                    if odd_draw > 0:
                        controle["odd_pre_live"] = odd_draw
                        controle["pre_live_fallback"] = True
                        print(
                            f"⚠️ FALLBACK REFERÊNCIA | {jogo.get('home')} x "
                            f"{jogo.get('away')} | odd={odd_draw}"
                        )

                resultado = analisar_ipm_com_memoria(
                    event_id,
                    mercados.get("odd_atual", 0.0),
                    mercados.get("minuto", 0),
                    mercados.get("gols", 0),
                    mercados.get("escanteios", 0),
                    mercados.get("finalizacoes", 0),
                    mercados.get("ataques_perigosos", 0),
                    odd_pre_live=controle.get("odd_pre_live"),
                )

                print(formatar_radar(jogo, resultado, mercados))
                print("🚦 SINAL:", classificar_sinal(resultado.get("ipm", 0)))
                print("🔄 CICLO 300s:", f"{float(resultado.get('variacao_ciclo', 0)):+.2f}%")
                print("📉 PRÉ-LIVE:", f"{float(resultado.get('variacao_pre_live', 0)):+.2f}%")

                processar_jogo(jogo, mercados, resultado)

            except Exception as erro_jogo:
                print("❌ ERRO AO ANALISAR JOGO:", type(erro_jogo).__name__, erro_jogo)

    except Exception as erro:
        print("❌ ERRO NO CICLO:", type(erro).__name__, erro)

def loop_consulta():
    carregar_controle()
    print("=" * 72)
    print(f"🚀 {NOME_BOT} | VERSÃO {VERSAO}")
    print("Protocolo: pré-live → 0-5 min → ciclos sucessivos de 300 s → resultado")
    print(f"Intervalo: {INTERVALO_RADAR} segundos")
    print(f"Máximo de jogos: {MAX_JOGOS_RADAR}")
    print(f"Janela de entrada: {MINUTO_MINIMO_ENTRADA}–{MINUTO_MAXIMO_ENTRADA} min")
    print(f"IPM mínimo entrada: {IPM_MINIMO_ENTRADA}")
    print("📨 Telegram: sinais e resultados preservados.")
    print("=" * 72)

    while True:
        inicio = time.time()
        try:
            if horario_ativo():
                executar_consulta()
            else:
                print("⏸️ Radar em período de pausa.")
        except Exception as erro:
            print("❌ ERRO NO LOOP:", type(erro).__name__, erro)

        espera = max(1, int(INTERVALO_RADAR - (time.time() - inicio)))
        print(f"⏳ Nova consulta em {espera} segundos...")
        time.sleep(espera)

if __name__ == "__main__":
    threading.Thread(target=iniciar_servidor_saude, daemon=True).start()
    loop_consulta()
