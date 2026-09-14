# ============================================================
# MAIN - IPM RADAR V5.2 | PRE-LIVE + MONITORAMENTO
# Compacto | Q + movimento ODD X
# ============================================================

import os
import time
import threading
from datetime import datetime, time as dtime
from http.server import BaseHTTPRequestHandler, HTTPServer

from config import Q_MIN, Q_MAX
from scanner_pre_live import escanear_pre_live
from odds_api import buscar_jogos_ao_vivo_por_ids, buscar_odds_multiplos, extrair_mercados
from telegram import enviar_mensagem


# =========================
# CONFIG
# =========================
INTERVALO_RADAR = int(os.getenv("INTERVALO_RADAR", "300"))
VARIACAO_MINIMA = float(os.getenv("PRE_ENTRADA_VARIACAO", "20.0"))
JANELA_VARIACAO = 10
CONFIRMACAO_MINUTOS = 5
MAX_MSG = 3800

ULTIMA_LISTA = None
MONITORADOS = {}


# =========================
# HEALTH
# =========================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"IPM RADAR OK")

    def log_message(self, *_):
        pass


def iniciar_servidor():
    porta = int(os.getenv("PORT", "10000"))
    servidor = HTTPServer(("0.0.0.0", porta), HealthHandler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    print(f"SERVIDOR DE SAUDE | PORTA={porta}")


# =========================
# HORARIO
# =========================
def _hora(valor, padrao):
    try:
        texto = str(valor or padrao).strip()
        h, m = texto.split(":")[:2]
        return dtime(int(h), int(m))
    except Exception:
        return dtime(*padrao)


def horario_ativo():
    inicio = _hora(os.getenv("HORA_INICIO", "00:00"), (0, 0))
    fim = _hora(os.getenv("HORA_FIM", "23:59"), (23, 59))
    agora = datetime.now().time().replace(second=0, microsecond=0)

    if inicio <= fim:
        return inicio <= agora <= fim
    return agora >= inicio or agora <= fim


# =========================
# AUXILIARES
# =========================
def num(valor, padrao=0.0):
    try:
        return padrao if valor in (None, "") else float(valor)
    except (TypeError, ValueError):
        return padrao


def equilibrio_r(r):
    r = num(r)
    if r <= 0:
        return 0.0, 0.0
    e = 100 / r
    return round(e, 2), round(100 - e, 2)


def filtrar_q(lista):
    return [
        j for j in lista
        if Q_MIN <= num(j.get("q", j.get("odd_pre_live", 0))) <= Q_MAX
    ]


# =========================
# MEMORIA DOS JOGOS
# =========================
def registrar_jogos(jogos):
    agora = time.time()

    for j in jogos:
        eid = j.get("event_id")
        if eid is None:
            continue

        eid = str(eid)

        if eid not in MONITORADOS:
            MONITORADOS[eid] = {
                "event_id": eid,
                "casa": j.get("casa", "Casa"),
                "fora": j.get("fora", "Fora"),
                "q": num(j.get("q")),
                "historico": [],
                "sinal": None,
                "confirmado": False,
            }
        else:
            MONITORADOS[eid]["casa"] = j.get(
                "casa", MONITORADOS[eid]["casa"]
            )
            MONITORADOS[eid]["fora"] = j.get(
                "fora", MONITORADOS[eid]["fora"]
            )


def registrar_x(eid, odd_x):
    odd_x = num(odd_x)
    if odd_x <= 0:
        return

    jogo = MONITORADOS.get(str(eid))
    if not jogo:
        return

    agora = time.time()
    jogo["historico"].append({
        "t": agora,
        "x": odd_x,
    })

    limite = agora - (JANELA_VARIACAO + 2) * 60
    jogo["historico"] = [
        p for p in jogo["historico"] if p["t"] >= limite
    ]

    print(
        f"ODD X | ID={eid} | X={odd_x:.2f} | "
        f"HIST={len(jogo['historico'])}"
    )


def base_10(eid):
    jogo = MONITORADOS.get(str(eid))
    if not jogo:
        return 0.0

    alvo = time.time() - JANELA_VARIACAO * 60
    pontos = [p for p in jogo["historico"] if p["t"] <= alvo]

    if not pontos:
        return 0.0

    return num(max(pontos, key=lambda p: p["t"])["x"])


def variacao(base, atual):
    base, atual = num(base), num(atual)
    if base <= 0 or atual <= 0:
        return 0.0
    return (atual - base) / base * 100


def direcao(v):
    if v >= VARIACAO_MINIMA:
        return "POSITIVO"
    if v <= -VARIACAO_MINIMA:
        return "NEGATIVO"
    return None


# =========================
# SINAL + CONFIRMACAO
# =========================
def verificar_sinal(eid, minuto, odd_x):
    jogo = MONITORADOS.get(str(eid))
    if not jogo or jogo["sinal"] or jogo["confirmado"]:
        return

    base = base_10(eid)
    if base <= 0:
        print(
            f"AGUARDANDO 10 MIN | "
            f"{jogo['casa']} x {jogo['fora']}"
        )
        return

    v = variacao(base, odd_x)
    d = direcao(v)

    print(
        f"VAR 10 MIN | {jogo['casa']} x {jogo['fora']} | "
        f"BASE={base:.2f} ATUAL={odd_x:.2f} VAR={v:+.2f}%"
    )

    if not d:
        return

    jogo["sinal"] = {
        "t": time.time(),
        "min": minuto,
        "base": base,
        "x": odd_x,
        "var": v,
        "dir": d,
    }

    print(
        f"PRIMEIRO SINAL | {jogo['casa']} x {jogo['fora']} | "
        f"{d} | {v:+.2f}%"
    )


def verificar_confirmacao(eid, minuto, odd_x):
    jogo = MONITORADOS.get(str(eid))
    if not jogo or not jogo["sinal"] or jogo["confirmado"]:
        return None

    sinal = jogo["sinal"]
    if time.time() - sinal["t"] < CONFIRMACAO_MINUTOS * 60:
        return None

    v = variacao(sinal["base"], odd_x)
    d = direcao(v)

    print(
        f"CONFIRMACAO | {jogo['casa']} x {jogo['fora']} | "
        f"VAR={v:+.2f}%"
    )

    if d != sinal["dir"]:
        print(
            f"SINAL NAO CONFIRMADO | "
            f"{jogo['casa']} x {jogo['fora']}"
        )
        jogo["sinal"] = None
        return None

    jogo["confirmado"] = True

    return {
        "casa": jogo["casa"],
        "fora": jogo["fora"],
        "minuto": minuto,
        "direcao": d,
        "base": sinal["base"],
        "x": odd_x,
        "var1": sinal["var"],
        "var2": v,
    }


# =========================
# LIVE
# =========================
def processar_live():
    ids = list(MONITORADOS)
    if not ids:
        print("LIVE | Nenhum jogo no radar.")
        return

    jogos = buscar_jogos_ao_vivo_por_ids(ids) or []
    mapa = {
        str(j["id"]): j for j in jogos
        if isinstance(j, dict) and j.get("id") is not None
    }

    eventos = []
    for eid in ids:
        eventos.append(
            mapa.get(
                eid,
                {
                    "id": eid,
                    "home": MONITORADOS[eid]["casa"],
                    "away": MONITORADOS[eid]["fora"],
                },
            )
        )

    odds = buscar_odds_multiplos(eventos) or []
    if not odds:
        print("LIVE | Nenhuma odds recebida.")
        return

    leituras = 0

    for eid in ids:
        jogo = MONITORADOS.get(eid)
        if not jogo:
            continue

        evento = mapa.get(eid, eventos[ids.index(eid)])
        mercado = extrair_mercados(evento, odds) or {}
        odd_x = num(mercado.get("odd_empate", mercado.get("odd_draw")))

        if odd_x <= 0:
            print(f"ODD X NAO ENCONTRADA | ID={eid}")
            continue

        minuto = int(num(mercado.get("minuto", 0)))

        print(
            f"LIVE | {jogo['casa']} x {jogo['fora']} | "
            f"MIN={minuto}' | X={odd_x:.2f}"
        )

        registrar_x(eid, odd_x)
        verificar_sinal(eid, minuto, odd_x)

        confirmado = verificar_confirmacao(eid, minuto, odd_x)
        if confirmado:
            enviar_mensagem(formatar_confirmacao(confirmado))

        leituras += 1

    print(f"LIVE | LEITURAS={leituras}")


# =========================
# PRE-LIVE
# =========================
def executar_pre_live():
    print("\n" + "=" * 64)
    print("SCANNER PRE-LIVE | IPM RADAR V5.2")
    print(f"Q: {Q_MIN:.2f} -> {Q_MAX:.2f}")
    print("=" * 64)

    try:
        resultados = escanear_pre_live() or []
    except Exception as erro:
        print("ERRO SCANNER:", type(erro).__name__, erro)
        return

    aprovados = filtrar_q(resultados)

    print(
        f"PRE-LIVE | ENCONTRADOS={len(resultados)} | "
        f"APROVADOS={len(aprovados)}"
    )

    if not aprovados:
        print("PRE-LIVE | Nenhum jogo dentro do Q.")
        return

    registrar_jogos(aprovados)

    global ULTIMA_LISTA
    assinatura = tuple(
        (
            j.get("event_id"),
            round(num(j.get("odd_empate")), 3),
            round(num(j.get("q")), 3),
        )
        for j in aprovados
    )

    if assinatura == ULTIMA_LISTA:
        print("PRE-LIVE | Lista igual a anterior.")
        return

    mensagens = montar_mensagens(aprovados)

    for msg in mensagens:
        if enviar_mensagem(msg):
            print("PRE-LIVE | Mensagem enviada.")

    ULTIMA_LISTA = assinatura


def montar_mensagens(jogos):
    """Monta a lista PRE-LIVE no formato definido pelo Radar."""
    mensagens = []
    linhas = [
        "⚽ PRE-LIVE - IPM RADAR",
        "",
        f"📐 Q: {Q_MIN:.2f} até {Q_MAX:.2f}",
        "📊 R = desequilíbrio entre as pontas",
        "⚖️ Equilíbrio = 100 / R",
        "⚠️ Desequilíbrio = 100 - Equilíbrio",
        "",
    ]

    ultimo_dia = None

    for j in jogos:
        data = j.get("data", "")
        if data != ultimo_dia:
            if ultimo_dia is not None:
                linhas.append("")
            linhas.append(f"📅 Data: {data}")
            ultimo_dia = data

        oc = num(j.get("odd_casa"))
        ox = num(j.get("odd_empate"))
        ov = num(j.get("odd_visitante"))
        q = num(j.get("q", j.get("odd_pre_live")))
        r = num(j.get("r"))
        px = num(j.get("probabilidade_x"))
        pxn = num(j.get("probabilidade_x_normalizada"))

        eq, des = equilibrio_r(r)

        bloco = [
            f"⚽ {j.get('horario', '--:--')} | {j.get('casa', 'Casa')} x {j.get('fora', 'Fora')}",
            f"🏠 Casa {oc:.2f} | 🤝 X {ox:.2f} | 🚌 Visitante {ov:.2f}",
            f"📐 Q: {q:.2f}",
            f"📊 R: {r:.2f}",
            f"⚖️ Equilíbrio: {eq:.2f}%",
            f"⚠️ Desequilíbrio: {des:.2f}%",
            f"🎯 Estrutura: {j.get('equilibrio', 'NÃO CLASSIFICADO')}",
            f"🧭 Padrão: {j.get('padrao', 'NÃO CLASSIFICADO')}",
            f"📊 P(X): {px:.2f}% | P(X) N: {pxn:.2f}%",
            "",
        ]

        if len("\n".join(linhas + bloco)) > MAX_MSG:
            mensagens.append("\n".join(linhas))
            linhas = [
                "⚽ PRE-LIVE - IPM RADAR",
                "",
                f"📐 Q: {Q_MIN:.2f} até {Q_MAX:.2f}",
                "",
                f"📅 Data: {data}",
            ]

        linhas.extend(bloco)

    if len(linhas) > 7:
        linhas.extend([
            "────────────────────",
            f"📋 Jogos selecionados: {len(jogos)}",
            "",
            "🤖 IPM-RADAR-V5.2",
            "📚 Monitoramento estatístico pré-live.",
            "⚠️ Não realiza apostas automaticamente.",
        ])
        mensagens.append("\n".join(linhas))

    return mensagens


def formatar_confirmacao(d):
    return (
        "🤖 PRE-ENTRADA CONFIRMADA\n\n"
        f"⚽ {d['casa']} x {d['fora']}\n"
        f"⏱️ Minuto: {d['minuto']}'\n\n"
        "📈 ODD X\n"
        f"📉 Base 10 min: {d['base']:.2f}\n"
        f"📊 Atual: {d['x']:.2f}\n"
        f"🔹 Primeiro sinal: {d['var1']:+.2f}%\n"
        f"🔹 Confirmacao: {d['var2']:+.2f}%\n"
        f"🧭 Direcao: {d['direcao']}\n\n"
        "🧪 LABORATORIO IPM\n"
        "📌 Sinal estatistico para observacao."
    )


# =========================
# LOOP
# =========================
def loop():
    print("=" * 60)
    print("IPM RADAR V5.2 INICIADO")
    print(f"Q: {Q_MIN:.2f} -> {Q_MAX:.2f}")
    print(f"INTERVALO: {INTERVALO_RADAR}s")
    print(f"VARIACAO: {VARIACAO_MINIMA:.2f}% em {JANELA_VARIACAO} min")
    print(f"CONFIRMACAO: {CONFIRMACAO_MINUTOS} min")
    print("=" * 60)

    while True:
        inicio = time.time()

        try:
            if horario_ativo():
                executar_pre_live()
                processar_live()
            else:
                print("RADAR | Periodo de pausa.")
        except Exception as erro:
            print("ERRO LOOP:", type(erro).__name__, erro)

        espera = max(
            1,
            INTERVALO_RADAR - (time.time() - inicio),
        )

        print(
            f"CICLO | {time.time() - inicio:.1f}s | "
            f"PROXIMO={espera:.0f}s"
        )
        time.sleep(espera)


if __name__ == "__main__":
    iniciar_servidor()
    loop()
