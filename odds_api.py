# ============================================================
# V4.7: evita falso 0.0 no ML e registra a estrutura recebida.
# ============================================================
# ODDS API - IPM RADAR V4.7
# SELECAO FIXA + ODDS ROBUSTAS + DIAGNOSTICO
# ============================================================

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from config import (
    BASE_URL,
    BOOKMAKER,
    SPORT,
    MAX_EVENTOS_POR_CONSULTA,
    TIMEOUT_REQUISICAO,
    obter_api_key,
    PRE_LIVE_JANELA_MINUTOS,
)


# Mantem os mesmos jogos ao longo dos ciclos enquanto eles
# continuarem disponiveis ao vivo.
_IDS_LIVE_SELECIONADOS = []


def _request_json(endpoint, params):
    url = f"{BASE_URL}/{endpoint.lstrip('/')}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "IPM-Radar/4.7",
            "Accept": "application/json",
        },
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
        return []

    except (urllib.error.URLError, TimeoutError) as e:
        print("ERRO DE CONEXAO ODDS API:", e)
        return []

    except Exception as e:
        print(f"ERRO ODDS API: {type(e).__name__}: {e}")
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
        v for v in resposta.values()
        if isinstance(v, dict) and v.get("id") is not None
    ]


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


def _extrair_minuto(jogo):
    if not isinstance(jogo, dict):
        return 0

    for valor in (
        jogo.get("minute"),
        jogo.get("elapsed"),
        jogo.get("timer"),
        jogo.get("clock"),
    ):
        if isinstance(valor, dict):
            valor = valor.get("minute", valor.get("elapsed"))

        if isinstance(valor, str):
            valor = (
                valor.replace("'", "")
                .replace("min", "")
                .strip()
            )

        minuto = _inteiro(valor, -1)

        if minuto >= 0:
            return minuto

    return 0


def buscar_jogos_ao_vivo():
    """
    Busca os jogos ao vivo e trabalha com no maximo
    MAX_EVENTOS_POR_CONSULTA.

    REGRA NOVA:
    - Na primeira selecao, escolhe os jogos com menor minuto.
    - Nos ciclos seguintes, MANTEM os mesmos IDs enquanto
      eles continuarem ao vivo na API.
    - Se algum jogo sair da lista (terminou, foi removido etc.),
      abre uma vaga e preenche com o proximo jogo disponivel.
    """

    global _IDS_LIVE_SELECIONADOS

    try:
        key = obter_api_key()
    except Exception as e:
        print("ERRO API KEY:", e)
        return []

    resposta = _request_json(
        "/events/live",
        {
            "apiKey": key,
            "sport": SPORT,
        },
    )

    eventos = _lista_eventos(resposta)

    if not eventos:
        print("JOGOS AO VIVO ENCONTRADOS: 0")
        return []

    # Mapa ID -> evento atual recebido da API.
    mapa_eventos = {}
    for evento in eventos:
        event_id = evento.get("id")
        if event_id is not None:
            mapa_eventos[str(event_id)] = evento

    # 1) Mantem somente os IDs antigos que continuam vivos.
    ids_mantidos = []
    for event_id in _IDS_LIVE_SELECIONADOS:
        if str(event_id) in mapa_eventos:
            ids_mantidos.append(str(event_id))

    # 2) Se ainda nao temos 10 jogos, preenche as vagas.
    restantes = [
        evento
        for event_id, evento in mapa_eventos.items()
        if event_id not in ids_mantidos
    ]

    restantes.sort(key=_extrair_minuto)

    vagas = max(0, MAX_EVENTOS_POR_CONSULTA - len(ids_mantidos))

    for evento in restantes[:vagas]:
        event_id = evento.get("id")
        if event_id is not None:
            ids_mantidos.append(str(event_id))

    # Limite final.
    _IDS_LIVE_SELECIONADOS = ids_mantidos[:MAX_EVENTOS_POR_CONSULTA]

    selecionados = [
        mapa_eventos[event_id]
        for event_id in _IDS_LIVE_SELECIONADOS
        if event_id in mapa_eventos
    ]

    print(
        "JOGOS AO VIVO ENCONTRADOS:",
        len(eventos),
        "| JOGOS SELECIONADOS:",
        len(selecionados),
    )
    print(
        "IDS FIXADOS PARA O CICLO:",
        _IDS_LIVE_SELECIONADOS,
    )

    for evento in selecionados:
        nome_casa = evento.get("home") or evento.get("homeTeam") or ""
        nome_fora = evento.get("away") or evento.get("awayTeam") or ""
        minuto = _extrair_minuto(evento)
        print(
            f"SELECIONADO | {minuto}' | "
            f"{nome_casa} x {nome_fora} | ID={evento.get('id')}"
        )

    return selecionados


