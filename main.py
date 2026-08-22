try:
    from telegram import enviar_mensagem
    print("✅ MÓDULO TELEGRAM IMPORTADO COM SUCESSO!")

except Exception as erro:
    print("❌ ERRO REAL AO IMPORTAR TELEGRAM:")
    print(type(erro).__name__)
    print(erro)
    raise


def enviar_teste_telegram():

    mensagem = (
        "🧪 TESTE DO TELEGRAM – IPM RADAR V3\n"
        "✅ Robô iniciado com sucesso.\n"
        "📡 Conexão com o Telegram funcionando.\n"
        "📊 Radar IPM V3 está online."
    )

    try:
        enviar_mensagem(mensagem)
        print("✅ TESTE DO TELEGRAM ENVIADO!")

    except Exception as erro:
        print("❌ ERRO AO ENVIAR TESTE:")
        print(type(erro).__name__)
        print(erro)
        raise


if __name__ == "__main__":
    enviar_teste_telegram()
