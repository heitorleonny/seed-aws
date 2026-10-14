# Prática Seed a Bit · planilha → S3 → Lambda (Python) → DynamoDB

```
você: aws s3 cp planilha.csv  ──►  S3 (entrada/)  ──►  Lambda Python  ──►  DynamoDB
                                     dispara o evento     lê em lotes de 50     1 item por empresa
                                                          e soma por empresa    com os totais
```

A planilha `dados/investimentos_esg.csv` tem 243 lançamentos de investimentos ESG de
10 empresas fictícias (colunas `data, empresa_id, empresa, pilar, acao, valor`).
Três linhas têm erro **de propósito** (pilar inexistente, empresa sem ID e valor em texto)
para mostrar a validação no log.

A Lambda:
1. lê o CSV que chegou no bucket;
2. valida cada linha e separa as inválidas;
3. agrupa em **lotes de 50 linhas**;
4. em cada lote, soma em memória por empresa e faz **uma escrita por empresa** no DynamoDB
   (`UpdateItem` com `ADD`), somando `total_investido`, `lancamentos` e o total de cada pilar.

Tudo é criado pelo `template.yaml` (AWS SAM). Nada é criado clicando no console.

---

## 0. Instale na sua máquina

- [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) → `aws --version`
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) → `sam --version`

O código só usa a biblioteca padrão do Python e o `boto3`, que já vem na Lambda.
Por isso não há dependências e nem é preciso rodar `sam build`.

## 1. Crie o usuário da sua máquina (uma vez, no console)

Na **conta de Dev**, logado com um administrador (nunca com o root):

1. **IAM → User groups → Create group** `seed-devs`, com a policy gerenciada **PowerUserAccess**
   (libera os serviços, mas não o IAM).
2. No grupo: **Permissions → Add permissions → Create inline policy → JSON**, cole
   `politica-seed-roles.json` e dê o nome `seed-roles-pratica`.
   Ela deixa o SAM criar **apenas** roles com nome `seed-pratica-*`.
3. **IAM → Users → Create user** `seunome-dev`, **sem** acesso ao console, dentro do grupo.
4. No usuário: **Security credentials → Create access key → Command Line Interface (CLI)**.
   O *secret* aparece uma vez só.

## 2. Configure a CLI

```bash
aws configure --profile seed-dev
#   Access Key ID / Secret: (cole)   Region: sa-east-1   Output: json

aws sts get-caller-identity --profile seed-dev    # deve mostrar user/seunome-dev
```

A chave fica em `~/.aws/credentials`, fora do projeto. Nunca no código, nunca no Git.

## 3. Suba

```bash
cd pratica
sam validate --lint --profile seed-dev
sam deploy --guided --profile seed-dev --tags projeto=seed-pratica
```

| Pergunta do `--guided` | Resposta |
|---|---|
| Stack Name | `seed-pratica` (**precisa** ser esse, por causa da policy) |
| AWS Region | `sa-east-1` |
| Confirm changes before deploy | `Y` |
| Allow SAM CLI IAM role creation | `Y` |
| Disable rollback | `N` |
| Save arguments to configuration file | `Y` |

Nos **Outputs** aparecem o nome do `Bucket` e da `Tabela`.

## 4. Teste

```bash
BUCKET=seed-pratica-planilhas-SEU_ID_DA_CONTA     # do output
TABELA=nome-da-tabela                             # do output

aws s3 cp dados/investimentos_esg.csv "s3://$BUCKET/entrada/" --profile seed-dev

# alguns segundos depois:
aws dynamodb get-item --table-name "$TABELA" \
  --key '{"empresa_id":{"S":"EMP-001"}}' --profile seed-dev

aws dynamodb scan --table-name "$TABELA" --profile seed-dev \
  --query "Items[].[empresa.S, total_investido.N, lancamentos.N]" --output table
```

Resultado esperado para a planilha de exemplo: 10 empresas, 240 lançamentos somados.
A EMP-001 (Verde Vale Alimentos) fica com `total_investido` = **203660.72** em 20 lançamentos.

## 5. Veja os logs

```bash
sam logs --stack-name seed-pratica --name ProcessarPlanilhaFunction --tail --profile seed-dev
```

Você vai ver o início, os 5 lotes, as 3 linhas inválidas (com o motivo) e o resumo final.

## 6. Para pensar

Envie a **mesma** planilha de novo e consulte a EMP-001. O total dobrou.
Como impedir que um arquivo seja somado duas vezes? (Dica: idempotência.)

## 7. Destrua tudo

```bash
aws s3 rm "s3://$BUCKET" --recursive --profile seed-dev   # o bucket precisa estar vazio
sam delete --stack-name seed-pratica --profile seed-dev
```

Depois, **desative a access key** em IAM → Users → seunome-dev → Security credentials.

## Erros comuns

| Erro | Causa provável |
|---|---|
| `not authorized to perform: iam:CreateRole` | Stack com nome diferente de `seed-pratica`, ou falta a inline policy no grupo |
| `The security token included in the request is invalid` | Chave ou perfil errado: rode `aws sts get-caller-identity --profile seed-dev` |
| `BucketAlreadyExists` | Muito raro: o nome usa o ID da conta. Confira se já não existe uma stack antiga |
| Nada aparece no DynamoDB | O arquivo precisa estar em `entrada/` e terminar em `.csv`. Veja o `sam logs` |
| `sam delete` falha no bucket | O bucket não está vazio: rode o `aws s3 rm` antes |
