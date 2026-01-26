package dlp.pii

patterns := [
  {"id": "pii-email", "regex": "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", "message": "Email address detected"},
  {"id": "pii-ssn", "regex": "\\b\d{3}-\d{2}-\d{4}\\b", "message": "US SSN detected"},
  {"id": "pii-credit-card", "regex": "\\b(?:\d[ -]*?){13,19}\\b", "message": "Payment card detected"}
]

default allow = true

deny[msg] {
  some pattern in patterns
  re_match(pattern.regex, input.payload)
  msg := pattern.message
}
