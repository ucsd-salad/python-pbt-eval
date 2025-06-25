from typing import List
import ast
from functools import reduce

type Literal = ast.Constant | ast.FormattedValue | ast.JoinedStr | ast.List | ast.Tuple | ast.Set | ast.Dict
type Comprehensions = ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp
type ExpressionNode = ast.UnaryOp | ast.BinOp | ast.BoolOp | ast.Compare | ast.Call | ast.IfExp | ast.Attribute | ast.Subscript | Comprehensions
type Value = ExpressionNode | Literal | ast.Name | ast.Lambda | ast.Yield | ast.YieldFrom
type Assignable = ast.Name | ast.Subscript | ast.Attribute | ast.Tuple  # tuple: in the case of multiple return values
type Statement = ast.Assign | ast.AnnAssign | ast.AugAssign | ast.NamedExpr | ast.Assert | ast.If | ast.For | ast.While | ast.Try | ast.ExceptHandler | ast.With | ast.withitem | ast.Expr


def flatten(matrix: List[List]):
    return list(reduce(lambda x, y: x + y, matrix, []))


def get_names_in_value(val: Value) -> List[ast.Name]:
    names: List[ast.Name] = []
    match val:
        case (
            ast.UnaryOp()
            | ast.BinOp()
            | ast.BoolOp()
            | ast.Compare()
            | ast.Call()
            | ast.IfExp()
            | ast.Attribute()
            | ast.Subscript()
            | ast.ListComp()
            | ast.SetComp()
            | ast.DictComp()
            | ast.GeneratorExp()
        ):
            names = get_names_in_expr(val)
        case (
            ast.Constant() | ast.FormattedValue() | ast.JoinedStr() | ast.List() | ast.Tuple() | ast.Set() | ast.Dict()
        ):
            if isinstance(val, (ast.List, ast.Tuple, ast.Set)):
                for elt in val.elts:
                    names += get_names_in_value(elt)
            if isinstance(val, ast.Dict):
                keys = val.keys
                for k in keys:
                    if k is not None:
                        names += get_names_in_expr(k)
                vals = val.values
                for v in vals:
                    names += get_names_in_expr(v)
        case ast.Name():
            names = [val]
        case ast.Lambda():
            # names = get_names_in_args(val.args)
            names = get_names_in_expr(val.body)
            arg_names = [arg.arg for arg in val.args.args]
            removed_names = []
            for arg in arg_names:
                for n in names:
                    if n.id == arg:
                        removed_names.append(n)
            for n in removed_names:
                names.remove(n)
        case ast.Yield():
            names = get_names_in_expr(val.value) if val.value is not None else []
        case ast.YieldFrom():
            names = get_names_in_expr(val.value)
    return names


