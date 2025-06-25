from typing import Optional, List, TypedDict, Dict
import ast
from github import Github, GithubException, Auth
from dotenv import dotenv_values
from scalpel.cfg import CFGBuilder, CFG, Block


type AssertTypes = ast.Assert | ast.Expr


class ImportName(TypedDict):
    alias: ast.alias
    parent_module: Optional[str]


class FunctionInfo(TypedDict):
    func: ast.FunctionDef
    inclass: bool
    isstaticorclass: bool
    given_dec: Optional[ast.Call]
    generated_values: List[ast.Name]


def get_file_contents(user: str, project: str, filepath: str) -> tuple[str, str]:
    config = dotenv_values(".env")
    auth = Auth.Token(config["GITHUB_ACCESS_TOKEN"])
    with Github(auth=auth) as g:
        try:
            repo = g.get_repo(f"{user}/{project}")
            contents = repo.get_contents(filepath)
            html_url: str = contents.html_url
            file_str: str = contents.decoded_content.decode()
        except GithubException as e:
            print(f"{user} {project} {filepath}")
            print(e)
            raise e
    return html_url, file_str


def skip_pytest_param_args(str_args_list: List[str], reversed_dec_list: List[ast.expr], imports: List[ImportName]):
    for dec in reversed_dec_list:
        match dec:
            case ast.Call(
                ast.Attribute(ast.Attribute(ast.Name(ident, _), attr1, _), attr2, _), [ast.Constant(val, _), _], _
            ):
                # @pytest.mark.parametrise(...) case
                # import pytest
                if any([imp["alias"] == "pytest" for imp in imports]):
                    if attr2 == "parametrize" and attr1 == "mark" and ident == "pytest":
                        if isinstance(val, str):
                            param_names_str: str = val
                            param_names = [pn.strip() for pn in param_names_str.split(",")]
                            for param_name in param_names:
                                try:
                                    str_args_list.remove(param_name)
                                except ValueError:
                                    continue
            case ast.Call(ast.Attribute(ast.Name(ident, _), attr, _), [ast.Constant(val, _), _], _):
                # @mark.parametrize(...) case
                # from pytest import mark
                if any([imp["alias"] == "mark" and imp["parent_module"] == "pytest" for imp in imports]):
                    if attr == "parametrize" and ident == "mark":
                        if isinstance(val, str):
                            param_names_str: str = val
                            param_names = [pn.strip() for pn in param_names_str.split(",")]
                            for param_name in param_names:
                                try:
                                    str_args_list.remove(param_name)
                                except ValueError:
                                    continue
            case ast.Call(ast.Name(ident, _), [ast.Constant(val, _), _], _):
                # @parametrize(...) case
                # from pytest.mark import parametrize
                if any([imp["alias"] == "parametrize" and imp["parent_module"] == "pytest.mark" for imp in imports]):
                    if ident == "parametrize" and isinstance(val, str):
                        param_names_str: str = val
                        param_names = [pn.strip() for pn in param_names_str.split(",")]
                        for param_name in param_names:
                            try:
                                str_args_list.remove(param_name)
                            except ValueError:
                                continue
    return


