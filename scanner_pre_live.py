from datetime import time
from config import FUSO_HORARIO,MAX_EVENTOS_POR_CONSULTA,PRE_LIVE_JANELA_MINUTOS,Q_MIN,Q_MAX
from odds_api import buscar_jogos_pre_live,buscar_odds_multiplos,extrair_mercados

def n(v,d=0.0):
    try:return d if v in (None,"") else float(v)
    except:return d
def pi(o): return 100/n(o) if n(o)>0 else 0
def px(a,x,b):
    p=[pi(a),pi(x),pi(b)];t=sum(p);return p[1]*100/t if t else 0
def eq(r):
    return "SEM_DADOS" if r<=0 else ("EQUILÍBRIO MUITO ALTO" if r<=1.2 else "EQUILÍBRIO ALTO" if r<=1.5 else "EQUILÍBRIO MODERADO" if r<=1.8 else "DESEQUILÍBRIO" if r<=2.2 else "DESEQUILÍBRIO ALTO")
def periodo(dt):
    h=dt.time()
    if time(6)<=h<time(12):return "06:00 - 12:00"
    if time(12)<=h<time(18):return "12:00 - 18:00"
    if h>=time(18) or h<time(0):return "18:00 - 00:00"
    return "FORA_DA_JANELA"
def gols(m):
    oo,ou=n(m.get("odd_over")),n(m.get("odd_under")); bs,bn=n(m.get("odd_btts_sim")),n(m.get("odd_btts_nao"))
    po,pu,pb,pn=pi(oo),pi(ou),pi(bs),pi(bn); pts=0
    os="SEM TOTALS" if not(oo>0 and ou>0) else "OVER FORTE" if po>=60 and oo<=1.7 else "OVER FAVORÁVEL" if po>=55 and oo<=1.85 else "OVER MODERADO" if po>=50 and oo<=2 else "OVER NEUTRO"
    bt="SEM BTTS" if not(bs>0 and bn>0) else "BTTS FORTE" if pb>=60 and bs<=1.7 else "BTTS FAVORÁVEL" if pb>=55 and bs<=1.85 else "BTTS MODERADO" if pb>=50 and bs<=2 else "BTTS NEUTRO"
    pts+=(2 if os=="OVER FORTE" else 1 if "FAVORÁVEL" in os or "MODERADO" in os else 0)
    pts+=(2 if bt=="BTTS FORTE" else 1 if "FAVORÁVEL" in bt or "MODERADO" in bt else 0)
    estrutura="ESTRUTURA MUITO FAVORÁVEL A GOLS" if pts>=4 else "ESTRUTURA FAVORÁVEL A GOLS" if pts>=3 else "ESTRUTURA MODERADA PARA GOLS" if pts>=2 else "ESTRUTURA FRACA PARA GOLS" if pts==1 else "SEM CONFIRMAÇÃO PRÉ-LIVE"
    return {**m,"prob_over":po,"prob_under":pu,"prob_btts_sim":pb,"prob_btts_nao":pn,"over_status":os,"btts_status":bt,"pontos_gol":pts,"estrutura_gol":estrutura,"mercado_gol_disponivel":oo>0 or ou>0 or bs>0 or bn>0}

def escanear_pre_live():
    print("\n"+"="*72+"\n🧪 SCANNER PRÉ-LIVE | IPM RADAR V5.2\n"+"="*72)
    print(f"⏱️ JANELA: {PRE_LIVE_JANELA_MINUTOS} minutos\n📐 Q REAL DO FILTRO: {Q_MIN:.2f} → {Q_MAX:.2f}\n⚽ ANÁLISE: TOTALS + BTTS\n"+"="*72)
    try:jogos=buscar_jogos_pre_live() or []
    except Exception as e:print("ERRO:",e);return []
    if not jogos:print("Nenhum jogo pré-live encontrado.");return []
    jogos=jogos[:MAX_EVENTOS_POR_CONSULTA]
    try:odds=buscar_odds_multiplos(jogos) or []
    except Exception as e:print("ERRO ODDS:",e);odds=[]
    print(f"JOGOS PRÉ-LIVE ENCONTRADOS: {len(jogos)}\nODDS RECEBIDAS: {len(odds)}\n")
    out=[]; validos=0; fora=0; qmin=qmax=None
    for j in jogos:
        if not isinstance(j,dict) or j.get("id") is None:continue
        m=extrair_mercados(j,odds); a,x,b=n(m.get("odd_casa")),n(m.get("odd_empate")),n(m.get("odd_visitante"))
        if min(a,x,b)<=0:continue
        validos+=1; dt=__import__("odds_api").data(j)
        if not dt or periodo(dt)=="FORA_DA_JANELA":continue
        q=m["q"]; rr=m["r"]; qmin=q if qmin is None else min(qmin,q); qmax=q if qmax is None else max(qmax,q)
        casa=j.get("home") or j.get("homeTeam","Casa"); fora_nome=j.get("away") or j.get("awayTeam","Fora")
        print(f"🔎 Q | {dt.astimezone(FUSO_HORARIO).strftime('%H:%M')} | {casa} x {fora_nome} | Casa={a:.2f} | Fora={b:.2f} | Q={q:.4f}")
        if not Q_MIN<=q<=Q_MAX:fora+=1;continue
        g=gols(m);out.append({"event_id":str(j["id"]),"data":dt.astimezone(FUSO_HORARIO).strftime("%d/%m/%Y"),"horario":dt.astimezone(FUSO_HORARIO).strftime("%H:%M"),"periodo":periodo(dt.astimezone(FUSO_HORARIO)),"casa":casa,"fora":fora_nome,"odd_casa":a,"odd_empate":x,"odd_visitante":b,"q":q,"r":rr,"probabilidade_x":pi(x),"probabilidade_x_normalizada":px(a,x,b),"equilibrio":eq(rr),"indice_equilibrio":100/rr if rr else 0,"padrao":"PADRÃO_EMPATE" if rr<=1.8 else "PADRÃO_GOL",**g,"radar":True})
    out.sort(key=lambda z:(-z["pontos_gol"],-z["q"],-z["r"],z["horario"]))
    print("\n"+"="*72+"\n📊 DIAGNÓSTICO PRÉ-LIVE\n"+"="*72)
    print(f"1X2 VÁLIDO: {validos}\nQ MÍNIMO ENCONTRADO: {qmin:.4f}" if qmin is not None else "Q MÍNIMO: --")
    print(f"Q MÁXIMO ENCONTRADO: {qmax:.4f}" if qmax is not None else "Q MÁXIMO: --")
    print(f"FORA DO Q: {fora}\nDENTRO DO Q {Q_MIN:.2f} → {Q_MAX:.2f}: {len(out)}")
    for j in out:print(f"🎯 {j['horario']} | {j['casa']} x {j['fora']} | Q={j['q']:.2f} | R={j['r']:.2f} | OVER={j['odd_over']:.2f} | BTTS={j['odd_btts_sim']:.2f} | PONTOS={j['pontos_gol']} | {j['estrutura_gol']}")
    return out
