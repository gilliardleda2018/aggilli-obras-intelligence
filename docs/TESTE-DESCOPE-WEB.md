# Homologação do Descope fora do Runner

A rota `/login` renderiza o fluxo oficial do projeto Aggilli Obras Intelligence com o SDK Next.js.

## Execução
1. Instalar dependências do frontend.
2. Configurar NEXT_PUBLIC_DESCOPE_PROJECT_ID no ambiente.
3. Iniciar `npm run dev` e acessar `http://localhost:3000/login`.
4. Testar Magic Link no mesmo navegador e confirmar o evento de sucesso.
5. Testar Passkey e Google separadamente; não compartilhar tokens ou URLs de autenticação.

## Segurança
A tela é somente um teste de autenticação. Não concede acesso às obras.
A API exige token JWT validado e membership. O fluxo SDK e o fluxo OIDC customizado existente não devem ser considerados intercambiáveis sem homologação de sessão, cookies, CSRF, logout e expiração.
Não utilizar o callback do SDK como prova de autorização financeira ou acesso a dados.
