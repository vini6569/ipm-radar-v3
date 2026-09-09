# ============================================================
# TELEGRAM
# IPM-RADAR-V5
#
# Função:
#   - Enviar sinais
#   - Enviar resultados
#   - Enviar relatórios
#   - Enviar lista PRÉ-LIVE detalhada
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

from config import Q_MIN, Q_MAX


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

        resultado = json.loads(dados)

        if not resultado.get("ok"):

            print(
                "❌ ERRO AO CONSULTAR TELEGRAM:"
            )

            print(resultado)

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

        for update in reversed(updates):

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

                return str(chat_id)

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

def enviar_mensagem(mensagem):

    if not TOKEN:

        print(
            "❌ TELEGRAM_BOT_TOKEN não configurado."
        )

        return False

    chat_id = CHAT_ID

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
        "text": str(mensagem),
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

        resultado = json.loads(retorno)

        if resultado.get("ok"):

            print(
                "✅ MENSAGEM ENVIADA PARA O TELEGRAM!"
            )

            return True

        print(
            "❌ TELEGRAM RECUSOU A MENSAGEM:"
        )

        print(resultado)

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

            print(corpo)

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
        "🤖 IPM-RADAR-V5\n"
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
                f"\n🧠 IPM registrado: {ipm}"
            )

        if mercado:

            mensagem += (
                f"\n🎯 Mercado: {mercado}"
            )

        if odd:

            mensagem += (
                f"\n💰 Odd: {odd}"
            )

    mensagem += (
        "\n\n"
        "📚 Resultado enviado para "
        "o laboratório IPM.\n"
        "\n"
        "🤖 IPM-RADAR-V5"
    )

    return enviar_mensagem(
        mensagem
    )


# ============================================================
# ENVIAR RELATÓRIO
# ============================================================

def enviar_relatorio(texto):

    mensagem = (
        "📊 RELATÓRIO — LABORATÓRIO IPM\n"
        "\n"
        f"{texto}\n"
        "\n"
        "🤖 IPM-RADAR-V5"
    )

    return enviar_mensagem(
        mensagem
    )


# ============================================================
# FORMATAÇÃO DE UM JOGO PRÉ-LIVE
# ============================================================

def formatar_jogo_pre_live(
    jogo
):

    casa = jogo.get(
        "casa",
        "Casa"
    )

    fora = jogo.get(
        "fora",
        "Fora"
    )

    horario = jogo.get(
        "horario",
        "--:--"
    )

    data = jogo.get(
        "data",
        ""
    )

    try:

        odd_casa = float(
            jogo.get(
                "odd_casa",
                0
            )
            or 0
        )

        odd_empate = float(
            jogo.get(
                "odd_empate",
                0
            )
            or 0
        )

        odd_visitante = float(
            jogo.get(
                "odd_visitante",
                0
            )
            or 0
        )

        q = float(
            jogo.get(
                "q",
                jogo.get(
                    "odd_pre_live",
                    0
                )
            )
            or 0
        )

        r = float(
            jogo.get(
                "r",
                0
            )
            or 0
        )

        prob_x = float(
            jogo.get(
                "probabilidade_x",
                0
            )
            or 0
        )

        prob_x_normalizada = float(
            jogo.get(
                "probabilidade_x_normalizada",
                0
            )
            or 0
        )

        indice_equilibrio = float(
            jogo.get(
                "indice_equilibrio",
                0
            )
            or 0
        )

    except (
        TypeError,
        ValueError
    ):

        return ""

    equilibrio = jogo.get(
        "equilibrio",
        "SEM_DADOS"
    )

    padrao = jogo.get(
        "padrao",
        "SEM_DADOS"
    )

    # --------------------------------------------------------
    # CLASSIFICAÇÃO VISUAL
    # --------------------------------------------------------

    if "EQUILÍBRIO" in equilibrio:

        indicador_equilibrio = "⚖️"

    elif "DESEQUILÍBRIO" in equilibrio:

        indicador_equilibrio = "⚠️"

    else:

        indicador_equilibrio = "❔"

    # --------------------------------------------------------
    # TEXTO
    # --------------------------------------------------------

    texto = (
        f"⚽ {horario} | "
        f"{casa} x {fora}\n"
        "\n"
        f"🏠 Casa: {odd_casa:.2f}\n"
        f"🤝 Empate (X): {odd_empate:.2f}\n"
        f"🚌 Visitante: {odd_visitante:.2f}\n"
        "\n"
        f"📐 Q: {q:.2f}\n"
        f"📊 R: {r:.2f}\n"
        f"{indicador_equilibrio} "
        f"Equilíbrio: {equilibrio}\n"
        f"📊 Índice de equilíbrio: "
        f"{indice_equilibrio:.2f}\n"
        "\n"
        f"📊 P(X): {prob_x:.2f}%\n"
        f"📊 P(X) normalizada: "
        f"{prob_x_normalizada:.2f}%\n"
        "\n"
        f"🎯 Hipótese: {padrao}\n"
    )

    return texto


