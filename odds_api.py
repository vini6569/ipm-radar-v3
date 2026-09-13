# ============================================================
# ODDS API - IPM RADAR V5.2
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


# Limite seguro de IDs enviados por lote à /odds/multi
MAX_EVENTOS_ODDS_MULTI = 10


def _request_json(endpoint, params):
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



def buscar_jogos_ao_vivo_por_ids(event_ids):
    """Busca os jogos ao vivo usando os IDs dos jogos pré-live.

    Importante: consulta /events com status=live e eventIds,
    preservando a mesma referência de evento usada no pré-live.
    """
    if not event_ids:
        return []

    ids = []
    for valor in event_ids:
        if valor is None:
            continue
        valor = str(valor)
        if valor not in ids:
            ids.append(valor)

    if not ids:
        return []

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
            "status": "live",
            "eventIds": ",".join(ids),
            "bookmaker": BOOKMAKER,
        },
    )

    eventos = _lista_eventos(resposta)
    permitidos = set(ids)

    filtrados = [
        evento
        for evento in eventos
        if isinstance(evento, dict)
        and str(evento.get("id")) in permitidos
    ]

    print(
        "JOGOS AO VIVO FILTRADOS POR ID:",
        len(filtrados),
        "/",
        len(ids),
    )

    return filtrados


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
    """Busca odds em lotes de no máximo 10 eventIds.

    A Odds API rejeita consultas com mais de 10 eventIds.
    Portanto, mesmo que MAX_EVENTOS_POR_CONSULTA seja maior,
    esta função nunca envia mais de MAX_EVENTOS_ODDS_MULTI IDs
    por requisição.
    """
    if not eventos:
        return []

    try:
        key = obter_api_key()
    except Exception as e:
        print("❌ ERRO API KEY:", e)
        return []

    ids = []

    for evento in eventos:
        if not isinstance(evento, dict):
            continue

        event_id = evento.get("id")
        if event_id is None:
            continue

        event_id = str(event_id)
        if event_id not in ids:
            ids.append(event_id)

    # Limite do scanner. O limite da Odds API por chamada continua sendo 10.
    ids = ids[:MAX_EVENTOS_POR_CONSULTA]

    if not ids:
        return []

    lotes = [
        ids[i:i + MAX_EVENTOS_ODDS_MULTI]
        for i in range(0, len(ids), MAX_EVENTOS_ODDS_MULTI)
    ]

    todos = []

    print(
        f"📦 ODDS MULTI | EVENTOS={len(ids)} | "
        f"LOTES={len(lotes)} | MAX/LOTE={MAX_EVENTOS_ODDS_MULTI}"
    )

    for numero_lote, lote in enumerate(lotes, 1):
        print(
            f"📡 ODDS MULTI | LOTE {numero_lote}/{len(lotes)} | "
            f"EVENTOS={len(lote)}"
        )

        resposta = _request_json(
            "/odds/multi",
            {
                "apiKey": key,
                "eventIds": ",".join(lote),
                "bookmakers": BOOKMAKER,
            },
        )

        eventos_odds = _lista_eventos(resposta)

        print(
            f"📥 LOTE {numero_lote}/{len(lotes)} | "
            f"RECEBIDOS={len(eventos_odds)}"
        )

        todos.extend(eventos_odds)

    resultado = []
    vistos = set()

    for evento in todos:
        if not isinstance(evento, dict):
            continue

        event_id = evento.get("id")
        if event_id is None:
            continue

        event_id = str(event_id)
        if event_id in vistos:
            continue

        vistos.add(event_id)
        resultado.append(evento)

    print(
        "ODDS RECEBIDAS:",
        len(resultado),
        "/",
        len(ids),
    )

    return resultado


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
    """
    Extrai os mercados do bookmaker configurado de forma robusta.

    A Odds API pode variar a estrutura entre endpoints/versões:
    - bookmakers como lista ou dicionário;
    - bookmaker identificado por key, name ou bookmaker;
    - markets como lista, dicionário ou dentro de data/results;
    - estruturas aninhadas.

    Esta função percorre essas formas sem alterar o filtro Q.
    """
    if not isinstance(evento, dict):
        return []

    alvo = str(BOOKMAKER or "").strip().lower()

    def normalizar_mercados(valor):
        if isinstance(valor, list):
            return [x for x in valor if isinstance(x, dict)]

        if not isinstance(valor, dict):
            return []

        # Estruturas comuns: {markets: [...]}, {data: [...]}, etc.
        for chave in ("markets", "data", "results"):
            v = valor.get(chave)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
            if isinstance(v, dict):
                encontrados = normalizar_mercados(v)
                if encontrados:
                    return encontrados

        # Um mercado isolado.
        if any(
            k in valor
            for k in ("odds", "outcomes", "name", "key", "type", "market")
        ):
            return [valor]

        return []

    def nomes_objeto(obj, chave=None):
        if not isinstance(obj, dict):
            return set()
        valores = (
            obj.get("key"),
            obj.get("name"),
            obj.get("bookmaker"),
            obj.get("bookmakerKey"),
            obj.get("bookmakerName"),
            chave,
        )
        return {
            str(x).strip().lower()
            for x in valores
            if x is not None
        }

    def procurar(node, profundidade=0):
        if profundidade > 8:
            return []

        if isinstance(node, list):
            for item in node:
                encontrados = procurar(item, profundidade + 1)
                if encontrados:
                    return encontrados
            return []

        if not isinstance(node, dict):
            return []

        # 1) Procurar bookmaker explicitamente em qualquer nível.
        bookmakers = node.get("bookmakers")
        if isinstance(bookmakers, list):
            for bookmaker in bookmakers:
                if not isinstance(bookmaker, dict):
                    continue
                if alvo in nomes_objeto(bookmaker):
                    mercados = normalizar_mercados(bookmaker.get("markets"))
                    if not mercados:
                        mercados = normalizar_mercados(bookmaker.get("data"))
                    if not mercados:
                        mercados = normalizar_mercados(bookmaker)
                    if mercados:
                        return mercados

        elif isinstance(bookmakers, dict):
            # Chave do bookmaker.
            for chave, valor in bookmakers.items():
                if str(chave).strip().lower() == alvo:
                    mercados = normalizar_mercados(valor)
                    if mercados:
                        return mercados

            # Bookmaker identificado dentro do valor.
            for chave, valor in bookmakers.items():
                if not isinstance(valor, dict):
                    continue
                if alvo in nomes_objeto(valor, chave):
                    mercados = normalizar_mercados(valor)
                    if mercados:
                        return mercados

        # 2) Alguns retornos trazem o bookmaker diretamente como objeto.
        if alvo in nomes_objeto(node):
            mercados = normalizar_mercados(node.get("markets"))
            if not mercados:
                mercados = normalizar_mercados(node.get("data"))
            if mercados:
                return mercados

        # 3) Mercados diretamente no evento.
        for chave in ("markets", "data", "results"):
            valor = node.get(chave)
            mercados = normalizar_mercados(valor)
            if mercados:
                return mercados

        # 4) Último recurso: percorrer estruturas aninhadas.
        for chave, valor in node.items():
            if chave in ("apiKey",):
                continue
            if isinstance(valor, (dict, list)):
                encontrados = procurar(valor, profundidade + 1)
                if encontrados:
                    return encontrados

        return []

    return procurar(evento)


