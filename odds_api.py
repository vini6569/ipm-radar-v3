# ============================================================
# ODDS API
# IPM-RADAR-V3
#
# Consulta:
# - Jogos ao vivo
# - Resultado 1X2
# - Total Goals (Over / Under)
# - Asian Handicap
#
# A chave fica na variável ODDS_API_KEY
# ============================================================

import os
import json
import urllib.request
import urllib.parse


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

    with urllib.request.urlopen(
        requisicao,
        timeout=20
    ) as resposta:

        conteudo = resposta.read().decode("utf-8")

        return json.loads(conteudo)


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

        print(
            "RESPOSTA DE JOGOS AO VIVO NÃO É LISTA"
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

        if not isinstance(evento, dict):
            continue

        evento_id = evento.get("id")

        if evento_id:

            ids.append(
                str(evento_id)
            )

    if not ids:

        print(
            "NENHUM ID DE EVENTO ENCONTRADO"
        )

        return []

    # A API permite até 10 eventos
    ids = ids[:10]

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

    if not isinstance(resposta, list):

        print(
            "RESPOSTA DE ODDS NÃO É LISTA"
        )

        print(
            "TIPO:",
            type(resposta)
        )

        return []

    print(
        "ODDS RECEBIDAS:",
        len(resposta)
    )

    return resposta


# ============================================================
# EXTRAÇÃO DOS MERCADOS
# ============================================================

def extrair_mercados(odds_evento):

    resultado = {
        "resultado": [],
        "gols": [],
        "handicap": []
    }


    # ========================================================
    # VERIFICAÇÃO BÁSICA
    # ========================================================

    if not isinstance(odds_evento, dict):

        print(
            "ODDS_EVENTO NÃO É DICT"
        )

        return resultado


    # ========================================================
    # DEBUG
    # ========================================================

    print("")
    print("========== DEBUG ODDS ==========")

    print(
        "EVENTO:",
        odds_evento.get("home"),
        "x",
        odds_evento.get("away")
    )

    bookmakers_debug = (
        odds_evento.get("bookmakers")
    )

    print(
        "TIPO BOOKMAKERS:",
        type(bookmakers_debug)
    )

    print(
        "BOOKMAKERS:",
        bookmakers_debug
    )

    print(
        "========== FIM DEBUG =========="
    )

    print("")


    # ========================================================
    # BOOKMAKERS
    # ========================================================

    bookmakers = odds_evento.get(
        "bookmakers",
        {}
    )


    # ========================================================
    # FORMATO ATUAL DA API
    #
    # bookmakers:
    # {
    #     "Bet365": [
    #         {
    #             "name": "ML",
    #             "odds": [...]
    #         },
    #         {
    #             "name": "Spread",
    #             "odds": [...]
    #         },
    #         {
    #             "name": "Totals",
    #             "odds": [...]
    #         }
    #     ]
    # }
    # ========================================================

    if isinstance(bookmakers, dict):

        mercados = bookmakers.get(
            BOOKMAKER,
            []
        )

        print(
            "BOOKMAKER:",
            BOOKMAKER
        )

        if isinstance(
            mercados,
            list
        ):

            print(
                "MERCADOS ENCONTRADOS:",
                len(mercados)
            )

        else:

            print(
                "MERCADOS NÃO É LISTA"
            )

            return resultado


        # ====================================================
        # CADA MERCADO
        # ====================================================

        for mercado in mercados:

            if not isinstance(
                mercado,
                dict
            ):

                continue


            nome = mercado.get(
                "name"
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


            print(
                "MERCADO:",
                nome
            )


            # =================================================
            # RESULTADO 1X2
            # =================================================

            if nome in (
                "ML",
                "Moneyline"
            ):

                resultado[
                    "resultado"
                ].extend(
                    outcomes
                )


            # =================================================
            # TOTAL GOALS
            # =================================================

            elif nome == "Totals":

                for odd in outcomes:

                    if not isinstance(
                        odd,
                        dict
                    ):

                        continue


                    resultado[
                        "gols"
                    ].append({

                        "linha":
                            odd.get("hdp"),

                        "over":
                            odd.get("over"),

                        "under":
                            odd.get("under")

                    })


            # =================================================
            # ASIAN HANDICAP
            # =================================================

            elif nome == "Spread":

                for odd in outcomes:

                    if not isinstance(
                        odd,
                        dict
                    ):

                        continue


                    resultado[
                        "handicap"
                    ].append({

                        "linha":
                            odd.get("hdp"),

                        "home":
                            odd.get("home"),

                        "away":
                            odd.get("away")

                    })


        return resultado


    # ========================================================
    # COMPATIBILIDADE COM FORMATO ANTIGO
    # ========================================================

    if isinstance(
        bookmakers,
        list
    ):

        print(
            "BOOKMAKERS EM FORMATO LISTA"
        )

        for bookmaker in bookmakers:

            if not isinstance(
                bookmaker,
                dict
            ):

                continue


            bookmaker_nome = bookmaker.get(
                "name"
            )

            print(
                "BOOKMAKER:",
                bookmaker_nome
            )


            mercados = bookmaker.get(
                "markets",
                []
            )


            if not isinstance(
                mercados,
                list
            ):

                continue


            for mercado in mercados:

                if not isinstance(
                    mercado,
                    dict
                ):

                    continue


                nome = mercado.get(
                    "name"
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


                # =============================================
                # RESULTADO
                # =============================================

                if nome in (
                    "ML",
                    "Moneyline"
                ):

                    resultado[
                        "resultado"
                    ].extend(
                        outcomes
                    )


                # =============================================
                # TOTAL GOALS
                # =============================================

                elif nome == "Totals":

                    for odd in outcomes:

                        if not isinstance(
                            odd,
                            dict
                        ):

                            continue


                        resultado[
                            "gols"
                        ].append({

                            "linha":
                                odd.get("hdp"),

                            "over":
                                odd.get("over"),

                            "under":
                                odd.get("under")

                        })


                # =============================================
                # ASIAN HANDICAP
                # =============================================

                elif nome == "Spread":

                    for odd in outcomes:

                        if not isinstance(
                            odd,
                            dict
                        ):

                            continue


                        resultado[
                            "handicap"
                        ].append({

                            "linha":
                                odd.get("hdp"),

                            "home":
                                odd.get("home"),

                            "away":
                                odd.get("away")

                        })


        return resultado


    # ========================================================
    # FORMATO DESCONHECIDO
    # ========================================================

    print(
        "FORMATO DE BOOKMAKERS DESCONHECIDO:"
    )

    print(
        type(bookmakers)
    )

    return resultado
