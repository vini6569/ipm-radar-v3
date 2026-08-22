import os
import time
import threading
import urllib.request
import urllib.parse

from config import NOME_BOT, VERSAO

from odds_api import (
    buscar_jogos_ao_vivo,
    buscar_odds_multiplos,
    extrair_mercados,
)

from historico import quantidade_jogos

from motor_ipm import (
    analisar_ipm,
)

from http.server import HTTPServer, BaseHTTPRequestHandler


# ============================================================
# CONFIGURAÇÕES
# ============================================================

INTERVALO = int(os.getenv("LAB_INTERVALO_SEGUNDOS", "60"))
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1004457093213")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# O radar começa a considerar uma movimentação depois
# de pelo menos 5 minutos de histórico.
MINUTOS_HISTORICO = 5

# IPM mínimo para gerar alerta.
IPM_MINIMO_ALERTA = 65

# Evita repetir o mesmo alerta a cada consulta.
COOLDOWN_ALERTA_SEGUNDOS = 10 * 60


# ============================================================
# MEMÓRIA
# ============================================================

# Última odd observada:
# (evento_id, mercado, linha) -> odd
memoria_odds = {}

# Primeira odd observada:
# (evento_id, mercado, linha) -> odd
odds_iniciais = {}

# Histórico de cada mercado:
# (evento_id, mercado, linha) -> [(timestamp, odd), ...]
historico_odds = {}

# Último alerta:
# (evento_id, mercado, linha) -> timestamp
ultimo_alerta = {}


# ============================================================
# SERVIDOR DE SAÚDE DO RENDER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"IPM RADAR V3 ONLINE")

    def log_message(self, format, *args):
        return


def iniciar_servidor():
    porta = int(os.environ.get("PORT", "10000"))

    servidor = HTTPServer(
        ("0.0.0.0", porta),
        HealthHandler
    )

    print(f"Servidor de saúde ativo na porta {porta}.")
    servidor.serve_forever()


# ============================================================
# TELEGRAM
# ============================================================

def enviar_telegram(texto):

    if not TOKEN:
        print("ERRO: TELEGRAM_BOT_TOKEN não configurado.")
        return False

    dados = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": texto
    }).encode("utf-8")

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    requisicao = urllib.request.Request(
        url,
        data=dados,
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            requisicao,
            timeout=20
        ) as resposta:

            resultado = resposta.read().decode("utf-8")

        if '"ok":true' in resultado.lower():
            print("Telegram: alerta enviado.")
            return True

        print("Telegram recusou:", resultado)
        return False

    except Exception as erro:
        print(
            "ERRO AO ENVIAR TELEGRAM:",
            type(erro).__name__,
            erro
        )
        return False


# ============================================================
# HISTÓRICO DE ODDS
# ============================================================

def registrar_odd(evento_id, mercado, linha, odd):

    try:
        odd = float(odd)
    except (TypeError, ValueError):
        return None

    if odd <= 0:
        return None

    chave = (
        str(evento_id),
        str(mercado),
        str(linha)
    )

    agora = time.time()

    if chave not in odds_iniciais:
        odds_iniciais[chave] = odd

    memoria_odds[chave] = odd

    historico_odds.setdefault(chave, []).append(
        (agora, odd)
    )

    # Mantém aproximadamente os últimos 30 minutos.
    limite = agora - (30 * 60)

    historico_odds[chave] = [
        item
        for item in historico_odds[chave]
        if item[0] >= limite
    ]

    return odd


def historico_suficiente(evento_id, mercado, linha):

    chave = (
        str(evento_id),
        str(mercado),
        str(linha)
    )

    historico = historico_odds.get(chave, [])

    if len(historico) < 2:
        return False

    primeiro_tempo = historico[0][0]
    ultimo_tempo = historico[-1][0]

    return (ultimo_tempo - primeiro_tempo) >= (
        MINUTOS_HISTORICO * 60
    )


