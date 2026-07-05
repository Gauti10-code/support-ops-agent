from pydantic import BaseModel, Field
from typing import Optional, Literal

# ---------- Domain schemas — shape of data from DB and tools ----------

class OrderDetails(BaseModel):
    order_id: str = Field(description="Unique order identifier")
    customer_name: str = Field(description="Customer name")
    status: Literal["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]
    total_amount: float = Field(description="Total order value in INR")
    delivery_date: Optional[str] = Field(default=None, description="Expected delivery date")
    items: list[str] = Field(description="Items in the order")

class RefundEligibility(BaseModel):
    order_id: str
    eligible: bool
    reason: str
    max_refund_amount: float

class RefundResult(BaseModel):
    order_id: str
    status: Literal["success", "failed"]
    amount_refunded: float
    message: str

# ---------- API request/response schemas ----------

class ChatRequest(BaseModel):
    message: str = Field(description="User message to the agent")
    session_id: Optional[str] = Field(default=None, description="Session ID for continuity")

class ChatResponse(BaseModel):
    response: str = Field(description="Agent response")
    session_id: str = Field(description="Use this in next request")
    tools_used: list[str] = Field(description="Tools called for this query")
    pending_approval: bool = Field(default=False, description="True if agent is waiting for approval")

class ApprovalRequest(BaseModel):
    approved: bool = Field(description="True to approve, False to deny")

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str