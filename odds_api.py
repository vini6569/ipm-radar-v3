# ============================================================
# ODDS API - IPM RADAR V4.7
# ============================================================
#
# CORREÇÕES:
# 1) leitura de clock.minute
# 2) leitura de scores.home / scores.away
# 3) odds/multi em blocos de no máximo 10 IDs
# 4) mantém FT no destino
# 5) estatísticas somente quando realmente existirem
# 6) preserva as 3 odds principais:
#       CASA / EMPATE / VISITANTE
#
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


_IDS_LIVE_SELECIONADOS = []


# ============================================================
# REQUISIÇÃO
# ============================================================

def _request_json(endpoint, params):
    url = (
        f"{BASE_URL}/{endpoint.lstrip('/')}"
        f"?{urllib.parse.urlencode(params)}"
    )

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "IPM-Radar/4.7",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(
            req,
            timeout=TIMEOUT_REQUISICAO
        ) as resp:

            body = resp.read().decode("utf-8")

            print("HTTP STATUS ODDS API:", resp.status)

            return json.loads(body) if body else []

    except urllib.error.HTTPError as e:

        try:
            detalhe = e.read().decode("utf-8")
        except Exception:
            detalhe = ""

        print(
            f"ERRO HTTP ODDS API: {e.code} | "
            f"{detalhe[:500]}"
        )

        return []

    except (urllib.error.URLError, TimeoutError) as e:

        print(
            "ERRO DE CONEXAO ODDS API:",
            e
        )

        return []

    except Exception as e:

        print(
            "ERRO ODDS API:",
            type(e).__name__,
            e
        )

        return []


# ============================================================
# LISTA DE EVENTOS
# ============================================================

def _lista_eventos(resposta):

    if isinstance(resposta, list):
        return [
            x for x in resposta
            if isinstance(x, dict)
        ]

    if not isinstance(resposta, dict):
        return []

    for chave in (
        "events",
        "data",
        "results",
    ):

        valor = resposta.get(chave)

        if isinstance(valor, list):

            return [
                x for x in valor
                if isinstance(x, dict)
            ]

    if resposta.get("id") is not None:
        return [resposta]

    return [
        v for v in resposta.values()
        if isinstance(v, dict)
        and v.get("id") is not None
    ]


# ============================================================
# CONVERSÕES
# ============================================================

def _numero(valor, padrao=0.0):

    try:

        if valor in (None, ""):
            return padrao

        return float(valor)

    except (TypeError, ValueError):

        return padrao


def _inteiro(valor, padrao=0):

    try:

        if valor in (None, ""):
            return padrao

        return int(float(valor))

    except (TypeError, ValueError):

        return padrao


# ============================================================
# MINUTO DO JOGO
# ============================================================

def _extrair_minuto(jogo):

    if not isinstance(jogo, dict):
        return 0

    # ----------------------------------------
    # FORMATO PRINCIPAL:
    # clock: {"minute": 35}
    # ----------------------------------------

    clock = jogo.get("clock")

    if isinstance(clock, dict):

        minuto = _inteiro(
            clock.get("minute"),
            -1
        )

        if minuto >= 0:
            return minuto

    # ----------------------------------------
    # FALLBACKS
    # ----------------------------------------

    for valor in (
        jogo.get("minute"),
        jogo.get("elapsed"),
        jogo.get("timer"),
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

        minuto = _inteiro(
            valor,
            -1
        )

        if minuto >= 0:
            return minuto

    return 0


# ============================================================
# JOGOS AO VIVO
# ============================================================

def buscar_jogos_ao_vivo():

    global _IDS_LIVE_SELECIONADOS

    try:
        key = obter_api_key()

    except Exception as e:

        print(
            "ERRO API KEY:",
            e
        )

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

        print(
            "JOGOS AO VIVO ENCONTRADOS: 0"
        )

        return []

    mapa_eventos = {}

    for evento in eventos:

        event_id = evento.get("id")

        if event_id is not None:

            mapa_eventos[str(event_id)] = evento

    # ----------------------------------------
    # Mantém jogos já selecionados
    # ----------------------------------------

    ids_mantidos = [
        str(event_id)
        for event_id in _IDS_LIVE_SELECIONADOS
        if str(event_id) in mapa_eventos
    ]

    # ----------------------------------------
    # Jogos novos
    # ----------------------------------------

    restantes = [
        evento
        for event_id, evento in mapa_eventos.items()
        if event_id not in ids_mantidos
    ]

    restantes.sort(
        key=_extrair_minuto
    )

    vagas = max(
        0,
        MAX_EVENTOS_POR_CONSULTA
        - len(ids_mantidos)
    )

    for evento in restantes[:vagas]:

        if evento.get("id") is not None:

            ids_mantidos.append(
                str(evento["id"])
            )

    _IDS_LIVE_SELECIONADOS = (
        ids_mantidos[
            :MAX_EVENTOS_POR_CONSULTA
        ]
    )

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
        _IDS_LIVE_SELECIONADOS
    )

    for evento in selecionados:

        nome_casa = (
            evento.get("home")
            or evento.get("homeTeam")
            or ""
        )

        nome_fora = (
            evento.get("away")
            or evento.get("awayTeam")
            or ""
        )

        print(
            f"SELECIONADO | "
            f"{_extrair_minuto(evento)}' | "
            f"{nome_casa} x {nome_fora} | "
            f"ID={evento.get('id')}"
        )

    return selecionados


