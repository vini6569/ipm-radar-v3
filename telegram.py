import os
import json
import urllib.request
import urllib.parse
import urllib.error


TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


# ============================================================
# ENVIAR MENSAGEM
# ============================================================

def enviar_mensagem(texto):

    if not TOKEN:
        print("ERRO: TELEGRAM_BOT_TOKEN não configurado.")
        return False

    if not CHAT_ID:
        print("ERRO: TELEGRAM_CHAT_ID não configurado.")
        return False

    url = (
        f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    )

    dados = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": texto
    }).encode("utf-8")

    requisicao = urllib.request.Request(
        url,
        data=dados,
        method="POST",
        headers={
            "Content-Type":
                "application/x-www-form-urlencoded",
            "User-Agent":
                "IPM-Radar-V3"
        }
    )

    try:

        with urllib.request.urlopen(
            requisicao,
            timeout=20
        ) as resposta:

            conteudo = (
                resposta
                .read()
                .decode("utf-8")
            )

        resultado = json.loads(conteudo)

        if resultado.get("ok"):

            print(
                "Telegram: mensagem enviada com sucesso."
            )

            return True

        print(
            "Telegram recusou a mensagem:"
        )

        print(resultado)

        return False

    except urllib.error.HTTPError as erro:

        print(
            "ERRO HTTP TELEGRAM:",
            erro.code
        )

        try:
            detalhe = (
                erro
                .read()
                .decode("utf-8")
            )

            print(detalhe)

        except Exception:
            pass

        return False

    except Exception as erro:

        print(
            "ERRO AO ENVIAR TELEGRAM:"
        )

        print(
            type(erro).__name__,
            erro
        )

        return False


# ============================================================
# TESTE MANUAL
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("TESTE TELEGRAM — IPM RADAR V3")
    print("=" * 60)

    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN não configurado.")
        raise SystemExit

    if not CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID não configurado.")
        raise SystemExit

    print("TOKEN: OK")
    print("CHAT_ID:", CHAT_ID)
    print()

    mensagem = (
        "🧪 IPM RADAR V3\n\n"
        "LABORATÓRIO — TESTE\n"
        "Telegram conectado com sucesso!\n\n"
        "Nenhuma aposta será realizada."
    )

    enviar_mensagem(mensagem)
