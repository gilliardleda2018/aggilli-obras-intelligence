# OCR — Procedimento de desbloqueio da homologação AWS

Data: 2026-10-16. Responsável: frente OCR, PR #19 Draft. Documento de handoff para outras instâncias.

## Estado confirmado
- Último SHA validado do PR #19: `ad2955f4aa15fd28c38d8528dc8062e761b144e9`, CI success em 38822412303 e 38822417655.
- Produção ECS `obras-api:2` em us-east-1: `DOC_AI_PROVIDER=off`, `ANTHROPIC_AWS_WORKSPACE_ID` vazio.
- IAM task role possui política inline `arquivos-e-leitura` com `aws-external-anthropic:*` em `*`. Isso não comprova acesso efetivo.
- Inspeção complementar CloudFormation bloqueada por controles da ferramenta. Não contornar.
- Não foi possível executar inferência real; nenhuma ativação realizada.

## Ações de desbloqueio, somente leitura
1. Pelo console autorizado da conta AWS, verificar a existência de workspace Claude Platform on AWS em us-east-1, seu identificador e a disponibilidade dos modelos. Não registrar credenciais nem tokens em arquivos.
2. Confirmar quais operações de inferência e recursos devem ser permitidos ao papel da tarefa; propor privilégio mínimo antes de modificar IAM.
3. Em ambiente de homologação separado, confirmar a versão do SDK `anthropic` e as assinaturas reais de `AnthropicAWS`, `AnthropicBedrockMantle` e `messages.create(output_config=...)`. Não presumir compatibilidade pelo CI com mocks.
4. Se o provedor estiver disponível, executar apenas uma leitura de imagem sintética, sem escrita em banco de produção e sem gerar despesa. Registrar modelo, resposta saneada, custo e eventuais erros.
5. Só depois apresentar proposta de configuração ECS, rollback para `DOC_AI_PROVIDER=off` e aprovação de ativação.

## Regras de colaboração
- PR #19 detém `backend/app/ocr.py`, `backend/tests/test_ocr_regression.py` e documentação OCR.
- PR #20 trabalha com importação FOPAG; não sobrescrever arquivos de outra frente.
- Não fazer merge, deploy ou mudanças de frontend, layout, banco, financeiro ou licença.
- Se não houver acesso autorizado ao workspace, manter bloqueio explícito. Não declarar OCR funcional.

## Próximo gate
Comprovação do workspace + compatibilidade do SDK + inferência sintética bem-sucedida. Sem esses três itens, a homologação permanece **BLOQUEADA**.

## Evidência adicional: catálogo Bedrock (2026-10-16)
- Consulta read-only `bedrock:ListFoundationModels` em `us-east-1` retornou modelos com entrada IMAGE e status ACTIVE:
  - `anthropic.claude-haiku-5-5`
  - `anthropic.claude-sonnet-5-5`
- Esta descoberta é apenas catálogo regional. **Não demonstra autorização da conta para invocar, compatibilidade do SDK, nem workspace Claude Platform on AWS**. Não trocar o provedor para `bedrock` sem validação específica.
- Nenhuma inferência, mudança de IAM ou configuração ECS foi executada.

## Evidência adicional: perfis de inferência Bedrock
- `bedrock:ListInferenceProfiles`, us-east-1, consulta somente leitura: `us.anthropic.claude-haiku-5-5`, `us.anthropic.claude-sonnet-5-5`, `global.anthropic.claude-haiku-5-5` e `global.anthropic.claude-sonnet-5-5` com status `ACTIVE`.
- Perfis disponíveis no catálogo **não** significam que a task role da API tenha permissão `bedrock:InvokeModel` nem que Claude Platform on AWS esteja configurado.
- Proibido mudar `DOC_AI_PROVIDER` para `bedrock` apenas com esta evidência; falta validação de IAM, SDK e leitura sintética isolada.

