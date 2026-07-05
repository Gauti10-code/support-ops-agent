import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.tools import tool
from schemas import RefundResult
from database import get_order

@tool("issue_refund", description="Actually issue and process a refund for an order. Use ONLY when the customer explicitly asks to issue or process a refund, not just check eligibility.")
def issue_refund(order_id: str) -> str:
    order = get_order(order_id.upper())
    if not order:
        return json.dumps({"error": f"Order {order_id} not found."})

    if order.status not in ["Delivered", "Cancelled"]:
        result = RefundResult(
            order_id=order.order_id,
            status="failed",
            amount_refunded=0.0,
            message=f"Cannot refund — order status is {order.status}"
        )
        return result.model_dump_json()

    # In production: hit payment gateway API here
    result = RefundResult(
        order_id=order.order_id,
        status="success",
        amount_refunded=order.total_amount,
        message=f"Refund of ₹{order.total_amount} processed for {order.customer_name}"
    )
    print(f"⚠️ REFUND EXECUTED: ₹{order.total_amount} for {order.order_id}")
    return result.model_dump_json()