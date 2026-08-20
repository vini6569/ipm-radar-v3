import os
import urllib.request
import urllib.parse

API_KEY = os.getenv("ODDS_API_KEY")

print("=" * 50)
print("TESTE DE AUTENTICAÇÃO ODDS-API.IO")
print("=" * 50)

print("CHAVE EXISTE:", bool(API_KEY))
print("TAMANHO:", len(API_KEY) if API_KEY else 0)

url = (
    "https://api.odds-api.io/v3/events/live?"
    + urllib.parse.urlencode({
        "apiKey": API_KEY,
        "sport": "football"
    })
)

try:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "IPM-Radar-V3/1.0",
            "Accept": "application/json"
        }
    )

    with urllib.request.urlopen(req, timeout=20) as resposta:
        dados = resposta.read().decode("utf-8")

        print("STATUS:", resposta.status)
        print("RESPOSTA:", dados[:1000])

except Exception as erro:
    print("ERRO:", type(erro).__name__)
    print("DETALHE:", erro)

print("=" * 50)
