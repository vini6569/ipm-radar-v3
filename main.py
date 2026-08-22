import os
import json
import time
import urllib.request
import urllib.parse

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = "-1004457093213"

print("=" * 60)
print("🤖 IPM EMPATE E GOL - TESTE TELEGRAM")
print("=" * 60)

if not TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN não encontrado!")
    while True:
        time.sleep(60)

def enviar_telegram(texto):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    dados = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": texto
    }).encode("utf-8")

    requisicao = urllib.request.Request(
        url,
        data=dados,
        method="POST"
    )

    try:
        with urllib.request.urlopen(requisicao, timeout=20) as resposta:
            resultado = resposta.read().decode("utf-8")

        print("✅ RESPOSTA DO TELEGRAM:")
        print(resultado)

        return True

    except Exception as erro:
        print("❌ ERRO AO ENVIAR TELEGRAM:")
        print(erro)
        return False


print(f"📌 CHAT ID: {CHAT_ID}")
print()

enviar_telegram(
    "🟢 TESTE DO ROBÔ IPM\n\n"
    "Telegram conectado com sucesso!\n"
    "Chat ID confirmado."
)

print()
print("🟢 BOT PERMANECERÁ RODANDO...")
print("=" * 60)

while True:
    time.sleep(60)
