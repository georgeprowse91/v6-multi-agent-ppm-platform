package dlp.pii

# DLP policy to deny payloads containing Personally Identifiable Information (PII).

# Patterns for PII detection. Each entry has a "regex" key with a regular
# expression to match against payload content.
pii_patterns := [
    {"type": "email", "regex": "[a-zA-Z0-9._%+\\-]+@[a-zA-Z0-9.\\-]+\\.[a-zA-Z]{2,}"},
    {"type": "ssn", "regex": "\\d{3}-\\d{2}-\\d{4}"},
    {"type": "phone", "regex": "\\b\\d{3}[-.\\s]\\d{3}[-.\\s]\\d{4}\\b"},
    {"type": "credit_card", "regex": "\\b(?:\\d[ -]?){13,16}\\b"},
]

default deny = false

deny {
    pattern := pii_patterns[_]
    regex.match(pattern.regex, input.payload)
}
