# Marco 02 — Persistência e autorização

## Implementado na branch de trabalho
- Modelos SQLAlchemy para organizações, memberships, obras, serviços, medições e auditoria.
- Migração Alembic inicial (necessita execução e validação em PostgreSQL).
- Rotas de obras com filtro por membership e auditoria de criação.
- Segurança fail-closed: as rotas persistentes retornam 503 até integrar identidade autenticada e verificada.

## Ainda pendente
- Configuração OIDC e validação criptográfica de JWT (issuer, audience, JWKS, exp).
- Provisionamento seguro de organizações e memberships, com política de owner.
- Testes PostgreSQL e migrações up/down, concorrência e isolamento entre organizações.
- Aprovação de medições com regras de quantidade, revisões e evidências.
- Frontend autenticado e conexão às rotas persistentes.
- CI completo e revisão de segurança.

## Atenção
O endpoint /api/v1/demo/project permanece exclusivamente demonstrativo.
Não promover a produção antes da conclusão dos controles acima.
