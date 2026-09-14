# ============================================================
# ODDS API - IPM RADAR V5.2
# CASA / EMPATE / VISITANTE
# W1 x W2 + Q + R | TOTALS + BTTS
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

REQUISICOES_REALIZADAS = 0
_IDS_LIVE_SELECIONADOS = []


def _numero(valor, padrao=0.0):
    try:
        if valor in (None, ""):
            return padrao
        return float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return padrao


def _inteiro(valor, padrao=0):
    try:
        if valor in (None, ""):
            return padrao
        return int(float(valor))
    except (TypeError, ValueError):
        return padrao


def _texto(valor):
    return str(valor or "").strip().lower()


def _request_json(endpoint, params):
    global REQUISICOES_REALIZADAS
    url = f"{BASE_URL}/{endpoint.lstrip('/')}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "IPM-Radar/5.2", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_REQUISICAO) as resp:
            REQUISICOES_REALIZADAS += 1
            body = resp.read().decode("utf-8")
            print("HTTP STATUS ODDS API:", resp.status)
            return json.loads(body) if body else []
    except urllib.error.HTTPError as erro:
        REQUISICOES_REALIZADAS += 1
        try:
            detalhe = erro.read().decode("utf-8")
        except Exception:
            detalhe = ""
        print(f"ERRO HTTP ODDS API: {erro.code} | {detalhe[:500]}")
    except (urllib.error.URLError, TimeoutError) as erro:
        print("ERRO DE CONEXAO ODDS API:", erro)
    except Exception as erro:
        print("ERRO ODDS API:", type(erro).__name__, erro)
    return []


def _lista_eventos(resposta):
    if isinstance(resposta, list):
        return [x for x in resposta if isinstance(x, dict)]
    if not isinstance(resposta, dict):
        return []

    for chave in ("events", "data", "results", "odds"):
        valor = resposta.get(chave)
        if isinstance(valor, list):
            return [x for x in valor if isinstance(x, dict)]

    if resposta.get("id") is not None:
        return [resposta]

    return [
        x for x in resposta.values()
        if isinstance(x, dict) and x.get("id") is not None
    ]


def calcular_w1xw2(odd_casa, odd_visitante):
    w1, w2 = _numero(odd_casa), _numero(odd_visitante)
    return w1 * w2 if w1 > 0 and w2 > 0 else 0.0


def calcular_q(odd_casa, odd_visitante):
    casa, fora = _numero(odd_casa), _numero(odd_visitante)
    if casa <= 0 or fora <= 0:
        return 0.0
    return 2.0 * casa * fora / (casa + fora)


def calcular_r(odd_casa, odd_visitante):
    casa, fora = _numero(odd_casa), _numero(odd_visitante)
    if casa <= 0 or fora <= 0:
        return 0.0
    return max(casa, fora) / min(casa, fora)


def _extrair_minuto(jogo):
    if not isinstance(jogo, dict):
        return 0
    clock = jogo.get("clock")
    if isinstance(clock, dict):
        minuto = _inteiro(clock.get("minute"), -1)
        if minuto >= 0:
            return minuto
    for valor in (jogo.get("minute"), jogo.get("elapsed"), jogo.get("timer")):
        if isinstance(valor, dict):
            valor = valor.get("minute", valor.get("elapsed"))
        if isinstance(valor, str):
            valor = valor.replace("'", "").replace("min", "").strip()
        minuto = _inteiro(valor, -1)
        if minuto >= 0:
            return minuto
    return 0


def _extrair_placar(jogo):
    for valor in (jogo.get("scores"), jogo.get("score"), jogo.get("result")):
        if isinstance(valor, dict):
            casa = valor.get("home", valor.get("homeScore"))
            fora = valor.get("away", valor.get("awayScore"))
            if casa is not None or fora is not None:
                return _inteiro(casa), _inteiro(fora)
        elif isinstance(valor, list) and len(valor) >= 2:
            return _inteiro(valor[0]), _inteiro(valor[1])
    return _inteiro(jogo.get("homeScore")), _inteiro(jogo.get("awayScore"))


