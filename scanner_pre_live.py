# ============================================================
# SCANNER PRÉ-LIVE - IPM RADAR V5.2
# Q + ESTRUTURA + TOTALS + BTTS
# ============================================================
from datetime import datetime, time

from config import FUSO_HORARIO, MAX_EVENTOS_POR_CONSULTA, PRE_LIVE_JANELA_MINUTOS, Q_MIN, Q_MAX
from odds_api import buscar_jogos_pre_live, buscar_odds_multiplos, extrair_mercados

def numero(v, p=0.0):
    try: return p if v in (None, "") else float(v)
    except (TypeError, ValueError): return p

def probabilidade_implicita(odd):
    odd = numero(odd)
    return 100.0 / odd if odd > 0 else 0.0

def probabilidade_normalizada(c, x, f):
    pc, px, pf = map(probabilidade_implicita, (c, x, f))
    total = pc + px + pf
    return px / total * 100 if total > 0 else 0.0

def calcular_q(c, f):
    c, f = numero(c), numero(f)
    return 2*c*f/(c+f) if c > 0 and f > 0 else 0.0

def calcular_r(c, f):
    c, f = numero(c), numero(f)
    return max(c, f)/min(c, f) if c > 0 and f > 0 else 0.0

def classificar_equilibrio(r):
    if r <= 0: return "SEM_DADOS"
    if r <= 1.20: return "EQUILÍBRIO MUITO ALTO"
    if r <= 1.50: return "EQUILÍBRIO ALTO"
    if r <= 1.80: return "EQUILÍBRIO MODERADO"
    if r <= 2.20: return "DESEQUILÍBRIO"
    return "DESEQUILÍBRIO ALTO"

def classificar_padrao(r):
    if r <= 0: return "SEM_DADOS"
    return "PADRÃO_EMPATE" if r <= 1.80 else "PADRÃO_GOL"

def converter_horario(e):
    v = e.get("date") or e.get("startTime") or e.get("start_time")
    if not v: return None
    try:
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=FUSO_HORARIO)
        return dt.astimezone(FUSO_HORARIO)
    except Exception:
        return None

def identificar_periodo(dt):
    h = dt.time()
    if time(6,0) <= h < time(12,0): return "06:00 - 12:00"
    if time(12,0) <= h < time(18,0): return "12:00 - 18:00"
    if h >= time(18,0): return "18:00 - 00:00"
    return "FORA_DA_JANELA"

def analisar_gols(m):
    oo, ou = numero(m.get("odd_over")), numero(m.get("odd_under"))
    bs, bn = numero(m.get("odd_btts_sim")), numero(m.get("odd_btts_nao"))
    po, pu = probabilidade_implicita(oo), probabilidade_implicita(ou)
    ps, pn = probabilidade_implicita(bs), probabilidade_implicita(bn)

    over_ok, btts_ok = oo > 0 and ou > 0, bs > 0 and bn > 0

    if not over_ok: os = "SEM TOTALS"
    elif po >= 60 and oo <= 1.70: os = "OVER FORTE"
    elif po >= 55 and oo <= 1.85: os = "OVER FAVORÁVEL"
    elif po >= 50 and oo <= 2.00: os = "OVER MODERADO"
    else: os = "OVER NEUTRO"

    if not btts_ok: bsx = "SEM BTTS"
    elif ps >= 60 and bs <= 1.70: bsx = "BTTS FORTE"
    elif ps >= 55 and bs <= 1.85: bsx = "BTTS FAVORÁVEL"
    elif ps >= 50 and bs <= 2.00: bsx = "BTTS MODERADO"
    else: bsx = "BTTS NEUTRO"

    pontos = (2 if os=="OVER FORTE" else 1 if os in ("OVER FAVORÁVEL","OVER MODERADO") else 0)
    pontos += (2 if bsx=="BTTS FORTE" else 1 if bsx in ("BTTS FAVORÁVEL","BTTS MODERADO") else 0)

    if pontos >= 4: estrutura = "ESTRUTURA MUITO FAVORÁVEL A GOLS"
    elif pontos >= 3: estrutura = "ESTRUTURA FAVORÁVEL A GOLS"
    elif pontos >= 2: estrutura = "ESTRUTURA MODERADA PARA GOLS"
    elif pontos == 1: estrutura = "ESTRUTURA FRACA PARA GOLS"
    else: estrutura = "SEM CONFIRMAÇÃO PRÉ-LIVE"

    return {
        "over_linha": numero(m.get("over_linha")), "under_linha": numero(m.get("under_linha")),
        "odd_over": oo, "odd_under": ou, "prob_over": po, "prob_under": pu,
        "odd_btts_sim": bs, "odd_btts_nao": bn, "prob_btts_sim": ps, "prob_btts_nao": pn,
        "over_status": os, "btts_status": bsx, "pontos_gol": pontos,
        "estrutura_gol": estrutura, "mercado_gol_disponivel": over_ok or btts_ok,
    }

