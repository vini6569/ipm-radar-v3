import json, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from config import BASE_URL, BOOKMAKER, SPORT, MAX_EVENTOS_POR_CONSULTA, TIMEOUT_REQUISICAO, obter_api_key
from motor_ipm import analisar_movimento

def _json(endpoint, params):
    url = f"{BASE_URL}/{endpoint.lstrip('/')}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent":"IPM-Radar/4.0","Accept":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_REQUISICAO) as r:
            print("HTTP STATUS ODDS API:", r.status)
            body = r.read().decode("utf-8")
        return json.loads(body) if body else []
    except urllib.error.HTTPError as e:
        try: detail = e.read().decode("utf-8")
        except Exception: detail = ""
        print(f"❌ ODDS API HTTP {e.code}: {detail[:1200]}")
    except Exception as e:
        print(f"❌ ODDS API: {type(e).__name__}: {e}")
    return []

def _lista(x):
    if isinstance(x, list): return x
    if not isinstance(x, dict): return []
    for k in ("events","data","results","response"):
        if isinstance(x.get(k), list): return x[k]
    return [x] if x.get("id") is not None else []

def buscar_jogos_ao_vivo():
    try: key = obter_api_key()
    except Exception as e:
        print("❌", e); return []
    eventos = _lista(_json("/events/live", {"apiKey":key,"sport":SPORT}))
    print("📡 JOGOS AO VIVO:", len(eventos))
    return eventos

def buscar_odds_multiplos(eventos):
    try: key = obter_api_key()
    except Exception as e:
        print("❌", e); return []
    ids = list(dict.fromkeys(str(e["id"]) for e in eventos if isinstance(e,dict) and e.get("id")))[:MAX_EVENTOS_POR_CONSULTA]
    if not ids: return []
    resposta = _json("/odds/multi", {"apiKey":key,"eventIds":",".join(ids),"bookmakers":BOOKMAKER})
    result = _lista(resposta)
    if not result and isinstance(resposta,dict):
        result = [v for v in resposta.values() if isinstance(v,dict) and v.get("id") is not None]
    print("📊 EVENTOS COM ODDS:", len(result))
    return result

def _evento(odds, event_id):
    alvo = str(event_id)
    if isinstance(odds,list):
        return next((x for x in odds if isinstance(x,dict) and str(x.get("id"))==alvo), None)
    if isinstance(odds,dict):
        if str(odds.get("id")) == alvo: return odds
        if isinstance(odds.get(alvo),dict): return odds[alvo]
    return None

def _mercados(evento):
    b = evento.get("bookmakers",{}) if isinstance(evento,dict) else {}
    if isinstance(b,dict):
        m = b.get(BOOKMAKER)
        if m is None:
            m = next((v for k,v in b.items() if str(k).lower()==BOOKMAKER.lower()), [])
        return m if isinstance(m,list) else []
    if isinstance(b,list):
        for x in b:
            if isinstance(x,dict) and str(x.get("name","")).lower()==BOOKMAKER.lower():
                return x.get("markets",[]) if isinstance(x.get("markets",[]),list) else []
    return []

def _periodo(nome, mercado):
    s = " ".join(str(mercado.get(k,"")) for k in ("name","period","scope","description")).lower()
    if any(x in s for x in ("half time","half-time","halftime","1st half","first half"," 1h"," ht")):
        return "HT"
    return "FT"

def _linha(o):
    for k in ("hdp","line","point","total","handicap"):
        if o.get(k) is not None: return str(o[k])
    return ""

def _valor(v):
    try:
        v=float(v)
        return v if v>0 else None
    except (TypeError,ValueError): return None

def _outcomes(o):
    if not isinstance(o,dict): return []
    for k in ("odd","price"):
        v=_valor(o.get(k))
        if v: return [(str(o.get("name",o.get("selection",k))),_linha(o),v)]
    out=[]
    for k in ("home","draw","away","over","under","yes","no","1X","12","X2","Home","Draw","Away","Over","Under","Yes","No"):
        v=_valor(o.get(k))
        if v: out.append((k,_linha(o),v))
    return out

def _minuto(j):
    for k in ("minute","elapsed","timer","clock"):
        v=j.get(k)
        if isinstance(v,dict): v=v.get("minute",v.get("elapsed"))
        try:
            v=int(float(v))
            if v>=0: return v
        except (TypeError,ValueError): pass
    return 0

def _placar(j):
    s=j.get("score",{})
    if isinstance(s,dict):
        try: return int(float(s.get("home",0) or 0)), int(float(s.get("away",0) or 0))
        except (TypeError,ValueError): pass
    return 0,0

def extrair_mercados(jogo, odds):
    eid=jogo.get("id")
    evento=_evento(odds,eid) or jogo
    mercados=_mercados(evento)
    r={"event_id":eid,"timestamp_utc":datetime.now(timezone.utc).isoformat(),
       "minuto":_minuto(jogo),"placar":dict(zip(("home","away"),_placar(jogo))),
       "bookmaker":BOOKMAKER,"HT":[],"FT":[],"OUTROS":[],"todos":[],"nomes_mercados":[]}
    for m in mercados:
        if not isinstance(m,dict): continue
        nome=str(m.get("name","UNKNOWN")).strip()
        periodo=_periodo(nome,m)
        if nome not in r["nomes_mercados"]: r["nomes_mercados"].append(nome)
        for o in m.get("odds",[]) if isinstance(m.get("odds",[]),list) else [m.get("odds",{})]:
            for selecao,linha,odd in _outcomes(o):
                mov=analisar_movimento(eid,periodo,nome,linha,selecao,odd)
                item={"mercado":nome,"periodo":periodo,"linha":linha,"selecao":selecao,"odd":odd,
                      "updated_at":m.get("updatedAt") or m.get("updated_at"),**mov}
                r["todos"].append(item); r[periodo].append(item) if periodo in ("HT","FT") else r["OUTROS"].append(item)
    return r
