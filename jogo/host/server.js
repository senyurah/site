// Host central do jogo com dashboard do host e SDK para jogadores.
// Execução: npm install && npm start  (porta padrão 3000)
const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const { v4: uuidv4 } = require('uuid');

const app = express();
app.use(express.static('public'));

// Servir o SDK para ser importado pelo jogo (via <script type="module" src="/sdk.js">)
app.get('/sdk.js', (req, res) => {
  res.type('application/javascript').send(sdkContent);
});

const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// ---- Estado de jogo em memória ----
const games = {};
const DEFAULT_GAME = 'main';

function ensureGame(gameId = DEFAULT_GAME) {
  if (!games[gameId]) {
    games[gameId] = {
      clients: new Map(), // ws -> { playerId, role }
      players: {},        // playerId -> { name, team, ready, score, connected, lastSeen }
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

function sendTo(ws, obj) {
  if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
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

// ---- WebSocket ----
wss.on('connection', (ws) => {
  let currentGameId = DEFAULT_GAME;
  ensureGame(currentGameId);
  let boundPlayerId = null;
  let role = 'player'; // 'player' | 'host'

  function bindToPlayer(game, playerId, newRole) {
    // fecha conexões antigas desse player
    for (const [sock, meta] of game.clients.entries()) {
      if (meta.playerId === playerId && sock !== ws) {
        try { sock.close(); } catch {}
        game.clients.delete(sock);
      }
    }
    boundPlayerId = playerId;
    role = newRole || role;
    game.clients.set(ws, { playerId, role });
  }

  ws.on('message', (raw) => {
    let data;
    try { data = JSON.parse(raw.toString()); } catch (e) {
      sendTo(ws, { type: 'error', payload: { message: 'invalid json' } });
      return;
    }
    const { type, payload = {} } = data;

    if (type === 'join') {
      // payload: { playerId?, name?, team?, role?, gameId? }
      currentGameId = payload.gameId || DEFAULT_GAME;
      const game = ensureGame(currentGameId);
      let playerId = payload.playerId;
      const incomingRole = (payload.role === 'host') ? 'host' : 'player';
      const isResume = playerId && game.players[playerId];

      if (incomingRole === 'host' && !game.hostId) {
        // host inédito assume
        if (!playerId) playerId = uuidv4();
        if (!isResume) {
          game.players[playerId] = {
            name: payload.name || 'Host',
            team: 'attack', ready: false, score: 0, connected: true, lastSeen: Date.now()
          };
        } else {
          game.players[playerId].connected = true;
          game.players[playerId].lastSeen = Date.now();
        }
        game.hostId = playerId;
        bindToPlayer(game, playerId, 'host');
        sendTo(ws, { type: (isResume ? 'resumed' : 'joined'), payload: { playerId, gameId: currentGameId } });
        sendTo(ws, fullStatePayload(currentGameId));
        broadcastToGame(currentGameId, { type: 'host_update', payload: { hostId: game.hostId } });
        broadcastToGame(currentGameId, playersUpdatePayload(currentGameId));
        return;
      }

      if (isResume) {
        // Reconnect jogador
        const p = game.players[playerId];
        bindToPlayer(game, playerId, 'player');
        p.connected = true;
        p.lastSeen = Date.now();
        if (payload.name) p.name = payload.name;
        if (payload.team) p.team = payload.team === 'defense' ? 'defense' : 'attack';
        sendTo(ws, { type: 'resumed', payload: { playerId, gameId: currentGameId } });
        sendTo(ws, fullStatePayload(currentGameId));
        broadcastToGame(currentGameId, playersUpdatePayload(currentGameId));
        return;
      }

      // Novo jogador
      playerId = uuidv4();
      const name = payload.name || `Player-${playerId.slice(0,4)}`;
      const team = payload.team === 'defense' ? 'defense' : 'attack';
      bindToPlayer(game, playerId, 'player');
      game.players[playerId] = { name, team, ready: false, score: 0, connected: true, lastSeen: Date.now() };
      sendTo(ws, { type: 'joined', payload: { playerId, gameId: currentGameId } });
      sendTo(ws, fullStatePayload(currentGameId));
      broadcastToGame(currentGameId, playersUpdatePayload(currentGameId));
      return;
    }

    const game = ensureGame(currentGameId);
    if (!boundPlayerId || !game.players[boundPlayerId]) {
      sendTo(ws, { type: 'error', payload: { message: 'not joined' } });
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
      broadcastToGame(currentGameId, { type: 'score_broadcast', payload: { players: game.players, teamScores: computeTeamScores(game) } });
      return;
    }

    if (type === 'finish') {
      // jogador finalizou com score final explícito
      if (typeof payload.finalScore === 'number') me.score = payload.finalScore;
      me.ready = false;
      broadcastToGame(currentGameId, { type: 'player_finished', payload: { playerId: boundPlayerId, players: game.players, teamScores: computeTeamScores(game) } });
      return;
    }

    if (type === 'start_request') {
      // apenas host
      if (game.hostId !== boundPlayerId) {
        sendTo(ws, { type: 'error', payload: { message: 'apenas o host pode iniciar' } });
        return;
      }
      const connectedPlayers = Object.entries(game.players).filter(([pid,p]) => p.connected && pid !== game.hostId);
      const allReady = connectedPlayers.length >= 4 && connectedPlayers.every(([,p]) => p.ready);
      if (!allReady) {
        sendTo(ws, { type: 'error', payload: { message: 'mínimo 4 jogadores prontos (exclui host)' } });
        return;
      }
      game.started = true;
      broadcastToGame(currentGameId, { type: 'start', payload: { message: 'game started' } });
      return;
    }

    if (type === 'end_session') {
      if (game.hostId !== boundPlayerId) {
        sendTo(ws, { type: 'error', payload: { message: 'apenas o host pode encerrar' } });
        return;
      }
      broadcastToGame(currentGameId, { type: 'end_session', payload: { message: 'session ending' } });
      for (const pid in game.players) { game.players[pid].score = 0; game.players[pid].ready = false; }
      game.started = false;
      broadcastToGame(currentGameId, playersUpdatePayload(currentGameId));
      sendTo(ws, fullStatePayload(currentGameId));
      return;
    }

    if (type === 'host_transfer') {
      if (game.hostId !== boundPlayerId) {
        sendTo(ws, { type: 'error', payload: { message: 'apenas o host pode transferir' } });
        return;
      }
      const target = String(payload.targetPlayerId || '');
      if (!target || !game.players[target] || !game.players[target].connected) {
        sendTo(ws, { type: 'error', payload: { message: 'destinatário inválido ou offline' } });
        return;
      }
      game.hostId = target;
      broadcastToGame(currentGameId, { type: 'host_update', payload: { hostId: game.hostId } });
      return;
    }

    sendTo(ws, { type: 'error', payload: { message: 'unknown message type' } });
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

// ---- Conteúdo do SDK injetado via /sdk.js ----
const sdkContent = `
export class GameClient {
  constructor({ serverUrl, name, team = 'attack', role = 'player', gameId = 'main', autoReconnect = true }) {
    this.serverUrl = serverUrl;
    this.name = name;
    this.team = (team === 'defense' ? 'defense' : 'attack');
    this.role = role;
    this.gameId = gameId;
    this.autoReconnect = autoReconnect;
    this.playerId = localStorage.getItem('game.playerId') || null;
    this.ws = null;
    this.listeners = new Map();
    this._reconnectTimer = null;
    this.connect();
  }
  on(type, fn){ this.listeners.set(type, fn); return this; }
  _emit(type, payload){ const fn = this.listeners.get(type); if (fn) fn(payload); }
  connect(){
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return;
    this.ws = new WebSocket(this.serverUrl);
    this.ws.onopen = () => {
      this.ws.send(JSON.stringify({ type: 'join', payload: { playerId: this.playerId, name: this.name, team: this.team, role: this.role, gameId: this.gameId } }));
      this._emit('open');
    };
    this.ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === 'joined' || msg.type === 'resumed') {
        this.playerId = msg.payload.playerId;
        localStorage.setItem('game.playerId', this.playerId);
        this._emit('session', msg.payload);
      }
      if (msg.type === 'full_state') this._emit('state', msg.payload);
      if (msg.type === 'players_update' || msg.type === 'score_broadcast' || msg.type === 'player_finished') this._emit('update', msg.payload);
      if (msg.type === 'start') this._emit('start', msg.payload);
      if (msg.type === 'end_session') this._emit('end', msg.payload);
      if (msg.type === 'host_update') this._emit('host', msg.payload);
      if (msg.type === 'error' || msg.type === 'info') this._emit('message', msg.payload);
    };
    this.ws.onclose = () => {
      this._emit('close');
      if (this.autoReconnect && !this._reconnectTimer) {
        this._reconnectTimer = setTimeout(() => { this._reconnectTimer = null; this.connect(); }, 2000);
      }
    };
  }
  ready(){ this._send('ready', { ready: true }); }
  updateScore(delta){ this._send('score_update', { scoreDelta: delta }); }
  finish(finalScore){ this._send('finish', { finalScore }); }
  claimHost(){ this._send('claim_host', {}); }
  start(){ this._send('start_request', {}); }
  end(){ this._send('end_session', {}); }
  transferHost(targetPlayerId){ this._send('host_transfer', { targetPlayerId }); }
  leave(){ this._send('leave', {}); try{ this.ws && this.ws.close(); }catch(e){} }
  _send(type, payload){ if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return; this.ws.send(JSON.stringify({ type, payload })); }
}
`;
