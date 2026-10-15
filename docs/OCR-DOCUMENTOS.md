# Leitura de documentos (OCR) — decisão e custos

> Base da proposta comercial. Preços de tabela consultados em 15/10/2026, em dólar. A conversão usa R$ 5,50 por US$
> (premissa, ajuste no fechamento). Estimativas por documento valem para foto de celular de nota, recibo ou orçamento
> de uma página.

## Decisão
**Leitura com Claude Haiku 5.5, contratado pela AWS (Claude Platform on AWS).** Quando a leitura sair com baixa
confiança ou não fechar a conta (soma dos itens ≠ total, chave da nota inválida), o documento é relido pelo
**Claude Sonnet 5.5**. Nenhum valor lido entra nos custos sem alguém conferir.

Para nota fiscal eletrônica, a **chave de acesso de 44 dígitos** é validada pelo dígito verificador. Isso confirma
CNPJ do emitente, número e mês da nota sem depender da IA.

### Por quê
| | Claude Haiku 5.5 (+ Sonnet 5.5 quando preciso) | Amazon Textract AnalyzeExpense |
|---|---|---|
| Custo por documento | ~US$ 0,001 (Haiku); ~US$ 0,02 quando relido pelo Sonnet | US$ 0,01 por página |
| Recibo escrito à mão | Lê | Fraco |
| Documento brasileiro fora do padrão (orçamento, recibo de pedreiro) | Lê e entende o tipo | Extrai campos genéricos; o resto fica por nossa conta |
| Já devolve tipo do documento, categoria e itens organizados | Sim | Não; exige regras adicionais |
| Cobrança | Fatura AWS (Marketplace), credenciais IAM | Fatura AWS |

Contratar pela **Claude Platform on AWS** em vez do Bedrock mantém tudo na conta AWS do cliente (IAM e fatura AWS)
com o preço de tabela da Anthropic e todos os recursos da API. O sistema também aceita Bedrock ou a API direta da
Anthropic, trocando só configuração (`DOC_AI_PROVIDER`).

## Estimativa de custo por documento
Premissas: foto reduzida para no máximo 1600 px no lado maior (~2.500 tokens de imagem), instruções ~500 tokens,
resposta ~1.500 tokens (inclui raciocínio em esforço baixo).

| Motor | Entrada | Saída | Total US$ | Total R$ |
|---|---|---|---|---|
| Claude Haiku 5.5 (US$ 0,10 / 0,50 por milhão de tokens) | 3.000 tok → US$ 0,0003 | 1.500 tok → US$ 0,00075 | **~0,001** | **~0,006** |
| Claude Sonnet 5.5 (US$ 2 / 10 por milhão), só nas releituras | 3.000 tok → US$ 0,006 | 1.500 tok → US$ 0,015 | ~0,021 | ~0,12 |
| Mistura esperada (10% relidos pelo Sonnet) | | | **~0,003** | **~0,017** |
| Textract AnalyzeExpense (comparação) | | | 0,01 | 0,055 |

### Exemplo mensal
10 obras × 300 documentos por mês = 3.000 documentos:
- Leitura: ~US$ 9 por mês (~R$ 50). Com Textract seriam ~US$ 30 (~R$ 165), lendo pior.
- Armazenamento S3 (≈ 2 MB por foto, 6 GB por mês acumulados): poucos reais por mês.

Sugestão para a proposta: cobrar a leitura de documentos dentro da mensalidade por obra, ou como franquia (por
exemplo 500 documentos por obra por mês), porque o custo variável é muito baixo.

## Pontos a confirmar antes da produção
- Preço final na AWS Marketplace para a conta do cliente (o cálculo usa o preço de tabela da Anthropic).
- Região e residência dos dados (LGPD): onde a inferência roda e o texto da cláusula de tratamento de dados no
  contrato com o cliente.
- Cotação do dólar usada na proposta.

## Configuração (backend)
| Variável | Valor | Uso |
|---|---|---|
| `DOC_AI_PROVIDER` | `off` (padrão), `aws`, `bedrock`, `anthropic` | `off` = só captura e lançamento manual |
| `DOC_AI_MODEL` | `claude-haiku-5-5` | Primeira leitura |
| `DOC_AI_REVIEW_MODEL` | `claude-sonnet-5-5` | Releitura quando a primeira não confere; vazio desliga |
| `AWS_REGION`, `ANTHROPIC_AWS_WORKSPACE_ID` | | Claude Platform on AWS (credenciais pelo IAM) |
| `FILE_STORAGE_BUCKET` | nome do bucket S3 | Fotos e documentos; vazio = disco local (`PHOTO_STORAGE_DIR`) |
