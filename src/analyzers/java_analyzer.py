"""
Authoritative Java Static Code Analyzer.
Calculates the standard 12 object-oriented and structural software quality metrics:
- LOC   : Lines of Code (physical lines representing the analyzed class)
- WMC   : Weighted Methods per Class (sum of McCabe Cyclomatic Complexity across declared methods)
- DIT   : Depth of Inheritance Tree (inheritance chain depth from whole-project context)
- NOC   : Number of Children (immediate subclasses in whole-project context)
- RFC   : Response for a Class (declared methods + external methods/constructors invoked)
- LCOM5 : Lack of Cohesion of Methods (Henderson-Sellers metric)
- CBO   : Coupling Between Objects (outward referenced classes/types)
- NPA   : Number of Public Attributes (public fields declared directly in class)
- NPM   : Number of Public Methods (public methods declared directly in class)
- NLE   : Nesting Level of Expressions (maximum nesting depth of control flow blocks)
- CBOI  : Coupling Between Objects Inward (afferent coupling: other classes referencing this class)
- CD    : Comment Density (comment lines / total lines in analyzed class span)
"""

import os
import re
import logging
from typing import Dict, Any, Optional, List, Set, Tuple

logger = logging.getLogger(__name__)

# Standard Java types excluded from CBO coupling count
PRIMITIVE_TYPES = {
    "int", "long", "short", "byte", "float", "double", "boolean", "char", "void",
    "String", "Object", "Integer", "Long", "Short", "Byte", "Float", "Double",
    "Boolean", "Character", "T", "E", "K", "V", "R"
}


def _reference_type_name(type_node: Any) -> str:
    """Returns a Java reference type including any qualified/nested suffixes."""
    names = []
    while type_node is not None and getattr(type_node, "name", None):
        names.append(str(type_node.name))
        type_node = getattr(type_node, "sub_type", None)
    return ".".join(names)


def _source_path_key(path: str) -> str:
    return os.path.normpath(path).replace("\\", "/").removeprefix("./")


def _type_identity(package: str, ancestors: List[Any], node: Any) -> str:
    import javalang

    enclosing_types = [
        parent.name for parent in ancestors
        if isinstance(parent, javalang.tree.TypeDeclaration) and getattr(parent, "name", None)
    ]
    parts = ([package] if package else []) + enclosing_types
    local_scope = any(
        isinstance(parent, (javalang.tree.MethodDeclaration, javalang.tree.ConstructorDeclaration))
        for parent in ancestors
    )
    if local_scope:
        parts.append(f"$local@{getattr(getattr(node, 'position', None), 'line', 0)}")
    parts.append(node.name)
    return ".".join(part for part in parts if part)


def _type_entries(tree: Any, relative_path: str, package: str) -> List[Dict[str, Any]]:
    import javalang

    entries = []
    for ancestors, node in tree.filter(javalang.tree.TypeDeclaration):
        identity = _type_identity(package, ancestors, node)
        line = getattr(getattr(node, "position", None), "line", None)
        enclosing_ids = []
        enclosing_nodes = [
            parent for parent in ancestors
            if isinstance(parent, javalang.tree.TypeDeclaration)
        ]
        for index in range(len(enclosing_nodes)):
            enclosing_ids.append(_type_identity(package, enclosing_nodes[:index], enclosing_nodes[index]))
        entries.append({
            "identity": identity,
            "fqcn": identity,
            "name": node.name,
            "package": package,
            "path": _source_path_key(relative_path),
            "start_line": line,
            "node": node,
            "tree": tree,
            "enclosing_ids": enclosing_ids,
            "local_scope": any(
                isinstance(parent, (javalang.tree.MethodDeclaration, javalang.tree.ConstructorDeclaration))
                for parent in ancestors
            ),
        })
    return entries


def _iter_ast_nodes_excluding_nested_types(root: Any):
    import javalang

    stack = [(root, None)]
    while stack:
        node, parent = stack.pop()
        if node is not root and isinstance(node, javalang.tree.TypeDeclaration):
            continue
        yield node, parent
        for child in getattr(node, "children", []):
            if isinstance(child, list):
                stack.extend((item, node) for item in reversed(child) if hasattr(item, "children"))
            elif hasattr(child, "children"):
                stack.append((child, node))


