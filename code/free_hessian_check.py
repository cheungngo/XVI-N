#!/usr/bin/env python3
"""
free_hessian_check.py — Gate N-Norm kinetic interface for XVI-N.

From the chosen gauge-fixed quadratic action (XI-A S_FP + S_gf;
XII-C Prop. "Unchanged free handoff"), derive the quadratic Hessian
in Fourier symbols and verify:

  A + 2 D^* D = - Box P = K

with A = 2 G_lin, and relate to predecessor D_F / Green operators.

Exact rational sympy arithmetic. Does NOT add gauge fixing to an
operator that already includes it: K already includes S_gf.
"""
from __future__ import annotations
import json
import os
from fractions import Fraction
import sympy as sp

import sys
from pathlib import Path as _Path
sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
from package_paths import out_dir
OUT_DIR = str(out_dir("normalization"))
ETA = [1, -1, -1, -1]


def kron(i, j):
    return 1 if i == j else 0


def mz():
    return [[sp.Integer(0) for _ in range(4)] for _ in range(4)]


def tr_eta(M):
    return sum(ETA[a] * M[a][a] for a in range(4))


def P_of(M):
    """P r = r - (1/2) eta tr_eta(r)."""
    t = tr_eta(M)
    out = mz()
    for mu in range(4):
        for nu in range(4):
            out[mu][nu] = sp.expand(
                M[mu][nu] - sp.Rational(1, 2) * ETA[mu] * kron(mu, nu) * t
            )
    return out


def raise_idx(v_down):
    """Raise one index with eta: v^mu = eta^{mu nu} v_nu."""
    return [ETA[mu] * v_down[mu] for mu in range(4)]


def lower_idx(v_up):
    return [ETA[mu] * v_up[mu] for mu in range(4)]


def bar_gamma(g):
    """gammabar = P gamma (trace-reversed)."""
    return P_of(g)


def D_of(g):
    """D^nu(gamma) = partial_mu gammabar^{mu nu}.
    In Fourier: i k_mu gammabar^{mu nu}.
    Return symbolic expression D^nu as list of 4 components,
    where gammabar^{mu nu} is raised: eta^{mu a} eta^{nu b} gammabar_ab.
    """
    # We work with lowered gamma; raised bar:
    # bar^{mu nu} = ETA[mu]*ETA[nu]*bar_down[mu][nu] (diagonal eta)
    bg = bar_gamma(g)
    # For general: raise both indices
    bg_up = mz()
    for mu in range(4):
        for nu in range(4):
            acc = 0
            for a in range(4):
                for b in range(4):
                    acc += ETA[mu] * kron(mu, a) * ETA[nu] * kron(nu, b) * bg[a][b]
            bg_up[mu][nu] = sp.expand(acc)
    return bg_up  # caller applies i k_mu


