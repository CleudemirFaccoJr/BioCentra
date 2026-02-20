# app.py
import platform
import os
import firebase_admin
from firebase_admin import credentials, db
import locale
from flask import Flask, json, jsonify, render_template, request,after_this_request, send_file, session, redirect, url_for
from weasyprint import HTML, CSS
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'chave_secreta_para_sessoes' # Essencial para o "session" funcionar

app.config['SESSION_PERMANENT'] = False

@app.template_filter('formato_moeda')
def formato_moeda(valor):
    try:
        if valor is None or valor == '':
            return "0,00"
        # Garante que o valor seja um float para formatação
        valor_float = float(valor)
        # Formata com separadores de milhar e decimal brasileiros
        return "{:,.2f}".format(valor_float).replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return valor
    
# Função que formata o CNPJ
@app.template_filter('cnpj')
def format_cnpj(value):
    if not value:
        return ""
    # Remove qualquer caractere que não seja número (caso já venha sujo)
    cnpj = "".join(filter(str.isdigit, str(value)))
    
    if len(cnpj) != 14:
        return cnpj # Retorna o original se não tiver 14 dígitos
    
    # Aplica a máscara: 00.000.000/0001-00
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

logo_path = os.path.join(BASE_DIR, 'static', 'logo.png').replace('\\', '/')

firebase_info = os.environ.get('FIREBASE_CONFIG')
# Inicialize o Firebase (faça isso fora das rotas, logo após o app = Flask(__name__))
# Certifique-se de ter o arquivo .json das suas credenciais
if not firebase_admin._apps:
    if firebase_info:
        # No Render
        cred = credentials.Certificate(json.loads(firebase_info))
    else:
        # Localmente (se você tiver o arquivo salvo como firebase-credentials.json)
        cred = credentials.Certificate("firebase-credentials.json")
    
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://orcamentos-bio-centra-default-rtdb.firebaseio.com/'
    })

    # Define a localização para português do Brasil para formatar moeda
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    except:
        locale.setlocale(locale.LC_ALL, '')

@app.route('/')
def index():
    cliente = session.get('cliente', {'nome':'', 'contato':'', 'email':'', 'telefone':'', 'endereco':''})
    return render_template('index.html', cliente=cliente)

@app.route('/proximo', methods=['POST'])
def proximo():
    # Coleta os dados do formulário
    dados_cliente = {
        'nome': request.form.get('nome'),
        'cnpj': request.form.get('cnpj').replace('.', '').replace('/', '').replace('-', ''), # Limpa a máscara
        'contato': request.form.get('contato'),
        'email': request.form.get('email'),
        'telefone': request.form.get('telefone'),
        'endereco': request.form.get('endereco'),
        'tipo_frete': request.form.get('tipo_frete'),
        'valor_frete': request.form.get('valor_frete') or '0'
    }

    # 1. Salva/Atualiza no Firebase usando o CNPJ como ID único
    if dados_cliente['cnpj']:
        ref = db.reference(f"clientes/{dados_cliente['cnpj']}")
        ref.set(dados_cliente) # O 'set' sobrescreve se já existir, evitando duplicatas

    # Busca o número atual para exibir na tela intermediária
    ref = db.reference('contador_orcamento')
    numero_atual = ref.get() or 0    

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

@app.route('/confirmar-numero', methods=['POST'])
def confirmar_numero():
    novo_num_input = request.form.get('novo_numero')
    ref = db.reference('contador_orcamento')
    
    if novo_num_input and novo_num_input.strip() != "":
        novo_valor = int(novo_num_input)
        # Atualiza o banco manualmente
        ref.set(novo_valor)
        # Opcional: usar flash message (requer {% with messages = get_flashed_messages() %} no HTML)
        print(f"Atenção! O número agora do contador de orçamentos é: {novo_valor}")
        # Armazena na sessão que este orçamento usará este número fixo ou apenas segue o fluxo
    
    return render_template('cadastro_produtos.html')

@app.route('/buscar-cliente/<cnpj>')
def buscar_cliente(cnpj):
    cnpj_limpo = cnpj.replace('.', '').replace('/', '').replace('-', '')
    ref = db.reference(f"clientes/{cnpj_limpo}")
    cliente = ref.get()
    return jsonify(cliente) if cliente else jsonify(None)

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
    garantias = request.form.getlist('prod_garantia[]')

    lista_produtos = []
    total_geral = 0
    arquivos_para_deletar = []

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
            arquivos_para_deletar.append(caminho_foto_final) 

        v_unit = float(valores[i].replace('.', '').replace(',', '.') or 0)
        qtd = int(quants[i] or 0)
        subtotal = v_unit * qtd
        total_geral += subtotal

        lista_produtos.append({
            'nome': nomes[i],
            'imagem': caminho_foto_final,
            'especificacoes': specs[i],
            'quantidade': qtd,
            'valor_unitario': v_unit,
            'subtotal': subtotal,
            'garantia': garantias[i]
        })

    # LÓGICA DO NÚMERO INCREMENTAL COM FIREBASE
    ref = db.reference('contador_orcamento')
    
    # transação garante que se dois usuários gerarem ao mesmo tempo, os números não batam
    def increment_transaction(current_value):
        return (current_value or 0) + 1

    novo_numero = ref.transaction(increment_transaction)
    
    # Formata para ter zeros a esquerda, ex: 2026-001
    numero_formatado = f"2026 - {novo_numero:03d}"
    
    html_renderizado = render_template(
        'orcamento.html',
        cliente=cliente,
        produtos=lista_produtos, # Passamos a lista completa com specs e imagens
        total=total_geral,
        data=datetime.now().strftime('%d/%m/%Y'),
        num_orcamento=numero_formatado,
        logo_path=f"file:///{logo_path}"
    )

    nome_arquivo = f"orcamento_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    caminho_pdf = os.path.join(OUTPUT_DIR, nome_arquivo)
    arquivos_para_deletar.append(caminho_pdf)

    HTML(string=html_renderizado, base_url=request.base_url).write_pdf(caminho_pdf)

    # Função mágica do Flask: executa algo DEPOIS que a resposta for enviada
    @after_this_request
    def remover_arquivo(response):
        try:
            os.remove(caminho_pdf)
            print(f"Arquivo {nome_arquivo} removido com sucesso!")
        except Exception as e:
            print(f"Erro ao deletar arquivo: {e}")
        return response
    
    @after_this_request
    def limpar_arquivos(response):
        for caminho in arquivos_para_deletar:
            try:
                if os.path.exists(caminho):
                    os.remove(caminho)
            except Exception as e:
                app.logger.error(f"Erro ao deletar {caminho}: {e}")
        return response
        
    return send_file(caminho_pdf, mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)
