package dlp.credentials

patterns := [
  {"id": "token-aws-access", "regex": "AKIA[0-9A-Z]{16}", "message": "AWS access key detected"},
  {"id": "token-github", "regex": "ghp_[A-Za-z0-9]{36}", "message": "GitHub token detected"},
  {"id": "token-slack", "regex": "xox[baprs]-[A-Za-z0-9-]+", "message": "Slack token detected"},
  {"id": "token-jwt", "regex": "eyJ[a-zA-Z0-9_-]+\\.[a-zA-Z0-9_-]+\\.[a-zA-Z0-9_-]+", "message": "JWT detected"}
]

default allow = true

deny[msg] {
  some pattern in patterns
  re_match(pattern.regex, input.payload)
  msg := pattern.message
}