def _primeiro_odds(mercado):
    if not isinstance(mercado, dict):
        return {}

    valores = mercado.get("odds")
    if isinstance(valores, list):
        return valores[0] if valores and isinstance(valores[0], dict) else {}
    if isinstance(valores, dict):
        return valores

    # Compatibilidade com respostas que usam outcomes em vez de odds.
    valores = mercado.get("outcomes")
    if isinstance(valores, list):
        if not valores:
            return {}
        # Converte outcomes [{name/outcome, price/odds}] para as chaves
        # esperadas pelo restante do IPM.
        saida = {}
        for item in valores:
            if not isinstance(item, dict):
                continue
            nome = str(item.get("name") or item.get("outcome") or "").strip().lower()
            odd = item.get("price", item.get("odds", item.get("odd")))
            if nome in ("home", "casa", "1"):
                saida["home"] = odd
            elif nome in ("draw", "empate", "x", "tie"):
                saida["draw"] = odd
            elif nome in ("away", "fora", "2"):
                saida["away"] = odd
            elif nome in ("yes", "sim"):
                saida["yes"] = odd
            elif nome in ("no", "nao", "não"):
                saida["no"] = odd
            elif nome.startswith("over"):
                saida["over"] = odd
            elif nome.startswith("under"):
                saida["under"] = odd
        return saida

    return {}


