# ============================================================
# MAIN - IPM RADAR V5.2
# PRÉ-LIVE + LIVE | COMPACTO
# ============================================================

import os
import time
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

from config import horario_ativo, FUSO_HORARIO, Q_MIN, Q_MAX
from scanner_pre_live import escanear_pre_live
from monitor_live import registrar_jogos, processar_live, MONITORADOS
from telegram import enviar_mensagem
import odds_api


INTERVALO = int(os.getenv("INTERVALO_RADAR", "300"))
LIMITE_DIARIO = int(os.getenv("LIMITE_DIARIO_API", "500"))

ULTIMA_LISTA = None
DATA_CONTROLE = None
INICIO_CONTADOR = 0


# ============================================================
# UTILITÁRIO
# ============================================================

def numero(valor, padrao=0.0):
    try:
        if valor is None:
            return float(padrao)

        if isinstance(valor, str):
            valor = valor.strip().replace(",", ".")

        return float(valor)

    except (TypeError, ValueError):
        return float(padrao)


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
        self.wfile.write(b"IPM RADAR V5.2 OK")

    def log_message(self, *args):
        pass


def iniciar_servidor():
    porta = int(os.getenv("PORT", "10000"))

    servidor = HTTPServer(
        ("0.0.0.0", porta),
        HealthHandler
    )

    threading.Thread(
        target=servidor.serve_forever,
        daemon=True
    ).start()

    print(f"SERVIDOR DE SAUDE | PORTA={porta}")


# ============================================================
# CONTROLE DA API
# ============================================================

def contador():

    global DATA_CONTROLE
    global INICIO_CONTADOR

    hoje = datetime.now(FUSO_HORARIO).date()

    if DATA_CONTROLE != hoje:

        DATA_CONTROLE = hoje

        INICIO_CONTADOR = getattr(
            odds_api,
            "REQUISICOES_REALIZADAS",
            0
        )

        print(
            f"🧮 CONTROLE API | NOVO DIA | "
            f"DATA={hoje} | LIMITE={LIMITE_DIARIO}"
        )

    atual = getattr(
        odds_api,
        "REQUISICOES_REALIZADAS",
        0
    )

    usadas = max(
        0,
        atual - INICIO_CONTADOR
    )

    restantes = max(
        0,
        LIMITE_DIARIO - usadas
    )

    return usadas, restantes


# ============================================================
# Q CANÔNICO
# ============================================================

def calcular_q_canonico(odd_casa, odd_visitante):

    odd_casa = numero(odd_casa)
    odd_visitante = numero(odd_visitante)

    if odd_casa <= 0 or odd_visitante <= 0:
        return 0.0

    # Q = 2 * Casa * Visitante / (Casa + Visitante)
    return (
        2.0
        * odd_casa
        * odd_visitante
        / (odd_casa + odd_visitante)
    )


# ============================================================
# MENSAGENS PRÉ-LIVE
# ============================================================

def mensagens_pre_live(jogos):

    msgs = []

    linhas = [
        "⚽ PRE-LIVE - IPM RADAR",
        "",
        "📐 Q: %.2f até %.2f" % (Q_MIN, Q_MAX),
        "📊 R = maior odd / menor odd",
        "⚖️ Equilíbrio = 100 / R",
        ""
    ]

    for jogo in jogos:

        r = numero(jogo.get("r"))

        if r > 0:
            equilibrio = 100 / r
            desequilibrio = 100 - equilibrio

            linha_equilibrio = (
                f"⚖️ Equilíbrio: {equilibrio:.2f}% | "
                f"⚠️ Desequilíbrio: {desequilibrio:.2f}%"
            )
        else:
            linha_equilibrio = "⚖️ Equilíbrio: --"

        bloco = [

            f"⚽ {jogo.get('horario', '--:--')} | "
            f"{jogo.get('casa', 'Casa')} x "
            f"{jogo.get('fora', 'Fora')}",

            f"🏠 {numero(jogo.get('odd_casa')):.2f} | "
            f"🤝 X {numero(jogo.get('odd_empate')):.2f} | "
            f"🚌 {numero(jogo.get('odd_visitante')):.2f}",

            f"📐 Q: {numero(jogo.get('q')):.2f} | "
            f"📊 R: {r:.2f}",

            linha_equilibrio,

            f"🎯 Estrutura: "
            f"{jogo.get('equilibrio', 'NAO CLASSIFICADO')}",

            f"🧭 Padrão: "
            f"{jogo.get('padrao', 'NAO CLASSIFICADO')}",

            f"⚽ GOLS: "
            f"{jogo.get('estrutura_gol', 'SEM CONFIRMAÇÃO PRÉ-LIVE')}",

            ""
        ]

        texto_atual = "\n".join(
            linhas + bloco
        )

        if len(texto_atual) > 3500:

            msgs.append(
                "\n".join(linhas)
            )

            linhas = [
                "⚽ PRE-LIVE - IPM RADAR",
                "",
                ""
            ]

        linhas += bloco

    if len(linhas) > 3:

        linhas += [
            "--------------------",
            f"📋 Jogos: {len(jogos)}",
            "🤖 IPM-RADAR-V5.2",
            "🧪 Monitoramento estatístico.",
            "⚠️ Não realiza apostas automaticamente."
        ]

        msgs.append(
            "\n".join(linhas)
        )

    return msgs


