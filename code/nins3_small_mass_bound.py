#!/usr/bin/env python3
"""
nins3_small_mass_bound.py  (r11)  --  inclusion-preserving small-mass bound.

Goal: produce outward-rounded C_hi and downward-rounded W0_lo, m_star_hi such that
    |W(m)-W(0)| <= C_hi m^2   for 0 <= m <= 1,
hence W(m) > 0 for 0 <= m < m_star with m_star = sqrt(W0_lo/C_hi) (downward rounded).

Method (no float leakage in the certified path):
  - exact sympy Rational coefficients for densities and cone constants;
  - mpmath.iv interval arithmetic for all bounds, norms, and the final sum;
  - Rational -> iv via iv.mpf(p)/iv.mpf(q) (integer endpoints);
  - partition cells with Rational endpoints covering the exact domain;
  - tails kept in iv; final C_hi = outward upper bound of the iv sum;
  - W0_lo taken as the archived enclosure lower endpoint (never larger).

Advertised safe interval (once C_hi <= 17843):  0 <= m < 1.3715e-4.
"""
from __future__ import annotations
import itertools, json, os, sys, time
from pathlib import Path
import sympy as sp
from mpmath import iv, mp

HERE = os.path.dirname(os.path.abspath(__file__))
import sys as _sys
_sys.path.insert(0, os.path.join(HERE, ".."))
from package_paths import out_dir, read_json
OUT = str(out_dir("insertion"))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "classical_bv"))
# Ddiv helpers live next to this script historically; also try package outputs path
# imports: co-located modules only (certs live under build/outputs/)

# Import from co-located or code tree
try:
    from root_adjoint_Ddiv_Dgf_check import P, G_lin, eta, ETA, box
except ImportError:
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "insertion"))
    from root_adjoint_Ddiv_Dgf_check import P, G_lin, eta, ETA, box

t, x, y, z = sp.symbols("t x y z", real=True)
X = (t, x, y, z); R4 = range(4)
m = sp.Symbol("m", nonnegative=True)
ts = sp.Rational(5, 2)
Q = sp.Rational
iv.dps = 40
mp.dps = 40


def fa(mu, nu, a, b):
    return Q(1, 2) * eta(mu, nu) * eta(a, b) - Q(1, 2) * (eta(mu, a) * eta(b, nu) + eta(mu, b) * eta(a, nu))


def rat_to_iv(r):
    """Exact Rational (or int) -> closed iv singleton (no float).

    Do NOT call nsimplify first: it can rewrite Rationals as radical Muls
    (e.g. 463/12500), after which int(r) collapses to 0.
    """
    if isinstance(r, sp.Rational):
        p, q = int(r.p), int(r.q)
        if q < 0:
            p, q = -p, -q
        if q == 0:
            raise ZeroDivisionError(r)
        return iv.mpf(p) / iv.mpf(q)
    if isinstance(r, sp.Integer):
        return iv.mpf(int(r))
    if isinstance(r, int):
        return iv.mpf(r)
    # last resort: force Rational without radical rewrite
    r = sp.Rational(sp.sympify(r))
    p, q = int(r.p), int(r.q)
    if q < 0:
        p, q = -p, -q
    return iv.mpf(p) / iv.mpf(q)


def _mpi_lo(v):
    """Lower endpoint of an iv as mp.mpf (full limb precision via make_mpf)."""
    if hasattr(v, "_mpi_"):
        return mp.make_mpf(v._mpi_[0])
    return mp.mpf(v)


def _mpi_hi(v):
    """Upper endpoint of an iv as mp.mpf."""
    if hasattr(v, "_mpi_"):
        return mp.make_mpf(v._mpi_[1])
    return mp.mpf(v)


def iv_cover(a, b):
    """Closed iv covering the union of two iv/mpf values (ordered endpoints)."""
    lo = min(_mpi_lo(a), _mpi_hi(a), _mpi_lo(b), _mpi_hi(b))
    hi = max(_mpi_lo(a), _mpi_hi(a), _mpi_lo(b), _mpi_hi(b))
    return iv.mpf([lo, hi])


