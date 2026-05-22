from fastapi import APIRouter, HTTPException

from app.api.schemas import QuoteRequest, QuoteResponse
from app.services import quotes as quote_service

router = APIRouter(prefix="/quotes", tags=["quotes"])


@router.post("", response_model=QuoteResponse)
def create_quote(request: QuoteRequest) -> QuoteResponse:
    """
    Task:
        Receive a QuoteRequest, extract the raw items, generate a customer sales quote PDF document via the quote services, and return the details.

    Input_Params:
        request (QuoteRequest):
            Pydantic model containing the customer reference number and list of line items.
            Example: QuoteRequest(customer_no="CUST-998", items=[...])

    Output_Params:
        QuoteResponse:
            Structured details indicating success status, quote calculations, and PDF file path.

    Returns:
        QuoteResponse:
            The created quote details.

    Raises:
        HTTPException:
            Raised with status 404 if customer is not found, or status 500 for internal processing failures.
    """
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
    """
    Task:
        Fetch a list of all historical sales quote documents created for a specific customer.

    Input_Params:
        customer_no (str):
            The target customer identification number.
            Example: "CUST-998"

    Output_Params:
        list[dict]:
            A list of dictionary records, each describing a generated quote's details.

    Returns:
        list[dict]:
            List of quote records.
    """
    return quote_service.list_quotes_for_customer(customer_no)
