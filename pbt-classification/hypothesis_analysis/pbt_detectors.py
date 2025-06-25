from typing import Optional, Dict, List, Set
from scalpel.cfg import CFG
import ast

from hypothesis_analysis.ast_utils import get_gen_val_derived_names
from .get_files import AssertTypes, FunctionInfo, get_file_contents, get_testing_func_info, get_asserts
from .detector_utils import (
    create_rec,
    get_names_in_assert,
    process_assert,
    TaintRecord,
    DetectionException,
    is_equality_check,
    merge_all_records,
)
from .roundtrip_detectors import detect_roundtrip, detect_partial_roundtrip
from .dfa_utils import dfa_with_rec, create_taints_table
from .comm_detectors import detect_comm, detect_partial_comm
from .const_detectors import detect_const_equality, detect_inclusion_check, detect_typecheck
from .bounds_check_detectors import detect_const_bounds, detect_gen_val_bounds

# detectors
ROUNDTRIP = "roundtrip"
PARTIAL_RT = "partial_roundtrip"
HETERO_RT = "hetero_gv_roundtrip"
COMM = "commutative"
PARTIAL_COMM = "partial_commutative"
CONST_EQ = "const_eq"
CONST_INCL = "const_inclusion"
INCL = "inclusion"
TC = "typecheck"
CONST_BOUNDS = "const_bounds"
GV_BOUNDS = "gen_val_bounds"
REL_BOUNDS = "cross_gv_bounds"
EXCEPTION = "exception"
CONST_NEQ = "const_neq"
GV_NEQ = "gen_val_neq"
FIELDNAMES = [
    ROUNDTRIP,
    PARTIAL_RT,
    HETERO_RT,
    COMM,
    PARTIAL_COMM,
    CONST_EQ,
    CONST_INCL,
    INCL,
    TC,
    CONST_BOUNDS,
    GV_BOUNDS,
    REL_BOUNDS,
    EXCEPTION,
    CONST_NEQ,
    GV_NEQ,
]


def detect_pbts(user: str, project: str, filepath: str) -> List[List[Dict[str, bool]]]:
    try:
        url, filestr = get_file_contents(user, project, filepath)
    except Exception as ex:
        raise Exception(f"failed to get file contents: {ex}")
    try:
        finfos, imports, cfgs = get_testing_func_info(filestr)
    except Exception as ex:
        raise Exception(f"failed to get function information: {ex}")
    di_list: List[List[Dict[str, bool]]] = []
    for i, finfo in enumerate(finfos):
        detections_info: List[Dict[str, bool]] = []
        try:
            assert_stmts = get_asserts(finfo["func"], imports) # type: ignore
        except Exception as ex:
            raise Exception(f"failed to get assert statements: {ex}")
        for assert_stmt in assert_stmts:
            try:
                detections_dict = detect_pbt_in_assert(assert_stmt, finfo, cfgs[i])
            except DetectionException as ex:
                raise ex
            if detections_dict is not None:  # is a pbt
                detections = {
                    "user": user,
                    "project_name": project,
                    "namespace": filepath,
                    "function": finfo["func"].name,
                    "assert_stmt": str(ast.unparse(assert_stmt)),
                }
                for detection, val in detections_dict.items():
                    if val > 0:
                        detections[detection] = "True"
                    else:
                        detections[detection] = "False"
                detections_info.append(detections) # type: ignore
        di_list.append(detections_info)

    return di_list


def detect_pbt_in_assert(stmt: AssertTypes, funcInfo: FunctionInfo, cfg: CFG) -> Optional[Dict[str, bool]]:
    gen_vals = funcInfo["generated_values"]
    _, name_rec = dfa_with_rec(cfg, gen_vals, stmt)
    tainted_names = name_rec.keys()
    asserts, special_assert = process_assert(stmt, funcInfo)
    is_pbt = False
    detections: Dict[str, int] = {f: 0 for f in FIELDNAMES}

    if special_assert == "generator_in_all":
        asserts, name_rec = handle_generator(asserts[0], funcInfo, name_rec) # type: ignore

    for a in asserts:
        assert_names = get_names_in_assert(a)
        # if there are any generated values in the assert statement, then it's a pbt
        if assert_names == [] or not any([n.id in tainted_names for n in assert_names]):
            continue
        is_pbt = True
        try:
            if special_assert == "assert_raises":
                detections[EXCEPTION] += 1
            taints_table = create_taints_table(name_rec)
            if special_assert == "not_equals":
                exec_detectors(a, funcInfo, name_rec, taints_table, detections, is_non_eq=True)
            else:
                exec_detectors(a, funcInfo, name_rec, taints_table, detections)
        except DetectionException as ex:
            raise ex
    if not is_pbt:
        # print(f"not a pbt: {str(ast.unparse(stmt))} {funcInfo['func'].name}")
        return None
    # print(detections)
    return detections # type: ignore


