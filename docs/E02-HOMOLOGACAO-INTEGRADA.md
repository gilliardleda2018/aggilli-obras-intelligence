# E02 — Homologação integrada de importação (checkpoint)

Data: 2026-10-16. Branch: `fix/e02-fopag-import-safe`; PR #20 Draft. Frente OCR: PR #19 independente.

## Matriz de homologação

| Gate | Evidência / procedimento | Estado |
|---|---|---|
| Backend e migrações em PostgreSQL descartável | CI GitHub Actions, upgrade/downgrade/upgrade e pytest | Reexecutar no SHA final |
| Frontend | CI lint e build | Reexecutar no SHA final |
| Usuário com uma organização | Hidden organization_id, API valida membership | Código implementado; E2E pendente |
| Usuário com múltiplas organizações | Seletor obrigatório; backend exige organização explícita | Código e teste backend; E2E pendente |
| Lista de obras | GET /projects, project.organization_id, filtro por organização | Código implementado; E2E pendente |
| Override de obra | Commit só recupera falta de obra; outros erros bloqueiam | Testes backend |
| Isolamento multiempresa | Não aceitar obra/organização de outra empresa | Testes backend adicionados |
| Idempotência | source_ref por hash de arquivo e linha, impedir repetição | Teste existente |
| FOPAG contratos/adiantamentos | Não lançar contrato como despesa nem marcar programação como PAID | **Pendente: não usar importador genérico para folha contratual** |
| Dados reais em produção | SELECT-only: memberships, projects, import_batches, expenses/source_ref | **Pendente: acesso autenticado read-only** |
| OCR | PR #19 independente, sem alteração | Preservado por isolamento |

## Política de aceite
Não realizar merge, deploy, seed, `--apply`, ou importação financeira real enquanto os gates E2E, reconciliação FOPAG e verificação de dados não estiverem concluídos. Não confundir CI verde com homologação operacional. Layout original deve ser mantido; único controle adicional é o seletor de organização para multiempresa.

## Verificação read-only de produção
Executar somente com credencial de consulta e sem exibir dados pessoais: conferir contagem de organizações, memberships do sujeito autenticado, obras por organization_id, lotes de importação por organização e source_refs existentes. Não acessar segredos, nem efetuar qualquer alteração. Documentar contagens e identificadores minimizados.

## Coordenação
Se PR #19 alterar arquivos compartilhados, comparar diffs antes de integrar. Nunca fazer merge cruzado automático.
