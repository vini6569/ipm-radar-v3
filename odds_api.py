# IPM-RADAR-V3 - odds_api.py

import os
import json
import urllib.request
import urllib.parse

BASE_URL = "https://api.odds-api.io/v3"
BOOKMAKER = "Bet365"

def obter_api_key():
    api_key = os.getenv("ODDS_API_KEY")
    if not api_key:
        raise RuntimeError("ODDS_API_KEY não configurada.")
    return api_key

def fazer_requisicao(url):
    requisicao = urllib.request.Request(
        url,
        headers={"User-Agent": "IPM-Radar/3.0", "Accept": "application/json"}
    )
    with urllib.request.urlopen(requisicao, timeout=20) as resposta:
        return json.loads(resposta.read().decode("utf-8"))

def buscar_jogos_ao_vivo():
    parametros = urllib.parse.urlencode({
        "apiKey": obter_api_key(),
        "sport": "football"
    })
    resposta = fazer_requisicao(BASE_URL + "/events/live?" + parametros)
    return resposta if isinstance(resposta, list) else []

def buscar_odds_multiplos(eventos):
    ids = [str(e.get("id")) for e in eventos if e.get("id")]
    if not ids:
        return []

    parametros = urllib.parse.urlencode({
        "apiKey": obter_api_key(),
        "eventIds": ",".join(ids[:10]),
        "bookmakers": BOOKMAKER
    })
    resposta = fazer_requisicao(BASE_URL + "/odds/multi?" + parametros)

    if isinstance(resposta, list):
        return resposta
    if isinstance(resposta, dict):
        return [resposta]
    return []

def extrair_mercados(odds_evento):
    resultado = {"resultado": [], "gols": [], "handicap": []}

    if not isinstance(odds_evento, dict):
        return resultado

    # CORREÇÃO PRINCIPAL:
    # A Odds API v3 retorna "bookmakers" como DICT:
    # "bookmakers": {"Bet365": [{"name":"ML",...},
    #                            {"name":"Totals",...},
    #                            {"name":"Spread",...}]}
    bookmakers = odds_evento.get("bookmakers", {})

    if isinstance(bookmakers, dict):
        mercados = bookmakers.get(BOOKMAKER)

        if mercados is None:
            for nome, valor in bookmakers.items():
                if str(nome).lower() == BOOKMAKER.lower():
                    mercados = valor
                    break

        if isinstance(mercados, list):
            processar_mercados(mercados, resultado)

        return resultado

    # Compatibilidade com formato antigo em lista
    if isinstance(bookmakers, list):
        for bookmaker in bookmakers:
            if not isinstance(bookmaker, dict):
                continue
            mercados = bookmaker.get("markets", [])
            if isinstance(mercados, list):
                processar_mercados(mercados, resultado)

    return resultado

def processar_mercados(mercados, resultado):
    for mercado in mercados:
        if not isinstance(mercado, dict):
            continue

        nome = str(mercado.get("name", "")).strip()
        outcomes = mercado.get("odds", [])

        if not isinstance(outcomes, list):
            continue

        if nome in ("ML", "Moneyline"):
            resultado["resultado"].extend(outcomes)

        elif nome == "Totals":
            for odd in outcomes:
                if isinstance(odd, dict):
                    resultado["gols"].append({
                        "linha": odd.get("hdp"),
                        "over": odd.get("over"),
                        "under": odd.get("under")
                    })

        elif nome == "Spread":
            for odd in outcomes:
                if isinstance(odd, dict):
                    resultado["handicap"].append({
                        "linha": odd.get("hdp"),
                        "home": odd.get("home"),
                        "away": odd.get("away")
                    })
                    
