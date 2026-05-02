# Pre-commit Hook: Automatic Dependency Compilation

The project includes a git pre-commit hook that automatically regenerates `requirements.txt` whenever `requirements.in` is modified, ensuring the dependency lockfile stays in sync with the source file.

## How it works

When you attempt to commit changes that include `requirements.in`:

1. **Detection** — the hook detects `requirements.in` in the staging area
2. **Compilation** — runs `make compile-deps` (which executes `pip-compile` inside the dev container)
3. **Auto-staging** — automatically stages the regenerated `requirements.txt`
4. **Commit** — allows the commit to proceed with both files

If compilation fails (e.g., due to version conflicts), the commit is **blocked** until you fix the constraint.

## Usage

### Normal workflow

```bash
# Edit requirements.in
vim requirements.in

# Stage your change
git add requirements.in

# Commit — the hook runs automatically
git commit -m "Add greenlet dependency"
# Hook output:
# requirements.in modified — regenerating requirements.txt in dev container...
# ✓ requirements.txt regenerated and staged
```

Both `requirements.in` and the auto-generated `requirements.txt` are committed together.

### If compilation fails

```bash
# Commit fails because pip-compile found a conflict
git commit -m "Add conflicting package"
# ERROR: make compile-deps failed. Fix requirements.in and try again.

# Fix the conflict
vim requirements.in

# Re-stage and retry
git add requirements.in
git commit -m "Add conflicting package"
```

### Manually recompiling (for testing)

```bash
# Recompile in the dev container anytime
make compile-deps

# Verify the output
git diff requirements.txt

# Stage and commit when satisfied
git add requirements.txt
git commit -m "Update pinned dependencies"
```

## Requirements

- **Docker**: The hook runs `make compile-deps`, which uses Docker to ensure Python 3.11 and correct resolution
- **Executable hook**: The hook is installed at `.git/hooks/pre-commit` and must be executable (`chmod +x`)

## Troubleshooting

### Hook doesn't run

```bash
# Verify the hook is executable
ls -la .git/hooks/pre-commit

# Make it executable if needed
chmod +x .git/hooks/pre-commit
```

### Hook fails — Docker not available

```
ERROR: make compile-deps failed. Fix requirements.in and try again.
```

Ensure Docker is running:
```bash
docker --version
docker ps
```

### Hook fails — pip-compile error

The hook will show the pip-compile error output. Common issues:

**Version conflict:**
```
ERROR: Could not find a version that matches >=1.0.0,<2.0.0
```
→ Adjust the version bound in `requirements.in`

**Transitive dependency conflict:**
```
ERROR: pip's dependency resolver does not currently take into account all the packages
```
→ May need to adjust multiple bounds; run `make compile-deps` manually to see full error

## Implementation details

The hook is a simple bash script at `.git/hooks/pre-commit`. It:

- Uses git to detect staged files
- Runs `make compile-deps` (which handles Docker + pip-compile)
- Uses `git add requirements.txt` to stage the output
- Exits with status 0 (success) or 1 (failure)

The hook respects the Makefile's dependency compilation workflow, so it automatically:
- Uses the dev container's Python 3.11
- Applies `--strip-extras` and `--resolver=backtracking` flags
- Generates annotated output showing which dependencies depend on which

## Skipping the hook (not recommended)

If you absolutely must skip the hook:

```bash
git commit --no-verify -m "Skip hook"
```

⚠️ **Warning:** This breaks the invariant that `requirements.txt` matches `requirements.in`. Use only in emergencies, then immediately fix and recommit.

## See also

- [Dependency management](dependencies.md) — how pip-compile works and manual workflow
- [Makefile reference](../Makefile) — `make compile-deps` target
