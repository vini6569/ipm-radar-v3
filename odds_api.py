# ============================================================
# ODDS API - IPM RADAR V5.2
# CASA / EMPATE / VISITANTE
# W1 x W2 + Q + R
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
# CONTADOR DA API
# ============================================================

REQUISICOES_REALIZADAS = 0


# ============================================================
# MEMÓRIA LIVE
# ============================================================

_IDS_LIVE_SELECIONADOS = []


# ============================================================
# REQUISIÇÃO
# ============================================================

def _request_json(endpoint, params):

    global REQUISICOES_REALIZADAS

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

            REQUISICOES_REALIZADAS += 1

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

        REQUISICOES_REALIZADAS += 1

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
# W1 x W2
# ============================================================

def calcular_w1xw2(odd_casa, odd_visitante):

    """
    W1 x W2

    W1 = odd da equipe da casa
    W2 = odd da equipe visitante

    Fórmula:

        W1 x W2 = W1 * W2
    """

    w1 = _numero(odd_casa)
    w2 = _numero(odd_visitante)

    if w1 <= 0 or w2 <= 0:
        return 0.0

    return w1 * w2


# ============================================================
# Q
# ============================================================

def calcular_q(odd_casa, odd_visitante):

    casa = _numero(odd_casa)
    fora = _numero(odd_visitante)

    if casa <= 0 or fora <= 0:
        return 0.0

    return (
        2.0 * casa * fora
        / (casa + fora)
    )


# ============================================================
# R
# ============================================================

def calcular_r(odd_casa, odd_visitante):

    casa = _numero(odd_casa)
    fora = _numero(odd_visitante)

    if casa <= 0 or fora <= 0:
        return 0.0

    menor = min(casa, fora)
    maior = max(casa, fora)

    return (
        maior / menor
        if menor > 0
        else 0.0
    )


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

    # --------------------------------------------------------
    # FORMATO DICT
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # FORMATO LISTA
    # --------------------------------------------------------

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
                or item.get("outcome")
                or item.get("selection")
                or item.get("key")
                or ""
            ).strip().lower()

            if nome not in alvo:
                continue

            preco = _preco_item(
                item
            )

            if preco > 0:
                return preco

    return 0.0


# ============================================================
# NORMALIZAR NOME
# ============================================================

def _normalizar_texto(valor):

    return (
        str(valor)
        .strip()
        .lower()
    )


# ============================================================
# IDENTIFICAR MERCADO 1X2
# ============================================================

def _eh_mercado_1x2(mercado):

    if not isinstance(
        mercado,
        dict,
    ):
        return False

    nome = _normalizar_texto(
        mercado.get("key")
        or mercado.get("name")
        or mercado.get("market")
        or mercado.get("type")
        or ""
    )

    return nome in (
        "1x2",
        "match",
        "match winner",
        "winner",
        "fulltime result",
        "result",
    )


# ============================================================
# EXTRAIR 1X2
# ============================================================

def _extrair_1x2(
    mercados,
    casa_nome="",
    fora_nome="",
):

    odd_casa = 0.0
    odd_empate = 0.0
    odd_visitante = 0.0

    casa_alvos = {
        "1",
        "home",
        "casa",
        "home team",
        "1x2 home",
        _normalizar_texto(casa_nome),
    }

    empate_alvos = {
        "x",
        "draw",
        "tie",
        "empate",
    }

    visitante_alvos = {
        "2",
        "away",
        "fora",
        "away team",
        "1x2 away",
        _normalizar_texto(fora_nome),
    }

    for mercado in mercados:

        if not isinstance(
            mercado,
            dict,
        ):
            continue

        if not _eh_mercado_1x2(mercado):
            continue

        linhas = _linhas_odds(
            mercado
        )

        for linha in linhas:

            nome = _normalizar_texto(
                linha.get("name")
                or linha.get("label")
                or linha.get("outcome")
                or linha.get("selection")
                or linha.get("key")
                or ""
            )

            preco = _preco_item(
                linha
            )

            if preco <= 0:
                continue

            if (
                nome in casa_alvos
                and odd_casa <= 0
            ):

                odd_casa = preco

            elif (
                nome in empate_alvos
                and odd_empate <= 0
            ):

                odd_empate = preco

            elif (
                nome in visitante_alvos
                and odd_visitante <= 0
            ):

                odd_visitante = preco

    return (
        odd_casa,
        odd_empate,
        odd_visitante,
    )


# ============================================================
# EXTRAIR TOTALS
# ============================================================

def _extrair_totals(mercados):

    over_linha = 0.0
    under_linha = 0.0

    odd_over = 0.0
    odd_under = 0.0

    for mercado in mercados:

        if not isinstance(
            mercado,
            dict,
        ):
            continue

        nome_mercado = _normalizar_texto(
            mercado.get("key")
            or mercado.get("name")
            or mercado.get("market")
            or mercado.get("type")
            or ""
        )

        if (
            "total" not in nome_mercado
            and "over" not in nome_mercado
        ):
            continue

        linhas = _linhas_odds(
            mercado
        )

        for linha in linhas:

            nome = _normalizar_texto(
                linha.get("name")
                or linha.get("label")
                or linha.get("outcome")
                or linha.get("selection")
                or ""
            )

            preco = _preco_item(
                linha
            )

            if preco <= 0:
                continue

            linha_valor = _numero(
                linha.get("line")
                or linha.get("handicap")
                or linha.get("total")
                or linha.get("point")
            )

            if "over" in nome:

                if odd_over <= 0:
                    odd_over = preco

                if (
                    linha_valor > 0
                    and over_linha <= 0
                ):
                    over_linha = linha_valor

            elif "under" in nome:

                if odd_under <= 0:
                    odd_under = preco

                if (
                    linha_valor > 0
                    and under_linha <= 0
                ):
                    under_linha = linha_valor

    return (
        over_linha,
        under_linha,
        odd_over,
        odd_under,
    )


