# P0 — Painel com dados do PostgreSQL

## Situação (15/10/2026)
| Item | Estado |
|---|---|
| Carteira, FOPAG semanal, contratos, obrigações e atividades lidos da API | Implementado e testado |
| Edição dos dados da obra (situação, responsável, orçamento, prazos, coordenadas) | Implementado e testado |
| Importação idempotente da FOPAG 28/08/2026 (`backend/scripts/import_tuntum.py`) | Implementado e testado; **não aplicada em ambiente real** |
| Identidade de desenvolvimento (`backend/scripts/dev_identity.py`) | Implementada, somente local |
| Login real (Descope dedicado) | **Pendente:** depende do projeto Descope das Obras |
| Homologação com usuários reais | Pendente |

Sem sessão, o painel mostra a importação de referência com o selo "Importação de referência". Com sessão, tudo vem do banco e o selo
fica "Banco de dados". Nenhum indicador da sessão autenticada usa valores fixos no código.

## Regras de modelagem
- A linha da FOPAG vira uma despesa mais um pagamento **programado**. Nada é marcado como pago sem comprovante.
- A dívida relatada de fornecedor vira uma única despesa em aberto. O valor da FOPAG para esse fornecedor vira pagamento programado
  contra ela, sem dupla contagem.
- "Diversas obras" vai para a obra técnica **Despesas comuns — a ratear** (situação `COST_POOL`). O rateio exige aprovação e não é automático.
- Orçamento, datas e coordenadas ficam vazios até serem informados. O avanço físico vem só de medições aprovadas.
- O adiantamento e o saldo dos contratos são guardados como **informados na fonte**. O percentual de adiantamento considera só
  contratos com valor total.

## Conferência da fonte (PDF da FOPAG 28/08/2026)
- A linha TOTAL do PDF usa fórmulas com intervalos diferentes:
  - **contratado:** R$ 730.169,72 na linha TOTAL, mas as linhas somam R$ 736.169,72 (falta Francisco);
  - **adiantamento:** R$ 195.790,00 na linha TOTAL, mas as linhas somam R$ 214.383,00 (faltam Juarez, Kleyton e Francisco).
- A coluna SALDO por linha não é contrato menos adiantamento (ex.: Raimundo BR: 38.000 − 27.500 ≠ 5.000). Ela é mantida como informada.
- Corrigido em relação à transcrição anterior:
  - contrato **Ipapel Teresina** (plotagem, Casa Barra, adiantamento de R$ 9.000,00, sem valor de contrato) incluído;
  - folha do **Laércio** passou para **Tabocal**, conforme o PDF.

## Endpoints novos
`GET /api/v1/portfolio`, `GET /api/v1/schedule[?start&end]`, `GET /api/v1/contracts`, `GET /api/v1/payables`,
`GET /api/v1/projects/{id}/details`, `PATCH /api/v1/projects/{id}`. Todos têm escopo por membership.

## Como rodar localmente
Veja [DESENVOLVIMENTO-LOCAL.md](DESENVOLVIMENTO-LOCAL.md).
