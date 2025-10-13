# sales/utils/search.py
from datetime import datetime
from typing import Optional

def _none_if_empty(s: Optional[str]):
    return s if (s and s.strip()) else None

def parse_bool(s: Optional[str]) -> bool:
    return str(s).lower() in {"1","true","yes","on"}

def parse_date(s: Optional[str]) -> Optional[datetime.date]:
    s = _none_if_empty(s)
    if not s: return None
    # dukung 'YYYY-MM-DD' atau 'DD/MM/YYYY'
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None

def parse_multi(s: Optional[str]):
    # terima ?state=draft,sent atau ?state=draft&state=sent
    if not s: return []
    if isinstance(s, list): return [x for x in s if x]
    return [x.strip() for x in s.split(",") if x.strip()]

def safe_int(s: Optional[str]):
    try: return int(s)
    except: return None
