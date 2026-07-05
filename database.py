import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from schemas import OrderDetails

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_order(order_id: str) -> OrderDetails | None:
    """Fetch a single order from Postgres by order_id."""
    with SessionLocal() as session:
        result = session.execute(
            text("SELECT order_id, customer_name, status, total_amount, delivery_date, items FROM orders WHERE order_id = :order_id"),
            {"order_id": order_id.upper()}
        ).fetchone()

        if not result:
            return None

        return OrderDetails(
            order_id=result.order_id,
            customer_name=result.customer_name,
            status=result.status,
            total_amount=float(result.total_amount),
            delivery_date=str(result.delivery_date) if result.delivery_date else None,
            items=list(result.items)
        )

def get_all_orders() -> list[OrderDetails]:
    """Fetch all orders — used for listing/debugging."""
    with SessionLocal() as session:
        results = session.execute(
            text("SELECT order_id, customer_name, status, total_amount, delivery_date, items FROM orders")
        ).fetchall()

        return [
            OrderDetails(
                order_id=r.order_id,
                customer_name=r.customer_name,
                status=r.status,
                total_amount=float(r.total_amount),
                delivery_date=str(r.delivery_date) if r.delivery_date else None,
                items=list(r.items)
            )
            for r in results
        ]

def test_connection() -> bool:
    """Returns True if DB connection works."""
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False