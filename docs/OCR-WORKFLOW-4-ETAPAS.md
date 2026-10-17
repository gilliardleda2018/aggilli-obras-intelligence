# Workflow de homologação OCR — quatro etapas e quatro checkpoints

Data: 2026-10-16. PR #19, branch `fix/ocr-integration-safe`.
**Autorização do usuário:** iniciar investigação e homologação em quatro etapas, mantendo escopo exclusivo do OCR, sem layout, regressões, merge ou deploy prematuro.

## Invariantes
- Alterar somente motor OCR, testes OCR e documentação OCR. Configuração de ambiente somente após evidência e aprovação específica de mudança.
- Nunca modificar CSS, frontend, navegação, contratos de API, banco/migrações, financeiro, licenciamento ou GPS.
- Nenhum documento real de cliente, dado sensível ou segredo em logs, PRs ou respostas.
- Não ativar OCR em produção, não executar inferência paga nem registrar despesas sem comprovação e autorização específica.
- Registrar SHA, CI, diferenças de arquivos, evidências e bloqueios a cada etapa.
- Caso AWS/integração não possa ser consultada, registrar bloqueio e seguir somente em verificações locais/estáticas; não inventar conclusão.
- Cada etapa termina com um checkpoint comunicável ao usuário.

## Etapa 1 — Baseline, segurança e documentação
1. Fixar SHA de base, SHA da branch e escopo do PR.
2. Verificar CI no último SHA; conferir diff para ausência de mudanças proibidas.
3. Documentar arquitetura e fluxos OCR atuais e bloqueios comprovados.
**Saída:** baseline auditável, CI e plano de rollback (não incorporar PR).

## Etapa 2 — AWS e compatibilidade do SDK (somente leitura)
1. Inspecionar definições ECS e variáveis *não secretas* do serviço OCR.
2. Verificar se workspace, IAM, região, permissões e modelos estão efetivamente habilitados, usando somente ferramentas autorizadas.
3. Verificar SDK e assinatura dos métodos usados pelo código, sem supor que CI mockado prova integração.
**Saída:** matriz `comprovado / pendente / bloqueado`, sem alterar produção.

## Etapa 3 — Teste de OCR isolado
1. Exercitar leitura de documento inteiramente sintético em ambiente separado, somente se provedor, permissão e custo estiverem autorizados e disponíveis.
2. Validar fornecedor, data, valor, chave fiscal, confiança, inconsistências e fallback.
3. Não enviar dados de clientes, não gravar despesas e não modificar produção.
**Saída:** evidências de leitura real, ou bloqueio explícito se execução real não for possível.

## Etapa 4 — Gate final e plano de ativação
1. Executar/verificar CI do SHA final e diff de escopo.
2. Revisar comportamento de erro, rollback e observabilidade.
3. Publicar relatório final com o que foi e não foi demonstrado.
4. Deixar PR em Draft se faltar qualquer gate. Não fazer merge/deploy nem ativar `DOC_AI_PROVIDER` sem autorização de publicação e homologação real.
**Saída:** decisão `pronto para homologação / bloqueado / pronto para solicitar deploy`, com evidências.

## Referências
- `backend/app/ocr.py`, `backend/app/documents.py`, `backend/tests/test_documents.py`, `backend/tests/test_ocr_regression.py`
- `docs/OCR-DOCUMENTOS.md`, `docs/OCR-IMPLEMENTATION-STATUS.md`
- PR: https://github.com/gilliardleda2018/aggilli-obras-intelligence/pull/19
