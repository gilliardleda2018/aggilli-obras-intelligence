# Coordenação entre frentes — Aggilli Obras Intelligence

Atualizado: 2026-10-16. Este documento é um protocolo de comunicação assíncrona entre instâncias ChatGPT trabalhando simultaneamente no repositório.

## Responsabilidades

- **Frente E02 / PR #20** — importação de planilhas, identificação de obras, validação de linhas, FOPAG e integridade financeira. Branch `fix/e02-fopag-import-safe`.
- **Frente OCR / PR #19** — extração de documentos, provedores OCR/IA e seus testes. Branch `fix/ocr-integration-safe`.

## Limites de alteração

E02: `backend/app/imports.py`, `backend/app/spreadsheet.py`, `backend/tests/test_imports.py` e documentação própria. Qualquer alteração em arquivos adicionais exige registrar justificativa e verificar conflitos antes de editar.

OCR: arquivos de OCR e testes específicos sob responsabilidade da outra frente. E02 não altera `backend/app/ocr.py`, documentos/OCR, dependências de provedores ou configurações do OCR.

Arquivos compartilhados (por exemplo `backend/app/main.py`, `backend/app/models.py`, `frontend/lib/data.ts`, `frontend/components/importer.tsx`, workflows e migrações) exigem aviso prévio por documento/PR e revisão dos diffs das duas branches. Não sobrescrever mudanças alheias.

## Situação E02

Base inicial `main` SHA `599bc2800ff665d9db0006c6588dedc7c83b2195`. PR #20 Draft. Implementado: correção do commit para aceitar escolha manual de obra autorizada quando o único bloqueio é obra não identificada; testes de regressão. Ainda pendentes: seletor vazio, contexto de organização, FOPAG específica, verificação read-only do PostgreSQL e homologação. CI ainda não declarado aprovado. Não houve merge/deploy.

## Situação OCR

PR #19 Draft, de outra instância ChatGPT. A frente E02 não revisa nem incorpora alterações de OCR automaticamente. Consultar o PR #19 para estado atualizado; não inferir homologação ou aprovação.

## Protocolo de handoff

1. Antes de editar, comparar `main`, PR #19 e PR #20 e conferir arquivos em comum.
2. Publicar no respectivo PR: escopo, SHA, arquivos tocados, testes executados, evidências, riscos e pendências.
3. Para mudanças compartilhadas, avisar no PR e aguardar alinhamento explícito; evitar cherry-pick ou merge cruzado não solicitado.
4. Cada frente executa seus testes e revisa regressões dos módulos vizinhos.
5. Nenhum merge, migração ou deploy em produção sem gates e autorização.
6. Ao encerrar cada entrega, atualizar este documento na branch correspondente ou registrar comentário com link ao checkpoint.

## Mensagem à frente OCR

A frente E02 está ativa no PR #20 e cuida exclusivamente do importador de planilhas/FOPAG. Não modificaremos arquivos do OCR. Pedimos que a frente OCR preserve os contratos de importação e nos avise antes de editar arquivos compartilhados. O PR #20 permanece Draft e não deve ser incorporado como dependência do PR #19.
