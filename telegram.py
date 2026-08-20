import os
import json
import urllib.request
import urllib.error

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

print("=" * 50)
print("TESTE COMPLETO TELEGRAM - IPM RADAR V3")
print("=" * 50)

if not TOKEN:
    print("ERRO: TELEGRAM_BOT_TOKEN não configurado")
    raise SystemExit

print("TOKEN EXISTE: True")
print("TAMANHO DO TOKEN:", len(TOKEN))

# ==================================================
# 1. TESTA O TOKEN COM getMe
# ==================================================

print("\n1 - VALIDANDO BOT...")
print("-" * 50)

url = f"https://api.telegram.org/bot{TOKEN}/getMe"

try:
    resposta = urllib.request.urlopen(url).read().decode("utf-8")
    dados = json.loads(resposta)

    print("RESPOSTA:")
    print(dados)

    if dados.get("ok"):
        bot = dados.get("result", {})

        print("\nBOT VALIDADO COM SUCESSO!")
        print("ID:", bot.get("id"))
        print("NOME:", bot.get("first_name"))
        print("USERNAME:", bot.get("username"))

    else:
        print("\nTELEGRAM RECUSOU O BOT.")

except urllib.error.HTTPError as erro:
    print("ERRO HTTP:", erro.code)
    print("RESPOSTA DO TELEGRAM:")

    try:
        detalhe = erro.read().decode("utf-8")
        print(detalhe)
    except Exception:
        print("Não foi possível ler a resposta.")

    raise SystemExit

except Exception as erro:
    print("ERRO:", type(erro).__name__)
    print(erro)
    raise SystemExit


# ==================================================
# 2. BUSCA ATUALIZAÇÕES
# ==================================================

print("\n2 - BUSCANDO ATUALIZAÇÕES...")
print("-" * 50)

url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

try:
    resposta = urllib.request.urlopen(url).read().decode("utf-8")
    dados = json.loads(resposta)

    print("RESPOSTA:")
    print(dados)

    atualizacoes = dados.get("result", [])

    print("\nTOTAL DE ATUALIZAÇÕES:", len(atualizacoes))

    for item in atualizacoes:

        print("\n" + "-" * 50)

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

        elif "my_chat_member" in item:

            chat = item["my_chat_member"]["chat"]

            print("CHAT/CANAL ENCONTRADO!")
            print("ID:", chat.get("id"))
            print("NOME:", chat.get("title") or chat.get("first_name"))
            print("USERNAME:", chat.get("username"))

    print("\n" + "=" * 50)
    print("FIM DO TESTE")
    print("=" * 50)

except urllib.error.HTTPError as erro:
    print("ERRO HTTP:", erro.code)
    print("RESPOSTA DO TELEGRAM:")

    try:
        detalhe = erro.read().decode("utf-8")
        print(detalhe)
    except Exception:
        print("Não foi possível ler a resposta.")

except Exception as erro:
    print("ERRO AO BUSCAR ATUALIZAÇÕES:")
    print(type(erro).__name__)
    print(erro)
