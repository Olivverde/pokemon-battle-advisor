#!/bin/bash
# Script para empaquetar la Lambda function con todas sus dependencias

echo "🔨 Empaquetando Lambda function..."

# Crear directorio temporal
mkdir -p lambda_package
cd lambda_package

# Instalar requests en el directorio
pip install requests -t . --quiet

# Copiar el código de la función
cp ../src/pipeline/lambda_scraper.py .

# Crear el ZIP
zip -r ../lambda_scraper.zip . -q

# Limpiar
cd ..
rm -rf lambda_package

echo "✅ Lambda package creado: lambda_scraper.zip"
echo ""
echo "📤 Para deployer a AWS Lambda:"
echo "   aws lambda update-function-code --function-name pokemon-advisor-scraper --zip-file fileb://lambda_scraper.zip"
