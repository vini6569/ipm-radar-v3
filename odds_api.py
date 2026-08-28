# ============================================================
# ODDS API - IPM RADAR V4.3
# ============================================================

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from config import (
    BASE_URL, BOOKMAKER, SPORT, MAX_EVENTOS_POR_CONSULTA,
    TIMEOUT_REQUISICAO, obter_api_key, PRE_LIVE_JANELA_MINUTOS,
)


def _request_json(endpoint, params):
    url = f"{BASE_URL}/{endpoint.lstrip('/')}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "IPM-Radar/4.3", "Accept": "application/json"},
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
        print(f"❌ ERRO HTTP ODDS API: {e.code} | {detalhe[:500]}")
        return []
    except (urllib.error.URLError, TimeoutError) as e:
        print("❌ ERRO DE CONEXÃO ODDS API:", e)
        return []
    except Exception as e:
        print(f"❌ ERRO ODDS API: {type(e).__name__}: {e}")
        return []


def _lista_eventos(resposta):
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
    return [v for v in resposta.values() if isinstance(v, dict) and v.get("id") is not None]


def buscar_jogos_ao_vivo():
    try:
        key = obter_api_key()
    except Exception as e:
        print("❌ ERRO API KEY:", e)
        return []
    resposta = _request_json("/events/live", {"apiKey": key, "sport": SPORT})
    eventos = _lista_eventos(resposta)
    print("JOGOS AO VIVO ENCONTRADOS:", len(eventos))
    return eventos


def _parse_data_evento(evento):
    valor = evento.get("date") or evento.get("startTime") or evento.get("start_time")
    if not valor:
        return None
    try:
        texto = str(valor).replace("Z", "+00:00")
        dt = datetime.fromisoformat(texto)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def buscar_jogos_pre_live():
    """Busca partidas pendentes próximas do início para capturar a odd pré-live."""
    try:
        key = obter_api_key()
    except Exception as e:
        print("❌ ERRO API KEY:", e)
        return []

    resposta = _request_json(
        "/events",
        {
            "apiKey": key,
            "sport": SPORT,
            "status": "pending",
            "limit": 100,
            "bookmaker": BOOKMAKER,
        },
    )
    eventos = _lista_eventos(resposta)
    agora = datetime.now(timezone.utc)
    limite = agora.timestamp() + PRE_LIVE_JANELA_MINUTOS * 60
    proximos = []
    for evento in eventos:
        dt = _parse_data_evento(evento)
        if dt is None:
            continue
        ts = dt.timestamp()
        if agora.timestamp() <= ts <= limite:
            proximos.append(evento)
    proximos.sort(key=lambda e: (_parse_data_evento(e) or agora))
    proximos = proximos[:MAX_EVENTOS_POR_CONSULTA]
    print("⏳ JOGOS PRÉ-LIVE PRÓXIMOS:", len(proximos))
    return proximos


def buscar_odds_multiplos(eventos):
    if not eventos:
        return []
    try:
        key = obter_api_key()
    except Exception as e:
        print("❌ ERRO API KEY:", e)
        return []
    ids = []
    for e in eventos:
        if isinstance(e, dict) and e.get("id") is not None:
            ids.append(str(e["id"]))
    ids = list(dict.fromkeys(ids))[:MAX_EVENTOS_POR_CONSULTA]
    if not ids:
        return []
    resposta = _request_json(
        "/odds/multi",
        {"apiKey": key, "eventIds": ",".join(ids), "bookmakers": BOOKMAKER},
    )
    eventos_odds = _lista_eventos(resposta)
    print("EVENTOS COM ODDS RECEBIDOS:", len(eventos_odds))
    return eventos_odds


def _numero(valor, padrao=0.0):
    try:
        return padrao if valor in (None, "") else float(valor)
    except (TypeError, ValueError):
        return padrao


def _inteiro(valor, padrao=0):
    try:
        return padrao if valor in (None, "") else int(float(valor))
    except (TypeError, ValueError):
        return padrao


def _evento_odds_por_id(odds, event_id):
    if event_id is None:
        return None
    alvo = str(event_id)
    if isinstance(odds, list):
        for item in odds:
            if isinstance(item, dict) and str(item.get("id")) == alvo:
                return item
    if isinstance(odds, dict):
        if str(odds.get("id")) == alvo:
            return odds
        item = odds.get(alvo)
        if isinstance(item, dict):
            return item
    return None