def _linhas_odds(mercado):
    if not isinstance(mercado, dict):
        return []
    valores = mercado.get("odds")
    if isinstance(valores, list):
        return [x for x in valores if isinstance(x, dict)]
    if isinstance(valores, dict):
        return [valores]

    if isinstance(mercado.get("outcomes"), list):
        linha = _primeiro_odds(mercado)
        return [linha] if linha else []

    return []


def _encontrar_mercado(mercados, nomes):
    """Localiza um mercado aceitando variações de nome da Odds API."""
    nomes_normalizados = {
        _nome_normalizado(n)
        for n in nomes
    }

    for mercado in mercados:
        if not isinstance(mercado, dict):
            continue

        candidatos = (
            mercado.get("name"),
            mercado.get("key"),
            mercado.get("type"),
            mercado.get("market"),
        )

        for candidato in candidatos:
            nome = _nome_normalizado(candidato)
            if nome in nomes_normalizados:
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

    # Chaves padronizadas do IPM RADAR.
    resultado.setdefault("odd_casa", resultado.get("odd_home", 0.0))
    resultado.setdefault("odd_empate", resultado.get("odd_draw", 0.0))
    resultado.setdefault("odd_visitante", resultado.get("odd_away", 0.0))

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

        mercado_ml = _encontrar_mercado(
        mercados,
        (
            "ML",
            "Moneyline",
            "1X2",
            "H2H",
            "h2h",
            "Head to Head",
            "Match Winner",
            "Match Result",
            "1X2 Result",
        ),
    )

    if mercado_ml:
        linhas_ml = _linhas_odds(mercado_ml)

        # Algumas respostas vêm com uma lista de odds.
        # Procuramos uma linha que realmente contenha Casa/Empate/Fora.
        linha = {}

        for candidata in linhas_ml:
            if not isinstance(candidata, dict):
                continue

            if (
                candidata.get("home") is not None
                or candidata.get("draw") is not None
                or candidata.get("away") is not None
                or candidata.get("1") is not None
                or candidata.get("X") is not None
                or candidata.get("2") is not None
            ):
                linha = candidata
                break

        if not linha:
            linha = _primeiro_odds(mercado_ml)

        odd_home = _numero(
            linha.get("home"),
            _numero(linha.get("1"))
        )

        odd_draw = _numero(
            linha.get("draw"),
            _numero(
                linha.get("X"),
                _numero(linha.get("tie"))
            )
        )

        odd_away = _numero(
            linha.get("away"),
            _numero(linha.get("2"))
        )

        resultado["odd_home"] = odd_home
        resultado["odd_draw"] = odd_draw
        resultado["odd_away"] = odd_away

        # O IPM trabalha com a odd do empate como odd_atual.
        resultado["odd_atual"] = odd_draw

        resultado["mercados_encontrados"].append("ML")

        print(
            f"💰 ML EXTRAÍDO | "
            f"CASA={odd_home:.2f} | "
            f"EMPATE={odd_draw:.2f} | "
            f"FORA={odd_away:.2f}"
        )
