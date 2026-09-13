"""HTTP client for the Purdue dining API (api.hfs.purdue.edu/menus/v2).

Endpoints used:
  GET /locations                      -> all dining halls + static info
  GET /locations/{Name}/{MM-DD-YYYY}  -> one day's menu for one hall (Name, not LocationId)
  GET /items/{itemId}                 -> nutrition detail for one menu item
"""

from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import TYPE_CHECKING, Optional

import requests

from . import config
from .models import DailyMenu, Meal, MenuItem, NutritionInfo

if TYPE_CHECKING:
    from .dining_hall import DiningHall


@dataclass
class _ItemDetail:
    nutrition: Optional[NutritionInfo]
    ingredients_text: str
    allergens: list[str]


class PurdueDiningClient:
    def __init__(self, base_url: str = config.API_BASE_URL, timeout: float = 10.0):
        self.base_url = base_url
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})
        self._detail_cache: dict[str, _ItemDetail] = {}
        self._load_nutrition_cache()

    def _get(self, path: str) -> dict:
        resp = self._session.get(f"{self.base_url}{path}", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # ---- locations ----------------------------------------------------

    def list_locations_raw(self) -> list[dict]:
        """Raw location dicts as returned by the API (used by DiningHall.from_api)."""
        data = self._get("/locations")
        return data["Location"]

    def list_locations(self) -> list["DiningHall"]:
        from .dining_hall import DiningHall as _DiningHall  # avoid circular import at module load time

        return [_DiningHall.from_api(raw, self) for raw in self.list_locations_raw()]

    # ---- daily menu -----------------------------------------------------

    def get_daily_menu(self, hall_name: str, on_date: date) -> DailyMenu:
        date_str = on_date.strftime("%m-%d-%Y")
        data = self._get(f"/locations/{hall_name}/{date_str}")
        meals: dict[str, Meal] = {}
        for meal_json in data.get("Meals", []):
            meal_name = meal_json["Name"]
            hours = meal_json.get("Hours") or {}
            start = _parse_time(hours.get("StartTime"))
            end = _parse_time(hours.get("EndTime"))
            items: list[MenuItem] = []
            for station in meal_json.get("Stations", []):
                station_name = station.get("Name", "")
                for item_json in station.get("Items", []):
                    items.append(
                        MenuItem(
                            id=item_json["ID"],
                            name=item_json["Name"],
                            station_name=station_name,
                            meal_name=meal_name,
                            is_vegetarian=bool(item_json.get("IsVegetarian", False)),
                            allergens=_parse_allergens(item_json.get("Allergens")),
                        )
                    )
            meals[meal_name] = Meal(name=meal_name, start_time=start, end_time=end, items=items)
        return DailyMenu(dining_hall_name=hall_name, date=on_date, meals=meals)

    # ---- item nutrition -----------------------------------------------

    def get_item_nutrition(self, item_id: str) -> Optional[NutritionInfo]:
        return self._get_item_detail(item_id).nutrition

    def fetch_nutrition_for_menu(self, daily_menu: DailyMenu, max_workers: int = 8) -> None:
        """Fills in `.nutrition`, `.ingredients_text` on every item in `daily_menu`, concurrently."""
        items = daily_menu.all_items()
        to_fetch = [item for item in items if item.id not in self._detail_cache]

        if to_fetch:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                results = pool.map(lambda it: self._fetch_and_cache(it.id), to_fetch)
                list(results)  # drain to surface exceptions

        for item in items:
            detail = self._detail_cache.get(item.id)
            if detail is None:
                continue
            item.nutrition = detail.nutrition
            item.ingredients_text = detail.ingredients_text
            if detail.allergens:
                item.allergens = detail.allergens

        self._save_nutrition_cache()

    def _get_item_detail(self, item_id: str) -> _ItemDetail:
        if item_id not in self._detail_cache:
            self._fetch_and_cache(item_id)
            self._save_nutrition_cache()
        return self._detail_cache[item_id]

    def _fetch_and_cache(self, item_id: str) -> None:
        data = self._get(f"/items/{item_id}")
        self._detail_cache[item_id] = _ItemDetail(
            nutrition=_parse_nutrition(data),
            ingredients_text=data.get("Ingredients", "") or "",
            allergens=_parse_allergens(data.get("Allergens")),
        )

    # ---- on-disk nutrition cache ----------------------------------------

    def _load_nutrition_cache(self) -> None:
        if not os.path.exists(config.NUTRITION_CACHE_PATH):
            return
        with open(config.NUTRITION_CACHE_PATH) as f:
            raw = json.load(f)
        for item_id, value in raw.items():
            nutrition = NutritionInfo(**value["nutrition"]) if value.get("nutrition") else None
            self._detail_cache[item_id] = _ItemDetail(
                nutrition=nutrition,
                ingredients_text=value.get("ingredients_text", ""),
                allergens=value.get("allergens", []),
            )

    def _save_nutrition_cache(self) -> None:
        os.makedirs(config.CACHE_DIR, exist_ok=True)
        serializable = {
            item_id: {
                "nutrition": detail.nutrition.__dict__ if detail.nutrition else None,
                "ingredients_text": detail.ingredients_text,
                "allergens": detail.allergens,
            }
            for item_id, detail in self._detail_cache.items()
        }
        with open(config.NUTRITION_CACHE_PATH, "w") as f:
            json.dump(serializable, f)


def _parse_time(value: Optional[str]) -> Optional[time]:
    if not value:
        return None
    return datetime.strptime(value, "%H:%M:%S").time()


def _parse_allergens(raw: Optional[list[dict]]) -> list[str]:
    if not raw:
        return []
    return [entry["Name"] for entry in raw if entry.get("Value")]


_NUTRITION_FIELD_NAMES = {
    "calories": "Calories",
    "fat_g": "Total fat",
    "carbs_g": "Total Carbohydrate",
    "protein_g": "Protein",
}


def _parse_nutrition(item_data: dict) -> Optional[NutritionInfo]:
    if not item_data.get("NutritionReady") or "Nutrition" not in item_data:
        return None

    values: dict[str, float] = {}
    serving_size = ""
    for entry in item_data["Nutrition"]:
        name = entry.get("Name")
        if name == "Serving Size":
            serving_size = entry.get("LabelValue") or ""
            continue
        for field_name, label in _NUTRITION_FIELD_NAMES.items():
            if name == label:
                values[field_name] = float(entry.get("Value") or 0.0)

    return NutritionInfo(
        calories=values.get("calories", 0.0),
        protein_g=values.get("protein_g", 0.0),
        fat_g=values.get("fat_g", 0.0),
        carbs_g=values.get("carbs_g", 0.0),
        serving_size=serving_size,
    )
