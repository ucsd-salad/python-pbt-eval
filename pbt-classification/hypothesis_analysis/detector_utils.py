import ast
from typing import List, Dict, Optional, Set
from .dfa_utils import TaintRecord
from .get_files import AssertTypes, FunctionInfo
from .ast_utils import ExpressionNode, get_names_in_value, flatten
from functools import reduce


class DetectionException(Exception):
    def __init__(self, detector, stmt, finfo, error):
        super().__init__(f"\n\nfailed {detector} {str(ast.unparse(stmt))} {finfo['func'].name} {error}")

class ClassificationException(Exception):
    def __init__(self):
        super().__init__(f"all() stmt with a generator expression")


def merge_records(tr1: TaintRecord, tr2: TaintRecord) -> TaintRecord:
    gvi = set(tr1["gen_val_influences"]).union(set(tr2["gen_val_influences"]))
    dvi = set(tr1["derived_influences"]).union(set(tr2["derived_influences"]))
    return TaintRecord(gen_val_influences=list(gvi), derived_influences=list(dvi))


def merge_all_records(lst: List[Optional[TaintRecord]]) -> TaintRecord:
    new_lst = [tr for tr in lst if tr is not None]
    if len(new_lst) != 0:
        return reduce(merge_records, new_lst)
    else:
        return TaintRecord(gen_val_influences=[], derived_influences=[])


def create_rec(
    node: ast.AST, names: List[str], name_rec: Dict[str, TaintRecord], gen_vals: List[str]
) -> Optional[TaintRecord]:
    # no records for constants
    if len(names) == 0 or all([n not in name_rec.keys() for n in names]):
        return None
    # treat any expressions in assert as a "name"
    if not isinstance(node, ast.Name):
        recs = []
        for n in names:
            rec = name_rec.get(n)
            if rec is not None:
                recs.append(rec.copy())
        rec: TaintRecord = merge_all_records(recs)
        rec["derived_influences"] = list(
            set(rec["derived_influences"]).union(
                set(rn for rn in names if (rn in name_rec.keys() and rn not in gen_vals))
            )
        )
    else:
        rec = name_rec.get(node.id)
    return rec


def check_is_below(
    top_names: List[str],
    bot_names: List[str],
    tainted_names: List[str],
    gen_vals: List[str],
    taints_table: Dict[str, Set[str]],
):
    # lhs is "above" rhs in tree so all (tainted) lhs names should be tainting all rhs names or they should be the same or they are gen vals
    isvalid = False
    for n in top_names:
        if n not in tainted_names:
            continue
        isvalid = all(
            [(n == rn or rn in taints_table[n] or rn in gen_vals) for rn in bot_names if rn in tainted_names]
        )
        if not isvalid:
            break
    return isvalid


def get_names_in_assert(a: AssertTypes):
    if isinstance(a, ast.Assert):
        return get_names_in_value(a.test)
    elif isinstance(a.value, ast.Call):
        args = [arg for arg in a.value.args] + [arg.value for arg in a.value.keywords]
        ns = flatten([get_names_in_value(arg) for arg in args])
        return ns
    else:
        return get_names_in_value(a.value)


def check_assert_names(stmt: ast.Expr, finfo: FunctionInfo, assert_names: List[str]):
    """returns true if the name is in the list of possible names"""
    has_self: bool = False
    if finfo["inclass"]:
        func: ast.FunctionDef = finfo["func"]
        args: List[str] = [arg.arg for arg in func.args.args]
        has_self = True if "self" in args else False
    if has_self:
        if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Attribute):
            func_call = stmt.value.func
            if (
                func_call.attr in assert_names
                and isinstance(func_call.value, ast.Name)
                and func_call.value.id == "self"
            ):
                return True
    return False


