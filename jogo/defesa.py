# jogo/defesa-jogo.py
# Modo jogador (DEFESA): nome -> PRONTO -> aguarda 'start' do host -> envia pontuação final.
# Ajuste o IP do host abaixo e rode:  python defesa-jogo.py
import asyncio, os, sys, random
from jogo.net.kahoot_client import KahootClient

HOST_WS = "ws://192.168.0.10:3000"   # <<< ALTERE PARA O IP DO HOST NA SUA LAN

def input_nome():
    try:
        nome = input("Seu nome (DEFESA): ").strip()
    except EOFError:
        nome = ""
    return nome or "Jogador-Defesa"

async def main():
    print(f"Conectando ao host em: {HOST_WS} ...")
    nome = input_nome()
    client = KahootClient(server_url=HOST_WS, name=nome, team="defense")
    st = await client.connect()
    print("Conectado. Jogadores atuais:", len(st.get("players", {})))
    print("Pressione ENTER para marcar 'PRONTO'...")
    try: input()
    except EOFError: pass

    def on_update(p):
        players = p.get("players", {})
        print(f"[Lobby] Jogadores prontos: {sum(1 for x in players.values() if x.get('ready'))} / {len(players)}")

    await client.ready(on_players_update=on_update)
    print("Aguardando o host iniciar a partida...")
    await client.wait_for_start()
    print("==> PARTIDA INICIADA! <==")

    # -------- INTEGRAÇÃO COM O SEU JOGO REAL --------
    # Aqui você chama seu loop do jogo. Exemplo didático abaixo:
    score = 0
    for _ in range(5):
        await asyncio.sleep(1.0)
        inc = random.randint(1, 10)
        score += inc
        print(f"[Jogo DEFESA] +{inc} pontos (parcial={score})")
        await client.update_score(inc)
    # -------------------------------------------------

    print(f"Finalizando com score={score}...")
    await client.finish(score)
    await client.close()
    print("Score enviado. Você pode fechar.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nEncerrado pelo usuário.")
