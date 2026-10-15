# Fechamento operacional — cinco requisitos

## Implementado
- Obras, serviços, quantitativos, registro e aprovação de medições.
- Cálculo de avanço físico por serviço, ponderado pelos pesos cadastrados.
- Materiais e movimentações de estoque.
- Despesas com categoria, fornecedor, referência a comprovante e vínculo à obra.
- Programação de pagamentos e confirmação com referência auditada.
- PostgreSQL via SQLAlchemy e migrations Alembic 0001–0004.
- OIDC JWT/JWKS no backend, com controle de membership por organização.
- Testes de autorização, saldos e concorrência.

## Pendente para considerar completo
- Fluxo de criação e homologação de organizações/memberships com identidades Descope reais.
- Formulários frontend persistentes e sessão Descope/OIDC ponta a ponta homologada.
- Upload privado real de comprovantes para S3, antivírus, autorização de leitura e retenção.
- Histórico de estornos, aprovações, rateio entre obras e reconciliação bancária.
- Migração de dados reais de Tuntum para PostgreSQL, com reconciliação manual de divergências.
- Testes E2E de Darlan e Denise, incluindo papéis e separação de funções.
- Validar CI do SHA final, testes de migração PostgreSQL e segurança.
- Deploy de homologação; não publicar em produção antes da conclusão desses gates.

## Regras
A FOPAG representa programação e não quitação. Pagamento confirmado requer referência verificável e trilha de auditoria. O avanço físico não deriva de despesas.