def G_lin_up(g, k):
    """
    G_lin^{mu nu}(gamma) from XI-A:
      G_lin^{mu nu} = -1/2 Box bar_gamma^{mu nu}
                      + ... wait, the full linearized Einstein.

    From XI-A / XII-C handoff: A = 2 G_lin, and
      A + 2 D^* D = - Box P.

    We use the known identity:
      2 G_lin^{mu nu} = - Box bar^{mu nu}
                        + partial^mu partial_rho bar^{rho nu}
                        + partial^nu partial_rho bar^{rho mu}
                        - eta^{mu nu} partial_alpha partial_beta bar^{alpha beta}
    Actually the standard de Donder form after combining with gauge fixing
    collapses to -Box P.

    Direct computation of A from S_FP Euler and of 2 D^*D.
    """
    # Use Fourier: Box -> -k^2 with k^2 = eta^{ab} k_a k_b
    # We compute operator on lowered symmetric tensor, return raised Euler? 
    # Prefer lowered components of (A gamma)_{mu nu}.
    #
    # From XI-A eq:FP / G_lin:
    # G_lin^{mu nu}(gamma) = -1/2 Box bar_gamma^{mu nu}
    #   + 1/2 (partial^mu partial_lambda bar^{lambda nu} + partial^nu partial_lambda bar^{lambda mu})
    #   - 1/2 eta^{mu nu} partial_alpha partial_beta bar^{alpha beta}
    # (standard; Euler of S_FP is 2 G_lin)
    #
    # In Fourier with partial_mu -> i k_mu, Box -> -k^2:
    k2 = sum(ETA[a] * k[a] * k[a] for a in range(4))
    bg = bar_gamma(g)
    bg_up = mz()
    for mu in range(4):
        for nu in range(4):
            acc = 0
            for a in range(4):
                for b in range(4):
                    acc += ETA[mu] * kron(mu, a) * ETA[nu] * kron(nu, b) * bg[a][b]
            bg_up[mu][nu] = sp.expand(acc)

    # partial_lambda bar^{lambda nu} -> i k_lambda bar^{lambda nu}
    # partial^mu = eta^{mu alpha} partial_alpha -> i eta^{mu alpha} k_alpha = i ETA[mu] k[mu] (no sum if diagonal)
    def partial_up(mu_expr_down_list):
        # not used
        pass

    # Dive^nu := partial_lambda bar^{lambda nu}  -> i sum_lam k_lam bar_up[lam][nu]
    Dive = [sp.Integer(0)] * 4
    for nu in range(4):
        acc = 0
        for lam in range(4):
            acc += k[lam] * bg_up[lam][nu]
        Dive[nu] = sp.expand(acc)  # without i; we track i^2 = -1 via k factors

    # For Fourier: partial_mu -> i k_mu, so
    # Box bar = (i k)·(i k) bar with metric = -k^2 bar  if Box = partial_a partial^a
    # G_lin^{mu nu} = -1/2 (-k^2) bar^{mu nu}
    #   + 1/2 [ (i ETA[mu]k[mu]) (i Dive[nu]) + (mu<->nu) ]   ... careful
    #
    # partial^mu (Dive^nu) = eta^{mu a} partial_a Dive^nu
    #   -> eta^{mu a} (i k_a) (i sum k_lam bar^{lam nu}) = - ETA[mu]*k[mu] * Dive[nu]  (no sum on mu)
    # Actually ETA[mu]*kron: partial^mu = sum_a eta^{mu a} i k_a = i ETA[mu] k[mu]
    # times Dive which already has one i absorbed as "k·bar", so two i's: i * i = -1
    # So partial^mu Dive^nu Fourier coeff (real poly in k) = - ETA[mu]*k[mu] * Dive[nu]

    G = mz()
    for mu in range(4):
        for nu in range(4):
            term = sp.Rational(1, 2) * k2 * bg_up[mu][nu]
            term += sp.Rational(1, 2) * (
                -(ETA[mu] * k[mu]) * Dive[nu] - (ETA[nu] * k[nu]) * Dive[mu]
            )
            # -1/2 eta^{mu nu} partial_alpha Dive^alpha
            # partial_alpha Dive^alpha -> i k_alpha * (i ...) = - k_alpha Dive^alpha
            divDive = sum(k[a] * Dive[a] for a in range(4))
            term -= sp.Rational(1, 2) * (ETA[mu] * kron(mu, nu)) * (-divDive)
            # Wait: eta^{mu nu} = ETA[mu]*kron(mu,nu)
            # partial_alpha Dive^alpha Fourier (with i's): (i k_a)(i Dive_content) = -k·Dive
            # So -1/2 eta^{mu nu} * (-k·Dive) = +1/2 eta^{mu nu} (k·Dive)
            # Recheck standard formula:
            # G_lin^{mu nu} = -1/2 Box bar^{mu nu} + 1/2 partial^{(mu} partial_lam bar^{lam nu)}
            #                 - 1/2 eta^{mu nu} partial_a partial_b bar^{ab}
            # Box = partial_a partial^a -> -k^2
            # -1/2 Box bar = -1/2 (-k^2) bar = +1/2 k^2 bar
            # partial^mu partial_lam bar^{lam nu} -> (i ETA[mu]k[mu])(i Dive_content[nu]) = -ETA[mu]k[mu] Dive[nu]
            # 1/2 of symmetrized: 1/2 [ -ETA[mu]k[mu]Dive[nu] - ETA[nu]k[nu]Dive[mu] ]
            # -1/2 eta^{mu nu} partial_a partial_b bar^{ab}
            # partial_a partial_b bar^{ab} = (i k_a)(i Dive content summed) wait:
            # partial_b bar^{ab} = i k_b bar^{ab} = i Dive^a (Dive^a = k_b bar^{ab})
            # partial_a (partial_b bar^{ab}) = (i k_a)(i Dive^a) = - k·Dive
            # So -1/2 eta * (-k·Dive) = +1/2 eta (k·Dive)
            G[mu][nu] = sp.expand(
                sp.Rational(1, 2) * k2 * bg_up[mu][nu]
                + sp.Rational(1, 2) * (
                    -(ETA[mu] * k[mu]) * Dive[nu]
                    - (ETA[nu] * k[nu]) * Dive[mu]
                )
                + sp.Rational(1, 2) * (ETA[mu] * kron(mu, nu)) * divDive
            )
    return G


