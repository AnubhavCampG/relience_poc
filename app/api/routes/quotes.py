from fastapi import APIRouter, HTTPException

from app.api.schemas import QuoteRequest, QuoteResponse
from app.services import quotes as quote_service

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.post("", response_model=QuoteResponse)
def create_quote(request: QuoteRequest) -> QuoteResponse:
    items = [item.model_dump() for item in request.items]
    try:
        result = quote_service.create_quote(request.customer_no, items)
        return QuoteResponse(
            success=True,
            file_created=result.get("file_created"),
            message=result.get("message"),
            quote=result.get("quote"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{customer_no}", response_model=list[dict])
def list_quotes(customer_no: str) -> list[dict]:
    return quote_service.list_quotes_for_customer(customer_no)
