import ast
from typing import Dict, List, TypedDict, Set
from scalpel.cfg import CFG, Block
from .ast_utils import get_names_in_stmts, get_names_in_value
from .get_files import AssertTypes


class TaintRecord(TypedDict):
    gen_val_influences: List[str]
    derived_influences: List[str]


class Visitor(ast.NodeVisitor):
    def __init__(self, names: List[ast.Name], names_rec: Dict[str, TaintRecord], gen_val_ids: List[str]):
        self.varnames: List[str] = [n.id for n in names]
        self.found_indices: List[int] = []
        self.path: List[ast.AST] = []
        self.taint_rec: TaintRecord = TaintRecord(gen_val_influences=[], derived_influences=[])
        self.names_rec: Dict[str, TaintRecord] = names_rec
        self.gen_val_ids = gen_val_ids

    def generic_visit(self, node: ast.AST):
        self.path.append(node)
        if hasattr(node, "id"):  # Variables.
            if node.id in self.varnames:
                self.found_indices.append(len(self.path) - 1)  # index of node in path
                self.taint_rec["gen_val_influences"] += self.names_rec.get(node.id)["gen_val_influences"]
                der_influences = (
                    self.names_rec.get(node.id)["derived_influences"] + [node.id]
                    if node.id not in self.gen_val_ids
                    else self.names_rec.get(node.id)["derived_influences"]
                )
                self.taint_rec["derived_influences"] += der_influences
        return super().generic_visit(node)


def trace_block_with_taint_record(
    block: Block, from_gen_val: List[ast.Name], from_gen_val_rec: Dict[str, TaintRecord], gen_val_ids: List[str]
) -> tuple[List[ast.AST], List[ast.Name], Dict[str, TaintRecord], bool]:

    stmts_using_genval: List[ast.AST] = []
    names_untainted_in_block: List[ast.Name] = []
    existing_taints: List[ast.Name] = from_gen_val.copy()  # avoids updating the original generated values
    existing_taints_rec: Dict[str, TaintRecord] = from_gen_val_rec.copy()
    add_new_taints: bool = False
    # get the variable names used to test an if/while statement
    exitcase_names = []
    for link in block.predecessors:
        if any([isinstance(s, ast.If) or isinstance(s, ast.While) for s in link.source.statements]):
            exitcase_names = [n.id for n in get_names_in_value(link.exitcase)]
    for stmt in block.statements:
        visitor: Visitor = Visitor(existing_taints, existing_taints_rec, gen_val_ids)
        visitor.generic_visit(stmt)
        # check if we are basing control flow on a tainted value
        for en in exitcase_names:
            # include gen val and derived influences arising from the if/while test 
            if en in existing_taints_rec.keys():
                visitor.taint_rec["gen_val_influences"] = list(set(visitor.taint_rec["gen_val_influences"] + (existing_taints_rec[en]["gen_val_influences"])))
                if en not in gen_val_ids:
                    visitor.taint_rec["derived_influences"] = list(set(visitor.taint_rec["derived_influences"] + existing_taints_rec[en]["derived_influences"] + [en]))
        # if we have found nodes that contain any of the old tainted values in the statement
        if len(visitor.found_indices) > 0 or len(visitor.taint_rec["gen_val_influences"]) > 0:
            add_new_taints = True
            # if we're calling an assert function, then the taints remain the same
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call: ast.Call = stmt.value
                if isinstance(call.func, ast.Attribute) and call.func.attr.startswith("assert"):
                    add_new_taints = False
            # check if anything needs to be untainted
            elif isinstance(stmt, (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.NamedExpr)):
                targets: List[ast.AST] = []
                if not hasattr(stmt, "targets"):  # janky workaround because only assign has a list of targets
                    targets = [stmt.target]
                else:
                    targets = stmt.targets
                # if any of the targets are names and are tainted, we don't care about non-names (e.g. subscripts)
                if any(
                    [isinstance(targ, ast.Name) and (targ.id in [n.id for n in existing_taints]) for targ in targets]
                ):
                    # get the names of variables in rhs
                    val_names: List[ast.Name] = get_names_in_value(stmt.value)
                    # if rhs is not tainted then the entire statement is not tainted
                    if not any([(n.id in [na.id for na in existing_taints]) for n in val_names]):
                        add_new_taints = False
                        for targ in targets:
                            # if my lhs was a tainted value, untaint it
                            if targ.id in [n.id for n in existing_taints]:
                                names_untainted_in_block.append(targ)
                        # filter out the untainted names
                        existing_taints = [
                            n for n in existing_taints if n.id not in [un.id for un in names_untainted_in_block]
                        ]
                        existing_taints_rec = {
                            k: existing_taints_rec[k]
                            for k in existing_taints_rec
                            if k in [n.id for n in existing_taints]
                        }

            # we're not in an assert and nothing needs to be untainted
            if add_new_taints:
                orig_len_existing_taints = len(existing_taints)
                stmts_using_genval.append(stmt)
                names_in_tainted_stmt: List[ast.Name] = get_names_in_stmts(stmt)
                # update our list of existing tainted names to include these new ones we've found
                # don't mark while or if tests as tainted unless they already are tainted
                if not (isinstance(stmt, ast.If) or isinstance(stmt, ast.While)):
                    for name in names_in_tainted_stmt:
                        if name.id not in [n.id for n in existing_taints]:
                            existing_taints.append(name)
                            existing_taints_rec[name.id] = visitor.taint_rec
                # we didn't actually find any new ones
                if len(existing_taints) == orig_len_existing_taints:
                    add_new_taints = False
    return stmts_using_genval, existing_taints, existing_taints_rec, add_new_taints


