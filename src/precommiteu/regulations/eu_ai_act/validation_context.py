"""AI Act validation context, kept separate from the public findings schema."""
from __future__ import annotations

import ast
import textwrap

from pydantic import StrictStr

from precommiteu.src.schemas import ValidatorOutput

FACTS_INSTRUCTIONS = """
Before findings, emit a code_facts string summarising the concrete actor, activity,
and effect of the cited operations. Evaluate constant values and whether a guard
actually executes. A disabled guard does not enforce its named safeguard.
Output exactly {"code_facts":"brief facts visible in the code","findings":[...]}.
Keep the same finding fields and source-evidence requirements.
"""


class AIActValidatorOutput(ValidatorOutput):
    # Used during validation; excluded from public findings.
    code_facts: StrictStr


def facts_first_grammar(evidence_grammar: str) -> str:
    """Emit code_facts before findings, keeping the existing evidence choices."""
    return evidence_grammar.replace(
        'root ::= "{" space "\\\"findings\\\""',
        'root ::= "{" space "\\\"code_facts\\\"" space ":" space string '
        'space "," space "\\\"findings\\\""',
        1,
    )


def literal_fields_on_line(code: str, evidence: str) -> dict:
    """Read literal configuration on the cited Python line without executing code.

    Variables, expressions and conflicting assignments are left to the model.
    """
    code = textwrap.dedent(code)
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError):
        return {}
    lines = {i for i, line in enumerate(code.splitlines(), 1) if line.strip() == evidence.strip()}
    observed = {}
    for node in ast.walk(tree):
        pairs = []
        if isinstance(node, ast.Call):
            pairs = [(keyword.arg, keyword.value) for keyword in node.keywords]
        elif isinstance(node, ast.Dict):
            pairs = [(key.value, value) for key, value in zip(node.keys, node.values, strict=True)
                     if isinstance(key, ast.Constant) and isinstance(key.value, str)]
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            pairs = [(target.id if isinstance(target, ast.Name) else target.attr, node.value)
                     for target in targets if isinstance(target, (ast.Name, ast.Attribute))]
        for key, value in pairs:
            if (key is not None and isinstance(value, ast.Constant) and value.lineno in lines
                and type(value.value) in (str, int, float, bool, type(None))):
                observed.setdefault(key, []).append(value.value)
    return {key: values[0] for key, values in observed.items()
            if all(type(value) is type(values[0]) and value == values[0] for value in values)}
