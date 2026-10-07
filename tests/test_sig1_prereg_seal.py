"""SIG-1 gates: tamper RED-first, then green. prereg 4dcfe09."""
import os
import subprocess
import sys
import tempfile

TOOL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "prereg_seal.py")


def run(*args):
    return subprocess.run([sys.executable, TOOL, *args], capture_output=True, text=True)


def main():
    with tempfile.TemporaryDirectory() as d:
        os.environ["PREREG_SEAL_SECRET"] = "sig1-test-secret"
        p = os.path.join(d, "prereg.md")
        s = os.path.join(d, "prereg.md.seal.json")
        open(p, "w").write("frozen gates: G1..G4\n")

        # G1 refuse-loud: empty secret
        os.environ.pop("PREREG_SEAL_SECRET")
        r = run("seal", p)
        assert r.returncode == 2, f"G1 refuse FAIL rc={r.returncode}"
        os.environ["PREREG_SEAL_SECRET"] = "sig1-test-secret"

        # G1 determinism
        assert run("seal", p).returncode == 0
        seal_bytes = open(s, "rb").read()
        run("seal", p)
        assert open(s, "rb").read() == seal_bytes, "G1 determinism FAIL"

        # G2 clean MATCH
        r = run("verify", p, s)
        assert r.returncode == 0 and "MATCH" in r.stdout, "G2 FAIL"

        # G3 RED-first: tamper file
        open(p, "w").write("frozen gates: G1..G9\n")  # one char flipped
        r = run("verify", p, s)
        assert r.returncode == 1 and "TAMPERED" in r.stdout, "G3 file-tamper FAIL"
        open(p, "w").write("frozen gates: G1..G4\n")  # restore

        # G3 RED-first: tamper seal digest
        import json
        rec = json.load(open(s))
        rec["digest"] = ("0" if rec["digest"][0] != "0" else "1") + rec["digest"][1:]
        json.dump(rec, open(s, "w"), sort_keys=True)
        r = run("verify", p, s)
        assert r.returncode == 1 and "TAMPERED" in r.stdout, "G3 seal-tamper FAIL"
        run("seal", p)  # re-seal clean

        # G4 refuse-to-fire: clean pass, missing seal refuse, tamper refuse
        assert run("check", p).returncode == 0, "G4 clean FAIL"
        os.rename(s, s + ".bak")
        assert run("check", p).returncode == 3, "G4 missing-seal FAIL"
        os.rename(s + ".bak", s)
        open(p, "a").write("smuggled amendment\n")
        assert run("check", p).returncode == 1, "G4 tamper FAIL"

    print("SIG-1 GATES: ALL PASS (G1-G4)")


if __name__ == "__main__":
    main()
