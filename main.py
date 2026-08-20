import time
from config import NOME_BOT, VERSAO
from odds_api import buscar_jogos_ao_vivo
from historico import quantidade_jogos


def iniciar():
    print("=" * 60)
    print(NOME_BOT)
    print("VERSÃO:", VERSAO)
    print("=" * 60)

    print("IPM-RADAR-V3 iniciado.")
    print("Histórico registrado:", quantidade_jogos())
    print()

    while True:

        try:
            jogos = buscar_jogos_ao_vivo()

            print("Jogos ao vivo encontrados:", len(jogos))

            for jogo in jogos:

                print("-" * 50)

                print(
                    jogo.get("home"),
                    "x",
                    jogo.get("away")
                )

                print("ID:", jogo.get("id"))
                print("PLACAR:", jogo.get("scores"))

            print()
            print("Nova consulta em 60 segundos...")

            time.sleep(60)

        except Exception as erro:

            print("ERRO NO RADAR:")
            print(type(erro).__name__)
            print(erro)

            time.sleep(30)


if __name__ == "__main__":
    iniciar()
