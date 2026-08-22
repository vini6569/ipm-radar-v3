# ============================================================
# TELEGRAM
# IPM-RADAR-V3
#
# Função:
# Enviar sinais, entradas e resultados do Radar
# para o Telegram.
#
# IMPORTANTE:
# Este módulo NÃO realiza apostas.
# Apenas envia informações.
# ============================================================

import os
import json
import urllib.request
import urllib.parse
import urllib.error


# ============================================================
# CONFIGURAÇÃO
# ============================================================

TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
).strip()

CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID",
    ""
).strip()


# ============================================================
# DESCOBRIR CHAT ID
# ============================================================

def descobrir_chat_id():

    if not TOKEN:

        print(
            "❌ TELEGRAM_BOT_TOKEN não configurado."
        )

        return None

    url = (
        f"https://api.telegram.org/"
        f"bot{TOKEN}/getUpdates"
    )

    try:

        with urllib.request.urlopen(
            url,
            timeout=20
        ) as resposta:

            dados = (
                resposta
                .read()
                .decode("utf-8")
            )

        resultado = json.loads(
            dados
        )

        if not resultado.get(
            "ok"
        ):

            print(
                "❌ ERRO AO CONSULTAR TELEGRAM:"
            )

            print(
                resultado
            )

            return None

        updates = resultado.get(
            "result",
            []
        )

        if not updates:

            print(
                "⚠️ Nenhuma mensagem encontrada."
            )

            print(
                "Envie primeiro uma mensagem "
                "para o bot no Telegram."
            )

            return None

        # ====================================================
        # PROCURAR ÚLTIMO CHAT VÁLIDO
        # ====================================================

        for update in reversed(
            updates
        ):

            mensagem = update.get(
                "message"
            )

            if not mensagem:

                continue

            chat = mensagem.get(
                "chat"
            )

            if not chat:

                continue

            chat_id = chat.get(
                "id"
            )

            if chat_id:

                print(
                    "CHAT ENCONTRADO:",
                    chat_id
                )

                return str(
                    chat_id
                )

        print(
            "❌ Não foi possível encontrar chat."
        )

        return None

    except Exception as erro:

        print(
            "❌ ERRO AO DESCOBRIR CHAT:"
        )

        print(
            type(erro).__name__,
            erro
        )

        return None


# ============================================================
# ENVIO DE MENSAGEM
# ============================================================

def enviar_mensagem(
    mensagem
):

    if not TOKEN:

        print(
            "❌ TELEGRAM_BOT_TOKEN não configurado."
        )

        return False

    chat_id = CHAT_ID

    # ========================================================
    # TENTAR DESCOBRIR CHAT AUTOMATICAMENTE
    # ========================================================

    if not chat_id:

        chat_id = descobrir_chat_id()

    if not chat_id:

        print(
            "❌ TELEGRAM_CHAT_ID não encontrado."
        )

        return False

    url = (
        f"https://api.telegram.org/"
        f"bot{TOKEN}/sendMessage"
    )

    dados = {

        "chat_id": chat_id,

        "text": str(
            mensagem
        ),

        "disable_web_page_preview": True

    }

    dados_codificados = (
        urllib.parse
        .urlencode(dados)
        .encode("utf-8")
    )

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

            retorno = (
                resposta
                .read()
                .decode("utf-8")
            )

        resultado = json.loads(
            retorno
        )

        if resultado.get(
            "ok"
        ):

            print(
                "✅ MENSAGEM ENVIADA PARA O TELEGRAM!"
            )

            return True

        print(
            "❌ TELEGRAM RECUSOU A MENSAGEM:"
        )

        print(
            resultado
        )

        return False

    except urllib.error.HTTPError as erro:

        print(
            "❌ ERRO HTTP AO ENVIAR TELEGRAM:"
        )

        print(
            "Código:",
            erro.code
        )

        try:

            corpo = (
                erro
                .read()
                .decode("utf-8")
            )

            print(
                "Resposta do Telegram:"
            )

            print(
                corpo
            )

        except Exception:

            pass

        return False

    except Exception as erro:

        print(
            "❌ ERRO AO ENVIAR TELEGRAM:"
        )

        print(
            type(erro).__name__,
            erro
        )

        return False


