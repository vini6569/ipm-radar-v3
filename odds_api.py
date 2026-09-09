# ============================================================
# ODDS API - IPM RADAR V5.0
# CASA / EMPATE / VISITANTE
# ============================================================
#
# Funções:
#
#   - Buscar jogos ao vivo
#   - Buscar jogos pré-live
#   - Buscar jogos ao vivo por IDs
#   - Buscar odds múltiplas
#   - Extrair mercados
#   - Extrair 1X2
#   - Extrair placar
#   - Extrair minuto
#   - Extrair estatísticas
#
# CÁLCULO DO Q:
#
#   Q = 2 × (W1 × W2) / (W1 + W2)
#
# Onde:
#
#   W1 = odd Casa
#   W2 = odd Visitante
#
# Este arquivo NÃO realiza apostas.
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
# MEMÓRIA DOS JOGOS LIVE
# ============================================================

_IDS_LIVE_SELECIONADOS = []


# ============================================================
# REQUISIÇÃO HTTP
# ============================================================

def _request_json(endpoint, params):

    url = (
        f"{BASE_URL}/{endpoint.lstrip('/')}"
        f"?{urllib.parse.urlencode(params)}"
    )

    requisicao = urllib.request.Request(
        url,
        headers={
            "User-Agent": "IPM-Radar/5.0",
            "Accept": "application/json",
        },
    )

    try:

        with urllib.request.urlopen(
            requisicao,
            timeout=TIMEOUT_REQUISICAO,
        ) as resposta:

            corpo = (
                resposta
                .read()
                .decode("utf-8")
            )

            print(
                "HTTP STATUS ODDS API:",
                resposta.status,
            )

            if not corpo:
                return []

            return json.loads(corpo)

    except urllib.error.HTTPError as erro:

        try:
            detalhe = (
                erro
                .read()
                .decode("utf-8")
            )

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
# NORMALIZAR LISTA DE EVENTOS
# ============================================================

def _lista_eventos(resposta):

    if isinstance(resposta, list):

        return [
            item
            for item in resposta
            if isinstance(item, dict)
        ]

    if not isinstance(
        resposta,
        dict,
    ):

        return []

    for chave in (
        "events",
        "data",
        "results",
    ):

        valor = resposta.get(
            chave
        )

        if isinstance(
            valor,
            list,
        ):

            return [
                item
                for item in valor
                if isinstance(item, dict)
            ]

    if resposta.get("id") is not None:

        return [resposta]

    return [
        valor
        for valor in resposta.values()
        if (
            isinstance(valor, dict)
            and valor.get("id") is not None
        )
    ]


# ============================================================
# CONVERSÃO NUMÉRICA
# ============================================================

def _numero(
    valor,
    padrao=0.0,
):

    try:

        if valor in (
            None,
            "",
        ):

            return padrao

        return float(valor)

    except (
        TypeError,
        ValueError,
    ):

        return padrao


# ============================================================
# CONVERSÃO INTEIRO
# ============================================================

def _inteiro(
    valor,
    padrao=0,
):

    try:

        if valor in (
            None,
            "",
        ):

            return padrao

        return int(
            float(valor)
        )

    except (
        TypeError,
        ValueError,
    ):

        return padrao


# ============================================================
# EXTRAIR MINUTO
# ============================================================

def _extrair_minuto(jogo):

    if not isinstance(
        jogo,
        dict,
    ):

        return 0

    clock = jogo.get(
        "clock"
    )

    if isinstance(
        clock,
        dict,
    ):

        minuto = _inteiro(
            clock.get(
                "minute"
            ),
            -1,
        )

        if minuto >= 0:
            return minuto

    valores = (
        jogo.get("minute"),
        jogo.get("elapsed"),
        jogo.get("timer"),
    )

    for valor in valores:

        if isinstance(
            valor,
            dict,
        ):

            valor = valor.get(
                "minute",
                valor.get(
                    "elapsed"
                ),
            )

        if isinstance(
            valor,
            str,
        ):

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
# EXTRAIR PLACAR
# ============================================================