# ============================================================
# PROCESSAR MOVIMENTAÇÃO
# ============================================================

def processar_movimentacao(
    evento_id,
    mercado,
    linha,
    odd_atual,
    nome_casa,
    nome_fora,
    minuto,
    placar
):

    try:
        odd_atual = float(odd_atual)
    except (TypeError, ValueError):
        return

    if odd_atual <= 0:
        return

    chave = (
        str(evento_id),
        str(mercado),
        str(linha)
    )

    odd_anterior = memoria_odds.get(chave)

    registrar_odd(
        evento_id,
        mercado,
        linha,
        odd_atual
    )

    if odd_anterior is None:
        print(
            f"  NOVA ODD | {mercado} | "
            f"Linha {linha} | {odd_atual:.2f}"
        )
        return

    if abs(odd_atual - odd_anterior) < 0.0001:
        return

    try:
        resultado = analisar_ipm(
            odds_iniciais[chave],
            odd_atual,
            minuto=minuto or 0,
            gols=0,
            escanteios=0,
            finalizacoes=0,
            ataques_perigosos=0
        )
    except Exception as erro:
        print("Erro no motor IPM:", erro)
        return

    print(
        f"  MOVIMENTO | {mercado} | "
        f"Linha {linha} | "
        f"{odd_anterior:.2f} -> {odd_atual:.2f} | "
        f"{resultado['variacao_pct']:+.2f}% | "
        f"IPM {resultado['ipm']:.0f} | "
        f"{resultado['sinal']}"
    )

    # Não dispara sinal superficial.
    if not historico_suficiente(
        evento_id,
        mercado,
        linha
    ):
        print("  AGUARDANDO HISTÓRICO DE 5 MINUTOS.")
        return

    if resultado["ipm"] < IPM_MINIMO_ALERTA:
        return

    agora = time.time()
    ultimo = ultimo_alerta.get(chave, 0)

    if agora - ultimo < COOLDOWN_ALERTA_SEGUNDOS:
        return

    ultimo_alerta[chave] = agora

    mensagem = (
        "🚨 IPM RADAR V3 — OPORTUNIDADE\n\n"
        f"⚽ {nome_casa} x {nome_fora}\n"
        f"⏱️ Minuto: {minuto}\n"
        f"📊 Placar: {placar}\n\n"
        f"🎯 Mercado: {mercado}\n"
        f"📏 Linha: {linha}\n"
        f"📉 Odd: {odds_iniciais[chave]:.2f} → {odd_atual:.2f}\n"
        f"📈 Variação: {resultado['variacao_pct']:+.2f}%\n"
        f"💪 Força: {resultado['forca']}\n"
        f"🔥 IPM: {resultado['ipm']:.0f}/100\n"
        f"🚦 {resultado['sinal']}\n\n"
        "⚠️ Análise estatística. "
        "Não realiza apostas automaticamente."
    )

    enviar_telegram(mensagem)


# ============================================================
# ANALISAR MERCADOS
# ============================================================

def analisar_movimentacao(jogo):

    evento_id = jogo.get("id")

    if not evento_id:
        return

    casa = jogo.get("home", "Casa")
    fora = jogo.get("away", "Fora")
    minuto = jogo.get("minute", jogo.get("timer", 0))
    placar = jogo.get("scores")

    for odd in jogo.get("gols", []):

        linha = odd.get("linha")

        processar_movimentacao(
            evento_id,
            "OVER",
            linha,
            odd.get("over"),
            casa,
            fora,
            minuto,
            placar
        )

        processar_movimentacao(
            evento_id,
            "UNDER",
            linha,
            odd.get("under"),
            casa,
            fora,
            minuto,
            placar
        )

    for odd in jogo.get("handicap", []):

        linha = odd.get("linha")

        processar_movimentacao(
            evento_id,
            "HANDICAP_HOME",
            linha,
            odd.get("home"),
            casa,
            fora,
            minuto,
            placar
        )

        processar_movimentacao(
            evento_id,
            "HANDICAP_AWAY",
            linha,
            odd.get("away"),
            casa,
            fora,
            minuto,
            placar
        )

    for odd in jogo.get("resultado", []):

        processar_movimentacao(
            evento_id,
            "HOME",
            "1X2",
            odd.get("home"),
            casa,
            fora,
            minuto,
            placar
        )

        processar_movimentacao(
            evento_id,
            "DRAW",
            "1X2",
            odd.get("draw"),
            casa,
            fora,
            minuto,
            placar
        )

        processar_movimentacao(
            evento_id,
            "AWAY",
            "1X2",
            odd.get("away"),
            casa,
            fora,
            minuto,
            placar
        )


