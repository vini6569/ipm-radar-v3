# ============================================================
# ODDS API
# IPM-RADAR-V3
#
# Versão econômica
#
# - Jogos ao vivo
# - Odds em lotes de até 10 eventos
# - Diagnóstico dos mercados
# - Controle de erro 429
# - Não faz requisições desnecessárias
# ============================================================

import os
import json
import urllib.request
import urllib.parse
import urllib.error


BASE_URL = "https://api.odds-api.io/v3"

# ============================================================
# BOOKMAKER
# ============================================================

BOOKMAKER = "Bet365"

# ============================================================
# LIMITE DE EVENTOS POR CONSULTA
# A API permite até 10 eventos no /odds/multi
# ============================================================

MAX_EVENTOS_POR_CONSULTA = 10


# ============================================================
# API KEY
# ============================================================

def obter_api_key():

    api_key = os.getenv("ODDS_API_KEY")

    if not api_key:

        raise RuntimeError(
            "ODDS_API_KEY não configurada."
        )

    return api_key


# ============================================================
# REQUISIÇÃO
# ============================================================

def fazer_requisicao(url):

    requisicao = urllib.request.Request(
        url,
        headers={
            "User-Agent": "IPM-Radar/3.0",
            "Accept": "application/json"
        }
    )

    try:

        with urllib.request.urlopen(
            requisicao,
            timeout=20
        ) as resposta:

            conteudo = resposta.read().decode(
                "utf-8"
            )

            return json.loads(
                conteudo
            )

    except urllib.error.HTTPError as erro:

        detalhe = ""

        try:

            detalhe = erro.read().decode(
                "utf-8"
            )

        except Exception:

            pass

        print()
        print(
            "ERRO HTTP ODDS API"
        )

        print(
            "Código:",
            erro.code
        )

        print(
            "Detalhes:",
            detalhe
        )

        # ====================================================
        # LIMITE DA API
        # ====================================================

        if erro.code == 429:

            print()
            print(
                "⚠️ LIMITE DA API ATINGIDO."
            )

            print(
                "Nenhuma nova consulta será feita "
                "até a próxima tentativa."
            )

        return []

    except Exception as erro:

        print()
        print(
            "ERRO NA REQUISIÇÃO ODDS API"
        )

        print(
            type(erro).__name__
        )

        print(
            erro
        )

        return []


# ============================================================
# JOGOS AO VIVO
# ============================================================

def buscar_jogos_ao_vivo():

    api_key = obter_api_key()

    parametros = urllib.parse.urlencode({

        "apiKey": api_key,

        "sport": "football"

    })

    url = (
        BASE_URL
        + "/events/live?"
        + parametros
    )

    print()
    print(
        "Consultando jogos ao vivo..."
    )

    resposta = fazer_requisicao(
        url
    )

    if not isinstance(
        resposta,
        list
    ):

        return []

    print(
        "Jogos ao vivo encontrados:",
        len(resposta)
    )

    return resposta


# ============================================================
# ODDS DOS JOGOS
# ============================================================

def buscar_odds_multiplos(eventos):

    api_key = obter_api_key()

    ids = []

    for evento in eventos:

        if not isinstance(
            evento,
            dict
        ):
            continue

        evento_id = evento.get(
            "id"
        )

        if evento_id:

            ids.append(
                str(evento_id)
            )

    if not ids:

        print(
            "Nenhum ID de evento disponível."
        )

        return []

    # ========================================================
    # IMPORTANTE
    #
    # A API permite até 10 eventos em /odds/multi.
    # Portanto não enviamos mais que 10 por requisição.
    # ========================================================

    ids = ids[
        :MAX_EVENTOS_POR_CONSULTA
    ]

    print()
    print(
        "======================================"
    )

    print(
        "CONSULTA DE ODDS"
    )

    print(
        "Eventos enviados:",
        len(ids)
    )

    print(
        "IDs:",
        ids
    )

    print(
        "Bookmaker:",
        BOOKMAKER
    )

    print(
        "======================================"
    )

    parametros = urllib.parse.urlencode({

        "apiKey": api_key,

        "eventIds": ",".join(ids),

        "bookmakers": BOOKMAKER

    })

    url = (
        BASE_URL
        + "/odds/multi?"
        + parametros
    )

    resposta = fazer_requisicao(
        url
    )

    # ========================================================
    # DIAGNÓSTICO
    # ========================================================

    print()
    print(
        "TIPO DA RESPOSTA ODDS:"
    )

    print(
        type(resposta).__name__
    )

    if isinstance(
        resposta,
        list
    ):

        print(
            "EVENTOS COM ODDS:",
            len(resposta)
        )

    elif isinstance(
        resposta,
        dict
    ):

        print(
            "RESPOSTA RECEBIDA COMO OBJETO"
        )

    else:

        print(
            "RESPOSTA DESCONHECIDA"
        )

        return []

    # ========================================================
    # NORMALIZAÇÃO
    # ========================================================

    if isinstance(
        resposta,
        list
    ):

        eventos_odds = resposta

    elif isinstance(
        resposta,
        dict
    ):

        eventos_odds = [
            resposta
        ]

    else:

        eventos_odds = []

    # ========================================================
    # DIAGNÓSTICO DOS BOOKMAKERS
    # ========================================================

    print()
    print(
        "========== DIAGNÓSTICO ODDS =========="
    )

    for evento in eventos_odds:

        if not isinstance(
            evento,
            dict
        ):
            continue

        evento_id = evento.get(
            "id"
        )

        print()
        print(
            "EVENTO:",
            evento_id
        )

        print(
            "JOGO:",
            evento.get("home"),
            "x",
            evento.get("away")
        )

        bookmakers = evento.get(
            "bookmakers"
        )

        if not bookmakers:

            print(
                "  Nenhum bookmaker retornado."
            )

            continue

        if not isinstance(
            bookmakers,
            dict
        ):

            print(
                "  Formato bookmakers:",
                type(bookmakers).__name__
            )

            continue

        print(
            "  BOOKMAKERS:",
            list(
                bookmakers.keys()
            )
        )

        for nome, mercados in bookmakers.items():

            print()
            print(
                "  BOOKMAKER:",
                nome
            )

            if not isinstance(
                mercados,
                list
            ):

                print(
                    "    Formato:",
                    type(mercados).__name__
                )

                continue

            for mercado in mercados:

                if not isinstance(
                    mercado,
                    dict
                ):
                    continue

                nome_mercado = mercado.get(
                    "name"
                )

                print(
                    "    MERCADO:",
                    repr(nome_mercado)
                )

    print()
    print(
        "======================================"
    )

    return eventos_odds


# ============================================================
# EXTRAÇÃO DOS MERCADOS
# ============================================================

def extrair_mercados(
    odds_evento
):

    resultado = {

        "resultado": [],

        "gols": [],

        "handicap": []

    }

    if not isinstance(
        odds_evento,
        dict
    ):

        return resultado

    bookmakers = odds_evento.get(
        "bookmakers",
        {}
    )

    if