def _extrair_estatisticas(jogo):
    for chave in ("statistics", "stats", "matchStatistics"):
        fonte = jogo.get(chave)
        if not isinstance(fonte, dict):
            continue
        vals = (
            fonte.get("corners"), fonte.get("shots"),
            fonte.get("dangerousAttacks"), fonte.get("cards")
        )
        if any(x is not None for x in vals):
            return tuple(_inteiro(x) for x in vals)
    return 0, 0, 0, 0


def _parse_data_evento(evento):
    valor = evento.get("date") or evento.get("startTime") or evento.get("start_time")
    if not valor:
        return None
    try:
        dt = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def buscar_jogos_ao_vivo():
    global _IDS_LIVE_SELECIONADOS
    try:
        key = obter_api_key()
    except Exception as erro:
        print("ERRO API KEY:", erro)
        return []

    resposta = _request_json("/events/live", {"apiKey": key, "sport": SPORT})
    eventos = _lista_eventos(resposta)
    mapa = {
        str(e["id"]): e for e in eventos if e.get("id") is not None
    }

    mantidos = [x for x in _IDS_LIVE_SELECIONADOS if str(x) in mapa]
    restantes = [e for i, e in mapa.items() if i not in mantidos]
    restantes.sort(key=_extrair_minuto)

    vagas = max(0, MAX_EVENTOS_POR_CONSULTA - len(mantidos))
    mantidos.extend(str(e["id"]) for e in restantes[:vagas])
    _IDS_LIVE_SELECIONADOS = mantidos[:MAX_EVENTOS_POR_CONSULTA]

    selecionados = [mapa[i] for i in _IDS_LIVE_SELECIONADOS if i in mapa]
    print("JOGOS AO VIVO ENCONTRADOS:", len(eventos),
          "| SELECIONADOS:", len(selecionados))
    return selecionados


def buscar_jogos_ao_vivo_por_ids(ids):
    if not ids:
        print("LIVE POR IDS: nenhum ID recebido.")
        return []
    try:
        key = obter_api_key()
    except Exception as erro:
        print("ERRO API KEY:", erro)
        return []

    ids_alvo = list(dict.fromkeys(str(x) for x in ids if x is not None))
    resposta = _request_json("/events/live", {"apiKey": key, "sport": SPORT})
    eventos = _lista_eventos(resposta)
    mapa = {
        str(e["id"]): e for e in eventos if e.get("id") is not None
    }
    selecionados = [mapa[i] for i in ids_alvo if i in mapa]
    print(f"LIVE POR IDS | SOLICITADOS={len(ids_alvo)} | ENCONTRADOS={len(selecionados)}")
    return selecionados


def buscar_jogos_pre_live():
    try:
        key = obter_api_key()
    except Exception as erro:
        print("ERRO API KEY:", erro)
        return []

    resposta = _request_json("/events", {
        "apiKey": key,
        "sport": SPORT,
        "status": "pending",
        "limit": 100,
        "bookmaker": BOOKMAKER,
    })
    eventos = _lista_eventos(resposta)
    agora = datetime.now(timezone.utc)
    limite = agora.timestamp() + PRE_LIVE_JANELA_MINUTOS * 60
    proximos = []

    for evento in eventos:
        dt = _parse_data_evento(evento)
        if dt and agora.timestamp() <= dt.timestamp() <= limite:
            proximos.append(evento)

    proximos.sort(key=lambda e: _parse_data_evento(e) or agora)
    proximos = proximos[:MAX_EVENTOS_POR_CONSULTA]
    print("JOGOS PRE-LIVE PROXIMOS:", len(proximos))
    return proximos