def _extrair_placar(jogo):

    if not isinstance(
        jogo,
        dict,
    ):

        return 0, 0

    for valor in (
        jogo.get("scores"),
        jogo.get("score"),
        jogo.get("result"),
    ):

        if isinstance(
            valor,
            dict,
        ):

            casa = valor.get(
                "home",
                valor.get(
                    "homeScore"
                ),
            )

            fora = valor.get(
                "away",
                valor.get(
                    "awayScore"
                ),
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
# EXTRAIR ESTATÍSTICAS
# ============================================================

def _extrair_estatisticas(jogo):

    if not isinstance(
        jogo,
        dict,
    ):

        return (
            0,
            0,
            0,
            0,
        )

    for chave in (
        "statistics",
        "stats",
        "matchStatistics",
    ):

        fonte = jogo.get(
            chave
        )

        if isinstance(
            fonte,
            dict,
        ):

            esc = fonte.get(
                "corners"
            )

            fin = fonte.get(
                "shots"
            )

            atq = fonte.get(
                "dangerousAttacks"
            )

            cart = fonte.get(
                "cards"
            )

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

    return (
        0,
        0,
        0,
        0,
    )


# ============================================================
# BUSCAR TODOS OS JOGOS AO VIVO
# ============================================================

def buscar_jogos_ao_vivo():

    global _IDS_LIVE_SELECIONADOS

    try:

        chave = obter_api_key()

    except Exception as erro:

        print(
            "ERRO API KEY:",
            erro,
        )

        return []

    resposta = _request_json(
        "/events/live",
        {
            "apiKey": chave,
            "sport": SPORT,
        },
    )

    eventos = _lista_eventos(
        resposta
    )

    mapa = {}

    for evento in eventos:

        event_id = evento.get(
            "id"
        )

        if event_id is not None:

            mapa[
                str(event_id)
            ] = evento

    ids_mantidos = [

        str(event_id)

        for event_id
        in _IDS_LIVE_SELECIONADOS

        if (
            str(event_id)
            in mapa
        )
    ]

    restantes = [

        evento

        for event_id, evento
        in mapa.items()

        if event_id
        not in ids_mantidos
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
            str(
                evento["id"]
            )
        )

    _IDS_LIVE_SELECIONADOS = (
        ids_mantidos[
            :MAX_EVENTOS_POR_CONSULTA
        ]
    )

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
# BUSCAR JOGOS AO VIVO POR IDs
# ============================================================
#
# IMPORTANTE:
#
# O main.py precisa desta função.
#
# Para evitar depender de um endpoint adicional,
# buscamos os jogos LIVE disponíveis e filtramos
# somente pelos IDs que vieram da PRÉ-LIVE.
#
# ============================================================

def buscar_jogos_ao_vivo_por_ids(
    ids
):

    if not ids:

        print(
            "LIVE POR IDS: "
            "nenhum ID recebido."
        )

        return []

    ids_alvo = {
        str(event_id)
        for event_id in ids
        if event_id is not None
    }

    if not ids_alvo:

        return []

    eventos = (
        buscar_jogos_ao_vivo()
        or []
    )

    selecionados = []

    for evento in eventos:

        if not isinstance(
            evento,
            dict,
        ):

            continue

        event_id = evento.get(
            "id"
        )

        if event_id is None:
            continue

        if str(event_id) in ids_alvo:

            selecionados.append(
                evento
            )

    print(
        "LIVE POR IDS | "
        f"IDS MONITORADOS: "
        f"{len(ids_alvo)} | "
        f"ENCONTRADOS: "
        f"{len(selecionados)}"
    )

    return selecionados


# ============================================================
# CONVERTER DATA DO EVENTO
# ============================================================

def _parse_data_evento(
    evento
):

    if not isinstance(
        evento,
        dict,
    ):

        return None

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
# BUSCAR JOGOS PRÉ-LIVE
# ============================================================

def buscar_jogos_pre_live():

    try:

        chave = obter_api_key()

    except Exception as erro:

        print(
            "ERRO API KEY:",
            erro,
        )

        return []

    resposta = _request_json(
        "/events",
        {
            "apiKey": chave,
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

    limite = (
        agora.timestamp()
        + (
            PRE_LIVE_JANELA_MINUTOS
            * 60
        )
    )

    proximos = []

    for evento in eventos:

        dt = _parse_data_evento(
            evento
        )

        if dt is None:
            continue

        timestamp = dt.timestamp()

        if (
            agora.timestamp()
            <= timestamp
            <= limite
        ):

            proximos.append(
                evento
            )

    proximos.sort(
        key=lambda evento:
            _parse_data_evento(
                evento
            )
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
# BUSCAR ODDS MÚLTIPLAS
# ============================================================

def buscar_odds_multiplos(
    eventos
):

    if not eventos:

        print(
            "ODDS MULTI: "
            "nenhum evento recebido."
        )

        return []

    try:

        chave = obter_api_key()

    except Exception as erro:

        print(
            "ERRO API KEY:",
            erro,
        )

        return []

    ids = [

        str(evento["id"])

        for evento in eventos

        if (
            isinstance(
                evento,
                dict,
            )
            and evento.get("id")
            is not None
        )
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
            inicio:
            inicio + 10
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
                "apiKey": chave,
                "eventIds": ",".join(
                    bloco
                ),
                "bookmakers": BOOKMAKER,
            },
        )

        eventos_odds = (
            _lista_eventos(
                resposta
            )
        )

        print(
            "EVENTOS COM ODDS "
            "RECEBIDOS:",
            len(eventos_odds),
        )

        resultados.extend(
            eventos_odds
        )

    return resultados


# ============================================================
# ENCONTRAR EVENTO DE ODDS PELO ID
# ============================================================

def _evento_odds_por_id(
    odds,
    event_id,
):

    if event_id is None:
        return None

    alvo = str(
        event_id
    )

    if isinstance(
        odds,
        list,
    ):

        for item in odds:

            if (
                isinstance(
                    item,
                    dict,
                )
                and str(
                    item.get("id")
                ) == alvo
            ):

                return item

    if isinstance(
        odds,
        dict,
    ):

        if (
            str(
                odds.get("id")
            )
            == alvo
        ):

            return odds

        item = odds.get(
            alvo
        )

        if isinstance(
            item,
            dict,
        ):

            return item

    return None


# ============================================================
# EXTRAIR MERCADOS DO BOOKMAKER
# ============================================================

def _mercados_bet365(
    evento
):

    if not isinstance(
        evento,
        dict,
    ):

        return []

    bookmakers = evento.get(
        "bookmakers",
        {},
    )

    if isinstance(
        bookmakers,
        dict,
    ):

        mercados = (
            bookmakers.get(
                BOOKMAKER
            )
        )

        if mercados is None:

            for nome, valor in (
                bookmakers.items()
            ):

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

                mercados = (
                    bookmaker.get(
                        "markets",
                        [],
                    )
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
# LINHAS DE ODDS
# ============================================================

def _linhas_odds(
    mercado
):

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

    return [



# ============================================================
# PREÇO DE UMA ODD
# ============================================================

def _preco_item(
    item
):

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

        valor = item.get(
            chave
        )

        if isinstance(
            valor,
            (
                int,
                float,
                str,
            ),
        ):

            numero = _numero(
                valor
            )

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
    # FORMATO DIRETO
    # --------------------------------------------------------

    for nome in nomes:

        valor = linha.get(
            nome
        )

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
    # OUTCOMES / SELECTIONS / ITEMS / OPTIONS
    # --------------------------------------------------------

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
    # A PRÓPRIA LINHA É O OUTCOME
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

def _nome_mercado(
    mercado
):

    if not isinstance(
        mercado,
        dict,
    ):

        return ""

    return str(
        mercado.get("name")
        or mercado.get("key")
        or mercado.get("market")
        or ""
    ).strip().lower()


# ============================================================
# ENCONTRAR MERCADO 1X2
# ============================================================

def _encontrar_1x2(
    mercados
):

    nomes = (
        "ml",
        "moneyline",
        "1x2",
        "match winner",
        "match result",
        "full time result",
        "winner",
    )

    for mercado in mercados:

        nome = _nome_mercado(
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

    return (
        0.0,
        0.0,
        0.0,
    )


# ============================================================
# CALCULAR Q
# ============================================================
#
# Fórmula ÚNICA do projeto:
#
# Q = 2 × (W1 × W2) / (W1 + W2)
#
# ============================================================

def calcular_q(
    odd_casa,
    odd_visitante,
):

    odd_casa = _numero(
        odd_casa
    )

    odd_visitante = _numero(
        odd_visitante
    )

    if (
        odd_casa <= 0
        or odd_visitante <= 0
    ):

        return 0.0

    soma = (
        odd_casa
        + odd_visitante
    )

    if soma <= 0:
        return 0.0

    return (
        2.0
        * odd_casa
        * odd_visitante
    ) / soma


# ============================================================
# EXTRAIR TODOS OS MERCADOS
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

    evento = (
        _evento_odds_por_id(
            odds,
            event_id,
        )
        or jogo
    )

    mercados = _mercados_bet365(
        evento
    )

    placar_casa, placar_fora = (
        _extrair_placar(
            jogo
        )
    )

    esc, fin, atq, cart = (
        _extrair_estatisticas(
            jogo
        )
    )

    (
        odd_casa,
        odd_draw,
        odd_away,
    ) = _encontrar_1x2(
        mercados
    )

    # ========================================================
    # Q PRÉ-LIVE / LIVE
    # ========================================================

    q_pre_live = calcular_q(
        odd_casa,
        odd_away,
    )

    resultado = {

        "event_id": event_id,

        "odd_home": odd_casa,
        "odd_draw": odd_draw,
        "odd_away": odd_away,

        "odd_casa": odd_casa,
        "odd_atual": odd_draw,
        "odd_empate": odd_draw,
        "odd_visitante": odd_away,

        "q": q_pre_live,
        "odd_pre_live": q_pre_live,

        "minuto": _extrair_minuto(
            jogo
        ),

        "gols": (
            placar_casa
            + placar_fora
        ),

        "escanteios": esc,
        "cartoes": cart,
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

    # ========================================================
    # ORGANIZAR MERCADOS
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
            or ""
        ).strip()

        if not nome:
            continue

        item = {

            "name": nome,

            "updatedAt":
                mercado.get(
                    "updatedAt"
                ),

            "odds":
                _linhas_odds(
                    mercado
                ),
        }

        resultado[
            "todos"
        ].append(
            item
        )

        resultado[
            "mercados_disponiveis"
        ].append(
            nome
        )

        nome_lower = nome.lower()

        # ----------------------------------------------------
        # HT
        # ----------------------------------------------------

        if (
            "half" in nome_lower
            or "halftime" in nome_lower
            or "1st half" in nome_lower
        ):

            destino = "odds_ht"

        # ----------------------------------------------------
        # ESCANTEIOS
        # ----------------------------------------------------

        elif (
            "corner" in nome_lower
            or "escante" in nome_lower
        ):

            destino = "odds_corners"

        # ----------------------------------------------------
        # CARTÕES
        # ----------------------------------------------------

        elif (
            "card" in nome_lower
            or "booking" in nome_lower
            or "cart" in nome_lower
        ):

            destino = "odds_cards"

        # ----------------------------------------------------
        # FULL TIME
        # ----------------------------------------------------

        else:

            destino = "odds_ft"

        resultado[
            destino
        ].append(
            item
        )

    # ========================================================
    # REMOVER DUPLICADOS
    # ========================================================

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
    # MARCAR 1X2
    # ========================================================

    if (
        odd_casa > 0
        or odd_draw > 0
        or odd_away > 0
    ):

        resultado[
            "mercados_encontrados"
        ].append(
            "1X2"
        )

    # ========================================================
    # LOG
    # ========================================================

    print(
        "ODDS 1X2 | "
        f"ID={event_id} | "
        f"CASA={odd_casa} | "
        f"EMPATE={odd_draw} | "
        f"VISITANTE={odd_away} | "
        f"Q={q_pre_live:.3f}"
    )

    return resultado


# ============================================================
# LIMPAR MEMÓRIA LIVE
# ============================================================

def limpar_memoria():

    global _IDS_LIVE_SELECIONADOS

    _IDS_LIVE_SELECIONADOS = []

    print(
        "MEMÓRIA LIVE LIMPA."
    )
