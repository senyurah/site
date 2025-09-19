# SDK do Jogador — Integração no seu app

### Como usar (browser / jogo web)
1) Suba o host (veja `host/`).
2) No seu jogo, importe o SDK do servidor (ele é servido em `/sdk.js` pelo host):
```html
<script type="module">
  import { GameClient } from 'http://<IP_DO_HOST>:3000/sdk.js';
  const gc = new GameClient({ serverUrl: 'ws://<IP_DO_HOST>:3000', name: 'Alice', team: 'attack' });
  gc.on('state', (s)=> console.log('estado', s));
</script>
```
3) Quando o jogador clicar **Pronto** dentro do seu jogo, chame:
```js
gc.ready();
```
4) Para atualizar pontuação enquanto joga (opcional):
```js
gc.updateScore(+10); // ou -5 etc.
```
5) Quando o jogador **finalizar** sua partida/nível, envie o placar final:
```js
gc.finish(finalScoreNumber);
```
> O host verá tudo em tempo real no dashboard (`/host.html`).

### Eventos úteis
- `state` — estado completo (players, placar por equipe, quem é host, se começou etc.).
- `update` — mudanças incrementais (scores/players).
- `start` — host iniciou a partida.
- `end` — host encerrou a sessão.

### Auto-conexão
Configure `serverUrl` fixo no build do jogo (ex.: variável de ambiente no build). Em ambiente de navegador **não é viável** fazer descoberta automática de IP por UDP/mDNS. Se o seu app for **nativo (Electron, Unity, etc.)**, podemos implementar descoberta via mDNS/Bonjour.
