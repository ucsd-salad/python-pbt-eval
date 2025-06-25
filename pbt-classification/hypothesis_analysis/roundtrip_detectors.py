import ast
from typing import Dict, List, Set
from .get_files import AssertTypes, FunctionInfo
from .dfa_utils import TaintRecord
from .ast_utils import get_gen_val_derived_names
from .detector_utils import check_assert_names, merge_all_records, check_is_below, create_rec


def detect_roundtrip(finfo: FunctionInfo, name_rec: Dict[str, TaintRecord], lhs: ast.AST, rhs: ast.AST) -> bool:
    isvalid = False
    gv = None
    dv = None
    gen_vals = [n.id for n in finfo["generated_values"]]
    has_gv = False
    if isinstance(lhs, ast.Name) and lhs.id in gen_vals:
        gv = lhs
        dv = rhs
        has_gv = True
    if isinstance(rhs, ast.Name) and rhs.id in gen_vals:
        if has_gv:
            # should only have one generated value
            return False
        gv = rhs
        dv = lhs

    if gv is not None and dv is not None:
        if not isinstance(dv, ast.Name):
            dv_names: List[str] = [n.id for n in get_gen_val_derived_names(dv)] # type: ignore
            dv_elt_rec: TaintRecord = merge_all_records([name_rec.get(n) for n in dv_names])
        else:
            dv_elt_rec = name_rec.get(dv.id) # type: ignore
            if dv_elt_rec is None:
                # dv_elt is a constant
                return False

        isvalid = gv.id in dv_elt_rec["gen_val_influences"]

    return isvalid


def detect_partial_roundtrip(
    gen_vals: List[str],
    tainted_names: List[str],
    taints_table: Dict[str, Set[str]],
    lhs_names: List[str],
    rhs_names: List[str],
    lhs_rec: Dict[str, TaintRecord],
    rhs_rec: Dict[str, TaintRecord],
) -> bool:
    # if they have the same derived influences, one cannot be derived from the other
    if set(lhs_rec["derived_influences"]) == set(rhs_rec["derived_influences"]):
        return False

    isvalid = False
    # both sides should have all the same gen val influences
    if set(lhs_rec["gen_val_influences"]) == set(rhs_rec["gen_val_influences"]):
        if set(lhs_rec["derived_influences"]).issubset(set(rhs_rec["derived_influences"])):
            # lhs is "above" rhs in tree so all (tainted) lhs names should be tainting all rhs names or they should be the same or they are gen vals
            isvalid = check_is_below(lhs_names, rhs_names, tainted_names, gen_vals, taints_table)
        elif set(rhs_rec["derived_influences"]).issubset(set(lhs_rec["derived_influences"])):
            # rhs is above lhs in tree so all (tainted) rhs names should be tainting all lhs names or they should be the same or they are gen vals
            isvalid = check_is_below(rhs_names, lhs_names, tainted_names, gen_vals, taints_table)

    return isvalid


# def detect_hetero_gv_roundtrip(
#     gen_vals: List[str],
#     tainted_names: List[str],
#     taints_table: Dict[str, Set[str]],
#     lhs_names: List[str],
#     rhs_names: List[str],
#     lhs_rec: Dict[str, TaintRecord],
#     rhs_rec: Dict[str, TaintRecord],
# ) -> bool:
#     # one side should have a subset of the other side's gen vals 
#     isvalid = False
#     if set(lhs_rec["gen_val_influences"]) != set(rhs_rec["gen_val_influences"]):
#         if set(lhs_rec["gen_val_influences"]).issubset(set(rhs_rec["gen_val_influences"])):
#             # lhs is "above" rhs in tree so all (tainted) lhs names should be tainting all rhs names or they should be the same or they are gen vals
#             isvalid = check_is_below(lhs_names, rhs_names, tainted_names, gen_vals, taints_table)
#         elif set(rhs_rec["gen_val_influences"]).issubset(set(lhs_rec["gen_val_influences"])):
#             # rhs is above lhs in tree so all (tainted) rhs names should be tainting all lhs names or they should be the same or they are gen vals
#             isvalid = check_is_below(rhs_names, lhs_names, tainted_names, gen_vals, taints_table)
#         pass
#     return isvalid