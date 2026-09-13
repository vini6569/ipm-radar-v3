# ============================================================
# ODDS API - IPM RADAR V5.2
# CASA / EMPATE / VISITANTE
# TOTALS + BTTS + OUTROS MERCADOS
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


# ============================================================
# MEMÓRIA LIVE
# ============================================================

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
            "User-Agent": "IPM-Radar/5.2",
            "Accept": "application/json",
        },
    )

    try:

        with urllib.request.urlopen(
            req,
            timeout=TIMEOUT_REQUISICAO,
        ) as resp:

            body = resp.read().decode("utf-8")

            print(
                "HTTP STATUS ODDS API:",
                resp.status,
            )

            return (
                json.loads(body)
                if body
                else []
            )

    except urllib.error.HTTPError as erro:

        try:
            detalhe = erro.read().decode("utf-8")
        except Exception:
            detalhe = ""

        print(
            f"ERRO HTTP ODDS API: "
            f"{erro.code} | "
            f"{detalhe[:500]}"
        )

        return []

    except (
        urllib.error.URLError,
        TimeoutError,
    ) as erro:

        print(
            "ERRO DE CONEXAO ODDS API:",
            erro,
        )

        return []

    except Exception as erro:

        print(
            "ERRO ODDS API:",
            type(erro).__name__,
            erro,
        )

        return []


# ============================================================
# LISTA DE EVENTOS
# ============================================================

def _lista_eventos(resposta):

    if isinstance(resposta, list):

        return [
            x
            for x in resposta
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
                x
                for x in valor
                if isinstance(x, dict)
            ]

    if resposta.get("id") is not None:
        return [resposta]

    return [
        valor
        for valor in resposta.values()
        if isinstance(valor, dict)
        and valor.get("id") is not None
    ]


# ============================================================
# CONVERSÕES
# ============================================================

def _numero(valor, padrao=0.0):

    try:

        if valor in (None, ""):
            return padrao

        return float(valor)

    except (
        TypeError,
        ValueError,
    ):

        return padrao


def _inteiro(valor, padrao=0):

    try:

        if valor in (None, ""):
            return padrao

        return int(float(valor))

    except (
        TypeError,
        ValueError,
    ):

        return padrao


# ============================================================
# MINUTO
# ============================================================

def _extrair_minuto(jogo):

    if not isinstance(jogo, dict):
        return 0

    clock = jogo.get("clock")

    if isinstance(clock, dict):

        minuto = _inteiro(
            clock.get("minute"),
            -1,
        )

        if minuto >= 0:
            return minuto

    for valor in (
        jogo.get("minute"),
        jogo.get("elapsed"),
        jogo.get("timer"),
    ):

        if isinstance(valor, dict):

            valor = valor.get(
                "minute",
                valor.get("elapsed"),
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
            -1,
        )

        if minuto >= 0:
            return minuto

    return 0


# ============================================================
# PLACAR
# ============================================================

