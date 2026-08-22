import os
import json
import urllib.request
import urllib.error


TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


def enviar_mensagem(mensagem):
    if not TOKEN:
        print("ERRO: TELEGRAM_BOT_TOKEN não configurado.")
        return False

    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not chat_id:
        print("ERRO: TELEGRAM_CHAT_ID não configurado.")
        return False

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    dados = {
        "chat_id": chat_id,
        "text": mensagem
    }

    try:
        dados_json = json.dumps(dados).encode("utf-8")

        requisicao = urllib.request.Request(
            url,
            data=dados_json,
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(requisicao, timeout=20) as resposta:
            resultado = json.loads(
                resposta.read().decode("utf-8")
            )

        if resultado.get("ok"):
            print("OK: Mensagem enviada para o Telegram.")
            return True

        print("ERRO: Telegram recusou a mensagem:")
        print(resultado)
        return False

    except Exception as erro:
        print("ERRO AO ENVIAR TELEGRAM:")
        print(type(erro).__name__, erro)
        return False


def descobrir_chats():
    if not TOKEN:
        print("ERRO: TELEGRAM_BOT_TOKEN não configurado.")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

    try:
        with urllib.request.urlopen(url, timeout=20) as resposta:
            dados = resposta.read().decode("utf-8")

        resultado = json.loads(dados)

        print("=" * 60)
        print("DIAGNÓSTICO TELEGRAM - IPM RADAR")
        print("=" * 60)

        if not resultado.get("ok"):
            print("ERRO TELEGRAM:")
            print(resultado)
            return

        updates = resultado.get("result", [])

        print("UPDATES ENCONTRADOS:", len(updates))
        print()

        chats = {}

        for update in updates:
            mensagem = update.get("message")

            if not mensagem:
                continue

            chat = mensagem.get("chat")

            if not chat:
                continue

            chat_id = chat.get("id")
            chat_type = chat.get("type")
            chat_title = chat.get("title")
            chat_username = chat.get("username")

            chats[str(chat_id)] = {
                "id": chat_id,
                "tipo": chat_type,
                "nome": chat_title,
                "username": chat_username
            }

        if not chats:
            print("NENHUM CHAT ENCONTRADO.")
            print()
            print(
                "Envie uma mensagem no grupo ou no bot "
                "IPM RADAR e execute novamente."
            )
        else:
            print("CHATS ENCONTRADOS:")
            print()

            for chat in chats.values():
                print("ID:", chat["id"])
                print("TIPO:", chat["tipo"])
                print("NOME:", chat["nome"])
                print("USERNAME:", chat["username"])
                print("-" * 40)

    except urllib.error.HTTPError as erro:
        print("ERRO HTTP:", erro.code)

        try:
            print(erro.read().decode("utf-8"))
        except Exception:
            pass

    except Exception as erro:
        print(
            "ERRO:",
            type(erro).__name__,
            erro
        )


if __name__ == "__main__":
    descobrir_chats()
        
