# Jogo LAN — Auto-conexão do app + Dashboard do Host

## Pastas
- `host/` — servidor + dashboard do host (`/host.html`) + endpoint do SDK (`/sdk.js`)
- `sdk/` — documentação do SDK
- `examples/` — exemplo mínimo de integração web

## Como rodar (host)
```bash
cd host
npm install
npm start
```
- Acesse `http://<IP_DO_HOST>:3000/host.html` para abrir o **Dashboard do Host**.
- No jogo dos jogadores, importe o SDK do host: `http://<IP_DO_HOST>:3000/sdk.js` e conecte via `ws://<IP_DO_HOST>:3000`.

## Notas importantes sobre auto-conexão
- Navegadores **não conseguem** descobrir IPs via UDP/mDNS; portanto, defina o `serverUrl` fixo no app (build-time ou config).
- Para jogos **nativos** (Unity/Electron), dá para implementar descoberta (mDNS/Bonjour). Posso fornecer módulo extra se necessário.
