# ============================================================
# ODDS API - IPM RADAR V5.2
# CASA / EMPATE / VISITANTE
# Q REAL + R + TOTALS + BTTS
# ============================================================

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from config import (
    BASE_URL, BOOKMAKER, SPORT,
    MAX_EVENTOS_POR_CONSULTA, TIMEOUT_REQUISICAO,
    obter_api_key, PRE_LIVE_JANELA_MINUTOS,
)

_IDS_LIVE_SELECIONADOS = []


def _num(v, d=0.0):
    try:
        return d if v in (None, "") else float(v)
    except (TypeError, ValueError):
        return d


def _int(v, d=0):
    try:
        return d if v in (None, "") else int(float(v))
    except (TypeError, ValueError):
        return d


def _texto(v):
    return str(v or "").strip().lower()


def _request(endpoint, params):
    url = f"{BASE_URL}/{endpoint.lstrip('/')}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "IPM-Radar/5.2", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_REQUISICAO) as resp:
            body = resp.read().decode("utf-8")
            print("HTTP STATUS ODDS API:", resp.status)
            return json.loads(body) if body else []
    except urllib.error.HTTPError as e:
        try:
            detalhe = e.read().decode("utf-8")
        except Exception:
            detalhe = ""
        print(f"ERRO HTTP ODDS API: {e.code} | {detalhe[:500]}")
    except (urllib.error.URLError, TimeoutError) as e:
        print("ERRO DE CONEXAO ODDS API:", e)
    except Exception as e:
        print("ERRO ODDS API:", type(e).__name__, e)
    return []


def _eventos(resposta):
    if isinstance(resposta, list):
        return [x for x in resposta if isinstance(x, dict)]
    if not isinstance(resposta, dict):
        return []
    for chave in ("events", "data", "results"):
        valor = resposta.get(chave)
        if isinstance(valor, list):
            return [x for x in valor if isinstance(x, dict)]
    if resposta.get("id") is not None:
        return [resposta]
    return [
        x for x in resposta.values()
        if isinstance(x, dict) and x.get("id") is not None
    ]


def _minuto(jogo):
    if not isinstance(jogo, dict):
        return 0
    clock = jogo.get("clock")
    if isinstance(clock, dict):
        m = _int(clock.get("minute"), -1)
        if m >= 0:
            return m
    for v in (jogo.get("minute"), jogo.get("elapsed"), jogo.get("timer")):
        if isinstance(v, dict):
            v = v.get("minute", v.get("elapsed"))
        if isinstance(v, str):
            v = v.replace("'", "").replace("min", "").strip()
        m = _int(v, -1)
        if m >= 0:
            return m
    return 0


def _placar(jogo):
    for v in (jogo.get("scores"), jogo.get("score"), jogo.get("result")):
        if isinstance(v, dict):
            h = v.get("home", v.get("homeScore"))
            a = v.get("away", v.get("awayScore"))
            if h is not None or a is not None:
                return _int(h), _int(a)
        elif isinstance(v, list) and len(v) >= 2:
            return _int(v[0]), _int(v[1])
    return _int(jogo.get("homeScore")), _int(jogo.get("awayScore"))


def _estatisticas(jogo):
    for chave in ("statistics", "stats", "matchStatistics"):
        v = jogo.get(chave)
        if isinstance(v, dict):
            campos = (
                v.get("corners"), v.get("shots"),
                v.get("dangerousAttacks"), v.get("cards")
            )
            if any(x is not None for x in campos):
                return tuple(_int(x) for x in campos)
    return 0, 0, 0, 0


def _data(evento):
    v = evento.get("date") or evento.get("startTime") or evento.get("start_time")
    if not v:
        return None
    try:
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)
    except Exception:
        return None


