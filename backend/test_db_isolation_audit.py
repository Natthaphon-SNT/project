"""Static audit of test-suite database isolation.

P5 gave test_ai_sessions and test_qa_fixes their own DATABASE_URL before
importing shop_api, and both pop the module so the engine is rebuilt. That
leaves one question unanswered: does any *other* suite import shop_api, and
therefore inherit whichever engine was built first in the interpreter?

This module answers it by reading the source rather than by importing it, so
the audit itself never opens a database. Importing shop_api here would defeat
the purpose, since a suite that imports it becomes the owner of the engine it
reports on.

WHAT THIS AUDIT DOES NOT PROVE
------------------------------
It reads one file per suite and reasons about statements it can see. It does
not execute anything, so it cannot confirm any of the following:

  * that the temporary path is actually created, writable, or deleted
  * that the module being imported is really shop_api and not an alias
  * that the isolation assertions inside the suite actually pass
  * that a suite reaches no database by some other route, e.g. via db_tools,
    a relative sqlite path, or an engine cached under a different module name
  * anything about ordering across suites at runtime; that is covered by the
    reversed test-order run, not here
  * control flow within a suite: line order does not prove that an assignment
    executes before an import (it may be conditional or in an uncalled function),
    or that sys.modules.pop executes before that import

A pass means "no suite declares an unisolated shop_api import". It is not
"isolation is guaranteed on every path".
"""

import ast
import os
from pathlib import Path
import unittest
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parent

# Suites that legitimately import shop_api, each with its own DATABASE_URL and
# its own sys.modules.pop. Listed explicitly so adding a new importing suite is
# a deliberate edit here rather than a silent behaviour change.
ISOLATED_SUITES = {
    "test_ai_sessions.py",
    "test_qa_fixes.py",
}

DATABASE_URL = "DATABASE_URL"
TARGET_MODULE = "shop_api"


def _module_name_from_dotted(value: str) -> str:
    return value.split(".", 1)[0]


def _imports_shop_api(path: Path) -> bool:
    """True if path imports shop_api by any means this audit recognises."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, SyntaxError, UnicodeDecodeError):
        return False
    return bool(import_sites(source))


def _dotted_name(node) -> str:
    """Render `a.b.c` or `a` from an ast expression, or '' if it is dynamic."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else ""
    return ""


def import_sites(source: str) -> list:
    """Line numbers where shop_api is imported, by any recognised form.

    Recognised: `import shop_api`, `from shop_api import x`,
    `importlib.import_module("shop_api")` and `__import__("shop_api")`. The last
    two are what the fixtures actually use, so a plain import statement scan
    would have missed every importing suite in this repository.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    sites = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _module_name_from_dotted(alias.name) == TARGET_MODULE:
                    sites.append(node.lineno)
        elif isinstance(node, ast.ImportFrom):
            # `from . import shop_api` has module=None and a level.
            module = node.module or ""
            names = [alias.name for alias in node.names]
            if (_module_name_from_dotted(module) == TARGET_MODULE
                    or TARGET_MODULE in names):
                sites.append(node.lineno)
        elif isinstance(node, ast.Call):
            func = _dotted_name(node.func)
            if func in ("importlib.import_module", "__import__"):
                if node.args and isinstance(node.args[0], ast.Constant) \
                        and node.args[0].value == TARGET_MODULE:
                    sites.append(node.lineno)
    return sorted(sites)


def database_url_writes(source: str) -> list:
    """Line numbers that actually assign DATABASE_URL into os.environ.

    An ast walk rather than a substring search, because both fixtures discuss
    DATABASE_URL in their comments and a read such as
    `os.environ.get("DATABASE_URL")` or a subscript read is not a write.
    setdefault is not an overwrite: it preserves an existing, possibly real URL.
    Counting any of those
    would let a suite pass this audit without ever isolating anything.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    writes = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Subscript)
                and isinstance(node.ctx, ast.Store)
                and _dotted_name(node.value) == "os.environ"):
            key = node.slice
            if isinstance(key, ast.Constant) and key.value == DATABASE_URL:
                writes.append(node.lineno)
    return sorted(writes)


def sys_modules_pops(source: str) -> set:
    """Module names passed to sys.modules.pop."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    popped = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_pop = (_dotted_name(func) == "sys.modules.pop")
        if is_pop and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                popped.add(first.value)
    return popped


def isolation_report(source: str) -> dict:
    """Summarise what a suite's source declares about shop_api isolation."""
    imports = import_sites(source)
    writes = database_url_writes(source)
    first_import = min(imports) if imports else None
    first_write = min(writes) if writes else None
    if not imports:
        writes_before_import = None
    elif first_write is None:
        writes_before_import = False
    else:
        writes_before_import = first_write < first_import
    return {
        "imports": imports,
        "writes": writes,
        "first_import": first_import,
        "first_write": first_write,
        "writes_before_import": writes_before_import,
        "pops": sys_modules_pops(source),
    }


