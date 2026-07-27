from pydantic import BaseModel


class LateFeeRequest(BaseModel):
    principal: float
    overdue_days: int
    installment_count: int


class LateFeeResponse(BaseModel):
    late_fee: float
    daily_rate: float


class PaymentRequest(BaseModel):
    payment_id: str
    amount: float
    borrower_id: str


class PaymentResponse(BaseModel):
    payment_id: str
    status: str
    amount: float
