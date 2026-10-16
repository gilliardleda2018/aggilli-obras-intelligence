# E02 — checkpoint de CI e próximos gates

Data: 2026-10-16. Branch: `fix/e02-fopag-import-safe`. PR #20 Draft.

## Evidência confirmada
- GitHub Actions run 38824162349: success no SHA `8c32f9f20a881fb8c18ca412fccbc3a3e2545c10`.
- Alteração backend: override de obra somente quando a falta de obra é o único bloqueio; outros erros continuam bloqueantes.
- Testes de regressão para override válido e valor inválido.
- Sem alterações no layout, OCR, modelos ou migrações. Sem deploy.

## Bloqueios ainda abertos
1. Verificação autenticada e somente leitura do banco de produção: organização, memberships, projetos, import_batches e despesas por source_ref.
2. A página /importar obtém projetos de getDataset(), que depende de quatro endpoints; uma falha de qualquer endpoint pode mascarar a origem do problema. Evitar alterar frontend/lib/data.ts sem coordenar com a outra frente.
3. Fluxo FOPAG deve diferenciar contratos, adiantamentos, programação e pagamentos efetivos. Não importar total contratado como despesa.
4. Não executar scripts de seed/import_tuntum --apply até reconciliação e autorização específica.

## Coordenação
A frente OCR permanece no PR #19. Antes de tocar arquivos compartilhados, registrar intenção no PR e verificar diffs atuais.

## Critério de conclusão E02
Reconhecimento de obras demonstrado em ambiente de teste, FOPAG estruturada sem duplicidade, testes de regressão e CI verde no SHA final, sem mudanças visuais. Até lá, PR Draft.
