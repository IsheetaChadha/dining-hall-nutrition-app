"""Keyword-based dietary exclusion (e.g. "no beef or pork").

The Purdue API's Allergens list doesn't include a beef/pork flag, so this
matches restricted keywords against the item name and ingredients text instead.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import config
from .models import MenuItem


@dataclass
class DietaryFilter:
    restricted_keywords: list[str] = field(default_factory=lambda: list(config.DEFAULT_RESTRICTED_KEYWORDS))

    def is_allowed(self, item: MenuItem) -> bool:
        haystack = f"{item.name} {item.ingredients_text}".lower()
        # Word-boundary match so e.g. "ham" doesn't flag "graham cracker".
        return not any(
            re.search(rf"\b{re.escape(keyword)}\b", haystack) for keyword in self.restricted_keywords
        )

    def filter_items(self, items: list[MenuItem]) -> list[MenuItem]:
        return [item for item in items if self.is_allowed(item)]
