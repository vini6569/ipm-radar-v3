# ============================================================
# ODDS API - IPM RADAR V4.1
# ============================================================
# Consulta jogos ao vivo e preserva TODOS os mercados recebidos.
# Também separa HT, escanteios e cartões para o laboratório.
# ============================================================

import json
import urllib.error
import urllib.parse
import urllib.request

from config import (
    BASE_URL, BOOKMAKER, SPORT, MAX_EVENTOS_POR_CONSULTA,
    TIMEOUT_REQUISICAO, obter_api_key,
)

_ODD_INICIAL = {}
_ODD_ANTERIOR = {}

def _request_json(endpoint, params):
    url = f"{BASE_URL}/{endpoint.lstrip('/')}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "IPM-Radar/4.1", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_REQUISICAO) as resp:
            body = resp.read().decode("utf-8")
            print("HTTP STATUS ODDS API:", resp.status)
        if not body:
            return []
        return json.loads(body)
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
    return [
        valor for valor in resposta.values()
        if isinstance(valor, dict) and valor.get("id") is not None
    ]

def buscar_jogos_ao_vivo():
    print("=" * 60)
    print("📡 CONSULTANDO JOGOS AO VIVO")
    print("=" * 60)
    try:
        key = obter_api_key()
    except Exception as e:
        print("❌ ERRO API KEY:", e)
        return []

    resposta = _request_json(
        "/events/live",
        {"apiKey": key, "sport": SPORT},
    )
    eventos = _lista_eventos(resposta)
    print("JOGOS AO VIVO ENCONTRADOS:", len(eventos))

    for e in eventos[:MAX_EVENTOS_POR_CONSULTA]:
        print(
            f"  {e.get('id')} | {e.get('home')} x "
            f"{e.get('away')} | {e.get('status')}"
        )
    return eventos

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

    print("📊 CONSULTANDO ODDS |", len(ids), "|", BOOKMAKER)

    resposta = _request_json(
        "/odds/multi",
        {
            "apiKey": key,
            "eventIds": ",".join(ids),
            "bookmakers": BOOKMAKER,
        },
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
            if (
                isinstance(item, dict)
                and str(item.get("id")) == alvo
            ):
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

            nome = str(
                bookmaker.get("name", "")
            ).strip().lower()

            if nome == BOOKMAKER.strip().lower():
                mercados = bookmaker.get("markets", [])
                return (
                    mercados
                    if isinstance(mercados, list)
                    else []
                )

    return []

def _primeiro_odds(mercado):
    if not isinstance(mercado, dict):
        return {}

    valores = mercado.get("odds")

    if isinstance(valores, list):
        if valores and isinstance(valores[0], dict):
            return valores[0]
        return {}

    if isinstance(valores, dict):
        return valores

    return {}

def _linhas_odds(mercado):
    if not isinstance(mercado, dict):
        return []

    valores = mercado.get("odds")

    if isinstance(valores, list):
        return [
            x for x in valores
            if isinstance(x, dict)
        ]

    if isinstance(valores, dict):
        return [valores]

    return []

def _encontrar_mercado(mercados, nomes):
    nomes = {
        str(nome).strip().lower()
        for nome in nomes
    }

    for mercado in mercados:
        if not isinstance(mercado, dict):
            continue

        nome = str(
            mercado.get("name", "")
        ).strip().lower()

        if nome in nomes:
            return mercado

    return None

def _nome_normalizado(nome):
    return (
        str(nome or "")
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )

def _eh_ht(nome):
    n = _nome_normalizado(nome)

    termos = (
        "half time",
        "halftime",
        "1st half",
        "first half",
        "1h",
        "ht result",
        "ht totals",
        "half time result",
    )

    return any(
        termo in n
        for termo in termos
    )

def _categoria_mercado(nome):
    n = _nome_normalizado(nome)

    if _eh_ht(nome):
        return "HT"

    if (
        "corner" in n
        or "escante" in n
    ):
        return "CORNERS"

    if (
        "card" in n
        or "cartão" in n
        or "cartoes" in n
        or "booking" in n
    ):
        return "CARDS"

    return "FT"

def _extrair_placar(jogo):
    for valor in (
        jogo.get("score"),
        jogo.get("scores"),
        jogo.get("result"),
    ):
        if isinstance(valor, dict):
            casa = valor.get(
                "home",
                valor.get("homeScore")
            )
            fora = valor.get(
                "away",
                valor.get("awayScore")
            )

            if (
                casa is not None
                or fora is not None
            ):
                return (
                    _inteiro(casa),
                    _inteiro(fora)
                )

        elif (
            isinstance(valor, list)
            and len(valor) >= 2
        ):
            return (
                _inteiro(valor[0]),
                _inteiro(valor[1])
            )

    return (
        _inteiro(jogo.get("homeScore")),
        _inteiro(jogo.get("awayScore"))
    )

def _extrair_minuto(jogo):
    for valor in (
        jogo.get("minute"),
        jogo.get("elapsed"),
        jogo.get("timer"),
        jogo.get("clock"),
    ):
        if isinstance(valor, dict):
            valor = valor.get(
                "minute",
                valor.get("elapsed")
            )

        if isinstance(valor, str):
            valor = (
                valor
                .replace("'", "")
                .replace("min", "")
                .strip()
            )

        minuto = _inteiro(valor, -1)

        if minuto >= 0:
            return minuto

    return 0

def _extrair_estatisticas(jogo):
    fontes = []

    for chave in (
        "statistics",
        "stats",
        "matchStatistics",
    ):
        valor = jogo.get(chave)

        if isinstance(valor, dict):
            fontes.append(valor)

    for fonte in fontes:
        escanteios = fonte.get("corners")
        finalizacoes = fonte.get("shots")
        ataques = fonte.get("dangerousAttacks")

        if (
            escanteios is not None
            or finalizacoes is not None
            or ataques is not None
        ):
            return (
                _inteiro(escanteios),
                _inteiro(finalizacoes),
                _inteiro(ataques),
            )

    return 0, 0, 0

def _copiar_mercado(mercado):
    return {
        "name": mercado.get("name", ""),
        "updatedAt": mercado.get("updatedAt"),
        "odds": _linhas_odds(mercado),
    }

def _memoria_odd(event_id, odd_atual):
    anterior = (
        _ODD_ANTERIOR.get(event_id, 0.0)
        if event_id is not None
        else 0.0
    )

    if (
        event_id is not None
        and odd_atual > 0
        and event_id not in _ODD_INICIAL
    ):
        _ODD_INICIAL[event_id] = odd_atual

    inicial = _ODD_INICIAL.get(
        event_id,
        odd_atual
    )

    recente = (
        ((odd_atual - anterior) / anterior) * 100.0
        if anterior > 0
        else 0.0
    )

    desde = (
        ((odd_atual - inicial) / inicial) * 100.0
        if inicial > 0
        else 0.0
    )

    if (
        event_id is not None
        and odd_atual > 0
    ):
        _ODD_ANTERIOR[event_id] = odd_atual

    return anterior, inicial, recente, desde

def extrair_mercados(jogo, odds):
    if not isinstance(jogo, dict):
        return {}

    event_id = jogo.get("id")

    evento = (
        _evento_odds_por_id(
            odds,
            event_id
        )
        or jogo
    )

    mercados = _mercados_bet365(evento)

    casa, fora = _extrair_placar(jogo)

    esc, fin, atq = _extrair_estatisticas(jogo)

    resultado = {
        "event_id": event_id,

        "odd_home": 0.0,
        "odd_draw": 0.0,
        "odd_away": 0.0,

        "odd_atual": 0.0,
        "odd_anterior": 0.0,
        "odd_inicial": 0.0,

        "variacao_desde_inicio": 0.0,
        "variacao_recente": 0.0,

        "over_linha": 0.0,
        "odd_over": 0.0,

        "under_linha": 0.0,
        "odd_under": 0.0,

        "odd_btts_sim": 0.0,
        "odd_btts_nao": 0.0,

        "handicap_linha": 0.0,
        "odd_handicap_home": 0.0,
        "odd_handicap_away": 0.0,

        "odd_1x": 0.0,
        "odd_12": 0.0,
        "odd_x2": 0.0,

        "odd_dnb_home": 0.0,
        "odd_dnb_away": 0.0,

        "minuto": _extrair_minuto(jogo),
        "gols": casa + fora,

        "escanteios": esc,
        "finalizacoes": fin,
        "ataques_perigosos": atq,

        "mercados_encontrados": [],
        "mercados_disponiveis": [],

        # SEMPRE existem. Evita KeyError: 'todos'.
        "todos": [],
        "odds_ft": [],
        "odds_ht": [],
        "odds_corners": [],
        "odds_cards": [],
    }

    # ========================================================
    # TODOS OS MERCADOS RECEBIDOS
    # ========================================================

    for mercado in mercados:
        if not isinstance(mercado, dict):
            continue

        nome = str(
            mercado.get("name", "")
        ).strip()

        if not nome:
            continue

        item = _copiar_mercado(mercado)
        item["categoria"] = _categoria_mercado(nome)

        resultado["todos"].append(item)
        resultado["mercados_disponiveis"].append(nome)

        if item["categoria"] == "HT":
            resultado["odds_ht"].append(item)

        elif item["categoria"] == "CORNERS":
            resultado["odds_corners"].append(item)

        elif item["categoria"] == "CARDS":
            resultado["odds_cards"].append(item)

        else:
            resultado["odds_ft"].append(item)

    resultado["mercados_disponiveis"] = list(
        dict.fromkeys(
            resultado["mercados_disponiveis"]
        )
    )

    # ========================================================
    # FT / 1X2
    # ========================================================

    mercado_ml = _encontrar_mercado(
        mercados,
        ("ML", "Moneyline", "1X2")
    )

    if mercado_ml:
        linha = _primeiro_odds(
            mercado_ml
        )

        resultado["odd_home"] = _numero(
            linha.get("home")
        )

        resultado["odd_draw"] = _numero(
            linha.get("draw"),
            _numero(
                linha.get("X"),
                _numero(linha.get("tie"))
            )
        )

        resultado["odd_away"] = _numero(
            linha.get("away")
        )

        resultado["odd_atual"] = (
            resultado["odd_draw"]
        )

        resultado[
            "mercados_encontrados"
        ].append("ML")

    # ========================================================
    # TOTALS
    # ========================================================

    mercado_totals = _encontrar_mercado(
        mercados,
        (
            "Totals",
            "Total",
            "Over/Under",
            "Over Under",
            "O/U",
        )
    )

    if mercado_totals:
        linha = _primeiro_odds(
            mercado_totals
        )

        resultado["over_linha"] = _numero(
            linha.get("hdp")
        )

        resultado["under_linha"] = (
            resultado["over_linha"]
        )

        resultado["odd_over"] = _numero(
            linha.get("over")
        )

        resultado["odd_under"] = _numero(
            linha.get("under")
        )

        resultado[
            "mercados_encontrados"
        ].append("TOTALS")

    # ========================================================
    # BTTS
    # ========================================================

    mercado_btts = _encontrar_mercado(
        mercados,
        (
            "Both Teams To Score",
            "BTTS",
            "Both Teams Score",
        )
    )

    if mercado_btts:
        linha = _primeiro_odds(
            mercado_btts
        )

        resultado["odd_btts_sim"] = _numero(
            linha.get("yes"),
            _numero(linha.get("Yes"))
        )

        resultado["odd_btts_nao"] = _numero(
            linha.get("no"),
            _numero(linha.get("No"))
        )

        resultado[
            "mercados_encontrados"
        ].append("BTTS")

    # ========================================================
    # HANDICAP
    # ========================================================

    mercado_handicap = _encontrar_mercado(
        mercados,
        (
            "Spread",
            "Asian Handicap",
            "Handicap",
            "Asian Handicap 3-Way",
        )
    )

    if mercado_handicap:
        linha = _primeiro_odds(
            mercado_handicap
        )

        resultado[
            "handicap_linha"
        ] = _numero(
            linha.get("hdp")
        )

        resultado[
            "odd_handicap_home"
        ] = _numero(
            linha.get("home")
        )

        resultado[
            "odd_handicap_away"
        ] = _numero(
            linha.get("away")
        )

        resultado[
            "mercados_encontrados"
        ].append("HANDICAP")

    # ========================================================
    # DOUBLE CHANCE
    # ========================================================

    mercado_dc = _encontrar_mercado(
        mercados,
        (
            "Double Chance",
            "DoubleChance",
            "DC",
        )
    )

    if mercado_dc:
        linha = _primeiro_odds(
            mercado_dc
        )

        resultado["odd_1x"] = _numero(
            linha.get("1X")
        )

        resultado["odd_12"] = _numero(
            linha.get("12")
        )

        resultado["odd_x2"] = _numero(
            linha.get("X2")
        )

        resultado[
            "mercados_encontrados"
        ].append("DOUBLE_CHANCE")

    # ========================================================
    # DNB
    # ========================================================

    mercado_dnb = _encontrar_mercado(
        mercados,
        (
            "Draw No Bet",
            "DrawNoBet",
            "DNB",
        )
    )

    if mercado_dnb:
        linha = _primeiro_odds(
            mercado_dnb
        )

        resultado[
            "odd_dnb_home"
        ] = _numero(
            linha.get("home")
        )

        resultado[
            "odd_dnb_away"
        ] = _numero(
            linha.get("away")
        )

        resultado[
            "mercados_encontrados"
        ].append("DNB")

    # ========================================================
    # MEMÓRIA DA ODD DO EMPATE
    # ========================================================

    (
        anterior,
        inicial,
        recente,
        desde,
    ) = _memoria_odd(
        event_id,
        resultado["odd_atual"]
    )

    resultado["odd_anterior"] = anterior
    resultado["odd_inicial"] = inicial
    resultado["variacao_recente"] = recente
    resultado["variacao_desde_inicio"] = desde

    print("-" * 60)
    print("📊 MERCADOS EXTRAÍDOS")
    print("EVENT ID:", event_id)
    print(
        "1X2:",
        resultado["odd_home"],
        "|",
        resultado["odd_draw"],
        "|",
        resultado["odd_away"]
    )
    print(
        "HT:",
        len(resultado["odds_ht"]),
        "| FT:",
        len(resultado["odds_ft"])
    )
    print(
        "CORNERS:",
        len(resultado["odds_corners"]),
        "| CARDS:",
        len(resultado["odds_cards"])
    )
    print(
        "VARIAÇÃO EMPATE:",
        f"{recente:.2f}%"
    )
    print(
        "MERCADOS:",
        resultado["mercados_disponiveis"]
    )
    print("-" * 60)

    return resultado

def limpar_memoria():
    _ODD_INICIAL.clear()
    _ODD_ANTERIOR.clear()
    
