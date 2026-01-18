import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_db, engine, Base
import services as api
from models import User, Company, Product, Sale, Expense
from datetime import datetime, timedelta
import base64
import io

# Configurações iniciais da página
st.set_page_config(page_title='PeegFlow Pro', page_icon='⚡', layout='wide')
Base.metadata.create_all(bind=engine)
db = next(get_db())
api.create_initial_data(db)

# --- ESTILOS CSS (Login, PDV e Financeiro) ---
st.markdown("""<style>
    /* Estilo Geral */
    .stApp { background-color: #F4F7FE; color: #1B2559; }
    [data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #1F2937; }

    /* TELA DE LOGIN (Referência image_ea97e5) */
    .login-container { display: flex; flex-direction: column; align-items: center; justify-content: center; padding-top: 50px; }
    .login-box { background: white; padding: 40px; border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); width: 450px; text-align: center; }
    .login-logo-top { margin-bottom: 20px; }

    /* CUPOM FISCAL PDV (Referência image_e9b6e2) */
    .receipt-panel {
        background-color: #111827 !important; 
        border-radius: 20px; 
        padding: 25px; 
        color: white !important; 
        min-height: 550px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    .receipt-title { color: #A3AED0 !important; font-size: 0.8rem; font-weight: 700; letter-spacing: 1px; border-bottom: 1px solid #2B3674; padding-bottom: 10px; margin-bottom: 20px; }
    .receipt-item { display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 0.95rem; color: white !important; }
    .receipt-total-section { margin-top: 30px; border-top: 1px dashed #2B3674; padding-top: 20px; }
    .total-value { font-size: 2.8rem; font-weight: 800; color: #10B981 !important; line-height: 1; }

    /* MÓDULO FINANCEIRO (Referência image_ea9519) */
    .fin-card-white { background: white; padding: 35px; border-radius: 24px; border: 1px solid #E0E5F2; box-shadow: 0 4px 12px rgba(0,0,0,0.02); }
    .fin-card-purple { background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%); padding: 35px; border-radius: 24px; color: white; box-shadow: 0 10px 20px rgba(99, 102, 241, 0.2); }
    .fin-title { color: #A3AED0; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; margin-bottom: 10px; }
    .fin-value-main { color: #10B981; font-size: 2.5rem; font-weight: 800; margin-bottom: 20px; }
    
    /* Botões */
    div.stButton > button { border-radius: 12px; font-weight: 600; transition: all 0.3s; }
</style>""", unsafe_allow_html=True)

# Inicialização do estado da sessão
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user_id': None, 'company_id': None, 'username': None, 'cart': []})

# --- FUNÇÃO AUXILIAR PARA IMAGEM (Pode ficar logo antes do if de login) ---
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return None