def dfa_with_rec(
    cfg: CFG, gen_val: List[ast.Name], assert_stmt: AssertTypes
) -> tuple[List[ast.AST], Dict[str, TaintRecord]]:
    worklist = cfg.get_all_blocks()
    stmts_using_genval = []
    names_of_tainted_vars = gen_val
    names_of_tainted_vars_w_rec = {
        gv.id: TaintRecord(gen_val_influences=[gv.id], derived_influences=[]) for gv in gen_val
    }
    # if we're only analyzing up to this assert statement, then truncate the worklist
    worklist_section = len(worklist)
    for i, block in enumerate(worklist):
        last_stmt = block.statements[-1]
        if last_stmt == assert_stmt:
            worklist_section = i + 1
            break
        elif assert_stmt in block.statements:
            worklist_section = i + 1
            break
    truncated_worklist = worklist[:worklist_section]
    worklist = truncated_worklist
    while worklist:
        block = worklist.pop(0)
        # if we found new tainted values, then add them to the list and add the next blocks to the worklist
        new_stmts_using_genval, updated_taints, updated_taints_w_rec, added_new_taints = trace_block_with_taint_record(
            block, names_of_tainted_vars, names_of_tainted_vars_w_rec, [n.id for n in gen_val]
        )
        names_of_tainted_vars = updated_taints
        stmts_using_genval += new_stmts_using_genval
        names_of_tainted_vars_w_rec = updated_taints_w_rec
        if added_new_taints:  # don't need to do this if we only removed taints
            # add next blocks to worklist (only if they stay within the original worklist)
            worklist += [exitlink.target for exitlink in block.exits if exitlink.target in truncated_worklist]
    return stmts_using_genval, names_of_tainted_vars_w_rec


def create_taints_table(name_rec: Dict[str, TaintRecord]):
    # maintains a list of what names each name taints
    all_names = name_rec.keys()
    taints_table: Dict[str, Set[str]] = {name: set() for name in all_names}
    for name in all_names:
        for n, rec in name_rec.items():
            dis = rec["derived_influences"]
            if name in dis:
                taints_table[name].add(n)
    return taints_table
