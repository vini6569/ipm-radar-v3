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
# Esta versão possui diagnóstico detalhado
# para verificarmos exatamente o retorno da API.
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
        "sport": "football"
    })

    url = (
        BASE_URL
        + "/events/live?"
        + parametros
    )

    resposta = fazer_requisicao(url)

    if not isinstance(resposta, list):

        return []

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

        evento_id = evento.get("id")

        if evento_id:

            ids.append(
                str(evento_id)
            )

    if not ids:

        return []

    # ========================================================
    # A API permite múltiplos eventos.
    #
    # Vamos limitar inicialmente a 10 para o nosso teste.
    # Depois aumentaremos quando o coletor estiver funcionando.
    # ========================================================

    ids = ids[:10]

    print()
    print("IDs ENVIADOS PARA ODDS API:")
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
    print("TIPO DA RESPOSTA ODDS:")
    print(type(resposta).__name__)

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

        # Caso a API entregue um único evento.

        eventos_odds = [
            resposta
        ]

    else:

        eventos_odds = []


    # ========================================================
    # MOSTRAR BOOKMAKERS E MERCADOS
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
            "bookmakers"
        )

        if not bookmakers:

            print(
                "  Nenhum bookmaker retornado."
            )

            continue

        if isinstance(
            bookmakers,
            dict
        ):

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

                if isinstance(
                    mercados,
                    list
                ):

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
                            nome_mercado
                        )

                else:

                    print(
                        "    Formato de mercados:",
                        type(mercados).__name__
                    )

        else:

            print(
                "  Formato bookmakers:",
                type(bookmakers).__name__
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


    # ========================================================
    # FORMATO NORMAL
    #
    # "bookmakers": {
    #
    #     "Bet365": [
    #
    #         {
    #             "name": "ML",
    #             "odds": [...]
    #         },
    #
    #         {
    #             "name": "Totals",
    #             "odds": [...]
    #         },
    #
    #         {
    #             "name": "Spread",
    #             "odds": [...]
    #         }
    #
    #     ]
    #
    # }
    # ========================================================

    if isinstance(
        bookmakers,
        dict
    ):

        mercados = bookmakers.get(
            BOOKMAKER
        )

        # ====================================================
        # Caso o nome venha com outra capitalização.
        # ====================================================

        if mercados is None:

            for nome, valor in bookmakers.items():

                if str(nome).lower() == str(
                    BOOKMAKER
                ).lower():

                    mercados = valor

                    break

        if mercados is None:

            return resultado

    else:

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
        # ====================================================

        if nome.lower() == "ml":

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
        # ====================================================

        elif nome.lower() == "totals":

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
        # ====================================================

        elif nome.lower() == "spread":

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
    # RESULTADO
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
