# ============================================================
# ODDS API - IPM RADAR V4.1
# ============================================================
# Consulta jogos ao vivo e odds da Bet365.
#
# Fluxo:
#   /events/live
#       ↓
#   seleciona até 10 jogos
#       ↓
#   /odds/multi
#       ↓
#   extrai todos os mercados
#       ↓
#   memória das odds
#       ↓
#   IPM
# ============================================================

import json
import urllib.error
import urllib.parse
import urllib.request

from config import (
    BASE_URL,
    BOOKMAKER,
    SPORT,
    MAX_EVENTOS_POR_CONSULTA,
    TIMEOUT_REQUISICAO,
    obter_api_key,
)


# ============================================================
# MEMÓRIA DAS ODDS
# ============================================================

_ODD_INICIAL = {}
_ODD_ANTERIOR = {}


# ============================================================
# REQUEST JSON
# ============================================================

def _request_json(
    endpoint,
    params
):

    url = (
        f"{BASE_URL}/"
        f"{endpoint.lstrip('/')}"
        f"?{urllib.parse.urlencode(params)}"
    )

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "IPM-Radar/4.1",
            "Accept": "application/json",
        },
    )

    try:

        with urllib.request.urlopen(
            req,
            timeout=TIMEOUT_REQUISICAO
        ) as resp:

            body = (
                resp
                .read()
                .decode("utf-8")
            )

            print(
                "HTTP STATUS ODDS API:",
                resp.status
            )

        if not body:
            return []

        return json.loads(body)

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
            "❌ ERRO HTTP ODDS API:",
            erro.code,
            "|",
            detalhe[:500]
        )

        return []

    except (
        urllib.error.URLError,
        TimeoutError
    ) as erro:

        print(
            "❌ ERRO DE CONEXÃO ODDS API:",
            erro
        )

        return []

    except json.JSONDecodeError as erro:

        print(
            "❌ RESPOSTA JSON INVÁLIDA:",
            erro
        )

        return []

    except Exception as erro:

        print(
            "❌ ERRO ODDS API:",
            type(erro).__name__,
            erro
        )

        return []


# ============================================================
# NORMALIZA LISTA DE EVENTOS
# ============================================================

def _lista_eventos(
    resposta
):

    if isinstance(
        resposta,
        list
    ):

        return [
            item
            for item in resposta
            if isinstance(
                item,
                dict
            )
        ]

    if not isinstance(
        resposta,
        dict
    ):

        return []

    for chave in (
        "events",
        "data",
        "results"
    ):

        valor = resposta.get(
            chave
        )

        if isinstance(
            valor,
            list
        ):

            return [
                item
                for item in valor
                if isinstance(
                    item,
                    dict
                )
            ]

    if resposta.get(
        "id"
    ) is not None:

        return [
            resposta
        ]

    resultado = []

    for valor in resposta.values():

        if (
            isinstance(
                valor,
                dict
            )
            and valor.get("id") is not None
        ):

            resultado.append(
                valor
            )

    return resultado


# ============================================================
# JOGOS AO VIVO
# ============================================================

def buscar_jogos_ao_vivo():

    print()
    print("=" * 70)
    print(
        "📡 CONSULTANDO JOGOS AO VIVO"
    )
    print("=" * 70)

    try:

        key = obter_api_key()

    except Exception as erro:

        print(
            "❌ ERRO API KEY:",
            erro
        )

        return []

    resposta = _request_json(
        "/events/live",
        {
            "apiKey": key,
            "sport": SPORT,
        }
    )

    eventos = _lista_eventos(
        resposta
    )

    print(
        "JOGOS AO VIVO ENCONTRADOS:",
        len(eventos)
    )

    limite = min(
        len(eventos),
        MAX_EVENTOS_POR_CONSULTA
    )

    for evento in eventos[:limite]:

        print(
            f"  {evento.get('id')} | "
            f"{evento.get('home')} x "
            f"{evento.get('away')} | "
            f"{evento.get('status')}"
        )

    return eventos


# ============================================================
# ODDS MULTI
# ============================================================

def buscar_odds_multiplos(
    eventos
):

    if not eventos:
        return []

    try:

        key = obter_api_key()

    except Exception as erro:

        print(
            "❌ ERRO API KEY:",
            erro
        )

        return []

    ids = []

    for evento in eventos:

        if not isinstance(
            evento,
            dict
        ):
            continue

        event_id = evento.get(
            "id"
        )

        if event_id is not None:

            ids.append(
                str(event_id)
            )

    ids = list(
        dict.fromkeys(
            ids
        )
    )

    ids = ids[
        :MAX_EVENTOS_POR_CONSULTA
    ]

    if not ids:

        return []

    print()
    print(
        "📊 CONSULTANDO ODDS |",
        len(ids),
        "|",
        BOOKMAKER
    )

    resposta = _request_json(
        "/odds/multi",
        {
            "apiKey": key,
            "eventIds": ",".join(ids),
            "bookmakers": BOOKMAKER,
        }
    )

    eventos_odds = _lista_eventos(
        resposta
    )

    print(
        "EVENTOS COM ODDS RECEBIDOS:",
        len(eventos_odds)
    )

    return eventos_odds