def is_isolated(source: str) -> bool:
    """True when a suite that imports shop_api sets its URL before the import."""
    report = isolation_report(source)
    if not report["imports"]:
        return True
    return bool(report["writes_before_import"]) and TARGET_MODULE in report["pops"]


class DetectorTests(unittest.TestCase):
    """The detectors themselves, against synthetic sources.

    A static audit that cannot fail on a known-bad input is worse than no
    audit, so each recogniser is checked against both shapes before the real
    suites are examined with it.
    """

    def test_detects_plain_import_statement(self):
        self.assertTrue(import_sites("import shop_api\n"))
        self.assertTrue(import_sites("from shop_api import Product\n"))

    def test_detects_the_dynamic_import_the_fixtures_really_use(self):
        """`import shop_api` alone would have missed both real suites."""
        for source in ('import importlib\ncls.api = importlib.import_module("shop_api")\n',
                       "cls.api = __import__('shop_api')\n"):
            with self.subTest(source=source):
                self.assertTrue(import_sites(source))

    def test_detects_conditional_and_relative_forms(self):
        self.assertTrue(import_sites("if True:\n    import shop_api\n"))
        self.assertTrue(import_sites("from . import shop_api\n"))

    def test_ignores_unrelated_imports(self):
        self.assertEqual(import_sites("import os\nfrom shop_api_helpers import x\n"), [])

    def test_detects_assignment(self):
        self.assertEqual(database_url_writes('os.environ["DATABASE_URL"] = "sqlite:///t.db"\n'), [1])

    def test_subscript_read_is_not_a_write(self):
        self.assertEqual(database_url_writes('original = os.environ["DATABASE_URL"]\n'), [])

    def test_setdefault_is_not_an_overwrite(self):
        self.assertEqual(database_url_writes('os.environ.setdefault("DATABASE_URL", "x")\n'), [])

    def test_a_comment_mentioning_database_url_is_not_a_write(self):
        source = (
            "# Point DATABASE_URL at this suite's own file before import.\n"
            "# os.environ[\"DATABASE_URL\"] would be wrong here.\n"
            "import os\n"
        )
        self.assertEqual(database_url_writes(source), [])

    def test_a_read_is_not_a_write(self):
        """`os.environ.get` appears in both fixtures; it isolates nothing."""
        self.assertEqual(database_url_writes('original = os.environ.get("DATABASE_URL")\n'), [])

    def test_a_string_literal_is_not_a_write(self):
        self.assertEqual(database_url_writes('msg = \'os.environ["DATABASE_URL"] = "x"\'\n'), [])

    def test_unparseable_source_reports_nothing_rather_than_crashing(self):
        self.assertEqual(import_sites("def (:\n"), [])
        self.assertEqual(import_sites("import shop_api\n"), [1])

    def test_pops_are_collected_by_name(self):
        self.assertIn("shop_api",
                      sys_modules_pops('sys.modules.pop("shop_api", None)\n'))


class IsolationRuleTests(unittest.TestCase):
    """The isolation rule, against synthetic sources.

    `is_isolated` must reject a dynamic import with no isolation, and an import
    that happens before the URL is set, while accepting the shape the fixtures
    use.
    """

    FIXTURE_SHAPE = (
        "import os, sys, importlib\n"
        'os.environ["DATABASE_URL"] = "sqlite:///tmp/x.db"\n'
        'sys.modules.pop("shop_api", None)\n'
        'api = importlib.import_module("shop_api")\n'
    )

    def test_accepts_the_shape_the_fixtures_use(self):
        self.assertTrue(is_isolated(self.FIXTURE_SHAPE))

    def test_rejects_a_dynamic_import_with_no_isolation_at_all(self):
        source = "import importlib\napi = importlib.import_module('shop_api')\n"

        self.assertTrue(import_sites(source))
        self.assertFalse(is_isolated(source))

    def test_rejects_a_url_set_after_the_import(self):
        """Setting it later leaves the engine pointing at the old default."""
        source = (
            "import os, sys, importlib\n"
            'sys.modules.pop("shop_api", None)\n'
            'api = importlib.import_module("shop_api")\n'
            'os.environ["DATABASE_URL"] = "sqlite:///tmp/x.db"\n'
        )
        report = isolation_report(source)

        self.assertTrue(report["writes"])
        self.assertFalse(report["writes_before_import"])
        self.assertFalse(is_isolated(source))

    def test_rejects_an_url_set_before_the_import_but_without_the_pop(self):
        source = (
            "import os, importlib\n"
            'os.environ["DATABASE_URL"] = "sqlite:///tmp/x.db"\n'
            'api = importlib.import_module("shop_api")\n'
        )
        self.assertFalse(is_isolated(source))

    def test_rejects_a_comment_only_url_mention(self):
        source = (
            "import importlib\n"
            "# we set DATABASE_URL in CI, see runbook\n"
            'api = importlib.import_module("shop_api")\n'
        )
        report = isolation_report(source)

        self.assertEqual(report["writes"], [])
        self.assertFalse(is_isolated(source))

    def test_a_suite_that_never_imports_shop_api_needs_no_isolation(self):
        self.assertTrue(is_isolated("import unittest\n"))

    def test_reading_an_existing_url_does_not_isolate(self):
        source = self.FIXTURE_SHAPE.replace(
            'os.environ["DATABASE_URL"] = "sqlite:///tmp/x.db"',
            'original = os.environ["DATABASE_URL"]',
        )
        with patch.dict(os.environ, {DATABASE_URL: "sqlite:///existing.db"}):
            self.assertFalse(is_isolated(source))

    def test_setdefault_preserves_an_existing_url_and_is_rejected(self):
        assignment = 'os.environ.setdefault("DATABASE_URL", "sqlite:///tmp/x.db")'
        source = self.FIXTURE_SHAPE.replace(
            'os.environ["DATABASE_URL"] = "sqlite:///tmp/x.db"', assignment,
        )
        with patch.dict(os.environ, {DATABASE_URL: "sqlite:///existing.db"}):
            exec(assignment, {"os": os})  # No engine or database is opened.
            self.assertEqual(os.environ[DATABASE_URL], "sqlite:///existing.db")
            self.assertFalse(is_isolated(source))


