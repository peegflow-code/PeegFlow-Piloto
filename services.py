# services.py
from sqlalchemy.orm import Session
from models import User, Company, Product, Sale, Expense
from datetime import datetime
import bcrypt
import pandas as pd
from sqlalchemy import func

# =========================
# 🔐 SEGURANÇA DE SENHA
# =========================

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# =========================
# 👤 AUTH
# =========================

def authenticate(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.password_hash):
        return user
    return None

# =========================
# 🚀 BOOTSTRAP INICIAL
# =========================

def create_initial_data(db: Session):
    """
    Bootstrap seguro:
    - cria empresa se não existir
    - cria admin se não existir
    - corrige hash antigo automaticamente (SHA256 → bcrypt)
    """

    # Empresa
    company = db.query(Company).filter(Company.id == 1).first()
    if not company:
        company = Company(
            id=1,
            name="Empresa Piloto",
            license_key="PEEGFLOW-001",
            is_active=True
        )
        db.add(company)
        db.commit()

    # Admin
    admin = db.query(User).filter(User.username == "admin").first()

    if not admin:
        # cria admin novo
        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            role="admin",
            company_id=company.id
        )
        db.add(admin)
        db.commit()

    else:
        # 🔁 garante que a senha esteja em bcrypt
        try:
            import bcrypt
            bcrypt.checkpw(b"test", admin.password_hash.encode())
        except Exception:
            # hash antigo → atualiza
            admin.password_hash = hash_password("admin123")
            db.commit()


# =========================
# 👥 CRUD DE USUÁRIOS
# =========================

def list_users(db: Session, company_id: int):
    return db.query(User).filter(User.company_id == company_id).all()

def create_user(db: Session, company_id: int, username: str, password: str, role: str):
    if db.query(User).filter(User.username == username).first():
        return False, "Usuário já existe"

    user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        company_id=company_id
    )
    db.add(user)
    db.commit()
    return True, "Usuário criado"

def change_password(db: Session, user_id: int, new_password: str):
    user = db.query(User).get(user_id)
    user.password_hash = hash_password(new_password)
    db.commit()

# =========================
# 🔐 PERMISSÕES
# =========================

def is_admin(user):
    return user.role in ["admin", "superadmin"]

# =========================
# 📦 PRODUTOS / VENDAS
# =========================

def get_products(db: Session, company_id: int):
    return db.query(Product).filter(Product.company_id == company_id).all()

def process_sale(db: Session, product_id: int, qty: int, kind: str, user_id: int, company_id: int):
    product = db.query(Product).filter(Product.id == product_id, Product.company_id == company_id).first()
    if not product or product.stock < qty:
        return False

    product.stock -= qty
    sale = Sale(
        product_id=product.id,
        quantity=qty,
        price=product.price_retail,
        kind=kind,
        user_id=user_id,
        company_id=company_id,
        date=datetime.now()
    )
    db.add(sale)
    db.commit()
    return True

# =========================
# 💰 FINANCEIRO
# =========================

def add_expense(db: Session, company_id: int, desc: str, amount: float, category: str, date: datetime):
    db.add(Expense(
        description=desc,
        amount=amount,
        category=category,
        date=date,
        company_id=company_id
    ))
    db.commit()

def get_financial_by_range(
    db: Session,
    company_id: int,
    start_date: datetime,
    end_date: datetime
):
    # Ajuste de datas
    if end_date.hour == 0 and end_date.minute == 0:
        end_date = end_date.replace(hour=23, minute=59, second=59)

    # --- VENDAS ---
    sales_q = (
        db.query(
            Sale.date.label("date"),
            Sale.quantity.label("quantity"),
            Sale.price.label("price"),
            Product.name.label("product_name")
        )
        .select_from(Sale)               # ✅ ANCORAGEM EXPLÍCITA
        .join(Product, Product.id == Sale.product_id)
        .filter(
            Sale.company_id == company_id,
            Sale.date >= start_date,
            Sale.date <= end_date
        )
    )

    # --- DESPESAS ---
    expenses_q = (
        db.query(
            Expense.date.label("date"),
            Expense.description.label("description"),
            Expense.category.label("category"),
            Expense.amount.label("amount")
        )
        .filter(
            Expense.company_id == company_id,
            Expense.date >= start_date,
            Expense.date <= end_date
        )
    )

    # Pandas
    df_sales = pd.read_sql(sales_q.statement, db.bind)
    df_expenses = pd.read_sql(expenses_q.statement, db.bind)

    return df_sales, df_expenses

def delete_product(db: Session, company_id: int, product_id: int):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.company_id == company_id
    ).first()

    if not product:
        return False, "Produto não encontrado"

    # Verificação de segurança: não excluir se houver vendas
    has_sales = db.query(Sale).filter(Sale.product_id == product_id).first()
    if has_sales:
        return False, "Produto possui vendas registradas"

    db.delete(product)
    db.commit()
    return True, "Produto excluído com sucesso"