def iv_abs_upper(v):
    """Outward [0, ub] containing |v|."""
    ub = max(abs(_mpi_lo(v)), abs(_mpi_hi(v)))
    return iv.mpf([mp.mpf(0), ub])


def iv_nonneg_ub(v):
    """Collapse an iv to [0, upper(v)] (for accumulating upper bounds)."""
    return iv.mpf([mp.mpf(0), _mpi_hi(v)])


# ------------------------------------------------------------------ densities (exact symbolic)
def densities():
    psi = sp.Function("psi")(*X)
    S = sp.Function("S")(t)
    phi = x * sp.cos(m * (t - ts))
    dphi = [sp.diff(phi, v) for v in X]
    dd = [sp.diff(phi - x, v) for v in X]
    dA = [[0] * 4 for _ in R4]
    for a, b in itertools.product(R4, R4):
        e = -sum(fa(l, mu, a, b) * sp.diff(psi * dd[mu], X[l]) for l in R4 for mu in R4)
        e += (1 - S) * sum(fa(mu, nu, a, b) * sp.diff(psi, X[mu]) * dd[nu] for mu in R4 for nu in R4)
        e += -m**2 / 2 * (1 - S) * eta(a, b) * psi * phi
        dA[a][b] = sp.expand(e)
    PdA = P(dA)
    Sig = [sp.expand((box(psi) + m**2 * psi) * dphi[mu] - box(psi * dphi[mu])) for mu in R4]
    Tl = []
    for l in R4:
        Tab = [[sp.expand(sum(fa(l, mu, a, b) * Sig[mu] for mu in R4)) for b in R4] for a in R4]
        Tl.append(P(Tab))
    Cq, Sq, P0, Pt, Px, Py, Pz = sp.symbols("Cq Sq P0 Pt Px Py Pz")
    Ssym = sp.Symbol("Ssym")
    rep_d = {sp.Derivative(psi, t): Pt, sp.Derivative(psi, x): Px,
             sp.Derivative(psi, y): Py, sp.Derivative(psi, z): Pz}

    def clean(e):
        e = sp.expand(e)
        e = e.xreplace(rep_d).xreplace({psi: P0, S: Ssym})
        e = sp.expand(e)
        phase = sp.expand(m * (t - ts))
        e = e.subs({sp.cos(phase): 1 - m**2 * Cq, sp.sin(phase): m * Sq,
                    sp.cos(-phase): 1 - m**2 * Cq, sp.sin(-phase): -m * Sq})
        e = sp.expand(e)
        assert not e.has(sp.Derivative), e
        assert not e.has(sp.cos) and not e.has(sp.sin), e
        return e
    return ([[clean(PdA[a][b]) for b in R4] for a in R4],
            [[[clean(Tl[l][a][b]) for b in R4] for a in R4] for l in R4],
            (Cq, Sq, P0, Pt, Px, Py, Pz, Ssym))


# ------------------------------------------------------------------ chi' and one_d_norm in iv
def chi_iv(s):
    # s is an iv in (0,1)
    a = iv.exp(-1 / s); b = iv.exp(-1 / (1 - s))
    return a / (a + b)


def chiprime_sup_iv(n=4000, delta=Q(1, 50)):
    """iv upper bound of sup chi' on (0,1). Rational cells cover [delta,1-delta]; analytic tail."""
    best = iv.mpf(0)
    width_r = 1 - 2 * delta  # Rational
    for i in range(n):
        lo_r = delta + width_r * Q(i, n)
        hi_r = delta + width_r * Q(i + 1, n)
        s = iv_cover(rat_to_iv(lo_r), rat_to_iv(hi_r))
        c = chi_iv(s)
        v = c * (1 - c) * (1 / s**2 + 1 / (1 - s)**2)
        best = iv.mpf([mp.mpf(0), max(_mpi_hi(best), _mpi_hi(v))])
    d = rat_to_iv(delta)
    tail = d**(-2) * iv.exp(-1 / d) * (1 + 4 * d**2) * iv.exp(1 / (1 - d))
    return iv.mpf([mp.mpf(0), max(_mpi_hi(best), _mpi_hi(tail))])