def buscar_jogos_ao_vivo():
    global _IDS_LIVE_SELECIONADOS
    try:
        key = obter_api_key()
    except Exception as e:
        print("ERRO API KEY:", e)
        return []

    eventos = _eventos(_request("/events/live", {"apiKey": key, "sport": SPORT}))
    mapa = {str(e["id"]): e for e in eventos if e.get("id") is not None}

    mantidos = [str(i) for i in _IDS_LIVE_SELECIONADOS if str(i) in mapa]
    restantes = [e for i, e in mapa.items() if i not in mantidos]
    restantes.sort(key=_minuto)

    vagas = max(0, MAX_EVENTOS_POR_CONSULTA - len(mantidos))
    mantidos.extend(str(e["id"]) for e in restantes[:vagas])
    _IDS_LIVE_SELECIONADOS = mantidos[:MAX_EVENTOS_POR_CONSULTA]

    selecionados = [mapa[i] for i in _IDS_LIVE_SELECIONADOS if i in mapa]
    print("JOGOS AO VIVO ENCONTRADOS:", len(eventos), "| SELECIONADOS:", len(selecionados))
    return selecionados


def buscar_jogos_ao_vivo_por_ids(ids):
    if not ids:
        print("LIVE POR IDS: nenhum ID recebido.")
        return []
    try:
        key = obter_api_key()
    except Exception as e:
        print("ERRO API KEY:", e)
        return []

    ids = list(dict.fromkeys(str(i) for i in ids if i is not None))
    eventos = _eventos(_request("/events/live", {"apiKey": key, "sport": SPORT}))
    mapa = {str(e["id"]): e for e in eventos if e.get("id") is not None}
    encontrados = [mapa[i] for i in ids if i in mapa]

    print(
        "LIVE POR IDS | SOLICITADOS=",
        len(ids), "| ENCONTRADOS=", len(encontrados)
    )
    return encontrados


def buscar_jogos_pre_live():
    try:
        key = obter_api_key()
    except Exception as e:
        print("ERRO API KEY:", e)
        return []

    resposta = _request("/events", {
        "apiKey": key,
        "sport": SPORT,
        "status": "pending",
        "limit": 100,
        "bookmaker": BOOKMAKER,
    })
    eventos = _eventos(resposta)
    agora = datetime.now(timezone.utc)
    limite = agora.timestamp() + PRE_LIVE_JANELA_MINUTOS * 60

    proximos = [
        e for e in eventos
        if _data(e) is not None
        and agora.timestamp() <= _data(e).timestamp() <= limite
    ]
    proximos.sort(key=lambda e: _data(e) or agora)
    proximos = proximos[:MAX_EVENTOS_POR_CONSULTA]
    print("JOGOS PRE-LIVE PROXIMOS:", len(proximos))
    return proximos


def buscar_odds_multiplos(eventos):
    if not eventos:
        print("ODDS MULTI: nenhum evento recebido.")
        return []
    try:
        key = obter_api_key()
    except Exception as e:
        print("ERRO API KEY:", e)
        return []

    ids = list(dict.fromkeys(
        str(e["id"]) for e in eventos
        if isinstance(e, dict) and e.get("id") is not None
    ))[:MAX_EVENTOS_POR_CONSULTA]

    resultados = []
    for inicio in range(0, len(ids), 10):
        bloco = ids[inicio:inicio + 10]
        print(f"CONSULTA ODDS {inicio // 10 + 1}: {len(bloco)} eventos | IDS={bloco}")
        resposta = _request("/odds/multi", {
            "apiKey": key,
            "eventIds": ",".join(bloco),
            "bookmakers": BOOKMAKER,
        })
        recebidos = _eventos(resposta)
        print("EVENTOS COM ODDS RECEBIDOS:", len(recebidos))
        resultados.extend(recebidos)
    return resultados


def _por_id(odds, event_id):
    if event_id is None:
        return None
    alvo = str(event_id)
    if isinstance(odds, list):
        return next((x for x in odds if isinstance(x, dict) and str(x.get("id")) == alvo), None)
    if isinstance(odds, dict):
        if str(odds.get("id")) == alvo:
            return odds
        return odds.get(alvo) if isinstance(odds.get(alvo), dict) else None
    return None