# ============================================================
# EXECUTA PRÉ-LIVE
# ============================================================

def executar_pre_live():

    global ULTIMA_LISTA

    usados_antes, _ = contador()

    resultados = escanear_pre_live() or []

    usados_depois, _ = contador()

    print(
        f"📡 API | USADAS NO CICLO="
        f"{usados_depois - usados_antes} | "
        f"USADAS HOJE={usados_depois} | "
        f"RESTANTES={contador()[1]}"
    )

    if not resultados:

        print(
            "PRÉ-LIVE | Nenhum jogo dentro da faixa Q."
        )

        return

    # ========================================================
    # REVALIDAÇÃO CANÔNICA DO Q
    # ========================================================

    aprovados = []

    for jogo in resultados:

        q = calcular_q_canonico(
            jogo.get("odd_casa", 0),
            jogo.get("odd_visitante", 0)
        )

        jogo["q"] = round(q, 4)

        if Q_MIN <= q <= Q_MAX:

            aprovados.append(jogo)

            print(
                f"✅ Q APROVADO | "
                f"ID={jogo.get('event_id')} | "
                f"Casa={numero(jogo.get('odd_casa')):.2f} | "
                f"Fora={numero(jogo.get('odd_visitante')):.2f} | "
                f"Q={q:.4f}"
            )

        else:

            print(
                f"⛔ Q REJEITADO | "
                f"ID={jogo.get('event_id')} | "
                f"Q={q:.4f} | "
                f"FAIXA={Q_MIN:.2f}→{Q_MAX:.2f}"
            )

    print(
        f"PRÉ-LIVE | DENTRO DO Q "
        f"{Q_MIN:.2f} → {Q_MAX:.2f}: "
        f"{len(aprovados)}"
    )

    if not aprovados:

        print(
            "PRÉ-LIVE | Nenhum jogo dentro da faixa Q."
        )

        return

    # ========================================================
    # REGISTRA PARA O LIVE
    # ========================================================

    registrar_jogos(aprovados)

    assinatura = tuple(
        (
            jogo.get("event_id"),
            round(numero(jogo.get("odd_empate")), 3),
            round(numero(jogo.get("q")), 3)
        )
        for jogo in aprovados
    )

    if assinatura == ULTIMA_LISTA:

        print(
            "PRÉ-LIVE | Lista igual à anterior."
        )

        return

    # ========================================================
    # ENVIA TELEGRAM
    # ========================================================

    for mensagem in mensagens_pre_live(aprovados):

        enviar_mensagem(mensagem)

    ULTIMA_LISTA = assinatura

    print(
        f"PRÉ-LIVE | {len(aprovados)} jogos no radar | "
        f"RADAR={len(MONITORADOS)}"
    )


# ============================================================
# LOOP PRINCIPAL
# ============================================================

def loop():

    print("=" * 60)
    print("IPM RADAR V5.2 INICIADO")
    print(
        f"Q: {Q_MIN:.2f} -> {Q_MAX:.2f}"
    )

    while True:

        inicio = time.time()

        try:

            usadas, restantes = contador()

            print(
                f"📡 API | USADAS={usadas} | "
                f"RESTANTES={restantes}"
            )

            if horario_ativo() and restantes > 0:

                executar_pre_live()

                if contador()[1] > 0:

                    processar_live()

            elif not horario_ativo():

                print(
                    "Radar em período de pausa."
                )

            else:

                print(
                    "⛔ COTA DIÁRIA ATINGIDA."
                )

        except Exception as erro:

            print(
                "ERRO LOOP:",
                type(erro).__name__,
                erro
            )

        duracao = time.time() - inicio

        espera = max(
            1,
            INTERVALO - duracao
        )

        print(
            f"CICLO | {duracao:.1f}s | "
            f"PRÓXIMO={espera:.0f}s"
        )

        time.sleep(espera)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    iniciar_servidor()
    loop()
