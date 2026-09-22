from __future__ import annotations

import json

__all__ = [
    "DETECTOR_GBNF",
    "LOOP_STEP_GBNF",
    "VALIDATOR_GBNF",
    "validator_evidence_grammar",
]

LOOP_STEP_GBNF = r"""
root ::= action | emit
action ::= "ACTION:" ws tool-name "(" args ")" ws? newline reason?
emit ::= "EMIT" ws? newline reason?
tool-name ::= ("read_file" | "read_chunk" | "list_chunks" | "list_dir"
            | "glob" | "grep" | "read_article" | "list_articles"
            | "grep_regulation" | "find_references"
            | "call_detector" | "call_validator" | "write_todos")
args ::= (kv (ws? "," ws? kv)*)?
kv ::= key ws? "=" ws? value
value ::= string | integer | boolean
key ::= [a-z_]+
string ::= "\"" chars "\""
chars ::= char*
char ::= [^"\\] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])
integer ::= "-"? [0-9]+
boolean ::= "true" | "false" | "True" | "False"
ws ::= [ \t]
newline ::= "\n"
reason ::= [^\x00]*
"""


DETECTOR_GBNF = r"""root ::= "<reasoning>" reasoning-content "</reasoning>" newline "<findings>" json-root "</findings>"
reasoning-content ::= [^<]*
newline ::= "\n"
InferenceFindingDescriptionOnly ::= "{" space InferenceFindingDescriptionOnly-description-kv "}" space
InferenceFindingDescriptionOnly-description-kv ::= "\"description\"" space ":" space string
char ::= [^"\\] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])
findings ::= "[" space (findings-item ("," space findings-item)*)? "]" space
findings-item ::= InferenceFindingDescriptionOnly
findings-kv ::= "\"findings\"" space ":" space findings
json-root ::= "{" space findings-kv "}" space
space ::= " "?
string ::= "\"" char* "\"" space"""


VALIDATOR_GBNF = r"""
root ::= "{" space "\"findings\"" space ":" space findings-array space "}" space
findings-array ::= "[" space "]" | "[" space finding (space "," space finding)* space "]"
finding ::= "{" space article-kv space "," space code-evidence-kv space "," space description-kv space "}"
article-kv ::= "\"article_no\"" space ":" space string
code-evidence-kv ::= "\"code_evidence\"" space ":" space evidence
evidence ::= string
description-kv ::= "\"description\"" space ":" space string
string ::= "\"" chars "\""
chars ::= char*
char ::= [^"\\] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F])
space ::= " "?
"""


def validator_evidence_grammar(evidence_options: list[str]) -> str:
    if not evidence_options:
        raise ValueError("validator grammar requires at least one source excerpt")
    # Each GBNF literal emits one complete JSON string copied from the source.
    literals = [
        json.dumps(json.dumps(excerpt, ensure_ascii=False), ensure_ascii=False)
        for excerpt in dict.fromkeys(evidence_options)
    ]
    return VALIDATOR_GBNF.replace("evidence ::= string", "evidence ::= " + " | ".join(literals))