def _parse_data_evento(evento):
    valor = (
        evento.get("date")
        or evento.get("startTime")
        or evento.get("start_time")
    )

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
    """Busca partidas pendentes proximas do inicio."""
    try:
        key = obter_api_key()
    except Exception as e:
        print("ERRO API KEY:", e)
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
    agora_ts = agora.timestamp()
    limite = agora_ts + PRE_LIVE_JANELA_MINUTOS * 60

    proximos = []

    for evento in eventos:
        dt = _parse_data_evento(evento)

        if dt is None:
            continue

        ts = dt.timestamp()

        if agora_ts <= ts <= limite:
            proximos.append(evento)

    proximos.sort(
        key=lambda e: (_parse_data_evento(e) or agora)
    )

    proximos = proximos[:MAX_EVENTOS_POR_CONSULTA]

    print(
        "JOGOS PRE-LIVE PROXIMOS:",
        len(proximos),
    )

    return proximos


def buscar_odds_multiplos(eventos):
    """
    Busca odds somente dos eventos selecionados.
    O diagnostico mostra o caminho da informacao sem despejar
    o payload inteiro no log.
    """
    if not eventos:
        print("ODDS MULTI: nenhum evento recebido.")
        return []

    try:
        key = obter_api_key()
    except Exception as e:
        print("ERRO API KEY:", e)
        return []

    ids = []

    for evento in eventos:
        if isinstance(evento, dict) and evento.get("id") is not None:
            ids.append(str(evento["id"]))

    ids = list(dict.fromkeys(ids))
    ids = ids[:MAX_EVENTOS_POR_CONSULTA]

    if not ids:
        print("ODDS MULTI: nenhum ID valido.")
        return []

    print("=" * 70)
    print("DIAGNOSTICO ODDS MULTI V4.7")
    print(f"EVENTOS SOLICITADOS: {len(ids)}")
    print(f"IDS SOLICITADOS: {ids}")
    print(f"LIMITE CONFIGURADO: {MAX_EVENTOS_POR_CONSULTA}")

    resposta = _request_json(
        "/odds/multi",
        {
            "apiKey": key,
            "eventIds": ",".join(ids),
            "bookmakers": BOOKMAKER,
        },
    )

    eventos_odds = _lista_eventos(resposta)

    print(f"RESPOSTA ODDS MULTI: {type(resposta).__name__}")
    print(f"EVENTOS COM ODDS RECEBIDOS: {len(eventos_odds)}")

    for event_id in ids[:2]:
        item = _evento_odds_por_id(eventos_odds, event_id)

        print("-" * 70)
        print(f"TESTE EVENT_ID: {event_id}")

        if item is None:
            print("EVENTO NAO ENCONTRADO NA RESPOSTA DE ODDS.")
            continue

        print("EVENTO ENCONTRADO NA RESPOSTA DE ODDS.")
        print(
            "CHAVES DO EVENTO:",
            list(item.keys())[:20],
        )

        bookmakers = item.get("bookmakers")

        if isinstance(bookmakers, dict):
            print(
                "BOOKMAKERS: dict | CHAVES:",
                list(bookmakers.keys())[:20],
            )

        elif isinstance(bookmakers, list):
            nomes = []

            for bookmaker in bookmakers[:20]:
                if isinstance(bookmaker, dict):
                    nomes.append(
                        bookmaker.get("name")
                        or bookmaker.get("title")
                        or bookmaker.get("key")
                    )

            print(
                "BOOKMAKERS: list | NOMES:",
                nomes,
            )

        else:
            print(
                "BOOKMAKERS:",
                type(bookmakers).__name__,
            )

    print("=" * 70)

    return eventos_odds


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
                if (
                    str(nome).strip().lower()
                    == BOOKMAKER.strip().lower()
                ):
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
                bookmaker.get("name")
                or bookmaker.get("title")
                or bookmaker.get("key")
                or ""
            ).strip().lower()

            if nome == BOOKMAKER.strip().lower():
                mercados = bookmaker.get("markets", [])
                return mercados if isinstance(mercados, list) else []

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


def _preco_item(item):
    """Extrai o preco em formatos price/value/odd/odds/decimal."""
    if not isinstance(item, dict):
        return 0.0
    for chave in ("price", "value", "odd", "odds", "decimal"):
        valor = item.get(chave)
        if isinstance(valor, (int, float, str)):
            numero = _numero(valor, 0.0)
            if numero > 0:
                return numero
    return 0.0


def _extrair_outcome(linha, nomes):
    """Busca um outcome mesmo em estruturas alternativas da Odds-API.io."""
    if not isinstance(linha, dict):
        return 0.0

    # Formato oficial: {home, draw, away}
    for nome in nomes:
        valor = linha.get(nome)
        if valor not in (None, ""):
            preco = _preco_item(valor) if isinstance(valor, dict) else _numero(valor, 0.0)
            if preco > 0:
                return preco

    # Formato alternativo: outcomes/selections/items/options
    candidatos = []
    for chave in ("outcomes", "selections", "items", "options"):
        valor = linha.get(chave)
        if isinstance(valor, list):
            candidatos.extend(x for x in valor if isinstance(x, dict))
        elif isinstance(valor, dict):
            candidatos.extend(x for x in valor.values() if isinstance(x, dict))

    alvo = {str(x).strip().lower() for x in nomes}
    for item in candidatos:
        nome = str(item.get("name") or item.get("label") or item.get("selection") or "").strip().lower()
        if nome in alvo:
            preco = _preco_item(item)
            if preco > 0:
                return preco

    # Formato achatado: {name: Home, price: 2.10}
    nome = str(linha.get("name") or linha.get("label") or "").strip().lower()
    if nome in alvo:
        return _preco_item(linha)

    return 0.0


