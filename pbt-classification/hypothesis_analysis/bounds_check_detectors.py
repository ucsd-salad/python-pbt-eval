import ast
from typing import Dict, List
from .get_files import AssertTypes, FunctionInfo
from .dfa_utils import TaintRecord
from .ast_utils import get_gen_val_derived_names
from .detector_utils import check_assert_names, merge_all_records


ALLOWED_ASSERT_NAMES = ["assertGreater", "assertGreaterEqual", "assertLess", "assertLessEqual"]


# bounds are not derived from a generated value
def detect_const_bounds(assert_stmt: AssertTypes, finfo: FunctionInfo, name_rec: Dict[str, TaintRecord]):
    match assert_stmt:
        case ast.Assert(ast.Compare(lhs, [op], [rhs]), _):
            if isinstance(op, ast.Lt | ast.LtE | ast.Gt | ast.GtE):
                lhs_names = get_gen_val_derived_names(lhs)
                rhs_names = get_gen_val_derived_names(rhs)
                is_tainted_l = any([ln.id in name_rec.keys() for ln in lhs_names])
                is_tainted_r = any([rn.id in name_rec.keys() for rn in rhs_names])
                # one of the two is true but not both
                return (is_tainted_l != is_tainted_r) and (is_tainted_l or is_tainted_r)
        case ast.Expr(ast.Call(func, [lhs, rhs], kws)):
            if check_assert_names(assert_stmt, finfo, ALLOWED_ASSERT_NAMES):
                lhs_names = get_gen_val_derived_names(lhs)
                rhs_names = get_gen_val_derived_names(rhs)
                is_tainted_l = any([ln.id in name_rec.keys() for ln in lhs_names])
                is_tainted_r = any([rn.id in name_rec.keys() for rn in rhs_names])
                # one of the two is true but not both
                return (is_tainted_l != is_tainted_r) and (is_tainted_l or is_tainted_r)
    return False


def merge_name_recs(names, name_rec) -> TaintRecord:
    recs = []
    for n in names:
        rec = name_rec.get(n)
        if rec is not None:
            recs.append(rec.copy())
    new_rec: TaintRecord = merge_all_records(recs)
    new_rec["derived_influences"] = list(
        set(new_rec["derived_influences"]).union(set(ln for ln in names if ln in name_rec.keys()))
    )
    return new_rec


# bounds are derived from the same generated value
def detect_gen_val_bounds(
    assert_stmt: AssertTypes, finfo: FunctionInfo, name_rec: Dict[str, TaintRecord]
) -> tuple[bool, bool]:
    lhs_names = []
    rhs_names = []
    is_tainted_l = False
    is_tainted_r = False
    match assert_stmt:
        case ast.Assert(ast.Compare(lhs, [op], [rhs]), _):
            if isinstance(op, ast.Lt | ast.LtE | ast.Gt | ast.GtE):
                lhs_names = get_gen_val_derived_names(lhs)
                rhs_names = get_gen_val_derived_names(rhs)
                is_tainted_l = any([ln.id in name_rec.keys() for ln in lhs_names])
                is_tainted_r = any([rn.id in name_rec.keys() for rn in rhs_names])
        case ast.Expr(ast.Call(func, [lhs, rhs], kws)) | ast.Expr(ast.Call(func, [lhs, rhs, _], kws)):
            if check_assert_names(assert_stmt, finfo, ALLOWED_ASSERT_NAMES):
                lhs_names = get_gen_val_derived_names(lhs)
                rhs_names = get_gen_val_derived_names(rhs)
                is_tainted_l = any([ln.id in name_rec.keys() for ln in lhs_names])
                is_tainted_r = any([rn.id in name_rec.keys() for rn in rhs_names])
    if is_tainted_l and is_tainted_r:
        lhs_rec = merge_name_recs(lhs_names, name_rec)
        rhs_rec = merge_name_recs(rhs_names, name_rec)
        if set(lhs_rec["gen_val_influences"]) == set(rhs_rec["gen_val_influences"]):
            return True, False
        else:
            return False, True
    else:
        return False, False