# ============================================================
# DATA DO EVENTO
# ============================================================

def _parse_data_evento(evento):

    valor = (
        evento.get("date")
        or evento.get("startTime")
        or evento.get("start_time")
    )

    if not valor:
        return None

    try:

        dt = datetime.fromisoformat(
            str(valor).replace(
                "Z",
                "+00:00"
            )
        )

        if dt.tzinfo is None:

            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            timezone.utc
        )

    except Exception:

        return None


# ============================================================
# JOGOS PRÉ-LIVE
# ============================================================

def buscar_jogos_pre_live():

    try:
        key = obter_api_key()

    except Exception as e:

        print(
            "ERRO API KEY:",
            e
        )

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

    eventos = _lista_eventos(
        resposta
    )

    agora = datetime.now(
        timezone.utc
    )

    agora_ts = agora.timestamp()

    limite = (
        agora_ts
        + PRE_LIVE_JANELA_MINUTOS * 60
    )

    proximos = []

    for evento in eventos:

        dt = _parse_data_evento(
            evento
        )

        if dt is None:
            continue

        ts = dt.timestamp()

        if agora_ts <= ts <= limite:

            proximos.append(
                evento
            )

    proximos.sort(
        key=lambda e: (
            _parse_data_evento(e)
            or agora
        )
    )

    proximos = proximos[
        :MAX_EVENTOS_POR_CONSULTA
    ]

    print(
        "JOGOS PRE-LIVE PROXIMOS:",
        len(proximos)
    )

    return proximos


# ============================================================
# ODDS MULTI
# ============================================================

def buscar_odds_multiplos(eventos):

    if not eventos:

        print(
            "ODDS MULTI: nenhum evento recebido."
        )

        return []

    try:
        key = obter_api_key()

    except Exception as e:

        print(
            "ERRO API KEY:",
            e
        )

        return []

    ids = [
        str(evento["id"])
        for evento in eventos
        if isinstance(evento, dict)
        and evento.get("id") is not None
    ]

    # Remove duplicados
    ids = list(
        dict.fromkeys(ids)
    )

    ids = ids[
        :MAX_EVENTOS_POR_CONSULTA
    ]

    if not ids:

        print(
            "ODDS MULTI: nenhum ID valido."
        )

        return []

    print("=" * 70)
    print("DIAGNOSTICO ODDS MULTI V4.7")
    print(
        f"EVENTOS SOLICITADOS: {len(ids)}"
    )
    print(
        f"IDS SOLICITADOS: {ids}"
    )
    print(
        f"LIMITE CONFIGURADO: "
        f"{MAX_EVENTOS_POR_CONSULTA}"
    )

    resultados = []

    # ========================================================
    # IMPORTANTE:
    # API recebe no máximo 10 IDs por consulta
    # ========================================================

    for inicio in range(
        0,
        len(ids),
        10
    ):

        bloco = ids[
            inicio:inicio + 10
        ]

        print("-" * 70)

        print(
            f"CONSULTA ODDS "
            f"{inicio // 10 + 1}: "
            f"{len(bloco)} eventos"
        )

        print(
            "IDS:",
            bloco
        )

        resposta = _request_json(
            "/odds/multi",
            {
                "apiKey": key,
                "eventIds": ",".join(bloco),
                "bookmakers": BOOKMAKER,
            },
        )

        eventos_odds = _lista_eventos(
            resposta
        )

        print(
            "RESPOSTA ODDS MULTI:",
            type(resposta).__name__
        )

        print(
            "EVENTOS COM ODDS RECEBIDOS:",
            len(eventos_odds)
        )

        resultados.extend(
            eventos_odds
        )

        # Diagnóstico dos dois primeiros
        # eventos de cada bloco

        for event_id in bloco[:2]:

            item = _evento_odds_por_id(
                eventos_odds,
                event_id
            )

            print("-" * 70)

            print(
                f"TESTE EVENT_ID: {event_id}"
            )

            if item is None:

                print(
                    "EVENTO NAO ENCONTRADO "
                    "NA RESPOSTA DE ODDS."
                )

                continue

            print(
                "EVENTO ENCONTRADO "
                "NA RESPOSTA DE ODDS."
            )

            print(
                "CHAVES DO EVENTO:",
                list(item.keys())[:20]
            )

            bookmakers = item.get(
                "bookmakers"
            )

            if isinstance(
                bookmakers,
                dict
            ):

                print(
                    "BOOKMAKERS: dict | "
                    "CHAVES:",
                    list(
                        bookmakers.keys()
                    )[:20],
                )

            elif isinstance(
                bookmakers,
                list
            ):

                nomes = []

                for bookmaker in bookmakers[:20]:

                    if isinstance(
                        bookmaker,
                        dict
                    ):

                        nomes.append(
                            bookmaker.get("name")
                            or bookmaker.get("title")
                            or bookmaker.get("key")
                        )

                print(
                    "BOOKMAKERS: list | "
                    "NOMES:",
                    nomes
                )

            else:

                print(
                    "BOOKMAKERS:",
                    type(bookmakers).__name__
                )

    print("=" * 70)

    return resultados