## IAM — verificação de autorização, 2026-10-16
- `iam:SimulatePrincipalPolicy` para `bedrock:InvokeModel` no perfil `arn:aws:bedrock:us-east-1:614471945241:inference-profile/us.anthropic.claude-haiku-5-5`, com a role `obras-ApiTaskRole-dZoLRIqsBvt6`, retornou `implicitDeny`.
- Primeira simulação misturando `bedrock:InvokeModel` e `aws-external-anthropic:InvokeModel` falhou com `InvalidInput` por exigir informações distintas de autorização; esse erro não é evidência de permissão nem de negação para Claude Platform on AWS.
- **Decisão:** não migrar silenciosamente para Bedrock, não editar IAM e não habilitar OCR. Requer avaliação específica da plataforma escolhida e privilégio mínimo.

## IAM — Claude Platform on AWS, simulação separada
- `iam:SimulatePrincipalPolicy` da role `obras-ApiTaskRole-dZoLRIqsBvt6`, ação `aws-external-anthropic:InvokeModel`, recurso `*`: decisão `allowed`.
- Isso confirma apenas a avaliação da política IAM simulada; **não** comprova workspace, habilitação comercial, credenciais em runtime, nem execução de modelo.
- Resultado anterior Bedrock `bedrock:InvokeModel` permanece `implicitDeny`. Os provedores são distintos; não confundir resultados.
- Próximo bloqueio: workspace Claude Platform on AWS ausente na configuração ECS; validar sua existência e SDK antes de ativar.

## Verificação do SDK oficial no CI
- Commit `feaef4d1a1f650e3ee00935c16c81d2f83c824a0`: teste adicionado para verificar que o pacote instalado expõe `AnthropicAWS`, `AnthropicBedrockMantle` e `Anthropic`.
- CI success em [38829505099](https://github.com/gilliardleda2018/aggilli-obras-intelligence/actions/runs/38829505099) e [38829509196](https://github.com/gilliardleda2018/aggilli-obras-intelligence/actions/runs/38829509196).
- Isso valida a presença dos símbolos no SDK instalado pelo CI, mas não prova que os argumentos, credenciais, workspace ou chamadas reais funcionam.

## SDK — construtores verificados em CI
- Commit `0b1d49809c33bcdfd6f2b7d1f69311df4ff02a51` testa parâmetros `timeout` de `AnthropicAWS` e `aws_region`/`timeout` de `AnthropicBedrockMantle` via `inspect.signature`.
- GitHub Actions success em [38830421524](https://github.com/gilliardleda2018/aggilli-obras-intelligence/actions/runs/38830421524) e [38830424753](https://github.com/gilliardleda2018/aggilli-obras-intelligence/actions/runs/38830424753).
- Esta validação é estática: não prova autenticação, assinatura de `messages.create`, resposta estruturada nem leitura real.

## Alternativa autorizada — Amazon Textract (2026-10-16)
- Usuário autorizou adotar Textract em vez de Claude Platform on AWS, sem modificar layout, dados ou produção.
- Commits `764c79e46118818bbcb81289943f374f0a5eb0eb` (adaptador opcional) e `bde82451b8cb7cea697ad0c541ed46ab8546e3c0` (teste sintético mockado).
- CI no SHA `bde82451b8cb7cea697ad0c541ed46ab8546e3c0`: success em [38833512053](https://github.com/gilliardleda2018/aggilli-obras-intelligence/actions/runs/38833512053) e [38833518238](https://github.com/gilliardleda2018/aggilli-obras-intelligence/actions/runs/38833518238).
- `DOC_AI_PROVIDER=textract` seleciona `AnalyzeExpense`, preservando os provedores existentes e a confirmação humana.
- Simulação IAM da role ECS para `textract:AnalyzeExpense` retornou `implicitDeny`. A permissão precisa ser concedida de forma restrita antes de executar OCR real. Nenhuma permissão foi alterada.
- Limitações atuais: mapeamento de campos Textract é parcial; OCR de comprovantes e orçamentos não pode ser declarado equivalente ao Claude sem testes de documentos representativos. Não promover produção antes de homologação real.
