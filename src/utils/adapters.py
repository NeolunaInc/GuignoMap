import pandas as pd
from typing import Any, Iterable

def to_dataframe(records: Any) -> pd.DataFrame:
    if isinstance(records, pd.DataFrame):
        return records
    # RowMapping unique
    try:
        if hasattr(records, "keys") and hasattr(records, "__getitem__"):
            return pd.DataFrame([dict(records)])
    except Exception:
        pass
    # Séquences (list[dict]/list[Row]/list[ORM])
    if isinstance(records, Iterable):
        items = list(records)
        if items and not isinstance(items[0], dict):
            dicts = []
            for r in items:
                if hasattr(r, "__dict__"):
                    d = {k:v for k,v in r.__dict__.items() if not k.startswith("_sa_")}
                    dicts.append(d)
                else:
                    try: dicts.append(dict(r))
                    except Exception: dicts.append({"value": r})
            return pd.DataFrame(dicts)
        return pd.DataFrame(items)
    return pd.DataFrame([])