# split up some kinds of asserts
def process_assert(assert_stmt: AssertTypes, finfo: FunctionInfo) -> tuple[List[AssertTypes], str]:
    asserts = []
    match assert_stmt:
        case ast.Assert(test, _):
            match test:
                # skip nots only for boolean operations (since we treat and & or the same)
                case ast.UnaryOp(ast.Not(), ast.BoolOp()):
                    asserts += process_expr(test.operand)
                case ast.BoolOp(_, values):
                    # split into multiple
                    for v in values:
                        asserts += process_expr(v)
                case ast.Compare(lhs, ops, rhs):
                    if len(ops) > 1:
                        asserts = process_multi_assertion(assert_stmt)
                    elif isinstance(ops[0], ast.NotEq):
                        return [ast.Assert(ast.Compare(lhs, [ast.Eq()], rhs))], "not_equals"
                    elif isinstance(ops[0], ast.IsNot):
                        return [ast.Assert(ast.Compare(lhs, [ast.Is()], rhs))], "not_equals"
                    else:
                        asserts = [assert_stmt]
                case ast.Call(func, args, keywords):
                    # if it's "all" or "any" treat it as an assertion of whatever is inside
                    # also matches assert np.all() etc.
                    if match_call(test, ["all", "any"]):
                        try:
                            if len(args) > 0:
                                asserts = process_expr(args[0])  # handle keywords?
                        except ClassificationException as ex:
                            return [ast.Assert(args[0])], "generator_in_all"
                        except Exception as ex:
                            print(f"exception in process expr: {ex}")
                    else:
                        asserts = process_custom_assertions(assert_stmt)
                case ast.IfExp():
                    asserts += process_expr(test.body)
                    asserts += process_expr(test.orelse)
                case _:
                    asserts = [assert_stmt]
        case ast.Expr(ast.Call(func, args, keywords)):
            if check_assert_names(assert_stmt, finfo, ["assertTrue"]):
                assertion = get_inside_comp(assert_stmt.value, {"expr": 0})
                if assertion["expr"] is not None:
                    asserts += process_expr(assertion["expr"])
                else:
                    asserts = [assert_stmt]
            elif check_assert_names(assert_stmt, finfo, ["assertFalse"]):
                # TODO figure out how to handle this
                assertion = get_inside_comp(assert_stmt.value, {"expr": 0})
                if assertion["expr"] is not None:
                    asserts += process_expr(ast.UnaryOp(ast.Not(), assertion["expr"]))
                else:
                    asserts = [assert_stmt]
            elif check_assert_names(assert_stmt, finfo, ["assertRaises"]):
                return [assert_stmt], "assert_raises"
            else:
                asserts = process_custom_assertions(assert_stmt)
    return asserts, ""


def process_custom_assertions(assert_stmt: AssertTypes) -> List[ast.Assert]:
    asserts = [assert_stmt]
    match assert_stmt:
        case ast.Assert(ast.Call(func, args, keywords), _):
            if match_func_name_any(func, "allclose"):
                # np.allclose(), arrays are equal within a tolerance, returns a bool
                asserts = [assert_stmt]
            if match_func_name_any(func, "isclose"):
                # np.isclose(), returns an array of bools
                asserts = [assert_stmt]
        case ast.Expr(ast.Call(func, args, keywords)):
            if match_call(assert_stmt.value, ["assert_called_with", "assert_called_once_with", "assert_has_calls"]):
                # from mock
                asserts = [assert_stmt]
            elif match_call(assert_stmt.value, ["assert_series_equal", "assert_equal"]):
                # from numpy: np.assert_series_equal
                try:
                    lhs_rhs = get_inside_comp(assert_stmt.value, {"left": 0, "right": 1})
                    asserts = [ast.Assert(ast.Compare(lhs_rhs["left"], [ast.Eq()], [lhs_rhs["right"]]))]
                except IndexError:
                    asserts = [assert_stmt]
            elif match_call(assert_stmt.value, ["assert_all_close"]):
                # from numpy: np.testing.assert_all_close
                asserts = [assert_stmt]
        
    return asserts


