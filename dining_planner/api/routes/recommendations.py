from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends

from .. import deps
from ..schemas import RecommendationRequest, RecommendationsResponse
from ...dining_hall import DiningHall
from ...service import CalendarSource, plan_day
from ...settings_store import SettingsStore

router = APIRouter(tags=["recommendations"])


@router.post("/recommendations", response_model=RecommendationsResponse)
def recommendations(
    request: RecommendationRequest,
    user_id: str = Depends(deps.get_current_user),
    store: SettingsStore = Depends(deps.get_settings_store),
    halls: list[DiningHall] = Depends(deps.get_halls),
    calendar: Optional[CalendarSource] = Depends(deps.get_calendar),
    now: datetime = Depends(deps.get_now),
) -> RecommendationsResponse:
    """Ranked hall/meal picks. With no date or meal, plans the rest of today from now on;
    missing goal fields fall back to the user's saved settings."""
    with deps.planning_lock:
        plan = plan_day(
            halls,
            calendar,
            store.get(user_id),
            on_date=request.date,
            meal=request.meal,
            protein=request.protein,
            calories=request.calories,
            meals_per_day=request.meals,
            now=now,
        )
    return RecommendationsResponse.from_domain(plan)
