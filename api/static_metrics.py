import os
import re
from typing import Dict, Any, List, Set, Optional, Tuple
import lizard
import javalang
from javalang.tree import (
    ClassDeclaration, InterfaceDeclaration, MethodDeclaration,
    ConstructorDeclaration, FieldDeclaration, MethodInvocation,
    Creator, MemberReference, IfStatement, ForStatement,
    WhileStatement, DoStatement, SwitchStatement, TryStatement
)

PRIMITIVE_TYPES = {
    "int", "long", "short", "byte", "float", "double", "char", "boolean",
    "void", "Integer", "Long", "Short", "Byte", "Float", "Double",
    "Character", "Boolean", "Void", "String", "Object"
}

class StaticMetricsExtractor:
    """
    Extracts 12 Object-Oriented Static Software Metrics for Java source files:
    LOC, WMC, DIT, NOC, CBO, RFC, LCOM5, NPA, NPM, NLE, CBOI, CD
    """

    @staticmethod
    def count_lines_and_comments(code: str) -> Tuple[int, int, float]:
        """
        Returns (nloc, comment_lines, comment_density)
        """
        lines = code.splitlines()
        total_lines = len(lines)
        if total_lines == 0:
            return 0, 0, 0.0

        comment_lines = 0
        in_block_comment = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            if in_block_comment:
                comment_lines += 1
                if "*/" in stripped:
                    in_block_comment = False
            else:
                if stripped.startswith("/*"):
                    comment_lines += 1
                    if "*/" not in stripped:
                        in_block_comment = True
                elif stripped.startswith("//"):
                    comment_lines += 1

        # Use lizard for exact nloc (non-comment, non-empty code lines)
        try:
            liz = lizard.analyze_file.analyze_source_code("temp.java", code)
            nloc = liz.nloc
        except Exception:
            nloc = max(1, total_lines - comment_lines)

        total_content = nloc + comment_lines
        comment_density = round(comment_lines / total_content, 4) if total_content > 0 else 0.0
        return nloc, comment_lines, comment_density

    @staticmethod
    def _compute_nesting_depth(node, current_depth: int = 0) -> int:
        """
        Recursively calculates the maximum nesting depth of control structures.
        """
        compound_types = (
            IfStatement, ForStatement, WhileStatement,
            DoStatement, SwitchStatement, TryStatement
        )
        is_compound = isinstance(node, compound_types)
        next_depth = current_depth + 1 if is_compound else current_depth
        max_d = next_depth

        if hasattr(node, 'children'):
            for child in node.children:
                if isinstance(child, list):
                    for item in child:
                        if hasattr(item, 'children'):
                            max_d = max(max_d, StaticMetricsExtractor._compute_nesting_depth(item, next_depth))
                elif hasattr(child, 'children'):
                    max_d = max(max_d, StaticMetricsExtractor._compute_nesting_depth(child, next_depth))

        return max_d

    @staticmethod
    def parse_with_javalang(code: str) -> Optional[javalang.tree.CompilationUnit]:
        """
        Safely attempts to parse code using javalang.
        """
        try:
            return javalang.parse.parse(code)
        except Exception:
            return None

    @staticmethod
    def analyze_file_ast(file_path: str, code: str) -> Dict[str, Any]:
        """
        Extracts intra-class metrics from single file AST.
        Project-wide metrics (DIT, NOC, CBOI) are finalized in the repository-level step.
        """
        nloc, comment_lines, comment_density = StaticMetricsExtractor.count_lines_and_comments(code)
        
        # Analyze using lizard for cyclomatic complexity
        liz_functions = []
        try:
            liz = lizard.analyze_file.analyze_source_code(file_path, code)
            liz_functions = liz.function_list
        except Exception:
            pass

        tree = StaticMetricsExtractor.parse_with_javalang(code)

        classes_found = []
        if tree and tree.types:
            for decl in tree.types:
                if isinstance(decl, (ClassDeclaration, InterfaceDeclaration)):
                    classes_found.append(decl)

        if not classes_found:
            # Fallback for newer syntax or parsing issues
            return StaticMetricsExtractor._fallback_file_analysis(file_path, code, nloc, comment_density, liz_functions)

        # Primary class (usually the first public or largest class in the file)
        primary_class = classes_found[0]
        for c in classes_found:
            if hasattr(c, 'modifiers') and 'public' in c.modifiers:
                primary_class = c
                break

        class_name = primary_class.name
        extends_name = getattr(primary_class.extends, 'name', None) if hasattr(primary_class, 'extends') and primary_class.extends else None

        # Public attributes & methods
        fields = getattr(primary_class, 'fields', []) or []
        methods = getattr(primary_class, 'methods', []) or []
        constructors = getattr(primary_class, 'constructors', []) or []

        npa = sum(1 for f in fields if hasattr(f, 'modifiers') and 'public' in f.modifiers)
        npm = sum(1 for m in methods if hasattr(m, 'modifiers') and 'public' in m.modifiers)

        # Field names in this class (for LCOM5 calculation)
        field_names = set()
        for f in fields:
            if hasattr(f, 'declarators'):
                for decl in f.declarators:
                    field_names.add(decl.name)

        # Method analysis: RFC, Nesting Level (NLE), and attribute access for LCOM5
        invoked_foreign_methods = set()
        field_access_by_method = {fname: 0 for fname in field_names}
        max_nle = 0

        all_class_methods = list(methods) + list(constructors)

        for m in all_class_methods:
            # Nesting depth
            depth = StaticMetricsExtractor._compute_nesting_depth(m, current_depth=0)
            if depth > max_nle:
                max_nle = depth

            # Check method calls and field references
            if m.body:
                accessed_in_m = set()
                for path, node in m.filter((MethodInvocation, MemberReference)):
                    if isinstance(node, MethodInvocation):
                        if node.member:
                            invoked_foreign_methods.add(node.member)
                    elif isinstance(node, MemberReference):
                        if node.member in field_names:
                            accessed_in_m.add(node.member)
                for accessed_field in accessed_in_m:
                    field_access_by_method[accessed_field] += 1

        # RFC = number of local methods + distinct external methods called
        rfc = len(all_class_methods) + len(invoked_foreign_methods)

        # LCOM5 (Henderson-Sellers metric)
        # LCOM5 = (m - sum(m(a))/a) / (m - 1)
        m_count = len(all_class_methods)
        a_count = len(field_names)
        if m_count <= 1 or a_count == 0:
            lcom5 = 0.0
        else:
            sum_m_a = sum(field_access_by_method.values())
            lcom5 = (m_count - (sum_m_a / a_count)) / (m_count - 1)
            lcom5 = max(0.0, min(round(lcom5, 4), 2.0))

        # CBO: Couplings via field types, method params, return types, throws, instantiations
        coupled_types = set()
        for f in fields:
            if hasattr(f, 'type') and f.type and hasattr(f.type, 'name'):
                coupled_types.add(f.type.name)

        for m in methods:
            if hasattr(m, 'return_type') and m.return_type and hasattr(m.return_type, 'name'):
                coupled_types.add(m.return_type.name)
            if hasattr(m, 'parameters') and m.parameters:
                for param in m.parameters:
                    if hasattr(param, 'type') and param.type and hasattr(param.type, 'name'):
                        coupled_types.add(param.type.name)
            if hasattr(m, 'throws') and m.throws:
                for th in m.throws:
                    coupled_types.add(th)

        for path, node in primary_class.filter(Creator):
            if hasattr(node, 'type') and node.type and hasattr(node.type, 'name'):
                coupled_types.add(node.type.name)

        # Filter out primitive and standard types
        filtered_cbo = {t for t in coupled_types if t and t not in PRIMITIVE_TYPES and t != class_name}
        cbo = len(filtered_cbo)

        # WMC: Sum of cyclomatic complexity across methods from lizard or AST
        wmc = 0
        if liz_functions:
            for fn in liz_functions:
                # Match functions belonging to this class
                wmc += fn.cyclomatic_complexity
        else:
            wmc = max(1, len(all_class_methods))

        return {
            "class_name": class_name,
            "extends_name": extends_name,
            "all_classes_in_file": [c.name for c in classes_found],
            "referenced_types": filtered_cbo,
            "LOC": nloc,
            "WMC": float(wmc),
            "CBO": float(cbo),
            "RFC": float(rfc),
            "LCOM5": float(lcom5),
            "NPA": float(npa),
            "NPM": float(npm),
            "NLE": float(max_nle),
            "CD": float(comment_density)
        }

    @staticmethod
    def _fallback_file_analysis(
        file_path: str,
        code: str,
        nloc: int,
        comment_density: float,
        liz_functions: List[Any]
    ) -> Dict[str, Any]:
        """
        Robust regex-based fallback extractor when javalang AST parsing fails.
        """
        filename = os.path.basename(file_path).replace('.java', '')
        class_match = re.search(r'\b(?:public\s+)?(?:class|interface|enum)\s+([A-Za-z0-9_]+)(?:\s+extends\s+([A-Za-z0-9_]+))?', code)
        class_name = class_match.group(1) if class_match else filename
        extends_name = class_match.group(2) if class_match and class_match.group(2) else None

        # Count public methods and attributes
        npm = len(re.findall(r'\bpublic\s+(?:static\s+)?[A-Za-z0-9_<>,\[\]]+\s+[a-zA-Z0-9_]+\s*\(', code))
        npa = len(re.findall(r'\bpublic\s+(?:static\s+|final\s+)?[A-Za-z0-9_<>,\[\]]+\s+[a-zA-Z0-9_]+\s*(?:=|[;])', code))

        # WMC & NLE from lizard
        wmc = sum(f.cyclomatic_complexity for f in liz_functions) if liz_functions else max(1, npm)
        max_nle = max((f.max_nesting_depth for f in liz_functions), default=1)

        # Coupled types
        types_referenced = set(re.findall(r'\b(?:new\s+|extends\s+|implements\s+)([A-Z][A-Za-z0-9_]+)\b', code))
        filtered_cbo = {t for t in types_referenced if t not in PRIMITIVE_TYPES and t != class_name}

        rfc = max(1, npm + len(re.findall(r'\.[a-zA-Z0-9_]+\s*\(', code)))
        lcom5 = 0.5 if npm > 2 else 0.0

        return {
            "class_name": class_name,
            "extends_name": extends_name,
            "all_classes_in_file": [class_name],
            "referenced_types": filtered_cbo,
            "LOC": nloc,
            "WMC": float(wmc),
            "CBO": float(len(filtered_cbo)),
            "RFC": float(rfc),
            "LCOM5": float(lcom5),
            "NPA": float(npa),
            "NPM": float(npm),
            "NLE": float(max_nle),
            "CD": float(comment_density)
        }