# ============================================================
# ENVIAR ENTRADA DO RADAR
# ============================================================

def enviar_entrada(
    casa,
    fora,
    placar,
    minuto,
    mercado,
    linha,
    odd_anterior,
    odd_atual,
    variacao,
    forca,
    ipm,
    sinal
):

    mensagem = (

        "🚨 IPM RADAR — ENTRADA\n"
        "\n"

        f"⚽ {casa} x {fora}\n"

        f"📊 Placar: {placar}\n"

        f"⏱️ Minuto: {minuto}\n"

        "\n"

        f"🎯 Mercado: {mercado}\n"

        f"📏 Linha: {linha}\n"

        f"📉 Odd: {odd_anterior:.2f} "
        f"→ {odd_atual:.2f}\n"

        f"📈 Variação: {variacao:+.2f}%\n"

        f"🔥 Força: {forca}\n"

        f"🧠 IPM: {ipm:.0f}/100\n"

        f"🚦 {sinal}\n"

        "\n"

        "🤖 IPM-RADAR-V3\n"

        "⚠️ Informação estatística — "
        "não realiza apostas automaticamente."
    )

    return enviar_mensagem(
        mensagem
    )


# ============================================================
# ENVIAR CICLO ENCERRADO
# ============================================================

def enviar_ciclo(
    casa,
    fora,
    placar_final,
    resultado,
    gols_total,
    dados=None
):

    mensagem = (

        "🏁 CICLO FINALIZADO\n"
        "\n"

        f"⚽ {casa} x {fora}\n"

        f"🏆 Placar final: {placar_final}\n"

        f"🎯 Resultado: {resultado}\n"

        f"⚽ Total de gols: {gols_total}\n"
    )

    # ========================================================
    # DADOS EXTRAS DO LABORATÓRIO
    # ========================================================

    if isinstance(
        dados,
        dict
    ):

        ipm = dados.get(
            "ipm"
        )

        mercado = dados.get(
            "mercado"
        )

        odd = dados.get(
            "odd"
        )

        if ipm is not None:

            mensagem += (
                f"\n🧠 IPM registrado: "
                f"{ipm}"
            )

        if mercado:

            mensagem += (
                f"\n🎯 Mercado: "
                f"{mercado}"
            )

        if odd:

            mensagem += (
                f"\n💰 Odd: "
                f"{odd}"
            )

    mensagem += (

        "\n\n"
        "📚 Resultado enviado para "
        "o laboratório IPM.\n"
        "\n"
        "🤖 IPM-RADAR-V3"
    )

    return enviar_mensagem(
        mensagem
    )


# ============================================================
# ENVIAR RELATÓRIO DO LABORATÓRIO
# ============================================================

def enviar_relatorio(
    texto
):

    mensagem = (

        "📊 RELATÓRIO — LABORATÓRIO IPM\n"
        "\n"
        f"{texto}\n"
        "\n"
        "🤖 IPM-RADAR-V3"
    )

    return enviar_mensagem(
        mensagem
    )


# ============================================================
# TESTE DO TELEGRAM
# ============================================================

def teste_telegram():

    mensagem = (

        "🧪 TESTE DO TELEGRAM — "
        "IPM RADAR V3\n"
        "\n"
        "✅ Robô conectado ao Telegram.\n"
        "📡 Comunicação funcionando.\n"
        "📊 Radar IPM V3 online.\n"
        "\n"
        "Aguardando as entradas do Radar."
    )

    sucesso = enviar_mensagem(
        mensagem
    )

    print()

    print(
        "=" * 50
    )

    if sucesso:

        print(
            "✅ TESTE DO TELEGRAM CONCLUÍDO!"
        )

    else:

        print(
            "❌ TESTE DO TELEGRAM FALHOU!"
        )

    print(
        "=" * 50
    )


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":

    teste_telegram()
