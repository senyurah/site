# Host do jogo (LAN) — autoridade e reconexão

## Como rodar
1. **No host** (máquina central na LAN):
   ```bash
   cd jogo/host
   npm install
   npm start
   ```
   O servidor sobe em `http://<IP_DO_HOST>:3000`.

2. **Nos clientes** (4 PCs na mesma rede):
   - Abra no browser: `http://<IP_DO_HOST>:3000/client.html`.
   - Preencha **Nome**, **Time** (Ataque/Defesa) e, se for o host, selecione **Função = Host** na primeira conexão.

## Fluxo
- Clique **Conectar**.
- Cada jogador clica **Pronto**.
- **Apenas o host** consegue **Iniciar partida** e **Encerrar sessão**.
- Se o host cair, o sistema elege automaticamente um novo host (primeiro conectado) e todos são notificados.
- Se **um cliente cair**, ao reconectar ele volta com o **mesmo playerId** e recebe o **estado completo** (placares, quem é host, quem está pronto etc.).
- Se não houver host (sala recém-criada), qualquer jogador pode **Assumir Host**.
- O host pode **Transferir Host** para outro jogador **online**.

## Observações
- O início requer **mínimo de 4 jogadores conectados** e **todos conectados precisam estar prontos**.
- `end_session` limpa os placares e marca todos como **não prontos**.
- Todos os dados são mantidos **apenas em memória**.

## Dicas de rede
- Em laboratório fechado, basta liberar a porta `3000` no host.
- Se quiser mudar a porta: `PORT=8080 npm start`.
