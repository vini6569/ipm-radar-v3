# ============================================================
# ODDS API
# IPM-RADAR-V3
#
# Consulta:
# - Jogos ao vivo
# - Odds dos jogos
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
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(requisicao, timeout=20) as resposta:
            conteudo = resposta.read().decode("utf-8")
            return json.loads(conteudo)

    except Exception as erro:
        print("ERRO NA REQUISICAO:", erro)
        return []


# ============================================================
# JOGOS AO VIVO
# ============================================================

def buscar_jogos_ao_vivo():
    api_key = obter_api_key()

    parametros = urllib.parse.urlencode({
        "apiKey": api_key,
        "sport": "football",
    })

    url = f"{BASE_URL}/events/live?{parametros}"

    resposta = fazer_requisicao(url)

    if not isinstance(resposta, list):
        print("RESPOSTA DE JOGOS AO VIVO NÃO É LISTA:", type(resposta))
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

        evento_id = evento.get("id")

        if evento_id is not None:
            ids.append(str(evento_id))

    if not ids:
        return []

    # A API permite consultar até 10 eventos por vez.
    ids = ids[:10]

    parametros = urllib.parse.urlencode({
        "apiKey": api_key,
        "eventIds": ",".join(ids),
        "bookmakers": BOOKMAKER,
    })

    url = f"{BASE_URL}/odds/multi?{parametros}"

    print("CONSULTANDO ODDS PARA:", ",".join(ids))

    resposta = fazer_requisicao(url)

    if not isinstance(resposta, list):
        print("RESPOSTA DE ODDS NÃO É LISTA:", type(resposta))
        return []

    return resposta


# ============================================================
# EXTRAÇÃO DOS MERCADOS
# ============================================================

def extrair_mercados(odds_evento):
    resultado = {
        "resultado": [],
        "gols": [],
        "handicap": [],
    }

    if not isinstance(odds_evento, dict):
        return resultado

    # Algumas respostas podem trazer bookmakers diretamente.
    bookmakers = odds_evento.get("bookmakers", [])

    if not isinstance(bookmakers, list):
        return resultado

    for bookmaker in bookmakers:
        if not isinstance(bookmaker, dict):
            continue

        bookmaker_nome = bookmaker.get("name", "")

        mercados = bookmaker.get("markets", [])

        if not isinstance(mercados, list):
            continue

        for mercado in mercados:
            if not isinstance(mercado, dict):
                continue

            nome = mercado.get("name")
            outcomes = mercado.get("odds", [])

            if not isinstance(outcomes, list):
                continue

            # ------------------------------------------------
            # RESULTADO 1X2
            # ------------------------------------------------
            if nome == "ML":
                resultado["resultado"].extend(outcomes)

            # ------------------------------------------------
            # TOTAL GOALS
            # ------------------------------------------------
            elif nome == "Totals":
                for odd in outcomes:
                    if not isinstance(odd, dict):
                        continue

                    resultado["gols"].append({
                        "linha": odd.get("hdp"),
                        "over": odd.get("over"),
                        "under": odd.get("under"),
                        "bookmaker": bookmaker_nome,
                    })

            # ------------------------------------------------
            # ASIAN HANDICAP
            # ------------------------------------------------
            elif nome == "Spread":
                for odd in outcomes:
                    if not isinstance(odd, dict):
                        continue

                    resultado["handicap"].append({
                        "linha": odd.get("hdp"),
                        "home": odd.get("home"),
                        "away": odd.get("away"),
                        "bookmaker": bookmaker_nome,
                    })

    return resultado


# ============================================================
# FUNÇÃO DE CONVENIÊNCIA
# ============================================================

def buscar_odds_e_extrair(eventos):
    """
    Recebe os eventos ao vivo, consulta as odds e devolve
    os mercados já separados por evento.
    """

    odds = buscar_odds_multiplos(eventos)

    resultados = []

    for odds_evento in odds:
        mercados = extrair_mercados(odds_evento)

        resultados.append({
            "evento_id": odds_evento.get("id"),
            "mercados": mercados,
        })

    return resultados
    