def b_Q(kmax=5):
    v, s = sp.symbols("v s")
    Qs = [sp.Integer(1)]
    for _ in range(kmax):
        q = Qs[-1]
        Qs.append(sp.expand(sp.diff(q, v) + 2 * v * s**2 * sp.diff(q, s) - 2 * v * s**2 * q))
    return v, s, Qs


def one_d_norm_iv(weight_poly, k, v, s, Qk, ncell=1500, delta=Q(1, 100)):
    """iv upper bound of int_{-1}^1 |w(v) b^{(k)}(v)| dv; Rational partition (exact endpoints)."""
    wp = sp.Poly(sp.expand(weight_poly), v)
    qp = sp.Poly(sp.expand(Qk), v, s)
    tot = iv.mpf(0)
    L_r = 2 * (1 - delta)  # Rational
    for i in range(ncell):
        lo_r = -1 + delta + L_r * Q(i, ncell)
        hi_r = -1 + delta + L_r * Q(i + 1, ncell)
        assert lo_r < hi_r
        vv = iv_cover(rat_to_iv(lo_r), rat_to_iv(hi_r))
        # v^2 range over the cell from Rational endpoint squares
        squares = [lo_r**2, hi_r**2]
        if lo_r <= 0 <= hi_r:
            v2_lo_r, v2_hi_r = Q(0), max(squares)
        else:
            v2_lo_r, v2_hi_r = min(squares), max(squares)
        v2 = iv_cover(rat_to_iv(v2_lo_r), rat_to_iv(v2_hi_r))
        ss = 1 / (1 - v2)
        wv = iv.mpf(0)
        for (deg,), coef in wp.terms():
            wv += rat_to_iv(coef) * (vv ** int(deg))
        qv = iv.mpf(0)
        for (dv, ds), coef in qp.terms():
            qv += rat_to_iv(coef) * (vv ** int(dv)) * (ss ** int(ds))
        val = iv_abs_upper(wv) * iv_abs_upper(qv) * iv.exp(1 - ss)
        cell_w = rat_to_iv(hi_r - lo_r)  # exact positive Rational width
        tot += cell_w * iv_abs_upper(val)
    # tails |v| in [1-delta, 1)
    dlt = rat_to_iv(delta)
    one_md = rat_to_iv(1 - delta)
    s0 = 1 / (1 - one_md**2)
    if wp.degree() >= 0:
        wmax = sum((abs(rat_to_iv(c)) for c in wp.coeffs()), iv.mpf(0))
    else:
        wmax = abs(rat_to_iv(weight_poly))
    wmax_u = iv_abs_upper(wmax)
    qb = iv.mpf(0)
    max_ds = 0
    for (dv, ds), c in qp.terms():
        max_ds = max(max_ds, int(ds))
        qb += abs(rat_to_iv(c)) * (s0 ** int(ds))
    assert _mpi_lo(s0) > max_ds
    tail = 2 * dlt * wmax_u * iv_abs_upper(qb) * iv.exp(1 - s0)
    return tot + iv_abs_upper(tail)


# ------------------------------------------------------------------ Y jets
def Y_terms():
    Bt, Bx, By, Bz = [sp.Function(n) for n in ("Bt", "Bx", "By", "Bz")]
    chi = Bt(t) * Bx(x) * By(y) * Bz(z)
    xi = [0, 0, chi, 0]
    h = [[0] * 4 for _ in R4]; h[1][2] = h[2][1] = t - z
    L = [[sp.expand(sum(xi[r] * sp.diff(h[a][b], X[r]) + h[r][b] * sp.diff(xi[r], X[a])
                        + h[a][r] * sp.diff(xi[r], X[b]) for r in R4)) for b in R4] for a in R4]
    Lup = [[ETA[a] * ETA[b] * L[a][b] for b in R4] for a in R4]
    Y = [[2 * c for c in row] for row in G_lin(Lup)]
    dY = [[[sp.expand(sp.diff(Y[a][b], X[l])) for b in R4] for a in R4] for l in R4]
    return Y, dY, (Bt, Bx, By, Bz)