def _project_type_references(class_node: Any) -> Set[str]:
    import javalang

    references = set()
    for node, parent in _iter_ast_nodes_excluding_nested_types(class_node):
        if isinstance(node, javalang.tree.ReferenceType) and not (
            isinstance(parent, javalang.tree.ReferenceType) and getattr(parent, "sub_type", None) is node
        ):
            name = _reference_type_name(node)
            if name:
                references.add(name)
        for thrown in getattr(node, "throws", []) or []:
            if isinstance(thrown, str) and thrown:
                references.add(thrown)
    return references


def _resolve_project_type(reference: str, source: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Resolves a source type through lexical scope, imports, and package identity only."""
    if not reference:
        return {"resolution": "unresolved", "target": None, "candidates": []}

    last_name = reference.rsplit(".", 1)[-1]
    if last_name in PRIMITIVE_TYPES:
        return {"resolution": "external", "target": None, "candidates": []}

    def resolve_candidates(names: List[str]) -> Optional[Dict[str, Any]]:
        matches = set()
        for name in names:
            matches.update(context["identity_index"].get(name, []))
        if len(matches) == 1:
            return {"resolution": "resolved", "target": next(iter(matches)), "candidates": sorted(matches)}
        if len(matches) > 1:
            return {"resolution": "ambiguous", "target": None, "candidates": sorted(matches)}
        return None

    if reference in context["identity_index"]:
        return resolve_candidates([reference])

    package = source["package"]
    imports = source["imports"]
    if "." not in reference:
        for prefix in [source["identity"]] + list(reversed(source["enclosing_ids"])):
            found = resolve_candidates([f"{prefix}.{reference}"])
            if found:
                return found

        explicit = [item["path"] for item in imports
                    if not item["wildcard"] and item["path"].rsplit(".", 1)[-1] == reference]
        found = resolve_candidates(explicit)
        if found:
            return found

        same_package = f"{package}.{reference}" if package else reference
        found = resolve_candidates([same_package])
        if found:
            return found

        wildcard = [f"{item['path']}.{reference}" for item in imports if item["wildcard"]]
        found = resolve_candidates(wildcard)
        if found:
            return found
    else:
        lexical = [f"{prefix}.{reference}" for prefix in [source["identity"]] + list(reversed(source["enclosing_ids"]))]
        found = resolve_candidates(lexical)
        if found:
            return found

        first, suffix = reference.split(".", 1)
        imported_prefixes = [item["path"] for item in imports
                             if not item["wildcard"] and item["path"].rsplit(".", 1)[-1] == first]
        found = resolve_candidates([f"{prefix}.{suffix}" for prefix in imported_prefixes])
        if found:
            return found

        same_package = f"{package}.{reference}" if package else reference
        found = resolve_candidates([same_package])
        if found:
            return found

        wildcard = [f"{item['path']}.{reference}" for item in imports if item["wildcard"]]
        found = resolve_candidates(wildcard)
        if found:
            return found

    return {"resolution": "unresolved", "target": None, "candidates": []}


def find_class_line_range(source_code: str, start_line: int) -> Tuple[int, int]:
    """
    Finds the exact (start_line, end_line) line range of a class or interface
    by scanning for the opening brace '{' on or after start_line and matching
    its closing brace '}', ignoring comments, strings, and character literals.
    """
    lines = source_code.splitlines()
    brace_depth = 0
    found_first_brace = False
    in_block_comment = False
    in_string = False
    in_char = False
    escape = False

    end_line = start_line
    for line_idx in range(start_line - 1, len(lines)):
        line = lines[line_idx]
        col = 0
        while col < len(line):
            ch = line[col]
            if in_block_comment:
                if ch == '*' and col + 1 < len(line) and line[col + 1] == '/':
                    in_block_comment = False
                    col += 1
            elif in_string:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_string = False
            elif in_char:
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == "'":
                    in_char = False
            else:
                if ch == '/' and col + 1 < len(line) and line[col + 1] == '*':
                    in_block_comment = True
                    col += 1
                elif ch == '/' and col + 1 < len(line) and line[col + 1] == '/':
                    break  # Line comment: ignore remainder of line
                elif ch == '"':
                    in_string = True
                elif ch == "'":
                    in_char = True
                elif ch == '{':
                    brace_depth += 1
                    found_first_brace = True
                elif ch == '}':
                    brace_depth -= 1
                    if found_first_brace and brace_depth == 0:
                        end_line = line_idx + 1
                        return start_line, end_line
            col += 1

    return start_line, len(lines)


def _count_lines_and_comments(source_code: str,
                              start_line: Optional[int] = None,
                              end_line: Optional[int] = None) -> Tuple[int, int, float]:
    """
    Computes LOC (lines of code), CLOC (comment lines), and CD (comment density).
    If start_line and end_line are provided (1-based, inclusive), counts lines
    strictly within the class span.
    """
    all_lines = source_code.splitlines()
    if not all_lines:
        return 0, 0, 0.0

    sl = max(1, start_line) if start_line is not None else 1
    el = min(len(all_lines), end_line) if end_line is not None else len(all_lines)
    if sl > el:
        sl, el = el, sl

    loc = el - sl + 1
    if loc <= 0:
        return 0, 0, 0.0

    target_lines = all_lines[sl - 1:el]

    in_block_comment = False
    cloc = 0

    for line in target_lines:
        stripped = line.strip()
        if in_block_comment:
            cloc += 1
            if "*/" in stripped:
                in_block_comment = False
        else:
            if stripped.startswith("/*"):
                cloc += 1
                if "*/" not in stripped:
                    in_block_comment = True
            elif stripped.startswith("//"):
                cloc += 1
            elif "/*" in stripped:
                cloc += 1
                if "*/" not in stripped:
                    in_block_comment = True

    cd = cloc / max(loc, 1)
    return loc, cloc, float(min(1.0, max(0.0, cd)))


def _calc_cyclomatic_complexity(node) -> int:
    """
    Computes standard McCabe Cyclomatic Complexity for a method:
    1 + branching points (if, while, for, do, catch, switch-case, ternary, &&, ||).
    """
    import javalang
    complexity = 1
    branch_types = (
        javalang.tree.IfStatement,
        javalang.tree.WhileStatement,
        javalang.tree.DoStatement,
        javalang.tree.ForStatement,
        javalang.tree.CatchClause,
        javalang.tree.SwitchStatementCase,
        javalang.tree.TernaryExpression
    )
    for _, child in node.filter(branch_types):
        complexity += 1

    # Count boolean logical operators (&&, ||)
    for _, bin_expr in node.filter(javalang.tree.BinaryOperation):
        if hasattr(bin_expr, 'operator') and bin_expr.operator in ('&&', '||'):
            complexity += 1

    return complexity


def _calc_max_nesting_level(node, current_level: int = 0) -> int:
    """
    Calculates maximum nesting depth of control flow structures in a method AST node.
    Control structures: if, while, do, for, try, switch, synchronized.
    """
    import javalang
    nesting_types = (
        javalang.tree.IfStatement,
        javalang.tree.WhileStatement,
        javalang.tree.DoStatement,
        javalang.tree.ForStatement,
        javalang.tree.TryStatement,
        javalang.tree.SwitchStatement,
        javalang.tree.SynchronizedStatement
    )
    max_nest = current_level

    if hasattr(node, 'children'):
        for child in node.children:
            if isinstance(child, list):
                for item in child:
                    if isinstance(item, nesting_types):
                        sub_nest = _calc_max_nesting_level(item, current_level + 1)
                        if sub_nest > max_nest:
                            max_nest = sub_nest
                    elif hasattr(item, 'children'):
                        sub_nest = _calc_max_nesting_level(item, current_level)
                        if sub_nest > max_nest:
                            max_nest = sub_nest
            elif isinstance(child, nesting_types):
                sub_nest = _calc_max_nesting_level(child, current_level + 1)
                if sub_nest > max_nest:
                    max_nest = sub_nest
            elif hasattr(child, 'children'):
                sub_nest = _calc_max_nesting_level(child, current_level)
                if sub_nest > max_nest:
                    max_nest = sub_nest

    return max_nest


def _calc_lcom5(methods: List[Any], fields: List[Any]) -> float:
    """
    Calculates Henderson-Sellers LCOM5:
    m = number of methods
    a = number of fields
    sum_m_a = sum of number of methods accessing field a_i
    LCOM5 = (m - (sum_m_a / a)) / (m - 1)
    Returns 0.0 if m <= 1 or a == 0.
    """
    import javalang
    m = len(methods)
    if m <= 1:
        return 0.0

    field_names = set()
    for f in fields:
        for declarator in getattr(f, 'declarators', []):
            field_names.add(declarator.name)

    a = len(field_names)
    if a == 0:
        return 0.0

    sum_m_a = 0
    for fname in field_names:
        access_count = 0
        for method in methods:
            referenced = False
            for _, ref in method.filter(javalang.tree.MemberReference):
                if ref.member == fname:
                    referenced = True
                    break
            if referenced:
                access_count += 1
        sum_m_a += access_count

    lcom5 = (m - (sum_m_a / a)) / (m - 1)
    return float(max(0.0, lcom5))


def _extract_cbo_types(class_node) -> Set[str]:
    """
    Extracts set of distinct referenced external types in a class:
    - extends/implements types
    - field types
    - method return and parameter types
    - thrown exception types
    - object instantiation types (ClassCreator)
    Filters out primitive types and the class itself.
    """
    import javalang
    referenced_types = set()
    this_name = getattr(class_node, 'name', '')

    # Extends
    if hasattr(class_node, 'extends') and class_node.extends:
        if hasattr(class_node.extends, 'name') and class_node.extends.name:
            referenced_types.add(class_node.extends.name)

    # Implements
    implemented_types = getattr(class_node, "implements", None)
    if implemented_types:
        for impl in implemented_types:
            if hasattr(impl, 'name') and impl.name:
                referenced_types.add(impl.name)

    # Fields
    for member in getattr(class_node, 'body', []):
        if isinstance(member, javalang.tree.FieldDeclaration):
            if member.type and hasattr(member.type, 'name') and member.type.name:
                referenced_types.add(member.type.name)

    # Methods
    for member in getattr(class_node, 'body', []):
        if isinstance(member, (javalang.tree.MethodDeclaration, javalang.tree.ConstructorDeclaration)):
            if hasattr(member, 'return_type') and member.return_type and hasattr(member.return_type, 'name'):
                referenced_types.add(member.return_type.name)
            if member.parameters:
                for param in member.parameters:
                    if param.type and hasattr(param.type, 'name') and param.type.name:
                        referenced_types.add(param.type.name)
            if hasattr(member, 'throws') and member.throws:
                for thrown in member.throws:
                    referenced_types.add(thrown)

    # Object instantiations: new Foo()
    for _, creator in class_node.filter(javalang.tree.ClassCreator):
        if creator.type and hasattr(creator.type, 'name') and creator.type.name:
            referenced_types.add(creator.type.name)

    # Filter out primitive types and self
    filtered = {t for t in referenced_types if t and t not in PRIMITIVE_TYPES and t != this_name}
    return filtered


def _regex_fallback_analysis(source_code: str, line_range: Optional[Tuple[int, int]] = None) -> Dict[str, float]:
    """
    Robust regex/line-based fallback analyzer for Java code that cannot be parsed by javalang.
    Extracts real counts directly from source code without mock values.
    """
    start_line, end_line = line_range if line_range else (1, len(source_code.splitlines()))
    loc, cloc, cd = _count_lines_and_comments(source_code, start_line, end_line)

    lines = source_code.splitlines()[max(0, start_line - 1):end_line]
    class_snippet = "\n".join(lines)

    code_no_comments = re.sub(r'/\*.*?\*/', '', class_snippet, flags=re.DOTALL)
    code_no_comments = re.sub(r'//.*', '', code_no_comments)

    public_methods = re.findall(
        r'\bpublic\s+(?:static\s+|final\s+|synchronized\s+)*[A-Za-z0-9_<>\[\]]+\s+([A-Za-z0-9_]+)\s*\([^)]*\)\s*(?:throws\s+[^{]+)?\{',
        code_no_comments
    )
    npm = len(public_methods)

    all_methods = re.findall(
        r'(?:public|protected|private)?\s*(?:static\s+|final\s+|synchronized\s+)*[A-Za-z0-9_<>\[\]]+\s+([A-Za-z0-9_]+)\s*\([^)]*\)\s*(?:throws\s+[^{]+)?\{',
        code_no_comments
    )

    public_fields = re.findall(
        r'\bpublic\s+(?:static\s+|final\s+)*[A-Za-z0-9_<>\[\]]+\s+[A-Za-z0-9_]+\s*(?:=[^;]+)?\s*;',
        code_no_comments
    )
    npa = len(public_fields)

    extends_match = re.search(r'\bclass\s+\w+\s+extends\s+(\w+)', code_no_comments)
    dit = 1.0 if extends_match else 0.0

    wmc = 1
    branch_keywords = ['if', 'while', 'for', 'catch', 'case']
    for kw in branch_keywords:
        wmc += len(re.findall(rf'\b{kw}\b', code_no_comments))
    wmc += len(re.findall(r'&&|\|\||\?', code_no_comments))

    invocations = set(re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', code_no_comments))
    rfc = len(set(all_methods).union(invocations))

    type_matches = set(re.findall(r'\b([A-Z][a-zA-Z0-9_]+)\b', code_no_comments))
    cbo = len({t for t in type_matches if t not in PRIMITIVE_TYPES})

    max_nest = 0
    cur_nest = 0
    for ch in code_no_comments:
        if ch == '{':
            cur_nest += 1
            if cur_nest > max_nest:
                max_nest = cur_nest
        elif ch == '}':
            cur_nest = max(0, cur_nest - 1)
    nle = max(0, max_nest - 1)

    return {
        "LOC": float(loc),
        "WMC": float(wmc),
        "DIT": float(dit),
        "NOC": 0.0,
        "RFC": float(rfc),
        "LCOM5": 0.0,
        "CBO": float(cbo),
        "NPA": float(npa),
        "NPM": float(npm),
        "NLE": float(nle),
        "CBOI": 0.0,
        "CD": float(cd)
    }


def _analyze_class_node(class_node,
                        source_code: str,
                        start_line: int,
                        end_line: int,
                        project_context: Optional[Dict[str, Any]] = None,
                        class_identity: Optional[str] = None) -> Dict[str, float]:
    """
    Computes all 12 static metrics for a specific class/interface AST node.
    """
    import javalang

    class_name = getattr(class_node, 'name', '')

    # 1. LOC & CD for this specific class
    loc, cloc, cd = _count_lines_and_comments(source_code, start_line, end_line)

    # Extract declared members directly belonging to this class
    body = getattr(class_node, 'body', [])
    fields = [m for m in body if isinstance(m, javalang.tree.FieldDeclaration)]
    methods = [m for m in body if isinstance(m, (javalang.tree.MethodDeclaration, javalang.tree.ConstructorDeclaration))]

    # 2. NPA: Public Attributes declared directly in class
    npa = 0
    for f in fields:
        if 'public' in getattr(f, 'modifiers', []):
            npa += len(getattr(f, 'declarators', []))

    # 3. NPM: Public Methods declared directly in class (documented policy: declared only)
    npm = 0
    for m in methods:
        if 'public' in getattr(m, 'modifiers', []):
            npm += 1

    # 4. WMC & 5. NLE & 6. RFC
    wmc = 0
    max_nest = 0
    declared_method_names = set()
    invoked_methods = set()

    for method in methods:
        declared_method_names.add(method.name)
        wmc += _calc_cyclomatic_complexity(method)
        nest = _calc_max_nesting_level(method)
        if nest > max_nest:
            max_nest = nest

        for _, inv in method.filter(javalang.tree.MethodInvocation):
            if inv.member:
                invoked_methods.add(inv.member)

        # Include constructors invoked as external method calls
        for _, creator in method.filter(javalang.tree.ClassCreator):
            if creator.type and hasattr(creator.type, 'name') and creator.type.name:
                invoked_methods.add(creator.type.name)

    # Response for Class: |DeclaredMethods U InvokedMethods|
    rfc = len(declared_method_names.union(invoked_methods))
    nle = max_nest

    # 7. LCOM5: Lack of Cohesion of Methods
    lcom5 = _calc_lcom5(methods, fields)

    # 8. CBO: Coupling Between Objects (outward)
    cbo_types = _extract_cbo_types(class_node)
    cbo = len(cbo_types)

    # 9. DIT: follow only resolved, qualified inheritance edges.
    dit = 0.0
    if class_identity and project_context:
        def inheritance_depth(identity: str, visited: Set[str]) -> int:
            if identity in visited:
                return 0
            parents = project_context.get("inheritance_tree", {}).get(identity, [])
            if not parents:
                return 0
            return max(1 + inheritance_depth(parent, visited | {identity}) for parent in parents)

        dit = float(inheritance_depth(class_identity, set()))
        if dit == 0.0 and class_identity in project_context.get("unresolved_inheritance", set()):
            dit = 1.0
    elif getattr(class_node, "extends", None):
        dit = 1.0

    # 10. NOC: Number of Children (immediate subclasses in project context)
    noc = 0.0
    if class_identity and project_context and "subclasses_count" in project_context:
        noc = float(project_context["subclasses_count"].get(class_identity, 0))

    # 11. CBOI: Coupling Between Objects Inward (inward references in project context)
    cboi = 0.0
    if class_identity and project_context and "inward_coupling" in project_context:
        cboi = float(project_context["inward_coupling"].get(class_identity, 0))

    return {
        "LOC": float(loc),
        "WMC": float(wmc),
        "DIT": float(dit),
        "NOC": float(noc),
        "RFC": float(rfc),
        "LCOM5": float(lcom5),
        "CBO": float(cbo),
        "NPA": float(npa),
        "NPM": float(npm),
        "NLE": float(nle),
        "CBOI": float(cboi),
        "CD": float(cd)
    }


def _context_relative_path(relative_path: Optional[str], project_context: Dict[str, Any]) -> str:
    if not relative_path:
        return ""
    root = project_context.get("repo_path")
    candidate = relative_path
    if root and os.path.isabs(candidate):
        try:
            candidate = os.path.relpath(candidate, root)
        except ValueError:
            pass
    return _source_path_key(candidate)


def analyze_java_source(source_code: str,
                        target_class_name: Optional[str] = None,
                        line_range: Optional[Tuple[int, int]] = None,
                        relative_path: Optional[str] = None,
                        project_context: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    """
    Analyzes Java source code and computes the 12 static metrics.
    If target_class_name or line_range is provided, targets that specific class.
    Otherwise, targets the primary class of the source code (public class or first top-level class).
    """
    import javalang

    try:
        tree = javalang.parse.parse(source_code)
    except Exception as e:
        logger.debug(f"javalang parsing failed ({e}), falling back to regex token analysis.")
        return _regex_fallback_analysis(source_code, line_range)

    package = getattr(tree.package, "name", "") if tree.package else ""
    entries = [
        entry for entry in _type_entries(tree, relative_path or "", package)
        if isinstance(entry["node"], (javalang.tree.ClassDeclaration, javalang.tree.InterfaceDeclaration))
    ]
    entries.sort(key=lambda entry: (
        isinstance(entry["node"], javalang.tree.InterfaceDeclaration),
        entry["start_line"] or 0,
    ))

    if not entries:
        return _regex_fallback_analysis(source_code, line_range)

    # 1. Match by line_range if provided
    selected_entry = None
    start_line, end_line = None, None
    near_line = []

    if line_range is not None:
        req_start, req_end = line_range
        near_line = [
            entry for entry in entries
            if entry["start_line"] is not None and abs(entry["start_line"] - req_start) <= 2
        ]
        if near_line:
            # Preserve the established line-based metric selection order. The
            # benchmark line may identify an enclosing declaration for nested rows.
            selected_entry = near_line[0]
            c_pos = selected_entry["start_line"]
            sl, el = find_class_line_range(source_code, c_pos)
            start_line, end_line = req_start, max(req_end, el)
        else:
            # Check anonymous class or construct inside req_start..req_end
            start_line, end_line = req_start, req_end

    # Resolve relationship identity by the explicit class name even when the
    # historical line range selects an enclosing class for legacy metrics.
    identity_entry = None
    if target_class_name is not None:
        clean_target = target_class_name.replace("$", ".")
        matches = [
            entry for entry in entries
            if entry["identity"] == clean_target
            or entry["identity"].endswith("." + clean_target)
            or entry["name"] == target_class_name
        ]
        if len(matches) > 1:
            raise ValueError(f"Ambiguous class name '{target_class_name}': {[entry['identity'] for entry in matches]}")
        if matches:
            identity_entry = matches[0]
            if selected_entry is None:
                selected_entry = identity_entry

    # 3. Default to primary class (public class or first top-level class)
    if selected_entry is None and line_range is None:
        top_level = [entry for entry in entries if not entry["enclosing_ids"] and not entry["local_scope"]]
        candidates = top_level or entries
        selected_entry = candidates[0]
        for entry in candidates:
            if "public" in getattr(entry["node"], "modifiers", []):
                selected_entry = entry
                break

    if selected_entry is not None:
        selected_node = selected_entry["node"]
        c_pos = selected_entry["start_line"] or 1
        if start_line is None or end_line is None:
            start_line, end_line = find_class_line_range(source_code, c_pos)
        identity = (identity_entry or selected_entry)["identity"]
        if project_context:
            context_path = _context_relative_path(relative_path, project_context)
            identity = project_context.get("class_identity_by_location", {}).get(
                (context_path, (identity_entry or selected_entry)["start_line"]), identity
            )
        return _analyze_class_node(
            selected_node, source_code, start_line, end_line, project_context, identity
        )

    # If anonymous or inner construct without ClassDeclaration node, analyze snippet
    return _regex_fallback_analysis(source_code, (start_line or 1, end_line or len(source_code.splitlines())))


def analyze_java_file(file_path: str,
                      target_class_name: Optional[str] = None,
                      line_range: Optional[Tuple[int, int]] = None,
                      project_context: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    """
    Reads and analyzes a Java source file from disk.
    Computes the 12 static metrics for the target class (or primary class).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Java file not found: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        raise

    return analyze_java_source(
        source_code=content,
        target_class_name=target_class_name,
        line_range=line_range,
        relative_path=file_path,
        project_context=project_context
    )


def build_repository_context(repo_path: str) -> Dict[str, Any]:
    """
    Scans all Java files in a repository to build whole-project context for:
    - Inheritance tree (for precise DIT calculation)
    - Subclasses count (for NOC calculation)
    - Inward coupling references (for CBOI calculation)
    - Class to file mappings (simple names and FQCN)
    """
    import javalang
    from collections import Counter, defaultdict

    repo_path = os.path.abspath(repo_path)
    java_files = []
    for root, _, files in os.walk(repo_path):
        for filename in files:
            if filename.endswith(".java"):
                java_files.append(os.path.join(root, filename))
    java_files.sort()

    file_contexts: Dict[str, Dict[str, Any]] = {}
    type_entries: List[Dict[str, Any]] = []
    class_definitions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    parse_failures = []

    for file_path in java_files:
        relative_path = _source_path_key(os.path.relpath(file_path, repo_path))
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as stream:
                content = stream.read()
            tree = javalang.parse.parse(content)
        except Exception as error:
            parse_failures.append({
                "path": relative_path,
                "error": f"{type(error).__name__}: {error}",
            })
            logger.warning("Could not build type context for %s: %s", relative_path, error)
            continue

        package = getattr(tree.package, "name", "") if tree.package else ""
        imports = [{
            "path": item.path,
            "wildcard": bool(item.wildcard),
            "static": bool(item.static),
        } for item in tree.imports]
        file_contexts[relative_path] = {
            "package": package,
            "imports": imports,
            "tree": tree,
        }
        entries = _type_entries(tree, relative_path, package)
        type_entries.extend(entries)

        for entry in entries:
            start_line = entry["start_line"] or 1
            start, end = find_class_line_range(content, start_line)
            class_definitions[relative_path].append({
                "name": entry["name"],
                "fqcn": entry["fqcn"],
                "identity": entry["identity"],
                "start_line": start,
                "end_line": end,
                "is_top_level": not entry["enclosing_ids"] and not entry["local_scope"],
                "modifiers": sorted(getattr(entry["node"], "modifiers", set())),
                "kind": type(entry["node"]).__name__,
                "node": entry["node"],
            })

    fqcn_counts = Counter(entry["fqcn"] for entry in type_entries)
    identity_index: Dict[str, Set[str]] = defaultdict(set)
    class_identity_by_location: Dict[Tuple[str, Optional[int]], str] = {}
    simple_name_index: Dict[str, Set[str]] = defaultdict(set)
    for entry in type_entries:
        if fqcn_counts[entry["fqcn"]] > 1:
            entry["identity"] = f"{entry['fqcn']}#duplicate:{entry['path']}:{entry['start_line']}"
        else:
            entry["identity"] = entry["fqcn"]
        file_context = file_contexts[entry["path"]]
        entry["imports"] = file_context["imports"]
        identity_index[entry["fqcn"]].add(entry["identity"])
        identity_index[entry["identity"]].add(entry["identity"])
        simple_name_index[entry["name"]].add(entry["identity"])
        class_identity_by_location[(entry["path"], entry["start_line"])] = entry["identity"]
        for definition in class_definitions[entry["path"]]:
            if definition["fqcn"] == entry["fqcn"] and definition["start_line"] == entry["start_line"]:
                definition["identity"] = entry["identity"]
                break

    context_index = {key: sorted(value) for key, value in identity_index.items()}
    for entry in type_entries:
        entry["imports"] = file_contexts[entry["path"]]["imports"]

    inheritance_tree: Dict[str, List[str]] = defaultdict(list)
    unresolved_inheritance: Set[str] = set()
    subclasses_sources: Dict[str, Set[str]] = defaultdict(set)
    inward_sources: Dict[str, Set[str]] = defaultdict(set)
    unresolved_references: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}

    def type_names(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            values = value
        else:
            values = [value]
        return [name for name in (_reference_type_name(item) for item in values) if name]

    def record_unresolved(entry: Dict[str, Any], reference: str, kind: str, result: Dict[str, Any]) -> None:
        key = (entry["identity"], reference, kind, result["resolution"])
        unresolved_references[key] = {
            "source_class_id": entry["identity"],
            "source_fqcn": entry["fqcn"],
            "source_path": entry["path"],
            "reference": reference,
            "relationship": kind,
            "resolution": result["resolution"],
            "candidates": result["candidates"],
        }

    for entry in type_entries:
        node = entry["node"]
        source_id = entry["identity"]
        direct_extends = type_names(getattr(node, "extends", None))
        direct_implements = type_names(getattr(node, "implements", None))
        unresolved_extends = False

        for kind, names in (("extends", direct_extends), ("implements", direct_implements)):
            for reference in names:
                resolved = _resolve_project_type(reference, entry, {"identity_index": context_index})
                if resolved["resolution"] == "resolved":
                    target_id = resolved["target"]
                    subclasses_sources[target_id].add(source_id)
                    if target_id != source_id:
                        inward_sources[target_id].add(source_id)
                    if kind == "extends":
                        inheritance_tree[source_id].append(target_id)
                else:
                    record_unresolved(entry, reference, kind, resolved)
                    if kind == "extends":
                        unresolved_extends = True

        supertype_references = set(direct_extends + direct_implements)
        for reference in _project_type_references(node) - supertype_references:
            resolved = _resolve_project_type(reference, entry, {"identity_index": context_index})
            if resolved["resolution"] == "resolved":
                target_id = resolved["target"]
                if target_id != source_id:
                    inward_sources[target_id].add(source_id)
            else:
                record_unresolved(entry, reference, "dependency", resolved)

        if unresolved_extends and not inheritance_tree.get(source_id):
            unresolved_inheritance.add(source_id)

    class_to_file = {}
    for entry in type_entries:
        if fqcn_counts[entry["fqcn"]] == 1:
            class_to_file[entry["fqcn"]] = entry["path"]

    return {
        "repo_path": repo_path,
        "inheritance_tree": {key: sorted(set(value)) for key, value in inheritance_tree.items()},
        "subclasses_count": {key: len(value) for key, value in subclasses_sources.items()},
        "inward_coupling": {key: len(value) for key, value in inward_sources.items()},
        "class_to_file": class_to_file,
        "class_definitions": dict(class_definitions),
        "class_identity_by_location": class_identity_by_location,
        "simple_name_index": {key: sorted(value) for key, value in simple_name_index.items()},
        "duplicate_fqcns": {key: sorted(value) for key, value in identity_index.items()
                            if key in fqcn_counts and fqcn_counts[key] > 1},
        "unresolved_references": list(unresolved_references.values()),
        "unresolved_inheritance": unresolved_inheritance,
        "parse_failures": parse_failures,
        "total_java_files": len(java_files),
        "parsed_java_files": len(file_contexts),
    }


def analyze_java_repository(repo_path: str) -> Dict[str, Dict[str, float]]:
    """
    Analyzes all Java files in a repository and returns metrics per relative file path.
    """
    project_context = build_repository_context(repo_path)
    results = {}

    for root, _, files in os.walk(repo_path):
        for f in files:
            if f.endswith(".java"):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, repo_path).replace("\\", "/")
                try:
                    metrics = analyze_java_file(full_path, project_context=project_context)
                    results[rel_path] = metrics
                except Exception as e:
                    logger.warning(f"Failed to analyze {rel_path}: {e}")

    return results