def process_expr(e: ExpressionNode) -> List[AssertTypes]:
    asserts = []
    match e:
        case ast.BoolOp(op, values):
            for v in values:
                asserts += process_expr(v)
        case ast.Compare(left, ops, comparators):
            if len(ops) > 1:
                asserts = process_multi_assertion(ast.Assert(e))
            else:
                asserts = [ast.Assert(e)]
        case ast.List(elts, _) | ast.Set(elts) | ast.Tuple(elts, _):
            for elt in elts:
                asserts += process_expr(elt)
        case ast.ListComp(elt, gens) | ast.SetComp(elt, gens) | ast.GeneratorExp(elt, gens):
            asserts = [ast.Assert(e)]
            raise ClassificationException
        case ast.DictComp(k, v, gens):
            # shouldn't happen
            asserts = [ast.Assert(e)]
        case _:
            asserts = [ast.Assert(e)]

    return asserts


def match_func_name_any(f: ast.expr, name: str) -> bool:
    match f:
        case ast.Name(ident, _):  # f(a)
            if ident == name:
                return True
        case ast.Attribute(value, attr, _):  # f.g.h(a)
            if attr == name:
                return True
            return match_func_name_any(value, name)
        case _:
            return False


def match_call(c: ast.Call, names: List[str]) -> bool:
    for name in names:
        if match_func_name_any(c.func, name):
            return True


def get_inside_comp(assert_call: ast.Call, arg_dict: Dict[str, int]) -> Dict[str, Optional[ast.AST]]:
    # look for keyword matches first then positional
    elts = {a: None for a in arg_dict.keys()}
    found_kws = []
    for kw in assert_call.keywords:
        if kw.arg in arg_dict.keys():
            elts[kw.arg] = kw.value
            found_kws.append(kw.arg)
            # update later arg positions bc they are inaccurate
            for a, p in arg_dict.items():
                if p > arg_dict[kw.arg]:
                    arg_dict[a] -= 1
    for kw_name, arg_pos in arg_dict.items():
        if kw_name not in found_kws:
            try:
                arg = assert_call.args[arg_pos]
                if isinstance(arg, ast.Starred):
                    elts[kw_name] = arg.value
                else:
                    elts[kw_name] = arg
            except IndexError:
                print("index error in inside comp: ", ast.unparse(assert_call))
    return elts


def process_multi_assertion(assert_stmt: AssertTypes) -> List[ast.Assert]:
    terms = []
    match assert_stmt:
        case ast.Assert(ast.Compare(left, ops_list, comparators), _):
            # we can split up the assertion into pairs
            for i, comp in enumerate(comparators):
                if i == 0:
                    terms.append(ast.Assert(ast.Compare(left, [ops_list[i]], [comp])))
                else:
                    terms.append(ast.Assert(ast.Compare(comparators[i - 1], [ops_list[i]], [comp])))
    if len(terms) == 0:
        terms = [assert_stmt]
    return terms


def is_equality_check(stmt: AssertTypes, finfo: FunctionInfo) -> Optional[tuple[ast.AST, ast.AST]]:
    match stmt:
        case ast.Assert():
            match stmt.test:
                case ast.Compare(lhs_val, [op], [rhs_val]):
                    # check that all comparisons are equality comparisons
                    if isinstance(op, ast.Eq):
                        return lhs_val, rhs_val
                    # check that all comparisons are equality comparisons
                    if isinstance(op, ast.Is):
                        return lhs_val, rhs_val
                    else:
                        return None
                case _:
                    return None
        case ast.Expr(call):
            if check_assert_names(stmt, finfo, ["assertEqual", "assertIs", "assertEquals"]):
                lhs_val = call.args[0]
                rhs_val = call.args[1]
                return lhs_val, rhs_val
            else:
                return None
        case _:
            return None