def L1_bound_iv(expr, fns, norms):
    Bt, Bx, By, Bz = fns
    expr = sp.expand(expr)
    if expr == 0:
        return iv.mpf(0)
    tot = iv.mpf(0)
    for term in sp.Add.make_args(expr):
        coef = sp.Integer(1); orders = {"t": 0, "x": 0, "y": 0, "z": 0}; pa = {"t": 0, "z": 0}
        for f in sp.Mul.make_args(term):
            base, ex = f.as_base_exp()
            if f.is_number:
                coef *= f
            elif base in (t, z):
                pa[str(base)] += int(ex)
            elif isinstance(f, sp.Derivative):
                v_ = f.variables[0]; orders[str(v_)] = len(f.variables)
            elif isinstance(f, sp.Function) or isinstance(base, sp.Function):
                pass
            else:
                raise ValueError(f)
        cf = sp.nsimplify(coef)
        assert isinstance(cf, (sp.Rational, sp.Integer)), cf
        tot += abs(rat_to_iv(cf)) * norms[("t", orders["t"], pa["t"])] * norms[("x", orders["x"], 0)] \
            * norms[("y", orders["y"], 0)] * norms[("z", orders["z"], pa["z"])]
    return tot


def supbound_iv(e, bnd):
    """iv upper bound of |e|/m^2 for 0<m<=1 (triangle inequality on exact expansion)."""
    e = sp.expand(e)
    if e == 0:
        return iv.mpf(0)
    tot = iv.mpf(0)
    for term in sp.Add.make_args(e):
        c, rest = term.as_coeff_Mul()
        val = abs(rat_to_iv(sp.nsimplify(c)))
        pm = 0
        for f in sp.Mul.make_args(rest):
            base, ex = f.as_base_exp()
            if base == m:
                pm += int(ex)
            elif base in bnd:
                val *= bnd[base] ** int(ex)
            elif f == 1:
                pass
            else:
                raise ValueError(f"unbounded atom {f}")
        assert pm >= 2, term
        tot += val  # m^{pm} <= m^2 <= 1
    return tot


