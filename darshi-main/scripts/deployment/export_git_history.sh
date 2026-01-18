#!/bin/bash

# Export Git History Script
# Exports each commit's details into docs/commits/{commit_hash}/

set -e

OUTPUT_DIR="docs/commits"
mkdir -p "$OUTPUT_DIR"

echo "Exporting git history to $OUTPUT_DIR..."

# Get list of all commit hashes (oldest to newest)
COMMITS=$(git rev-list --reverse HEAD)

TOTAL=$(echo "$COMMITS" | wc -l)
COUNT=0

# Process each commit
for COMMIT in $COMMITS; do
    COUNT=$((COUNT + 1))
    echo "Processing commit $COUNT/$TOTAL: $COMMIT"

    # Create directory for this commit
    COMMIT_DIR="$OUTPUT_DIR/$COMMIT"
    mkdir -p "$COMMIT_DIR"

    # 1. Commit metadata (author, date, message, etc.)
    git show --no-patch --pretty=fuller "$COMMIT" > "$COMMIT_DIR/metadata.txt"

    # 2. Commit message only
    git log -1 --pretty=%B "$COMMIT" > "$COMMIT_DIR/message.txt"

    # 3. Files changed with stats
    git show --stat "$COMMIT" > "$COMMIT_DIR/stats.txt"

    # 4. List of files changed (one per line)
    git diff-tree --no-commit-id --name-only -r "$COMMIT" > "$COMMIT_DIR/files-changed.txt"

    # 5. Full diff (what actually changed)
    git show "$COMMIT" > "$COMMIT_DIR/diff.txt"

    # 6. Files changed with status (Added, Modified, Deleted)
    git show --name-status --pretty="" "$COMMIT" > "$COMMIT_DIR/file-status.txt"

    # 7. Compact summary (one-line)
    git log -1 --oneline "$COMMIT" > "$COMMIT_DIR/summary.txt"

    # 8. Parent commits
    git log -1 --pretty=%P "$COMMIT" > "$COMMIT_DIR/parents.txt"

    # 9. Author and committer info
    cat > "$COMMIT_DIR/info.txt" << EOF
Commit: $COMMIT
Author: $(git log -1 --pretty=%an "$COMMIT")
Author Email: $(git log -1 --pretty=%ae "$COMMIT")
Author Date: $(git log -1 --pretty=%aI "$COMMIT")
Committer: $(git log -1 --pretty=%cn "$COMMIT")
Committer Email: $(git log -1 --pretty=%ce "$COMMIT")
Committer Date: $(git log -1 --pretty=%cI "$COMMIT")
EOF

done

# Create a master index file
echo "Creating master index..."
cat > "$OUTPUT_DIR/INDEX.md" << 'EOF'
# Git History Index

This directory contains the complete git history of the repository.
Each commit has its own directory with the following files:

- `metadata.txt` - Full commit metadata (author, date, message)
- `message.txt` - Commit message only
- `summary.txt` - One-line summary
- `info.txt` - Structured author/committer information
- `stats.txt` - File statistics (insertions/deletions)
- `files-changed.txt` - List of files modified
- `file-status.txt` - Files with their status (A/M/D)
- `diff.txt` - Complete diff of changes
- `parents.txt` - Parent commit hashes

## Commits (newest first)

EOF

# Append commit list to index
git log --oneline --reverse >> "$OUTPUT_DIR/INDEX.md"

echo ""
echo "✓ Export complete!"
echo "Total commits exported: $TOTAL"
echo "Output directory: $OUTPUT_DIR"
echo "Index file: $OUTPUT_DIR/INDEX.md"
