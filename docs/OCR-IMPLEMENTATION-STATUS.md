# OCR — Estado de implementação e controles de regressão

Atualizado em 2026-10-16. Escopo exclusivo do PR #19 `fix/ocr-integration-safe`.

## Fonte de verdade
- Repositório: `gilliardleda2018/aggilli-obras-intelligence`.
- Base inicial da branch: `599bc2800ff665d9db0006c6588dedc7c83b2195`.
- Commits de proteção OCR: `3b2c747c4d6e28e4e1b3093ec0336b4455012385`, `6326433bd79ffb1fc30e69831851643ac28fb71c`, `2d6ef064dd6c1645d2d3ccda01f35104cf39428a`.
- Evidência de CI no último commit antes desta documentação: [38819969824](https://github.com/gilliardleda2018/aggilli-obras-intelligence/actions/runs/38819969824) e [38819973995](https://github.com/gilliardleda2018/aggilli-obras-intelligence/actions/runs/38819973995), ambos success.

## Escopo imutável
Não modificar CSS, componentes visuais, páginas, rotas externas, contratos de API, tabelas/migrações, finanças, licenciamento, GPS ou regras de confirmação de despesas. Não fazer merge/deploy sem homologação e aprovação explícita.

## Confirmado
1. A captura existente envia imagens, mantém documentos pendentes e exige confirmação humana para gerar despesa.
2. O backend contém leitura com Claude, validação de chave NF-e e segunda leitura em caso de inconsistência.
3. Os testes de documentos usam mocks; não comprovam invocação real dos modelos.
4. A definição ECS `obras-api:2`, consultada em `us-east-1`, apresenta `DOC_AI_PROVIDER=off` e `ANTHROPIC_AWS_WORKSPACE_ID` vazio; os serviços web e api estavam com 1/1 tarefas em execução.
5. O PR #19 adiciona testes e tratamento defensivo de SDK ausente e itens de leitura inesperados; CI verde no SHA anterior à documentação.

## Não comprovado
- Existência, configuração e autorização de workspace Claude Platform on AWS para esta aplicação.
- Disponibilidade dos identificadores de modelos e compatibilidade exata do SDK em produção.
- OCR real em ambiente isolado com documento sintético.
- Homologação E2E autenticada e observabilidade de falhas de OCR em produção.

## Critérios obrigatórios de aceite
1. CI verde no SHA final (backend, frontend e migrações).
2. Testes sem rede para leitura, erro de SDK, erros de provedor, dados inválidos, escalonamento e confirmação humana.
3. Prova real em ambiente de homologação com documento sintético, sem lançamento financeiro.
4. Nenhum diff de layout, componentes ou rotas; nenhuma migração.
5. Configuração e permissões AWS verificadas sem revelar segredos.
6. Plano de reversão e aprovação explícita antes de ativar o provedor.

## Próxima ação
Inspecionar apenas configuração IAM/workspace do OCR por métodos autorizados. Se houver bloqueio de ferramenta, registrar a limitação sem presumir o estado. Não habilitar `DOC_AI_PROVIDER` até concluir prova real e revisão de segurança.

## Atualização — 2026-10-16: bloqueios de configuração e CI
- Commit `b844fa926a2c43140dfabe8b1af43ee06b7cae4e`: falha segura para workspace AWS vazio ou chave da API Anthropic ausente.
- Commit `c4336e18234b6b7f5903a52e260d5fdd208becc2`: testes de regressão para os dois cenários.
- CI do commit `c4336e18234b6b7f5903a52e260d5fdd208becc2` confirmado como `success` em [38820331499](https://github.com/gilliardleda2018/aggilli-obras-intelligence/actions/runs/38820331499) e [38820337666](https://github.com/gilliardleda2018/aggilli-obras-intelligence/actions/runs/38820337666).
- A verificação de presença de variável **não** prova permissão IAM, existência de workspace ou compatibilidade do modelo.
- Sem leitura real de documento, sem ativação AWS, sem alterações de layout, migrações ou financeiro.
