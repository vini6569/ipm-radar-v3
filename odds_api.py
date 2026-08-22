# ============================================================
# ODDS API
# IPM-RADAR-V3
#
# Consulta:
# - Jogos ao vivo
# - Total Goals
# - Asian Handicap
# - Resultado 1X2
#
# Bet365
# ============================================================

import os
import json
import urllib.request
import urllib.parse
import urllib.error


BASE_URL = "https://api.odds-api.io/v3"

BOOKMAKER = "Bet365"


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

            return json.loads(conteudo)

    except urllib.error.HTTPError as erro:

        detalhe = ""

        try:
            detalhe = erro.read().decode(
                "utf-8"
            )
        except Exception:
            pass

        print()
        print("ERRO HTTP ODDS API")
        print("Código:", erro.code)
        print("Detalhes:", detalhe)

        return []

    except Exception as erro:

        print()
        print("ERRO NA REQUISIÇÃO ODDS API")
        print(type(erro).__name__)
        print(erro)

        return []


# ============================================================
# JOGOS AO VIVO
# ============================================================

def buscar_jogos_ao_vivo():

    api_key = obter_api_key()

    parametros = urllib.parse.urlencode({

        "apiKey": api_key,

        "sport": "football",

        "status": "live",

        "bookmaker": BOOKMAKER

    })

    url = (
        BASE_URL
        + "/events?"
        + parametros
    )

    print()
    print("======================================")
    print("CONSULTANDO JOGOS AO VIVO")
    print("BOOKMAKER:", BOOKMAKER)
    print("======================================")

    resposta = fazer_requisicao(url)

    if not isinstance(
        resposta,
        list
    ):

        print(
            "Resposta de eventos inválida:",
            type(resposta).__name__
        )

        return []

    print(
        "JOGOS AO VIVO ENCONTRADOS:",
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

        print()
        print(
            "NENHUM ID DE EVENTO PARA CONSULTAR ODDS."
        )

        return []

    # ========================================================
    # NÃO LIMITAR A 10
    # ========================================================

    print()
    print(
        "TOTAL DE IDS PARA CONSULTA:",
        len(ids)
    )

    print()
    print(
        "IDs ENVIADOS PARA ODDS API:"
    )

    print(ids)

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

    resposta = fazer_requisicao(url)

    # ========================================================
    # DIAGNÓSTICO
    # ========================================================

    print()
    print(
        "TIPO DA RESPOSTA ODDS:",
        type(resposta).__name__
    )

    if isinstance(
        resposta,
        list
    ):

        print(
            "EVENTOS RECEBIDOS:",
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
    # DIAGNÓSTICO DE BOOKMAKERS E MERCADOS
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

        bookmakers = evento.get(
            "bookmakers",
            {}
        )

        if not bookmakers:

            print(
                "  NENHUM BOOKMAKER RETORNADO."
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
            list(bookmakers.keys())
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
                    "    Formato de mercados:",
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

                odds = mercado.get(
                    "odds",
                    []
                )

                if isinstance(
                    odds,
                    list
                ):

                    print(
                        "      ODDS:",
                        len(odds)
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

    if not isinstance(
        bookmakers,
        dict
    ):

        return resultado

    # ========================================================
    # LOCALIZAR BET365
    # ========================================================

    mercados = None

    for nome, valor in bookmakers.items():

        if str(nome).strip().lower() == str(
            BOOKMAKER
        ).strip().lower():

            mercados = valor

            break

    if mercados is None:

        print(
            "BET365 NÃO ENCONTRADA NO EVENTO."
        )

        return resultado

    if not isinstance(
        mercados,
        list
    ):

        return resultado

    # ========================================================
    # PROCESSAR MERCADOS
    # ========================================================

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
        ).strip()

        nome_normalizado = nome.lower()

        print(
            "PROCESSANDO MERCADO:",
            repr(nome)
        )

        outcomes = mercado.get(
            "odds",
            []
        )

        if not isinstance(
            outcomes,
            list
        ):

            continue

        # ====================================================
        # RESULTADO 1X2
        # API: ML
        # ====================================================

        if nome_normalizado in {

            "ml",

            "moneyline",

            "1x2",

            "match winner",

            "match_winner",

            "winner"

        }:

            for odd in outcomes:

                if not isinstance(
                    odd,
                    dict
                ):
                    continue

                resultado[
                    "resultado"
                ].append({

                    "home": odd.get(
                        "home"
                    ),

                    "draw": odd.get(
                        "draw"
                    ),

                    "away": odd.get(
                        "away"
                    )

                })

        # ====================================================
        # TOTAL GOALS
        # API: Totals
        # ====================================================

        elif nome_normalizado in {

            "totals",

            "total goals",

            "total_goals"

        }:

            for odd in outcomes:

                if not isinstance(
                    odd,
                    dict
                ):
                    continue

                resultado[
                    "gols"
                ].append({

                    "linha": odd.get(
                        "hdp"
                    ),

                    "over": odd.get(
                        "over"
                    ),

                    "under": odd.get(
                        "under"
                    )

                })

        # ====================================================
        # ASIAN HANDICAP
        # API: Spread
        # ====================================================

        elif nome_normalizado in {

            "spread",

            "asian handicap",

            "asian_handicap",

            "handicap"

        }:

            for odd in outcomes:

                if not isinstance(
                    odd,
                    dict
                ):
                    continue

                resultado[
                    "handicap"
                ].append({

                    "linha": odd.get(
                        "hdp"
                    ),

                    "home": odd.get(
                        "home"
                    ),

                    "away": odd.get(
                        "away"
                    )

                })

    return resultado


# ============================================================
# FUNÇÃO DE TESTE
# ============================================================

def mostrar_resumo_odds(
    odds_evento
):

    mercados = extrair_mercados(
        odds_evento
    )

    print()
    print(
        "========== RESUMO =========="
    )

    # ========================================================
    # RESULTADO 1X2
    # ========================================================

    print()
    print(
        "RESULTADO 1X2"
    )

    if mercados[
        "resultado"
    ]:

        for odd in mercados[
            "resultado"
        ]:

            print(
                "  Casa:",
                odd.get("home"),
                "| Empate:",
                odd.get("draw"),
                "| Fora:",
                odd.get("away")
            )

    else:

        print(
            "  Sem odds de Resultado."
        )

    # ========================================================
    # TOTAL GOALS
    # ========================================================

    print()
    print(
        "TOTAL GOALS"
    )

    if mercados[
        "gols"
    ]:

        for odd in mercados[
            "gols"
        ]:

            print(
                "  Linha:",
                odd.get("linha"),
                "| Over:",
                odd.get("over"),
                "| Under:",
                odd.get("under")
            )

    else:

        print(
            "  Sem odds de Total Goals."
        )

    # ========================================================
    # ASIAN HANDICAP
    # ========================================================

    print()
    print(
        "ASIAN HANDICAP"
    )

    if mercados[
        "handicap"
    ]:

        for odd in mercados[
            "handicap"
        ]:

            print(
                "  Linha:",
                odd.get("linha"),
                "| Casa:",
                odd.get("home"),
                "| Fora:",
                odd.get("away")
            )

    else:

        print(
            "  Sem odds de Asian Handicap."
        )

    print()
    print(
        "============================"
                )
