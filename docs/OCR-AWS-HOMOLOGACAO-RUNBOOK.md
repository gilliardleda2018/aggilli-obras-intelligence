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
