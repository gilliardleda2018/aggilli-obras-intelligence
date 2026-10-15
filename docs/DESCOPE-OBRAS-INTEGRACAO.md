# Integração Descope — Aggilli Obras

## Estado verificado
A conexão Descope atual aponta para o projeto Personal Assistant - DAI NonProd.
Não reutilizar ou alterar suas configurações para a plataforma de obras.

## Provisionamento necessário
- Projeto Descope dedicado a Aggilli Obras (preferencialmente nonprod primeiro).
- Aplicação OIDC confidencial com Authorization Code + PKCE.
- Redirect URI exata do frontend: `https://<host>/api/auth/callback`.
- Configurar no backend: OIDC_ISSUER, OIDC_AUDIENCE, OIDC_JWKS_URL.
- Configurar no frontend: OIDC_ISSUER, OIDC_CLIENT_ID, OIDC_CLIENT_SECRET, OIDC_REDIRECT_URI, SESSION_ENCRYPTION_KEY.
- Manter segredos em gerenciador seguro; nunca em git.
- Criar memberships no banco por fluxo administrativo autenticado e auditado.

## Gate antes de produção
- Validar endpoint authorization/token e discovery do provedor.
- Testar login, callback, expiração, logout e revogação de sessão.
- Garantir que cookies não sejam usados como prova de autorização sem verificação de JWT no backend.
- Testar duas organizações e perfis OWNER, ENGINEER e VIEWER.
- Corrigir o logout para revogação real no provedor e implementar proteção CSRF para operações futuras.
- Executar E2E no ambiente de homologação e registrar evidências.

Não compartilhar projeto, client secret, chaves de sessão ou dados com Personal Assistant.
