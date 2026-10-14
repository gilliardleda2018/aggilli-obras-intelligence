# Integração de identidade — requisitos operacionais

Backend valida JWT assimétrico RS256 usando OIDC_ISSUER, OIDC_AUDIENCE e OIDC_JWKS_URL.
O issuer deve ser um domínio HTTPS sob controle do provedor de identidade. Não aceitar token arbitrário do frontend.
O provisionamento de memberships deve ocorrer em fluxo administrativo autorizado; nunca permitir autoatribuição OWNER por header ou payload.
O frontend atual mantém páginas persistentes bloqueadas até existir uma sessão individual autenticada com cookies HttpOnly/Secure/SameSite e fluxo de callback PKCE.
Não armazenar access tokens em localStorage e não usar DASHBOARD_SERVICE_TOKEN compartilhado.
Para ativação: registrar cliente OIDC, configurar redirect URI, secrets por ambiente, logout, renovação e testes E2E.
