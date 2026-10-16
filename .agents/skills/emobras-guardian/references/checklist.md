# Checklist operacional — Em Obras Guardian

## Antes de alterar
- [ ] Pedido, escopo, autorização e exclusões compreendidos
- [ ] SHA main e PRs paralelos conferidos
- [ ] Arquivos compartilhados e possíveis conflitos mapeados
- [ ] Causa raiz apoiada por evidência, não hipótese
- [ ] Plano de rollback e critérios de aceite definidos

## Segurança e testes
- [ ] Sem segredo, credencial ou PII em logs/commits
- [ ] Autorização no servidor por organização/obra/ação
- [ ] Testes de sucesso, falha, duplicidade e isolamento
- [ ] Financeiro: Decimal, idempotência, comprovante, transições de estado
- [ ] Mapas: key browser/server separadas, API restrictions, renderização e Street View
- [ ] Backend CI e frontend lint/build no SHA final
- [ ] Migrações PostgreSQL testadas se houver mudanças de schema
- [ ] Layout e módulos vizinhos sem regressão

## Produção
- [ ] Aprovação de deploy e gates confirmados
- [ ] SHA da main e workflow final verificados
- [ ] ECS/API/web estabilizados, não só CI verde
- [ ] Teste autenticado quando necessário
- [ ] Evidência do comportamento funcional (não apenas RUNNING)
- [ ] Checkpoint e pendências atualizados