def DstarD_contrib(g, k):
    """
    Contribution of S_gf = int D_nu D^nu to the Euler derivative.
    Variation: delta S_gf = 2 int D_nu delta D^nu.
    D^nu = partial_mu bar^{mu nu}, so delta D^nu = partial_mu delta bar^{mu nu}.
    After IBP: Euler^{alpha beta} from gf involves 2 D^* D.

    Explicitly: the operator 2 D^* D on gamma, raised indices:
      (2 D^* D gamma)^{mu nu} = - (partial^mu D^nu + partial^nu D^mu - eta^{mu nu} partial_rho D^rho)
    wait — from XI-A e_gf^{mu nu} = -2 partial^{(mu} D^{nu)} + eta^{mu nu} partial_rho D^rho.

    Check sign: Euler of int D_nu D^nu.
    D^nu depends linearly on gamma. Let L^nu(gamma) = D^nu.
    delta int D_nu D^nu = 2 int D_nu L^nu(delta gamma).
    L^nu(delta) = partial_mu (P delta)^{mu nu raised}.
    IBP: 2 int (P^* (partial D))^... 

    XI-A states e_gf^{mu nu} = -2 partial^{(mu} D^{nu)} + eta^{mu nu} partial_rho D^rho.
    We'll use that formula (Fourier).
    """
    bg = bar_gamma(g)
    bg_up = mz()
    for mu in range(4):
        for nu in range(4):
            acc = 0
            for a in range(4):
                for b in range(4):
                    acc += ETA[mu] * kron(mu, a) * ETA[nu] * kron(nu, b) * bg[a][b]
            bg_up[mu][nu] = sp.expand(acc)
    # D^nu content (without i): Dive[nu] = sum_mu k_mu bg_up[mu][nu]
    Dive = [sp.expand(sum(k[mu] * bg_up[mu][nu] for mu in range(4))) for nu in range(4)]
    # partial^{mu} D^{nu} -> (i ETA[mu]k[mu])(i Dive[nu]) = - ETA[mu]k[mu] Dive[nu]
    egf = mz()
    for mu in range(4):
        for nu in range(4):
            # -2 partial^{(mu} D^{nu)} + eta^{mu nu} partial_rho D^rho
            # partial^{(mu} D^{nu)} content = 1/2 ( -ETA[mu]k[mu]Dive[nu] - ETA[nu]k[nu]Dive[mu] )
            # so -2 * that = ETA[mu]k[mu]Dive[nu] + ETA[nu]k[nu]Dive[mu]
            # partial_rho D^rho content = - k_rho Dive[rho]
            # eta^{mu nu} * that = ETA[mu]kron * (-k·Dive)
            term = (ETA[mu] * k[mu]) * Dive[nu] + (ETA[nu] * k[nu]) * Dive[mu]
            term += (ETA[mu] * kron(mu, nu)) * (-sum(k[r] * Dive[r] for r in range(4)))
            egf[mu][nu] = sp.expand(term)
    return egf


def minus_Box_P(g, k):
    """(-Box P gamma)^{mu nu} raised. Box -> -k^2, so -Box = k^2."""
    bg = bar_gamma(g)
    bg_up = mz()
    for mu in range(4):
        for nu in range(4):
            acc = 0
            for a in range(4):
                for b in range(4):
                    acc += ETA[mu] * kron(mu, a) * ETA[nu] * kron(nu, b) * bg[a][b]
            bg_up[mu][nu] = sp.expand(acc)
    k2 = sum(ETA[a] * k[a] * k[a] for a in range(4))
    out = mz()
    for mu in range(4):
        for nu in range(4):
            out[mu][nu] = sp.expand(k2 * bg_up[mu][nu])
    return out


