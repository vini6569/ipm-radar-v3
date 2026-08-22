import time
import os
import threading

from config import NOME_BOT, VERSAO
from odds_api import buscar_jogos_ao_vivo, buscar_odds_multiplos, extrair_mercados
from historico import quantidade_jogos
from motor_ipm import calcular_variacao_odd, classificar_forca
from http.server import HTTPServer, BaseHTTPRequestHandler


# ============================================================
# MEMÓRIA E CONTADORES
# ============================================================

memoria_odds = {}
total_odds_processadas = 0
total_movimentos = 0

# Só considera movimentação real quando a variação atingir
# pelo menos este percentual.
# Pode ser alterado no Render pela variável de ambiente:
# MIN_VARIACAO_ODDS=2.0
MIN_VARIACAO_ODDS = float(os.environ.get("MIN_VARIACAO_ODDS", "2.0"))


# ============================================================
# SERVIDOR DE SAÚDE DO RENDER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"IPM RADAR V3 ONLINE")

    def log_message(self, format, *args):
        return


def iniciar_servidor():
    porta = int(os.environ.get("PORT", 10000))
    servidor = HTTPServer(("0.0.0.0", porta), HealthHandler)
    servidor.serve_forever()


# ============================================================
# PROCESSAMENTO DE MOVIMENTAÇÃO
# ============================================================

def processar_movimentacao(evento_id, mercado, linha, odd_atual):
    global total_odds_processadas, total_movimentos

    try:
        odd_atual = float(odd_atual)
    except (TypeError, ValueError):
        return None

    if odd_atual <= 0:
        return None

    total_odds_processadas += 1

    chave = (str(evento_id), str(mercado), str(linha))

    # Primeira vez que esta odd aparece:
    # apenas grava na memória, sem chamar de movimento.
    if chave not in memoria_odds:
        memoria_odds[chave] = odd_atual
        print(
            f"  NOVA ODD | {mercado} | Linha: {linha} | "
            f"Odd: {odd_atual:.2f}"
        )
        return None

    odd_anterior = memoria_odds[chave]

    # Atualiza a memória com a odd mais recente.
    memoria_odds[chave] = odd_atual

    variacao = calcular_variacao_odd(odd_anterior, odd_atual)
    forca = classificar_forca(variacao)

    # ========================================================
    # FILTRO PRINCIPAL:
    # pequenas oscilações não são consideradas movimento.
    # ========================================================
    if abs(variacao) >= MIN_VARIACAO_ODDS:
        total_movimentos += 1

        print(
            f"  MOVIMENTO REAL | {mercado} | Linha: {linha} | "
            f"{odd_anterior:.2f} → {odd_atual:.2f} | "
            f"{variacao:+.2f}% | {forca}"
        )

        return {
            "mercado": mercado,
            "linha": linha,
            "odd_anterior": odd_anterior,
            "odd_atual": odd_atual,
            "variacao_pct": round(variacao, 2),
            "forca": forca
        }

    # Oscilação abaixo do limite: não conta como movimento.
    return None


# ============================================================
# EXIBIÇÃO DAS ODDS
# ============================================================

def mostrar_odds(jogo):
    print("\nTOTAL GOALS")
    gols = jogo.get("gols", [])

    if gols:
        for odd in gols:
            print(
                f"  Linha {odd.get('linha')} | "
                f"Over: {odd.get('over')} | "
                f"Under: {odd.get('under')}"
            )
    else:
        print("  Sem odds de Total Goals.")

    print("\nASIAN HANDICAP")
    handicap = jogo.get("handicap", [])

    if handicap:
        for odd in handicap:
            print(
                f"  Linha {odd.get('linha')} | "
                f"Casa: {odd.get('home')} | "
                f"Fora: {odd.get('away')}"
            )
    else:
        print("  Sem odds de Asian Handicap.")

    print("\nRESULTADO 1X2")
    resultado = jogo.get("resultado", [])

    if resultado:
        for odd in resultado:
            print(
                f"  Casa: {odd.get('home')} | "
                f"Empate: {odd.get('draw')} | "
                f"Fora: {odd.get('away')}"
            )
    else:
        print("  Sem odds de Resultado.")


# ============================================================
# ANÁLISE DE MOVIMENTAÇÃO
# ============================================================

