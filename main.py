import os
import json
import urllib.request

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

print("=" * 60)
print("🔎 DESCOBRINDO CHAT ID DO TELEGRAM")
print("=" * 60)

if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN não encontrado!")
    raise SystemExit

url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

try:
    with urllib.request.urlopen(url, timeout=20) as resposta:
        dados = resposta.read().decode("utf-8")

    resultado = json.loads(dados)

    print("Resposta do Telegram:")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))

    if not resultado.get("ok"):
        print("❌ Erro ao consultar Telegram.")
        raise SystemExit

    updates = resultado.get("result", [])

    print()
    print("=" * 60)
    print(f"📨 UPDATES ENCONTRADOS: {len(updates)}")
    print("=" * 60)

    encontrados = set()

    for update in updates:
        mensagem = update.get("message")

        if not mensagem:
            continue

        chat = mensagem.get("chat", {})
        chat_id = chat.get("id")
        nome = chat.get("first_name", "")
        sobrenome = chat.get("last_name", "")
        username = chat.get("username", "")
        texto = mensagem.get("text", "")

        if chat_id:
            encontrados.add(chat_id)

            print()
            print("✅ CHAT ENCONTRADO")
            print(f"CHAT ID: {chat_id}")
            print(f"NOME: {nome} {sobrenome}")
            print(f"USERNAME: @{username}")
            print(f"MENSAGEM: {texto}")

    print()
    print("=" * 60)

    if encontrados:
        print("🎯 CHAT IDs:")
        for chat_id in encontrados:
            print(chat_id)
    else:
        print("⚠️ NENHUM CHAT ENCONTRADO.")
        print("Envie /start novamente para o bot.")

    print("=" * 60)

except Exception as erro:
    print("❌ ERRO:")
    print(erro)