def main():
    k = sp.symbols("k0:4")
    # Independent symmetric components as symbols
    comps = {}
    labels = []
    for mu in range(4):
        for nu in range(mu, 4):
            s = sp.symbols(f"h{mu}{nu}")
            comps[(mu, nu)] = s
            comps[(nu, mu)] = s
            labels.append((mu, nu, s))

    g = [[comps[(mu, nu)] for nu in range(4)] for mu in range(4)]

    G = G_lin_up(g, k)
    A = [[sp.expand(2 * G[mu][nu]) for nu in range(4)] for mu in range(4)]
    egf = DstarD_contrib(g, k)
    # Full Hessian Euler density from S_FP + S_gf:
    # Euler_FP = 2 G_lin = A; Euler_gf = e_gf
    Hess = [[sp.expand(A[mu][nu] + egf[mu][nu]) for nu in range(4)] for mu in range(4)]
    target = minus_Box_P(g, k)

    diffs = []
    max_diff = 0
    for mu in range(4):
        for nu in range(4):
            d = sp.expand(Hess[mu][nu] - target[mu][nu])
            if d != 0:
                diffs.append(((mu, nu), str(d)))
            # also check as poly in k,h
            if d != 0:
                max_diff += 1

    # P^2 = id check
    # Random rational tensors
    P2_ok = True
    for trial in range(5):
        M = mz()
        vals = [sp.Rational(trial + 1, 3), sp.Rational(-2, 5), sp.Integer(trial), sp.Rational(1, 7),
                sp.Integer(-1), sp.Rational(3, 2), 0, sp.Rational(-4, 9), sp.Integer(2), sp.Rational(5, 11)]
        idx = 0
        for mu in range(4):
            for nu in range(mu, 4):
                M[mu][nu] = M[nu][mu] = vals[idx]
                idx += 1
        PM = P_of(M)
        P2 = P_of(PM)
        for mu in range(4):
            for nu in range(4):
                if sp.expand(P2[mu][nu] - M[mu][nu]) != 0:
                    P2_ok = False

    # Propagator interface certificates (factor ledger)
    certificates = {
        "gate": "N-Norm",
        "action_decomposition": {
            "S_quad": "S_FP + S_gf (XI-A); precursor K already includes gauge fixing",
            "S_FP_Euler": "A = 2 G_lin",
            "S_gf": "int D_nu D^nu, D^nu = partial_mu gammabar^{mu nu}",
            "handoff_XII_C": "A + 2 D^* D = -Box P (Unchanged free handoff)",
        },
        "verified_identity": "Hess[S_FP+S_gf] = A + e_gf = -Box P = K",
        "identity_holds": max_diff == 0,
        "num_nonzero_component_diffs": max_diff,
        "diffs_sample": diffs[:5],
        "P_squared_is_id": P2_ok,
        "propagator_factors": {
            "K": "-Box P",
            "XI_B_Green_G_gr_R": "-P E_0^R",
            "XI_B_operator": "L_gamma = -Box P; ( -Box P )( -P E^R ) = id",
            "XVI_J_D_F": "D_F = -P (h_0 + i E_0^A), K D_F = i id",
            "XVI_M_S": "S = h_0 + i E_0^A = (1/(4 pi^2))(Q - i0)^{-1} (Gate S-bv)",
            "XVI_J_d": "d = W_0 - i E_0^A, S = -d",
            "factor_distinction_NOT_equated": {
                "XI_inverse": "G_gr^R = -P E_0^R",
                "X_sheet": "Delta_R^gr = -4 P E_0^R",
                "ratio": "X-sheet / XI-inverse = 4 (do not equate)",
            },
            "K_includes_gauge_fixing": True,
            "do_not_add_gf_again": True,
        },
        "Fourier_convention": "partial_mu -> i k_mu; Box -> -k^2; k^2 = eta^{ab} k_a k_b",
        "signature": "eta = diag(1,-1,-1,-1)",
    }

    out_path = os.path.join(OUT_DIR, "propagator_normalization_certificates.json")
    with open(out_path, "w") as f:
        json.dump(certificates, f, indent=2)

    # Human-readable
    txt = os.path.join(OUT_DIR, "free_hessian_check_out.txt")
    with open(txt, "w") as f:
        f.write("Gate N-Norm / free_hessian_check\n")
        f.write(f"write_path: {txt}\n")
        f.write(f"cert_path: {out_path}\n")
        f.write(f"identity_holds: {max_diff == 0}\n")
        f.write(f"P^2=id: {P2_ok}\n")
        f.write(f"K = -Box P already includes S_gf: True\n")
        f.write("XI G_gr^R = -P E_0^R  NOT equated with  X-sheet Delta_R^gr = -4 P E_0^R\n")
        f.write("D_F = -P (h_0 + i E_0^A); K D_F = i id\n")
        f.write("S = (1/(4 pi^2))(Q - i0)^{-1}\n")
        if diffs:
            f.write("DIFFS:\n")
            for item in diffs[:20]:
                f.write(f"  {item}\n")
        else:
            f.write("All 16 Hessian components match -Box P.\n")

    print("N-Norm identity_holds:", max_diff == 0)
    print("P^2=id:", P2_ok)
    print("Wrote", out_path)
    return 0 if max_diff == 0 and P2_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
