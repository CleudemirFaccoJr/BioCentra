# app.py
import platform
import os
import pandas as pd
from flask import Flask, render_template, request, send_file, session, redirect, url_for
from weasyprint import HTML, CSS
from datetime import datetime
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.secret_key = 'chave_secreta_para_sessoes' # Essencial para o "session" funcionar

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

logo_path = os.path.join(BASE_DIR, 'static', 'logo.png').replace('\\', '/')

@app.route('/')
def index():
    cliente = session.get('cliente', {'nome':'', 'contato':'', 'email':'', 'telefone':'', 'endereco':''})
    return render_template('index.html', cliente=cliente)

@app.route('/proximo', methods=['POST'])
def proximo():
    # Salva os dados do cliente na sessão
    session['cliente'] = {
        'nome': request.form.get('nome'),
        'contato': request.form.get('contato'),
        'cnpj': request.form.get('cnpj'),
        'email': request.form.get('email'),
        'telefone': request.form.get('telefone'),
        'endereco': request.form.get('endereco'),
        'tipo_frete': request.form.get('tipo_frete'),
        'valor_frete': request.form.get('valor_frete') if request.form.get('tipo_frete') != 'Proprio' else 0
    }
    return render_template('cadastro_produtos.html')

@app.route('/gerar-orcamento', methods=['POST'])
def gerar_orcamento():
    cliente = session.get('cliente')
    if not cliente:
        return redirect(url_for('index'))

    # Coleta listas do formulário
    nomes = request.form.getlist('prod_nome[]')
    quants = request.form.getlist('prod_quant[]')
    valores = request.form.getlist('prod_valor[]')
    specs = request.form.getlist('prod_specs[]')
    fotos = request.files.getlist('prod_foto[]') # Arquivos de imagem

    lista_produtos = []
    total_geral = 0

    for i in range(len(nomes)):
        if not nomes[i]: continue # Pula linhas vazias

        # Trata o upload da imagem
        foto = fotos[i]
        caminho_foto_final = ""
        if foto and foto.filename != '':
            filename = secure_filename(f"{datetime.now().timestamp()}_{foto.filename}")
            caminho_foto_final = os.path.join(UPLOAD_FOLDER, filename)
            foto.save(caminho_foto_final)
            caminho_foto_final = caminho_foto_final.replace('\\', '/')

        v_unit = float(valores[i] or 0)
        qtd = int(quants[i] or 0)
        subtotal = v_unit * qtd
        total_geral += subtotal

        lista_produtos.append({
            'nome': nomes[i],
            'imagem': caminho_foto_final,
            'especificacoes': specs[i],
            'quantidade': qtd,
            'valor_unitario': v_unit,
            'subtotal': subtotal
        })

    
    html_renderizado = render_template(
        'orcamento.html',
        cliente=cliente,
        produtos=lista_produtos, # Passamos a lista completa com specs e imagens
        total=total_geral,
        data=datetime.now().strftime('%d/%m/%Y'),
        logo_path=f"file:///{logo_path}"
    )

    nome_arquivo = f"orcamento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    caminho_pdf = os.path.join(OUTPUT_DIR, nome_arquivo)

    HTML(string=html_renderizado, base_url=request.base_url).write_pdf(caminho_pdf)

    return send_file(caminho_pdf, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
