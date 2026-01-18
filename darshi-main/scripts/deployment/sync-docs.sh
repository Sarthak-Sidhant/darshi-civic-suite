#!/bin/bash
#
# Documentation Sync & Preview Script
# Usage: ./sync-docs.sh [build|serve|deploy]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCS_DIR="$SCRIPT_DIR/docs"
QUARTZ_DIR="$SCRIPT_DIR/docs-quartz"
CONTENT_DIR="$QUARTZ_DIR/content"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}Darshi Documentation Sync${NC}"
echo "=============================="

# Function to sync docs
sync_docs() {
    echo -e "\n${YELLOW}Syncing /docs to /docs-quartz/content...${NC}"
    rm -rf "$CONTENT_DIR"/*
    cp -r "$DOCS_DIR"/* "$CONTENT_DIR"/
    echo -e "${GREEN}✓ Documentation synced${NC}"
}

# Function to build
build_docs() {
    echo -e "\n${YELLOW}Building Quartz site...${NC}"
    cd "$QUARTZ_DIR"
    npx quartz build
    echo -e "${GREEN}✓ Build complete${NC}"
    echo -e "\nOutput: ${QUARTZ_DIR}/public"
}

# Function to serve
serve_docs() {
    echo -e "\n${YELLOW}Starting local server...${NC}"
    cd "$QUARTZ_DIR"
    echo -e "${GREEN}✓ Server starting at http://localhost:8080${NC}"
    echo -e "${BLUE}Press Ctrl+C to stop${NC}\n"
    npx quartz build --serve
}

# Function to deploy
deploy_docs() {
    echo -e "\n${YELLOW}Committing and pushing changes...${NC}"
    cd "$SCRIPT_DIR"
    git add docs/ docs-quartz/

    if git diff --staged --quiet; then
        echo -e "${YELLOW}No changes to commit${NC}"
    else
        echo -e "${BLUE}Enter commit message (or press Enter for default):${NC}"
        read -r commit_msg

        if [ -z "$commit_msg" ]; then
            commit_msg="docs: update documentation $(date +%Y-%m-%d)"
        fi

        git commit -m "$commit_msg"
        git push origin main
        echo -e "${GREEN}✓ Changes pushed - GitHub Actions will deploy automatically${NC}"
        echo -e "${BLUE}Monitor deployment: https://github.com/YOUR_USERNAME/darshi/actions${NC}"
    fi
}

# Parse command
case "${1:-serve}" in
    build)
        sync_docs
        build_docs
        ;;
    serve)
        sync_docs
        serve_docs
        ;;
    deploy)
        sync_docs
        build_docs
        deploy_docs
        ;;
    sync)
        sync_docs
        ;;
    *)
        echo "Usage: $0 [sync|build|serve|deploy]"
        echo ""
        echo "Commands:"
        echo "  sync   - Sync /docs to /docs-quartz/content"
        echo "  build  - Sync + build Quartz site"
        echo "  serve  - Sync + build + serve locally (default)"
        echo "  deploy - Sync + build + commit + push to trigger deployment"
        exit 1
        ;;
esac
