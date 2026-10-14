# Desafios · entrega amanhã, 15/10

## Desafio 1 · Essa arquitetura está bem montada?

Use o diagrama `arquitetura-plataforma-esg.png`. Pesquise, use IA e consulte a documentação
da AWS para dizer se esse desenho atende a Plataforma Web ESG. Vale discordar.

Perguntas-guia:
- Responde em menos de 500 ms, mesmo com partida a frio?
- A Lambda dentro da VPC consegue falar com SQS, S3 e SES?
- O que acontece se o Aurora ou uma zona de disponibilidade cair?
- O isolamento entre empresas está garantido?
- O que está sobrando ou faltando?

**Entregue (1 página):** 3 pontos fortes · 3 riscos ou falhas · o que você mudaria e por quê ·
fontes e prompts usados.

## Desafio 2 · Quanto custa a Plataforma ESG por mês?

Ferramenta: **AWS Pricing Calculator** → https://calculator.aws/

Cenário de Produção (região sa-east-1):

| Serviço | Uso |
|---|---|
| Cognito | 5.000 usuários ativos por mês |
| API Gateway (HTTP) | 3 milhões de requisições por mês |
| Lambda (API) | 3 milhões de chamadas, 300 ms, 512 MB |
| Lambda (workers) | 200 mil chamadas, 2 s, 1 GB |
| Aurora Serverless v2 | média de 1 ACU, 20 GB + RDS Proxy |
| S3 | 200 GB de vídeos + 20 GB de documentos |
| CloudFront | 1 TB transferido por mês |
| SQS · SES | 500 mil mensagens · 20 mil e-mails |
| CloudWatch | 10 GB de logs por mês |

**Entregue:** o link compartilhado (botão *Share*) da estimativa de **Produção** e de **Dev** ·
os 3 serviços mais caros · uma ideia para baratear cada um.
