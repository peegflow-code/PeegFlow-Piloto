import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_db, engine, Base
import services as api
from models import User, Company, Product, Sale, Expense
from datetime import datetime, timedelta
import base64
import io
from fpdf import FPDF
import textwrap

# -------------------------
# Helpers
# -------------------------
def brl(v: float) -> str:
    try:
        # Formato brasileiro simples (sem locale)
        s = f"{float(v):,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"
    except Exception:
        return "R$ 0,00"

def update_product_db(db, company_id: int, product_id: int, name: str, sku: str,
                      price_retail: float, price_wholesale: float, stock_min: int):
    prod = db.query(Product).filter(Product.id == product_id, Product.company_id == company_id).first()
    if not prod:
        return False, "Produto não encontrado."

    # SKU não pode repetir dentro da mesma empresa (se você quiser permitir duplicado, remova isso)
    if sku:
        conflict = db.query(Product).filter(
            Product.company_id == company_id,
            Product.sku == sku,
            Product.id != product_id
        ).first()
        if conflict:
            return False, "Já existe outro produto com esse SKU."

    prod.name = name
    prod.sku = sku
    prod.price_retail = float(price_retail)
    prod.price_wholesale = float(price_wholesale)
    prod.stock_min = int(stock_min)

    db.commit()
    return True, "Produto atualizado com sucesso."

def delete_product_db(db, company_id: int, product_id: int):
    prod = db.query(Product).filter(Product.id == product_id, Product.company_id == company_id).first()
    if not prod:
        return False, "Produto não encontrado."

    # Evita quebrar histórico de vendas
    has_sales = db.query(Sale).filter(Sale.company_id == company_id, Sale.product_id == product_id).first()
    if has_sales:
        return False, "Não é possível excluir: existem vendas registradas para este produto."

    db.delete(prod)
    db.commit()
    return True, "Produto excluído."

# -------------------------
# Configurações iniciais
# -------------------------
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

# --- FUNÇÃO AUXILIAR PARA IMAGEM ---
def get_img_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return None