def analisar_movimentacao(jogo):
    evento_id = jogo.get("id")

    if not evento_id:
        return

    print("\nMOVIMENTAÇÃO DE ODDS")

    for odd in jogo.get("gols", []):
        linha = odd.get("linha")

        processar_movimentacao(
            evento_id,
            "OVER",
            linha,
            odd.get("over")
        )

        processar_movimentacao(
            evento_id,
            "UNDER",
            linha,
            odd.get("under")
        )

    for odd in jogo.get("handicap", []):
        linha = odd.get("linha")

        processar_movimentacao(
            evento_id,
            "HANDICAP_HOME",
            linha,
            odd.get("home")
        )

        processar_movimentacao(
            evento_id,
            "HANDICAP_AWAY",
            linha,
            odd.get("away")
        )

    for odd in jogo.get("resultado", []):
        processar_movimentacao(
            evento_id,
            "HOME",
            "1X2",
            odd.get("home")
        )

        processar_movimentacao(
            evento_id,
            "DRAW",
            "1X2",
            odd.get("draw")
        )

        processar_movimentacao(
            evento_id,
            "AWAY",
            "1X2",
            odd.get("away")
        )


# ============================================================
# LOOP PRINCIPAL
# ============================================================

def iniciar():
    print("=" * 60)
    print(NOME_BOT)
    print("VERSÃO:", VERSAO)
    print("=" * 60)
    print("IPM-RADAR-V3 iniciado.")
    print("Filtro mínimo de movimentação:", f"{MIN_VARIACAO_ODDS:.2f}%")
    print("Histórico registrado:", quantidade_jogos())
    print()

    while True:
        try:
            jogos = buscar_jogos_ao_vivo()

            if not isinstance(jogos, list):
                jogos = []

            print("Jogos ao vivo encontrados:", len(jogos))

            odds_eventos = buscar_odds_multiplos(jogos) if jogos else []

            if not isinstance(odds_eventos, list):
                odds_eventos = []

            print(
                "Eventos com odds recebidos:",
                len(odds_eventos)
            )

            odds_por_id = {}

            for odds_evento in odds_eventos:
                if not isinstance(odds_evento, dict):
                    continue

                evento_id = odds_evento.get("id")

                if evento_id:
                    odds_por_id[str(evento_id)] = odds_evento

            print(
                "Eventos organizados por ID:",
                len(odds_por_id)
            )

            for jogo in jogos:
                if not isinstance(jogo, dict):
                    continue

                print("-" * 60)
                print(
                    jogo.get("home"),
                    "x",
                    jogo.get("away")
                )
                print("ID:", jogo.get("id"))
                print("PLACAR:", jogo.get("scores"))

                jogo_id = jogo.get("id")
                odds_evento = odds_por_id.get(str(jogo_id))

                if odds_evento:
                    mercados = extrair_mercados(odds_evento)

                    if not isinstance(mercados, dict):
                        mercados = {}

                    jogo["gols"] = mercados.get("gols", [])
                    jogo["handicap"] = mercados.get("handicap", [])
                    jogo["resultado"] = mercados.get(
                        "resultado",
                        []
                    )

                    print(
                        "Mercados extraídos:",
                        "gols=", len(jogo["gols"]),
                        "| handicap=", len(jogo["handicap"]),
                        "| resultado=", len(jogo["resultado"])
                    )

                else:
                    jogo["gols"] = []
                    jogo["handicap"] = []
                    jogo["resultado"] = []

                    print(
                        "Nenhuma resposta de odds encontrada "
                        "para este ID."
                    )

                mostrar_odds(jogo)
                analisar_movimentacao(jogo)

            print("\n" + "=" * 60)
            print("DIAGNÓSTICO IPM")
            print("=" * 60)
            print(
                "Jogos nesta consulta:",
                len(jogos)
            )
            print(
                "Eventos com odds:",
                len(odds_eventos)
            )
            print(
                "Odds processadas:",
                total_odds_processadas
            )
            print(
                "Movimentos reais detectados:",
                total_movimentos
            )
            print(
                "Odds na memória:",
                len(memoria_odds)
            )
            print(
                "Filtro mínimo:",
                f"{MIN_VARIACAO_ODDS:.2f}%"
            )
            print("=" * 60)
            print("\nNova consulta em 60 segundos...")

            time.sleep(60)

        except Exception as erro:
            print("\nERRO NO RADAR:")
            print(type(erro).__name__)
            print(erro)
            print()
            time.sleep(30)


if __name__ == "__main__":
    threading.Thread(
        target=iniciar_servidor,
        daemon=True
    ).start()

    iniciar()
        