# Notes: can't mix positional and keyword arguments in Hypothesis given
# https://github.com/HypothesisWorks/hypothesis/blob/5578efc734aeeaf3375b69e2d8fc77de9d80cc9a/hypothesis-python/src/hypothesis/core.py#L408
# if we have kwargs to given then those are the names of the tainted values
# if we don't have kwargs then: we assume given is the top-level decorator, and consider the first n arguments of the fcn as tainted (ignoring self)
def get_generated_values(
    finfo: FunctionInfo, given_is_attr: bool, imports: List[ImportName]
) -> tuple[ast.expr, List[ast.Name]]:
    given_dec: ast.expr = None
    gen_vals: List[ast.Name] = []
    fd: ast.FunctionDef = finfo["func"]
    for dec in fd.decorator_list:
        if isinstance(dec, ast.Name) and ("staticmethod" == dec.id or "classmethod" == dec.id):
            finfo["isstaticorclass"] = True
    # decorators are stored top-down, so switch to bottom up
    reversed_dec_list = fd.decorator_list
    reversed_dec_list.reverse()
    for dec in reversed_dec_list:
        # there is only one given decorator per function
        # https://github.com/HypothesisWorks/hypothesis/blob/5578efc734aeeaf3375b69e2d8fc77de9d80cc9a/hypothesis-python/src/hypothesis/core.py#L1448
        if given_is_attr:
            if (
                isinstance(dec, ast.Call)
                and isinstance(dec.func, ast.Attribute)
                and isinstance(dec.func.value, ast.Name)
            ):
                if dec.func.value.id == "hypothesis" and dec.func.attr == "given":
                    given_dec = dec
        else:
            if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and dec.func.id == "given":
                given_dec = dec
        if given_dec is not None:
            break
    if given_dec is not None:
        skipfirst = True if (finfo["inclass"] and not finfo["isstaticorclass"]) else False
        kwargs = given_dec.keywords
        if kwargs != []:  # we only have kwargs
            gen_vals = [ast.Name(id=kw.arg, ctx=ast.Load()) for kw in kwargs]
        else:
            # we need to pay attention to the position of args in the func def
            func_args = finfo["func"].args
            # gives in order list of arguments
            str_args_list: List[str] = [arg.lstrip() for arg in (ast.unparse(func_args)).split(",")]
            pos_args_list: List[ast.arg] = func_args.posonlyargs + func_args.args
            if skipfirst:  # skip "self", etc.
                str_args_list.pop(0)
            # pytest parameterized args are not generated values
            skip_pytest_param_args(str_args_list, reversed_dec_list, imports)
            for arg in str_args_list:
                if arg in [a.arg for a in pos_args_list]:
                    gen_vals.append(ast.Name(id=arg, ctx=ast.Load()))
    return (given_dec, gen_vals)


def get_generated_values_all_funcs(
    imports: List[ImportName], all_funcs_info: List[FunctionInfo], all_cfgs: Dict[str, List[CFG]]
) -> tuple[List[FunctionInfo], List[tuple[str, CFG]]]:
    testing_funcs_info: List[FunctionInfo] = []
    testing_cfgs = []
    if any([imp["alias"] == "given" and imp["parent_module"] == "hypothesis" for imp in imports]):
        given_is_attr = False
    elif any([imp["alias"] == "hypothesis" for imp in imports]):
        given_is_attr = True
    else:
        return testing_funcs_info, testing_cfgs
    func_removal_idx = None
    for i, finfo in enumerate(all_funcs_info):
        given_dec, gen_vals = get_generated_values(finfo, given_is_attr, imports)
        if given_dec is not None:
            finfo["given_dec"] = given_dec
            finfo["generated_values"] = gen_vals
            testing_funcs_info.append(finfo)
            try:
                cfg = all_cfgs[finfo["func"].name].pop(0)
                testing_cfgs.append((finfo["func"].name, cfg))
            except Exception as ex:
                if len(all_funcs_info) > len(all_cfgs):
                    # two functions of the same name
                    testing_funcs_info.pop()
                    continue
                else:
                    print(finfo["func"].name)
                    print(all_cfgs)
                    print(ex)
                    raise ex
    return testing_funcs_info, testing_cfgs


def get_func_infos(blocks: List[Block]) -> tuple[List[FunctionInfo], List[ImportName]]:
    TESTING_IMPORT_NAMES = ["hypothesis", "pytest", "unittest"]
    all_funcs_info: List[FunctionInfo] = []
    imports: List[ImportName] = []
    for block in blocks:
        for stmt in block.statements:
            match stmt:
                case ast.Import():
                    if any([any([name in alias.name for name in TESTING_IMPORT_NAMES]) for alias in stmt.names]):
                        for alias in stmt.names:
                            imports.append(ImportName(alias=alias.name, parent_module=None))
                case ast.ImportFrom():
                    if stmt.module is None:  # when importing from . or .. etc.
                        pass
                    elif any([name in stmt.module for name in TESTING_IMPORT_NAMES]):
                        for alias in stmt.names:
                            imports.append(ImportName(alias=alias.name, parent_module=stmt.module))
                case ast.ClassDef():
                    for fd in stmt.body:
                        if isinstance(fd, ast.FunctionDef):
                            all_funcs_info.append(
                                FunctionInfo(
                                    func=fd,
                                    inclass=True,
                                    isstaticorclass=False,
                                    generated_values=[],
                                    given_dec=None,
                                )
                            )
                        elif isinstance(fd, ast.AsyncFunctionDef):
                            # turn into a normal function def, we don't care about async
                            new_stmt = ast.FunctionDef(
                                name=fd.name,
                                args=fd.args,
                                body=fd.body,
                                decorator_list=fd.decorator_list,
                                returns=fd.returns,
                            )
                            all_funcs_info.append(
                                FunctionInfo(
                                    func=new_stmt,
                                    inclass=True,
                                    isstaticorclass=False,
                                    generated_values=[],
                                    given_dec=None,
                                )
                            )
                case ast.FunctionDef():
                    all_funcs_info.append(
                        FunctionInfo(
                            func=stmt, inclass=False, isstaticorclass=False, generated_values=[], given_dec=None
                        )
                    )
                case ast.AsyncFunctionDef():
                    # turn into a normal function def, we don't care about async
                    new_stmt = ast.FunctionDef(
                        name=stmt.name,
                        args=stmt.args,
                        body=stmt.body,
                        decorator_list=stmt.decorator_list,
                        returns=stmt.returns,
                    )
                    all_funcs_info.append(
                        FunctionInfo(
                            func=new_stmt, inclass=False, isstaticorclass=False, generated_values=[], given_dec=None
                        )
                    )
    return all_funcs_info, imports


