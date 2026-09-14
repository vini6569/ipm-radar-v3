# ============================================================
# MONITOR LIVE - IPM RADAR V5.2
# ODD X: variação de 20% em 10 min + confirmação em 5 min
# ============================================================
import time
from odds_api import buscar_jogos_ao_vivo_por_ids, buscar_odds_multiplos, extrair_mercados
from telegram import enviar_mensagem

VARIACAO_MINIMA = 20.0
JANELA_VARIACAO = 10
CONFIRMACAO_MINUTOS = 5

MONITORADOS = {}

def num(v, p=0.0):
    try: return p if v in (None,"") else float(v)
    except (TypeError,ValueError): return p

def registrar_jogos(jogos):
    agora = time.time()
    for j in jogos:
        eid = j.get("event_id")
        if eid is None: continue
        eid = str(eid)
        if eid not in MONITORADOS:
            MONITORADOS[eid] = {
                "event_id": eid, "casa": j.get("casa","Casa"), "fora": j.get("fora","Fora"),
                "q": num(j.get("q")), "historico": [], "sinal": None, "confirmado": False,
                "criado": agora,
            }
        else:
            MONITORADOS[eid]["casa"] = j.get("casa", MONITORADOS[eid]["casa"])
            MONITORADOS[eid]["fora"] = j.get("fora", MONITORADOS[eid]["fora"])

def registrar_x(eid, x):
    x = num(x)
    if x <= 0 or str(eid) not in MONITORADOS: return
    jogo = MONITORADOS[str(eid)]
    agora = time.time()
    jogo["historico"].append({"t": agora, "x": x})
    limite = agora - (JANELA_VARIACAO + 2)*60
    jogo["historico"] = [p for p in jogo["historico"] if p["t"] >= limite]
    print(f"ODD X | ID={eid} | X={x:.2f} | HIST={len(jogo['historico'])}")

def base_10(eid):
    jogo = MONITORADOS.get(str(eid))
    if not jogo: return 0.0
    alvo = time.time() - JANELA_VARIACAO*60
    pontos = [p for p in jogo["historico"] if p["t"] <= alvo]
    return num(max(pontos, key=lambda p:p["t"])["x"]) if pontos else 0.0

def variacao(base, atual):
    return (num(atual)-num(base))/num(base)*100 if num(base)>0 and num(atual)>0 else 0.0

def direcao(v):
    if v >= VARIACAO_MINIMA: return "POSITIVO"
    if v <= -VARIACAO_MINIMA: return "NEGATIVO"
    return None

def verificar_sinal(eid, minuto, x):
    jogo = MONITORADOS.get(str(eid))
    if not jogo or jogo["sinal"] or jogo["confirmado"]: return
    base = base_10(eid)
    if base <= 0:
        print(f"AGUARDANDO 10 MIN | {jogo['casa']} x {jogo['fora']}")
        return
    v, d = variacao(base,x), direcao(variacao(base,x))
    print(f"VAR 10 MIN | {jogo['casa']} x {jogo['fora']} | BASE={base:.2f} ATUAL={x:.2f} VAR={v:+.2f}%")
    if d:
        jogo["sinal"] = {"t":time.time(),"min":minuto,"base":base,"x":x,"var":v,"dir":d}
        print(f"PRIMEIRO SINAL | {jogo['casa']} x {jogo['fora']} | {d} | {v:+.2f}%")

def verificar_confirmacao(eid, minuto, x):
    jogo = MONITORADOS.get(str(eid))
    if not jogo or not jogo["sinal"] or jogo["confirmado"]: return None
    s = jogo["sinal"]
    if time.time()-s["t"] < CONFIRMACAO_MINUTOS*60:
        return None
    v, d = variacao(s["base"],x), direcao(variacao(s["base"],x))
    print(f"CONFIRMACAO 5 MIN | {jogo['casa']} x {jogo['fora']} | VAR={v:+.2f}%")
    if d != s["dir"]:
        print(f"SINAL NAO CONFIRMADO | {jogo['casa']} x {jogo['fora']}")
        jogo["sinal"] = None
        return None
    jogo["confirmado"] = True
    return {"casa":jogo["casa"],"fora":jogo["fora"],"minuto":minuto,"direcao":d,
            "base":s["base"],"x":x,"var1":s["var"],"var2":v}

def formatar_confirmacao(d):
    return (
        "🤖 PRE-ENTRADA CONFIRMADA\n\n"
        f"⚽ {d['casa']} x {d['fora']}\n"
        f"⏱️ Minuto: {d['minuto']}'\n\n"
        "📈 ODD X\n"
        f"📉 Base 10 min: {d['base']:.2f}\n"
        f"📊 Atual: {d['x']:.2f}\n"
        f"🔹 Primeiro sinal: {d['var1']:+.2f}%\n"
        f"🔹 Confirmação: {d['var2']:+.2f}%\n"
        f"🧭 Direção: {d['direcao']}\n\n"
        "🧪 LABORATÓRIO IPM\n"
        "📌 Sinal estatístico para observação."
    )

def processar_live():
    ids = list(MONITORADOS)
    if not ids:
        print("LIVE | Nenhum jogo no radar.")
        return

    jogos_live = buscar_jogos_ao_vivo_por_ids(ids) or []
    mapa = {str(j["id"]):j for j in jogos_live if isinstance(j,dict) and j.get("id") is not None}
    eventos = [
        mapa.get(eid, {"id":eid,"home":MONITORADOS[eid]["casa"],"away":MONITORADOS[eid]["fora"]})
        for eid in ids
    ]
    odds = buscar_odds_multiplos(eventos) or []
    if not odds:
        print("LIVE | Nenhuma odds recebida.")
        return

    leituras = 0
    for eid in ids:
        evento = mapa.get(eid, eventos[ids.index(eid)])
        m = extrair_mercados(evento, odds) or {}
        x = num(m.get("odd_empate", m.get("odd_draw")))
        if x <= 0:
            print(f"ODD X NAO ENCONTRADA | ID={eid}")
            continue
        minuto = int(num(m.get("minuto")))
        print(f"LIVE | {MONITORADOS[eid]['casa']} x {MONITORADOS[eid]['fora']} | MIN={minuto}' | X={x:.2f}")
        registrar_x(eid,x)
        verificar_sinal(eid,minuto,x)
        confirmado = verificar_confirmacao(eid,minuto,x)
        if confirmado: enviar_mensagem(formatar_confirmacao(confirmado))
        leituras += 1
    print(f"LIVE | LEITURAS={leituras}")
