"""Java and C++ versions of every problem, generated from its Python one.

The problems are written once, in Python. The method signatures in a coding problem's stubs.json
and an algorithm problem's `signature` carry type annotations (`int`, `str`, `int | None`,
`list[list[int]]`, `TreeNode | None`...), and those are enough to write, for each other language:

* the starter code, the per-level method stubs and the scratch file a session starts with;
* the read-only tests view (coding problems) with the shown tests in that language's syntax;
* the test harness: a program that reads the tests as JSON on stdin, calls the solution's methods
  with typed arguments and reports each call's result as JSON (static/lang/ holds the parts every
  problem shares; the browser compiles it with the solution, see static/compiled.js).

Names follow each language's conventions: `add_file` becomes `addFile` in Java and C++ (a name
that is a keyword there gets a trailing underscore). Python's `None` is `null` (boxed types) in
Java and `nullopt` (std::optional) in C++. An `int` is a 64-bit `long` / `long long` only where a
test value needs it.

A problem can name its tuple types for Java, which has none: problem.json's
`"records": {"tuple[str, int]": "OrderLine(sku, qty)"}` makes Java use `record OrderLine(String
sku, int qty)` (C++ uses std::pair and std::tuple). An algorithm problem can also set
`"java_return"` to the Java return type when the usual one (an array for a list of numbers, a List
otherwise) isn't the conventional choice, e.g. `"int[][]"` for interval lists.
"""

from __future__ import annotations

import ast
import json
import re
import textwrap
from dataclasses import dataclass, field

LANGUAGES = ("java", "cpp")
LABELS = {"python": "Python", "java": "Java", "cpp": "C++"}
INT32_MAX = 2**31 - 1


def _words(text: str) -> frozenset[str]:
    return frozenset(text.split())


JAVA_KEYWORDS = _words(
    "abstract assert boolean break byte case catch char class const continue default do double "
    "else enum extends final finally float for goto if implements import instanceof int "
    "interface long native new package private protected public return short static strictfp "
    "super switch synchronized this throw throws transient try void volatile while true false "
    "null var record yield sealed permits"
)
CPP_KEYWORDS = _words(
    "alignas alignof and and_eq asm auto bitand bitor bool break case catch char char8_t "
    "char16_t char32_t class compl concept const consteval constexpr constinit const_cast "
    "continue co_await co_return co_yield decltype default delete do double dynamic_cast else "
    "enum explicit export extern false float for friend goto if inline int long mutable "
    "namespace new noexcept not not_eq nullptr operator or or_eq private protected public "
    "register reinterpret_cast requires return short signed sizeof static static_assert "
    "static_cast struct switch template this thread_local throw true try typedef typeid "
    "typename union unsigned using virtual void volatile wchar_t while xor xor_eq"
)


class LangError(ValueError):
    """A signature uses a type the other languages can't express (yet)."""


# -- types -------------------------------------------------------------------------------
SCALARS = ("int", "float", "bool", "str")
NODES = {"ListNode": "listnode", "TreeNode": "treenode", "Node": "node"}
# The runner's adapter kind for each node type (runner.py, algorithms/README.md).
ADAPTER = {"listnode": "listnode", "treenode": "tree", "node": "graph"}


@dataclass(eq=False)
class Type:
    """A parsed annotation. kind: int, float, bool, str, none, list, tuple, optional, or a node
    (listnode, treenode, node). `wide` marks an int that needs 64 bits."""

    kind: str
    args: tuple[Type, ...] = ()
    wide: bool = False

    def __str__(self) -> str:
        if self.kind == "optional":
            return f"{self.args[0]} | None"
        if self.kind in ("list", "tuple"):
            return f"{self.kind}[{', '.join(str(a) for a in self.args)}]"
        names = {v: k for k, v in NODES.items()}
        return names.get(self.kind, "None" if self.kind == "none" else self.kind)

    @property
    def is_node(self) -> bool:
        return self.kind in ADAPTER


def parse_type(text: str) -> Type:
    """`list[int] | None` -> Type. Node types are nullable already, so `TreeNode | None` is just
    a tree node."""
    try:
        tree = ast.parse(text.strip(), mode="eval").body
    except SyntaxError as exc:
        raise LangError(f"can't parse the type {text!r}") from exc
    return _from_ast(tree, text)


def _from_ast(node: ast.expr, text: str) -> Type:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left, right = _from_ast(node.left, text), _from_ast(node.right, text)
        if right.kind == "none":
            left, right = right, left
        if left.kind != "none" or right.kind == "none":
            raise LangError(f"only `X | None` unions are supported: {text!r}")
        return right if right.is_node else Type("optional", (right,))
    if isinstance(node, ast.Constant) and node.value is None:
        return Type("none")
    if isinstance(node, ast.Name):
        if node.id in SCALARS:
            return Type(node.id)
        if node.id in NODES:
            return Type(NODES[node.id])
        raise LangError(f"unsupported type {node.id!r} in {text!r}")
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
        inner = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
        args = tuple(_from_ast(a, text) for a in inner)
        name = node.value.id
        if name in ("list", "List") and len(args) == 1:
            return Type("list", args)
        if name in ("tuple", "Tuple") and len(args) >= 2:
            return Type("tuple", args)
        if name == "Optional" and len(args) == 1:  # typing.Optional[X]: X | None
            return args[0] if args[0].is_node else Type("optional", args)
    raise LangError(f"unsupported type {ast.unparse(node)!r} in {text!r}")


def mark_wide(t: Type, value) -> None:
    """Flag the ints of `t` that `value` (test data) shows need 64 bits."""
    if value is None:
        return
    if isinstance(value, dict) and set(value) == {"__tuple__"}:
        value = value["__tuple__"]
    if t.kind == "int" and isinstance(value, int) and not isinstance(value, bool):
        t.wide = t.wide or abs(value) > INT32_MAX
    elif t.kind == "optional":
        mark_wide(t.args[0], value)
    elif t.kind == "list" and isinstance(value, list):
        for item in value:
            mark_wide(t.args[0], item)
    elif t.kind == "tuple" and isinstance(value, list):
        for sub, item in zip(t.args, value, strict=False):
            mark_wide(sub, item)


def walk(t: Type):
    yield t
    for a in t.args:
        yield from walk(a)


# -- methods -----------------------------------------------------------------------------
@dataclass
class Param:
    name: str  # as in Python
    type: Type


@dataclass
class Method:
    name: str  # as in Python: add_file, twoSum
    params: list[Param]
    ret: Type
    doc: str = ""
    level: int | None = None  # coding problems: the level that adds it