# ============================================================
# CONVERSOR NUMÉRICO
# ============================================================

def _numero(
    valor,
    padrao=0.0
):

    try:

        if valor in (
            None,
            ""
        ):

            return padrao

        numero = float(
            valor
        )

        return (
            numero
            if numero > 0
            else padrao
        )

    except (
        TypeError,
        ValueError
    ):

        return padrao


# ============================================================
# CONVERSOR INTEIRO
# ============================================================

def _inteiro(
    valor,
    padrao=0
):

    try:

        if valor in (
            None,
            ""
        ):

            return padrao

        return int(
            float(valor)
        )

    except (
        TypeError,
        ValueError
    ):

        return padrao


# ============================================================
# LOCALIZA EVENTO NAS ODDS
# ============================================================

def _evento_odds_por_id(
    odds,
    event_id
):

    if event_id is None:
        return None

    alvo = str(
        event_id
    )

    if isinstance(
        odds,
        list
    ):

        for item in odds:

            if (
                isinstance(
                    item,
                    dict
                )
                and str(
                    item.get("id")
                ) == alvo
            ):

                return item

    if isinstance(
        odds,
        dict
    ):

        if str(
            odds.get("id")
        ) == alvo:

            return odds

        item = odds.get(
            alvo
        )

        if isinstance(
            item,
            dict
        ):

            return item

    return None


# ============================================================
# MERCADOS BET365
# ============================================================

def _mercados_bet365(
    evento
):

    if not isinstance(
        evento,
        dict
    ):

        return []

    bookmakers = evento.get(
        "bookmakers",
        {}
    )

    nome_bet = (
        BOOKMAKER
        .strip()
        .lower()
    )

    # --------------------------------------------------------
    # Estrutura:
    #
    # "bookmakers": {
    #     "Bet365": [...]
    # }
    # --------------------------------------------------------

    if isinstance(
        bookmakers,
        dict
    ):

        mercados = bookmakers.get(
            BOOKMAKER
        )

        if mercados is None:

            for nome, valor in (
                bookmakers.items()
            ):

                if (
                    str(nome)
                    .strip()
                    .lower()
                    == nome_bet
                ):

                    mercados = valor
                    break

        if isinstance(
            mercados,
            list
        ):

            return mercados

    # --------------------------------------------------------
    # Estrutura alternativa:
    #
    # "bookmakers": [
    #     {
    #         "name": "Bet365",
    #         "markets": [...]
    #     }
    # ]
    # --------------------------------------------------------

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
                bookmaker.get(
                    "name",
                    ""
                )
            ).strip().lower()

            if nome == nome_bet:

                mercados = bookmaker.get(
                    "markets",
                    []
                )

                if isinstance(
                    mercados,
                    list
                ):

                    return mercados

    return []


# ============================================================
# PRIMEIRA LINHA DE ODDS
# ============================================================

def _primeiro_odds(
    mercado
):

    if not isinstance(
        mercado,
        dict
    ):

        return {}

    valores = mercado.get(
        "odds"
    )

    if isinstance(
        valores,
        list
    ):

        for valor in valores:

            if isinstance(
                valor,
                dict
            ):

                return valor

        return {}

    if isinstance(
        valores,
        dict
    ):

        return valores

    return {}


# ============================================================
# TODAS AS LINHAS DE ODDS
# ============================================================

def _linhas_odds(
    mercado
):

    if not isinstance(
        mercado,
        dict
    ):

        return []

    valores = mercado.get(
        "odds"
    )

    if isinstance(
        valores,
        list
    ):

        return [
            valor
            for valor in valores
            if isinstance(
                valor,
                dict
            )
        ]

    if isinstance(
        valores,
        dict
    ):

        return [
            valores
        ]

    return []


# ============================================================
# ENCONTRAR MERCADO
# ============================================================

def _encontrar_mercado(
    mercados,
    nomes
):

    nomes_normalizados = {
        str(nome)
        .strip()
        .lower()
        for nome in nomes
    }

    for mercado in mercados:

        if not isinstance(
            mercado,
            dict
        ):

            continue

        nome = str(
            mercado.get(
                "name",
                ""
            )
        ).strip().lower()

        if nome in nomes_normalizados:

            return mercado

    return None


# ============================================================
# NORMALIZA NOME
# ============================================================

def _nome_normalizado(
    nome
):

    return (
        str(nome or "")
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )


# ============================================================
# IDENTIFICA HT
# ============================================================

def _eh_ht(
    nome
):

    n = _nome_normalizado(
        nome
    )

    termos = (
        "half time",
        "halftime",
        "1st half",
        "first half",
        "1sthalf",
        "1h",
        "ht result",
        "ht totals",
        "half time result",
    )

    return any(
        termo in n
        for termo in termos
    )


# ============================================================
# CATEGORIA DO MERCADO
# ============================================================