class TestDbIsolationAudit(unittest.TestCase):
    """The real suites."""

    def _source(self, name: str) -> str:
        return (BACKEND / name).read_text(encoding="utf-8")

    def test_test_modules_exist(self):
        modules = sorted(p.name for p in BACKEND.glob("test_*.py"))
        self.assertGreaterEqual(len(modules), 39, modules)

    def test_only_declared_suites_import_shop_api(self):
        """No suite may reach the real shop.db engine by accident."""
        importers = {
            path.name for path in BACKEND.glob("test_*.py")
            if _imports_shop_api(path)
        }
        undeclared = importers - ISOLATED_SUITES
        self.assertEqual(
            undeclared, set(),
            "these suites import shop_api but are not listed in ISOLATED_SUITES: "
            f"{sorted(undeclared)}. Each needs its own DATABASE_URL set before "
            "the import and a sys.modules.pop, or it will reuse another suite's "
            "engine.",
        )

    def test_declared_suites_import_shop_api_the_way_the_detector_looks_for(self):
        """Guards the detector against drifting away from the real fixtures."""
        for name in sorted(ISOLATED_SUITES):
            with self.subTest(suite=name):
                self.assertTrue(import_sites(self._source(name)),
                                f"{name} was expected to import shop_api")

    def test_every_declared_suite_isolates_before_importing(self):
        for name in sorted(ISOLATED_SUITES):
            with self.subTest(suite=name):
                self.assertTrue((BACKEND / name).exists(),
                                f"missing declared suite {name}")
                self.assertTrue(
                    is_isolated(self._source(name)),
                    f"{name} imports shop_api without setting DATABASE_URL before "
                    "the import and popping the cached module",
                )

    def test_declared_suites_write_database_url_before_their_import(self):
        for name in sorted(ISOLATED_SUITES):
            with self.subTest(suite=name):
                report = isolation_report(self._source(name))

                self.assertTrue(report["writes_before_import"],
                                f"{name}: DATABASE_URL write at "
                                f"{report['writes']} does not precede the import "
                                f"at line {report['first_import']}")

    def test_shops_api_is_not_imported_by_this_audit(self):
        """The auditor must not become the owner of the engine it audits."""
        self.assertFalse(
            _imports_shop_api(Path(__file__)),
            "this audit module must not import shop_api, or its own import "
            "would build an engine before the suites under test run",
        )

    def test_declared_suites_dispose_the_engine_before_cleanup(self):
        """Reversing the suite order failed with PermissionError before these
        changes, so the dispose and the pop are load-bearing, not tidying."""
        for name in sorted(ISOLATED_SUITES):
            with self.subTest(suite=name):
                source = self._source(name)
                self.assertIn(
                    "engine.dispose()", source,
                    f"{name} must dispose the engine or Windows keeps the file "
                    "locked and TemporaryDirectory.cleanup() raises PermissionError",
                )

    def test_audit_scope_limitations_are_documented(self):
        """The module must keep stating what it cannot prove."""
        doc = Path(__file__).read_text(encoding="utf-8")

        self.assertIn("WHAT THIS AUDIT DOES NOT PROVE", doc)
        self.assertIn("guaranteed on every path", doc)
        self.assertIn("db_tools", doc)


if __name__ == "__main__":
    unittest.main()
