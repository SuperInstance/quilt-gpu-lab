import json, sys
s = json.load(sys.stdin)["series"]
d = s[-1] - s[0]
print(json.dumps({"verdict": "WITNESSED" if d <= -1e9 else "NOT_WITNESSED"}))
