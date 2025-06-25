import ast
from typing import Dict, List, Set
from .get_files import AssertTypes, FunctionInfo
from .dfa_utils import TaintRecord
from .ast_utils import get_gen_val_derived_names, ExpressionNode, Assignable
from .detector_utils import check_assert_names, merge_all_records, match_call


# x in y
def detect_inclusion_check(
    assert_stmt: AssertTypes, finfo: FunctionInfo, name_rec: Dict[str, TaintRecord]
) -> tuple[bool, bool]:
    # either lhs is tainted or both are tainted
    match assert_stmt:
        case ast.Assert(ast.Compare(lhs, [ast.In()], [rhs]), _) | ast.Assert(ast.Compare(lhs, [ast.NotIn()], [rhs]), _):
            lhs_names = get_gen_val_derived_names(lhs)
            # if the lhs is not tainted then it's a const inclusion
            if not (any([ln.id in name_rec.keys() for ln in lhs_names])):
                return True, False
            else:
                return False, True
        case ast.Expr(ast.Call(_, [lhs, rhs], _)):
            if check_assert_names(assert_stmt, finfo, ["assertIn", "assertNotIn"]):
                lhs_names = get_gen_val_derived_names(lhs)
                # if the lhs is not tainted then it's a const inclusion
                if not (any([ln.id in name_rec.keys() for ln in lhs_names])):
                    return True, False
                else:
                    return False, True
    return False, False


# isinstance, x == type(y)
def detect_typecheck(assert_stmt: AssertTypes, finfo: FunctionInfo) -> bool:
    is_typecheck = False
    match assert_stmt:
        case ast.Assert(ast.Call(), _):
            if match_call(assert_stmt.test, ["isinstance"]):
                is_typecheck = True
        case ast.Assert(ast.Compare(lhs, [ast.Eq()], [rhs]), _):
            # x == type(y)
            if isinstance(lhs, ast.Call) and match_call(lhs, ["type"]):
                is_typecheck = True
            elif isinstance(rhs, ast.Call) and match_call(rhs, ["type"]):
                is_typecheck = True
        case ast.Assert(ast.Compare(lhs, [ast.Is()], [rhs]), _):
            # x == type(y)
            if isinstance(lhs, ast.Call) and match_call(lhs, ["type"]):
                is_typecheck = True
            elif isinstance(rhs, ast.Call) and match_call(rhs, ["type"]):
                is_typecheck = True
        case ast.Expr():
            if check_assert_names(assert_stmt, finfo, ["assertIsInstance"]):
                is_typecheck = True
    return is_typecheck


# assert a, assertTrue(x) (no comparison)
def detect_const_equality(assert_stmt: AssertTypes, finfo: FunctionInfo, name_rec: Dict[str, TaintRecord]):
    match assert_stmt:
        case (
            ast.Assert(ast.Compare(lhs, [ast.Eq()], [rhs]), _)
            | ast.Assert(ast.Compare(lhs, [ast.Is()], [rhs]), _)
            | ast.Assert(ast.Compare(lhs, [ast.NotEq()], [rhs]), _)
            | ast.Assert(ast.Compare(lhs, [ast.IsNot()], [rhs]), _)
        ):
            lhs_names = get_gen_val_derived_names(lhs)
            rhs_names = get_gen_val_derived_names(rhs)
            return not (
                any([ln.id in name_rec.keys() for ln in lhs_names])
                and any([rn.id in name_rec.keys() for rn in rhs_names])
            )
        case ast.Assert(arg, _):
            # assertTrue(x) case turned into assert x by process_assert()
            # because we checked if it's a pbt, there is at least one name that is tainted in this
            # so, some tainted expr is being checked if it's true => const
            if isinstance(arg, ast.UnaryOp | ast.BinOp | ast.BoolOp | ast.Call | ast.IfExp) or isinstance(
                arg, ast.Name | ast.Subscript | ast.Attribute
            ):
                if isinstance(arg, ast.Name) and arg.id == "isinstance":
                    return False
                return True
        case ast.Expr(ast.Call(_, args, _)):
            if check_assert_names(assert_stmt, finfo, ["assertEqual", "assertEquals", "assertIs"]):
                lhs = args[0]
                rhs = args[1]
                lhs_names = get_gen_val_derived_names(lhs)
                rhs_names = get_gen_val_derived_names(rhs)
                return not (
                    any([ln.id in name_rec.keys() for ln in lhs_names])
                    and any([rn.id in name_rec.keys() for rn in rhs_names])
                )
            if check_assert_names(assert_stmt, finfo, ["assertIsNone", "assertIsNotNone"]):
                return True

    return False