def _extrair_placar(jogo):

    for valor in (
        jogo.get("scores"),
        jogo.get("score"),
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

            if (
                casa is not None
                or fora is not None
            ):

                return (
                    _inteiro(casa),
                    _inteiro(fora),
                )

        elif (
            isinstance(valor, list)
            and len(valor) >= 2
        ):

            return (
                _inteiro(valor[0]),
                _inteiro(valor[1]),
            )

    return (
        _inteiro(
            jogo.get("homeScore")
        ),
        _inteiro(
            jogo.get("awayScore")
        ),
    )


# ============================================================
# ESTATÍSTICAS
# ============================================================

def _extrair_estatisticas(jogo):

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
            cart = fonte.get("cards")

            if (
                esc is not None
                or fin is not None
                or atq is not None
                or cart is not None
            ):

                return (
                    _inteiro(esc),
                    _inteiro(fin),
                    _inteiro(atq),
                    _inteiro(cart),
                )

    return 0, 0, 0, 0


# ============================================================
# LIVE
# ============================================================

def buscar_jogos_ao_vivo():

    global _IDS_LIVE_SELECIONADOS

    try:
        key = obter_api_key()

    except Exception as erro:

        print(
            "ERRO API KEY:",
            erro,
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

    mapa = {}

    for evento in eventos:

        event_id = evento.get("id")

        if event_id is not None:

            mapa[str(event_id)] = evento

    ids_mantidos = [
        str(event_id)
        for event_id in _IDS_LIVE_SELECIONADOS
        if str(event_id) in mapa
    ]

    restantes = [
        evento
        for event_id, evento in mapa.items()
        if event_id not in ids_mantidos
    ]

    restantes.sort(
        key=_extrair_minuto
    )

    vagas = max(
        0,
        MAX_EVENTOS_POR_CONSULTA
        - len(ids_mantidos),
    )

    for evento in restantes[:vagas]:

        ids_mantidos.append(
            str(evento["id"])
        )

    _IDS_LIVE_SELECIONADOS = ids_mantidos[
        :MAX_EVENTOS_POR_CONSULTA
    ]

    selecionados = [
        mapa[event_id]
        for event_id
        in _IDS_LIVE_SELECIONADOS
        if event_id in mapa
    ]

    print(
        "JOGOS AO VIVO ENCONTRADOS:",
        len(eventos),
        "| SELECIONADOS:",
        len(selecionados),
    )

    for evento in selecionados:

        print(
            "SELECIONADO | "
            f"{_extrair_minuto(evento)}' | "
            f"{evento.get('home', '')} x "
            f"{evento.get('away', '')} | "
            f"ID={evento.get('id')}"
        )

    return selecionados


# ============================================================
# LIVE POR IDS
# ============================================================

def buscar_jogos_ao_vivo_por_ids(ids):

    if not ids:

        print(
            "LIVE POR IDS: nenhum ID recebido."
        )

        return []

    try:
        key = obter_api_key()

    except Exception as erro:

        print(
            "ERRO API KEY:",
            erro,
        )

        return []

    ids_alvo = [
        str(event_id)
        for event_id in ids
        if event_id is not None
    ]

    ids_alvo = list(
        dict.fromkeys(ids_alvo)
    )

    if not ids_alvo:
        return []

    resposta = _request_json(
        "/events/live",
        {
            "apiKey": key,
            "sport": SPORT,
        },
    )

    eventos = _lista_eventos(resposta)

    mapa = {}

    for evento in eventos:

        event_id = evento.get("id")

        if event_id is None:
            continue

        mapa[str(event_id)] = evento

    selecionados = []

    for event_id in ids_alvo:

        evento = mapa.get(event_id)

        if evento is not None:

            selecionados.append(evento)

    print(
        "LIVE POR IDS | "
        f"SOLICITADOS={len(ids_alvo)} | "
        f"ENCONTRADOS={len(selecionados)}"
    )

    for evento in selecionados:

        print(
            "LIVE MONITORADO | "
            f"{_extrair_minuto(evento)}' | "
            f"{evento.get('home', '')} x "
            f"{evento.get('away', '')} | "
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
                "+00:00",
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
# PRÉ-LIVE
# ============================================================

def buscar_jogos_pre_live():

    try:
        key = obter_api_key()

    except Exception as erro:

        print(
            "ERRO API KEY:",
            erro,
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

    eventos = _lista_eventos(resposta)

    agora = datetime.now(
        timezone.utc
    )

    limite = (
        agora.timestamp()
        + PRE_LIVE_JANELA_MINUTOS * 60
    )

    proximos = []

    for evento in eventos:

        dt = _parse_data_evento(evento)

        if dt is None:
            continue

        if (
            agora.timestamp()
            <= dt.timestamp()
            <= limite
        ):

            proximos.append(evento)

    proximos.sort(
        key=lambda e:
        _parse_data_evento(e)
        or agora
    )

    proximos = proximos[
        :MAX_EVENTOS_POR_CONSULTA
    ]

    print(
        "JOGOS PRE-LIVE PROXIMOS:",
        len(proximos),
    )

    return proximos


# ============================================================
# ODDS MULTIPLAS
# ============================================================

def buscar_odds_multiplos(eventos):

    if not eventos:

        print(
            "ODDS MULTI: nenhum evento recebido."
        )

        return []

    try:
        key = obter_api_key()

    except Exception as erro:

        print(
            "ERRO API KEY:",
            erro,
        )

        return []

    ids = [
        str(evento["id"])
        for evento in eventos
        if isinstance(evento, dict)
        and evento.get("id") is not None
    ]

    ids = list(
        dict.fromkeys(ids)
    )

    ids = ids[
        :MAX_EVENTOS_POR_CONSULTA
    ]

    if not ids:
        return []

    resultados = []

    for inicio in range(
        0,
        len(ids),
        10,
    ):

        bloco = ids[
            inicio:inicio + 10
        ]

        print(
            f"CONSULTA ODDS "
            f"{inicio // 10 + 1}: "
            f"{len(bloco)} eventos | "
            f"IDS={bloco}"
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
            "EVENTOS COM ODDS RECEBIDOS:",
            len(eventos_odds),
        )

        resultados.extend(
            eventos_odds
        )

    return resultados


# ============================================================
# ENCONTRAR ODDS POR ID
# ============================================================

def _evento_odds_por_id(
    odds,
    event_id,
):

    if event_id is None:
        return None

    alvo = str(event_id)

    if isinstance(odds, list):

        for item in odds:

            if (
                isinstance(item, dict)
                and str(
                    item.get("id")
                ) == alvo
            ):

                return item

    if isinstance(odds, dict):

        if str(
            odds.get("id")
        ) == alvo:

            return odds

        item = odds.get(alvo)

        if isinstance(item, dict):
            return item

    return None


# ============================================================
# BOOKMAKER
# ============================================================

def _mercados_bookmaker(evento):

    if not isinstance(evento, dict):
        return []

    bookmakers = evento.get(
        "bookmakers",
        {},
    )

    # ----------------------------
    # FORMATO DICT
    # ----------------------------

    if isinstance(bookmakers, dict):

        mercados = bookmakers.get(
            BOOKMAKER
        )

        if mercados is None:

            for nome, valor in bookmakers.items():

                if (
                    str(nome)
                    .strip()
                    .lower()
                    ==
                    BOOKMAKER
                    .strip()
                    .lower()
                ):

                    mercados = valor
                    break

        if isinstance(
            mercados,
            dict,
        ):

            mercados = mercados.get(
                "markets",
                []
            )

        return (
            mercados
            if isinstance(
                mercados,
                list,
            )
            else []
        )

    # ----------------------------
    # FORMATO LISTA
    # ----------------------------

    if isinstance(
        bookmakers,
        list,
    ):

        for bookmaker in bookmakers:

            if not isinstance(
                bookmaker,
                dict,
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
                BOOKMAKER
                .strip()
                .lower()
            ):

                mercados = bookmaker.get(
                    "markets",
                    [],
                )

                return (
                    mercados
                    if isinstance(
                        mercados,
                        list,
                    )
                    else []
                )

    return []


# ============================================================
# COMPATIBILIDADE
# ============================================================

def _mercados_bet365(evento):

    return _mercados_bookmaker(evento)


# ============================================================
# LINHAS DE ODDS
# ============================================================

def _linhas_odds(mercado):

    if not isinstance(
        mercado,
        dict,
    ):
        return []

    valores = mercado.get(
        "odds"
    )

    if isinstance(
        valores,
        list,
    ):

        return [
            item
            for item in valores
            if isinstance(
                item,
                dict,
            )
        ]

    if isinstance(
        valores,
        dict,
    ):

        return [valores]

    return []


# ============================================================
# PREÇO
# ============================================================

def _preco_item(item):

    if not isinstance(
        item,
        dict,
    ):
        return 0.0

    for chave in (
        "price",
        "value",
        "odd",
        "odds",
        "decimal",
    ):

        valor = item.get(chave)

        if isinstance(
            valor,
            (
                int,
                float,
                str,
            ),
        ):

            numero = _numero(valor)

            if numero > 0:
                return numero

    return 0.0


# ============================================================
# EXTRAIR OUTCOME
# ============================================================

def _extrair_outcome(
    linha,
    nomes,
):

    if not isinstance(
        linha,
        dict,
    ):
        return 0.0

    alvo = {
        str(nome)
        .strip()
        .lower()
        for nome in nomes
    }

    # --------------------------------------------------------
    # CAMPOS DIRETOS
    # --------------------------------------------------------

    for nome in nomes:

        valor = linha.get(nome)

        if valor not in (
            None,
            "",
        ):

            if isinstance(
                valor,
                dict,
            ):

                preco = _preco_item(
                    valor
                )

            else:

                preco = _numero(
                    valor
                )

            if preco > 0:
                return preco

    # --------------------------------------------------------
    # OUTCOMES / SELECTIONS / ITEMS
    # --------------------------------------------------------

    for chave in (
        "outcomes",
        "selections",
        "items",
        "options",
    ):

        valor = linha.get(chave)

        if isinstance(
            valor,
            list,
        ):

            candidatos = [
                item
                for item in valor
                if isinstance(
                    item,
                    dict,
                )
            ]

        elif isinstance(
            valor,
            dict,
        ):

            candidatos = [
                item
                for item in valor.values()
                if isinstance(
                    item,
                    dict,
                )
            ]

        else:

            candidatos = []

        for item in candidatos:

            nome = str(
                item.get("name")
                or item.get("label")
                or item.get("selection")
                or item.get("key")
                or ""
            ).strip().lower()

            if nome in alvo:

                preco = _preco_item(
                    item
                )

                if preco > 0:
                    return preco

    # --------------------------------------------------------
    # LINHA DIRETA
    # --------------------------------------------------------

    nome = str(
        linha.get("name")
        or linha.get("label")
        or linha.get("selection")
        or ""
    ).strip().lower()

    if nome in alvo:

        return _preco_item(
            linha
        )

    return 0.0


# ============================================================
# NOME DO MERCADO
# ============================================================

def _nome_mercado(mercado):

    return str(
        mercado.get("name")
        or mercado.get("key")
        or mercado.get("market")
        or ""
    ).strip()


def _nome_mercado_lower(mercado):

    return _nome_mercado(
        mercado
    ).lower()


# ============================================================
# ENCONTRAR MERCADO POR NOME
# ============================================================

def _encontrar_mercado(
    mercados,
    nomes,
):

    procurados = {
        str(nome)
        .strip()
        .lower()
        for nome in nomes
    }

    for mercado in mercados:

        if not isinstance(
            mercado,
            dict,
        ):
            continue

        nome = _nome_mercado_lower(
            mercado
        )

        if nome in procurados:
            return mercado

    return None


# ============================================================
# 1X2
# ============================================================

def _encontrar_1x2(mercados):

    nomes = (
        "ml",
        "moneyline",
        "1x2",
        "match winner",
        "match result",
        "full time result",
        "winner",
        "h2h",
        "head to head",
    )

    # --------------------------------------------------------
    # PRIMEIRO: NOME EXATO
    # --------------------------------------------------------

    for mercado in mercados:

        nome = _nome_mercado_lower(
            mercado
        )

        if nome not in nomes:
            continue

        linhas = _linhas_odds(
            mercado
        )

        for linha in linhas:

            casa = _extrair_outcome(
                linha,
                (
                    "home",
                    "1",
                ),
            )

            empate = _extrair_outcome(
                linha,
                (
                    "draw",
                    "x",
                    "tie",
                ),
            )

            fora = _extrair_outcome(
                linha,
                (
                    "away",
                    "2",
                ),
            )

            if (
                casa > 0
                or empate > 0
                or fora > 0
            ):

                return (
                    casa,
                    empate,
                    fora,
                )

    # --------------------------------------------------------
    # SEGUNDO: PROCURA MAIS FLEXÍVEL
    # --------------------------------------------------------

    for mercado in mercados:

        nome = _nome_mercado_lower(
            mercado
        )

        if not (
            "moneyline" in nome
            or "match winner" in nome
            or nome == "ml"
            or "1x2" in nome
            or nome == "h2h"
        ):
            continue

        linhas = _linhas_odds(
            mercado
        )

        for linha in linhas:

            casa = _extrair_outcome(
                linha,
                (
                    "home",
                    "1",
                ),
            )

            empate = _extrair_outcome(
                linha,
                (
                    "draw",
                    "x",
                    "tie",
                ),
            )

            fora = _extrair_outcome(
                linha,
                (
                    "away",
                    "2",
                ),
            )

            if (
                casa > 0
                or empate > 0
                or fora > 0
            ):

                return (
                    casa,
                    empate,
                    fora,
                )

    return (
        0.0,
        0.0,
        0.0,
    )


# ============================================================
# TOTALS
# ============================================================

def _extrair_totals(mercados):

    mercado = _encontrar_mercado(
        mercados,
        (
            "Totals",
            "Total",
            "Over/Under",
            "Over Under",
            "O/U",
            "Totals - Over/Under",
            "Goals Over/Under",
        ),
    )

    if not mercado:

        # Busca flexível
        for item in mercados:

            nome = _nome_mercado_lower(
                item
            )

            if (
                "total" in nome
                or "over/under" in nome
                or "over under" in nome
            ):

                mercado = item
                break

    if not mercado:

        return (
            0.0,
            0.0,
            0.0,
            0.0,
        )

    linhas = _linhas_odds(
        mercado
    )

    over_linha = 0.0
    under_linha = 0.0
    odd_over = 0.0
    odd_under = 0.0

    # --------------------------------------------------------
    # CASO 1: linha contém over/under diretamente
    # --------------------------------------------------------

    for linha in linhas:

        if not isinstance(
            linha,
            dict,
        ):
            continue

        hdp = _numero(
            linha.get("hdp"),
            _numero(
                linha.get("handicap")
            ),
        )

        if hdp <= 0:

            hdp = _numero(
                linha.get("line")
            )

        over = _extrair_outcome(
            linha,
            (
                "over",
                "Over",
            ),
        )

        under = _extrair_outcome(
            linha,
            (
                "under",
                "Under",
            ),
        )

        if (
            over > 0
            and under > 0
        ):

            over_linha = hdp
            under_linha = hdp
            odd_over = over
            odd_under = under

            return (
                over_linha,
                under_linha,
                odd_over,
                odd_under,
            )

    # --------------------------------------------------------
    # CASO 2: cada linha é uma seleção
    # Exemplo: Over 2.5 / Under 2.5
    # --------------------------------------------------------

    for linha in linhas:

        nome = str(
            linha.get("name")
            or linha.get("label")
            or linha.get("selection")
            or ""
        ).strip()

        nome_lower = nome.lower()

        preco = _preco_item(
            linha
        )

        hdp = _numero(
            linha.get("hdp"),
            _numero(
                linha.get("handicap")
            ),
        )

        if hdp <= 0:

            hdp = _numero(
                linha.get("line")
            )

        # tenta descobrir a linha no nome
        if hdp <= 0:

            partes = nome_lower.replace(
                ",",
                ".",
            ).split()

            for parte in partes:

                try:

                    numero_linha = float(
                        parte
                    )

                    if (
                        0.5
                        <= numero_linha
                        <= 20
                    ):

                        hdp = numero_linha
                        break

                except Exception:
                    pass

        if (
            "over" in nome_lower
            and preco > 0
        ):

            if (
                odd_over <= 0
                or (
                    hdp > 0
                    and (
                        over_linha <= 0
                        or hdp == over_linha
                    )
                )
            ):

                odd_over = preco

                if hdp > 0:
                    over_linha = hdp

        elif (
            "under" in nome_lower
            and preco > 0
        ):

            if (
                odd_under <= 0
                or (
                    hdp > 0
                    and (
                        under_linha <= 0
                        or hdp == under_linha
                    )
                )
            ):

                odd_under = preco

                if hdp > 0:
                    under_linha = hdp

    if (
        over_linha <= 0
        and under_linha > 0
    ):
        over_linha = under_linha

    if (
        under_linha <= 0
        and over_linha > 0
    ):
        under_linha = over_linha

    return (
        over_linha,
        under_linha,
        odd_over,
        odd_under,
    )


# ============================================================
# BTTS
# ============================================================

def _extrair_btts(mercados):

    mercado = _encontrar_mercado(
        mercados,
        (
            "Both Teams To Score",
            "BTTS",
            "Both Teams Score",
            "Both Teams To Score - Yes/No",
        ),
    )

    if not mercado:

        for item in mercados:

            nome = _nome_mercado_lower(
                item
            )

            if (
                "both teams to score"
                in nome
                or nome == "btts"
                or "both teams score"
                in nome
            ):

                mercado = item
                break

    if not mercado:

        return (
            0.0,
            0.0,
        )

    linhas = _linhas_odds(
        mercado
    )

    odd_sim = 0.0
    odd_nao = 0.0

    # --------------------------------------------------------
    # CASO 1: yes/no diretamente
    # --------------------------------------------------------

    for linha in linhas:

        sim = _extrair_outcome(
            linha,
            (
                "yes",
                "sim",
            ),
        )

        nao = _extrair_outcome(
            linha,
            (
                "no",
                "não",
                "nao",
            ),
        )

        if sim > 0:
            odd_sim = sim

        if nao > 0:
            odd_nao = nao

        if (
            odd_sim > 0
            and odd_nao > 0
        ):

            return (
                odd_sim,
                odd_nao,
            )

    # --------------------------------------------------------
    # CASO 2: linhas individuais
    # --------------------------------------------------------

    for linha in linhas:

        nome = str(
            linha.get("name")
            or linha.get("label")
            or linha.get("selection")
            or ""
        ).strip().lower()

        preco = _preco_item(
            linha
        )

        if preco <= 0:
            continue

        if (
            nome in (
                "yes",
                "sim",
            )
            or "yes" == nome
        ):

            odd_sim = preco

        elif nome in (
            "no",
            "não",
            "nao",
        ):

            odd_nao = preco

    return (
        odd_sim,
        odd_nao,
    )


# ============================================================
# HANDICAP
# ============================================================

def _extrair_handicap(mercados):

    mercado = _encontrar_mercado(
        mercados,
        (
            "Spread",
            "Asian Handicap",
            "Handicap",
            "Asian Handicap 3-Way",
        ),
    )

    if not mercado:

        return (
            0.0,
            0.0,
            0.0,
        )

    linhas = _linhas_odds(
        mercado
    )

    for linha in linhas:

        hdp = _numero(
            linha.get("hdp")
        )

        home = _extrair_outcome(
            linha,
            (
                "home",
                "1",
            ),
        )

        away = _extrair_outcome(
            linha,
            (
                "away",
                "2",
            ),
        )

        if (
            home > 0
            or away > 0
        ):

            return (
                hdp,
                home,
                away,
            )

    return (
        0.0,
        0.0,
        0.0,
    )


# ============================================================
# DOUBLE CHANCE
# ============================================================

def _extrair_double_chance(mercados):

    mercado = _encontrar_mercado(
        mercados,
        (
            "Double Chance",
            "DoubleChance",
            "DC",
        ),
    )

    if not mercado:

        return (
            0.0,
            0.0,
            0.0,
        )

    linhas = _linhas_odds(
        mercado
    )

    for linha in linhas:

        x1 = _extrair_outcome(
            linha,
            ("1X",),
        )

        x12 = _extrair_outcome(
            linha,
            ("12",),
        )

        x2 = _extrair_outcome(
            linha,
            ("X2",),
        )

        if (
            x1 > 0
            or x12 > 0
            or x2 > 0
        ):

            return (
                x1,
                x12,
                x2,
            )

    return (
        0.0,
        0.0,
        0.0,
    )


# ============================================================
# DRAW NO BET
# ============================================================

def _extrair_dnb(mercados):

    mercado = _encontrar_mercado(
        mercados,
        (
            "Draw No Bet",
            "DrawNoBet",
            "DNB",
        ),
    )

    if not mercado:

        return (
            0.0,
            0.0,
        )

    linhas = _linhas_odds(
        mercado
    )

    for linha in linhas:

        home = _extrair_outcome(
            linha,
            (
                "home",
                "1",
            ),
        )

        away = _extrair_outcome(
            linha,
            (
                "away",
                "2",
            ),
        )

        if (
            home > 0
            or away > 0
        ):

            return (
                home,
                away,
            )

    return (
        0.0,
        0.0,
    )


# ============================================================
# CATEGORIA DO MERCADO
# ============================================================

def _categoria_mercado(nome):

    nome_lower = str(
        nome
    ).strip().lower()

    if (
        "half" in nome_lower
        or "halftime" in nome_lower
        or "1st half" in nome_lower
        or "2nd half" in nome_lower
    ):

        return "HT"

    if (
        "corner" in nome_lower
        or "escante" in nome_lower
    ):

        return "CORNERS"

    if (
        "card" in nome_lower
        or "booking" in nome_lower
        or "cart" in nome_lower
    ):

        return "CARDS"

    return "FT"


# ============================================================
# CÓPIA PADRONIZADA DO MERCADO
# ============================================================

def _copiar_mercado(mercado):

    return {
        "name": (
            mercado.get("name")
            or mercado.get("key")
            or mercado.get("market")
            or ""
        ),

        "updatedAt":
            mercado.get("updatedAt"),

        "odds":
            _linhas_odds(mercado),
    }


# ============================================================
# PRIMEIRA LINHA
# ============================================================

def _primeiro_odds(mercado):

    linhas = _linhas_odds(
        mercado
    )

    if linhas:
        return linhas[0]

    return {}


# ============================================================
# EXTRAÇÃO PRINCIPAL DOS MERCADOS
# ============================================================

def extrair_mercados(
    jogo,
    odds,
):

    if not isinstance(
        jogo,
        dict,
    ):
        return {}

    event_id = jogo.get("id")

    evento = (
        _evento_odds_por_id(
            odds,
            event_id,
        )
        or jogo
    )

    mercados = _mercados_bookmaker(
        evento
    )

    placar_casa, placar_fora = (
        _extrair_placar(jogo)
    )

    esc, fin, atq, cart = (
        _extrair_estatisticas(jogo)
    )

    # ========================================================
    # 1X2
    # ========================================================

    (
        odd_casa,
        odd_draw,
        odd_away,
    ) = _encontrar_1x2(
        mercados
    )

    # ========================================================
    # Q PRÉ-LIVE
    # ========================================================

    q_pre_live = 0.0

    if (
        odd_casa > 0
        and odd_away > 0
    ):

        q_pre_live = (
            2.0
            * odd_casa
            * odd_away
            / (
                odd_casa
                + odd_away
            )
        )

    
    # ========================================================
    # RESULTADO BASE
    # ========================================================

    resultado = {

        "event_id": event_id,

        # 1X2
        "odd_home": odd_casa,
        "odd_draw": odd_draw,
        "odd_away": odd_away,

        # ALIASES IPM
        "odd_casa": odd_casa,
        "odd_atual": odd_draw,
        "odd_empate": odd_draw,
        "odd_visitante": odd_away,

        # Q
        "odd_pre_live": q_pre_live,

        # JOGO
        "minuto":
            _extrair_minuto(jogo),

        "gols":
            placar_casa + placar_fora,

        "escanteios":
            esc,

        "cartoes":
            cart,

        "finalizacoes":
            fin,

        "ataques_perigosos":
            atq,

        # MERCADOS
        "mercados_encontrados": [],

        "mercados_disponiveis": [],

        "todos": [],

        "odds_ft": [],

        "odds_ht": [],

        "odds_corners": [],

        "odds_cards": [],

        # TOTALS
        "over_linha": 0.0,
        "under_linha": 0.0,
        "odd_over": 0.0,
        "odd_under": 0.0,

        # BTTS
        "odd_btts_sim": 0.0,
        "odd_btts_nao": 0.0,

        # HANDICAP
        "handicap_linha": 0.0,
        "odd_handicap_home": 0.0,
        "odd_handicap_away": 0.0,

        # DOUBLE CHANCE
        "odd_1x": 0.0,
        "odd_12": 0.0,
        "odd_x2": 0.0,

        # DNB
        "odd_dnb_home": 0.0,
        "odd_dnb_away": 0.0,
    }

    # ========================================================
    # MERCADOS DISPONÍVEIS
    # ========================================================

    for mercado in mercados:

        if not isinstance(
            mercado,
            dict,
        ):
            continue

        nome = str(
            mercado.get("name")
            or mercado.get("key")
            or mercado.get("market")
            or ""
        ).strip()

        if not nome:
            continue

        item = _copiar_mercado(
            mercado
        )

        item["categoria"] = (
            _categoria_mercado(nome)
        )

        resultado["todos"].append(
            item
        )

        resultado[
            "mercados_disponiveis"
        ].append(nome)

        categoria = item[
            "categoria"
        ]

        destino = {
            "HT": "odds_ht",
            "CORNERS": "odds_corners",
            "CARDS": "odds_cards",
            "FT": "odds_ft",
        }.get(
            categoria,
            "odds_ft",
        )

        resultado[
            destino
        ].append(item)

    resultado[
        "mercados_disponiveis"
    ] = list(
        dict.fromkeys(
            resultado[
                "mercados_disponiveis"
            ]
        )
    )

    # ========================================================
    # MARCA 1X2
    # ========================================================

    if (
        odd_casa > 0
        or odd_draw > 0
        or odd_away > 0
    ):

        resultado[
            "mercados_encontrados"
        ].append("1X2")

    # ========================================================
    # TOTALS
    # ========================================================

    (
        over_linha,
        under_linha,
        odd_over,
        odd_under,
    ) = _extrair_totals(
        mercados
    )

    resultado[
        "over_linha"
    ] = over_linha

    resultado[
        "under_linha"
    ] = under_linha

    resultado[
        "odd_over"
    ] = odd_over

    resultado[
        "odd_under"
    ] = odd_under

    if (
        odd_over > 0
        or odd_under > 0
    ):

        resultado[
            "mercados_encontrados"
        ].append("TOTALS")

    # ========================================================
    # BTTS
    # ========================================================

    (
        odd_btts_sim,
        odd_btts_nao,
    ) = _extrair_btts(
        mercados
    )

    resultado[
        "odd_btts_sim"
    ] = odd_btts_sim

    resultado[
        "odd_btts_nao"
    ] = odd_btts_nao

    if (
        odd_btts_sim > 0
        or odd_btts_nao > 0
    ):

        resultado[
            "mercados_encontrados"
        ].append("BTTS")

    # ========================================================
    # HANDICAP
    # ========================================================

    (
        handicap_linha,
        odd_handicap_home,
        odd_handicap_away,
    ) = _extrair_handicap(
        mercados
    )

    resultado[
        "handicap_linha"
    ] = handicap_linha

    resultado[
        "odd_handicap_home"
    ] = odd_handicap_home

    resultado[
        "odd_handicap_away"
    ] = odd_handicap_away

    if (
        odd_handicap_home > 0
        or odd_handicap_away > 0
    ):

        resultado[
            "mercados_encontrados"
        ].append("HANDICAP")

    # ========================================================
    # DOUBLE CHANCE
    # ========================================================

    (
        odd_1x,
        odd_12,
        odd_x2,
    ) = _extrair_double_chance(
        mercados
    )

    resultado[
        "odd_1x"
    ] = odd_1x

    resultado[
        "odd_12"
    ] = odd_12

    resultado[
        "odd_x2"
    ] = odd_x2

    if (
        odd_1x > 0
        or odd_12 > 0
        or odd_x2 > 0
    ):

        resultado[
            "mercados_encontrados"
        ].append(
            "DOUBLE_CHANCE"
        )

    # ========================================================
    # DNB
    # ========================================================

    (
        odd_dnb_home,
        odd_dnb_away,
    ) = _extrair_dnb(
        mercados
    )

    resultado[
        "odd_dnb_home"
    ] = odd_dnb_home

    resultado[
        "odd_dnb_away"
    ] = odd_dnb_away

    if (
        odd_dnb_home > 0
        or odd_dnb_away > 0
    ):

        resultado[
            "mercados_encontrados"
        ].append("DNB")

    # ========================================================
    # DEBUG FINAL
    # ========================================================

    casa_nome = (
        jogo.get("home")
        or jogo.get("homeTeam")
        or ""
    )

    fora_nome = (
        jogo.get("away")
        or jogo.get("awayTeam")
        or ""
    )

    print(
        f"🔎 DEBUG MERCADOS | "
        f"{casa_nome} x {fora_nome} | "
        f"quantidade: {len(mercados)} | "
        f"nomes: "
        f"{resultado['mercados_disponiveis']}"
    )

    print(
        "ODDS 1X2 | "
        f"ID={event_id} | "
        f"CASA={odd_casa} | "
        f"EMPATE={odd_draw} | "
        f"VISITANTE={odd_away} | "
        f"Q={q_pre_live:.4f}"
    )

    print(
        "ODDS GOLS | "
        f"TOTALS={odd_over} / {odd_under} | "
        f"LINHA={over_linha} | "
        f"BTTS={odd_btts_sim} / {odd_btts_nao}"
    )

    return resultado


# ============================================================
# LIMPAR MEMÓRIA
# ============================================================

def limpar_memoria():

    global _IDS_LIVE_SELECIONADOS

    _IDS_LIVE_SELECIONADOS = []
