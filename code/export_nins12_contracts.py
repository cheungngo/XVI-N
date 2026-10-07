#!/usr/bin/env python3
"""Regenerate N-Ins.1/2 completion_space.json and insertion_contract.json.

Must agree with hypotheses H4 / body Sec. N-Ins.4 / Lemma P0Q0A0:
insertion completion I_t = F_t + A_0 + κ A_1 (NOT completion of prepared S_D).
pass=true means contract text agrees with those declarations; it does NOT claim
universal N-Ins.4 completion (still Unresolved universally).
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from package_paths import write_json

REVISION = "r12"

ANSATZ = (
    "regular, seed-preserving, antifield-linear insertion completion "
    "I_t = F_t + A_0 + kappa A_1 in the Gate N-Ins kernel class, with "
    "A_0 = int(h^{*mu nu} U_{mu nu} + phi* V + c*_mu W^mu), "
    "gh(U,V,W)=(1,1,2), and seed I_t|_{c=cbar=b=Phi*=0} = F_t"
)

EQUATIONS = (
    "insertion closure: Q_inv I_t = O(kappa^2); "
    "degree-zero: P_0 Q_0 A_0 = -s_0 F_t "
    "(field-only projection of Q_0 A_0; Lemma P0Q0A0). "
    "N-Ins.4 remains Unresolved as a universal completion statement."
)


def main():
    completion_space = {
        "revision": REVISION,
        "gate": "N-Ins.1",
        "status": "Constructed",
        "minimal_sector": "metric + real scalar + diffeomorphism ghosts (frozen classical BV)",
        "ansatz": ANSATZ,
        "ghost_numbers": {"h": 0, "phi": 0, "c": 1, "cbar": -1, "b": 0},
        "U_V_W_ghost_numbers": {"U": 1, "V": 1, "W": 2},
        "seed_preservation": (
            "I_t|_{c=cbar=b=Phi*=0} = F_t (independent of b); "
            "t_D / E_F / J_t as in XVI-I / Gate N-Ins.2"
        ),
        "degrees": {"antifield_polynomial": "linear", "kappa": "through O(kappa)"},
        "derivative_bounds": (
            "finite-order classical densities as declared for the Gate N-Ins kernel class "
            "(H4 / body Sec. N-Ins.4); no new analytic bound is introduced by this export"
        ),
        "kernels": "inherited XII-D / XVI-H compact root; not re-derived",
        "support": "compactly supported cutoffs as in Lem. support / XII-D",
        "regularity": "C^infty",
        "inverse_operators": (
            "advanced/retarded Green operators E_m^A inherited only; "
            "scalar vs tensor inverses distinguished as in the inherited root; "
            "no new inverse operators"
        ),
        "equivalence": (
            "no new equivalence relation; any field-redefinition / free-equation "
            "language refers only to the inherited factorization scaffold "
            "(Lemma P0Q0A0 / Gate N-Ins), not a newly declared relation"
        ),
        "equations": EQUATIONS,
        "outcome_with_onshell_witness": (
            "N-Ins.3 conditional massless obstruction (Route A) + certified small-mass "
            "interval; Route B and arbitrary prescribed m>0 unresolved; "
            "N-Ins.4 Unresolved universally"
        ),
        "pass": True,
        "pass_means": (
            "contract text agrees with H4 / Lemma P0Q0A0 / Thm massless hypotheses; "
            "does not claim universal N-Ins.4 completion"
        ),
    }
    contract = {
        "revision": REVISION,
        "gate": "N-Ins.1/2",
        "option": "insertion completion interface (Gate N-Ins)",
        "functional_seed": "F_t / t_D / E_F / J_t as constructed",
        "external_data": "g, sigma, chi_I fixed-external policy",
        "source": "XII-C / XII-D / XVI-I inheritance",
        "completion_space": "see completion_space.json (insertion class I_t=F_t+A_0+kappa A_1)",
        "analytic_domain": "Route A ambient-smooth configurations; Route B not claimed",
        "Q_U": "Q_U = Q_inv (invariant differential). Separate operation: field-only projection P_0 Q_0 A_0 (Lemma P0Q0A0).",
        "ansatz": ANSATZ,
        "equations": EQUATIONS,
        "pass": True,
        "pass_means": completion_space["pass_means"],
    }
    write_json("insertion", "completion_space.json", completion_space)
    write_json("insertion", "insertion_contract.json", contract)
    write_json(
        "insertion",
        "completion_ansatz.json",
        {
            "revision": REVISION,
            "ansatz": ANSATZ,
            "A_0": "int(h* U + phi* V + c* W)",
            "ghost_numbers_UVW": {"U": 1, "V": 1, "W": 2},
            "seed": "I_t|_{c=cbar=b=Phi*=0}=F_t",
            "pass": True,
            "pass_means": completion_space["pass_means"],
        },
    )
    print("wrote completion_space, insertion_contract, completion_ansatz (r12 / H4-aligned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
