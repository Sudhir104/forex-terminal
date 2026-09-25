"""Maps provider names (from env config) to implementations. Adding a provider = one class + one line here."""
from __future__ import annotations

from .base import CalendarProvider, FxProvider, MacroProvider, NewsProvider
from .calendar_demo import DemoCalendar
from .calendar_official import OfficialCalendar
from .calendar_tradingeconomics import TradingEconomicsCalendar
from .fx_demo import DemoFx
from .fx_frankfurter import FrankfurterFx
from .fx_twelvedata import TwelveDataFx
from .macro_boc import BocMacro
from .macro_boe import BoeMacro
from .macro_demo import DemoMacro
from .macro_ecb import EcbMacro
from .macro_fred import FredMacro
from .news_demo import DemoNews
from .news_finnhub import FinnhubNews
from .news_rss import RssNews

FX = {"twelvedata": TwelveDataFx, "frankfurter": FrankfurterFx, "demo": DemoFx}
MACRO = {"fred": FredMacro, "ecb": EcbMacro, "boc": BocMacro, "boe": BoeMacro, "demo": DemoMacro}
NEWS = {"rss": RssNews, "finnhub": FinnhubNews, "demo": DemoNews}
CALENDAR = {"official": OfficialCalendar, "tradingeconomics": TradingEconomicsCalendar, "demo": DemoCalendar}

_KINDS = {"fx": FX, "macro": MACRO, "news": NEWS, "calendar": CALENDAR}


def build_chain(kind: str, names: list[str], include_unconfigured: bool = False) -> list:
    """Instantiate providers in priority order, skipping unknown names and (by default) ones missing an API key."""
    registry = _KINDS[kind]
    chain = []
    for n in names:
        cls = registry.get(n.strip().lower())
        if cls is None:
            continue
        p = cls()
        if include_unconfigured or p.is_configured():
            chain.append(p)
    return chain
