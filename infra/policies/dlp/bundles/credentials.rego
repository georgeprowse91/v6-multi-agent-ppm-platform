package dlp.credentials

# DLP policy to deny payloads containing credentials or secret keys.

# Patterns for credential detection. Each entry has a "regex" key with a
# regular expression to match against payload content.
credential_patterns := [
    {"type": "aws_access_key", "regex": "AKIA[0-9A-Z]{16}"},
    {"type": "github_pat", "regex": "ghp_[A-Za-z0-9]{36}"},
    {"type": "bearer_token", "regex": "Bearer\\s+[A-Za-z0-9\\-._~+/]+=*"},
    {"type": "generic_secret", "regex": "(?i)(secret|password|passwd|token)[\\s:=]+[A-Za-z0-9\\-_]{8,}"},
]

default deny = false

deny {
    pattern := credential_patterns[_]
    regex.match(pattern.regex, input.payload)
}
