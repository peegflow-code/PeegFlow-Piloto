import streamlit as st
from datetime import datetime
from database import get_db
import services as api

st.set_page_config(page_title="PeegFlow", layout="wide")

if "user" not in st.session_state:
    st.session_state.user = None


# ---------- LOGIN ----------

def login(db):
    st.title("🔐 Login")

    with st.form("login"):
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")

        if st.form_submit_button("Entrar"):
            user = api.authenticate_user(db, u, p)
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Credenciais inválidas")


def logout():
    st.session_state.user = None
    st.rerun()


# ---------- PÁGINAS ----------

def estoque(db):
    user = st.session_state.user
    cid = user.company_id

    st.title("📦 Estoque")

    prods = api.get_products(db, cid)
    st.dataframe([{
        "Produto": p.name,
        "SKU": p.sku,
        "Estoque": p.stock,
        "Mínimo": p.stock_min
    } for p in prods], use_container_width=True)

    if user.role != "admin":
        st.info("🔒 Somente administradores podem alterar o estoque.")
        return

    st.divider()
    st.subheader("➕ Novo Produto")

    with st.form("new_prod"):
        name = st.text_input("Nome")
        sku = st.text_input("SKU")
        price = st.number_input("Preço Venda", min_value=0.0)
        cost = st.number_input("Preço Custo", min_value=0.0)
        min_stock = st.number_input("Estoque mínimo", min_value=1, value=5)

        if st.form_submit_button("Salvar"):
            api.register_product(db, cid, name, price, cost, min_stock, sku)
            st.success("Produto cadastrado")
            st.rerun()


def financeiro(db):
    user = st.session_state.user

    if user.role != "admin":
        st.error("🔒 Acesso restrito ao administrador")
        return

    st.title("💰 Financeiro")

    start = st.date_input("Data início")
    end = st.date_input("Data fim")

    df_sales, df_exp = api.get_financial_by_range(
        db,
        user.company_id,
        datetime.combine(start, datetime.min.time()),
        datetime.combine(end, datetime.max.time())
    )

    st.subheader("Vendas")
    st.dataframe(df_sales, use_container_width=True)

    st.subheader("Despesas")
    st.dataframe(df_exp, use_container_width=True)


# ---------- APP ----------

def main():
    db = next(get_db())

    if not st.session_state.user:
        login(db)
        return

    with st.sidebar:
        st.write(f"👤 {st.session_state.user.username}")
        st.write(f"🔑 Perfil: {st.session_state.user.role}")
        page = st.radio("Menu", ["📦 Estoque", "💰 Financeiro", "🚪 Sair"])

    if page == "📦 Estoque":
        estoque(db)
    elif page == "💰 Financeiro":
        financeiro(db)
    elif page == "🚪 Sair":
        logout()


if __name__ == "__main__":
    main()
