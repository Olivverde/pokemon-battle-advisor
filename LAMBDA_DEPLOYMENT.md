# AWS Lambda Deployment Guide - Pokemon Advisor Scraper

## Qué hace
La función Lambda `lambda_scraper.py` descarga replays recientes de Pokémon Showdown y los guarda en S3.

## Requisitos previos
- AWS CLI configurado (`aws configure`)
- Acceso a S3 y Lambda
- Bucket S3 ya creado: `pokemon-advisor-raw-317520059338`

## Paso 1: Crear la Lambda function en AWS

```bash
aws lambda create-function \
  --function-name pokemon-advisor-scraper \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-s3-role \
  --handler lambda_scraper.handler \
  --timeout 300 \
  --memory-size 256
```

## Paso 2: Crear el IAM Role

Crea un archivo `lambda_trust_policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Crea el role:

```bash
aws iam create-role \
  --role-name lambda-s3-role \
  --assume-role-policy-document file://lambda_trust_policy.json
```

Asigna permisos para S3:

```bash
aws iam put-role-policy \
  --role-name lambda-s3-role \
  --policy-name lambda-s3-policy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:GetObject",
          "s3:PutObject",
          "s3:HeadObject"
        ],
        "Resource": "arn:aws:s3:::pokemon-advisor-raw-317520059338/*"
      }
    ]
  }'
```

## Paso 3: Empaquetar con dependencias

```bash
bash build_lambda.sh
```

Esto crea `lambda_scraper.zip` con `requests` incluido.

## Paso 4: Desplegar la función

```bash
aws lambda update-function-code \
  --function-name pokemon-advisor-scraper \
  --zip-file fileb://lambda_scraper.zip
```

## Paso 5: Configurar variables de entorno

```bash
aws lambda update-function-configuration \
  --function-name pokemon-advisor-scraper \
  --environment Variables="{
    RAW_BUCKET=pokemon-advisor-raw-317520059338,
    POKEMON_FORMAT=gen9ou,
    MAX_REPLAYS=50
  }"
```

## Paso 6: Configurar triggers (opcional)

Para ejecutar cada hora con EventBridge:

```bash
# Crear regla
aws events put-rule \
  --name pokemon-scraper-hourly \
  --schedule-expression "rate(1 hour)"

# Permitir que EventBridge invoque la Lambda
aws lambda add-permission \
  --function-name pokemon-advisor-scraper \
  --statement-id AllowEventBridgeInvoke \
  --action 'lambda:InvokeFunction' \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:YOUR_REGION:YOUR_ACCOUNT:rule/pokemon-scraper-hourly

# Configurar target
aws events put-targets \
  --rule pokemon-scraper-hourly \
  --targets "Id"="1","Arn"="arn:aws:lambda:YOUR_REGION:YOUR_ACCOUNT:function:pokemon-advisor-scraper"
```

## Prueba local

```bash
# Sin AWS Lambda
cd src/pipeline
python lambda_scraper.py
```

## Monitoreo

Ver logs en CloudWatch:

```bash
aws logs tail /aws/lambda/pokemon-advisor-scraper --follow
```

Invocar manualmente desde CLI:

```bash
aws lambda invoke \
  --function-name pokemon-advisor-scraper \
  --payload '{}' \
  response.json

cat response.json
```

## Configuración recomendada

- **Timeout**: 300 segundos (5 minutos)
- **Memory**: 256 MB
- **Ephemeral storage**: 512 MB (default)
- **Concurrent executions**: 1 (para evitar duplicados)
