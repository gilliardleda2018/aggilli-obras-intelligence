# Engenheiro IA — contrato de primeira capacidade

Status: desenvolvimento em branch, **não publicado**.

## Objetivo
Agente consultivo para engenheiros e gestores, sobre medições aprovadas, prazo e orçamento. Não é um LLM nem um processo autônomo. A primeira entrega implementa a camada de recomendações determinísticas, com evidências verificáveis.

## API
`GET /api/v1/projects/{project_id}/engineering-advice` exige autenticação e autorização por obra. Retorna `agent`, `version`, `mode=advisory`, `project_id`, `evaluated_on`, `findings` e `writes_performed=false`.

Cada finding inclui `code`, `severity`, `message`, `recommended_action` e `evidence`. Os códigos iniciais são:
- `SCHEDULE_INPUTS_MISSING`, `PRODUCTIVITY_INSUFFICIENT`;
- `DEADLINE_RISK`, `CRITICAL_SERVICE`;
- `COST_INPUTS_MISSING`, `COST_OVERRUN_RISK`;
- `NO_ACTIONABLE_RISK`.

## Regras de integridade
- Usar apenas medições aprovadas e despesas efetivamente registradas.
- Nunca derivar avanço físico de pagamentos ou de relatos textuais.
- Não inferir prazo ou orçamento se a fonte não suportar.
- Não gravar histórico, pagamentos, contratos, medições ou previsões por esta rota.
- Acesso a obra de outra organização deve resultar em 404.
- A avaliação deve ser reproduzível para o mesmo conjunto de dados e data.
- As recomendações não substituem a responsabilidade técnica do engenheiro.

## Homologação necessária antes de produção
1. Testes unitários para dados insuficientes, risco e ausência de falsa precisão.
2. Teste integrado de autenticação e isolamento entre organizações.
3. Confirmação de ausência de gravação em `ForecastRun`.
4. Testes de regressão da API, mapas, financeiro, OCR e login.
5. Interface de apresentação das recomendações com estados de erro e sem dados.
6. CI, deploy e verificação autenticada na AWS.
7. Manual de uso e evidência funcional.

A primeira branch implementa a API e os testes iniciais; não é a entrega completa do agente.
