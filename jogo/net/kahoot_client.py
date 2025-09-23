# jogo/net/kahoot_client.py
# Cliente simples em Python para integrar com o host (Node) do jogo.
# Requer: pip install websockets
import asyncio, json, sys
try:
    import websockets
except Exception as e:
    print("ERRO: módulo 'websockets' não instalado. Rode: pip install websockets")
    raise

class KahootClient:
    def __init__(self, server_url="ws://192.168.0.10:3000", name="Player", team="attack", game_id="main"):
        self.server_url = server_url
        self.name = name
        self.team = "defense" if team == "defense" else "attack"
        self.game_id = game_id
        self.ws = None
        self.player_id = None
        self.state = None

    async def connect(self):
        self.ws = await websockets.connect(self.server_url, max_size=None)
        await self._send("join", {"name": self.name, "team": self.team, "gameId": self.game_id})
        # aguarda uma confirmação inicial
        while True:
            raw = await self.ws.recv()
            msg = json.loads(raw)
            if msg.get("type") in ("joined","resumed"):
                self.player_id = msg["payload"]["playerId"]
                # não retorna ainda; espera full_state para ter placar inicial
            if msg.get("type") == "full_state":
                self.state = msg["payload"]
                return self.state  # estado inicial
            # ignora outras mensagens por ora

    async def ready(self, on_players_update=None):
        await self._send("ready", {"ready": True})
        # opcional: processa algumas mensagens até ver players_update
        if on_players_update:
            while True:
                msg = await self._recv()
                if msg.get("type") in ("players_update","score_broadcast","player_finished"):
                    on_players_update(msg.get("payload",{}))
                    break

    async def wait_for_start(self, on_tick=None):
        # bloqueia até receber 'start' do host
        while True:
            msg = await self._recv()
            t = msg.get("type")
            if t == "start":
                return True
            # dá chance de o chamador consumir atualizações durante o lobby
            if on_tick:
                on_tick(t, msg.get("payload"))

    async def update_score(self, delta:int):
        await self._send("score_update", {"scoreDelta": int(delta)})

    async def finish(self, final_score:int):
        await self._send("finish", {"finalScore": int(final_score)})

    async def close(self):
        try:
            if self.ws:
                await self.ws.close()
        except Exception:
            pass

    async def _send(self, type_, payload):
        await self.ws.send(json.dumps({"type": type_, "payload": payload}))

    async def _recv(self):
        raw = await self.ws.recv()
        return json.loads(raw)
