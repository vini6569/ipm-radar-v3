import json, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from config import *

REQUISICOES_REALIZADAS = 0
_IDS_LIVE_SELECIONADOS = []

def n(v,d=0.0):
    try: return d if v in (None,"") else float(v)
    except: return d

def i(v,d=0):
    try: return d if v in (None,"") else int(float(v))
    except: return d

def txt(v): return str(v or "").strip().lower()

def req(endpoint, params):
    global REQUISICOES_REALIZADAS
    url=f"{BASE_URL}/{endpoint.lstrip('/')}?{urllib.parse.urlencode(params)}"
    try:
        r=urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"IPM-Radar/5.2"}),timeout=TIMEOUT_REQUISICAO)
        REQUISICOES_REALIZADAS+=1
        print("HTTP STATUS ODDS API:",r.status)
        return json.loads(r.read().decode() or "[]")
    except urllib.error.HTTPError as e:
        REQUISICOES_REALIZADAS+=1
        print("ERRO HTTP ODDS API:",e.code)
        return []
    except Exception as e:
        print("ERRO ODDS API:",type(e).__name__,e)
        return []

def lista(r):
    if isinstance(r,list): return [x for x in r if isinstance(x,dict)]
    if not isinstance(r,dict): return []
    for k in ("events","data","results"):
        if isinstance(r.get(k),list): return [x for x in r[k] if isinstance(x,dict)]
    if r.get("id") is not None: return [r]
    return [x for x in r.values() if isinstance(x,dict) and x.get("id") is not None]

def w1xw2(a,b): return n(a)*n(b) if n(a)>0 and n(b)>0 else 0.0
def q(a,b):
    a,b=n(a),n(b)
    return 2*a*b/(a+b) if a>0 and b>0 else 0.0
def r(a,b):
    a,b=n(a),n(b)
    return max(a,b)/min(a,b) if a>0 and b>0 else 0.0

def minuto(j):
    c=j.get("clock")
    if isinstance(c,dict) and i(c.get("minute"),-1)>=0: return i(c.get("minute"))
    for v in (j.get("minute"),j.get("elapsed"),j.get("timer")):
        if isinstance(v,dict): v=v.get("minute",v.get("elapsed"))
        v=str(v).replace("'","").replace("min","").strip()
        if i(v,-1)>=0:return i(v)
    return 0

def data(j):
    v=j.get("date") or j.get("startTime") or j.get("start_time")
    try:
        d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except: return None

def buscar_jogos_pre_live():
    try:key=obter_api_key()
    except Exception as e: print("ERRO API KEY:",e); return []
    ev=lista(req("/events",{"apiKey":key,"sport":SPORT,"status":"pending","limit":100,"bookmaker":BOOKMAKER}))
    now=datetime.now(timezone.utc); lim=now.timestamp()+PRE_LIVE_JANELA_MINUTOS*60
    out=[e for e in ev if data(e) and now.timestamp()<=data(e).timestamp()<=lim]
    out.sort(key=lambda e:data(e) or now)
    out=out[:MAX_EVENTOS_POR_CONSULTA]
    print("JOGOS PRE-LIVE PROXIMOS:",len(out))
    return out

def buscar_odds_multiplos(eventos):
    if not eventos:return []
    try:key=obter_api_key()
    except Exception as e: print("ERRO API KEY:",e); return []
    ids=list(dict.fromkeys(str(e["id"]) for e in eventos if e.get("id") is not None))[:MAX_EVENTOS_POR_CONSULTA]
    out=[]
    for p in range(0,len(ids),10):
        bloco=ids[p:p+10]
        print(f"CONSULTA ODDS {p//10+1}: {len(bloco)} eventos")
        out+=lista(req("/odds/multi",{"apiKey":key,"eventIds":",".join(bloco),"bookmakers":BOOKMAKER}))
    print("EVENTOS COM ODDS RECEBIDOS:",len(out))
    return out

def _evento(odds,eid):
    for x in lista(odds):
        if str(x.get("id"))==str(eid):return x
    return None

def _mercados(e):
    b=e.get("bookmakers",{})
    if isinstance(b,dict):
        m=b.get(BOOKMAKER)
        if m is None:
            for k,v in b.items():
                if txt(k)==txt(BOOKMAKER):m=v;break
        return m.get("markets",[]) if isinstance(m,dict) else (m if isinstance(m,list) else [])
    if isinstance(b,list):
        for x in b:
            if txt(x.get("name") or x.get("title") or x.get("key"))==txt(BOOKMAKER):
                return x.get("markets",[])
    return []

def linhas(m): 
    v=m.get("odds",[]) if isinstance(m,dict) else []
    return [x for x in (v if isinstance(v,list) else [v]) if isinstance(x,dict)]

def preco(x):
    if isinstance(x,(int,float,str)):return n(x)
    if isinstance(x,dict):
        for k in ("price","value","odd","odds","decimal"):
            if n(x.get(k))>0:return n(x.get(k))
    return 0.0

def outcome(m,names):
    alvos={txt(x) for x in names}
    for x in linhas(m):
        nome=txt(x.get("name") or x.get("label") or x.get("outcome") or x.get("selection") or x.get("key"))
        if nome in alvos and preco(x)>0:return preco(x)
    return 0.0

def extrair_mercados(jogo,odds):
    e=_evento(odds,jogo.get("id")) or jogo
    ms=_mercados(e); casa=jogo.get("home") or jogo.get("homeTeam",""); fora=jogo.get("away") or jogo.get("awayTeam","")
    oc=oe=ov=0.0
    for m in ms:
        nome=txt(m.get("key") or m.get("name") or m.get("market") or m.get("type"))
        if nome in ("1x2","match","match winner","winner","fulltime result","result") or "1x2" in nome:
            oc=oc or outcome(m,("1","home","casa",casa))
            oe=oe or outcome(m,("x","draw","tie","empate"))
            ov=ov or outcome(m,("2","away","fora",fora))
    oc=oc or n(e.get("odd_casa") or e.get("homeOdd") or e.get("home_odd"))
    oe=oe or n(e.get("odd_empate") or e.get("drawOdd") or e.get("draw_odd"))
    ov=ov or n(e.get("odd_visitante") or e.get("awayOdd") or e.get("away_odd"))
    oo=ou=ol=ul=bs=bn=0.0
    for m in ms:
        name=txt(m.get("key") or m.get("name") or m.get("market") or m.get("type"))
        for x in linhas(m):
            nm=txt(x.get("name") or x.get("label") or x.get("outcome") or x.get("selection"))
            p=preco(x); line=n(x.get("line") or x.get("handicap") or x.get("total") or x.get("point"))
            if "total" in name or "over" in name:
                if "over" in nm and p>0: oo=oo or p; ol=ol or line
                if "under" in nm and p>0: ou=ou or p; ul=ul or line
            if "btts" in name or "both teams" in name:
                if nm in ("yes","sim","true"): bs=p
                if nm in ("no","não","nao","false"): bn=p
    return {"odd_casa":oc,"odd_empate":oe,"odd_visitante":ov,"w1":oc,"w2":ov,
            "w1xw2":round(w1xw2(oc,ov),4),"q":round(q(oc,ov),4),"r":round(r(oc,ov),4),
            "over_linha":ol,"under_linha":ul,"odd_over":oo,"odd_under":ou,
            "odd_btts_sim":bs,"odd_btts_nao":bn,"tem_1x2":oc>0 and oe>0 and ov>0,
            "tem_w1xw2":oc>0 and ov>0,"tem_totals":oo>0 or ou>0,"tem_btts":bs>0 or bn>0}
