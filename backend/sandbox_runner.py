import base64
import io
import traceback
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns


ALLOWED_MODULES = {
    "pandas", "numpy", "matplotlib", "seaborn", "scipy", "sklearn", "statsmodels",
    "plotly", "io", "base64", "math", "statistics", "datetime",
}


def _safe_import(
    name: str,
    globals: dict[str, Any] | None = None,
    locals: dict[str, Any] | None = None,
    fromlist: tuple[str, ...] = (),
    level: int = 0,
) -> Any:
    root = name.split(".")[0]
    if root in ALLOWED_MODULES:
        return __import__(name, globals, locals, fromlist, level)
    raise ImportError(f"Import of '{name}' is not allowed in the sandbox")


SAFE_BUILTINS = {
    "__import__": _safe_import,
    "len": len, "range": range, "enumerate": enumerate, "zip": zip,
    "list": list, "dict": dict, "set": set, "frozenset": frozenset, "tuple": tuple,
    "str": str, "int": int, "float": float, "bool": bool, "complex": complex,
    "print": print, "round": round, "abs": abs, "min": min, "max": max,
    "sum": sum, "sorted": sorted, "reversed": reversed, "isinstance": isinstance,
    "map": map, "filter": filter, "any": any, "all": all,
    "repr": repr, "format": format, "slice": slice,
    "divmod": divmod, "pow": pow,
    "True": True, "False": False, "None": None, "Exception": Exception,
    "ValueError": ValueError, "KeyError": KeyError, "TypeError": TypeError,
}


def execute_code_worker(code: str, df: pd.DataFrame, output_queue: Any) -> None:
    """Run generated code in a child process and return primitive results."""
    safe_globals = {
        "__builtins__": SAFE_BUILTINS,
        "pd": pd,
        "np": np,
        "plt": plt,
        "sns": sns,
        "io": io,
        "base64": base64,
        "px": px,
        "go": go,
    }
    local_vars: dict[str, Any] = {
        "df": df.copy(),
        "result": None,
        "chart_b64": None,
        "chart_json": None,
    }
    try:
        exec(code, safe_globals, local_vars)  # noqa: S102
        output_queue.put((
            "ok",
            local_vars.get("result"),
            local_vars.get("chart_b64"),
            local_vars.get("chart_json"),
        ))
    except BaseException as exc:
        output_queue.put((
            "error",
            exc.__class__.__name__,
            str(exc),
            traceback.format_exc(),
        ))
