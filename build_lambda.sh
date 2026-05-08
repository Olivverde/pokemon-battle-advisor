#!/bin/bash
# Script para empaquetar la Lambda function con todas sus dependencias

echo "🔨 Empaquetando Lambda function..."

# Crear directorio temporal
mkdir -p lambda_package
cd lambda_package

# Instalar requests y pandas en el directorio
pip install requests pandas -t . --quiet

# Copiar el código de las funciones
cp ../src/pipeline/lambda_scraper.py .
cp ../src/pipeline/lambda_parser.py .

# Crear el ZIP
zip -r ../lambda_scraper.zip . -q

# Limpiar
cd ..
rm -rf lambda_package

echo "✅ Lambda package creado: lambda_scraper.zip"
echo ""
echo "📤 Para deployer a AWS Lambda:"
echo "   aws lambda update-function-code --function-name pokemon-advisor-scraper --zip-file fileb://lambda_scraper.zip"