def _linhas_odds(mercado):
    if not isinstance(mercado, dict):
        return []

    valores = mercado.get("odds")

    if isinstance(valores, list):
        return [
            item
            for item in valores
            if isinstance(item, dict)
        ]

    if isinstance(valores, dict):
        return [valores]

    return []


def _valor_odds(linha, *chaves, padrao=0.0):
    """Obtém uma odd aceitando variacoes de maiusculas/minusculas."""
    if not isinstance(linha, dict):
        return padrao

    mapa = {
        str(k).strip().lower(): v
        for k, v in linha.items()
    }

    for chave in chaves:
        valor = mapa.get(
            str(chave).strip().lower()
        )

        if valor not in (None, ""):
            return _numero(valor, padrao)

    return padrao


def _encontrar_mercado(mercados, nomes):
    nomes_normalizados = {
        str(nome)
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
        for nome in nomes
    }

    for mercado in mercados:
        if not isinstance(mercado, dict):
            continue

        nome = str(
            mercado.get("name", "")
        ).strip().lower()

        nome = (
            nome
            .replace("_", " ")
            .replace("-", " ")
        )

        if nome in nomes_normalizados:
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

    return any(
        termo in n
        for termo in (
            "half time",
            "halftime",
            "1st half",
            "first half",
            "1h",
            "ht result",
            "ht totals",
            "half time result",
        )
    )


def _categoria_mercado(nome):
    n = _nome_normalizado(nome)

    if _eh_ht(nome):
        return "HT"

    if "corner" in n or "escante" in n:
        return "CORNERS"

    if (
        "card" in n
        or "cartao" in n
        or "cartões" in n
        or "booking" in n
    ):
        return "CARDS"

    return "FT"


def _extrair_placar(jogo):
    if not isinstance(jogo, dict):
        return 0, 0

    for valor in (
        jogo.get("score"),
        jogo.get("scores"),
        jogo.get("result"),
    ):
        if isinstance(valor, dict):
            casa = valor.get(
                "home",
                valor.get("homeScore"),
            )
            fora = valor.get(
                "away",
                valor.get("awayScore"),
            )

            if casa is not None or fora is not None:
                return (
                    _inteiro(casa),
                    _inteiro(fora),
                )

        elif isinstance(valor, list) and len(valor) >= 2:
            return (
                _inteiro(valor[0]),
                _inteiro(valor[1]),
            )

    return (
        _inteiro(jogo.get("homeScore")),
        _inteiro(jogo.get("awayScore")),
    )


def _extrair_estatisticas(jogo):
    if not isinstance(jogo, dict):
        return 0, 0, 0

    for chave in (
        "statistics",
        "stats",
        "matchStatistics",
    ):
        fonte = jogo.get(chave)

        if isinstance(fonte, dict):
            esc = fonte.get("corners")
            fin = fonte.get("shots")
            atq = fonte.get("dangerousAttacks")

            if (
                esc is not None
                or fin is not None
                or atq is not None
            ):
                return (
                    _inteiro(esc),
                    _inteiro(fin),
                    _inteiro(atq),
                )

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

    evento_odds = _evento_odds_por_id(
        odds,
        event_id,
    )

    evento = evento_odds or jogo
    mercados = _mercados_bet365(evento)

    try:
        nome_casa = (
            jogo.get("home")
            or jogo.get("homeTeam")
            or ""
        )

        nome_fora = (
            jogo.get("away")
            or jogo.get("awayTeam")
            or ""
        )

        print(
            f"ODDS EVENTO | {nome_casa} x {nome_fora} | "
            f"ID={event_id} | "
            f"evento_odds={'SIM' if evento_odds else 'NAO'} | "
            f"BOOKMAKER={BOOKMAKER} | "
            f"mercados={len(mercados)}"
        )

    except Exception:
        pass

    casa, fora = _extrair_placar(jogo)
    esc, fin, atq = _extrair_estatisticas(jogo)

    resultado = {
        "event_id": event_id,
        "odd_home": 0.0,
        "odd_draw": 0.0,
        "odd_away": 0.0,
        "odd_atual": 0.0,
        "odd_pre_live": 0.0,
        "over_linha": 0.0,
        "under_linha": 0.0,
        "odd_over": 0.0,
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
        "todos": [],
        "odds_ft": [],
        "odds_ht": [],
        "odds_corners": [],
        "odds_cards": [],
    }

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

        destino = {
            "HT": "odds_ht",
            "CORNERS": "odds_corners",
            "CARDS": "odds_cards",
          