def _mercados_bet365(evento):
    if not isinstance(evento, dict):
        return []
    bookmakers = evento.get("bookmakers", {})
    if isinstance(bookmakers, dict):
        mercados = bookmakers.get(BOOKMAKER)
        if isinstance(mercados, dict):
            mercados = mercados.get("markets", [])
        if mercados is None:
            for nome, valor in bookmakers.items():
                if str(nome).strip().lower() == BOOKMAKER.strip().lower():
                    mercados = valor
                    break
        if isinstance(mercados, dict):
            mercados = mercados.get("markets", [])
        return mercados if isinstance(mercados, list) else []
    if isinstance(bookmakers, list):
        for bookmaker in bookmakers:
            if not isinstance(bookmaker, dict):
                continue
            nome = str(bookmaker.get("name", "")).strip().lower()
            if nome == BOOKMAKER.strip().lower():
                mercados = bookmaker.get("markets", [])
                return mercados if isinstance(mercados, list) else []
    return []


def _primeiro_odds(mercado):
    if not isinstance(mercado, dict):
        return {}
    valores = mercado.get("odds")
    if isinstance(valores, list):
        return valores[0] if valores and isinstance(valores[0], dict) else {}
    return valores if isinstance(valores, dict) else {}


def _linhas_odds(mercado):
    if not isinstance(mercado, dict):
        return []
    valores = mercado.get("odds")
    if isinstance(valores, list):
        return [x for x in valores if isinstance(x, dict)]
    return [valores] if isinstance(valores, dict) else []


def _encontrar_mercado(mercados, nomes):
    nomes = {str(n).strip().lower() for n in nomes}
    for mercado in mercados:
        if not isinstance(mercado, dict):
            continue
        if str(mercado.get("name", "")).strip().lower() in nomes:
            return mercado
    return None


def _nome_normalizado(nome):
    return str(nome or "").strip().lower().replace("_", " ").replace("-", " ")


def _eh_ht(nome):
    n = _nome_normalizado(nome)
    return any(t in n for t in (
        "half time", "halftime", "1st half", "first half",
        "1h", "ht result", "ht totals", "half time result"
    ))


def _categoria_mercado(nome):
    n = _nome_normalizado(nome)
    if _eh_ht(nome):
        return "HT"
    if "corner" in n or "escante" in n:
        return "CORNERS"
    if "card" in n or "cartão" in n or "cartoes" in n or "booking" in n:
        return "CARDS"
    return "FT"


def _extrair_placar(jogo):
    for valor in (jogo.get("score"), jogo.get("scores"), jogo.get("result")):
        if isinstance(valor, dict):
            casa = valor.get("home", valor.get("homeScore"))
            fora = valor.get("away", valor.get("awayScore"))
            if casa is not None or fora is not None:
                return _inteiro(casa), _inteiro(fora)
        elif isinstance(valor, list) and len(valor) >= 2:
            return _inteiro(valor[0]), _inteiro(valor[1])
    return _inteiro(jogo.get("homeScore")), _inteiro(jogo.get("awayScore"))


def _extrair_minuto(jogo):
    for valor in (jogo.get("minute"), jogo.get("elapsed"), jogo.get("timer"), jogo.get("clock")):
        if isinstance(valor, dict):
            valor = valor.get("minute", valor.get("elapsed"))
        if isinstance(valor, str):
            valor = valor.replace("'", "").replace("min", "").strip()
        minuto = _inteiro(valor, -1)
        if minuto >= 0:
            return minuto
    return 0


def _extrair_estatisticas(jogo):
    for chave in ("statistics", "stats", "matchStatistics"):
        fonte = jogo.get(chave)
        if isinstance(fonte, dict):
            esc = fonte.get("corners")
            fin = fonte.get("shots")
            atq = fonte.get("dangerousAttacks")
            if esc is not None or fin is not None or atq is not None:
                return _inteiro(esc), _inteiro(fin), _inteiro(atq)
    return 0, 0, 0


def _copiar_mercado(mercado):
    return {
        "name": mercado.get("name", ""),
        "updatedAt": mercado.get("updatedAt"),
        "odds": _linhas_odds(mercado),
    }


