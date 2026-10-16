# Financeiro IA — aceite operacional (16/10/2026)

## Versão
- Commit implantado: `1afc8f3a82b3008be758ca5c52ef08e3ab91234e`.
- GitHub Actions deploy `38971896703`: sucesso.
- CI backend/frontend e Guardian Integrity: sucesso no mesmo SHA.
- ECS `obras-api` e `obras-web`: 1/1, rollout COMPLETED.

## Evidência de dados reais
- Auditoria ECS read-only: `78ae780fc7b041dd908f2dffab363b95`, exit code 0.
- CloudWatch: `/obras/api`, stream `api/api/78ae780fc7b041dd908f2dffab363b95`.
- OWNER ativo: confirmado; 15 projetos acessíveis.
- 19 findings: 2 `CONTRACT_BALANCE_DIVERGENCE`, 16 `SCHEDULED_OVERDUE`, 1 `CONTRACT_VALUES_MISSING`.
- `writes_performed=false`; sessão em `SET TRANSACTION READ ONLY` e rollback.
- Pagamentos vencidos permanecem `SCHEDULED`, sem prova de liquidação.
- Quatro divergências documentais da FOPAG não são equivalentes aos dois alertas contratuais calculados: totais agregados requerem conciliação separada.

## Limites do aceite
| Gate | Estado |
|---|---|
| Implementação, testes sintéticos e integração | APROVADO |
| CI, deploy e estabilidade ECS | APROVADO |
| Execução de diagnóstico com dados reais, somente leitura | APROVADO |
| HTTP autenticado com sessão real | PENDENTE |
| Interface E2E no navegador | PENDENTE |
| Conciliação documental das diferenças agregadas | PENDENTE (fora do escopo consultivo) |

A publicação e o motor foram homologados; **não declarar E2E visual concluído**. A API não pode ser desprotegida para testar a interface. O agente não executa pagamentos nem altera registros.
