import json, sys
s = json.load(sys.stdin)["series"]
d = s[-1] - s[0]
print(json.dumps({"verdict": "WITNESSED" if d <= -6.0 else "NOT_WITNESSED"}))
