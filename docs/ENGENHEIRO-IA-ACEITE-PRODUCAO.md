# Engenheiro IA — aceite operacional de produção

## Identificação
- Versão: advisory 1.0
- Merge e SHA implantado: `6e27d99ceccb787c8ea9bb559382959c95576c3b`
- Deploy: GitHub Actions run `38967185310`, sucesso.
- CI e Guardian Integrity: aprovados no SHA.
- Escopo: recomendações técnicas consultivas por obra; sem execução autônoma.

## Evidência operacional AWS (16/10/2026)
- Cluster ECS: `obras`; API e web com rollout COMPLETED, 1/1.
- Tarefa de auditoria read-only: `6c6af6051e0e4d4891d13081093e81bf` — exit code 0.
- CloudWatch `/obras/api` stream `api/api/6c6af6051e0e4d4891d13081093e81bf`.
- OWNER ativo reconhecido; 14 projetos físicos autorizados avaliados.
- 28 findings, dois por obra: `COST_INPUTS_MISSING` e `SCHEDULE_INPUTS_MISSING`.
- Histórico `ForecastRun` com contagem idêntica antes e depois; transação rollback; sem alteração de dados financeiros.
- O agente não inferiu avanço físico nem previsão de prazo/custo quando faltaram medições e planejamento.

## Evidências de testes
- `backend/tests/test_engineering_advisor.py`: dados insuficientes, risco de prazo/custo e ausência de falsa precisão.
- `backend/tests/test_forecast.py`: acesso por organização, resposta do endpoint e ausência de escrita no histórico.
- Frontend compilado no CI, painel incluído na página autenticada da obra.

## Critérios e estado
| Critério | Resultado |
|---|---|
| Código, testes e merge | APROVADO |
| Deploy, ECS, motor com dados reais | APROVADO |
| Sem escrita no histórico ou finanças | APROVADO |
| Isolamento entre organizações em testes | APROVADO |
| Requisição HTTP com token de usuário real em produção | NÃO EXECUTADA |
| Renderização E2E no navegador autenticado | NÃO EXECUTADA |

## Restrições
Não declarar homologação E2E concluída. A API e o painel estão publicados, mas o aceite visual autenticado continua pendente. Não usar sessão, token ou credenciais de usuário em logs. Não desproteger rotas para validar o frontend.

## Continuidade
O próximo agente pode iniciar desenvolvimento em branch isolada, sem tocar no Engenheiro IA. Antes de qualquer anúncio de homologação E2E, obter evidência de resposta HTTP autenticada e captura do fluxo visual por operador autorizado. Preservar os dados reais da FOPAG e as divergências financeiras.