# ============================================================
# ENCONTRAR EVENTO NAS ODDS
# ============================================================

def _evento_odds_por_id(
    odds,
    event_id
):

    if event_id is None:
        return None

    alvo = str(event_id)

    if isinstance(odds, list):

        for item in odds:

            if (
                isinstance(item, dict)
                and str(item.get("id"))
                == alvo
            ):

                return item

    if isinstance(odds, dict):

        if str(
            odds.get("id")
        ) == alvo:

            return odds

        item = odds.get(alvo)

        if isinstance(
            item,
            dict
        ):

            return item

    return None


# ============================================================
# MERCADOS BET365
# ============================================================

def _mercados_bet365(evento):

    if not isinstance(
        evento,
        dict
    ):

        return []

    bookmakers = evento.get(
        "bookmakers",
        {}
    )

    # ----------------------------------------
    # bookmakers como dict
    # ----------------------------------------

    if isinstance(
        bookmakers,
        dict
    ):

        mercados = bookmakers.get(
            BOOKMAKER
        )

        if isinstance(
            mercados,
            dict
        ):

            mercados = mercados.get(
                "markets",
                []
            )

        if mercados is None:

            for nome, valor in bookmakers.items():

                if (
                    str(nome).strip().lower()
                    ==
                    BOOKMAKER.strip().lower()
                ):

                    mercados = valor
                    break

        if isinstance(
            mercados,
            dict
        ):

            mercados = mercados.get(
                "markets",
                []
            )

        return (
            mercados
            if isinstance(
                mercados,
                list
            )
            else []
        )

    # ----------------------------------------
    # bookmakers como list
    # ----------------------------------------

    if isinstance(
        bookmakers,
        list
    ):

        for bookmaker in bookmakers:

            if not isinstance(
                bookmaker,
                dict
            ):

                continue

            nome = str(
                bookmaker.get("name")
                or bookmaker.get("title")
                or bookmaker.get("key")
                or ""
            ).strip().lower()

            if (
                nome
                ==
                BOOKMAKER.strip().lower()
            ):

                mercados = bookmaker.get(
                    "markets",
                    []
                )

                return (
                    mercados
                    if isinstance(
                        mercados,
                        list
                    )
                    else []
                )

    return []


# ============================================================
# PREÇO DA ODD
# ============================================================

def _preco_item(item):

    if not isinstance(
        item,
        dict
    ):

        return 0.0

    for chave in (
        "price",
        "value",
        "odd",
        "odds",
        "decimal",
    ):

        valor = item.get(
            chave
        )

        if isinstance(
            valor,
            (int, float, str)
        ):

            numero = _numero(
                valor,
                0.0
            )

            if numero > 0:
                return numero

    return 0.0


# ============================================================
# OUTCOME
# ============================================================

def _extrair_outcome(
    linha,
    nomes
):

    if not isinstance(
        linha,
        dict
    ):

        return 0.0

    # ----------------------------------------
    # Busca direta
    # ----------------------------------------

    for nome in nomes:

        valor = linha.get(
            nome
        )

        if valor not in (
            None,
            ""
        ):

            preco = (
                _preco_item(valor)
                if isinstance(
                    valor,
                    dict
                )
                else _numero(
                    valor,
                    0.0
                )
            )

            if preco > 0:
                return preco

    # ----------------------------------------
    # Busca em outcomes/selections/items
    # ----------------------------------------

    candidatos = []

    for chave in (
        "outcomes",
        "selections",
        "items",
        "options",
    ):

        valor = linha.get(
            chave
        )

        if isinstance(
            valor,
            list
        ):

            candidatos.extend(
                x for x in valor
                if isinstance(
                    x,
                    dict
                )
            )

        elif isinstance(
            valor,
            dict
        ):

            candidatos.extend(
                x for x in valor.values()
                if isinstance(
                    x,
                    dict
                )
            )

    alvo = {
        str(x).strip().lower()
        for x in nomes
    }

    for item in candidatos:

        nome = str(
            item.get("name")
            or item.get("label")
            or item.get("selection")
            or ""
        ).strip().lower()

        if nome in alvo:

            preco = _preco_item(
                item
            )

            if preco > 0:
                return preco

    # ----------------------------------------
    # A própria linha pode ser o outcome
    # ----------------------------------------

    nome = str(
        linha.get("name")
        or linha.get("label")
        or ""
    ).strip().lower()

    if nome in alvo:

        return _preco_item(
            linha
        )

    return 0.0


# ============================================================
# LINHAS DAS ODDS
# ============================================================

def _linhas_odds(mercado):

    if not is
