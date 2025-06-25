import ast
from pathlib import Path

test_imports = {}


class ImportVisitor(ast.NodeVisitor):
    """Visitor which records which modules are imported."""
    def __init__(self) -> None:
        super().__init__()
        self.imports = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.imports.append(node.module)


def init():
    """Find all test files located under the 'tests' directory and create an abstract syntax tree for each.
    Let the ``ImportVisitor`` find out what modules they import and store the information in a global dictionary
    which can be accessed by ``pre_mutation(context)``."""
    test_files = (Path(__file__).parent / "tests").rglob("test*.py")
    for fpath in test_files:
        visitor = ImportVisitor()
        visitor.visit(ast.parse(fpath.read_bytes()))
        test_imports[str(fpath)] = visitor.imports


def pre_mutation(context):
    """Construct the module name from the filename and run all test files which import that module."""
    tests_to_run = []
    for testfile, imports in test_imports.items():
        module_name = context.filename.rstrip(".py").replace("/", ".")
        if module_name in imports:
            tests_to_run.append(testfile)
    context.config.test_command += f"{' '.join(tests_to_run)}"