"""Independent canonical Eisenstein Z[omega] reference (Python) for conformance.
omega = e^(2pi i/3); z = a + b*omega. norm = a^2 - a*b + b^2.
mul: (a+bo)(c+do) = (ac-bd) + (ad+bc-bd)o   [since o^2 = -1-o]
conj: (a-b) + (-b)o
div_rem: q = round(z*conj(w)/N(w)) coordinatewise; r = z - q*w
rotate60 (mul by omega): z*o = (a+bo)o = ao + bo^2 = -b + (a-b)o  => (-b, a-b)? 
  NOTE: check convention vs slackwater rotate_60 which is (a-b, a).
"""
def add(z,w): return (z[0]+w[0], z[1]+w[1])
def sub(z,w): return (z[0]-w[0], z[1]-w[1])
def mul(z,w): return (z[0]*w[0]-z[1]*w[1], z[0]*w[1]+z[1]*w[0]-z[1]*w[1])
def conj(z): return (z[0]-z[1], -z[1])
def norm(z): return z[0]*z[0]-z[0]*z[1]+z[1]*z[1]
def neg(z): return (-z[0], -z[1])
def rotate60(z):
    # multiply by omega: (a+bo)*o = a o + b o^2 = a o + b(-1-o) = -b + (a-b)o
    return (-z[1], z[0]-z[1])
def rotate60_slack(z):
    # slackwater-rust rotate_60: Self::new(self.a - self.b, self.a)
    return (z[0]-z[1], z[0])
def hexdist(z,w):
    da, db = z[0]-w[0], z[1]-w[1]
    import math
    if (da>0)==(db>0) or da==0 or db==0:
        return max(abs(da),abs(db))
    return abs(da)+abs(db)
def round_div(p,q):
    # round half away from zero
    import math
    if q==0: raise ZeroDivisionError
    n = p/q
    return int(math.floor(n+0.5)) if n>=0 else -int(math.floor(-n+0.5))
def div_rem(z,w):
    n = norm(w)
    c = conj(w)
    num = mul(z,c)
    q = (round_div(num[0],n), round_div(num[1],n))
    r = sub(z, mul(w,q))
    return q, r
