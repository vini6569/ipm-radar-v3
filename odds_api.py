import json
import urllib.error
import urllib.parse
import urllib.request

from config import BASE_URL, BOOKMAKER, MAX_EVENTOS_POR_CONSULTA, TIMEOUT_REQUISICAO, SPORT, obter_api_key

_ODD_INICIAL = {}
_ODD_ANTERIOR = {}

def _request_json(endpoint, params):
    url = f"{BASE_URL}/{endpoint.lstrip('/')}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "IPM-Radar/3.0",
                                                "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_REQUISICAO) as resp:
            body = resp.read().decode("utf-8")
            print("HTTP STATUS ODDS API:", resp.status)
            return json.loads(body) if body else []
    except urllib.error.HTTPError as e:
        detalhe = ""
        try: detalhe = e.read().decode("utf-8")
        except Exception: pass
        print(f"❌ ERRO HTTP ODDS API: {e.code} | {detalhe[:1000]}")
        return []
    except urllib.error.URLError as e:
        print("❌ ERRO DE CONEXÃO ODDS API:", e)
        return []
    except Exception as e:
        print(f"❌ ERRO ODDS API: {type(e).__name__}: {e}")
        return []

def _lista_eventos(resposta):
    if isinstance(resposta, list): return resposta
    if not isinstance(resposta, dict): return []
    for chave in ("events", "data", "results"):
        if isinstance(resposta.get(chave), list): return resposta[chave]
    return [resposta] if resposta.get("id") is not None else []

def buscar_jogos_ao_vivo():
    try: key = obter_api_key()
    except Exception as e:
        print("❌ ERRO API KEY:", e); return []
    print("=" * 60)
    print("📡 CONSULTANDO JOGOS AO VIVO")
    eventos = _lista_eventos(_request_json("/events/live", {"apiKey": key, "sport": SPORT}))
    print("JOGOS AO VIVO ENCONTRADOS:", len(eventos))
    for e in eventos[:MAX_EVENTOS_POR_CONSULTA]:
        if isinstance(e, dict):
            print(f"  {e.get('id')} | {e.get('home')} x {e.get('away')} | {e.get('status')}")
    return eventos

def buscar_odds_multiplos(eventos):
    if not eventos: return []
    try: key = obter_api_key()
    except Exception as e:
        print("❌ ERRO API KEY:", e); return []
    ids = list(dict.fromkeys(str(e["id"]) for e in eventos
                            if isinstance(e, dict) and e.get("id") is not None))
    ids = ids[:MAX_EVENTOS_POR_CONSULTA]
    if not ids: return []
    print("📊 CONSULTANDO ODDS |", len(ids), "|", BOOKMAKER)
    resposta = _request_json("/odds/multi", {
        "apiKey": key, "eventIds": ",".join(ids), "bookmakers": BOOKMAKER})
    eventos_odds = _lista_eventos(resposta)
    if not eventos_odds and isinstance(resposta, dict):
        eventos_odds = [v for v in resposta.values()
                        if isinstance(v, dict) and v.get("id") is not None]
    print("EVENTOS COM ODDS RECEBIDOS:", len(eventos_odds))
    return eventos_odds

def _evento_odds_por_id(odds, event_id):
    alvo = str(event_id)
    if isinstance(odds, list):
        for item in odds:
            if isinstance(item, dict) and str(item.get("id")) == alvo: return item
    if isinstance(odds, dict):
        if str(odds.get("id")) == alvo: return odds
        if isinstance(odds.get(alvo), dict): return odds[alvo]
    return None

def _mercados_bet365(evento):
    b = evento.get("bookmakers", {}) if isinstance(evento, dict) else {}
    m = b.get(BOOKMAKER, []) if isinstance(b, dict) else []
    return m if isinstance(m, list) else []

def _primeiro_odds(mercado):
    odds = mercado.get("odds") if isinstance(mercado, dict) else None
    if isinstance(odds, list) and odds and isinstance(odds[0], dict): return odds[0]
    return odds if isinstance(odds, dict) else {}

def _encontrar_mercado(mercados, nomes):
    nomes = {str(n).strip().lower() for n in nomes}
    for m in mercados:
        if isinstance(m, dict) and str(m.get("name", "")).strip().lower() in nomes: return m
    return None

def _numero(v, padrao=0.0):
    try: return padrao if v in (None, "") else float(v)
    except (TypeError, ValueError): return padrao

def _inteiro(v, padrao=0):
    try: return padrao if v in (None, "") else int(float(v))
    except (TypeError, ValueError): return padrao

def _extrair_minuto(jogo):
    for chave in ("minute", "elapsed", "timer", "clock"):
        v = jogo.get(chave)
        if isinstance(v, dict): v = v.get("minute", v.get("elapsed"))
        if isinstance(v, str): v = v.replace("'", "").replace("min", "").strip()
        n = _inteiro(v, -1)
        if n >= 0: return n
    return 0

def extrair_mercados(jogo, odds):
    event_id = jogo.get("id")
    evento = _evento_odds_por_id(odds, event_id) or jogo
    mercados = _mercados_bet365(evento)
    r = {"event_id": event_id, "odd_home": 0.0, "odd_draw": 0.0, "odd_away": 0.0,
         "odd_atual": 0.0, "odd_anterior": 0.0, "odd_inicial": 0.0,
         "variacao_desde_inicio": 0.0, "variacao_recente": 0.0,
         "minuto": _extrair_minuto(jogo), "mercados_encontrados": [],
         "mercados_disponiveis": []}
    ml = _encontrar_mercado(mercados, ("ML", "Moneyline", "1X2"))
    if ml:
        linha = _primeiro_odds(ml)
        r["odd_home"] = _numero(linha.get("home"))
        r["odd_draw"] = _numero(linha.get("draw"))
        r["odd_away"] = _numero(linha.get("away"))
        r["odd_atual"] = r["odd_draw"]
        r["mercados_encontrados"].append("ML")
    r["mercados_disponiveis"] = list(dict.fromkeys(str(m.get("name"))
        for m in mercados if isinstance(m, dict) and m.get("name")))
    atual = r["odd_atual"]
    anterior = _ODD_ANTERIOR.get(event_id, 0.0)
    inicial = _ODD_INICIAL.get(event_id, atual)
    if event_id is not None and atual > 0:
        if event_id not in _ODD_INICIAL:
            _ODD_INICIAL[event_id] = atual
            inicial = atual
        if anterior > 0:
            r["variacao_recente"] = ((atual - anterior) / anterior) * 100.0
        r["variacao_desde_inicio"] = ((atual - inicial) / inicial) * 100.0
        _ODD_ANTERIOR[event_id] = atual
    r["odd_anterior"] = anterior
    r["odd_inicial"] = inicial
    print(f"📊 {event_id} | empate={atual} | variação={r['variacao_recente']:.2f}%")
    return r

def limpar_memoria():
    _ODD_INICIAL.clear()
    _ODD_ANTERIOR.clear()
    
