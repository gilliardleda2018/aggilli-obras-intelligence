# Gates de produção — evidências mínimas

| Gate | Critério | Evidência |
|---|---|---|
| P0 | Escopo e autorização identificados | pedido/PR |
| P1 | Baseline e PRs paralelos verificados | SHA e PRs |
| P2 | CI e regressões do SHA final verdes | workflow |
| P3 | Migrações compatíveis e backup quando há escrita de dados | plano + snapshot disponível |
| P4 | Publicação do SHA desejado concluída | GitHub Actions + ECS |
| P5 | API e frontend respondem corretamente | health + rota autenticada |
| P6 | Dados/fluxos reais verificados sem inventar resultados | consulta, teste E2E ou validação |
| P7 | Handoff e rollback registrados | checkpoint |

## Finanças
- Separar `SCHEDULED` de `PAID`.
- Nunca usar valor de planilha como prova de pagamento.
- Fonte `backend/data/tuntum_2026-08-28.json` preservada; conferir `docs/FOPAG-CONTRATO-FIDELIDADE-FONTE.md`.
- Importação idempotente e transacional; comparar contagens antes/depois; preservar divergências e não recalcular saldos declarados.
- Confirmar organização e papel do usuário com consulta somente leitura; nunca conceder OWNER automaticamente como parte de auditoria.
- Backups não substituem validação transacional; não restaurar produção sem plano aprovado.

## Segurança
- Sem sessão: rotas operacionais devem redirecionar para login; endpoints de dados devem exigir autenticação no servidor.
- Testar sessão válida, expirada e sem vínculo de organização.
- Nunca publicar dados reais em página de referência anônima.
- Segredos: nomes/ARNs podem ser usados para identificar recursos, nunca valores em logs ou commits.

## Status
Use exatamente: `PREPARADO`, `TESTADO`, `INTEGRADO`, `PUBLICADO`, `VALIDADO_FUNCIONALMENTE` ou `BLOQUEADO`. Cada avanço requer evidência independente; não confundir contagem no banco com tela homologada.
