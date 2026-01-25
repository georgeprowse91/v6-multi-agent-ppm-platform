# Merge Conflict Troubleshooting

This note captures the conflict resolution workflow used for this repo when a PR reports
"Unable to merge" in GitHub.

## Current observation

Attempting to fetch the remote in this environment failed due to network restrictions:

```text
fatal: unable to access 'https://github.com/georgeprowse91/multi-agent-ppm-platform.git/': CONNECT tunnel failed, response 403
```

## How to resolve locally

Run these commands from a clone that has access to the remote:

```bash
git checkout <your-feature-branch>
git fetch origin
git rebase origin/main   # or origin/develop, matching the PR base branch
# resolve conflicts
# edit files, then:
git add <resolved_files>
git rebase --continue
git push --force-with-lease
```

## How to verify

```bash
git status --short
```

Expected output shows a clean working tree (no conflict markers and no unmerged paths).