def get_testing_func_info(src: str) -> tuple[List[FunctionInfo], List[ImportName], List[CFG]]:
    try:
        cfg: CFG = CFGBuilder().build_from_src("filename", src)
        blocks: List[Block] = cfg.get_all_blocks()
    except Exception as ex:
        raise Exception("problem in Scalpel: ", ex)
    else:
        all_funcs_info, imports = get_func_infos(blocks)
        if all_funcs_info == []:
            return [], imports, []
        all_cfgs_wname: Dict[str, List[CFG]] = {}

        # get CFGs for functions
        for (_, fun_name), fun_cfg in cfg.functioncfgs.items():
            if fun_name in [func["func"].name for func in all_funcs_info]:
                if fun_name in all_cfgs_wname.keys():
                    all_cfgs_wname[fun_name].append(fun_cfg)
                else:
                    all_cfgs_wname[fun_name] = [fun_cfg]
        for _, class_cfg in cfg.class_cfgs.items():
            for (_, fun_name), fun_cfg in class_cfg.functioncfgs.items():
                if fun_name in [func["func"].name for func in all_funcs_info]:
                    if fun_name in all_cfgs_wname.keys():
                        all_cfgs_wname[fun_name].append(fun_cfg)
                    else:
                        all_cfgs_wname[fun_name] = [fun_cfg]
        tested_funcs_info, tested_cfgs_wname = get_generated_values_all_funcs(
            imports=imports, all_funcs_info=all_funcs_info, all_cfgs=all_cfgs_wname
        )
        tested_cfgs = [cfgwname[1] for cfgwname in tested_cfgs_wname]
    return tested_funcs_info, imports, tested_cfgs


def locate_asserts(stmt: ast.AST) -> List[AssertTypes]:
    assert_info = []
    match stmt:
        case ast.Expr():
            val = stmt.value
            if isinstance(val, ast.Call):
                # checks for assertIn, assertEquals, etc.
                if isinstance(val.func, ast.Attribute) and "assert" in val.func.attr:
                    assert_info = [stmt]
        case ast.Assert():
            assert_info = [stmt]
        case ast.For() | ast.While():
            # check in for or while block
            for substmt in stmt.body:
                assert_info += locate_asserts(stmt=substmt)
        case ast.If():
            # check in if block
            for substmt in stmt.body:
                assert_info += locate_asserts(stmt=substmt)
            # check in else or elif blocks
            for substmt in stmt.orelse:
                assert_info += locate_asserts(stmt=substmt)
        case ast.With():
            for substmt in stmt.body:
                assert_info += locate_asserts(stmt=substmt)
    return assert_info


def get_asserts(func: ast.FunctionDef, importList: List[ast.alias]) -> List[AssertTypes]:
    assert_stmts: List[AssertTypes] = []

    search_string = ""
    if any([imp["alias"] == "raises" and imp["parent_module"] == "pytest" for imp in importList]):
        search_string = "raises"
    elif any([imp["alias"] == "pytest" for imp in importList]):
        search_string = "pytest.raises"
    for dec in func.decorator_list:
        # skip attribute decorators
        if hasattr(dec, "func") and not isinstance(dec.func, ast.Attribute):
            if search_string == dec.func.id:
                # print(dec.func)
                assert_stmts.append(dec)
    for stmt in func.body:
        assert_stmts += locate_asserts(stmt)
    return assert_stmts
