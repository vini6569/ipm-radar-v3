# ============================================================
# MAIN - IPM RADAR V5.2
# PRÉ-LIVE + LIVE | COMPACTO
#
# ARQUITETURA:
# IPM ANALISA → ENVIA AO TELEGRAM PRINCIPAL
#             → ENVIA CÓPIA AO BSD WOM LAB
#
# O BSD é uma saída secundária independente.
# Falha no BSD NÃO interrompe o IPM.
# ============================================================

import os, time, threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

from config import horario_ativo, FUSO_HORARIO, Q_MIN, Q_MAX
from scanner_pre_live import escanear_pre_live
from monitor_live import registrar_jogos, processar_live, MONITORADOS
from telegram import enviar_mensagem, enviar_para_bsd
import odds_api

INTERVALO = int(os.getenv("INTERVALO_RADAR","300"))
LIMITE_DIARIO = int(os.getenv("LIMITE_DIARIO_API","500"))
ULTIMA_LISTA = None
DATA_CONTROLE = None
INICIO_CONTADOR = 0


def numero(valor, padrao=0.0):
    try:
        if valor is None:
            return float(padrao)
        if isinstance(valor, str):
            valor = valor.strip().replace(',', '.')
        return float(valor)
    except (TypeError, ValueError):
        return float(padrao)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; charset=utf-8"
        )
        self.end_headers()
        self.wfile.write(b"IPM RADAR V5.2 OK")

    def log_message(self,*args):
        pass


def iniciar_servidor():
    porta = int(os.getenv("PORT","10000"))
    s = HTTPServer(("0.0.0.0",porta),HealthHandler)
    threading.Thread(
        target=s.serve_forever,
        daemon=True
    ).start()
    print(f"SERVIDOR DE SAUDE | PORTA={porta}")


def contador():
    global DATA_CONTROLE, INICIO_CONTADOR

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

    return usadas, max(
        0,
        LIMITE_DIARIO - usadas
    )


def calcular_q_canonico(
    odd_casa,
    odd_visitante
):
    odd_casa = numero(odd_casa)
    odd_visitante = numero(odd_visitante)

    if odd_casa <= 0 or odd_visitante <= 0:
        return 0.0

    return (
        2.0
        * odd_casa
        * odd_visitante
        / (odd_casa + odd_visitante)
    )


def mensagens_pre_live(jogos):
    empate = [
        j for j in jogos
        if str(j.get("padrao", "")).upper()
        == "PADRÃO_EMPATE"
    ]

    gol = [
        j for j in jogos
        if str(j.get("padrao", "")).upper()
        == "PADRÃO_GOL"
    ]

    cabecalho = [
        "⚽ PRE-LIVE - IPM RADAR",
        "",
        f"📐 Q: {Q_MIN:.2f} até {Q_MAX:.2f}",
        "📊 R = maior odd / menor odd",
        "⚖️ Equilíbrio = 100 / R",
        "⚠️ Desequilíbrio = 100 - Equilíbrio",
        ""
    ]

    mensagens = []
    linhas = cabecalho[:]

    for titulo, grupo in (
        ("🟢 PADRÃO_EMPATE", empate),
        ("🔴 PADRÃO_GOL", gol)
    ):
        if not grupo:
            continue

        linhas.extend([
            titulo,
            ""
        ])

        for j in grupo:
            r = numero(j.get("r"))
            eq = 100 / r if r > 0 else 0.0
            deq = 100 - eq if r > 0 else 0.0

            px = numero(
                j.get(
                    "p_x",
                    j.get("probabilidade_x", 0)
                )
            )

            pxn = numero(
                j.get(
                    "p_x_normalizada",
                    j.get(
                        "probabilidade_x_normalizada",
                        0
                    )
                )
            )

            linhas.extend([
                f"⚽ {j.get('horario','--:--')} | "
                f"{j.get('casa','Casa')} x "
                f"{j.get('fora','Fora')}",

                f"🏠 {numero(j.get('odd_casa')):.2f} | "
                f"🤝 X {numero(j.get('odd_empate')):.2f} | "
                f"🚌 {numero(j.get('odd_visitante')):.2f}",

                f"📐 Q: {numero(j.get('q')):.2f}",
                f"📊 R: {r:.2f}",
                f"⚖️ Equilíbrio: {eq:.2f}%",
                f"⚠️ Desequilíbrio: {deq:.2f}%",

                f"🎯 Estrutura: "
                f"{j.get('equilibrio','NAO CLASSIFICADO')}",

                f"🧭 Padrão: "
                f"{j.get('padrao','NAO CLASSIFICADO')}",

                f"📊 P(x): {px:.2f}% | "
                f"Px(n): {pxn:.2f}%",

                ""
            ])

    linhas.extend([
        "--------------------",
        f"📋 Jogos selecionados: {len(jogos)}",
        "",
        "🤖 IPM-RADAR-V5.2",
        "🧪 Monitoramento estatístico.",
        "⚠️ Não realiza apostas automaticamente."
    ])

    texto = "\n".join(linhas)

    if len(texto) <= 4000:
        return [texto]

    # Divide em mensagens sem separar um bloco de jogo.
    mensagens = []
    atual = cabecalho[:]

    for titulo, grupo in (
        ("🟢 PADRÃO_EMPATE", empate),
        ("🔴 PADRÃO_GOL", gol)
    ):
        if not grupo:
            continue

        secao = [
            titulo,
            ""
        ]

        for j in grupo:
            r = numero(j.get("r"))
            eq = 100 / r if r > 0 else 0.0
            deq = 100 - eq if r > 0 else 0.0

            px = numero(
                j.get(
                    "p_x",
                    j.get("probabilidade_x", 0)
                )
            )

            pxn = numero(
                j.get(
                    "p_x_normalizada",
                    j.get(
                        "probabilidade_x_normalizada",
                        0
                    )
                )
            )

            secao.extend([
                f"⚽ {j.get('horario','--:--')} | "
                f"{j.get('casa','Casa')} x "
                f"{j.get('fora','Fora')}",

                f"🏠 {numero(j.get('odd_casa')):.2f} | "
                f"🤝 X {numero(j.get('odd_empate')):.2f} | "
                f"🚌 {numero(j.get('odd_visitante')):.2f}",

                f"📐 Q: {numero(j.get('q')):.2f}",
                f"📊 R: {r:.2f}",
                f"⚖️ Equilíbrio: {eq:.2f}%",
                f"⚠️ Desequilíbrio: {deq:.2f}%",

                f"🎯 Estrutura: "
                f"{j.get('equilibrio','NAO CLASSIFICADO')}",

                f"🧭 Padrão: "
                f"{j.get('padrao','NAO CLASSIFICADO')}",

                f"📊 P(x): {px:.2f}% | "
                f"Px(n): {pxn:.2f}%",

                ""
            ])

        if (
            len("\n".join(atual + secao)) > 3500
            and len(atual) > len(cabecalho)
        ):
            mensagens.append(
                "\n".join(atual)
            )
            atual = cabecalho[:]

        atual.extend(secao)

    atual.extend([
        "--------------------",
        f"📋 Jogos selecionados: {len(jogos)}",
        "",
        "🤖 IPM-RADAR-V5.2",
        "🧪 Monitoramento estatístico.",
        "⚠️ Não realiza apostas automaticamente."
    ])

    mensagens.append(
        "\n".join(atual)
    )

    return mensagens


