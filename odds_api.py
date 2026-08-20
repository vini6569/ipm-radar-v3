# ============================================================
# ODDS API
# IPM-RADAR-V3
#
# Responsável por consultar:
# - jogos ao vivo
# - informações dos eventos
# - odds dos eventos
#
# A chave da API NÃO fica neste arquivo.
# Ela será obtida pela variável ODDS_API_KEY.
# ============================================================

import os
import json
import urllib.request
import urllib.parse


BASE_URL = "https://api.odds-api.io/v3"


def obter_api_key():
    """
    Obtém a chave da Odds-API.io
    através da variável de ambiente.
    """

    api_key = os.getenv("ODDS_API_KEY")

    if not api_key:
        raise RuntimeError(
            "ODDS_API_KEY não configurada."
        )

    return api_key


def fazer_requisicao(url):
    """
    Executa uma requisição HTTP e retorna JSON.
    """

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
