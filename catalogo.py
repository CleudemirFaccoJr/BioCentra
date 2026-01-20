def gerar_catalogo_html(lista_produtos):
    def gerar_tabela(p):
        specs = [s.strip() for s in p['especificacoes'].split(";") if s.strip()]
        linhas = []
        for i in range(0, len(specs), 2):
            if i + 1 < len(specs):
                linhas.append(f"<tr><td>{specs[i]}</td><td>{specs[i+1]}</td></tr>")

        return f"""
        <div class="product" style="page-break-inside: avoid; margin-top: 30px;">
          <center><img src="file:///{p['imagem']}" width="250"></center>
          <h2 style="text-align: center;">{p['nome']}</h2>
          <table border="1" style="width:100%; border-collapse: collapse;">
            <thead><tr style="background: #eee;"><th>Especificação</th><th>Detalhe</th></tr></thead>
            <tbody>{"".join(linhas)}</tbody>
          </table>
        </div>
        """

    return "".join([gerar_tabela(prod) for prod in lista_produtos if prod['imagem']])