# --- LÓGICA DE LOGIN ---
if not st.session_state['logged_in']:
    _, col_central, _ = st.columns([1, 1.2, 1])
    with col_central:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)

        img_b64 = get_img_as_base64("logo_peegflow.jpg")
        html_header = f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 20px;">
            <img src="data:image/jpeg;base64,{img_b64}" style="width: 80px; margin-bottom: 10px; border-radius: 50%;">
            <h2 style="text-align: center; color: #1B2559; margin: 0; font-size: 2rem;">Bem-vindo ao PeegFlow</h2>
            <p style="text-align: center; color: #A3AED0; margin-top: 10px; font-size: 1rem;">Insira os seus dados para aceder ao painel.</p>
        </div>
        """
        st.markdown(html_header, unsafe_allow_html=True)

        with st.form("login_form"):
            u = st.text_input("USUÁRIO", placeholder="Ex: admin")
            p = st.text_input("SENHA", type="password", placeholder="••••••••")
            st.write("")

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
    if st.button("Sair"):
        st.session_state.clear()
        st.rerun()

# -------------------------
# DASHBOARD
# -------------------------
if choice == "📊 Dashboard":
    st.title("Dashboard Executivo")
    st.markdown("Visão estratégica do seu negócio em tempo real.")

    end_date = datetime.now()
    start_date_current = end_date - timedelta(days=30)
    start_date_previous = start_date_current - timedelta(days=30)

    df_vendas_atual, df_desp_atual = api.get_financial_by_range(db, cid, start_date_current, end_date)
    df_vendas_prev, df_desp_prev = api.get_financial_by_range(db, cid, start_date_previous, start_date_current)

    rec_atual = df_vendas_atual['price'].sum() if not df_vendas_atual.empty else 0
    rec_prev = df_vendas_prev['price'].sum() if not df_vendas_prev.empty else 0
    delta_rec = rec_atual - rec_prev

    lucro_atual = rec_atual - (df_desp_atual['amount'].sum() if not df_desp_atual.empty else 0)
    ticket_medio = df_vendas_atual['price'].mean() if not df_vendas_atual.empty else 0
    qtd_vendas = len(df_vendas_atual)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Faturamento (30d)", brl(rec_atual), f"{brl(delta_rec)} vs mês ant.", delta_color="normal")
    col2.metric("Lucro Líquido Est.", brl(lucro_atual),
                "Margem: " + (f"{lucro_atual/rec_atual:.1%}" if rec_atual > 0 else "0%"),
                delta_color="off")
    col3.metric("Ticket Médio", brl(ticket_medio), help="Valor médio gasto por cliente por compra")
    col4.metric("Total Vendas", f"{qtd_vendas}", f"{qtd_vendas - len(df_vendas_prev)} vs mês ant.")

    st.divider()

    col_g1, col_g2 = st.columns([0.65, 0.35], gap="large")

    with col_g1:
        st.subheader("📈 Mapa de Calor de Vendas")
        if not df_vendas_atual.empty:
            df_heat = df_vendas_atual.copy()
            df_heat['date'] = pd.to_datetime(df_heat['date'])
            df_heat['hour'] = df_heat['date'].dt.hour
            df_heat['weekday'] = df_heat['date'].dt.day_name()

            heat_data = df_heat.groupby(['weekday', 'hour'])['price'].sum().reset_index()
            days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

            fig_heat = px.density_heatmap(
                heat_data,
                x='hour',
                y='weekday',
                z='price',
                color_continuous_scale='Viridis',
                category_orders={"weekday": days_order},
                title="Intensidade de Vendas (Dia x Hora)",
                labels={'weekday': 'Dia', 'hour': 'Hora', 'price': 'Vendas (R$)'}
            )
            fig_heat.update_layout(xaxis_dtick=1)
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.info("Sem dados suficientes para gerar o mapa de calor.")

    with col_g2:
        st.subheader("🏆 Top Produtos")
        if not df_vendas_atual.empty:
            df_top = df_vendas_atual.groupby('product_name')['price'].sum().reset_index()
            df_top = df_top.sort_values(by='price', ascending=True).tail(5)

            fig_bar = px.bar(
                df_top,
                x='price',
                y='product_name',
                orientation='h',
                text_auto='.2s',
                title="Campeões de Receita",
                color='price',
                color_continuous_scale=['#A3AED0', '#6366F1']
            )
            fig_bar.update_layout(showlegend=False, xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Sem vendas registradas.")

    st.subheader("Evolução Diária (Vendas vs Custos)")
    if not df_vendas_atual.empty:
        daily_sales = df_vendas_atual.groupby(df_vendas_atual['date'].dt.date)['price'].sum().reset_index()
        daily_sales['Tipo'] = 'Receita'
        daily_sales.rename(columns={'price': 'Valor'}, inplace=True)

        daily_exp = df_desp_atual.groupby(df_desp_atual['date'].dt.date)['amount'].sum().reset_index()
        daily_exp['Tipo'] = 'Despesa'
        daily_exp.rename(columns={'amount': 'Valor'}, inplace=True)

        df_chart = pd.concat([daily_sales, daily_exp])

        fig_evol = px.area(
            df_chart,
            x='date',
            y='Valor',
            color='Tipo',
            color_discrete_map={'Receita': '#10B981', 'Despesa': '#FF4B4B'},
            title="Comparativo Diário"
        )
        st.plotly_chart(fig_evol, use_container_width=True)

# -------------------------
# PDV (igual ao seu atual)
# -------------------------
def add_to_cart(product, qty: int):
    cart = st.session_state["cart"]

    qty = int(qty)
    if qty <= 0:
        return

    # soma automaticamente se já existir
    for item in cart:
        if item["id"] == product.id:
            item["qty"] = int(item.get("qty", 0)) + qty
            return

    cart.append({
        "id": product.id,
        "name": product.name,
        "price": float(product.price_retail),
        "qty": qty
    })


def generate_receipt_80mm(cart, total, payment):
    pdf = FPDF("P", "mm", (80, 200))
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=5)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 6, "PEEGFLOW", ln=True, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "CUPOM NAO FISCAL", ln=True, align="C")
    pdf.ln(3)

    for item in cart:
        name = (item.get("name") or "")[:32]
        qty = int(item.get("qty", 1))
        price = float(item.get("price", 0.0))

        pdf.set_font("Helvetica", "B", 9)
        pdf.multi_cell(0, 4, name)

        pdf.set_font("Helvetica", "", 9)
        pdf.cell(
            0, 5,
            f'{qty} x R$ {price:.2f} = R$ {(price * qty):.2f}',
            ln=True
        )

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 6, f"TOTAL: R$ {total:.2f}", ln=True)

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, f"Pagamento: {payment}", ln=True)
    pdf.cell(0, 5, datetime.now().strftime("%d/%m/%Y %H:%M"), ln=True)

    # ✅ jeito correto: gerar bytes
    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    buffer = io.BytesIO(pdf_bytes)
    buffer.seek(0)
    return buffer

# --- PDV (Checkout) COMPLETO ---
if choice == "🛒 Checkout (PDV)":
    st.title("Ponto de Venda")

    if "cart" not in st.session_state:
        st.session_state["cart"] = []

    if "discount_type" not in st.session_state:
        st.session_state["discount_type"] = "R$"

    if "discount_value" not in st.session_state:
        st.session_state["discount_value"] = 0.0

    if "last_receipt" not in st.session_state:
        st.session_state["last_receipt"] = None

    col_prod, col_receipt = st.columns([0.6, 0.4], gap="large")

    # ---------------- PRODUTOS ----------------
    with col_prod:
        search = st.text_input("🔍 Pesquisar produto ou código de barras...")
        prods = api.get_products(db, cid)

        filtered = [
            p for p in prods
            if search.lower() in (p.name or "").lower()
            or search.lower() in (p.sku or "").lower()
        ]

        p_cols = st.columns(3)
        for i, p in enumerate(filtered):
            with p_cols[i % 3]:
                st.markdown(f"""
                <div style="background:white;padding:20px;border-radius:15px;border:1px solid #E0E5F2;text-align:center;">
                    <div style="font-size:2rem;">📦</div>
                    <div style="font-weight:700;">{p.name}</div>
                    <div style="color:#6366F1;font-weight:800;">{brl(p.price_retail)}</div>
                    <div style="font-size:0.85rem;color:#64748B;">Estoque: {p.stock}</div>
                </div>
                """, unsafe_allow_html=True)

                qty = st.number_input(
                    "Qtd",
                    min_value=1,
                    step=1,
                    value=1,
                    key=f"pdv_qty_{p.id}"
                )

                if st.button("Adicionar", key=f"add_{p.id}", use_container_width=True):
                    if qty > p.stock:
                        st.error("Estoque insuficiente")
                    else:
                        add_to_cart(p, qty)
                        st.rerun()

   # ---------------- CUPOM ----------------
with col_receipt:
    receipt_html = '<div class="receipt-panel">'
    receipt_html += f'<div class="receipt-title">CUPOM #{datetime.now().strftime("%H%M")}</div>'

    subtotal = 0.0

    # ---------- ITENS ----------
    for item in st.session_state["cart"]:
        price = float(item.get("price", 0))
        qty = int(item.get("qty", 1))
        line_total = price * qty
        subtotal += line_total

        receipt_html += f"""
        <div class="receipt-item">
            <span>{item.get("name","")} (x{qty})</span>
            <span>{brl(line_total)}</span>
        </div>
        """

        # TOTALIZAÇÃO (SEM INDENTAÇÃO = MUITO IMPORTANTE)
        receipt_html += f"""