def extrair_mercados(jogo, odds):
    if not isinstance(jogo, dict):
        return {}

    event_id = jogo.get("id")
    evento = _evento_odds_por_id(odds, event_id) or jogo
    mercados = _mercados_bet365(evento)
    casa, fora = _extrair_placar(jogo)
    esc, fin, atq = _extrair_estatisticas(jogo)

    resultado = {
        "event_id": event_id,
        "odd_home": 0.0, "odd_draw": 0.0, "odd_away": 0.0,
        "odd_atual": 0.0, "odd_pre_live": 0.0,
        "over_linha": 0.0, "under_linha": 0.0,
        "odd_over": 0.0, "odd_under": 0.0,
        "odd_btts_sim": 0.0, "odd_btts_nao": 0.0,
        "handicap_linha": 0.0,
        "odd_handicap_home": 0.0, "odd_handicap_away": 0.0,
        "odd_1x": 0.0, "odd_12": 0.0, "odd_x2": 0.0,
        "odd_dnb_home": 0.0, "odd_dnb_away": 0.0,
        "minuto": _extrair_minuto(jogo),
        "gols": casa + fora,
        "escanteios": esc, "finalizacoes": fin, "ataques_perigosos": atq,
        "mercados_encontrados": [], "mercados_disponiveis": [],
        "todos": [], "odds_ft": [], "odds_ht": [],
        "odds_corners": [], "odds_cards": [],
    }

    # ========================================================
    # BLOCO DE MERCADOS + DEBUG
    # ========================================================
    for mercado in mercados:
        if not isinstance(mercado, dict):
            continue
        nome = str(mercado.get("name", "")).strip()
        if not nome:
            continue
        item = _copiar_mercado(mercado)
        item["categoria"] = _categoria_mercado(nome)
        resultado["todos"].append(item)
        resultado["mercados_disponiveis"].append(nome)
        destino = {
            "HT": "odds_ht", "CORNERS": "odds_corners",
            "CARDS": "odds_cards", "FT": "odds_ft"
        }[item["categoria"]]
        resultado[destino].append(item)

    resultado["mercados_disponiveis"] = list(dict.fromkeys(resultado["mercados_disponiveis"]))

    try:
        casa_nome = jogo.get("home") or jogo.get("homeTeam") or ""
        fora_nome = jogo.get("away") or jogo.get("awayTeam") or ""
        print(
            f"🔎 DEBUG MERCADOS | {casa_nome} x {fora_nome} | "
            f"quantidade: {len(mercados)} | "
            f"nomes: {resultado['mercados_disponiveis']}"
        )
    except Exception:
        pass

    mercado_ml = _encontrar_mercado(mercados, ("ML", "Moneyline", "1X2"))
    if mercado_ml:
        linha = _primeiro_odds(mercado_ml)
        resultado["odd_home"] = _numero(linha.get("home"))
        resultado["odd_draw"] = _numero(linha.get("draw"), _numero(linha.get("X"), _numero(linha.get("tie"))))
        resultado["odd_away"] = _numero(linha.get("away"))
        resultado["odd_atual"] = resultado["odd_draw"]
        resultado["mercados_encontrados"].append("ML")

    mercado_totals = _encontrar_mercado(mercados, ("Totals", "Total", "Over/Under", "Over Under", "O/U"))
    if mercado_totals:
        linha = _primeiro_odds(mercado_totals)
        resultado["over_linha"] = _numero(linha.get("hdp"))
        resultado["under_linha"] = resultado["over_linha"]
        resultado["odd_over"] = _numero(linha.get("over"))
        resultado["odd_under"] = _numero(linha.get("under"))
        resultado["mercados_encontrados"].append("TOTALS")

    mercado_btts = _encontrar_mercado(mercados, ("Both Teams To Score", "BTTS", "Both Teams Score"))
    if mercado_btts:
        linha = _primeiro_odds(mercado_btts)
        resultado["odd_btts_sim"] = _numero(linha.get("yes"), _numero(linha.get("Yes")))
        resultado["odd_btts_nao"] = _numero(linha.get("no"), _numero(linha.get("No")))
        resultado["mercados_encontrados"].append("BTTS")

    mercado_handicap = _encontrar_mercado(mercados, ("Spread", "Asian Handicap", "Handicap", "Asian Handicap 3-Way"))
    if mercado_handicap:
        linha = _primeiro_odds(mercado_handicap)
        resultado["handicap_linha"] = _numero(linha.get("hdp"))
        resultado["odd_handicap_home"] = _numero(linha.get("home"))
        resultado["odd_handicap_away"] = _numero(linha.get("away"))
        resultado["mercados_encontrados"].append("HANDICAP")

    mercado_dc = _encontrar_mercado(mercados, ("Double Chance", "DoubleChance", "DC"))
    if mercado_dc:
        linha = _primeiro_odds(mercado_dc)
        resultado["odd_1x"] = _numero(linha.get("1X"))
        resultado["odd_12"] = _numero(linha.get("12"))
        resultado["odd_x2"] = _numero(linha.get("X2"))
        resultado["mercados_encontrados"].append("DOUBLE_CHANCE")

    mercado_dnb = _encontrar_mercado(mercados, ("Draw No Bet", "DrawNoBet", "DNB"))
    if mercado_dnb:
        linha = _primeiro_odds(mercado_dnb)
        resultado["odd_dnb_home"] = _numero(linha.get("home"))
        resultado["odd_dnb_away"] = _numero(linha.get("away"))
        resultado["mercados_encontrados"].append("DNB")

    return resultado


def limpar_memoria():
    pass
        
