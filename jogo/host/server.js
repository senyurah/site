// Host central do jogo: WebSocket server + static para servir o cliente.
// Execução: npm install && npm start (porta padrão 3000)

const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { v4: uuidv4 } = require('uuid');

const app = express();
app.use(express.static('public'));

const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Estado em memória por jogo
// games: {
//   [gameId]: {
//     clients: Map<WebSocket, { playerId }>,
//     players: {
//       [playerId]: { name, team, ready, score, connected, lastSeen }
//     },
//     hostId: string|null,
//     started: boolean,
//     createdAt: number
//   }
// }
const games = {};
const DEFAULT_GAME = 'main';

function ensureGame(gameId = DEFAULT_GAME) {
  if (!games[gameId]) {
    games[gameId] = {
      clients: new Map(),
      players: {},
      hostId: null,
      started: false,
      createdAt: Date.now(),
    };
  }
  return games[gameId];
}

function computeTeamScores(game) {
  const teamScores = { attack: 0, defense: 0 };
  for (const pId in game.players) {
    const p = game.players[pId];
    const val = Number(p.score || 0);
    if (p.team === 'defense') teamScores.defense += val; else teamScores.attack += val;
  }
  return teamScores;
}

function broadcastToGame(gameId, obj) {
  const game = games[gameId];
  if (!game) return;
  const raw = JSON.stringify(obj);
  for (const ws of game.clients.keys()) {
    if (ws.readyState === WebSocket.OPEN) ws.send(raw);
  }
}

function fullStatePayload(gameId) {
  const game = games[gameId];
  return {
    type: 'full_state',
    payload: {
      gameId,
      players: game.players,
      teamScores: computeTeamScores(game),
      started: game.started,
      hostId: game.hostId,
    }
  };
}

function playersUpdatePayload(gameId) {
  const game = games[gameId];
  return { type: 'players_update', payload: { players: game.players } };
}

function chooseNewHost(gameId) {
  const game = games[gameId];
  if (!game) return null;
  const candidates = Object.entries(game.players)
    .filter(([, p]) => p.connected)
    .map(([pid]) => pid);
  game.hostId = candidates.length ? candidates[0] : null;
  return game.hostId;
}

