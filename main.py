# ============================================================
# MAIN - IPM RADAR | PRE-LIVE + MONITORAMENTO
# ============================================================

import os
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from config import horario_ativo
from scanner_pre_live import escanear_pre_live
from odds_api import (
    buscar_jogos_ao_vivo_por_ids,
    buscar_odds_multiplos,
    extrair_mercados,
)
from telegram import enviar_mensagem

INTERVALO_RADAR = int(os.getenv("INTERVALO_RADAR", "300"))
Q_MIN = float(os.getenv("Q_PRE_LIVE_MINIMO", "2.30"))
Q_MAX = float(os.getenv("Q_PRE_LIVE_MAXIMO", "3.00"))
VARIACAO_MINIMA = float(os.getenv("PRE_ENTRADA_VARIACAO", "20.0"))
JANELA_VARIACAO_MINUTOS = 10
CONFIRMACAO_MINUTOS = 5
TELEGRAM_MAX_CARACTERES = 3800

ULTIMA_LISTA = None
JOGOS_MONITORADOS = {}
SINAIS_PRE_ENTRADA = {}


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"IPM RADAR OK")

    def log_message(self, format, *args):
        return


def iniciar_servidor_saude():
    porta = int(os.getenv("PORT", "10000"))
    servidor = HTTPServer(("0.0.0.0", porta), HealthHandler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    print(f"🌐 SERVIDOR DE SAUDE ATIVO | PORTA={porta}")


def numero(valor, padrao=0.0):
    try:
        if valor in (None, ""):
            return padrao
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def calcular_valores_equilibrio(r):
    r = numero(r)
    if r <= 0:
        return 0.0, 0.0
    equilibrio = 100.0 / r
    return round(equilibrio, 2), round(100.0 - equilibrio, 2)


def obter_equilibrio_jogo(jogo):
    r = numero(jogo.get("r", 0))
    equilibrio = numero(jogo.get("equilibrio_percentual", 0))
    desequilibrio = numero(jogo.get("desequilibrio_percentual", 0))
    if equilibrio <= 0 and desequilibrio <= 0:
        equilibrio, desequilibrio = calcular_valores_equilibrio(r)
    return equilibrio, desequilibrio


def filtrar_por_q(resultados):
    return [
        jogo for jogo in resultados
        if Q_MIN <= numero(jogo.get("odd_pre_live", jogo.get("q", 0))) <= Q_MAX
    ]


def registrar_jogos_monitorados(jogos):
    agora = time.time()
    for jogo in jogos:
        event_id = jogo.get("event_id")
        if event_id is None:
            continue
        event_id = str(event_id)
        if event_id not in JOGOS_MONITORADOS:
            JOGOS_MONITORADOS[event_id] = {
                "event_id": event_id,
                "casa": jogo.get("casa", "Casa"),
                "fora": jogo.get("fora", "Fora"),
                "q": numero(jogo.get("q", 0)),
                "odd_pre_live": numero(jogo.get("odd_empate", 0)),
                "criado_em": agora,
                "historico": [],
                "primeiro_sinal": None,
                "confirmado": False,
            }
        else:
            JOGOS_MONITORADOS[event_id]["casa"] = jogo.get("casa", JOGOS_MONITORADOS[event_id]["casa"])
            JOGOS_MONITORADOS[event_id]["fora"] = jogo.get("fora", JOGOS_MONITORADOS[event_id]["fora"])


def registrar_odd_x(event_id, odd_x):
    event_id = str(event_id)
    odd_x = numero(odd_x)
    if odd_x <= 0:
        return
    jogo = JOGOS_MONITORADOS.get(event_id)
    if not jogo:
        return
    agora = time.time()
    jogo.setdefault("historico", []).append({"timestamp": agora, "odd_x": odd_x})
    limite = agora - ((JANELA_VARIACAO_MINUTOS + 2) * 60)
    jogo["historico"] = [p for p in jogo["historico"] if p.get("timestamp", 0) >= limite]
    print(f"📊 ODD X REGISTRADA | ID={event_id} | ODD X={odd_x:.2f} | HISTORICO={len(jogo['historico'])}")


def obter_odd_base_10_min(event_id):
    jogo = JOGOS_MONITORADOS.get(str(event_id))
    if not jogo:
        return 0.0
    alvo = time.time() - JANELA_VARIACAO_MINUTOS * 60
    candidatos = [p for p in jogo.get("historico", []) if p.get("timestamp", 0) <= alvo]
    if not candidatos:
        return 0.0
    ponto = max(candidatos, key=lambda p: p["timestamp"])
    base = numero(ponto.get("odd_x", 0))
    print(f"📊 BASE 10 MIN | ID={event_id} | ODD X BASE={base:.2f}")
    return base


def calcular_variacao(odd_base, odd_atual):
    odd_base = numero(odd_base)
    odd_atual = numero(odd_atual)
    if odd_base <= 0 or odd_atual <= 0:
        return 0.0
    return ((odd_atual - odd_base) / odd_base) * 100.0


def identificar_direcao(variacao):
    if variacao >= VARIACAO_MINIMA:
        return "POSITIVO"
    if variacao <= -VARIACAO_MINIMA:
        return "NEGATIVO"
    return None


def verificar_primeiro_sinal(event_id, minuto, odd_x):
    event_id = str(event_id)
    jogo = JOGOS_MONITORADOS.get(event_id)
    if not jogo or jogo.get("primeiro_sinal") is not None or jogo.get("confirmado"):
        return
    odd_base = obter_odd_base_10_min(event_id)
    if odd_base <= 0:
        print(f"⏳ AGUARDANDO 10 MIN DE HISTORICO | {jogo['casa']} x {jogo['fora']}")
        return
    variacao = calcular_variacao(odd_base, odd_x)
    direcao = identificar_direcao(variacao)
    print(f"📈 VARIACAO 10 MIN | {jogo['casa']} x {jogo['fora']} | BASE={odd_base:.2f} | ATUAL={odd_x:.2f} | VAR={variacao:+.2f}%")
    if direcao is None:
        return
    jogo["primeiro_sinal"] = {
        "timestamp": time.time(),
        "minuto": minuto,
        "odd_base": odd_base,
        "odd_x": odd_x,
        "variacao": variacao,
        "direcao": direcao,
    }
    print(f"🚨 PRIMEIRO SINAL | {jogo['casa']} x {jogo['fora']} | {direcao} | {variacao:+.2f}%")


def verificar_confirmacao(event_id, minuto, odd_x):
    event_id = str(event_id)
    jogo = JOGOS_MONITORADOS.get(event_id)
    if not jogo:
        return None
    sinal = jogo.get("primeiro_sinal")
    if not sinal or jogo.get("confirmado"):
        return None
    passado = time.time() - sinal["timestamp"]
    if passado < CONFIRMACAO_MINUTOS * 60:
        print(f"⏳ AGUARDANDO CONFIRMACAO | {jogo['casa']} x {jogo['fora']} | FALTAM={max(0, CONFIRMACAO_MINUTOS * 60 - passado):.0f}s")
        return None
    variacao = calcular_variacao(sinal["odd_base"], odd_x)
    direcao_atual = identificar_direcao(variacao)
    print(f"📊 CONFIRMACAO 5 MIN | {jogo['casa']} x {jogo['fora']} | BASE={sinal['odd_base']:.2f} | ATUAL={odd_x:.2f} | VAR={variacao:+.2f}%")
    if direcao_atual != sinal["direcao"]:
        print(f"❌ SINAL NAO CONFIRMADO | {jogo['casa']} x {jogo['fora']}")
        jogo["primeiro_sinal"] = None
        return None
    jogo["confirmado"] = True
    resultado = {
        "event_id": event_id,
        "casa": jogo["casa"],
        "fora": jogo["fora"],
        "minuto": minuto,
        "direcao": direcao_atual,
        "variacao_inicial": sinal["variacao"],
        "variacao_confirmada": variacao,
        "odd_base": sinal["odd_base"],
        "odd_x": odd_x,
    }
    print(f"🚨 PRE-ENTRADA CONFIRMADA | {jogo['casa']} x {jogo['fora']} | {direcao_atual} | {variacao:+.2f}%")
    return resultado


def processar_live():
    ids = list(JOGOS_MONITORADOS.keys())
    if not ids:
        print("📡 LIVE | Nenhum jogo no radar.")
        return

    print(f"📡 LIVE | Consultando {len(ids)} jogos monitorados.")
    jogos_live = buscar_jogos_ao_vivo_por_ids(ids) or []

    mapa_live = {str(j.get("id")): j for j in jogos_live if isinstance(j, dict) and j.get("id") is not None}
    eventos_para_odds = []
    for event_id in ids:
        evento = mapa_live.get(str(event_id))
        if evento is None:
            monitorado = JOGOS_MONITORADOS[str(event_id)]
            evento = {
                "id": str(event_id),
                "home": monitorado.get("casa", "Casa"),
                "away": monitorado.get("fora", "Fora"),
            }
        eventos_para_odds.append(evento)

    odds = buscar_odds_multiplos(eventos_para_odds) or []
    if not odds:
        print("❌ ODDS MONITORAMENTO: nenhuma odds recebida neste ciclo.")
        return

    processados = 0
    for event_id in ids:
        event_id = str(event_id)
        monitorado = JOGOS_MONITORADOS.get(event_id)
        if not monitorado:
            continue
        jogo_live = mapa_live.get(event_id)
        if jogo_live is None:
            jogo_live = {
                "id": event_id,
                "home": monitorado.get("casa", "Casa"),
                "away": monitorado.get("fora", "Fora"),
            }
        mercados = extrair_mercados(jogo_live, odds) or {}
        odd_x = numero(mercados.get("odd_empate", mercados.get("odd_draw", 0)))
        if odd_x <= 0:
            print(f"❌ ODD X NAO ENCONTRADA | ID={event_id}")
            continue
        minuto = int(numero(mercados.get("minuto", 0)))
        print(f"📈 MOVIMENTACAO 5 MIN | {monitorado['casa']} x {monitorado['fora']} | MIN={minuto}' | ODD X={odd_x:.2f} | ID={event_id}")
        registrar_odd_x(event_id, odd_x)
        verificar_primeiro_sinal(event_id, minuto, odd_x)
        confirmacao = verificar_confirmacao(event_id, minuto, odd_x)
        if confirmacao:
            enviar_mensagem(formatar_pre_entrada(confirmacao))
        processados += 1
    print(f"✅ MONITORAMENTO CONCLUIDO | LEITURAS={processados}")


def formatar_pre_entrada(dados):
    return (
        "🚨 PRE-ENTRADA CONFIRMADA\n\n"
        f"⚽ Jogo: {dados['casa']} x {dados['fora']}\n"
        f"⏱️ Minuto: {dados['minuto']}'\n\n"
        "📊 MONITORAMENTO DA ODD X\n"
        f"💰 Odd X base (10 min): {numero(dados.get('odd_base')):.2f}\n"
        f"💰 Odd X atual: {numero(dados.get('odd_x')):.2f}\n"
        f"📉 Primeiro sinal: {numero(dados.get('variacao_inicial')):+.2f}%\n"
        f"📈 Confirmacao: {numero(dados.get('variacao_confirmada')):+.2f}%\n"
        f"🚦 Direcao: {dados['direcao']}\n\n"
        "🧪 LABORATORIO IPM\n"
        "⚠️ Sinal estatistico para observacao. Nao realiza apostas."
    )


def executar_pre_live():
    print("\n" + "=" * 72)
    print("🧪 PRE-LIVE | IPM RADAR")
    print(f"📐 Q: {Q_MIN:.2f} -> {Q_MAX:.2f}")
    print("=" * 72)
    try:
        resultados = escanear_pre_live() or []
    except Exception as erro:
        print("❌ ERRO NO SCANNER:", type(erro).__name__, erro)
        return
    aprovados = filtrar_por_q(resultados)
    print("🎯 JOGOS APROVADOS:", len(aprovados))
    if not aprovados:
        print("⚠️ Nenhum jogo dentro da faixa Q.")
        return
    registrar_jogos_monitorados(aprovados)
    global ULTIMA_LISTA
    assinatura = tuple((j.get("event_id"), j.get("odd_empate"), j.get("q"), j.get("r")) for j in aprovados)
    if assinatura == ULTIMA_LISTA:
        print("📋 Lista igual a anterior.")
        return
    for mensagem in montar_mensagens(aprovados):
        if enviar_mensagem(mensagem):
            print("✅ LISTA PRE-LIVE ENVIADA.")
    ULTIMA_LISTA = assinatura


def montar_mensagens(resultados):
    mensagens = []

    def novo_bloco():
        return [
            "🧪 PRE-LIVE - IPM RADAR", "",
            f"📐 Q: {Q_MIN:.2f} ate {Q_MAX:.2f}",
            "📊 R = desequilibrio entre as pontas",
            "⚖️ Equilibrio = 100 / R",
            "⚠️ Desequilibrio = 100 - Equilibrio", "",
        ]

    linhas = novo_bloco()
    ultimo_dia = None

    for jogo in resultados:
        data = jogo.get("data", "")

        if data != ultimo_dia:
            if ultimo_dia is not None:
                linhas.append("")
            linhas.append(f"📅 Data: {data}")
            ultimo_dia = data

        odd_casa = numero(jogo.get("odd_casa", 0))
        odd_empate = numero(jogo.get("odd_empate", 0))
        odd_visitante = numero(jogo.get("odd_visitante", 0))
        q = numero(jogo.get("q", 0))
        r = numero(jogo.get("r", 0))
        prob_x = numero(jogo.get("probabilidade_x", 0))
        prob_x_normalizada = numero(jogo.get("probabilidade_x_normalizada", 0))
        equilibrio, desequilibrio = obter_equilibrio_jogo(jogo)
        classificacao = jogo.get("equilibrio", "")
        padrao = jogo.get("padrao", "")

        linhas.extend([
            f"⚽ {jogo.get('horario', '--:--')} | {jogo.get('casa', 'Casa')} x {jogo.get('fora', 'Fora')}",
            f"🏠 Casa {odd_casa:.2f} | 🤝 X {odd_empate:.2f} | 🚌 Visitante {odd_visitante:.2f}",
            f"📐 Q: {q:.2f}",
            f"📊 R: {r:.2f}",
            f"⚖️ Equilibrio: {equilibrio:.2f}%",
            f"⚠️ Desequilibrio: {desequilibrio:.2f}%",
            f"🎯 Estrutura: {classificacao or 'NAO CLASSIFICADO'}",
            f"🧭 Padrao: {padrao or 'NAO CLASSIFICADO'}",
            f"📊 P(X): {prob_x:.2f}% | P(X) N: {prob_x_normalizada:.2f}%",
            "",
        ])

        if len("\n".join(linhas)) > TELEGRAM_MAX_CARACTERES:
            mensagens.append("\n".join(linhas[:-10]))
            linhas = novo_bloco()
            linhas.extend([
                f"📅 Data: {data}",
                f"⚽ {jogo.get('horario', '--:--')} | {jogo.get('casa', 'Casa')} x {jogo.get('fora', 'Fora')}",
                f"🏠 Casa {odd_casa:.2f} | 🤝 X {odd_empate:.2f} | 🚌 Visitante {odd_visitante:.2f}",
                f"📐 Q: {q:.2f}",
                f"📊 R: {r:.2f}",
                f"⚖️ Equilibrio: {equilibrio:.2f}%",
                f"⚠️ Desequilibrio: {desequilibrio:.2f}%",
                f"🎯 Estrutura: {classificacao or 'NAO CLASSIFICADO'}",
                f"🧭 Padrao: {padrao or 'NAO CLASSIFICADO'}",
                f"📊 P(X): {prob_x:.2f}% | P(X) N: {prob_x_normalizada:.2f}%",
                "",
            ])

    if len(linhas) > 7:
        linhas.extend([
            "────────────────────",
            f"📋 Jogos selecionados: {len(resultados)}",
            "",
            "🤖 IPM-RADAR-V5",
            "📚 Monitoramento estatistico pre-live.",
            "⚠️ Nao realiza apostas automaticamente.",
        ])
        mensagens.append("\n".join(linhas))

    return mensagens


def loop_consulta():
    print("🤖 IPM RADAR INICIADO")
    print(f"📐 Q: {Q_MIN:.2f} -> {Q_MAX:.2f}")
    print(f"⏱️ INTERVALO: {INTERVALO_RADAR}s")
    print(f"📈 VARIACAO MINIMA: {VARIACAO_MINIMA:.2f}%")
    print(f"📊 JANELA DE VARIACAO: {JANELA_VARIACAO_MINUTOS} minutos")
    print(f"⏳ CONFIRMACAO: {CONFIRMACAO_MINUTOS} minutos")

    while True:
        inicio = time.time()

        try:
            if horario_ativo():
                executar_pre_live()
                processar_live()
            else:
                print("⏸️ Radar em periodo de pausa.")

        except Exception as erro:
            print("❌ ERRO NO LOOP:", type(erro).__name__, erro)

        agora = time.time()
        proximo_ciclo = ((int(agora) // INTERVALO_RADAR) + 1) * INTERVALO_RADAR
        espera = max(1, proximo_ciclo - agora)

        print(f"⏱️ CICLO TERMINADO EM {agora - inicio:.1f}s | PROXIMO CICLO EM {espera:.0f}s")

        time.sleep(espera)


if __name__ == "__main__":
    iniciar_servidor_saude()
    loop_consulta()
