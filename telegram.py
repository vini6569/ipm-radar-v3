# ============================================================
# TELEGRAM
# IPM-RADAR-V3
#
# Responsável exclusivamente pelo envio de mensagens
# para o Telegram.
#
# O TOKEN e o CHAT_ID ficam protegidos nas variáveis
# de ambiente do Render.
# ============================================================

import os
import json
import urllib.request
import urllib.parse


def obter_configuracao():
    """
    Obtém as credenciais do Telegram
    através das variáveis de ambiente.
    """

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN não configurado."
        )

    if not chat_id:
        raise RuntimeError(
            "TELEGRAM_CHAT_ID não configurado."
        )

    return token, chat_id


def enviar_mensagem(mensagem):
    """
    Envia uma mensagem para o Telegram.
    """

    token, chat_id = obter_configuracao()

    url = (
        "https://api.telegram.org/"
        f"bot{token}/sendMessage"
    )

    dados = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": mensagem
    }).encode("utf-8")

    requisicao = urllib.request.Request(
        url,
        data=dados,
        method="POST",
        headers={
            "User-Agent": "IPM-Radar/3.0",
            "Content-Type": (
                "application/x-www-form-urlencoded"
            )
        }
    )

    with urllib.request.urlopen(
        requisicao,
        timeout=20
    ) as resposta:

        retorno = json.loads(
            resposta.read().decode(
                "utf-8",
                errors="ignore"
            )
        )

    if not retorno.get("ok"):
        raise RuntimeError(
            f"Telegram retornou erro: {retorno}"
        )

    return retorno