def get_names_in_expr(e: ExpressionNode) -> List[ast.Name]:
    names: List[ast.Name] = []
    match e:
        case ast.UnaryOp():
            names = get_names_in_value(e.operand)
        case ast.BinOp():
            names = get_names_in_value(e.left)
            names += get_names_in_value(e.right)
        case ast.BoolOp():
            for val in e.values:
                names += get_names_in_value(val)
        case ast.Compare():
            names = get_names_in_value(e.left)
            for comp in e.comparators:
                names += get_names_in_value(comp)
        case ast.Call():
            args = e.args
            kws = e.keywords
            for arg in args:
                if isinstance(arg, ast.Starred):
                    names += get_names_in_value(arg.value)
                names += get_names_in_value(arg)
            for kw in kws:
                names += get_names_in_value(kw.value)
            # call can be a function or an attribute
            if isinstance(e.func, ast.Attribute):
                names += get_names_in_value(e.func)
        case ast.IfExp():
            names = get_names_in_value(e.test)
            names += get_names_in_value(e.body)
            names += get_names_in_value(e.orelse)
        case ast.Attribute():
            names = get_names_in_value(e.value)
        case ast.Subscript():
            # don't care about the indices since they can get mixed up later
            names = get_names_in_value(e.value) + get_names_in_value(e.slice)
        case ast.ListComp() | ast.SetComp() | ast.DictComp() | ast.GeneratorExp():  # must match on classes
            gen_targets = flatten([get_names_in_value(gen.target) for gen in e.generators])
            if isinstance(e, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
                names = get_names_in_value(e.elt)
            elif isinstance(e, ast.DictComp):
                names = get_names_in_value(e.key)
                names += get_names_in_value(e.value)
            names += flatten([get_names_in_value(generator.iter) for generator in e.generators])
            # remove the target from names since that's out of scope outside the comprehension
            names = list(filter((lambda x: x.id not in [n.id for n in gen_targets]), names))
    return names


def get_names_in_assignable(a: Assignable) -> List[ast.Name]:
    names: List[ast.Name] = []
    match a:
        case ast.Name:
            names = [a]
        case ast.Subscript():
            names = get_names_in_expr(a.value)
        case ast.Attribute():
            names = get_names_in_expr(a.value)
        case ast.Tuple():
            for elt in a.elts:
                names += get_names_in_expr(elt)
    return names


def get_names_in_stmts(s: Statement) -> List[ast.Name]:
    names: List[ast.Name] = []
    match s:
        case ast.Assign():
            targets = s.targets
            for targ in targets:
                names += get_names_in_value(targ)
        case ast.AnnAssign():
            targ = s.target
            names = get_names_in_assignable(targ)  # guaranteed to be an assignable
        case ast.AugAssign() | ast.NamedExpr():
            targ = s.target
            names = get_names_in_assignable(targ)  # guaranteed to be an assignable
        case ast.Assert():
            pass
            # nothing in an assert statement should be considered tainted?
        case ast.If():
            names = get_names_in_value(s.test)
        case ast.For():
            names = get_names_in_value(s.target)
        case ast.While():
            names = get_names_in_value(s.test)
        case ast.Try():  # don't need this: won't have any generated names
            pass
        case ast.ExceptHandler():  # handled above
            pass
        case ast.With():
            for item in s.items:
                if item.optional_vars is None:
                    names += get_names_in_value(item.context_expr)
                else:
                    names += get_names_in_value(item.optional_vars)
        case ast.withitem():  # handled above
            pass
        case ast.Expr():
            names = get_names_in_value(s.value)
    return names


def get_gen_val_derived_names(val: Value):
    names: List[ast.Name] = []
    match val:
        case (
            ast.UnaryOp()
            | ast.BinOp()
            | ast.BoolOp()
            | ast.Compare()
            | ast.Call()
            | ast.IfExp()
            | ast.Attribute()
            | ast.Subscript()
            | ast.ListComp()
            | ast.SetComp()
            | ast.DictComp()
            | ast.GeneratorExp()
        ):
            names = get_gen_val_derived_names_in_expr(val)
        case (
            ast.Constant() | ast.FormattedValue() | ast.JoinedStr() | ast.List() | ast.Tuple() | ast.Set() | ast.Dict()
        ):
            # none of these are a transformation of a variable
            pass
        case ast.Name():
            names = [val]
        case ast.Lambda():
            names = get_names_in_expr(val.body)
            arg_names = [arg.arg for arg in val.args.args]
            removed_names = []
            for arg in arg_names:
                for n in names:
                    if n.id == arg:
                        removed_names.append(n)
            for n in removed_names:
                names.remove(n)
        case ast.Yield():
            names = get_names_in_expr(val.value) if val.value is not None else []
        case ast.YieldFrom():
            names = get_names_in_expr(val.value)
    return names


def get_gen_val_derived_names_in_expr(e: ExpressionNode) -> List[ast.Name]:
    names: List[ast.Name] = []
    match e:
        case ast.UnaryOp():
            names = get_names_in_value(e.operand)
        case ast.BinOp():
            names = get_names_in_value(e.left)
            names += get_names_in_value(e.right)
        case ast.BoolOp():
            for val in e.values:
                names += get_names_in_value(val)
        case ast.Compare():
            pass
        case ast.Call():
            args = e.args
            kws = e.keywords
            for arg in args:
                if isinstance(arg, ast.Starred):
                    names += get_names_in_value(arg.value)
                names += get_names_in_value(arg)
            for kw in kws:
                names += get_names_in_value(kw.value)
            # call can be a function or an attribute
            if isinstance(e.func, ast.Attribute):
                names += get_names_in_value(e.func)
        case ast.IfExp():
            names = get_names_in_value(e.body)
            names += get_names_in_value(e.orelse)
        case ast.Attribute():
            names = get_names_in_value(e.value)
        case ast.Subscript():
            # don't care about the indices since they can get mixed up later
            names = get_names_in_value(e.value)
        case ast.ListComp() | ast.SetComp() | ast.DictComp() | ast.GeneratorExp():
            gen_targets = flatten([get_names_in_value(gen.target) for gen in e.generators])
            if isinstance(e, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
                names = get_names_in_value(e.elt)
            elif isinstance(e, ast.DictComp):
                names = get_names_in_value(e.key)
                names += get_names_in_value(e.value)
            names += flatten([get_names_in_value(generator.iter) for generator in e.generators])
            # remove the target from names since that's out of scope outside the comprehension
            names = list(filter((lambda x: x.id not in [n.id for n in gen_targets]), names))
    return names
