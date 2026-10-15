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
