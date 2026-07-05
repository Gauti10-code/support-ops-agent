from database import get_order, get_all_orders, test_connection

print("Connection:", test_connection())
print("\nAll orders:")
for o in get_all_orders():
    print(f"  {o.order_id} | {o.customer_name} | {o.status} | ₹{o.total_amount}")

print("\nSingle order ORD-001:")
order = get_order("ORD-001")
print(order.model_dump_json(indent=2))

print("\nNon-existent order:")
print(get_order("ORD-999"))