import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.tools import tool
from schemas import RefundEligibility
from database import get_order

@tool("get_order_details", description="Get full details of a customer order by order ID. Use when asked about order status, items, delivery date, or customer info.")
def get_order_details(order_id: str) -> str:
    order = get_order(order_id.upper())
    if not order:
        return json.dumps({"error": f"Order {order_id} not found in the system."})
    return order.model_dump_json()

@tool("check_refund_eligibility", description="Check if an order is eligible for a refund. Use when asked about refunds, returns, or money back.")
def check_refund_eligibility(order_id: str) -> str:
    order = get_order(order_id.upper())
    if not order:
        return json.dumps({"error": f"Order {order_id} not found."})

    if order.status in ["Delivered", "Cancelled"]:
        result = RefundEligibility(
            order_id=order.order_id,
            eligible=True,
            reason=f"Order is {order.status} — eligible for refund",
            max_refund_amount=order.total_amount
        )
    elif order.status == "Shipped":
        result = RefundEligibility(
            order_id=order.order_id,
            eligible=False,
            reason="Order already shipped — cannot refund until delivered",
            max_refund_amount=0.0
        )
    else:
        result = RefundEligibility(
            order_id=order.order_id,
            eligible=False,
            reason=f"Order in '{order.status}' status — not eligible yet",
            max_refund_amount=0.0
        )
    return result.model_dump_json()