def _methods_from_source(source: str, level: int | None) -> list[Method]:
    out = []
    tree = ast.parse(textwrap.dedent(source))
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name == "__init__":
            continue
        params = []
        for arg in node.args.args[1:]:  # skip self
            if arg.annotation is None:
                raise LangError(f"{node.name}: parameter {arg.arg} has no type annotation")
            params.append(Param(arg.arg, parse_type(ast.unparse(arg.annotation))))
        if node.returns is None:
            raise LangError(f"{node.name}: no return annotation")
        doc = ast.get_docstring(node) or ""
        out.append(Method(node.name, params, parse_type(ast.unparse(node.returns)), doc, level))
    return out


@dataclass
class Spec:
    """Everything the generators need about one problem, in no particular language."""

    track: str  # "coding" or "algo"
    id: str
    class_name: str
    methods: list[Method]
    records: dict[str, tuple[str, list[str]]] = field(default_factory=dict)  # Java tuple names
    java_return: str | None = None
    check_arg0: bool = False  # algo: compare the first argument after the call
    first_test: dict | None = None  # the example scratch starts from
    levels: tuple[int, ...] = ()

    def methods_up_to(self, level: int | None) -> list[Method]:
        return [m for m in self.methods if level is None or (m.level or 0) <= level]

    @property
    def node_kinds(self) -> list[str]:
        """The node types the problem uses, in a fixed order."""
        used = {t.kind for m in self.methods for p in m.params for t in walk(p.type)}
        used |= {t.kind for m in self.methods for t in walk(m.ret)}
        return [k for k in ("listnode", "treenode", "node") if k in used]

    @property
    def tuple_types(self) -> list[Type]:
        """Each distinct tuple type, innermost first, by its Python spelling."""
        seen: dict[str, Type] = {}
        for m in self.methods:
            for t in [*(p.type for p in m.params), m.ret]:
                for sub in reversed(list(walk(t))):
                    if sub.kind == "tuple":
                        seen.setdefault(str(sub), sub)
        return list(seen.values())


def _records(raw: dict | None) -> dict[str, tuple[str, list[str]]]:
    """{"tuple[str, int]": "OrderLine(sku, qty)"} -> {"tuple[str, int]": ("OrderLine", [...])}."""
    out = {}
    for key, value in (raw or {}).items():
        m = re.fullmatch(r"\s*([A-Z]\w*)\s*\(([^)]*)\)\s*", value)
        if not m:
            raise LangError(f"records: {value!r} should look like Name(field, field)")
        out[str(parse_type(key))] = (m.group(1), [f.strip() for f in m.group(2).split(",")])
    return out


def coding_spec(problem, stubs: dict, tests: list[dict], meta: dict) -> Spec:
    """A coding problem: its class, the methods each level's stubs add, and the test data."""
    methods = []
    for level in sorted(int(k) for k in stubs if k.isdigit()):
        methods += _methods_from_source(stubs[str(level)], level)
    spec = Spec(
        track="coding",
        id=problem.id,
        class_name=problem.class_name,
        methods=methods,
        records=_records(meta.get("records")),
        levels=tuple(lv["level"] for lv in problem.levels),
    )
    by_name = {m.name: m for m in methods}
    for test in tests:
        for step in test["steps"]:
            method = by_name.get(step["call"])
            if method is None:
                raise LangError(f"{problem.id}: a test calls {step['call']}, which no stub has")
            for param, value in zip(method.params, step["args"], strict=False):
                mark_wide(param.type, value)
            if "expect" in step:
                mark_wide(method.ret, step["expect"])
    shown = [t for t in tests if t["level"] == 1 and t["visibility"] == "shown"]
    spec.first_test = shown[0] if shown else None
    _check_records(spec)
    return spec


def algo_spec(problem, cases: list[dict], meta: dict) -> Spec:
    """An algorithm problem: one method on Solution, and its test cases (shown first)."""
    (method,) = _methods_from_source(problem.signature.strip() + "\n    pass\n", None)
    kinds = list((problem.adapters or {}).get("args") or [])
    for param, kind in zip(method.params, kinds, strict=False):
        want = ADAPTER.get(param.type.kind)
        listnodes = param.type.kind == "list" and param.type.args[0].kind == "listnode"
        if kind and want != kind and not (kind == "listnodes" and listnodes):
            raise LangError(f"{problem.id}: adapter {kind!r} doesn't match {param.type}")
    for case in cases:
        for param, value in zip(method.params, case["args"], strict=False):
            mark_wide(param.type, value)
        mark_wide(method.ret, case["expect"])
    spec = Spec(
        track="algo",
        id=problem.id,
        class_name="Solution",
        methods=[method],
        records=_records(meta.get("records")),
        java_return=meta.get("java_return"),
        check_arg0=(problem.adapters or {}).get("check") == "arg0",
        first_test=cases[0] if cases else None,
    )
    _check_records(spec)
    return spec


def _check_records(spec: Spec) -> None:
    for t in spec.tuple_types:
        name = spec.records.get(str(t))
        if name is None:
            raise LangError(f'{spec.id}: name {t} for Java in problem.json\'s "records"')
        if len(name[1]) != len(t.args):
            raise LangError(f"{spec.id}: {name[0]} needs {len(t.args)} field names")


# -- shared helpers ----------------------------------------------------------------------
def camel(name: str) -> str:
    """add_file -> addFile; twoSum stays twoSum."""
    head, *rest = name.split("_")
    return head + "".join(p[:1].upper() + p[1:] for p in rest)


def pascal(name: str) -> str:
    c = camel(re.sub(r"[^0-9A-Za-z_]+", "_", name).strip("_") or "case")
    return c[:1].upper() + c[1:]


def ident(name: str, keywords: frozenset[str]) -> str:
    out = camel(name)
    return out + "_" if out in keywords else out


def obj_name(class_name: str) -> str:
    """FileStore -> fileStore (the variable the scratch and tests views use)."""
    return class_name[:1].lower() + class_name[1:]