def _mercados(evento):
    if not isinstance(evento, dict):
        return []
    bookmakers = evento.get("bookmakers", {})
    alvo = BOOKMAKER.strip().lower()

    if isinstance(bookmakers, dict):
        m = bookmakers.get(BOOKMAKER)
        if m is None:
            for nome, valor in bookmakers.items():
                if _texto(nome) == alvo:
                    m = valor
                    break
        if isinstance(m, dict):
            m = m.get("markets", [])
        return m if isinstance(m, list) else []

    if isinstance(bookmakers, list):
        for b in bookmakers:
            if _texto(b.get("name") or b.get("title") or b.get("key")) == alvo:
                m = b.get("markets", [])
                return m if isinstance(m, list) else []
    return []


def _linhas(mercado):
    v = mercado.get("odds") if isinstance(mercado, dict) else None
    if isinstance(v, list):
        return [x for x in v if isinstance(x, dict)]
    if isinstance(v, dict):
        return [v]
    return []


def _preco(item):
    if not isinstance(item, dict):
        return _num(item)
    for k in ("price", "value", "odd", "odds", "decimal"):
        v = item.get(k)
        n = _num(v)
        if n > 0:
            return n
    return 0.0


def _outcome(linha, nomes):
    nomes = {_texto(x) for x in nomes}
    for chave in ("outcomes", "selections", "items", "options"):
        v = linha.get(chave)
        if isinstance(v, dict):
            v = list(v.values())
        if not isinstance(v, list):
            continue
        for item in v:
            if not isinstance(item, dict):
                continue
            nome = _texto(
                item.get("name") or item.get("label")
                or item.get("outcome") or item.get("selection")
                or item.get("key")
            )
            if nome in nomes:
                p = _preco(item)
                if p > 0:
                    return p

    for nome in nomes:
        for chave in (nome,):
            if chave in linha:
                p = _preco(linha[chave])
                if p > 0:
                    return p
    return 0.0


def _nome_mercado(m):
    return _texto(m.get("key") or m.get("name") or m.get("market") or m.get("type"))


def _extrair_1x2(mercados):
    for m in mercados:
        nome = _nome_mercado(m)
        if nome not in {
            "1x2", "ml", "moneyline", "match", "match winner",
            "match result", "full time result", "winner", "result"
        } and "1x2" not in nome:
            continue

        casa = empate = fora = 0.0
        for linha in _linhas(m):
            casa = casa or _outcome(linha, ("home", "1", "casa"))
            empate = empate or _outcome(linha, ("draw", "x", "tie", "empate"))
            fora = fora or _outcome(linha, ("away", "2", "fora"))
            if casa and empate and fora:
                return casa, empate, fora
    return 0.0, 0.0, 0.0


def _extrair_totals(mercados):
    over_linha = under_linha = odd_over = odd_under = 0.0
    for m in mercados:
        nome_m = _nome_mercado(m)
        if "total" not in nome_m and "over" not in nome_m:
            continue
        for linha in _linhas(m):
            nome = _texto(
                linha.get("name") or linha.get("label")
                or linha.get("outcome") or linha.get("selection")
            )
            p = _preco(linha)
            if p <= 0:
                continue
            ponto = _num(
                linha.get("line") or linha.get("handicap")
                or linha.get("total") or linha.get("point")
            )
            if "over" in nome:
                odd_over = odd_over or p
                over_linha = over_linha or ponto
            elif "under" in nome:
                odd_under = odd_under or p
                under_linha = under_linha or ponto
    return over_linha, under_linha, odd_over, odd_under


