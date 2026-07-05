from tools.order_tools import get_order_details, check_refund_eligibility
from tools.refund_tool import issue_refund
from tools.rag_tool import search_policy_docs

print("=== ORDER DETAILS ===")
print(get_order_details.invoke({"order_id": "ORD-001"}))
print(get_order_details.invoke({"order_id": "ORD-999"}))

print("\n=== REFUND ELIGIBILITY ===")
print(check_refund_eligibility.invoke({"order_id": "ORD-001"}))  # Delivered → eligible
print(check_refund_eligibility.invoke({"order_id": "ORD-002"}))  # Pending → not eligible
print(check_refund_eligibility.invoke({"order_id": "ORD-004"}))  # Shipped → not eligible

print("\n=== ISSUE REFUND ===")
print(issue_refund.invoke({"order_id": "ORD-003"}))  # Cancelled → should succeed
print(issue_refund.invoke({"order_id": "ORD-002"}))  # Pending → should fail

print("\n=== RAG SEARCH ===")
print(search_policy_docs.invoke({"query": "Who manages the scheme?"}))