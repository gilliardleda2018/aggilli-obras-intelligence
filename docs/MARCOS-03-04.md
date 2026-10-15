# Marcos 03 e 04 — Materiais, financeiro e campo

## Implementação inicial
- Catálogo de materiais por obra e movimentação IN/OUT com saldo não negativo.
- Lançamentos de custos e resumo de orçamento, gasto e saldo.
- Acesso por membership e auditoria de operações.

## Não homologado
- Testes PostgreSQL de concorrência e rollback para estoque.
- Integração de fornecedores, compras, contratos, anexos e notas fiscais.
- Diário de obra, inspeções, evidências fotográficas e assinatura.
- Regras de estorno contábil, conciliação e classificação de custos.
- UX operacional completa.

## Regras de segurança
- Nenhuma escrita pública ou sem identidade autenticada.
- Sem configuração OIDC, todas as rotas persistentes falham fechadas.
- Não publicar em produção até testes, revisão de autorização e infraestrutura.
