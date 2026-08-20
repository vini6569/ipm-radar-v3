import os
import json
import urllib.request
import urllib.parse

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print("=" * 50)
print("TESTE TELEGRAM - IPM RADAR V3")
print("=" * 50)

print("TOKEN EXISTE:", bool(TOKEN))
print("CHAT_ID EXISTE:", bool(CHAT_ID))

if not TOKEN:
    print("ERRO: TELEGRAM_BOT_TOKEN não configurada")
    raise SystemExit(1)

if not CHAT_ID:
    print("ERRO: TELEGRAM_CHAT_ID não configurada")
    raise SystemExit(1)

mensagem = (
    "🟢 TESTE IPM RADAR V3\n\n"
    "Telegram conectado com sucesso!\n"
    "Robô 2 — Radar de Movimentação"
)

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

dados = urllib.parse.urlencode({
    "chat_id": CHAT_ID,
    "text": mensagem
}).encode("utf-8")

try:
    requisicao = urllib.request.Request(
        url,
        data=dados,
        method="POST"
    )

    with urllib.request.urlopen(
        requisicao,
        timeout=20
    ) as resposta:

        retorno = json.loads(
            resposta.read().decode("utf-8")
        )

    print("STATUS:", resposta.status)
    print("TELEGRAM OK:", retorno.get("ok"))

    if retorno.get("ok"):
        print("MENSAGEM ENVIADA COM SUCESSO!")
    else:
        print("ERRO TELEGRAM:")
        print(retorno)

except Exception as erro:
    print("ERRO:", type(erro).__name__)
    print("DETALHE:", erro)

print("=" * 50)
