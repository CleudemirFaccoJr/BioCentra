#!/usr/bin/env bash
# exit on error
set -o errexit

# Instalar dependências do Python
pip install -r requirements.txt

# Baixar e instalar o wkhtmltopdf para Linux (essencial para o Render)
mkdir -p bin
curl -L https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.focal_amd64.deb -o wkhtmltopdf.deb
dpkg -x wkhtmltopdf.deb .
cp usr/local/bin/wkhtmltopdf bin/