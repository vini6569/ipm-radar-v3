# === ADIÇÃO 1: depois dos imports de motor_ipm ===
try:
    from telegram import enviar_mensagem
except ImportError:
    enviar_mensagem = None


def enviar_teste_telegram():
    mensagem = (
        "🧪 TESTE DO TELEGRAM — IPM RADAR V3\n\n"
        "✅ Robô iniciado com sucesso.\n"
        "📡 Conexão com o Telegram funcionando.\n"
        "📊 Radar IPM V3 está online."
    )

    if enviar_mensagem:
        try:
            enviar_mensagem(mensagem)
            print("✅ TESTE DO TELEGRAM ENVIADO COM SUCESSO.")
        except Exception as erro:
            print("❌ ERRO AO ENVIAR TESTE PARA O TELEGRAM:")
            print(type(erro).__name__, erro)
    else:
        print("⚠️ Módulo telegram não encontrado.")


# === ADIÇÃO 2: dentro de iniciar(), depois de:
# print("Histórico registrado:", quantidade_jogos())
# print()
# coloque:
enviar_teste_telegram()
print()