def buscar_odds_multiplos(eventos):
    if not eventos:
        print("ODDS MULTI: nenhum evento recebido.")
        return []
    try:
        key = obter_api_key()
    except Exception as erro:
        print("ERRO API KEY:", erro)
        return []

    ids = list(dict.fromkeys(
        str(e["id"]) for e in eventos
        if isinstance(e, dict) and e.get("id") is not None
    ))[:MAX_EVENTOS_POR_CONSULTA]

    resultados = []
    for inicio in range(0, len(ids), 10):
        bloco = ids[inicio:inicio + 10]
        print(f"CONSULTA ODDS {inicio // 10 + 1}: {len(bloco)} eventos")
        resposta = _request_json("/odds/multi", {
            "apiKey": key,
            "eventIds": ",".join(bloco),
            "bookmakers": BOOKMAKER,
        })
        resultados.extend(_lista_eventos(resposta))
    return resultados


def _evento_odds_por_id(odds, event_id):
    if event_id is None:
        return None
    alvo = str(event_id)
    if isinstance(odds, list):
        return next(
            (x for x in odds if isinstance(x, dict) and str(x.get("id")) == alvo),
            None,
        )
    if isinstance(odds, dict):
        if str(odds.get("id")) == alvo:
            return odds
        item = odds.get(alvo)
        if isinstance(item, dict):
            return item
    return None


def _mercados_bookmaker(evento):
    if not isinstance(evento, dict):
        return []

    alvo = _texto(BOOKMAKER)
    bookmakers = evento.get("bookmakers")

    if isinstance(bookmakers, dict):
        escolhido = bookmakers.get(BOOKMAKER)
        if escolhido is None:
            escolhido = next(
                (v for k, v in bookmakers.items() if _texto(k) == alvo), None
            )
        if isinstance(escolhido, dict):
            mercados = escolhido.get("markets", escolhido.get("odds", []))
            return mercados if isinstance(mercados, list) else []
        if isinstance(escolhido, list):
            return [x for x in escolhido if isinstance(x, dict)]

    if isinstance(bookmakers, list):
        for bookmaker in bookmakers:
            if not isinstance(bookmaker, dict):
                continue
            nome = _texto(
                bookmaker.get("name") or bookmaker.get("title") or bookmaker.get("key")
            )
            if nome == alvo:
                mercados = bookmaker.get("markets", bookmaker.get("odds", []))
                return mercados if isinstance(mercados, list) else []

    # Alguns retornos colocam markets diretamente no evento.
    mercados = evento.get("markets")
    if isinstance(mercados, list):
        return [x for x in mercados if isinstance(x, dict)]

    # Fallback para odds diretamente no evento.
    odds = evento.get("odds")
    if isinstance(odds, list) and any(isinstance(x, dict) for x in odds):
        return [x for x in odds if isinstance(x, dict)]

    return []


def _mercados_bet365(evento):
    return _mercados_bookmaker(evento)


def _linhas_odds(mercado):
    if not isinstance(mercado, dict):
        return []

    for chave in ("odds", "outcomes", "selections", "items", "options"):
        valor = mercado.get(chave)
        if isinstance(valor, list):
            return [x for x in valor if isinstance(x, dict)]
        if isinstance(valor, dict):
            return [x for x in valor.values() if isinstance(x, dict)]

    # O próprio mercado pode ser uma seleção/outcome.
    if any(k in mercado for k in ("price", "value", "odd", "decimal")):
        return [mercado]
    return []


def _preco_item(item):
    if not isinstance(item, dict):
        return 0.0
    for chave in ("price", "value", "odd", "odds", "decimal"):
        valor = item.get(chave)
        if isinstance(valor, (int, float, str)):
            preco = _numero(valor)
            if preco > 0:
                return preco
    return 0.0


def _nome_linha(linha):
    return _texto(
        linha.get("name") or linha.get("label") or linha.get("outcome")
        or linha.get("selection") or linha.get("key") or linha.get("type")
    )