# ============================================================
# LOOP PRINCIPAL
# ============================================================

def iniciar():

    print("=" * 60)
    print(NOME_BOT)
    print("VERSÃO:", VERSAO)
    print("=" * 60)

    print("IPM-RADAR-V3 iniciado.")
    print("Histórico registrado:", quantidade_jogos())
    print("Intervalo:", INTERVALO, "segundos")
    print("Histórico mínimo:", MINUTOS_HISTORICO, "minutos")
    print("IPM mínimo para alerta:", IPM_MINIMO_ALERTA)
    print("Telegram:", "CONFIGURADO" if TOKEN else "NÃO CONFIGURADO")
    print("Chat ID:", CHAT_ID)
    print()

    while True:

        try:

            jogos = buscar_jogos_ao_vivo()

            if not isinstance(jogos, list):
                jogos = []

            print(
                "Jogos ao vivo encontrados:",
                len(jogos)
            )

            odds_eventos = []

            if jogos:
                odds_eventos = buscar_odds_multiplos(jogos)

            if not isinstance(odds_eventos, list):
                odds_eventos = []

            print(
                "Eventos com odds recebidos:",
                len(odds_eventos)
            )

            odds_por_id = {}

            for odds_evento in odds_eventos:

                if not isinstance(
                    odds_evento,
                    dict
                ):
                    continue

                evento_id = odds_evento.get("id")

                if evento_id:
                    odds_por_id[str(evento_id)] = odds_evento

            for jogo in jogos:

                if not isinstance(jogo, dict):
                    continue

                jogo_id = jogo.get("id")

                if not jogo_id:
                    continue

                print("-" * 60)

                print(
                    jogo.get("home"),
                    "x",
                    jogo.get("away")
                )

                print(
                    "ID:",
                    jogo_id
                )

                print(
                    "MINUTO:",
                    jogo.get("minute", jogo.get("timer"))
                )

                print(
                    "PLACAR:",
                    jogo.get("scores")
                )

                odds_evento = odds_por_id.get(
                    str(jogo_id)
                )

                if not odds_evento:
                    print(
                        "Nenhuma resposta de odds "
                        "para este ID."
                    )
                    continue

                try:
                    mercados = extrair_mercados(
                        odds_evento
                    )
                except Exception as erro:
                    print(
                        "Erro ao extrair mercados:",
                        type(erro).__name__,
                        erro
                    )
                    continue

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

                analisar_movimentacao(jogo)

            print()
            print(
                "ODDS NA MEMÓRIA:",
                len(memoria_odds)
            )

            print(
                "MERCADOS COM HISTÓRICO:",
                len(historico_odds)
            )

            print()
            print(
                f"Nova consulta em {INTERVALO} segundos..."
            )

            time.sleep(INTERVALO)

        except Exception as erro:

            print()
            print("ERRO NO RADAR:")
            print(type(erro).__name__)
            print(erro)
            print()

            time.sleep(30)


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    threading.Thread(
        target=iniciar_servidor,
        daemon=True
    ).start()

    iniciar()
time.sleep(60)