<div class="receipt-total-section">
  <div class="receipt-item">
    <span style="color:#A3AED0;">Subtotal</span>
    <span>{brl(subtotal)}</span>
  </div>

  <div class="receipt-item">
    <span style="color:#A3AED0;">Desconto</span>
    <span>- {brl(discount_amount)}</span>
  </div>

  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:10px;">
    <span style="color:#A3AED0;font-weight:700;font-size:0.9rem;">TOTAL</span>
    <span class="total-value">{brl(total)}</span>
  </div>
</div>
</div>
"""

        st.markdown(receipt_html, unsafe_allow_html=True)


          # ---------- DESCONTO ----------
st.markdown("### 🏷️ Desconto")

d1, d2 = st.columns(2)

with d1:
    st.session_state["discount_type"] = st.selectbox(
        "Tipo",
        ["R$", "%"],
        key="disc_type"
    )

with d2:
    st.session_state["discount_value"] = st.number_input(
        "Valor",
        min_value=0.0,
        step=1.0,
        key="disc_val"
    )

# cálculo do desconto
if st.session_state["discount_type"] == "%":
    discount_amount = subtotal * (st.session_state["discount_value"] / 100)
else:
    discount_amount = st.session_state["discount_value"]

discount_amount = min(discount_amount, subtotal)
total = subtotal - discount_amount

receipt_html += f"""
<div class="receipt-total-section">
  <div class="receipt-item">
    <span>Subtotal</span>
    <span>{brl(subtotal)}</span>
  </div>
  <div class="receipt-item">
    <span>Desconto</span>
    <span>- {brl(discount_amount)}</span>
  </div>
  <div style="display:flex;justify-content:space-between;margin-top:10px;">
    <strong>TOTAL</strong>
    <strong>{brl(total)}</strong>
  </div>