def _extrair_btts(mercados):
    sim = nao = 0.0
    for m in mercados:
        nome_m = _nome_mercado(m)
        if not any(x in nome_m for x in ("btts", "both teams", "both to score")):
            continue
        for linha in _linhas(m):
            nome = _texto(
                linha.get("name") or linha.get("label")
                or linha.get("outcome") or linha.get("selection")
            )
            p = _preco(linha)
            if nome in ("yes", "sim", "true"):
                sim = p
            elif nome in ("no", "nao", "não", "false"):
                nao = p
    return sim, nao


def extrair_mercados(jogo, odds):
    if not isinstance(jogo, dict):
        return {}

    evento = _por_id(odds, jogo.get("id")) or jogo
    mercados = _mercados(evento)

    casa, empate, fora = _extrair_1x2(mercados)

    # Q REAL usado pelo filtro do radar:
    # Q = 2 x Casa x Visitante / (Casa + Visitante)
    q = 2.0 * casa * fora / (casa + fora) if casa > 0 and fora > 0 else 0.0

    r = max(casa, fora) / min(casa, fora) if casa > 0 and fora > 0 else 0.0
    equilibrio = 100.0 / r if r > 0 else 0.0
    desequilibrio = 100.0 - equilibrio if r > 0 else 0.0

    over_linha, under_linha, odd_over, odd_under = _extrair_totals(mercados)
    btts_sim, btts_nao = _extrair_btts(mercados)
    ph, pf = _placar(jogo)
    esc, fin, atq, cart = _estatisticas(jogo)

    resultado = {
        "event_id": jogo.get("id"),
        "odd_home": casa,
        "odd_draw": empate,
        "odd_away": fora,
        "odd_casa": casa,
        "odd_empate": empate,
        "odd_visitante": fora,
        "odd_atual": empate,
        "odd_pre_live": q,
        "q": round(q, 4),
        "r": round(r, 4),
        "equilibrio_percentual": round(equilibrio, 2),
        "desequilibrio_percentual": round(desequilibrio, 2),
        "minuto": _minuto(jogo),
        "gols": ph + pf,
        "escanteios": esc,
        "cartoes": cart,
        "finalizacoes": fin,
        "ataques_perigosos": atq,
        "over_linha": over_linha,
        "under_linha": under_linha,
        "odd_over": odd_over,
        "odd_under": odd_under,
        "odd_btts_sim": btts_sim,
        "odd_btts_nao": btts_nao,
        "tem_1x2": casa > 0 and empate > 0 and fora > 0,
        "tem_totals": odd_over > 0 or odd_under > 0,
        "tem_btts": btts_sim > 0 or btts_nao > 0,
        "mercados_encontrados": [],
        "mercados_disponiveis": [],
        "todos": [],
        "odds_ft": [],
        "odds_ht": [],
        "odds_corners": [],
        "odds_cards": [],
    }

    for m in mercados:
        nome = str(m.get("name") or m.get("key") or "").strip()
        if not nome:
            continue
        item = {
            "name": nome,
            "updatedAt": m.get("updatedAt"),
            "odds": _linhas(m),
        }
        resultado["todos"].append(item)
        resultado["mercados_disponiveis"].append(nome)
        nl = nome.lower()
        if "half" in nl or "halftime" in nl or "1st half" in nl:
            destino = "odds_ht"
        elif "corner" in nl or "escante" in nl:
            destino = "odds_corners"
        elif "card" in nl or "booking" in nl or "cart" in nl:
            destino = "odds_cards"
        else:
            destino = "odds_ft"
        resultado[destino].append(item)

    resultado["mercados_disponiveis"] = list(dict.fromkeys(resultado["mercados_disponiveis"]))
    if resultado["tem_1x2"]:
        resultado["mercados_encontrados"].append("1X2")

    print(
        "ODDS 1X2 | ID=", jogo.get("id"),
        "| CASA=", casa, "| EMPATE=", empate,
        "| VISITANTE=", fora, "| Q=", round(q, 4)
    )
    return resultado


def limpar_memoria():
    global _IDS_LIVE_SELECIONADOS
    _IDS_LIVE_SELECIONADOS = []
