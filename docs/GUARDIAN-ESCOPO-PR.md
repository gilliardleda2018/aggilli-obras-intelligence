# Guardian v1.4 — política de escopo

O validador `tools/guardian/pr_scope.py` compara o diff real do Git com prefixos declarados em `.guardian/scope.json`.

**Estado atual: advisory.** O workflow registra violações, mas utiliza `continue-on-error: true`. Isso evita bloquear PRs legítimos de financeiro, OCR, mapas e outros módulos, pois a política inicial descreve apenas a manutenção da Guardian.

## Limites de segurança
- `allow_prefixes` é declaração de escopo, **não** autorização para mudar dados, credenciais ou produção.
- O arquivo da política dentro do PR não é uma fonte de confiança suficiente para um gate obrigatório: o autor pode alterá-lo junto com o código.
- Um gate obrigatório futuro deve ler a política da branch protegida e validar permissões, responsáveis, caminhos e aprovação independente.
- Os PRs existentes devem continuar submetidos aos testes backend/frontend e revisão humana.
- Não usar `pull_request_target` para executar código de PR não confiável com credenciais.

## Critérios para tornar obrigatório
1. Política versionada por módulos, aprovada em branch protegida.
2. Detecção de renomeações e exclusões, além de adições/modificações.
3. Verificação do diff com base SHA imutável e proteção contra manipulação de política no PR.
4. Regras de exceção auditáveis para mudanças transversais.
5. Testes positivos e negativos em PRs de financeiro, autenticação, OCR, mapas e Guardian.
6. Configuração de branch protection revisada, sem conceder bypass automático.

Até lá, tratar `GUARDIAN_SCOPE_FAIL` como alerta de revisão, não como reprovação automática de um PR.
