# services.py
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Tuple, Optional

import pandas as pd
from sqlalchemy.orm import Session

from models import User, Company, Product, Sale, Expense


# =========================
# 🔐 SENHAS (bcrypt com fallback)
# =========================

def _bcrypt_available() -> bool:
    try:
        import bcrypt  # noqa
        return True
    except Exception:
        return False


def hash_password(password: str) -> str:
    """
    Retorna hash.
    - Preferencial: bcrypt (mais seguro)
    - Fallback: sha256 (não ideal, mas evita quebrar o deploy)
    """
    if _bcrypt_available():
        import bcrypt
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False

    # Se parece bcrypt ($2b$, $2a$, $2y$)
    if hashed.startswith("$2"):
        try:
            import bcrypt
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    # Fallback sha256
    return hashlib.sha256(password.encode("utf-8")).hexdigest() == hashed


# =========================
# 👤 AUTH / BOOTSTRAP
# =========================

def authenticate(db: Session, username: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.password_hash):
        return user
    return None


def create_initial_data(db: Session) -> None:
    """
    Cria uma empresa e um admin padrão se o banco estiver vazio.
    Compatível com seu models.py atual (Company só tem name).
    """
    # Se já existe algum usuário, não mexe
    exists_user = db.query(User.id).first()
    if exists_user:
        return

    # Cria empresa base
    company = db.query(Company).first()
    if not company:
        company = Company(name="Empresa Principal")
        db.add(company)
        db.commit()
        db.refresh(company)

    # Cria admin
    admin = User(
        username="admin",
        password_hash=hash_password("admin123"),
        role="admin",
        company_id=company.id
    )
    db.add(admin)
    db.commit()


# =========================
# 📦 PRODUTOS / ESTOQUE
# =========================

def get_products(db: Session, company_id: int):
    return db.query(Product).filter(Product.company_id == company_id).all()


def register_product(
    db: Session,
    company_id: int,
    name: str,
    price_retail: float,
    price_wholesale: float,
    stock_min: int,
    sku: str
) -> Tuple[bool, str]:
    if not name or not sku:
        return False, "Nome e SKU são obrigatórios"

    # Evita SKU duplicado por empresa
    exists = db.query(Product).filter(
        Product.company_id == company_id,
        Product.sku == sku
    ).first()
    if exists:
        return False, "Já existe um produto com esse SKU"

    prod = Product(
        company_id=company_id,
        name=name,
        sku=sku,
        price_retail=float(price_retail),
        price_wholesale=float(price_wholesale),
        stock=0,
        stock_min=int(stock_min)
    )
    db.add(prod)
    db.commit()
    return True, "Produto cadastrado"


def restock_product(db: Session, company_id: int, product_id: int, qty: int, cost_unit: float) -> Tuple[bool, str]:
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.company_id == company_id
    ).first()
    if not product:
        return False, "Produto não encontrado"

    if qty <= 0:
        return False, "Quantidade inválida"

    product.stock = int(product.stock or 0) + int(qty)

    # Registra despesa (CMV)
    total_cost = float(qty) * float(cost_unit)
    desc = f"Reposição Estoque: {product.name} ({qty}x R$ {cost_unit:.2f})"

    exp = Expense(
        company_id=company_id,
        description=desc,
        category="CMV",
        amount=total_cost,
        date=datetime.utcnow()
    )
    db.add(exp)
    db.commit()
    return True, "Estoque atualizado"


def delete_product(db: Session, company_id: int, product_id: int) -> Tuple[bool, str]:
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.company_id == company_id
    ).first()
    if not product:
        return False, "Produto não encontrado"

    # Segurança: não excluir se já tem venda
    has_sale = db.query(Sale.id).filter(
        Sale.company_id == company_id,
        Sale.product_id == product_id
    ).first()
    if has_sale:
        return False, "Não é possível excluir: produto já tem vendas registradas"

    db.delete(product)
    db.commit()
    return True, "Produto excluído"


# =========================
# 🛒 VENDAS (PDV) - valida estoque por empresa
# =========================

def process_sale(
    db: Session,
    product_id: int,
    qty: int,
    kind: str,
    user_id: int,
    company_id: int
) -> Tuple[bool, str]:
    qty = int(qty)

    product = db.query(Product).filter(
        Product.id == product_id,
        Product.company_id == company_id
    ).first()

    if not product:
        return False, "Produto não encontrado"

    if qty <= 0:
        return False, "Quantidade inválida"

    stock_now = int(product.stock or 0)
    if stock_now < qty:
        return False, f"Estoque insuficiente ({stock_now} disponível)"

    product.stock = stock_now - qty

    sale = Sale(
        company_id=company_id,
        product_id=product_id,
        quantity=qty,
        price=float(product.price_retail or 0.0),
        user_id=user_id,
        date=datetime.utcnow()
    )

    db.add(sale)
    db.commit()
    return True, "Venda concluída"


# =========================
# 💰 FINANCEIRO
# =========================

def add_expense(db: Session, company_id: int, desc: str, amount: float, category: str, date: datetime) -> Tuple[bool, str]:
    if not desc or float(amount) <= 0:
        return False, "Preencha descrição e valor"

    exp = Expense(
        company_id=company_id,
        description=desc,
        category=category,
        amount=float(amount),
        date=date
    )
    db.add(exp)
    db.commit()
    return True, "Despesa lançada"


def get_financial_by_range(db: Session, company_id: int, start_date: datetime, end_date: datetime):
    """
    Como seu models.py não tem FK/relationship em Sale->Product,
    evitamos join ORM e montamos o dataframe com lookup de produtos.
    """
    sales = db.query(Sale).filter(
        Sale.company_id == company_id,
        Sale.date >= start_date,
        Sale.date <= end_date
    ).all()

    expenses = db.query(Expense).filter(
        Expense.company_id == company_id,
        Expense.date >= start_date,
        Expense.date <= end_date
    ).all()

    # Mapa de produto_id -> nome (para preencher product_name)
    prods = db.query(Product.id, Product.name).filter(Product.company_id == company_id).all()
    prod_map = {pid: name for pid, name in prods}

    df_sales = pd.DataFrame([{
        "date": s.date,
        "quantity": s.quantity,
        "price": s.price,
        "product_name": prod_map.get(s.product_id, f"Produto #{s.product_id}")
    } for s in sales])

    df_expenses = pd.DataFrame([{
        "date": e.date,
        "description": e.description,
        "category": e.category,
        "amount": e.amount
    } for e in expenses])

    # garante colunas mesmo vazio
    if df_sales.empty:
        df_sales = pd.DataFrame(columns=["date", "quantity", "price", "product_name"])
    if df_expenses.empty:
        df_expenses = pd.DataFrame(columns=["date", "description", "category", "amount"])

    return df_sales, df_expenses