def _extrair_outcome(linha, nomes):
    if not isinstance(linha, dict):
        return 0.0

    alvos = {_texto(x) for x in nomes if x}

    # Campos diretos: home/draw/away, 1/x/2 etc.
    for nome in nomes:
        valor = linha.get(nome)
        preco = _preco_item(valor) if isinstance(valor, dict) else _numero(valor)
        if preco > 0:
            return preco

    if _nome_linha(linha) in alvos:
        return _preco_item(linha)

    for chave in ("outcomes", "selections", "items", "options", "odds"):
        valor = linha.get(chave)
        candidatos = (
            [x for x in valor if isinstance(x, dict)]
            if isinstance(valor, list)
            else [x for x in valor.values() if isinstance(x, dict)]
            if isinstance(valor, dict)
            else []
        )
        for item in candidatos:
            if _nome_linha(item) in alvos:
                preco = _preco_item(item)
                if preco > 0:
                    return preco
    return 0.0


def _eh_mercado_1x2(mercado):
    nome = _texto(
        mercado.get("key") or mercado.get("name") or mercado.get("market")
        or mercado.get("type")
    )
    compactado = nome.replace("_", " ").replace("-", " ").strip()
    return compactado in {
        "1x2", "match", "match winner", "match result", "winner",
        "full time result", "fulltime result", "result", "moneyline", "ml",
    } or "1x2" in compactado


def _extrair_1x2(mercados, casa_nome="", fora_nome=""):
    casa = empate = fora = 0.0
    casa_alvos = {
        "1", "home", "casa", "home team", "1x2 home", _texto(casa_nome)
    }
    empate_alvos = {"x", "draw", "tie", "empate"}
    fora_alvos = {
        "2", "away", "fora", "away team", "1x2 away", _texto(fora_nome)
    }

    for mercado in mercados:
        if not _eh_mercado_1x2(mercado):
            continue

        # Primeiro tenta a estrutura normal.
        for linha in _linhas_odds(mercado):
            nome = _nome_linha(linha)
            preco = _preco_item(linha)
            if nome in casa_alvos and preco > 0 and casa <= 0:
                casa = preco
            elif nome in empate_alvos and preco > 0 and empate <= 0:
                empate = preco
            elif nome in fora_alvos and preco > 0 and fora <= 0:
                fora = preco

            if casa <= 0:
                casa = _extrair_outcome(linha, casa_alvos)
            if empate <= 0:
                empate = _extrair_outcome(linha, empate_alvos)
            if fora <= 0:
                fora = _extrair_outcome(linha, fora_alvos)

        # Alguns provedores guardam home/draw/away diretamente no market.
        if casa <= 0:
            casa = _extrair_outcome(mercado, casa_alvos)
        if empate <= 0:
            empate = _extrair_outcome(mercado, empate_alvos)
        if fora <= 0:
            fora = _extrair_outcome(mercado, fora_alvos)

        if casa > 0 and empate > 0 and fora > 0:
            return casa, empate, fora

    return casa, empate, fora


def _extrair_totals(mercados):
    over_linha = under_linha = odd_over = odd_under = 0.0
    for mercado in mercados:
        nome_mercado = _texto(
            mercado.get("key") or mercado.get("name") or mercado.get("market")
            or mercado.get("type")
        )
        if "total" not in nome_mercado and "over" not in nome_mercado:
            continue
        for linha in _linhas_odds(mercado):
            nome = _nome_linha(linha)
            preco = _preco_item(linha)
            valor = _numero(
                linha.get("line") or linha.get("handicap")
                or linha.get("total") or linha.get("point")
            )
            if preco <= 0:
                continue
            if "over" in nome:
                odd_over = odd_over or preco
                over_linha = over_linha or valor
            elif "under" in nome:
                odd_under = odd_under or preco
                under_linha = under_linha or valor
    return over_linha, under_linha, odd_over, odd_under


def _extrair_btts(mercados):
    sim = nao = 0.0
    for mercado in mercados:
        nome_mercado = _texto(
            mercado.get("key") or mercado.get("name") or mercado.get("market")
            or mercado.get("type")
        )
        if "btts" not in nome_mercado and "both teams" not in nome_mercado:
            continue
        for linha in _linhas_odds(mercado):
            nome, preco = _nome_linha(linha), _preco_item(linha)
            if nome in {"yes", "sim", "true"}:
                sim = preco
            elif nome in {"no", "não", "nao", "false"}:
                nao = preco
    return sim, nao


