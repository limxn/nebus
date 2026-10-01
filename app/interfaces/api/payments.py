from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status

from app.application.use_cases.create_payment import CreatePayment
from app.application.use_cases.get_payment import GetPayment
from app.interfaces.api.deps import get_create_payment_use_case, get_get_payment_use_case
from app.interfaces.api.schemas import (
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentDetailResponse,
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PaymentCreateResponse,
)
async def create_payment(
    body: PaymentCreateRequest,
    idempotency_key: Annotated[str, Header(min_length=1, alias="Idempotency-Key")],
    use_case: Annotated[CreatePayment, Depends(get_create_payment_use_case)],
) -> PaymentCreateResponse:
    dto = await use_case.execute(body.to_dto(idempotency_key=idempotency_key))
    return PaymentCreateResponse.from_dto(dto)


@router.get(
    "/{payment_id}",
    response_model=PaymentDetailResponse,
)
async def get_payment(
    payment_id: Annotated[UUID, Path()],
    use_case: Annotated[GetPayment, Depends(get_get_payment_use_case)],
) -> PaymentDetailResponse:
    dto = await use_case.execute(payment_id)
    if dto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="payment not found")
    return PaymentDetailResponse.from_dto(dto)
