import os
import json
import urllib.request
import urllib.parse
import urllib.error


TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def descobrir_chat_id():
    """
    Descobre automaticamente o último chat que enviou
    mensagem para o bot.
    """

    if not TOKEN:
        print("ERRO: TELEGRAM_BOT_TOKEN não configurado.")
        return None

    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

    try:
        with urllib.request.urlopen(url, timeout=20) as resposta:
            dados = resposta.read().decode("utf-8")

        resultado = json.loads(dados)

        if not resultado.get("ok"):
            print("ERRO AO CONSULTAR TELEGRAM:")
            print(resultado)
            return None

        updates = resultado.get("result", [])

        if not updates:
            print("NENHUMA MENSAGEM ENCONTRADA.")
            print("Envie primeiro uma mensagem para o bot no Telegram.")
            return None

        # Procura o último chat válido
        for update in reversed(updates):
            mensagem = update.get("message")

            if not mensagem:
                continue

            chat = mensagem.get("chat")

            if not chat:
                continue

            chat_id = chat.get("id")

            if chat_id:
                print("CHAT ENCONTRADO:", chat_id)
                return str(chat_id)

        print("NÃO FOI POSSÍVEL ENCONTRAR CHAT.")
        return None

    except Exception as erro:
        print("ERRO AO DESCOBRIR CHAT:")
        print(type(erro).__name__, erro)
        return None


def enviar_mensagem(mensagem):
    """
    Envia uma mensagem para o Telegram.
    """

    if not TOKEN:
        print("ERRO: TELEGRAM_BOT_TOKEN não configurado.")
        return False

    chat_id = CHAT_ID

    # Se não existir CHAT_ID nas variáveis do Render,
    # tenta descobrir automaticamente.
    if not chat_id:
        chat_id = descobrir_chat_id()

    if not chat_id:
        print("ERRO: CHAT_ID não encontrado.")
        return False

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    dados = {
        "chat_id": chat_id,
        "text": str(mensagem)
    }

    dados_codificados = urllib.parse.urlencode(dados).encode("utf-8")

    try:
        requisicao = urllib.request.Request(
            url,
            data=dados_codificados,
            method="POST"
        )

        requisicao.add_header(
            "Content-Type",
            "application/x-www-form-urlencoded"
        )

        with urllib.request.urlopen(
            requisicao,
            timeout=20
        ) as resposta:

            retorno = resposta.read().decode("utf-8")

        resultado = json.loads(retorno)

        if resultado.get("ok"):
            print("✅ MENSAGEM ENVIADA PARA O TELEGRAM!")
            return True

        print("❌ TELEGRAM RECUSOU A MENSAGEM:")
        print(resultado)

        return False

    except urllib.error.HTTPError as erro:

        print("❌ ERRO HTTP AO ENVIAR TELEGRAM:")
        print("Código:", erro.code)

        try:
            corpo = erro.read().decode("utf-8")
            print("Resposta do Telegram:")
            print(corpo)
        except Exception:
            pass

        return False

    except Exception as erro:

        print("❌ ERRO AO ENVIAR TELEGRAM:")
        print(type(erro).__name__, erro)

        return False


def teste_telegram():

    mensagem = (
        "🧪 TESTE DO TELEGRAM — IPM RADAR V3\n\n"
        "✅ Robô iniciado com sucesso.\n"
        "📡 Conexão com o Telegram funcionando.\n"
        "📊 Radar IPM V3 está online."
    )

    sucesso = enviar_mensagem(mensagem)

    if sucesso:
        print("========================================")
        print("✅ TESTE DO TELEGRAM CONCLUÍDO!")
        print("========================================")
    else:
        print("========================================")
        print("❌ TESTE DO TELEGRAM FALHOU!")
        print("========================================")


if __name__ == "__main__":
    teste_telegram()