def executar_pre_live():
    global ULTIMA_LISTA

    usados_antes, _ = contador()

    resultados = escanear_pre_live() or []

    usados_depois, _ = contador()

    print(
        f"📡 API | USADAS NO CICLO="
        f"{usados_depois-usados_antes} | "
        f"USADAS HOJE={usados_depois} | "
        f"RESTANTES={contador()[1]}"
    )

    if not resultados:
        print(
            "PRÉ-LIVE | Nenhum jogo dentro da faixa Q."
        )
        return

    # --------------------------------------------------------
    # REVALIDAÇÃO CANÔNICA DO Q
    # --------------------------------------------------------
    aprovados = []

    for jogo in resultados:
        q = calcular_q_canonico(
            jogo.get("odd_casa", 0),
            jogo.get("odd_visitante", 0),
        )

        jogo["q"] = round(q, 4)
        jogo["odd_pre_live"] = round(q, 4)

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

    registrar_jogos(aprovados)

    assinatura = tuple(
        (
            j.get("event_id"),
            round(j.get("odd_empate", 0), 3),
            round(j.get("q", 0), 3)
        )
        for j in aprovados
    )

    if assinatura == ULTIMA_LISTA:
        print(
            "PRÉ-LIVE | Lista igual à anterior."
        )
        return

    # --------------------------------------------------------
    # DISTRIBUIÇÃO DO PRE-LIVE
    #
    # 1) Telegram principal do IPM
    # 2) BSD WOM LAB
    #
    # Falha no BSD NÃO interrompe o IPM.
    # --------------------------------------------------------

    for msg in mensagens_pre_live(aprovados):

        enviado_ipm = enviar_mensagem(msg)

        print(
            f"📤 IPM | TELEGRAM PRINCIPAL | "
            f"{'OK' if enviado_ipm else 'FALHOU'}"
        )

        enviado_bsd = enviar_para_bsd(
            msg,
            tipo="PRE-LIVE"
        )

        print(
            f"📤 BSD | PRE-LIVE | "
            f"{'OK' if enviado_bsd else 'FALHOU'}"
        )

    ULTIMA_LISTA = assinatura

    print(
        f"PRÉ-LIVE | {len(aprovados)} jogos no radar | "
        f"RADAR={len(MONITORADOS)}"
    )


def loop():
    print("="*60)
    print("IPM RADAR V5.2 INICIADO")
    print(f"Q: {Q_MIN:.2f} -> {Q_MAX:.2f}")

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
                print("Radar em período de pausa.")

            else:
                print("⛔ COTA DIÁRIA ATINGIDA.")

        except Exception as e:
            print(
                "ERRO LOOP:",
                type(e).__name__,
                e
            )

        espera = max(
            1,
            INTERVALO - (time.time() - inicio)
        )

        print(
            f"CICLO | "
            f"{time.time()-inicio:.1f}s | "
            f"PRÓXIMO={espera:.0f}s"
        )

        time.sleep(espera)


if __name__=="__main__":
    iniciar_servidor()
    loop()
    