def handle_generator(
    stmt: ast.Assert,
    finfo: FunctionInfo,
    name_rec: Dict[str, TaintRecord],
):
    # [x == x for x in lst]
    match stmt.test:
        case ast.ListComp(elt, gens) | ast.SetComp(elt, gens) | ast.GeneratorExp(elt, gens):
            asserts, _ = process_assert(ast.Assert(elt), finfo)
            for comp in gens:
                iter_names = get_gen_val_derived_names(comp.iter) # type: ignore
                if any([n.id in name_rec.keys() for n in iter_names]):
                    if isinstance(comp.target, ast.Name) and comp.target in name_rec.keys():
                        pass
                    elif isinstance(comp.target, ast.Name):
                        # add the target name to name_rec
                        targ_recs = [name_rec.get(n.id) for n in iter_names]
                        if isinstance(comp.target, ast.Name):
                            name_rec[comp.target.id] = merge_all_records(targ_recs)
        case _:
            asserts = [stmt]
    return asserts, name_rec

def exec_detectors(
    stmt: AssertTypes,
    finfo: FunctionInfo,
    name_rec: Dict[str, TaintRecord],
    taints_table: Dict[str, Set[str]],
    detectors_dict: Dict[str, int],
    is_non_eq=False,
):
    const_comp = False
    try:
        ci, incl = detect_inclusion_check(stmt, finfo, name_rec)
        if ci:
            detectors_dict[CONST_INCL] += 1
            const_comp = True
            return
        if incl:
            detectors_dict[INCL] += 1
            return
    except Exception as ex:
        raise DetectionException(f"{CONST_INCL} / {INCL}", stmt, finfo, ex)
    try:
        if detect_typecheck(stmt, finfo):
            const_comp = True
            detectors_dict[TC] += 1
            return
    except Exception as ex:
        raise DetectionException(TC, stmt, finfo, ex)
    try:
        ce = detect_const_equality(stmt, finfo, name_rec)
        if ce and is_non_eq:
            detectors_dict[CONST_NEQ] += 1
            const_comp = True
        elif ce:
            detectors_dict[CONST_EQ] += 1
            const_comp = True
    except Exception as ex:
        raise DetectionException(CONST_EQ, stmt, finfo, ex)
    try:
        if detect_const_bounds(stmt, finfo, name_rec):
            detectors_dict[CONST_BOUNDS] += 1
            const_comp = True
    except Exception as ex:
        raise DetectionException(CONST_BOUNDS, stmt, finfo, ex)
    if not const_comp:
        try:
            gv, rel = detect_gen_val_bounds(stmt, finfo, name_rec)
            if gv:
                detectors_dict[GV_BOUNDS] += 1
            if rel:
                detectors_dict[REL_BOUNDS] += 1
        except Exception as ex:
            raise DetectionException(f"{GV_BOUNDS} / {REL_BOUNDS}", stmt, finfo, ex)

        eq_sides = is_equality_check(stmt, finfo)
        if eq_sides is None:
            return
        if eq_sides is not None and is_non_eq:
            detectors_dict[GV_NEQ] += 1
            return
        lhs, rhs = eq_sides
        gen_vals = [n.id for n in finfo["generated_values"]]

        try:
            rt = detect_roundtrip(finfo, name_rec, lhs, rhs)
            if rt:
                detectors_dict[ROUNDTRIP] += 1
        except Exception as ex:
            raise DetectionException(ROUNDTRIP, stmt, finfo, ex)

        if not (isinstance(lhs, ast.Name) and lhs.id in gen_vals) and not (
            isinstance(rhs, ast.Name) and rhs.id in gen_vals
        ):
            # for the following detections, neither lhs nor rhs can be a generated value
            tainted_names = name_rec.keys()
            lhs_names: List[str] = [n.id for n in get_gen_val_derived_names(lhs)] # type: ignore
            lhs_rec = create_rec(lhs, lhs_names, name_rec, gen_vals)
            rhs_names: List[str] = [n.id for n in get_gen_val_derived_names(rhs)] # type: ignore
            rhs_rec = create_rec(rhs, rhs_names, name_rec, gen_vals)

            if rhs_rec is None or lhs_rec is None:
                # one side isn't tainted
                return

            try:
                if detect_partial_roundtrip(gen_vals, tainted_names, taints_table, lhs_names, rhs_names, lhs_rec, rhs_rec): # type: ignore
                    detectors_dict[PARTIAL_RT] += 1
                    # check if testing idempotence
            except Exception as ex:
                raise DetectionException(PARTIAL_RT, stmt, finfo, ex)
            # try:
            #     if detect_hetero_gv_roundtrip(gen_vals, tainted_names, taints_table, lhs_names, rhs_names, lhs_rec, rhs_rec):  # type: ignore
            #         detectors_dict[HETERO_RT] += 1
            #         # check if testing idempotence
            # except Exception as ex:
            #     raise DetectionException(PARTIAL_RT, stmt, finfo, ex)
            try:
                if detect_comm(gen_vals, tainted_names, taints_table, lhs_names, rhs_names, lhs_rec, rhs_rec):  # type: ignore
                    detectors_dict[COMM] += 1
            except Exception as ex:
                raise DetectionException(COMM, stmt, finfo, ex)
            try:
                if detect_partial_comm(tainted_names, taints_table, lhs_names, rhs_names, lhs_rec, rhs_rec):  # type: ignore
                    detectors_dict[PARTIAL_COMM] += 1
            except Exception as ex:
                raise DetectionException(PARTIAL_COMM, stmt, finfo, ex)

    return
