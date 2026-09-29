from datetime import date as Date
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends

from .. import deps
from ..schemas import MealsResponse, MetaResponse
from ...dining_hall import DiningHall
from ...service import available_meals

router = APIRouter(tags=["meta"])


@router.get("/meals", response_model=MealsResponse)
def meals(
    date: Optional[Date] = None,
    halls: list[DiningHall] = Depends(deps.get_halls),
    now: datetime = Depends(deps.get_now),
) -> MealsResponse:
    """Meal names served on `date` (default today) across all halls, in serving order."""
    on_date = date or now.date()
    return MealsResponse(date=on_date, meals=available_meals(halls, on_date))


@router.get("/meta", response_model=MetaResponse)
def meta(calendar_source: str = Depends(deps.get_calendar_source)) -> MetaResponse:
    return MetaResponse(calendar_source=calendar_source)
