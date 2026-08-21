# ============================================================
# ODDS API
# IPM-RADAR-V3
#
# Consulta:
# - Jogos ao vivo
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
        raise RuntimeError("ODDS_API_KEY não configurada.")

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

    with urllib.request.urlopen(requisicao, timeout=20) as resposta:
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

    url = BASE_URL + "/events/live?" + parametros

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
        if not isinstance(evento, dict):
            continue
        print("DEBUG: ENTROU NA BUSCA DE ODDS")
        evento_id = evento.get("id")

        if evento_id:
            ids.append(str(evento_id))

    if not ids:
        return []

    # A API permite consultar até 10 eventos por chamada.
    ids = ids[:10]

    parametros = urllib.parse.urlencode({
        "apiKey": api_key,
        "eventIds": ",".join(ids),
        "bookmakers": BOOKMAKER
    })

    url = BASE_URL + "/odds/multi?" + parametros
    print("DEBUG: VOU CONSULTAR ODDS")
    resposta = fazer_requisicao(url)
    print("DEBUG ODDS:", json.dumps(resposta, ensure_ascii=False))
    # O endpoint /odds/multi retorna uma lista de eventos.
    if isinstance(resposta, list):
        return resposta

    # Proteção caso a API retorne um único objeto.
    if isinstance(resposta, dict):
        return [resposta]

    return []


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
        return resultado

    bookmakers = odds_evento.get("bookmakers", {})

    # ========================================================
    # IMPORTANTE:
    # A API Odds-API.io v3 normalmente retorna:
    #
    # "bookmakers": {
    #     "Bet365": [
    #         {"name": "ML", ...},
    #         {"name": "Totals", ...},
    #         {"name": "Spread", ...}
    #     ]
    # }
    #
    # Portanto BOOKMAKERS é um DICT, e não uma LISTA.
    # ========================================================

    if isinstance(bookmakers, dict):

        lista_bookmakers = []

        for nome_bookmaker, mercados in bookmakers.items():
            lista_bookmakers.append({
                "name": nome_bookmaker,
                "markets": mercados
            })

    elif isinstance(bookmakers, list):

        # Mantém compatibilidade com outro formato de resposta.
        lista_bookmakers = bookmakers

    else:
        return resultado

    # ========================================================
    # CADA BOOKMAKER
    # ========================================================

    for bookmaker in lista_bookmakers:

        if not isinstance(bookmaker, dict):
            continue

        bookmaker_nome = bookmaker.get("name")

        # Formato normalizado acima.
        mercados = bookmaker.get("markets", [])

        # Alguns retornos podem trazer os mercados diretamente
        # como valor de uma chave de bookmaker.
        if not isinstance(mercados, list):
            continue

        for mercado in mercados:

            if not isinstance(mercado, dict):
                continue

            nome = mercado.get("name")
            outcomes = mercado.get("odds", [])
            print("DEBUG MERCADO:", nome)
            print("DEBUG ODDS:", outcomes)
            if not isinstance(outcomes, list):
                continue

            # =================================================
            # RESULTADO 1X2
            # =================================================

            if nome == "ML":

                for odd in outcomes:

                    if isinstance(odd, dict):
                        resultado["resultado"].append({
                            "home": odd.get("home"),
                            "draw": odd.get("draw"),
                            "away": odd.get("away")
                        })

            # =================================================
            # TOTAL GOALS
            # =================================================

            elif nome == "Totals":

                for odd in outcomes:

                    if not isinstance(odd, dict):
                        continue

                        "linha": odd.get("point"),
                        "linha": odd.get("hdp"),
                        "over": odd.get("over"),
                        "under": odd.get("under")
                    })

            # =================================================
            # ASIAN HANDICAP
            # =================================================

            elif nome == "Spread":

                for odd in outcomes:

                    if not isinstance(odd, dict):
                        continue

                    resultado["handicap"].append({
                        "linha": odd.get("hdp"),
                        "home": odd.get("home"),
                        "away": odd.get("away")
                    })

    return resultado
    
