import os
import json
import urllib.request
import urllib.error


TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")


def descobrir_chats():

    if not TOKEN:
        print("ERRO: TELEGRAM_BOT_TOKEN não configurado.")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

    try:

        with urllib.request.urlopen(
            url,
            timeout=20
        ) as resposta:

            dados = resposta.read().decode("utf-8")

        resultado = json.loads(dados)

        print("=" * 60)
        print("DIAGNÓSTICO TELEGRAM — IPM RADAR V3")
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
                "Envie uma mensagem no grupo "
                "IPM RADAR — ENTRADA e execute novamente."
            )

        else:

            print("CHATS ENCONTRADOS:")
            print()

            for chat in chats.values():

                print(
                    "ID:",
                    chat["id"]
                )

                print(
                    "TIPO:",
                    chat["tipo"]
                )

                print(
                    "NOME:",
                    chat["nome"]
                )

                print(
                    "USERNAME:",
                    chat["username"]
                )

                print("-" * 40)

    except urllib.error.HTTPError as erro:

        print(
            "ERRO HTTP:",
            erro.code
        )

        try:
            print(
                erro.read().decode("utf-8")
            )
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
