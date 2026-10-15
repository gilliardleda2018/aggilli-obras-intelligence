# Deploy na AWS — plano

> Conta 614471945241 · domínio `emobras.aggillintelligence.com.br` · certificado ACM já emitido em **us-east-1**.
> Valores mensais são estimativas de tabela (on-demand, 15/10/2026). Confirmar na AWS Pricing Calculator antes da proposta.

## Arquitetura recomendada (custo-benefício)
```
 Navegador / celular
        │ HTTPS (certificado ACM)
        ▼
 Application Load Balancer ──► ECS Fargate "web" (Next.js, 0,5 vCPU / 1 GB)
                                     │  chamada interna (Service Connect), API não fica exposta na internet
                                     ▼
                               ECS Fargate "api" (FastAPI, 0,5 vCPU / 1 GB)
                                │            │                 │
                                ▼            ▼                 ▼
                     RDS PostgreSQL     S3 privado        Claude Platform on AWS
                     (db.t4g.micro)    (fotos e notas)    (leitura de notas)
```
- **Só o site é público.** A API responde apenas ao site, pela rede interna do ECS.
- **Sem NAT Gateway:** as tarefas ficam em sub-redes públicas, mas o security group só aceita tráfego do load balancer. Isso economiza ~US$ 33 por mês.
- **Segredos** (senha do banco, chaves de sessão, OIDC) ficam no AWS Secrets Manager e são injetados nas tarefas, nunca no código.
- **Permissões por papel IAM da tarefa:** a API pode ler e gravar só no bucket dela e chamar o Claude. Nenhuma chave de acesso fixa.
- **Deploy pelo GitHub Actions** com papel IAM via OIDC (sem chave guardada no GitHub):
  1. Gera as imagens e envia ao ECR.
  2. Roda `alembic upgrade head` numa tarefa avulsa.
  3. Atualiza os serviços.
- **Proteção:** RDS criptografado com backup automático de 7 dias; bucket com bloqueio de acesso público, criptografia e versionamento; logs no CloudWatch (30 dias); alerta de orçamento no AWS Budgets.

## Custo mensal estimado (us-east-1)
| Item | US$/mês |
|---|---|
| Load balancer (ALB) | ~22 |
| ECS Fargate: web + api (0,5 vCPU / 1 GB cada, 24 h) | ~36 |
| RDS PostgreSQL db.t4g.micro + 20 GB | ~14 |
| IPv4 público (ALB + tarefas) | ~15 |
| S3, logs, Secrets Manager, ECR | ~5 |
| **Total fixo** | **~92 (≈ R$ 505)** |
| Leitura de notas (variável, ver `OCR-DOCUMENTOS.md`) | ~0,003 por documento |

**Para crescer:** banco Multi-AZ (+~US$ 14), 2 tarefas de cada serviço para alta disponibilidade (+~US$ 36) e instância de banco maior conforme o uso.

## Região: decisão pendente
| | us-east-1 (N. Virginia), **recomendada** | sa-east-1 (São Paulo) |
|---|---|---|
| Custo | base | ~40–50% mais caro |
| Certificado | já emitido | emitir outro (grátis, ~5 min) |
| Latência no Maranhão | ~150 ms (aceitável para o sistema) | ~40 ms |
| Dados no Brasil (LGPD / exigência de órgão público) | não | sim |

Se algum cliente (prefeitura, por exemplo) exigir dados armazenados no Brasil, use sa-east-1. Caso contrário, us-east-1.

## Antes de tudo: usuário de administração (em vez do root)
Feito uma única vez, pelo dono da conta, no console da AWS logado como root:
1. Ligue o **MFA no root**: menu da conta (canto superior direito) → *Credenciais de segurança* → *Atribuir dispositivo MFA*.
2. Busque **IAM Identity Center** → *Habilitar* (região us-east-1).
3. Em *Usuários* → *Adicionar usuário*: use seu e-mail e defina a senha pelo link que chega por e-mail.
4. Em *Conjuntos de permissões* → *Criar* → *Conjunto predefinido* → `AdministratorAccess`.
5. Em *Contas da AWS* → marque a conta 614471945241 → *Atribuir usuários* → seu usuário + `AdministratorAccess`.
6. Entre pelo **portal de acesso** (link mostrado no painel do Identity Center), ative o MFA do novo usuário e
   **reconecte o conector da AWS no Claude com esse usuário**.
7. Daqui em diante, use o root só para cobrança e emergências.

## Ordem de execução (quando o conector AWS estiver ativo)
1. **Base:** orçamento com alerta, ECR, bucket S3, segredos.
2. **Rede e banco:** VPC com 2 sub-redes públicas, security groups e RDS.
3. **ECS:** cluster, serviços web e api, load balancer com o certificado, migração inicial.
4. **DNS:** CNAME de `emobras` apontando para o load balancer, no provedor do domínio.
5. **Claude Platform on AWS:** workspace e permissão no papel da API; ligar `DOC_AI_PROVIDER=aws`.
6. **GitHub Actions:** papel OIDC e workflow de deploy.
7. **Verificação:** login, diário com foto, nota real lida e lançada.

A infraestrutura será descrita como código (CloudFormation) neste repositório, para poder ser recriada e auditada.
