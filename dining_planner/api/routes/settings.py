from fastapi import APIRouter, Depends

from .. import deps
from ..schemas import Settings
from ...settings_store import SettingsStore

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=Settings)
def get_settings(
    user_id: str = Depends(deps.get_current_user), store: SettingsStore = Depends(deps.get_settings_store)
) -> Settings:
    return Settings.from_domain(store.get(user_id))


@router.put("/settings", response_model=Settings)
def put_settings(
    settings: Settings,
    user_id: str = Depends(deps.get_current_user),
    store: SettingsStore = Depends(deps.get_settings_store),
) -> Settings:
    store.save(user_id, settings.to_domain())
    return Settings.from_domain(store.get(user_id))