wss.on('connection', (ws) => {
  let currentGameId = DEFAULT_GAME;
  ensureGame(currentGameId);
  let boundPlayerId = null; // quem este socket representa

  function bindToPlayer(game, playerId) {
    // remove ws antigo se houver
    for (const [sock, meta] of game.clients.entries()) {
      if (meta.playerId === playerId && sock !== ws) {
        try { sock.close(); } catch {}
        game.clients.delete(sock);
      }
    }
    boundPlayerId = playerId;
    game.clients.set(ws, { playerId });
  }

  ws.on('message', (raw) => {
    let data;
    try { data = JSON.parse(raw.toString()); } catch (e) {
      ws.send(JSON.stringify({ type: 'error', payload: { message: 'invalid json' } }));
      return;
    }
    const { type, payload = {} } = data;

    if (type === 'join') {
      // payload: { playerId?, name, team, role?, gameId? }
      currentGameId = payload.gameId || DEFAULT_GAME;
      const game = ensureGame(currentGameId);

      let playerId = payload.playerId;
      const isResume = playerId && game.players[playerId];

      if (isResume) {
        // Reconexão
        const p = game.players[playerId];
        bindToPlayer(game, playerId);
        p.connected = true;
        p.lastSeen = Date.now();
        // opcionalmente atualiza nome/time se enviados
        if (payload.name) p.name = payload.name;
        if (payload.team) p.team = payload.team === 'defense' ? 'defense' : 'attack';

        ws.send(JSON.stringify({ type: 'resumed', payload: { playerId, gameId: currentGameId } }));
        ws.send(JSON.stringify(fullStatePayload(currentGameId)));
        broadcastToGame(currentGameId, playersUpdatePayload(currentGameId));
        return;
      }

      // Novo jogador
      playerId = uuidv4();
      const name = payload.name || `Player-${playerId.slice(0, 4)}`;
      const team = payload.team === 'defense' ? 'defense' : 'attack';

      bindToPlayer(game, playerId);
      game.players[playerId] = {
        name,
        team,
        ready: false,
        score: 0,
        connected: true,
        lastSeen: Date.now(),
      };

      // papel e autoridade de host
      if (!game.hostId && payload.role === 'host') {
        game.hostId = playerId;
        broadcastToGame(currentGameId, { type: 'host_update', payload: { hostId: game.hostId } });
      } else if (payload.role === 'host' && game.hostId) {
        ws.send(JSON.stringify({ type: 'info', payload: { message: 'Host já definido nesta sala' } }));
      }

      ws.send(JSON.stringify({ type: 'joined', payload: { playerId, gameId: currentGameId, name, team } }));
      ws.send(JSON.stringify(fullStatePayload(currentGameId)));
      broadcastToGame(currentGameId, playersUpdatePayload(currentGameId));
      return;
    }

    const game = ensureGame(currentGameId);
    if (!boundPlayerId || !game.players[boundPlayerId]) {
      ws.send(JSON.stringify({ type: 'error', payload: { message: 'not joined' } }));
      return;
    }

    const me = game.players[boundPlayerId];

    if (type === 'ready') {
      me.ready = !!payload.ready;
      broadcastToGame(currentGameId, playersUpdatePayload(currentGameId));
      return;
    }

    if (type === 'score_update') {
      const delta = Number(payload.scoreDelta) || 0;
      me.score = (me.score || 0) + delta;
      broadcastToGame(currentGameId, {
        type: 'score_broadcast',
        payload: { players: game.players, teamScores: computeTeamScores(game) }
      });
      return;
    }

    if (type === 'start_request') {
      if (game.hostId !== boundPlayerId) {
        ws.send(JSON.stringify({ type: 'error', payload: { message: 'apenas o host pode iniciar' } }));
        return;
      }
      const connectedPlayers = Object.values(game.players).filter(p => p.connected);
      const allReady = connectedPlayers.length >= 4 && connectedPlayers.every(p => p.ready);
      if (!allReady) {
        ws.send(JSON.stringify({ type: 'error', payload: { message: 'jogadores conectados precisam estar prontos (mínimo 4)' } }));
        return;
      }
      game.started = true;
      broadcastToGame(currentGameId, { type: 'start', payload: { message: 'game started' } });
      return;
    }

    if (type === 'end_session') {
      if (game.hostId !== boundPlayerId) {
        ws.send(JSON.stringify({ type: 'error', payload: { message: 'apenas o host pode encerrar' } }));
        return;
      }
      broadcastToGame(currentGameId, { type: 'end_session', payload: { message: 'session ending' } });
      for (const pid in game.players) {
        game.players[pid].score = 0;
        game.players[pid].ready = false;
      }
      game.started = false;
      broadcastToGame(currentGameId, playersUpdatePayload(currentGameId));
      ws.send(JSON.stringify(fullStatePayload(currentGameId)));
      return;
    }

    if (type === 'claim_host') {
      if (!game.hostId) {
        game.hostId = boundPlayerId;
        broadcastToGame(currentGameId, { type: 'host_update', payload: { hostId: game.hostId } });
      } else {
        ws.send(JSON.stringify({ type: 'error', payload: { message: 'host já existe' } }));
      }
      return;
    }

    if (type === 'host_transfer') {
      if (game.hostId !== boundPlayerId) {
        ws.send(JSON.stringify({ type: 'error', payload: { message: 'apenas o host pode transferir' } }));
        return;
      }
      const target = String(payload.targetPlayerId || '');
      if (!target || !game.players[target] || !game.players[target].connected) {
        ws.send(JSON.stringify({ type: 'error', payload: { message: 'destinatário inválido ou offline' } }));
        return;
      }
      game.hostId = target;
      broadcastToGame(currentGameId, { type: 'host_update', payload: { hostId: game.hostId } });
      return;
    }

    if (type === 'leave') {
      const wasHost = (game.hostId === boundPlayerId);
      delete game.players[boundPlayerId];
      game.clients.delete(ws);
      boundPlayerId = null;
      if (wasHost) {
        const newHost = chooseNewHost(currentGameId);
        broadcastToGame(currentGameId, { type: 'host_update', payload: { hostId: newHost } });
      }
      broadcastToGame(currentGameId, playersUpdatePayload(currentGameId));
      return;
    }

    ws.send(JSON.stringify({ type: 'error', payload: { message: 'unknown message type' } }));
  });

  ws.on('close', () => {
    const game = games[currentGameId];
    if (!game) return;
    const meta = game.clients.get(ws);
    if (!meta) return;
    const pid = meta.playerId;
    game.clients.delete(ws);
    const p = game.players[pid];
    if (p) {
      p.connected = false;
      p.lastSeen = Date.now();
      const wasHost = (game.hostId === pid);
      if (wasHost) {
        const newHost = chooseNewHost(currentGameId);
        if (newHost !== pid) {
          broadcastToGame(currentGameId, { type: 'host_update', payload: { hostId: newHost } });
        }
      }
      broadcastToGame(currentGameId, playersUpdatePayload(currentGameId));
    }
  });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Game host listening on port ${PORT}`);
});
