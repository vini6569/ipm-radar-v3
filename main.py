# ============================================================
# MAIN - IPM RADAR V5.2 | SOMENTE PRÉ-LIVE
# ============================================================

import os
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from config import horario_ativo
from scanner_pre_live import escanear_pre_live
from telegram import enviar_mensagem


# ============================================================
# CONFIG
# ============================================================

INTERVALO_RADAR = int(os.getenv("INTERVALO_RADAR", "60"))
Q_MIN = float(os.getenv("Q_PRE_LIVE_MINIMO", "2.30"))
Q_MAX = float(os.getenv("Q_PRE_LIVE_MAXIMO", "3.00"))
TELEGRAM_MAX_CARACTERES = 3800

ULTIMA_LISTA = None


# ============================================================
# SERVIDOR DE SAÚDE
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"IPM RADAR V5.2 PRE-LIVE OK")

    def log_message(self, format, *args):
        return


def iniciar_servidor_saude():
    porta = int(os.getenv("PORT", "10000"))
    servidor = HTTPServer(("0.0.0.0", porta), HealthHandler)

    threading.Thread(
        target=servidor.serve_forever,
        daemon=True
    ).start()

    print(f"SERVIDOR DE SAUDE ATIVO | PORTA={porta}")


# ============================================================
# CONVERSÃO / EQUILÍBRIO
# ============================================================

def numero(valor, padrao=0.0):
    try:
        return padrao if valor in (None, "") else float(valor)
    except (TypeError, ValueError):
        return padrao


def equilibrio_r(r):
    r = numero(r)

    if r <= 0:
        return 0.0, 0.0

    eq = 100.0 / r
    return round(eq, 2), round(100.0 - eq, 2)


def obter_equilibrio(jogo):
    eq = numero(jogo.get("equilibrio_percentual"))
    deq = numero(jogo.get("desequilibrio_percentual"))

    if eq <= 0 and deq <= 0:
        eq, deq = equilibrio_r(jogo.get("r"))

    return eq, deq


# ============================================================
# FILTRO Q
# ============================================================

def filtrar_q(resultados):
    return [
        jogo for jogo in resultados
        if Q_MIN <= numero(
            jogo.get("odd_pre_live", jogo.get("q", 0))
        ) <= Q_MAX
    ]


# ============================================================
# MONTAR MENSAGENS
# ============================================================

def montar_mensagens(resultados):
    mensagens = []
    linhas = [
        "⚽ PRE-LIVE - IPM RADAR",
        "",
        f"📐 Q: {Q_MIN:.2f} ate {Q_MAX:.2f}",
        "📊 R = desequilibrio entre as pontas",
        "⚖️ Equilibrio = 100 / R",
        "⚠️ Desequilibrio = 100 - Equilibrio",
        "",
    ]

    ultimo_dia = None

    for jogo in resultados:
        data = jogo.get("data", "")

        if data != ultimo_dia:
            if ultimo_dia is not None:
                linhas.append("")
            linhas.append(f"📅 Data: {data}")
            ultimo_dia = data

        casa = numero(jogo.get("odd_casa"))
        empate = numero(jogo.get("odd_empate"))
        visitante = numero(jogo.get("odd_visitante"))
        q = numero(jogo.get("q"))
        r = numero(jogo.get("r"))
        px = numero(jogo.get("probabilidade_x"))
        pxn = numero(jogo.get("probabilidade_x_normalizada"))
        eq, deq = obter_equilibrio(jogo)

        linhas.extend([
            f"⚽ {jogo.get('horario', '--:--')} | "
            f"{jogo.get('casa', 'Casa')} x {jogo.get('fora', 'Fora')}",

            f"🏠 Casa {casa:.2f} | "
            f"🤝 X {empate:.2f} | "
            f"🚌 Visitante {visitante:.2f}",

            f"📐 Q: {q:.2f}",
            f"📊 R: {r:.2f}",
            f"⚖️ Equilibrio: {eq:.2f}%",
            f"⚠️ Desequilibrio: {deq:.2f}%",
            f"🎯 Estrutura: {jogo.get('equilibrio') or 'NAO CLASSIFICADO'}",
            f"🧭 Padrao: {jogo.get('padrao') or 'NAO CLASSIFICADO'}",
            f"📊 P(X): {px:.2f}% | P(X) N: {pxn:.2f}%",
            "",
        ])

        if len("\n".join(linhas)) > TELEGRAM_MAX_CARACTERES:
            bloco = linhas[:-11]
            if bloco:
                mensagens.append("\n".join(bloco))

            linhas = [
                "⚽ PRE-LIVE - IPM RADAR",
                "",
                f"📐 Q: {Q_MIN:.2f} ate {Q_MAX:.2f}",
                f"📅 Data: {data}",
                f"⚽ {jogo.get('horario', '--:--')} | "
                f"{jogo.get('casa', 'Casa')} x {jogo.get('fora', 'Fora')}",
                f"🏠 Casa {casa:.2f} | 🤝 X {empate:.2f} | "
                f"🚌 Visitante {visitante:.2f}",
                f"📐 Q: {q:.2f}",
                f"📊 R: {r:.2f}",
                f"⚖️ Equilibrio: {eq:.2f}%",
                f"⚠️ Desequilibrio: {deq:.2f}%",
                f"🎯 Estrutura: {jogo.get('equilibrio') or 'NAO CLASSIFICADO'}",
                f"🧭 Padrao: {jogo.get('padrao') or 'NAO CLASSIFICADO'}",
                f"📊 P(X): {px:.2f}% | P(X) N: {pxn:.2f}%",
                "",
            ]

    if len(linhas) > 7:
        linhas.extend([
            "--------------------",
            f"📋 Jogos selecionados: {len(resultados)}",
            "",
            "🤖 IPM-RADAR-V5.2",
            "🧪 Monitoramento estatistico pre-live.",
            "⚠️ Nao realiza apostas automaticamente.",
        ])
        mensagens.append("\n".join(linhas))

    return mensagens