# ============================================================
# ENVIAR LISTA PRÉ-LIVE
# ============================================================

def enviar_lista_pre_live(
    jogos,
    q_min=None,
    q_max=None
):

    if not jogos:

        print(
            "⚠️ NENHUM JOGO PRÉ-LIVE PARA ENVIAR."
        )

        return False

    if q_min is None:

        q_min = Q_MIN

    if q_max is None:

        q_max = Q_MAX

    # --------------------------------------------------------
    # CABEÇALHO
    # --------------------------------------------------------

    mensagem = (
        "🧪 IPM RADAR — PRÉ-LIVE V5\n"
        "\n"
        "📡 MAPA ESTATÍSTICO DOS JOGOS\n"
        "\n"
        f"📐 Faixa Q: "
        f"{q_min:.2f} → {q_max:.2f}\n"
        "📊 Q = região conjunta das pontas\n"
        "📊 R = relação de desequilíbrio\n"
        "⚖️ R baixo = maior equilíbrio\n"
        "⚠️ R alto = maior desequilíbrio\n"
        "\n"
    )

    # --------------------------------------------------------
    # PERÍODOS
    # --------------------------------------------------------

    periodos = (
        "06:00 - 12:00",
        "12:00 - 18:00",
        "18:00 - 00:00",
    )

    quantidade = 0

    for periodo in periodos:

        jogos_periodo = [
            jogo
            for jogo in jogos
            if jogo.get(
                "periodo"
            ) == periodo
        ]

        if not jogos_periodo:
            continue

        mensagem += (
            f"🕐 {periodo}\n"
            "════════════════════\n"
        )

        for jogo in jogos_periodo:

            try:

                q = float(
                    jogo.get(
                        "q",
                        jogo.get(
                            "odd_pre_live",
                            0
                        )
                    )
                    or 0
                )

            except (
                TypeError,
                ValueError
            ):

                continue

            if (
                q < q_min
                or q > q_max
            ):

                continue

            texto = formatar_jogo_pre_live(
                jogo
            )

            if not texto:
                continue

            mensagem += (
                texto
                + "────────────────────\n\n"
            )

            quantidade += 1

    # --------------------------------------------------------
    # NENHUM JOGO
    # --------------------------------------------------------

    if quantidade == 0:

        print(
            "⚠️ Nenhum jogo dentro "
            "do intervalo Q."
        )

        return False

    # --------------------------------------------------------
    # RODAPÉ
    # --------------------------------------------------------

    mensagem += (
        f"📋 Jogos selecionados: "
        f"{quantidade}\n"
        "\n"
        "📚 LABORATÓRIO IPM\n"
        "Este bloco é exclusivamente "
        "PRÉ-LIVE.\n"
        "\n"
        "🎯 Acompanhar:\n"
        "• Q\n"
        "• R\n"
        "• Equilíbrio\n"
        "• Índice de equilíbrio\n"
        "• P(X)\n"
        "• P(X) normalizada\n"
        "• Hipótese estatística\n"
        "\n"
        "⚠️ Não é entrada.\n"
        "⚠️ Não realiza apostas automaticamente.\n"
        "\n"
        "🤖 IPM-RADAR-V5"
    )

    # --------------------------------------------------------
    # TELEGRAM TEM LIMITE DE 4096 CARACTERES
    # --------------------------------------------------------

    limite = 3800

    if len(mensagem) <= limite:

        return enviar_mensagem(
            mensagem
        )

    # --------------------------------------------------------
    # DIVIDIR MENSAGEM
    # --------------------------------------------------------

    blocos = []

    atual = ""

    linhas = mensagem.split(
        "\n"
    )

    for linha in linhas:

        if (
            len(atual)
            + len(linha)
            + 1
            > limite
        ):

            if atual.strip():

                blocos.append(
                    atual.rstrip()
                )

            atual = linha + "\n"

        else:

            atual += linha + "\n"

    if atual.strip():

        blocos.append(
            atual.rstrip()
        )

    sucesso_total = True

    total_blocos = len(
        blocos
    )

    for indice, bloco in enumerate(
        blocos,
        start=1
    ):

        # Acrescenta identificação
        # somente quando houver divisão.

        cabecalho = (
            "🧪 IPM RADAR — PRÉ-LIVE V5\n"
            f"📄 Parte {indice}/{total_blocos}\n\n"
        )

        texto_envio = (
            cabecalho
            + bloco
        )

        if not enviar_mensagem(
            texto_envio
        ):

            sucesso_total = False

    return sucesso_total


# ============================================================
# TESTE DO TELEGRAM
# ============================================================

def teste_telegram():

    mensagem = (
        "🧪 TESTE DO TELEGRAM — "
        "IPM RADAR V5\n"
        "\n"
        "✅ Robô conectado ao Telegram.\n"
        "📡 Comunicação funcionando.\n"
        "📊 Radar IPM V5 online.\n"
        "\n"
        "Aguardando as informações "
        "do Radar."
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
