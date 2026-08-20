import os
import json
import urllib.request

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

print("=" * 50)
print("DESCOBRINDO CHAT ID - IPM RADAR")
print("=" * 50)

if not TOKEN:
    print("ERRO: TELEGRAM_BOT_TOKEN não configurado")
    raise SystemExit

# Testa o bot
url = f"https://api.telegram.org/bot{TOKEN}/getMe"

try:
    resposta = urllib.request.urlopen(url).read().decode()
    dados = json.loads(resposta)

    print("BOT:")
    print(dados)

except Exception as erro:
    print("ERRO AO VALIDAR BOT:")
    print(type(erro).__name__)
    print(erro)
    raise SystemExit

# Busca atualizações recebidas pelo bot
url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

try:
    resposta = urllib.request.urlopen(url).read().decode()
    dados = json.loads(resposta)

    print("\nATUALIZAÇÕES:")

    for item in dados.get("result", []):
        print("-" * 50)

        if "channel_post" in item:
            chat = item["channel_post"]["chat"]

            print("CANAL ENCONTRADO!")
            print("ID:", chat.get("id"))
            print("TÍTULO:", chat.get("title"))
            print("USERNAME:", chat.get("username"))

        elif "message" in item:
            chat = item["message"]["chat"]

            print("CHAT ENCONTRADO!")
            print("ID:", chat.get("id"))
            print("NOME:", chat.get("title") or chat.get("first_name"))
            print("USERNAME:", chat.get("username"))

    print("=" * 50)
    print("FIM DO TESTE")
    print("=" * 50)

except Exception as erro:
    print("ERRO AO BUSCAR ATUALIZAÇÕES:")
    print(type(erro).__name__)
    print(erro)