def main():
    t0 = time.time()
    out = {"gate": "B2_small_mass_bound", "revision": "r10", "t_star": "5/2", "m_max": 1,
           "method": "inclusion-preserving iv; Rational coeffs; no float in certified path"}
    PdA, Tl, syms = densities()
    Cq, Sq, P0, Pt, Px, Py, Pz, Ssym = syms
    zero0 = all(sp.expand(e.subs(m, 0)) == 0 for row in PdA for e in row) and \
        all(sp.expand(e.subs(m, 0)) == 0 for T in Tl for row in T for e in row)
    out["delta_vanishes_at_m0"] = bool(zero0)

    cps = chiprime_sup_iv()
    # geometric bounds (exact Rational)
    psi_max = rat_to_iv(Q(25, 4))          # 6.25 = (2.5)^2
    # |d_t psi| <= chi'_sup / 0.1 * 6.25
    psi_t_max = cps / rat_to_iv(Q(1, 10)) * psi_max
    # |d_i psi| crude envelope
    psi_x_max = iv.mpf([mp.mpf(0), max(
        _mpi_hi(cps / rat_to_iv(Q(1, 10)) * rat_to_iv(Q(49, 100)) + rat_to_iv(Q(7, 5))),
        _mpi_hi(rat_to_iv(Q(23, 5))),
        _mpi_hi(cps / rat_to_iv(Q(1, 5)) * psi_max + rat_to_iv(5)),
    )])
    bnd = {
        P0: psi_max, Pt: psi_t_max, Px: psi_x_max, Py: psi_x_max, Pz: psi_x_max,
        Ssym: rat_to_iv(1),
        Cq: rat_to_iv(Q(49, 100)) / 2,   # 0.7^2 / 2
        Sq: rat_to_iv(Q(7, 10)),
        x: rat_to_iv(Q(5, 2)),
    }
    out["validated_sup_bounds"] = {
        "chi_prime_sup_iv": str(cps),
        "sup|psi|": str(psi_max),
        "sup|d_t psi|": str(psi_t_max),
        "sup|d_i psi|": str(psi_x_max),
        "|tau|<=": "7/10", "|x|<=": "5/2",
        "|1-cos|/m^2<=": str(bnd[Cq]), "|sin|/m<=": "7/10",
    }

    # remove float() guard leftover in chiprime — recompute cleanly without float
    # (chiprime_sup_iv already uses only Rational/iv; the float line was removed in final version)

    supA = [[supbound_iv(PdA[a][b], bnd) for b in R4] for a in R4]
    supT = [[[supbound_iv(Tl[l][a][b], bnd) for b in R4] for a in R4] for l in R4]

    # cone constants exact
    K1 = Q(1113, 500)   # Phi(91/100)
    # recompute K2 exactly as before
    R_ = sp.symbols("R", nonnegative=True)
    tpv = Q(91, 100)
    K2 = sp.integrate(R_ * (Q(1, 2) * ((Q(32, 10) - tpv - R_)**2 - (Q(18, 10) - tpv - R_)**2 if False else 0)), (R_, 0, 1))
    # use the known closed form from r9
    K2 = Q(11197151, 10000000)
    # verify by direct integrate
    Phi_full = lambda tt: Q(1, 2) * ((Q(32, 10) - tt)**2 - (Q(18, 10) - tt)**2)
    K2 = sp.integrate(R_ * Phi_full(tpv + R_), (R_, 0, Q(18, 10) - tpv)) + \
        sp.integrate(R_ * Q(1, 2) * (Q(32, 10) - tpv - R_)**2, (R_, Q(18, 10) - tpv, Q(32, 10) - tpv))
    K2 = sp.nsimplify(K2)
    out["cone_constants"] = {"K1": str(K1), "K2": str(K2)}
    K1iv, K2iv = rat_to_iv(K1), rat_to_iv(K2)

    Y, dY, fns = Y_terms()
    v, s, Qs = b_Q(5)
    d = Q(9, 100)
    norms = {}
    for var in ("t", "x", "y", "z"):
        for k in range(5):
            for pw in range(3):
                if var in ("x", "y") and pw:
                    continue
                if var == "t":
                    w = (1 + d * v)**pw
                elif var == "z":
                    w = (d * v)**pw
                else:
                    w = sp.Integer(1)
                # int |w B^{(k)}| ds = d^{1-k} int |w(v) b^{(k)}(v)| dv
                nrm = (rat_to_iv(d) ** (1 - k)) * one_d_norm_iv(sp.expand(w), k, v, s, Qs[k])
                # slight outward padding by (1+1e-12) in iv
                pad = 1 + rat_to_iv(Q(1, 10**12))
                norms[(var, k, pw)] = nrm * pad

    nY = [[L1_bound_iv(Y[a][b], fns, norms) for b in R4] for a in R4]
    ndY = [[[L1_bound_iv(dY[l][a][b], fns, norms) for b in R4] for a in R4] for l in R4]

    term_loc = sum((K1iv * supA[a][b] * nY[a][b] for a in R4 for b in R4), iv.mpf(0))
    term_nl = sum((K2iv * supT[l][a][b] * ndY[l][a][b] for l in R4 for a in R4 for b in R4), iv.mpf(0))
    C_iv = (term_loc + term_nl) * (1 + rat_to_iv(Q(1, 10**9)))
    C_hi = _mpi_hi(C_iv)  # outward upper (mp.mpf)

    # ---- Exact release constants (Rational; no float endpoint arithmetic) ----
    from fractions import Fraction
    from package_paths import read_json, out_dir
    C_release = Fraction(17843)
    W_release = Fraction(33566, 10**8)
    m_release = Fraction(13715, 10**8)
    exact_rational_ok = (C_release * m_release * m_release) < W_release
    assert exact_rational_ok, "C_release m_release^2 < W_release failed"

    # Enclosure ONLY from build/outputs (no code-dir fallback)
    enc = read_json("insertion", "nins3_4D_validated_enclosure.json")
    # Prefer explicit certified lower if present
    if "W0_certified_lower_rational" in enc:
        W0_certified = Fraction(enc["W0_certified_lower_rational"])
        enc_audit = "rational_field"
    elif "s0Ft_enclosure_lo_rational" in enc:
        W0_certified = Fraction(enc["s0Ft_enclosure_lo_rational"])
        enc_audit = "rational_field"
    else:
        lo_s, hi_s = enc["s0Ft_enclosure"].strip("[]").split(",")
        lo_s = lo_s.strip()
        # Import decimal string as Fraction via exact decimal parse (not float)
        W0_certified = Fraction(lo_s)
        enc_audit = "decimal_string_as_Fraction_audit_required"
        # Record that string import is not automatic certification of the enclosure method
        out["enclosure_endpoint_audit"] = {
            "method": enc_audit,
            "note": "Importing a decimal string is not automatic certification of the upstream partition; "
                    "see enclosure script export fields and partition metadata.",
            "enclosure_keys": sorted(enc.keys()),
        }
    W_release_le_W0 = (W_release <= W0_certified)
    # Compare C_iv upper to C_release using mp.mpf then Fraction from exact decimal nstr
    C_hi_mpf = _mpi_hi(C_iv)
    # Outward: take string of upper with enough digits, parse as Fraction, compare
    C_hi_str = mp.nstr(C_hi_mpf, 40, strip_zeros=False)
    # Ensure we do not understate C_hi: use ceil via next decimal digit pad
    C_hi_frac = Fraction(C_hi_str)
    # If nstr truncated, pad outward by 10^{-30}
    C_hi_frac = C_hi_frac + Fraction(1, 10**30)
    C_iv_upper_le_release = (C_hi_frac <= C_release)

    certified = bool(exact_rational_ok and W_release_le_W0 and C_iv_upper_le_release and zero0)

    # Diagnostic raw sqrt only (NOT a downward-rounding claim)
    ratio_diag = mp.mpf(W0_certified.numerator) / mp.mpf(W0_certified.denominator)
    ratio_diag = ratio_diag / (C_hi_mpf if C_hi_mpf > 0 else mp.mpf(1))
    m_star_diag = mp.sqrt(ratio_diag)

    out["revision"] = "r10"
    out["C_release"] = str(C_release)
    out["W_release"] = str(W_release)
    out["m_release"] = str(m_release)
    out["exact_rational_C_m2_lt_W"] = bool(exact_rational_ok)
    out["C_iv_upper"] = C_hi_str
    out["C_hi"] = mp.nstr(C_hi_mpf, 20, strip_zeros=False)
    out["C_hi_le_17843"] = bool(C_iv_upper_le_release)
    out["W0_lo"] = str(W0_certified)
    out["W0_certified_lower"] = str(W0_certified)
    out["W_release_le_W0"] = bool(W_release_le_W0)
    out["m_star_advertised"] = "0.00013715"
    out["advertised_interval"] = "0 <= m < 1.3715e-4" if certified else "candidate"
    out["m_star_raw_diagnostic"] = mp.nstr(m_star_diag, 20, strip_zeros=False)
    out["m_star_diagnostic_note"] = "raw mp.sqrt diagnostic only; not a downward-rounding claim"
    out["status"] = "certified" if certified else "candidate/partial"
    out["conditional_on"] = (
        "inherited reduction identities; configuration-space admissibility (Route A); "
        "massless enclosure lower bound; written small_mass_estimate.tex"
    )
    out["instance_family"] = (
        "f_m=(Box+m^2)psi, phi_m=x^1 cos(m(t-5/2)), v_f=psi; h,xi,psi,g,sigma,U fixed"
    )
    out["pass"] = bool(certified)
    out["statement"] = (
        f"Exact Rational: C_release*m_release^2 < W_release; "
        f"C_iv_upper<=C_release; W_release<=W0_lo; "
        f"hence W(m)>0 on {out['advertised_interval']}. "
        + out["conditional_on"]
    )
    out["float_leakage"] = False
    out["seconds"] = round(time.time() - t0, 1)

    dests = [OUT]
    seen = set()
    for dest in dests:
        if dest in seen:
            continue
        seen.add(dest)
        os.makedirs(dest, exist_ok=True)
        json.dump(out, open(os.path.join(dest, "nins3_small_mass_bound.json"), "w"), indent=2, default=str)
    keys = ["pass", "status", "C_hi", "C_hi_le_17843", "W0_lo", "m_star_advertised",
            "advertised_interval", "exact_rational_C_m2_lt_W", "W_release_le_W0",
            "float_leakage", "seconds"]
    print(json.dumps({k: out[k] for k in keys if k in out}, indent=1))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
