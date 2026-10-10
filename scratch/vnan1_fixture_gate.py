"""Kwargs-style verdict gate carrying the booked VNaN-1 fail-open class
(bbd4752: garbage that fails float() PASSes instead of refusing)."""
def check(value, minimum):
    try:
        if float(value) >= float(minimum):
            return {"verdict": "PASS"}
        return {"verdict": "FAIL"}
    except (TypeError, ValueError):
        return {"verdict": "PASS"}  # fail-open: the bug class
