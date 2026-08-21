# ============================================================
# ODDS API
# IPM-RADAR-V3
#
# DIAGNÓSTICO DOS MERCADOS
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
        print("ERRO: resposta de jogos ao vivo não é lista.")
        print(resposta)
        return []

    print("JOGOS AO VIVO ENCONTRADOS:", len(resposta))

    return resposta


# ============================================================
# ODDS DOS JOGOS
# ============================================================

def buscar_odds_multiplos(eventos):

    api_key = obter_api_key()

    ids = []

    for evento in eventos:

        evento_id = evento.get("id")

        if evento_id:
            ids.append(str(evento_id))

    if not ids:

        print("Nenhum ID de evento encontrado.")

        return []

    # A API permite até 10 eventos por consulta
    ids = ids[:10]

    print("IDS CONSULTADOS:", ids)

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

    print("CONSULTANDO ODDS...")
    print("BOOKMAKER:", BOOKMAKER)

    resposta = fazer_requisicao(url)

    if not isinstance(resposta, list):

        print("ERRO: resposta de odds não é lista.")
        print(resposta)

        return []

    print("EVENTOS COM ODDS RECEBIDOS:", len(resposta))

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

    if not isinstance(odds_evento, dict):

        print("ODDS EVENTO NÃO É DICT")

        return resultado


    # ========================================================
    # IDENTIFICAÇÃO DO JOGO
    # ========================================================

    evento_id = odds_evento.get("id")

    home = odds_evento.get("home")
    away = odds_evento.get("away")

    print("")
    print("==============================================")
    print("DIAGNÓSTICO DO EVENTO")
    print("==============================================")
    print("ID:", evento_id)
    print("HOME:", home)
    print("AWAY:", away)


    # ========================================================
    # BOOKMAKERS
    # ========================================================

    bookmakers = odds_evento.get(
        "bookmakers",
        []
    )

    if not isinstance(bookmakers, list):

        print("BOOKMAKERS NÃO É LISTA")

        return resultado


    print("BOOKMAKERS ENCONTRADOS:", len(bookmakers))


    # ========================================================
    # CADA BOOKMAKER
    # ========================================================

    for bookmaker in bookmakers:

        if not isinstance(bookmaker, dict):
            continue

        bookmaker_nome = bookmaker.get(
            "name"
        )

        print("")
        print("----------------------------------------------")
        print("BOOKMAKER:", bookmaker_nome)
        print("----------------------------------------------")


        mercados = bookmaker.get(
            "markets",
            []
        )

        if not isinstance(mercados, list):

            print("MERCADOS NÃO É LISTA")

            continue


        print(
            "QUANTIDADE DE MERCADOS:",
            len(mercados)
        )


        # ====================================================
        # CADA MERCADO
        # ====================================================

        for mercado in mercados:

            if not isinstance(mercado, dict):
                continue

            nome = mercado.get(
                "name"
            )

            outcomes = mercado.get(
                "odds",
                []
            )


            print("")
            print("MERCADO ENCONTRADO:", nome)
            print(
                "QUANTIDADE DE ODDS:",
                len(outcomes)
                if isinstance(outcomes, list)
                else "NÃO É LISTA"
            )


            # =================================================
            # MOSTRA O CONTEÚDO REAL DO MERCADO
            # =================================================

            print(
                "DADOS DO MERCADO:"
            )

            try:

                print(
                    json.dumps(
                        mercado,
                        ensure_ascii=False,
                        indent=2
                    )
                )

            except Exception:

                print(mercado)


            if not isinstance(
                outcomes,
                list
            ):

                continue


            # =================================================
            # RESULTADO 1X2
            # =================================================

            if nome == "ML":

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


    # ========================================================
    # RESUMO FINAL
    # ========================================================

    print("")
    print("==============================================")
    print("RESUMO DOS MERCADOS")
    print("==============================================")

    print(
        "RESULTADO 1X2:",
        len(resultado["resultado"])
    )

    print(
        "TOTAL GOALS:",
        len(resultado["gols"])
    )

    print(
        "ASIAN HANDICAP:",
        len(resultado["handicap"])
    )

    print("==============================================")
    print("")


    return resultado
