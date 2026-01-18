import streamlit as st
from database import get_db, engine, Base
import services as api
from models import User
from datetime import datetime
import base64

# ---------------- INIT ----------------
st.set_page_config(page_title="PeegFlow Pro", page_icon="⚡", layout="wide")
Base.metadata.create_all(bind=engine)

db = next(get_db())
api.create_initial_data(db)

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.update({
        "logged_in": False,
        "user_id": None,
        "company_id": None,
        "username": None,
        "role": None
    })

# ---------------- LOGIN ----------------
if not st.session_state["logged_in"]:
    st.title("PeegFlow Login")
    with st.form("login"):
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            user = api.authenticate(db, u, p)
            if user:
                st.session_state.update({
                    "logged_in": True,
                    "user_id": user.id,
                    "company_id": user.company_id,
                    "username": user.username,
                    "role": user.role
                })
                st.rerun()
            else:
                st.error("Credenciais inválidas")
    st.stop()

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.write(f"👤 {st.session_state['username']}")
    st.write(f"🔐 Perfil: {st.session_state['role']}")
    st.divider()

    menu = ["📊 Dashboard", "🛒 PDV"]

    if st.session_state["role"] == "admin":
        menu += ["👥 Usuários", "🔐 Trocar Senha"]

    choice = st.radio("Menu", menu)

    if st.button("Sair"):
        st.session_state.clear()
        st.rerun()

# ---------------- DASHBOARD ----------------
if choice == "📊 Dashboard":
    st.title("Dashboard")
    st.success("Sistema funcionando com permissões ✔")

# ---------------- PDV ----------------
elif choice == "🛒 PDV":
    st.title("Checkout (PDV)")
    st.info("Acesso permitido para admin e user")

# ---------------- USUÁRIOS (ADMIN) ----------------
elif choice == "👥 Usuários":
    st.title("Gestão de Usuários")

    users = api.list_users(db, st.session_state["company_id"])

    for u in users:
        col1, col2, col3 = st.columns([3,2,1])
        col1.write(u.username)
        col2.write(u.role)
        if u.username != "admin":
            if col3.button("🗑️", key=f"del{u.id}"):
                api.delete_user(db, u.id, st.session_state["company_id"])
                st.rerun()

    st.divider()
    st.subheader("Novo Usuário")
    with st.form("new_user"):
        nu = st.text_input("Usuário")
        np = st.text_input("Senha", type="password")
        nr = st.selectbox("Perfil", ["user", "admin"])
        if st.form_submit_button("Criar"):
            api.create_user(db, st.session_state["company_id"], nu, np, nr)
            st.success("Usuário criado")
            st.rerun()

# ---------------- TROCAR SENHA ----------------
elif choice == "🔐 Trocar Senha":
    st.title("Trocar Senha")
    with st.form("pwd"):
        p1 = st.text_input("Nova senha", type="password")
        p2 = st.text_input("Confirmar senha", type="password")
        if st.form_submit_button("Salvar"):
            if p1 == p2 and len(p1) >= 6:
                api.change_password(db, st.session_state["user_id"], p1)
                st.success("Senha atualizada")
            else:
                st.error("Senhas inválidas")