# ============================================================
# EXECUTAR PRÉ-LIVE
# ============================================================

def executar_pre_live():
    global ULTIMA_LISTA

    print("\n" + "=" * 60)
    print("PRE-LIVE | IPM RADAR V5.2")
    print(f"Q: {Q_MIN:.2f} -> {Q_MAX:.2f}")
    print("=" * 60)

    try:
        resultados = escanear_pre_live() or []
    except Exception as erro:
        print(
            "ERRO NO SCANNER:",
            type(erro).__name__,
            erro
        )
        return

    aprovados = filtrar_q(resultados)

    print(
        f"JOGOS RECEBIDOS={len(resultados)} | "
        f"JOGOS APROVADOS={len(aprovados)}"
    )

    if not aprovados:
        print("Nenhum jogo dentro da faixa Q.")
        return

    assinatura = tuple(
        (
            j.get("event_id"),
            j.get("odd_empate"),
            j.get("q"),
            j.get("r"),
        )
        for j in aprovados
    )

    if assinatura == ULTIMA_LISTA:
        print("Lista igual a anterior. Sem novo envio.")
        return

    mensagens = montar_mensagens(aprovados)

    for mensagem in mensagens:
        if enviar_mensagem(mensagem):
            print("LISTA PRE-LIVE ENVIADA.")

    ULTIMA_LISTA = assinatura


# ============================================================
# LOOP
# ============================================================

def loop_consulta():
    print("IPM RADAR V5.2 | SOMENTE PRÉ-LIVE")
    print(f"Q: {Q_MIN:.2f} -> {Q_MAX:.2f}")
    print(f"INTERVALO: {INTERVALO_RADAR}s")

    while True:
        inicio = time.time()

        try:
            if horario_ativo():
                executar_pre_live()
            else:
                print("Radar em periodo de pausa.")
        except Exception as erro:
            print(
                "ERRO NO LOOP:",
                type(erro).__name__,
                erro
            )

        agora = time.time()
        proximo = (
            (int(agora) // INTERVALO_RADAR) + 1
        ) * INTERVALO_RADAR

        espera = max(1, proximo - agora)

        print(
            f"CICLO TERMINADO EM {agora - inicio:.1f}s | "
            f"PROXIMO CICLO EM {espera:.0f}s"
        )

        time.sleep(espera)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    iniciar_servidor_saude()
    loop_consulta()
    