</div>
</div>
"""

st.markdown(receipt_html, unsafe_allow_html=True)

            # -------- CONTROLE DE ITENS --------
            st.subheader("Itens no Cupom")
            for idx in range(len(st.session_state["cart"]) - 1, -1, -1):
                item = st.session_state["cart"][idx]
                c1, c2, c3, c4, c5 = st.columns([5, 2, 2, 2, 2])

                c1.write(item["name"])
                c2.write(f'Qtd: {item["qty"]}')

                if c3.button("➕", key=f"inc_{idx}"):
                    item["qty"] += 1
                    st.rerun()

                if c4.button("➖", key=f"dec_{idx}"):
                    item["qty"] -= 1
                    if item["qty"] <= 0:
                        st.session_state["cart"].pop(idx)
                    st.rerun()

                if c5.button("❌", key=f"del_{idx}"):
                    st.session_state["cart"].pop(idx)
                    st.rerun()

            payment = st.radio("Pagamento", ["PIX", "Dinheiro", "Cartão"], horizontal=True)

            # -------- FINALIZAR VENDA --------
            if st.button("FINALIZAR VENDA", type="primary", use_container_width=True):
                for item in st.session_state["cart"]:
                    api.process_sale(
                        db,
                        item["id"],
                        item["qty"],
                        "varejo",
                        st.session_state["user_id"],
                        cid
                    )

                st.session_state["last_receipt"] = {
                    "cart": [dict(x) for x in st.session_state["cart"]],
                    "total": total,
                    "subtotal": subtotal,
                    "discount_amount": discount_amount,
                    "payment": payment
                }

                st.session_state["cart"] = []
                st.success("Venda concluída!")
                st.rerun()

            # -------- IMPRIMIR ÚLTIMO CUPOM --------
            if st.session_state["last_receipt"]:
                if st.button("🧾 Imprimir Último Cupom", use_container_width=True):
                    last = st.session_state["last_receipt"]
                    pdf = generate_receipt_80mm(
                        last["cart"],
                        last["total"],
                        last["payment"],
                        discount_amount=last["discount_amount"],
                        subtotal=last["subtotal"]
                    )
                    st.download_button(
                        "📥 Baixar Cupom (80mm)",
                        pdf,
                        file_name="cupom_ultimo.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )

            if st.button("🗑️ Limpar Carrinho", use_container_width=True):
                st.session_state["cart"] = []
                st.rerun()


# -------------------------
# FINANCEIRO (R$)
# -------------------------
elif choice == "💰 Fluxo Financeiro":
    st.title("Gestão Financeira Integrada")

    tab_fechamento, tab_calendario = st.tabs(["📊 Fechamento de Caixa", "🗓️ Calendário Fiscal & Despesas"])

    with tab_fechamento:
        st.markdown("### Selecione o Período")

        c_date1, c_date2 = st.columns(2)
        with c_date1:
            dt_inicio = st.date_input("Data Início", datetime.now().replace(day=1))
        with c_date2:
            dt_fim = st.date_input("Data Fim", datetime.now())

        dt_start_full = datetime.combine(dt_inicio, datetime.min.time())
        dt_end_full = datetime.combine(dt_fim, datetime.max.time())

        if st.button("🔍 Gerar Fechamento"):
            df_vendas, df_despesas = api.get_financial_by_range(db, cid, dt_start_full, dt_end_full)

            total_entradas = df_vendas['price'].sum() if not df_vendas.empty else 0.0
            total_saidas = df_despesas['amount'].sum() if not df_despesas.empty else 0.0
            saldo = total_entradas - total_saidas

            col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
            col_kpi1.markdown(f"""
                <div class="fin-card-white" style="padding: 20px;">
                    <div class="fin-title">Total Entradas</div>
                    <div style="color: #10B981; font-size: 1.8rem; font-weight: 800;">{brl(total_entradas)}</div>
                </div>""", unsafe_allow_html=True)

            col_kpi2.markdown(f"""
                <div class="fin-card-white" style="padding: 20px;">
                    <div class="fin-title">Total Saídas</div>
                    <div style="color: #FF4B4B; font-size: 1.8rem; font-weight: 800;">{brl(total_saidas)}</div>
                </div>""", unsafe_allow_html=True)

            cor_saldo = "#10B981" if saldo >= 0 else "#FF4B4B"
            col_kpi3.markdown(f"""
                <div class="fin-card-white" style="padding: 20px; border: 2px solid {cor_saldo};">
                    <div class="fin-title">Saldo Líquido</div>
                    <div style="color: {cor_saldo}; font-size: 1.8rem; font-weight: 800;">{brl(saldo)}</div>
                </div>""", unsafe_allow_html=True)

            st.divider()

            col_det1, col_det2 = st.columns(2)

            with col_det1:
                st.subheader("📥 Detalhe de Entradas (Vendas)")
                if not df_vendas.empty:
                    st.dataframe(
                        df_vendas[['date', 'product_name', 'quantity', 'price']].rename(
                            columns={'date': 'Data', 'product_name': 'Produto', 'quantity': 'Qtd', 'price': 'Valor (R$)'}
                        ),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Nenhuma venda neste período.")

            with col_det2:
                st.subheader("📤 Detalhe de Saídas (Despesas)")
                if not df_despesas.empty:
                    st.dataframe(
                        df_despesas[['date', 'category', 'description', 'amount']].rename(
                            columns={'date': 'Data', 'category': 'Categoria', 'description': 'Descrição', 'amount': 'Valor (R$)'}
                        ),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("Nenhuma despesa neste período.")

    with tab_calendario:
        c_form, c_list = st.columns([0.4, 0.6], gap="large")

        with c_form:
            st.markdown('<div class="fin-card-purple">', unsafe_allow_html=True)
            st.markdown("### 📝 Nova Despesa")
            with st.form("form_despesa"):
                d_desc = st.text_input("Descrição", placeholder="Ex: Aluguel, Luz, Fornecedor X")
                d_valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
                d_tipo = st.selectbox("Tipo de Despesa", ["Fixa (Recorrente)", "Variável (Extra)", "Impostos", "Pessoal"])
                d_data = st.date_input("Data de Vencimento/Pagamento", datetime.now())

                submitted = st.form_submit_button("💾 Salvar Despesa", use_container_width=True)
                if submitted:
                    if d_desc and d_valor > 0:
                        d_data_full = datetime.combine(d_data, datetime.now().time())
                        api.add_expense(db, cid, d_desc, d_valor, d_tipo, d_data_full)
                        st.success("Despesa lançada com sucesso!")
                        st.rerun()
                    else:
                        st.error("Preencha descrição e valor.")
            st.markdown('</div>', unsafe_allow_html=True)

        with c_list:
            st.subheader("📅 Histórico e Previsão de Contas")

            d_start = datetime.now() - timedelta(days=60)
            d_end = datetime.now() + timedelta(days=30)
            _, df_all_expenses = api.get_financial_by_range(db, cid, d_start, d_end)

            if not df_all_expenses.empty:
                df_all_expenses['date'] = pd.to_datetime(df_all_expenses['date'])
                df_all_expenses = df_all_expenses.sort_values(by='date', ascending=False)

                st.dataframe(
                    df_all_expenses[['date', 'category', 'description', 'amount']],
                    column_config={
                        "date": st.column_config.DateColumn("Data"),
                        "amount": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
                        "category": "Tipo",
                        "description": "Descrição"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Nenhuma despesa registrada recentemente.")

# -------------------------
# ESTOQUE (R$ + editar/excluir)
# -------------------------
elif choice == "📦 Estoque":
    st.title("Gestão de Inventário Inteligente")

    prods = api.get_products(db, cid)

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
            "Preço Venda (R$)": p.price_retail,
            "Estoque Atual": p.stock,
            "Mínimo": p.stock_min,
            "Status": status
        })
    df_estoque = pd.DataFrame(data_list)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total de Produtos", len(prods))
    m2.metric("Valor em Estoque (Estimado)", brl(sum([p.stock * p.price_wholesale for p in prods]) if prods else 0.0))
    m3.metric("Alertas de Reposição", low_stock_count, delta=-low_stock_count if low_stock_count > 0 else 0, delta_color="inverse")

    st.divider()

    tab_visao, tab_repor, tab_novo, tab_gerenciar = st.tabs(
        ["📋 Visão Geral & Alertas", "➕ Repor Estoque", "✨ Novo Produto", "🛠️ Editar / Excluir"]
    )

    with tab_visao:
        if low_stock_count > 0:
            st.warning(f"⚠️ Atenção! Existem {low_stock_count} produtos com estoque abaixo do mínimo.")

        st.dataframe(
            df_estoque,
            column_config={
                "Preço Venda (R$)": st.column_config.NumberColumn(format="R$ %.2f"),
                "Estoque Atual": st.column_config.ProgressColumn(
                    "Nível de Estoque",
                    format="%d",
                    min_value=0,
                    max_value=100,
                ),
            },
            use_container_width=True,
            hide_index=True
        )

    # ✅ corrigido: tudo dentro do tab_repor
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

    with tab_novo:
        st.markdown("### ✨ Cadastro de Produto")
        with st.form("form_novo_prod"):
            c_n1, c_n2 = st.columns(2)
            with c_n1:
                n_nome = st.text_input("Nome do Produto", placeholder="Ex: Capa iPhone 15")
                n_sku = st.text_input("Código SKU / Barras", placeholder="Ex: CAP-IP15-SIL")
            with c_n2:
                n_venda = st.number_input("Preço de Venda (R$)", min_value=0.0)
                n_custo_base = st.number_input("Preço de Custo Base (R$)", min_value=0.0)

            n_min = st.number_input("Estoque Mínimo (Alerta)", min_value=1, value=5,
                                    help="O sistema avisará quando o estoque for menor que este número.")

            if st.form_submit_button("💾 Salvar Produto"):
                if n_nome and n_sku:
                    api.register_product(db, cid, n_nome, n_venda, n_custo_base, n_min, n_sku)
                    st.success(f"Produto {n_nome} cadastrado com sucesso!")
                    st.rerun()
                else:
                    st.error("Preencha o Nome e o SKU.")

    with tab_gerenciar:
        st.markdown("### 🛠️ Editar / Excluir Produto")

        prods = api.get_products(db, cid)
        if not prods:
            st.info("Cadastre um produto primeiro para editar ou excluir.")
        else:
            options = {f"{p.sku} — {p.name} (ID {p.id})": p for p in prods}
            label = st.selectbox("Selecione um produto", list(options.keys()))
            prod = options[label]

            st.markdown("#### ✏️ Editar")
            with st.form("form_edit_prod"):
                c1, c2 = st.columns(2)
                with c1:
                    e_name = st.text_input("Nome", value=prod.name or "")
                    e_sku = st.text_input("SKU", value=prod.sku or "")
                    e_min = st.number_input("Estoque mínimo", min_value=1, value=int(prod.stock_min or 1))
                with c2:
                    e_retail = st.number_input("Preço venda (R$)", min_value=0.0, value=float(prod.price_retail or 0.0))
                    e_wholesale = st.number_input("Preço custo (R$)", min_value=0.0, value=float(prod.price_wholesale or 0.0))
                    st.write(f"Estoque atual: **{prod.stock}**")

                if st.form_submit_button("💾 Salvar alterações", use_container_width=True):
                    ok, msg = update_product_db(db, cid, prod.id, e_name, e_sku, e_retail, e_wholesale, e_min)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

            st.divider()

            st.markdown("#### 🗑️ Excluir")
            st.warning("Exclusão é permanente. Se houver vendas desse produto, o sistema bloqueia para não perder histórico.")
            confirm = st.checkbox("Confirmo que quero excluir este produto", value=False)

            if st.button("🗑️ Excluir produto", type="primary", use_container_width=True, disabled=not confirm):
                ok, msg = delete_product_db(db, cid, prod.id)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