# ============================================================
# EXTRAIR BTTS
# ============================================================

def _extrair_btts(mercados):

    odd_sim = 0.0
    odd_nao = 0.0

    for mercado in mercados:

        if not isinstance(
            mercado,
            dict,
        ):
            continue

        nome_mercado = _normalizar_texto(
            mercado.get("key")
            or mercado.get("name")
            or mercado.get("market")
            or mercado.get("type")
            or ""
        )

        if not (
            "btts" in nome_mercado
            or "both teams" in nome_mercado
            or "both teams to score" in nome_mercado
        ):
            continue

        linhas = _linhas_odds(
            mercado
        )

        for linha in linhas:

            nome = _normalizar_texto(
                linha.get("name")
                or linha.get("label")
                or linha.get("outcome")
                or linha.get("selection")
                or ""
            )

            preco = _preco_item(
                linha
            )

            if preco <= 0:
                continue

            if nome in (
                "yes",
                "sim",
                "true",
            ):

                odd_sim = preco

            elif nome in (
                "no",
                "não",
                "nao",
                "false",
            ):

                odd_nao = preco

    return (
        odd_sim,
        odd_nao,
    )


# ============================================================
# EXTRAIR MERCADOS
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

    event_id = jogo.get(
        "id"
    )

    evento_odds = _evento_odds_por_id(
        odds,
        event_id,
    )

    if evento_odds is None:

        # Alguns formatos devolvem as odds
        # diretamente no próprio evento.

        evento_odds = jogo

    mercados = _mercados_bookmaker(
        evento_odds
    )

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

    # ========================================================
    # 1X2
    # ========================================================

    (
        odd_casa,
        odd_empate,
        odd_visitante,
    ) = _extrair_1x2(
        mercados,
        casa_nome,
        fora_nome,
    )

    # ========================================================
    # FALLBACK PARA CAMPOS DIRETOS
    # ========================================================

    if odd_casa <= 0:

        odd_casa = _numero(
            evento_odds.get("odd_casa")
            or evento_odds.get("homeOdd")
            or evento_odds.get("home_odd")
        )

    if odd_empate <= 0:

        odd_empate = _numero(
            evento_odds.get("odd_empate")
            or evento_odds.get("drawOdd")
            or evento_odds.get("draw_odd")
        )

    if odd_visitante <= 0:

        odd_visitante = _numero(
            evento_odds.get("odd_visitante")
            or evento_odds.get("awayOdd")
            or evento_odds.get("away_odd")
        )

    # ========================================================
    # W1 x W2
    # ========================================================

    w1xw2 = calcular_w1xw2(
        odd_casa,
        odd_visitante,
    )

    # ========================================================
    # Q
    # ========================================================

    q = calcular_q(
        odd_casa,
        odd_visitante,
    )

    # ========================================================
    # R
    # ========================================================

    r = calcular_r(
        odd_casa,
        odd_visitante,
    )

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

    # ========================================================
    # BTTS
    # ========================================================

    (
        odd_btts_sim,
        odd_btts_nao,
    ) = _extrair_btts(
        mercados
    )

    # ========================================================
    # RESULTADO
    # ========================================================

    return {

        # ----------------------------------------------------
        # 1X2
        # ----------------------------------------------------

        "odd_casa": odd_casa,
        "odd_empate": odd_empate,
        "odd_visitante": odd_visitante,

        # ----------------------------------------------------
        # W1 x W2
        # ----------------------------------------------------

        "w1": odd_casa,
        "w2": odd_visitante,

        "w1xw2": round(
            w1xw2,
            4,
        ),

        # ----------------------------------------------------
        # Q
        # ----------------------------------------------------

        "q": round(
            q,
            4,
        ),

        # ----------------------------------------------------
        # R
        # ----------------------------------------------------

        "r": round(
            r,
            4,
        ),

        # ----------------------------------------------------
        # TOTALS
        # ----------------------------------------------------

        "over_linha": over_linha,
        "under_linha": under_linha,

        "odd_over": odd_over,
        "odd_under": odd_under,

        # ----------------------------------------------------
        # BTTS
        # ----------------------------------------------------

        "odd_btts_sim": odd_btts_sim,
        "odd_btts_nao": odd_btts_nao,

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        "tem_1x2": (
            odd_casa > 0
            and odd_empate > 0
            and odd_visitante > 0
        ),

        "tem_w1xw2": (
            w1xw2 > 0
        ),

        "tem_totals": (
            odd_over > 0
            or odd_under > 0
        ),

        "tem_btts": (
            odd_btts_sim > 0
            or odd_btts_nao > 0
        ),
    }


# ============================================================
# TESTE W1 x W2
# ============================================================

def testar_w1xw2():

    print()
    print("=" * 60)
    print("TESTE W1 x W2")
    print("=" * 60)

    exemplos = [
        (2.40, 2.10),
        (1.50, 4.00),
        (3.00, 3.00),
    ]

    for w1, w2 in exemplos:

        resultado = calcular_w1xw2(
            w1,
            w2,
        )

        print(
            f"W1={w1:.2f} | "
            f"W2={w2:.2f} | "
            f"W1xW2={resultado:.4f}"
        )

    print("=" * 60)


# ============================================================
# TESTE DIRETO
# ============================================================

if __name__ == "__main__":

    testar_w1xw2()
