"""
Prática Seed a Bit · soma investimentos ESG por empresa.

Fluxo: alguém envia um CSV para s3://BUCKET/entrada/ → o S3 dispara esta Lambda
→ ela lê a planilha, agrupa as linhas em lotes e, para cada lote, soma os
valores de cada empresa no DynamoDB.
"""
import csv
import io
import json
import os
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from urllib.parse import unquote_plus

import boto3  # já vem no runtime Python da Lambda

s3 = boto3.client("s3")
tabela = boto3.resource("dynamodb").Table(os.environ["TABELA"])
TAMANHO_LOTE = int(os.environ.get("TAMANHO_LOTE", "50"))

PILARES = {"Ambiental": "total_ambiental", "Social": "total_social", "Governança": "total_governanca"}
COLUNAS = {"empresa_id", "empresa", "pilar", "valor"}


def handler(event, context):
    resumo = []
    for registro in event["Records"]:
        bucket = registro["s3"]["bucket"]["name"]
        chave = unquote_plus(registro["s3"]["object"]["key"])
        resumo.append(processar_planilha(bucket, chave))
    return {"planilhas": resumo}


def processar_planilha(bucket, chave):
    print(json.dumps({"evento": "inicio", "arquivo": chave}))
    corpo = s3.get_object(Bucket=bucket, Key=chave)["Body"].read().decode("utf-8-sig")
    leitor = csv.DictReader(io.StringIO(corpo))

    faltando = COLUNAS - set(leitor.fieldnames or [])
    if faltando:
        raise ValueError(f"Planilha sem as colunas: {sorted(faltando)}")

    lote, n_lote, linhas_ok, linhas_invalidas = [], 0, 0, 0
    for numero, linha in enumerate(leitor, start=2):  # linha 1 é o cabeçalho
        try:
            lote.append(normalizar(linha))
        except ValueError as erro:
            linhas_invalidas += 1
            print(json.dumps({"evento": "linha_invalida", "linha": numero, "erro": str(erro)}))
            continue
        if len(lote) == TAMANHO_LOTE:
            n_lote += 1
            linhas_ok += gravar_lote(lote, n_lote)
            lote = []
    if lote:
        n_lote += 1
        linhas_ok += gravar_lote(lote, n_lote)

    resultado = {"evento": "fim", "arquivo": chave, "lotes": n_lote,
                 "linhas_ok": linhas_ok, "linhas_invalidas": linhas_invalidas}
    print(json.dumps(resultado))
    return resultado


def normalizar(linha):
    empresa_id = (linha.get("empresa_id") or "").strip()
    if not empresa_id:
        raise ValueError("empresa_id vazio")
    pilar = (linha.get("pilar") or "").strip()
    if pilar not in PILARES:
        raise ValueError(f"pilar desconhecido: {pilar!r}")
    try:
        valor = Decimal((linha.get("valor") or "").strip().replace(",", "."))
    except InvalidOperation:
        raise ValueError(f"valor inválido: {linha.get('valor')!r}")
    return {"empresa_id": empresa_id, "empresa": linha["empresa"].strip(), "pilar": pilar, "valor": valor}


def somar_por_empresa(lote):
    """Soma as linhas do lote em memória, agrupando por empresa."""
    totais = defaultdict(lambda: {"empresa": "", "total": Decimal(0), "qtd": 0,
                                  **{campo: Decimal(0) for campo in PILARES.values()}})
    for linha in lote:
        t = totais[linha["empresa_id"]]
        t["empresa"] = linha["empresa"]
        t["total"] += linha["valor"]
        t["qtd"] += 1
        t[PILARES[linha["pilar"]]] += linha["valor"]
    return totais


def gravar_lote(lote, n_lote):
    """Faz UMA escrita por empresa no DynamoDB (em vez de uma por linha)."""
    totais = somar_por_empresa(lote)
    for empresa_id, t in totais.items():
        tabela.update_item(
            Key={"empresa_id": empresa_id},
            # ADD soma ao valor que já existe (ou cria o campo começando do zero)
            UpdateExpression=(
                "SET empresa = :nome "
                "ADD total_investido :total, lancamentos :qtd, "
                "total_ambiental :amb, total_social :soc, total_governanca :gov"
            ),
            ExpressionAttributeValues={
                ":nome": t["empresa"], ":total": t["total"], ":qtd": t["qtd"],
                ":amb": t["total_ambiental"], ":soc": t["total_social"], ":gov": t["total_governanca"],
            },
        )
    print(json.dumps({"evento": "lote", "numero": n_lote, "linhas": len(lote), "empresas": len(totais)}))
    return len(lote)
