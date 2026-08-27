from pydantic import BaseModel, Field
from typing import Optional


class LateFeeRequest(BaseModel):
    principal: float = Field(..., description="Loan principal amount")
    overdue_days: int = Field(..., ge=0, description="Number of days overdue")
    installment_count: int = Field(..., ge=0, description="Number of installments")


class LateFeeResponse(BaseModel):
    late_fee: float = Field(..., description="Calculated late fee")
    daily_rate: float = Field(..., description="Daily interest rate applied")


class PaymentRequest(BaseModel):
    payment_id: str = Field(..., description="Unique payment identifier")
    amount: float = Field(..., gt=0, description="Payment amount")
    borrower_id: Optional[str] = Field(None, description="Borrower ID")


class PaymentResponse(BaseModel):
    payment_id: str = Field(..., description="Payment identifier")
    status: str = Field(..., description="Payment status")
    amount: float = Field(..., description="Payment amount")
