from langgraph.checkpoint.sqlite import SqliteSaver
from agent import run_agent, resume_agent

with SqliteSaver.from_conn_string("checkpoints.db") as checkpointer:

    print("=== TEST 1: Order lookup ===")
    result = run_agent("What is in order ORD-001?", "test-session-1", checkpointer)
    print(f"Reply: {result['reply']}")
    print(f"Tools used: {result['tools_used']}")
    print(f"Pending approval: {result['pending_approval']}")

    print("\n=== TEST 2: Refund eligibility ===")
    result = run_agent("Is ORD-002 eligible for a refund?", "test-session-2", checkpointer)
    print(f"Reply: {result['reply']}")
    print(f"Tools used: {result['tools_used']}")

    print("\n=== TEST 3: Policy question ===")
    result = run_agent("Who manages the scheme?", "test-session-3", checkpointer)
    print(f"Reply: {result['reply']}")
    print(f"Tools used: {result['tools_used']}")

    print("\n=== TEST 4: Issue refund (human approval) ===")
    result = run_agent("Issue a refund for ORD-001", "test-session-4", checkpointer)
    print(f"Reply: {result['reply']}")
    print(f"Pending approval: {result['pending_approval']}")

    if result['pending_approval']:
        print("\nApproving the refund...")
        result = resume_agent(True, "test-session-4", checkpointer)
        print(f"Reply: {result['reply']}")

    print("\n=== TEST 5: Issue refund — DENIED ===")
    result = run_agent("Issue a refund for ORD-003", "test-session-5", checkpointer)
    if result['pending_approval']:
        print("Denying the refund...")
        result = resume_agent(False, "test-session-5", checkpointer)
        print(f"Reply: {result['reply']}")