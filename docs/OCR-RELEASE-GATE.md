# OCR — Gate final da etapa 4/4 (2026-10-16)

## Identificação
- PR #19 (Draft): https://github.com/gilliardleda2018/aggilli-obras-intelligence/pull/19
- Branch: `fix/ocr-integration-safe`
- Base auditada: `599bc2800ff665d9db0006c6588dedc7c83b2195`
- Último SHA antes deste relatório: `e18e2b52102dcb719ca0c71a42f09106871c0cdf`
- Outra frente: PR #20, importação FOPAG; nenhum arquivo em comum na inspeção anterior.

## Escopo verificado
Arquivos do PR #19 antes deste relatório: `backend/app/ocr.py`, `backend/tests/test_ocr_regression.py`, `docs/OCR-IMPLEMENTATION-STATUS.md`, `docs/OCR-WORKFLOW-4-ETAPAS.md`. Nenhuma alteração de frontend, CSS, modelos, migrações, rotas, financeiro ou infraestrutura.

## Evidência
- CI do SHA `d21de351f5f4992c7686f29e75e584bff7d3ed34`: success em runs 38822089792 e 38822093579.
- CI do SHA `e18e2b52102dcb719ca0c71a42f09106871c0cdf`: ainda em andamento no instante desta verificação (runs 38822285610 e 38822291990); **não declarar verde antes de verificar**.
- Testes do OCR são mockados; não demonstram uma leitura com Claude real.
- ECS `obras-api:2`: `DOC_AI_PROVIDER=off`, `ANTHROPIC_AWS_WORKSPACE_ID` vazio.
- IAM task role contém `aws-external-anthropic:*` em `*`, sem prova de workspace ou de autorização efetiva para o modelo.

## Decisão
**BLOQUEADO PARA ATIVAÇÃO EM PRODUÇÃO.** Código defensivo e documentação são candidatos a revisão/merge separado, mas a integração OCR real ainda não está homologada. Manter PR em Draft até CI do SHA final e revisão.

## Gates para liberar
1. Confirmar workspace e modelo autorizados; verificar SDK real e permissões mínimas.
2. Prova real de leitura de documento sintético em homologação, sem despesas e sem dados de cliente.
3. CI do SHA final verde, revisão do diff e validação de não regressão.
4. Aprovação explícita de ativação e plano de rollback.

## Plano de reversão
- Não modificar produção antes dos gates. Se ocorrer falha após eventual ativação autorizada, restaurar `DOC_AI_PROVIDER=off` via revisão controlada da definição ECS, com atualização do serviço e verificação de estabilidade.
- Se o PR introduzir regressão, reverter apenas os commits do PR #19, preservando alterações de outras frentes; não usar reset/force-push na `main`.
- Documentos existentes permanecem sob o fluxo de conferência humana; não executar operações de escrita financeira como parte do teste.

## Coordenação entre instâncias
A outra instância deve considerar os arquivos OCR como de propriedade desta frente até a conclusão do PR #19. Não sobrescrever alterações de outras frentes e comunicar mudanças compartilhadas por PR ou documentação.

## Revisão pré-deploy — 2026-10-16
- `main` atual: `21cc7240c1524f73085d4ba104d4baf2d43c9cee`; branch OCR divergiu (30 commits à frente e 23 atrás), merge-base `599bc2800ff665d9db0006c6588dedc7c83b2195`.
- Comparação `main...fix/ocr-integration-safe` altera exclusivamente `backend/app/ocr.py`, testes OCR e documentação OCR.
- CI do commit `f91a0e15f946fdd4b521723f75d5abe3e223a0dd` success em 38882514235 e 38882519908.
- Workflow `.github/workflows/deploy.yml` executa build/push de **API e web**, migrações Alembic e reinicialização dos dois serviços. **Não** disparar workflow completo para ativar somente OCR sem plano de isolamento.
- Gate adicional: reconciliar a branch com a `main` atual, sem sobrescrever trabalho das outras frentes; CI final após reconciliação; deploy backend-only com artefato imutável, validação de health e rollback, e ativação `DOC_AI_PROVIDER=textract` separadamente.
- Enquanto esse gate estiver aberto: PR Draft, sem merge e sem deploy.
