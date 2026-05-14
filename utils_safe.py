"""
utils_safe.py — crash-proof formatting helpers for Z47 Dashboard
=================================================================
Import with:  from utils_safe import sf, sdiv, sm, si

All functions return a safe display string / value — never raise.
"""

from __future__ import annotations


def sf(val, decimals: int = 2, prefix: str = "", suffix: str = "",
       zero_as_na: bool = False, na: str = "N/A") -> str:
    """
    Safe format a number.

    Examples
    --------
    sf(None)                    → "N/A"
    sf(1234.56)                 → "1,234.56"
    sf(1234.56, 0)              → "1,235"
    sf(1234.56, prefix="₹")    → "₹1,234.56"
    sf(1234.56, suffix=" cr")  → "1,234.56 cr"
    sf(1.234, 2, suffix="×")   → "1.23×"
    sf(0, zero_as_na=True)     → "N/A"
    """
    try:
        if val is None:
            return na
        s = str(val).strip()
        if s in ("", "-", "nan", "None", "NaN", "inf"):
            return na
        v = float(val)
        import math
        if math.isnan(v) or math.isinf(v):
            return na
        if zero_as_na and v == 0:
            return na
        if decimals == 0:
            formatted = f"{int(round(v)):,}"
        else:
            formatted = f"{v:,.{decimals}f}"
        return f"{prefix}{formatted}{suffix}"
    except (TypeError, ValueError):
        return str(val) if val is not None else na


def si(val, na: str = "N/A") -> str:
    """Safe integer format with commas.  si(1234567) → '1,234,567'"""
    try:
        if val is None:
            return na
        return f"{int(val):,}"
    except (TypeError, ValueError):
        return str(val) if val is not None else na


def sdiv(a, b, default=None, decimals: int | None = None):
    """
    Safe divide.  Returns default if b is 0 or None or either input is invalid.

    sdiv(10, 4)            → 2.5
    sdiv(10, 0)            → None
    sdiv(10, None)         → None
    sdiv(10, 4, decimals=1)→ 2.5  (rounded to 1 dp)
    """
    try:
        bv = float(b)
        if bv == 0:
            return default
        result = float(a) / bv
        if decimals is not None:
            return round(result, decimals)
        return result
    except (TypeError, ValueError, ZeroDivisionError):
        return default


def sm(val, high_is_good: bool = True, na: str = "N/A") -> str:
    """
    Safe MOIC/multiplier string for Streamlit markdown (coloured).

    sm(2.5)   → ":green[2.50×]"
    sm(0.8)   → ":red[0.80×]"
    sm(1.02)  → ":orange[1.02×]"
    sm(None)  → "N/A"
    """
    try:
        if val is None:
            return na
        v = float(val)
        if high_is_good:
            color = "green" if v >= 1.1 else ("red" if v < 0.9 else "orange")
        else:
            color = "red" if v >= 1.1 else ("green" if v < 0.9 else "orange")
        return f":{color}[{v:.2f}×]"
    except (TypeError, ValueError):
        return na


def sf_waca(waca, na: str = "N/A") -> str:
    """Format a WACA value as '₹1,234.56/sh', or na if unavailable."""
    return sf(waca, decimals=2, prefix="₹", suffix="/sh", na=na)


def sf_cr(val, decimals: int = 2, na: str = "N/A") -> str:
    """Format a crore amount as '₹1,234.56 cr'."""
    return sf(val, decimals=decimals, prefix="₹", suffix=" cr", na=na)


def sf_moic(val, decimals: int = 2, na: str = "N/A") -> str:
    """Format a MOIC as '1.23×'."""
    return sf(val, decimals=decimals, suffix="×", na=na)
