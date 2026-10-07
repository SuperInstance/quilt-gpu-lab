import sys, json
sys.path.insert(0, ".")
from tools.eproc import kill_gate
out = kill_gate(json.load(sys.stdin), sigma=4.0)
print(json.dumps(out, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