# --- LÓGICA DE LOGIN ---
if not st.session_state['logged_in']:
    # Layout de colunas apenas para limitar a largura no Desktop
    # No mobile, o Streamlit empilha, mas o HTML interno manterá o centro
    _, col_central, _ = st.columns([1, 1.2, 1])
    
    with col_central:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        # 1. Carregar e converter a imagem
        img_b64 = get_img_as_base64("logo_peegflow.jpg")
        
        # 2. Renderizar Cabeçalho (Logo + Títulos) em HTML Puro
        # Isso garante que o alinhamento central funcione em qualquer dispositivo
        html_header = f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 20px;">
            <img src="data:image/jpeg;base64,{img_b64}" style="width: 80px; margin-bottom: 10px; border-radius: 50%;">
            <h2 style="text-align: center; color: #1B2559; margin: 0; font-size: 2rem;">Bem-vindo ao PeegFlow</h2>
            <p style="text-align: center; color: #A3AED0; margin-top: 10px; font-size: 1rem;">Insira os seus dados para aceder ao painel.</p>
        </div>
        """
        st.markdown(html_header, unsafe_allow_html=True)

        # 3. Formulário de Login
        with st.form("login_form"):
            u = st.text_input("USUÁRIO", placeholder="Ex: admin")
            p = st.text_input("SENHA", type="password", placeholder="••••••••")
            
            st.write("") # Espaçamento
            
            # Botão de Login
            if st.form_submit_button("Entrar no Sistema ⚡", use_container_width=True):
                user = api.authenticate(db, u, p)
                if user:
                    st.session_state.update({
                        'logged_in': True, 
                        'user_id': user.id, 
                        'company_id': user.company_id, 
                        'username': user.username
                    })
                    st.rerun()
                else:
                    st.error("Credenciais inválidas")

                
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()
# --- ESTRUTURA PRINCIPAL (SIDEBAR) ---
cid = st.session_state['company_id']
with st.sidebar:
    st.image("logo_peegflow.jpg", width=140)
    st.write(f"👤 **{st.session_state['username']}**")
    st.divider()
    choice = st.radio("Navegação", ["📊 Dashboard", "🛒 Checkout (PDV)", "💰 Fluxo Financeiro", "📦 Estoque"])
    if st.button("Sair"): st.session_state.clear(); st.rerun()

# --- DASHBOARD EXECUTIVO 2.0 ---
if choice == "📊 Dashboard":
    st.title("Dashboard Executivo")
    st.markdown("Visão estratégica do seu negócio em tempo real.")
    
    # 1. PREPARAÇÃO DOS DADOS
    # Vamos pegar 60 dias para poder comparar "Mês Atual" vs "Mês Anterior"
    end_date = datetime.now()
    start_date_current = end_date - timedelta(days=30)
    start_date_previous = start_date_current - timedelta(days=30)
    
    # Busca dados brutos
    df_vendas_atual, df_desp_atual = api.get_financial_by_range(db, cid, start_date_current, end_date)
    df_vendas_prev, df_desp_prev = api.get_financial_by_range(db, cid, start_date_previous, start_date_current)

    # Cálculos dos KPIs
    rec_atual = df_vendas_atual['price'].sum() if not df_vendas_atual.empty else 0
    rec_prev = df_vendas_prev['price'].sum() if not df_vendas_prev.empty else 0
    delta_rec = rec_atual - rec_prev
    
    lucro_atual = rec_atual - (df_desp_atual['amount'].sum() if not df_desp_atual.empty else 0)
    
    ticket_medio = df_vendas_atual['price'].mean() if not df_vendas_atual.empty else 0
    
    # Contagem de Vendas (Transações)
    qtd_vendas = len(df_vendas_atual)

    # 2. KPI CARDS COM DELTA (COMPARATIVO)
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric(
        "Faturamento (30d)", 
        f"€ {rec_atual:,.2f}", 
        f"{delta_rec:,.2f} vs mês ant.",
        delta_color="normal" # Verde se positivo, vermelho se negativo
    )
    col2.metric(
        "Lucro Líquido Est.", 
        f"€ {lucro_atual:,.2f}",
        "Margem: " + (f"{lucro_atual/rec_atual:.1%}" if rec_atual > 0 else "0%"),
        delta_color="off"
    )
    col3.metric(
        "Ticket Médio", 
        f"€ {ticket_medio:,.2f}",
        help="Valor médio gasto por cliente por compra"
    )
    col4.metric(
        "Total Vendas", 
        f"{qtd_vendas}",
        f"{qtd_vendas - len(df_vendas_prev)} vs mês ant."
    )

    st.divider()

    # 3. GRÁFICOS AVANÇADOS
    col_g1, col_g2 = st.columns([0.65, 0.35], gap="large")

    with col_g1:
        st.subheader("📈 Mapa de Calor de Vendas")
        if not df_vendas_atual.empty:
            # Processamento para Heatmap (Dia da Semana x Hora)
            df_heat = df_vendas_atual.copy()
            df_heat['date'] = pd.to_datetime(df_heat['date'])
            df_heat['hour'] = df_heat['date'].dt.hour
            df_heat['weekday'] = df_heat['date'].dt.day_name()
            
            # Agrupar dados
            heat_data = df_heat.groupby(['weekday', 'hour'])['price'].sum().reset_index()
            
            # Ordenar dias da semana corretamente
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            fig_heat = px.density_heatmap(
                heat_data, 
                x='hour', 
                y='weekday', 
                z='price', 
                color_continuous_scale='Viridis',
                category_orders={"weekday": days_order},
                title="Intensidade de Vendas (Dia x Hora)",
                labels={'weekday': 'Dia', 'hour': 'Hora', 'price': 'Vendas (€)'}
            )
            fig_heat.update_layout(xaxis_dtick=1) # Mostrar todas as horas
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("Sem dados suficientes para gerar o mapa de calor.")

    with col_g2:
        st.subheader("🏆 Top Produtos")
        if not df_vendas_atual.empty:
            # Agrupar por produto e somar vendas
            df_top = df_vendas_atual.groupby('product_name')['price'].sum().reset_index()
            df_top = df_top.sort_values(by='price', ascending=True).tail(5) # Top 5
            
            fig_bar = px.bar(
                df_top, 
                x='price', 
                y='product_name', 
                orientation='h',
                text_auto='.2s',
                title="Campeões de Receita",
                color='price',
                color_continuous_scale=['#A3AED0', '#6366F1'] # Cores do seu tema
            )
            fig_bar.update_layout(showlegend=False, xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Sem vendas registradas.")

    # 4. GRÁFICO DE TENDÊNCIA (LINHA DO TEMPO)
    st.subheader("Evolução Diária (Vendas vs Custos)")
    if not df_vendas_atual.empty:
        # Agrupa Vendas por dia
        daily_sales = df_vendas_atual.groupby(df_vendas_atual['date'].dt.date)['price'].sum().reset_index()
        daily_sales['Tipo'] = 'Receita'
        daily_sales.rename(columns={'price': 'Valor'}, inplace=True)
        
        # Agrupa Despesas por dia
        daily_exp = df_desp_atual.groupby(df_desp_atual['date'].dt.date)['amount'].sum().reset_index()
        daily_exp['Tipo'] = 'Despesa'
        daily_exp.rename(columns={'amount': 'Valor'}, inplace=True)
        
        # Junta tudo
        df_chart = pd.concat([daily_sales, daily_exp])
        
        fig_evol = px.area(
            df_chart, 
            x='date', 
            y='Valor', 
            color='Tipo',
            color_discrete_map={'Receita': '#10B981', 'Despesa': '#FF4B4B'}, # Verde e Vermelho
            title="Comparativo Diário"
        )
        st.plotly_chart(fig_evol, use_container_width=True)


import io
from fpdf import FPDF

def add_to_cart(product):
    cart = st.session_state["cart"]
    for item in cart:
        if item["id"] == product.id:
            item["qty"] += 1
            return
    cart.append({
        "id": product.id,
        "name": product.name,
        "price": product.price_retail,
        "qty": 1
    })

def generate_receipt_80mm(cart, total, payment):
    pdf = FPDF("P", "mm", (80, 200))
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 6, "PEEGFLOW", ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "CUPOM NAO FISCAL", ln=True, align="C")
    pdf.ln(3)

    for item in cart:
        pdf.cell(0, 5, item["name"][:32], ln=True)
        pdf.cell(
            0, 5,
            f'{item["qty"]} x R$ {item["price"]:.2f} = R$ {item["price"] * item["qty"]:.2f}',
            ln=True
        )

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, f"TOTAL: R$ {total:.2f}", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"Pagamento: {payment}", ln=True)
    pdf.cell(0, 5, datetime.now().strftime("%d/%m/%Y %H:%M"), ln=True)

    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

if choice == "🛒 Checkout (PDV)":
    st.title("Ponto de Venda")

    if "cart" not in st.session_state:
        st.session_state["cart"] = []

    col_prod, col_receipt = st.columns([0.6, 0.4])

    with col_prod:
        search = st.text_input("🔍 Buscar produto")
        prods = api.get_products(db, cid)
        for p in prods:
            if search.lower() in p.name.lower():
                st.markdown(f"**{p.name}** — R$ {p.price_retail:.2f} (Estoque: {p.stock})")
                if st.button("Adicionar", key=f"add_{p.id}"):
                    if p.stock <= 0:
                        st.error("Sem estoque")
                    else:
                        add_to_cart(p)
                        st.rerun()

    with col_receipt:
        total = 0.0
        for i, item in enumerate(st.session_state["cart"]):
            subtotal = item["price"] * item["qty"]
            total += subtotal
            st.write(f'{item["name"]} x{item["qty"]} — R$ {subtotal:.2f}')
            c1, c2, c3 = st.columns(3)
            if c1.button("➖", key=f"dec_{i}"):
                item["qty"] -= 1
                if item["qty"] <= 0:
                    st.session_state["cart"].pop(i)
                st.rerun()
            if c3.button("❌", key=f"del_{i}"):
                st.session_state["cart"].pop(i)
                st.rerun()

        st.markdown(f"## TOTAL: R$ {total:.2f}")

        payment = st.radio("Pagamento", ["PIX", "Dinheiro", "Cartão"], horizontal=True)

        if st.button("FINALIZAR VENDA", type="primary"):
            errors = []
            for item in st.session_state["cart"]:
                ok, msg = api.process_sale(
                    db,
                    item["id"],
                    item["qty"],
                    "varejo",
                    st.session_state["user_id"],
                    cid
                )
                if not ok:
                    errors.append(msg)

            if errors:
                for e in errors:
                    st.error(e)
            else:
                st.session_state["cart"] = []
                st.success("Venda concluída")

        if st.button("🧾 Imprimir Cupom"):
            pdf = generate_receipt_80mm(st.session_state["cart"], total, payment)
            st.download_button("Baixar Cupom", pdf, file_name="cupom.pdf")



# --- FINANCEIRO ATUALIZADO ---
elif choice == "💰 Fluxo Financeiro":
    st.title("Gestão Financeira Integrada")
    
    # Criação de abas para separar Relatórios de Cadastros
    tab_fechamento, tab_calendario = st.tabs(["📊 Fechamento de Caixa", "🗓️ Calendário Fiscal & Despesas"])

    # --- ABA 1: FECHAMENTO DE CAIXA ---
    with tab_fechamento:
        st.markdown("### Selecione o Período")
        
        # Filtros de Data
        c_date1, c_date2 = st.columns(2)
        with c_date1:
            dt_inicio = st.date_input("Data Início", datetime.now().replace(day=1))
        with c_date2:
            dt_fim = st.date_input("Data Fim", datetime.now())

        # Converter para datetime para passar para o serviço
        dt_start_full = datetime.combine(dt_inicio, datetime.min.time())
        dt_end_full = datetime.combine(dt_fim, datetime.max.time())

        if st.button("🔍 Gerar Fechamento"):
            # Busca dados filtrados
            df_vendas, df_despesas = api.get_financial_by_range(db, cid, dt_start_full, dt_end_full)
            
            # Cálculos
            total_entradas = df_vendas['price'].sum() if not df_vendas.empty else 0.0
            total_saidas = df_despesas['amount'].sum() if not df_despesas.empty else 0.0
            saldo = total_entradas - total_saidas

            # Cards de Resumo (Estilo CSS do usuário)
            col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
            col_kpi1.markdown(f"""
                <div class="fin-card-white" style="padding: 20px;">
                    <div class="fin-title">Total Entradas</div>
                    <div style="color: #10B981; font-size: 1.8rem; font-weight: 800;">€ {total_entradas:,.2f}</div>
                </div>""", unsafe_allow_html=True)
            
            col_kpi2.markdown(f"""
                <div class="fin-card-white" style="padding: 20px;">
                    <div class="fin-title">Total Saídas</div>
                    <div style="color: #FF4B4B; font-size: 1.8rem; font-weight: 800;">€ {total_saidas:,.2f}</div>
                </div>""", unsafe_allow_html=True)

            cor_saldo = "#10B981" if saldo >= 0 else "#FF4B4B"
            col_kpi3.markdown(f"""
                <div class="fin-card-white" style="padding: 20px; border: 2px solid {cor_saldo};">
                    <div class="fin-title">Saldo Líquido</div>
                    <div style="color: {cor_saldo}; font-size: 1.8rem; font-weight: 800;">€ {saldo:,.2f}</div>
                </div>""", unsafe_allow_html=True)

            st.divider()

            # Detalhamento
            col_det1, col_det2 = st.columns(2)
            
            with col_det1:
                st.subheader("📥 Detalhe de Entradas (Vendas)")
                if not df_vendas.empty:
                    # Tratamento visual da tabela
                    st.dataframe(
                        df_vendas[['date', 'product_name', 'quantity', 'price']].rename(columns={'date': 'Data', 'product_name': 'Produto', 'quantity': 'Qtd', 'price': 'Valor'}),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Nenhuma venda neste período.")

            with col_det2:
                st.subheader("📤 Detalhe de Saídas (Despesas)")
                if not df_despesas.empty:
                    st.dataframe(
                        df_despesas[['date', 'category', 'description', 'amount']].rename(columns={'date': 'Data', 'category': 'Categoria', 'description': 'Descrição', 'amount': 'Valor'}),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Nenhuma despesa neste período.")

    # --- ABA 2: CALENDÁRIO FISCAL (CADASTROS) ---
    with tab_calendario:
        c_form, c_list = st.columns([0.4, 0.6], gap="large")

        # Formulário de Cadastro
        with c_form:
            st.markdown('<div class="fin-card-purple">', unsafe_allow_html=True)
            st.markdown("### 📝 Nova Despesa")
            with st.form("form_despesa"):
                d_desc = st.text_input("Descrição", placeholder="Ex: Aluguel, Luz, Fornecedor X")
                d_valor = st.number_input("Valor (€)", min_value=0.0, format="%.2f")
                d_tipo = st.selectbox("Tipo de Despesa", ["Fixa (Recorrente)", "Variável (Extra)", "Impostos", "Pessoal"])
                d_data = st.date_input("Data de Vencimento/Pagamento", datetime.now())
                
                submitted = st.form_submit_button("💾 Salvar Despesa", use_container_width=True)
                if submitted:
                    if d_desc and d_valor > 0:
                        # Converte data para datetime completo
                        d_data_full = datetime.combine(d_data, datetime.now().time())
                        api.add_expense(db, cid, d_desc, d_valor, d_tipo, d_data_full)
                        st.success("Despesa lançada com sucesso!")
                        st.rerun()
                    else:
                        st.error("Preencha descrição e valor.")
            st.markdown('</div>', unsafe_allow_html=True)

        # Listagem Geral de Despesas (Futuras e Passadas)
        with c_list:
            st.subheader("📅 Histórico e Previsão de Contas")
            
            # Pega todas as despesas dos últimos 60 dias e próximos 30 dias
            d_start = datetime.now() - timedelta(days=60)
            d_end = datetime.now() + timedelta(days=30)
            _, df_all_expenses = api.get_financial_by_range(db, cid, d_start, d_end)
            
            if not df_all_expenses.empty:
                # Ordenar por data
                df_all_expenses['date'] = pd.to_datetime(df_all_expenses['date'])
                df_all_expenses = df_all_expenses.sort_values(by='date', ascending=False)
                
                # Exibir tabela interativa
                st.dataframe(
                    df_all_expenses[['date', 'category', 'description', 'amount']],
                    column_config={
                        "date": st.column_config.DateColumn("Data"),
                        "amount": st.column_config.NumberColumn("Valor (€)", format="€ %.2f"),
                        "category": "Tipo",
                        "description": "Descrição"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Nenhuma despesa registrada recentemente.")

# --- MÓDULO DE ESTOQUE ATUALIZADO ---
elif choice == "📦 Estoque":
    st.title("Gestão de Inventário Inteligente")
    
    # Busca dados atualizados
    prods = api.get_products(db, cid)
    
    # Prepara Dataframe
    data_list = []
    low_stock_count = 0
    for p in prods:
        status = "🟢 OK"
        if p.stock <= p.stock_min:
            status = "🔴 BAIXO"
            low_stock_count += 1
            
        data_list.append({
            "ID": p.id,
            "SKU": p.sku,
            "Produto": p.name,
            "Preço Venda": p.price_retail,
            "Estoque Atual": p.stock,
            "Mínimo": p.stock_min,
            "Status": status
        })
    df_estoque = pd.DataFrame(data_list)

    # Métricas de Topo
    m1, m2, m3 = st.columns(3)
    m1.metric("Total de Produtos", len(prods))
    m2.metric("Valor em Estoque (Estimado)", f"€ {sum([p.stock * p.price_wholesale for p in prods]):,.2f}")
    m3.metric("Alertas de Reposição", low_stock_count, delta=-low_stock_count if low_stock_count > 0 else 0, delta_color="inverse")

    st.divider()

    # ABAS: Visão Geral | Reposição | Novo Produto
    tab_visao, tab_repor, tab_novo = st.tabs(["📋 Visão Geral & Alertas", "➕ Repor Estoque", "✨ Novo Produto"])

    # --- ABA 1: VISÃO GERAL ---
    with tab_visao:
        if low_stock_count > 0:
            st.warning(f"⚠️ Atenção! Existem {low_stock_count} produtos com estoque abaixo do mínimo.")
        
        # Tabela com formatação visual
        st.dataframe(
            df_estoque,
            column_config={
                "Preço Venda": st.column_config.NumberColumn(format="€ %.2f"),
                "Estoque Atual": st.column_config.ProgressColumn(
                    "Nível de Estoque", 
                    format="%d", 
                    min_value=0, 
                    max_value=100, # Ajuste conforme sua média de estoque
                ),
            },
            use_container_width=True,
            hide_index=True
        )

    # --- ABA 2: REPOR ESTOQUE (ENTRADA) ---
    with tab_repor:
        c_r1, c_r2 = st.columns([1, 1])
    with c_r1:
        st.markdown("### 📥 Entrada de Mercadoria")
        st.info("Esta ação aumentará o estoque e lançará uma despesa no financeiro automaticamente.")

        prods = api.get_products(db, cid)

        if not prods:
            st.warning("Nenhum produto cadastrado. Cadastre um produto na aba ✨ Novo Produto para poder repor estoque.")
        else:
            with st.form("form_repor"):
                prod_options = {f"{p.sku} - {p.name} (Atual: {p.stock})": p.id for p in prods}

                selected_label = st.selectbox("Selecione o Produto", options=list(prod_options.keys()))
                selected_id = prod_options.get(selected_label)

                r_qty = st.number_input("Quantidade a Adicionar", min_value=1, step=1)
                r_cost = st.number_input(
                    "Custo Unitário de Compra (R$)",
                    min_value=0.01,
                    format="%.2f",
                    help="Quanto você pagou por cada unidade ao fornecedor?"
                )

                if st.form_submit_button("✅ Confirmar Entrada"):
                    ok, msg = api.restock_product(db, cid, selected_id, r_qty, r_cost)
                    if ok:
                        st.success("Estoque atualizado e custo lançado no Financeiro!")
                        st.rerun()
                    else:
                        st.error(msg)


    # --- ABA 3: CADASTRAR NOVO PRODUTO ---
    with tab_novo:
        st.markdown("### ✨ Cadastro de Produto")
        with st.form("form_novo_prod"):
            c_n1, c_n2 = st.columns(2)
            with c_n1:
                n_nome = st.text_input("Nome do Produto", placeholder="Ex: Capa iPhone 15")
                n_sku = st.text_input("Código SKU / Barras", placeholder="Ex: CAP-IP15-SIL")
            with c_n2:
                n_venda = st.number_input("Preço de Venda (€)", min_value=0.0)
                n_custo_base = st.number_input("Preço de Custo Base (Ref.)", min_value=0.0)
            
            n_min = st.number_input("Estoque Mínimo (Alerta)", min_value=1, value=5, help="O sistema avisará quando o estoque for menor que este número.")
            
            if st.form_submit_button("💾 Salvar Produto"):
                if n_nome and n_sku:
                    api.register_product(db, cid, n_nome, n_venda, n_custo_base, n_min, n_sku)
                    st.success(f"Produto {n_nome} cadastrado com sucesso!")
                    st.rerun()
                else:
                    st.error("Preencha o Nome e o SKU.")