def decode(value):
    """Test data with {"__tuple__": [...]} markers as plain lists."""
    if isinstance(value, dict):
        if set(value) == {"__tuple__"}:
            return [decode(v) for v in value["__tuple__"]]
        return {k: decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [decode(v) for v in value]
    return value


def adapt_doc(doc: str, null: str) -> str:
    """A Python docstring in the other language's words."""
    doc = re.sub(r"\bNone\b", null, doc)
    doc = re.sub(r"\bTrue\b", "true", doc)
    return re.sub(r"\bFalse\b", "false", doc)


def quote(text: str) -> str:
    """A string literal both Java and C++ read the same way."""
    return json.dumps(text, ensure_ascii=True)


def _test_names(tests: list[dict]) -> list[str]:
    names, seen = [], set()
    for test in tests:
        base = pascal(test["name"])
        name, n = base, 2
        while name in seen:
            name, n = f"{base}{n}", n + 1
        seen.add(name)
        names.append(name)
    return names


def _tests_header(class_name: str, max_level: int, comment: str) -> list[str]:
    levels = "Level 1" if max_level == 1 else f"Levels 1-{max_level}"
    return [
        f"{comment} Shown tests for {levels} (read-only). Run executes exactly these; each test",
        f"{comment} starts from a fresh {class_name}. Submit also runs the hidden tests: they aren't",
        f"{comment} listed here and report only how many pass per level.",
    ]


# -- Java --------------------------------------------------------------------------------
JAVA_NODES = {
    "listnode": """class ListNode {
    int val;
    ListNode next;

    ListNode() {}

    ListNode(int val) {
        this.val = val;
    }

    ListNode(int val, ListNode next) {
        this.val = val;
        this.next = next;
    }
}
""",
    "treenode": """class TreeNode {
    int val;
    TreeNode left;
    TreeNode right;

    TreeNode() {}

    TreeNode(int val) {
        this.val = val;
    }

    TreeNode(int val, TreeNode left, TreeNode right) {
        this.val = val;
        this.left = left;
        this.right = right;
    }
}
""",
    "node": """import java.util.ArrayList;
import java.util.List;

class Node {
    public int val;
    public List<Node> neighbors;

    public Node() {
        neighbors = new ArrayList<Node>();
    }

    public Node(int val) {
        this.val = val;
        neighbors = new ArrayList<Node>();
    }

    public Node(int val, ArrayList<Node> neighbors) {
        this.val = val;
        this.neighbors = neighbors;
    }
}
""",
}
JAVA_NODE_CLASS = {"listnode": "ListNode", "treenode": "TreeNode", "node": "Node"}
JAVA_NODE_TITLE = {
    "listnode": "a singly-linked list node",
    "treenode": "a binary tree node",
    "node": "a graph node",
}
JAVA_PLAIN = {
    "listnode": "SweAdapt.fromList",
    "treenode": "SweAdapt.fromTree",
    "node": "SweAdapt.fromGraph",
}
JAVA_BOXED = {"int": "Integer", "long": "Long", "double": "Double", "boolean": "Boolean"}
JAVA_STUB_BODY = 'throw new UnsupportedOperationException("Not implemented yet");'


class JavaGen:
    lang = "java"
    null = "null"

    def __init__(self, spec: Spec):
        self.spec = spec

    # names and types
    @property
    def file_name(self) -> str:
        return f"{self.spec.class_name}.java"

    def name(self, py_name: str) -> str:
        return ident(py_name, JAVA_KEYWORDS)

    def scalar(self, t: Type) -> str:
        return {
            "int": "long" if t.wide else "int",
            "float": "double",
            "bool": "boolean",
            "str": "String",
        }[t.kind]

    def record(self, t: Type) -> tuple[str, list[str]]:
        return self.spec.records[str(t)]

    def type(self, t: Type, ctx: str = "param") -> str:
        """ctx: "param" (arrays for lists of numbers, strings and nodes), "return", or "generic"
        (inside a List or record: boxed and List all the way down)."""
        if t.kind in SCALARS:
            name = self.scalar(t)
            return JAVA_BOXED.get(name, name) if ctx == "generic" else name
        if t.kind == "optional":
            inner = self.type(t.args[0], "generic" if t.args[0].kind in SCALARS else ctx)
            return inner
        if t.is_node:
            return JAVA_NODE_CLASS[t.kind]
        if t.kind == "tuple":
            return self.record(t)[0]
        if t.kind == "none":
            return "void"
        if t.kind == "list":
            item = t.args[0]
            if ctx == "param" and self.arrayable(item):
                return self.type(item, "param") + "[]"
            if ctx == "return" and item.kind in ("int", "float", "bool"):
                return self.scalar(item) + "[]"
            return f"List<{self.type(item, 'generic')}>"
        raise LangError(f"no Java type for {t}")

    def arrayable(self, t: Type) -> bool:
        return t.kind in SCALARS or t.is_node or (t.kind == "list" and self.arrayable(t.args[0]))

    def ret_type(self, m: Method) -> str:
        if self.spec.java_return:
            return self.spec.java_return
        return self.type(m.ret, "return")

    def signature(self, m: Method) -> str:
        params = ", ".join(f"{self.type(p.type)} {self.name(p.name)}" for p in m.params)
        return f"public {self.ret_type(m)} {self.name(m.name)}({params})"

    # what a session starts with
    def method_stub(self, m: Method) -> str:
        lines = []
        if m.doc:
            lines.append(f"    /** {adapt_doc(m.doc, self.null)} */")
        lines += [f"    {self.signature(m)} {{", f"        {JAVA_STUB_BODY}", "    }"]
        return "\n".join(lines) + "\n"

    def level_stubs(self, level: int) -> str:
        return "\n".join(self.method_stub(m) for m in self.spec.methods if m.level == level)

    def provided(self) -> str:
        """A comment showing the classes the harness provides, which the solution uses as is."""
        blocks = []
        for kind in self.spec.node_kinds:
            body = JAVA_NODES[kind].split("\n\n", 1)[-1] if kind == "node" else JAVA_NODES[kind]
            text = "\n".join(f" * {line}".rstrip() for line in body.rstrip().splitlines())
            blocks.append(
                f"/**\n * Definition for {JAVA_NODE_TITLE[kind]} (provided; don't redefine it):\n{text}\n */"
            )
        for t in self.spec.tuple_types:
            blocks.append(f"// Provided (don't redefine it): {self.record_decl(t)}")
        return "\n".join(blocks)

    def record_decl(self, t: Type) -> str:
        name, fields = self.record(t)
        parts = ", ".join(
            f"{self.type(a, 'field')} {f}" for a, f in zip(t.args, fields, strict=True)
        )
        return f"record {name}({parts}) {{}}"

    def starter_code(self) -> str:
        spec = self.spec
        out = ["import java.util.*;", ""]
        provided = self.provided()
        if provided:
            out += [provided, ""]
        out.append(f"class {spec.class_name} {{")
        if spec.track == "coding":
            out += [f"    public {spec.class_name}() {{", "    }", ""]
            out.append(self.level_stubs(1).rstrip("\n"))
        else:
            (m,) = spec.methods
            out += [f"    {self.signature(m)} {{", f"        {JAVA_STUB_BODY}", "    }"]
        out.append("}")
        return "\n".join(out) + "\n"

    # literals (scratch and the tests view)
    def literal(self, t: Type, value, top: bool = True) -> str:
        value = decode(value)
        if value is None:
            return "null"
        if t.kind == "optional":
            return self.literal(t.args[0], value, top)
        if t.kind == "int":
            return f"{value}L" if t.wide else str(value)
        if t.kind == "float":
            return repr(float(value))
        if t.kind == "bool":
            return "true" if value else "false"
        if t.kind == "str":
            return quote(value)
        if t.kind == "listnode":
            return f"Helpers.makeList({', '.join(str(v) for v in value)})"
        if t.kind == "treenode":
            return f"Helpers.makeTree({', '.join('null' if v is None else str(v) for v in value)})"
        if t.kind == "node":
            rows = ", ".join("{" + ", ".join(str(v) for v in row) + "}" for row in value)
            return f"Helpers.makeGraph(new int[][] {{{rows}}})"
        if t.kind == "tuple":
            name, _ = self.record(t)
            items = ", ".join(self.literal(a, v, False) for a, v in zip(t.args, value, strict=True))
            return f"new {name}({items})"
        if t.kind == "list":
            item = t.args[0]
            if top and self.arrayable(item):
                return f"new {self.type(t)} {self._braces(item, value)}"
            items = ", ".join(self.literal(item, v, False) for v in value)
            return f"new ArrayList<>(List.of({items}))" if top else f"List.of({items})"
        raise LangError(f"no Java literal for {t}")

    def _braces(self, item: Type, values: list) -> str:
        if item.kind == "list":
            return "{" + ", ".join(self._braces(item.args[0], v) for v in values) + "}"
        return "{" + ", ".join(self.literal(item, v, False) for v in values) + "}"

    def call(self, obj: str, m: Method, args: list) -> str:
        values = ", ".join(self.literal(p.type, a) for p, a in zip(m.params, args, strict=True))
        return f"{obj}.{self.name(m.name)}({values})"

    def scratch_starter(self) -> str:
        spec = self.spec
        first = spec.first_test
        head = [
            "import java.util.*;",
            "",
            f"// Scratch: try your code here. Run scratch compiles this with {self.file_name} and runs main.",
            "public class Scratch {",
            "    public static void main(String[] args) {",
        ]
        tail = ["    }", "}"]
        body = []
        if spec.track == "coding" and first:
            by_name = {m.name: m for m in spec.methods}
            obj = obj_name(spec.class_name)
            body.append(
                "        // The first shown test (see Tests.java). Until you implement the methods, they throw."
            )
            body.append(f"        {spec.class_name} {obj} = new {spec.class_name}();")
            for step in first["steps"]:
                call = self.call(obj, by_name[step["call"]], step["args"])
                if "expect" in step and by_name[step["call"]].ret.kind != "none":
                    expect = json.dumps(decode(step["expect"]))
                    body.append(
                        f"        System.out.println(Helpers.show({call}));  // expected: {expect}"
                    )
                else:
                    body.append(f"        {call};")
        elif spec.track == "algo" and first:
            (m,) = spec.methods
            for p, value in zip(m.params, first["args"], strict=True):
                body.append(
                    f"        {self.type(p.type)} {self.name(p.name)} = {self.literal(p.type, value)};"
                )
            call = f"new Solution().{self.name(m.name)}({', '.join(self.name(p.name) for p in m.params)})"
            expect = json.dumps(decode(first["expect"]))
            if spec.check_arg0:
                body += [
                    f"        {call};",
                    f"        System.out.println(Helpers.show({self.name(m.params[0].name)}));  // expected: {expect}",
                ]
            else:
                body += [
                    f"        {self.ret_type(m)} result = {call};",
                    f"        System.out.println(Helpers.show(result));  // expected: {expect}",
                ]
        return "\n".join(head + body + tail) + "\n"

    def tests_view(self, tests: list[dict], max_level: int) -> str:
        """Tests.java for a coding session: the shown tests as JUnit-style methods."""
        spec = self.spec
        by_name = {m.name: m for m in spec.methods}
        obj = obj_name(spec.class_name)
        out = _tests_header(spec.class_name, max_level, "//")
        level = None
        for test, name in zip(tests, _test_names(tests), strict=True):
            if test["level"] != level:
                if level is not None:
                    out.append("}")
                level = test["level"]
                out += ["", f"class Level{level}Tests {{"]
            else:
                out.append("")
            out += [
                "    @Test",
                f"    void {name[:1].lower() + name[1:]}() {{",
                f"        // {test['name']}",
            ]
            out.append(f"        {spec.class_name} {obj} = new {spec.class_name}();")
            for step in test["steps"]:
                m = by_name[step["call"]]
                call = self.call(obj, m, step["args"])
                if "expect" not in step or m.ret.kind == "none":
                    out.append(f"        {call};")
                elif step["expect"] is None:
                    out.append(f"        assertNull({call});")
                elif m.ret.kind == "bool":
                    out.append(f"        assert{'True' if step['expect'] else 'False'}({call});")
                else:
                    out.append(
                        f"        assertEquals({self.literal(m.ret, step['expect'], False)}, {call});"
                    )
            out.append("    }")
        if level is not None:
            out.append("}")
        return "\n".join(out) + "\n"

    # the harness
    def decoder(self, t: Type, ctx: str, v: str) -> str:
        """Java that turns parsed JSON `v` into a value of type(t, ctx)."""
        if t.kind == "optional":
            return f"({v} == null ? null : {self.decoder(t.args[0], 'generic', v)})"
        if t.kind in SCALARS:
            return {
                "int": "SweJson.toLong" if t.wide else "SweJson.toInt",
                "float": "SweJson.toDouble",
                "bool": "SweJson.toBool",
                "str": "SweJson.toStr",
            }[t.kind] + f"({v})"
        if t.kind == "listnode":
            return f"SweAdapt.toList({v})"
        if t.kind == "treenode":
            return f"SweAdapt.toTree({v})"
        if t.kind == "node":
            return f"SweAdapt.toGraph({v})"
        if t.kind == "tuple":
            return f"SweAdapt.to{self.record(t)[0]}({v})"
        if t.kind == "list":
            item = t.args[0]
            java = self.type(t, ctx)
            if java.endswith("[]"):
                if item.kind in ("int", "float", "bool"):
                    name = {
                        "int": "Long" if item.wide else "Int",
                        "float": "Double",
                        "bool": "Bool",
                    }[item.kind]
                    return f"SweJson.to{name}Array({v})"
                each = self.decoder(item, "param", "x")
                return f"SweJson.toArray({v}, {self.type(item, 'param')}[]::new, x -> {each})"
            return f"SweJson.toList({v}, x -> {self.decoder(item, 'generic', 'x')})"
        raise LangError(f"no Java decoder for {t}")

    def adapt_source(self) -> str:
        """SweAdapt.java: building and reading the problem's nodes and records."""
        spec = self.spec
        kinds = spec.node_kinds
        out = ["import java.util.*;", "", "final class SweAdapt {", "    private SweAdapt() {}", ""]
        hooks = []
        if "listnode" in kinds:
            out.append(JAVA_LIST_ADAPT)
            hooks.append("        if (o instanceof ListNode n) return fromList(n);")
        if "treenode" in kinds:
            out.append(JAVA_TREE_ADAPT)
            hooks.append("        if (o instanceof TreeNode n) return fromTree(n);")
        if "node" in kinds:
            out.append(JAVA_GRAPH_ADAPT)
            hooks.append("        if (o instanceof Node n) return fromGraph(n);")
        for t in spec.tuple_types:
            name, fields = self.record(t)
            reads = ", ".join(self.decoder(a, "field", f"l.get({i})") for i, a in enumerate(t.args))
            out += [
                f"    static {name} to{name}(Object v) {{",
                "        List<Object> l = SweJson.list(v);",
                f"        return new {name}({reads});",
                "    }",
                "",
            ]
            parts = ", ".join(f"r.{f}()" for f in fields)
            hooks.append(f"        if (o instanceof {name} r) return Arrays.asList({parts});")
        out += [
            "    /** The problem's nodes and records as lists (what SweJson writes), else NOT_MINE. */",
            "    static Object plain(Object o) {",
            *hooks,
            "        return SweJson.NOT_MINE;",
            "    }",
            "}",
        ]
        return "\n".join(out) + "\n"

    def records_source(self) -> str:
        decls = [self.record_decl(t) for t in self.spec.tuple_types]
        return "import java.util.*;\n\n" + "\n".join(decls) + "\n" if decls else ""

    def helpers_source(self) -> str:
        """Helpers.java for scratch: build lists, trees and graphs, and show any value."""
        kinds = self.spec.node_kinds
        out = [
            "import java.util.*;",
            "",
            "/** For Scratch.java: build the inputs the tests describe, and print results the way they do. */",
            "final class Helpers {",
            "    private Helpers() {}",
            "",
            '    /** A value as the tests write it: [1, 2], "text", null, true. */',
            "    static String show(Object value) {",
            "        return SweJson.show(value);",
            "    }",
        ]
        if "listnode" in kinds:
            out += [
                "",
                "    /** makeList(1, 2, 3) is 1 -> 2 -> 3 (null for no values). */",
                "    static ListNode makeList(int... values) {",
                "        List<Object> list = new ArrayList<>();",
                "        for (int v : values) list.add((long) v);",
                "        return SweAdapt.toList(list);",
                "    }",
            ]
        if "treenode" in kinds:
            out += [
                "",
                "    /** makeTree(3, 9, 20, null, null, 15, 7): level order, null for a missing child. */",
                "    static TreeNode makeTree(Integer... values) {",
                "        List<Object> list = new ArrayList<>();",
                "        for (Integer v : values) list.add(v == null ? null : (Object) (long) v);",
                "        return SweAdapt.toTree(list);",
                "    }",
            ]
        if "node" in kinds:
            out += [
                "",
                "    /** makeGraph(new int[][] {{2, 4}, {1, 3}}): row i lists node i+1's neighbors. Returns node 1. */",
                "    static Node makeGraph(int[][] adjacency) {",
                "        List<Object> rows = new ArrayList<>();",
                "        for (int[] row : adjacency) {",
                "            List<Object> r = new ArrayList<>();",
                "            for (int v : row) r.add((long) v);",
                "            rows.add(r);",
                "        }",
                "        return SweAdapt.toGraph(rows);",
                "    }",
            ]
        out.append("}")
        return "\n".join(out) + "\n"

    def support_files(self) -> dict[str, str]:
        """The problem's Java files besides the solution, the scratch file and the harness."""
        files = {f"{JAVA_NODE_CLASS[k]}.java": JAVA_NODES[k] for k in self.spec.node_kinds}
        if self.spec.tuple_types:
            files["SweTypes.java"] = self.records_source()
        files["SweAdapt.java"] = self.adapt_source()
        files["Helpers.java"] = self.helpers_source()
        return files

    def harness(self, level: int | None = None) -> str:
        """SweMain.java: dispatch each test step to the solution's methods (levels 1..level)."""
        spec = self.spec
        cases = []
        pad = " " * 20
        for m in spec.methods_up_to(level):
            lines = [f'                case "{m.name}": {{']
            for i, p in enumerate(m.params):
                lines.append(
                    f"{pad}{self.type(p.type)} a{i} = {self.decoder(p.type, 'param', f'a.get({i})')};"
                )
            args = ", ".join(f"a{i}" for i in range(len(m.params)))
            call = f"o.{self.name(m.name)}({args})"
            graph_check = (
                spec.track == "algo"
                and m.ret.kind == "node"
                and m.params
                and m.params[0].type.kind == "node"
            )
            if graph_check:
                lines.append(f"{pad}Set<Object> originals = SweAdapt.graphNodes(a0);")
            lines.append(f"{pad}clock.start();")
            # A node result is returned as its values (an empty list, tree or graph as []).
            if spec.check_arg0:
                kind = m.params[0].type.kind
                lines += [
                    f"{pad}{call};",
                    f"{pad}clock.stop();",
                    f"{pad}return {JAVA_PLAIN.get(kind, '')}(a0);",
                ]
            elif m.ret.kind == "none":
                lines += [f"{pad}{call};", f"{pad}clock.stop();", f"{pad}return null;"]
            else:
                lines += [f"{pad}{self.ret_type(m)} r = {call};", f"{pad}clock.stop();"]
                if graph_check:
                    lines.append(f"{pad}SweAdapt.checkNotShared(r, originals);")
                lines.append(f"{pad}return {JAVA_PLAIN.get(m.ret.kind, '')}(r);")
            lines.append("                }")
            cases.append("\n".join(lines))
        return JAVA_HARNESS.format(cls=spec.class_name, cases="\n".join(cases))


JAVA_LIST_ADAPT = """    static ListNode toList(Object v) {
        ListNode head = null;
        List<Object> values = SweJson.list(v);
        for (int i = values.size() - 1; i >= 0; i--) head = new ListNode(SweJson.toInt(values.get(i)), head);
        return head;
    }

    static List<Object> fromList(ListNode head) {
        List<Object> out = new ArrayList<>();
        Set<ListNode> seen = Collections.newSetFromMap(new IdentityHashMap<>());
        for (ListNode n = head; n != null; n = n.next) {
            if (!seen.add(n)) throw new SweAdapterError("The linked list loops back on itself (it has a cycle).");
            if (out.size() >= SweJson.MAX_NODES) throw new SweAdapterError("The linked list is too long.");
            out.add(n.val);
        }
        return out;
    }
"""
JAVA_TREE_ADAPT = """    static TreeNode toTree(Object v) {
        List<Object> values = SweJson.list(v);
        if (values.isEmpty() || values.get(0) == null) return null;
        TreeNode root = new TreeNode(SweJson.toInt(values.get(0)));
        ArrayDeque<TreeNode> queue = new ArrayDeque<>();
        queue.add(root);
        int i = 1;
        while (!queue.isEmpty() && i < values.size()) {
            TreeNode parent = queue.poll();
            if (i < values.size() && values.get(i) != null) {
                parent.left = new TreeNode(SweJson.toInt(values.get(i)));
                queue.add(parent.left);
            }
            i++;
            if (i < values.size() && values.get(i) != null) {
                parent.right = new TreeNode(SweJson.toInt(values.get(i)));
                queue.add(parent.right);
            }
            i++;
        }
        return root;
    }

    static List<Object> fromTree(TreeNode root) {
        List<Object> out = new ArrayList<>();
        Set<TreeNode> seen = Collections.newSetFromMap(new IdentityHashMap<>());
        ArrayList<TreeNode> queue = new ArrayList<>();
        queue.add(root);
        for (int k = 0; k < queue.size(); k++) {
            TreeNode n = queue.get(k);
            if (n == null) {
                out.add(null);
                continue;
            }
            if (!seen.add(n)) throw new SweAdapterError("That isn't a tree: a node is reachable twice.");
            if (seen.size() > SweJson.MAX_NODES) throw new SweAdapterError("The tree is too large.");
            out.add(n.val);
            queue.add(n.left);
            queue.add(n.right);
        }
        while (!out.isEmpty() && out.get(out.size() - 1) == null) out.remove(out.size() - 1);
        return out;
    }
"""
JAVA_GRAPH_ADAPT = """    static Node toGraph(Object v) {
        List<Object> rows = SweJson.list(v);
        List<Node> nodes = new ArrayList<>();
        for (int i = 0; i < rows.size(); i++) nodes.add(new Node(i + 1));
        for (int i = 0; i < rows.size(); i++) {
            for (Object w : SweJson.list(rows.get(i))) nodes.get(i).neighbors.add(nodes.get(SweJson.toInt(w) - 1));
        }
        return nodes.isEmpty() ? null : nodes.get(0);
    }

    static Set<Object> graphNodes(Node start) {
        Set<Object> seen = Collections.newSetFromMap(new IdentityHashMap<>());
        ArrayDeque<Node> queue = new ArrayDeque<>();
        if (start != null) queue.add(start);
        while (!queue.isEmpty()) {
            Node n = queue.poll();
            if (!seen.add(n)) continue;
            if (seen.size() > SweJson.MAX_NODES) throw new SweAdapterError("The graph is too large.");
            if (n.neighbors != null) for (Node w : n.neighbors) if (w != null) queue.add(w);
        }
        return seen;
    }

    static void checkNotShared(Object result, Set<Object> originals) {
        if (!(result instanceof Node n)) return;
        for (Object x : graphNodes(n)) {
            if (originals.contains(x)) throw new SweAdapterError("The copy reuses nodes of the original graph: clone every node.");
        }
    }

    static List<Object> fromGraph(Node start) {
        Map<Integer, Node> byVal = new HashMap<>();
        for (Object x : graphNodes(start)) {
            Node n = (Node) x;
            if (byVal.put(n.val, n) != null) throw new SweAdapterError("Two nodes have the value " + n.val + ".");
        }
        for (int v = 1; v <= byVal.size(); v++) {
            if (!byVal.containsKey(v)) throw new SweAdapterError("Node values must be 1..n, like the input's.");
        }
        List<Object> out = new ArrayList<>();
        for (int v = 1; v <= byVal.size(); v++) {
            List<Object> row = new ArrayList<>();
            for (Node w : byVal.get(v).neighbors) row.add(w == null ? null : (Object) w.val);
            out.add(row);
        }
        return out;
    }
"""
JAVA_HARNESS = """import java.util.*;

/** The test harness (generated): SweRun reads the tests and calls step() for each call. */
public class SweMain {{
    public static void main(String[] args) {{
        SweRun.run(new SweRun.Target() {{
            public Object create() {{
                return new {cls}();
            }}

            public Object step(Object self, String name, List<Object> a, SweRun.Clock clock) {{
                {cls} o = ({cls}) self;
                switch (name) {{
{cases}
                default:
                    throw new SweAdapterError("The tests call an unknown method: " + name);
                }}
            }}
        }});
    }}
}}
"""


# -- C++ ---------------------------------------------------------------------------------
CPP_NODES = {
    "listnode": """struct ListNode {
    int val;
    ListNode *next;
    ListNode() : val(0), next(nullptr) {}
    ListNode(int x) : val(x), next(nullptr) {}
    ListNode(int x, ListNode *next) : val(x), next(next) {}
};
""",
    "treenode": """struct TreeNode {
    int val;
    TreeNode *left;
    TreeNode *right;
    TreeNode() : val(0), left(nullptr), right(nullptr) {}
    TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
    TreeNode(int x, TreeNode *left, TreeNode *right) : val(x), left(left), right(right) {}
};
""",
    "node": """class Node {
public:
    int val;
    std::vector<Node*> neighbors;
    Node() : val(0) {}
    Node(int _val) : val(_val) {}
    Node(int _val, std::vector<Node*> _neighbors) : val(_val), neighbors(_neighbors) {}
};
""",
}
CPP_NODE_TYPE = {"listnode": "ListNode*", "treenode": "TreeNode*", "node": "Node*"}
CPP_NODE_MACRO = {"listnode": "SWE_LISTNODE", "treenode": "SWE_TREENODE", "node": "SWE_GRAPHNODE"}


class CppGen:
    lang = "cpp"
    null = "nullopt"
    file_name = "solution.cpp"

    def __init__(self, spec: Spec):
        self.spec = spec

    def name(self, py_name: str) -> str:
        return ident(py_name, CPP_KEYWORDS)

    def type(self, t: Type) -> str:
        if t.kind == "int":
            return "long long" if t.wide else "int"
        if t.kind == "float":
            return "double"
        if t.kind == "bool":
            return "bool"
        if t.kind == "str":
            return "string"
        if t.kind == "none":
            return "void"
        if t.kind == "optional":
            return f"optional<{self.type(t.args[0])}>"
        if t.is_node:
            return CPP_NODE_TYPE[t.kind]
        if t.kind == "list":
            return f"vector<{self.type(t.args[0])}>"
        if t.kind == "tuple":
            inner = ", ".join(self.type(a) for a in t.args)
            return f"pair<{inner}>" if len(t.args) == 2 else f"tuple<{inner}>"
        raise LangError(f"no C++ type for {t}")

    def std_type(self, t: Type) -> str:
        """type(t) with std:: spelled out, for the harness (which can't rely on using namespace)."""
        text = self.type(t)
        return re.sub(r"\b(string|vector|optional|pair|tuple)\b", r"std::\1", text)

    def param(self, p: Param) -> str:
        """Algorithm problems take lists as `vector<int>& nums`, as is usual; a coding problem's
        methods take `const vector<...>&`, so calls can pass a braced list."""
        cpp = self.type(p.type)
        if p.type.kind == "list":
            cpp = f"{cpp}&" if self.spec.track == "algo" else f"const {cpp}&"
        return f"{cpp} {self.name(p.name)}"

    def signature(self, m: Method) -> str:
        params = ", ".join(self.param(p) for p in m.params)
        return f"{self.type(m.ret)} {self.name(m.name)}({params})"

    def body(self, m: Method) -> list[str]:
        return [
            f"    {self.signature(m)} {{",
            *([] if m.ret.kind == "none" else ["        return {};"]),
            "    }",
        ]

    def method_stub(self, m: Method) -> str:
        lines = [f"    // {adapt_doc(m.doc, self.null)}"] if m.doc else []
        return "\n".join(lines + self.body(m)) + "\n"

    def level_stubs(self, level: int) -> str:
        return "\n".join(self.method_stub(m) for m in self.spec.methods if m.level == level)

    def provided(self) -> str:
        blocks = []
        for kind in self.spec.node_kinds:
            text = "\n".join(
                f" * {line}".rstrip() for line in CPP_NODES[kind].rstrip().splitlines()
            )
            blocks.append(
                f"/**\n * Definition for {JAVA_NODE_TITLE[kind]} (provided; don't redefine it):\n{text}\n */"
            )
        return "\n".join(blocks)

    def starter_code(self) -> str:
        spec = self.spec
        out = ["#include <bits/stdc++.h>", "using namespace std;", ""]
        provided = self.provided()
        if provided:
            out += [provided, ""]
        out += [f"class {spec.class_name} {{", "public:"]
        if spec.track == "coding":
            out += [f"    {spec.class_name}() {{", "    }", ""]
            out.append(self.level_stubs(1).rstrip("\n"))
        else:
            out += self.body(spec.methods[0])
        out.append("};")
        return "\n".join(out) + "\n"

    def literal(self, t: Type, value) -> str:
        value = decode(value)
        if t.kind == "optional":
            return "nullopt" if value is None else self.literal(t.args[0], value)
        if value is None:
            return "nullptr" if t.is_node else "nullopt"
        if t.kind == "int":
            return f"{value}LL" if t.wide else str(value)
        if t.kind == "float":
            return repr(float(value))
        if t.kind == "bool":
            return "true" if value else "false"
        if t.kind == "str":
            return quote(value)
        if t.kind == "listnode":
            return "makeList({" + ", ".join(str(v) for v in value) + "})"
        if t.kind == "treenode":
            return "makeTree({" + ", ".join("null" if v is None else str(v) for v in value) + "})"
        if t.kind == "node":
            return (
                "makeGraph({"
                + ", ".join("{" + ", ".join(str(v) for v in row) + "}" for row in value)
                + "})"
            )
        if t.kind in ("list", "tuple"):
            subs = t.args if t.kind == "tuple" else [t.args[0]] * len(value)
            return (
                "{" + ", ".join(self.literal(s, v) for s, v in zip(subs, value, strict=True)) + "}"
            )
        raise LangError(f"no C++ literal for {t}")

    def arg(self, t: Type, value) -> str:
        """An argument expression: a braced list, with its type spelled out to read clearly."""
        text = self.literal(t, value)
        return f"{self.type(t)}{text}" if text.startswith("{") else text

    def scratch_starter(self) -> str:
        spec = self.spec
        first = spec.first_test
        head = [
            "// Scratch: try your code here. Run scratch compiles this file and runs main().",
            '#include "solution.cpp"',
            '#include "helpers.hpp"  // show(), and makeList / makeTree / makeGraph for inputs',
            "",
            "int main() {",
        ]
        body = []
        if spec.track == "coding" and first:
            by_name = {m.name: m for m in spec.methods}
            obj = obj_name(spec.class_name)
            body.append(
                "    // The first shown test (see tests.cpp). The stubs return empty values until you write them."
            )
            body.append(f"    {spec.class_name} {obj};")
            for step in first["steps"]:
                m = by_name[step["call"]]
                values = ", ".join(
                    self.arg(p.type, a) for p, a in zip(m.params, step["args"], strict=True)
                )
                call = f"{obj}.{self.name(m.name)}({values})"
                if "expect" in step and m.ret.kind != "none":
                    expect = json.dumps(decode(step["expect"]))
                    body.append(f"    cout << show({call}) << endl;  // expected: {expect}")
                else:
                    body.append(f"    {call};")
        elif spec.track == "algo" and first:
            (m,) = spec.methods
            for p, value in zip(m.params, first["args"], strict=True):
                body.append(
                    f"    {self.type(p.type)} {self.name(p.name)} = {self.literal(p.type, value)};"
                )
            call = (
                f"Solution().{self.name(m.name)}({', '.join(self.name(p.name) for p in m.params)})"
            )
            expect = json.dumps(decode(first["expect"]))
            if spec.check_arg0:
                body += [
                    f"    {call};",
                    f"    cout << show({self.name(m.params[0].name)}) << endl;  // expected: {expect}",
                ]
            else:
                body += [
                    f"    auto result = {call};",
                    f"    cout << show(result) << endl;  // expected: {expect}",
                ]
        body.append("    return 0;")
        return "\n".join(head + body + ["}"]) + "\n"

    def tests_view(self, tests: list[dict], max_level: int) -> str:
        """tests.cpp for a coding session: the shown tests in GoogleTest style."""
        spec = self.spec
        by_name = {m.name: m for m in spec.methods}
        obj = obj_name(spec.class_name)
        out = _tests_header(spec.class_name, max_level, "//")
        for test, name in zip(tests, _test_names(tests), strict=True):
            out += [
                "",
                f"TEST(Level{test['level']}, {name}) {{",
                f"    // {test['name']}",
                f"    {spec.class_name} {obj};",
            ]
            for step in test["steps"]:
                m = by_name[step["call"]]
                values = ", ".join(
                    self.arg(p.type, a) for p, a in zip(m.params, step["args"], strict=True)
                )
                call = f"{obj}.{self.name(m.name)}({values})"
                if "expect" not in step or m.ret.kind == "none":
                    out.append(f"    {call};")
                else:
                    out.append(f"    EXPECT_EQ({call}, {self.literal(m.ret, step['expect'])});")
            out.append("}")
        return "\n".join(out) + "\n"

    def nodes_source(self) -> str:
        """swe_nodes.hpp, included before solution.cpp: the node types the problem uses."""
        out = [
            "// The node types this problem's tests build (included before solution.cpp).",
            "#pragma once",
        ]
        for kind in self.spec.node_kinds:
            out += [f"#define {CPP_NODE_MACRO[kind]} 1", CPP_NODES[kind]]
        return "\n".join(out) + "\n"

    def support_files(self) -> dict[str, str]:
        return {"swe_nodes.hpp": self.nodes_source()}

    def harness(self, level: int | None = None) -> str:
        """main.cpp: dispatch each test step to the solution's methods (levels 1..level)."""
        spec = self.spec
        cases = []
        for m in spec.methods_up_to(level):
            lines = [f'    if (name == "{m.name}") {{']
            for i, p in enumerate(m.params):
                cpp = self.std_type(p.type)
                lines.append(f"        {cpp} a{i} = swe::from_json<{cpp}>(a[{i}]);")
            args = ", ".join(f"a{i}" for i in range(len(m.params)))
            call = f"o.{self.name(m.name)}({args})"
            graph_check = (
                spec.track == "algo"
                and m.ret.kind == "node"
                and m.params
                and m.params[0].type.kind == "node"
            )
            if graph_check:
                lines.append("        auto originals = swe::graph_nodes(a0);")
            if spec.check_arg0:
                lines.append(
                    f"        return step.call([&] {{ {call}; }}, [&](swe::Writer& w) {{ swe::write(w, a0); }});"
                )
            elif graph_check:
                lines.append(
                    f"        return step.call_graph_copy([&] {{ return {call}; }}, originals);"
                )
            else:
                lines.append(f"        return step.call([&] {{ return {call}; }});")
            lines.append("    }")
            cases.append("\n".join(lines))
        return CPP_HARNESS.format(cls=spec.class_name, cases="\n".join(cases))


CPP_HARNESS = """// The test harness (generated): swe::run reads the tests and calls swe_step for each call.
// It's compiled with -include swe_nodes.hpp, so the problem's node types come first.
#include "solution.cpp"
#include "swe.hpp"

static void swe_step({cls}& o, const std::string& name, const swe::Json& a, swe::Step& step) {{
{cases}
    step.unknown(name);
}}

int main() {{
    return swe::run<{cls}>(swe_step);
}}
"""


# -- what the build writes -------------------------------------------------------------------
def generators(spec: Spec) -> dict:
    return {"java": JavaGen(spec), "cpp": CppGen(spec)}


def coding_bundle(spec: Spec, shown_by_level: dict[int, list[dict]]) -> dict:
    """data.json's per-language view of a coding problem: files, starter, stubs, tests views."""
    out = {}
    for lang, gen in generators(spec).items():
        out[lang] = {
            "file": gen.file_name,
            "starter_code": gen.starter_code(),
            "scratch_starter": gen.scratch_starter(),
            "stubs": {str(lv): gen.level_stubs(lv) for lv in spec.levels},
            "tests_source": {str(lv): gen.tests_view(shown_by_level[lv], lv) for lv in spec.levels},
            "names": {m.name: gen.name(m.name) for m in spec.methods},
        }
    return out


def algo_bundle(spec: Spec) -> dict:
    out = {}
    (m,) = spec.methods
    for lang, gen in generators(spec).items():
        out[lang] = {
            "file": gen.file_name,
            "starter_code": gen.starter_code(),
            "scratch_starter": gen.scratch_starter(),
            "signature": gen.signature(m),
            "names": {m.name: gen.name(m.name)},
        }
    return out


def harness_files(spec: Spec) -> dict:
    """The tests file's per-language part: the problem's support files and its harness (one
    per level for a coding problem, since only the unlocked levels' methods exist yet)."""
    out = {}
    for lang, gen in generators(spec).items():
        if spec.track == "coding":
            harness = {str(lv): gen.harness(lv) for lv in spec.levels}
        else:
            harness = gen.harness()
        out[lang] = {
            "file": gen.file_name,
            "files": gen.support_files(),
            "harness": harness,
            "names": {m.name: gen.name(m.name) for m in spec.methods},
        }
    return out


# -- loading a problem's spec ------------------------------------------------------------------
def _meta(problem) -> dict:
    return json.loads((problem.path / "problem.json").read_text(encoding="utf-8"))


def for_coding(problem) -> Spec:
    """The Spec of a coding problem (problems.Problem), from its stubs and every test."""
    from . import config, problems

    tests = problems.tests(problem, len(config.LEVELS), include_hidden=True)
    return coding_spec(problem, problems.stubs(problem), tests, _meta(problem))


def for_algo(problem) -> Spec:
    """The Spec of an algorithm problem (algorithms.Problem), from its signature and tests."""
    data = json.loads((problem.path / "tests.json").read_text(encoding="utf-8"))
    return algo_spec(problem, data["shown"] + data["hidden"], _meta(problem))
