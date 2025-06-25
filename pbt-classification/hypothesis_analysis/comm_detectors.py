import ast
from typing import Dict, List, Set, Optional
from .get_files import AssertTypes, FunctionInfo
from .dfa_utils import TaintRecord
from .ast_utils import get_gen_val_derived_names
from .detector_utils import create_rec, check_is_below


def detect_comm(
    gen_vals: List[str],
    tainted_names: List[str],
    taints_table: Dict[str, Set[str]],
    lhs_names: List[str],
    rhs_names: List[str],
    lhs_rec: Dict[str, TaintRecord],
    rhs_rec: Dict[str, TaintRecord],
) -> bool:
    isvalid = False
    # gen val influences must overlap
    if set(lhs_rec["gen_val_influences"]).intersection(set(rhs_rec["gen_val_influences"])) != set():
        if set(lhs_rec["derived_influences"]).intersection(set(rhs_rec["derived_influences"])) == set():
            if set(lhs_rec["derived_influences"]) == set() and set(rhs_rec["derived_influences"]) == set():
                isvalid = True
            elif set(lhs_rec["derived_influences"]) == set():
                isvalid = not check_is_below(lhs_names, rhs_names, tainted_names, gen_vals, taints_table)
            elif set(rhs_rec["derived_influences"]) == set():
                isvalid = not check_is_below(rhs_names, lhs_names, tainted_names, gen_vals, taints_table)
            else:
                # overlapping gen val influences but disjoint (but nonempty) derived influences 
                isvalid = True

    return isvalid


def detect_partial_comm(
    tainted_names: List[str],
    taints_table: Dict[str, Set[str]],
    lhs_names: List[str],
    rhs_names: List[str],
    lhs_rec: Dict[str, TaintRecord],
    rhs_rec: Dict[str, TaintRecord],
) -> bool:
    isvalid = False
    # gen val influences should overlap
    if set(lhs_rec["gen_val_influences"]).intersection(set(rhs_rec["gen_val_influences"])) != set():
        # derived influences should overlap
        intersection = set(lhs_rec["derived_influences"]).intersection(set(rhs_rec["derived_influences"]))
        if intersection == set():
            return False
        # but not be subsets
        if not check_subset_lists(lhs_rec["derived_influences"], rhs_rec["derived_influences"]):
            isvalid = True
        # but if they have the exact same derived influences, then it's okay
        elif set(lhs_rec["derived_influences"]) == set(rhs_rec["derived_influences"]):
            isvalid = True
        # or if one of them has no derived influences but they don't have the exact same gen val influences
        elif (lhs_rec["derived_influences"] == [] or rhs_rec["derived_influences"] == []) and (
            set(lhs_rec["gen_val_influences"]) != (set(rhs_rec["gen_val_influences"]))
        ):
            isvalid = True
        else:
            # or if one side does not taint the other then it's okay

            # every tainted rhs name is tainted by some lhs name 
            lhs_taints_rhs = False
            for n in rhs_names:
                if n not in tainted_names:
                    continue
                # if an lhs name taints a rhs name 
                if any([ln in taints_table[n] for ln in lhs_names]):
                    lhs_taints_rhs = True
                else:
                    lhs_taints_rhs = False
                    break
            if not lhs_taints_rhs:
                # every tainted lhs name is tainted by some rhs name  
                rhs_taints_lhs = False
                for n in lhs_names:
                    if n not in tainted_names:
                        continue
                    # if an rhs name taints a lhs name 
                    if any([rn in taints_table[n] for rn in rhs_names]):
                        rhs_taints_lhs = True
                    else:
                        rhs_taints_lhs = False
                        break
                if not rhs_taints_lhs:
                    isvalid = True

    return isvalid


def check_subset_lists(l1: List, l2: List) -> bool:
    s1 = set(l1)
    s2 = set(l2)
    return s1.issubset(s2) or s2.issubset(s1)