def _categoria_mercado(
    nome
):

    n = _nome_normalizado(
        nome
    )

    if _eh_ht(
        nome
    ):

        return "HT"

    if (
        "corner" in n
        or "corners" in n
        or "escante" in n
    ):

        return "CORNERS"

    if (
        "card" in n
        or "cards" in n
        or "cartão" in n
        or "cartoes" in n
        or "booking" in n
    ):

        return "CARDS"

    return "FT"


# ============================================================
# EXTRAIR PLACAR
# ============================================================

def _extrair_placar(
    jogo
):

    if not isinstance(
        jogo,
        dict
    ):

        return 0, 0

    candidatos = (
        jogo.get("score"),
        jogo.get("scores"),
        jogo.get("result"),
    )

    for valor in candidatos:

        if isinstance(
            valor,
            dict
        ):

            casa = valor.get(
                "home"
            )

            if casa is None:

                casa = valor.get(
                    "homeScore"
                )

            fora = valor.get(
                "away"
            )

            if fora is None:

                fora = valor.get(
                    "awayScore"
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
            isinstance(
                valor,
                list
            )
            and len(valor) >= 2
        ):

            return (
                _inteiro(
                    valor[0]
                ),
                _inteiro(
                    valor[1]
                )
            )

    return (
        _inteiro(
            jogo.get(
                "homeScore"
            )
        ),
        _inteiro(
            jogo.get(
                "awayScore"
            )
        )
    )


# ============================================================
# EXTRAIR MINUTO
# ============================================================

def _extrair_minuto(
    jogo
):

    if not isinstance(
        jogo,
        dict
    ):

        return 0

    candidatos = (
        jogo.get("minute"),
        jogo.get("elapsed"),
        jogo.get("timer"),
        jogo.get("clock"),
    )

    for valor in candidatos:

        # ----------------------------------------------------
        # Caso a API envie:
        #
        # {"minute": 42}
        #
        # ou
        #
        # {"elapsed": 42}
        # ----------------------------------------------------

        if isinstance(
            valor,
            dict
        ):

            minuto_dict = valor.get(
                "minute"
            )

            if minuto_dict is None:

                minuto_dict = valor.get(
                    "elapsed"
                )

            if minuto_dict is None:

                minuto_dict = valor.get(
                    "value"
                )

            valor = minuto_dict

        # ----------------------------------------------------
        # Caso venha:
        #
        # "42'"
        # "42 min"
        # ----------------------------------------------------

        if isinstance(
            valor,
            str
        ):

            valor = (
                valor
                .replace(
                    "'",
                    ""
                )
                .replace(
                    "min",
                    ""
                )
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
# EXTRAIR ESTATÍSTICAS
# ============================================================

def _extrair_estatisticas(
    jogo
):

    if not isinstance(
        jogo,
        dict
    ):

        return 0, 0, 0

    fontes = []

    for chave in (
        "statistics",
        "stats",
        "matchStatistics",
    ):

        valor = jogo.get(
            chave
        )

        if isinstance(
            valor,
            dict
        ):

            fontes.append(
                valor
            )

    for fonte in fontes:

        escanteios = fonte.get(
            "corners"
        )

        finalizacoes = fonte.get(
            "shots"
        )

        ataques = fonte.get(
            "dangerousAttacks"
        )

        if (
            escanteios is not None
            or finalizacoes is not None
            or ataques is not None
        ):

            return (
                _inteiro(
                    escanteios
                ),
                _inteiro(
                    finalizacoes
                ),
                _inteiro(
                    ataques
                )
            )

    # Não inventamos estatísticas.
    return 0, 0, 0


# ============================================================
# COPIAR MERCADO
# ============================================================

def _copiar_mercado(
    mercado
):

    return {
        "name": mercado.get(
            "name",
            ""
        ),

        "updatedAt": mercado.get(
            "updatedAt"
        ),

        "odds": _linhas_odds(
            mercado
        )
    }


# ============================================================
# MEMÓRIA DA ODD
# ============================================================

def _memoria_odd(
    event_id,
    odd_atual
):

    anterior = (
        _ODD_ANTERIOR.get(
            event_id,
            0.0
        )
        if event_id is not None
        else 0.0
    )

    # --------------------------------------------------------
    # Guarda a primeira odd válida
    # --------------------------------------------------------

    if (
        event_id is not None
        and odd_atual > 0
        and event_id not in _ODD_INICIAL
    ):

        _ODD_INICIAL[
            event_id
        ] = odd_atual

    inicial = _ODD_INICIAL.get(
        event_id,
        odd_atual
    )

    recente = 0.0
    desde = 0.0

    # --------------------------------------------------------
    # Variação desde a última consulta
    # --------------------------------------------------------

    if anterior > 0:

        recente = (
            (
                odd_atual
                - anterior
            )
            / anterior
        ) * 100.0

    # --------------------------------------------------------
    # Variação desde a primeira consulta
    # --------------------------------------------------------

    if inicial > 0:

        desde = (
            (
                odd_atual