def probabilidade_implicita(odd):
    odd = _numero(odd)
    return 100.0 / odd if odd > 0 else 0.0


def probabilidade_x_normalizada(odd_casa, odd_empate, odd_visitante):
    c, x, f = map(_numero, (odd_casa, odd_empate, odd_visitante))
    if min(c, x, f) <= 0:
        return 0.0
    total = 1/c + 1/x + 1/f
    return (1/x) / total * 100.0


def odds_1x2_validas(odds):
    return bool(
        isinstance(odds, dict)
        and _numero(odds.get("odd_casa")) > 0
        and _numero(odds.get("odd_empate")) > 0
        and _numero(odds.get("odd_visitante")) > 0
    )


def extrair_mercados(jogo, odds):
    if not isinstance(jogo, dict):
        return {}

    evento = _evento_odds_por_id(odds, jogo.get("id")) or jogo
    mercados = _mercados_bookmaker(evento)
    casa_nome = jogo.get("home") or jogo.get("homeTeam") or ""
    fora_nome = jogo.get("away") or jogo.get("awayTeam") or ""

    casa, empate, fora = _extrair_1x2(mercados, casa_nome, fora_nome)

    # Fallback para campos diretos do evento.
    casa = casa or _numero(evento.get("odd_casa") or evento.get("homeOdd") or evento.get("home_odd"))
    empate = empate or _numero(evento.get("odd_empate") or evento.get("drawOdd") or evento.get("draw_odd"))
    fora = fora or _numero(evento.get("odd_visitante") or evento.get("awayOdd") or evento.get("away_odd"))

    if not (casa > 0 and empate > 0 and fora > 0):
        nomes = [
            _texto(m.get("key") or m.get("name") or m.get("market") or m.get("type"))
            for m in mercados if isinstance(m, dict)
        ]
        print(f"1X2 NÃO EXTRAÍDO | ID={jogo.get('id')} | MERCADOS={nomes[:20]}")

    w1xw2 = calcular_w1xw2(casa, fora)
    q = calcular_q(casa, fora)
    r = calcular_r(casa, fora)
    over_linha, under_linha, odd_over, odd_under = _extrair_totals(mercados)
    btts_sim, btts_nao = _extrair_btts(mercados)

    return {
        "odd_casa": casa,
        "odd_empate": empate,
        "odd_visitante": fora,
        "w1": casa,
        "w2": fora,
        "w1xw2": round(w1xw2, 4),
        "q": round(q, 4),
        "r": round(r, 4),
        "over_linha": over_linha,
        "under_linha": under_linha,
        "odd_over": odd_over,
        "odd_under": odd_under,
        "odd_btts_sim": btts_sim,
        "odd_btts_nao": btts_nao,
        "tem_1x2": casa > 0 and empate > 0 and fora > 0,
        "tem_w1xw2": w1xw2 > 0,
        "tem_totals": odd_over > 0 or odd_under > 0,
        "tem_btts": btts_sim > 0 or btts_nao > 0,
        "probabilidade_x": round(probabilidade_implicita(empate), 4),
        "probabilidade_x_normalizada": round(
            probabilidade_x_normalizada(casa, empate, fora), 4
        ),
    }


def testar_w1xw2():
    print("=" * 60)
    print("TESTE W1 x W2 | Q | R")
    for w1, w2 in ((2.40, 2.10), (1.50, 4.00), (3.00, 3.00)):
        print(
            f"W1={w1:.2f} | W2={w2:.2f} | "
            f"W1xW2={calcular_w1xw2(w1,w2):.4f} | "
            f"Q={calcular_q(w1,w2):.4f} | R={calcular_r(w1,w2):.4f}"
        )
    print("=" * 60)


if __name__ == "__main__":
    testar_w1xw2()
            