def escanear_pre_live():
    print("\n" + "="*72)
    print("🧪 SCANNER PRÉ-LIVE | IPM RADAR V5.2")
    print("="*72)
    print(f"⏱️ JANELA: {PRE_LIVE_JANELA_MINUTOS} minutos")
    print(f"📐 Q REAL DO FILTRO: {Q_MIN:.2f} → {Q_MAX:.2f}")
    print("⚽ ANÁLISE: TOTALS + BTTS")
    print("="*72)

    jogos = buscar_jogos_pre_live() or []
    if not jogos:
        print("Nenhum jogo pré-live encontrado.")
        return []

    jogos = jogos[:MAX_EVENTOS_POR_CONSULTA]
    odds = buscar_odds_multiplos(jogos) or []

    resultados, validos, fora_q = [], 0, 0
    qmin = qmax = None

    for jogo in jogos:
        if not isinstance(jogo, dict) or jogo.get("id") is None: continue
        m = extrair_mercados(jogo, odds) or {}
        oc, ox, ov = map(lambda k: numero(m.get(k)), ("odd_casa","odd_empate","odd_visitante"))
        if min(oc, ox, ov) <= 0: continue
        validos += 1

        dt = converter_horario(jogo)
        if not dt or identificar_periodo(dt) == "FORA_DA_JANELA": continue

        q, r = calcular_q(oc, ov), calcular_r(oc, ov)
        qmin = q if qmin is None else min(qmin, q)
        qmax = q if qmax is None else max(qmax, q)

        casa = jogo.get("home") or jogo.get("homeTeam") or "Casa"
        fora = jogo.get("away") or jogo.get("awayTeam") or "Fora"
        print(f"🔎 Q | {dt:%H:%M} | {casa} x {fora} | Casa={oc:.2f} | Fora={ov:.2f} | Q={q:.4f}")

        if not Q_MIN <= q <= Q_MAX:
            fora_q += 1
            continue

        g = analisar_gols(m)
        resultados.append({
            "event_id": str(jogo["id"]), "data": dt.strftime("%d/%m/%Y"),
            "horario": dt.strftime("%H:%M"), "periodo": identificar_periodo(dt),
            "casa": casa, "fora": fora, "odd_casa": oc, "odd_empate": ox,
            "odd_visitante": ov, "q": round(q,4), "r": round(r,4),
            "odd_pre_live": round(q,4),
            "probabilidade_x": probabilidade_implicita(ox),
            "probabilidade_x_normalizada": probabilidade_normalizada(oc,ox,ov),
            "equilibrio": classificar_equilibrio(r), "indice_equilibrio": round(100/r,2),
            "equilibrio_percentual": round(100/r,2),
            "desequilibrio_percentual": round(100 - 100/r,2),
            "padrao": classificar_padrao(r), **g,
        })

    resultados.sort(key=lambda x: (-x["pontos_gol"], -x["q"], -x["r"], x["data"], x["horario"]))

    print("\n" + "="*72)
    print("📊 DIAGNÓSTICO PRÉ-LIVE")
    print("="*72)
    print(f"1X2 VÁLIDO: {validos}")
    print(f"Q MÍNIMO ENCONTRADO: {qmin:.4f}" if qmin is not None else "Q MÍNIMO: --")
    print(f"Q MÁXIMO ENCONTRADO: {qmax:.4f}" if qmax is not None else "Q MÁXIMO: --")
    print(f"FORA DO Q: {fora_q}")
    print(f"DENTRO DO Q {Q_MIN:.2f} → {Q_MAX:.2f}: {len(resultados)}")

    for j in resultados:
        print(f"🎯 {j['horario']} | {j['casa']} x {j['fora']} | Q={j['q']:.2f} | R={j['r']:.2f} | OVER={j['odd_over']:.2f} | BTTS={j['odd_btts_sim']:.2f} | PONTOS={j['pontos_gol']} | {j['estrutura_gol']}")
    return resultados
