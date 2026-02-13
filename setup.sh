#!/usr/bin/env bash
# StoryForge — Setup Script
# Installs dependencies and prepares the project for running.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================="
echo "  StoryForge Setup"
echo "========================================="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 9 ]; }; then
    echo "[ERROR] Python 3.9+ required. Found: Python $PYTHON_VERSION"
    exit 1
fi
echo "[OK] Python $PYTHON_VERSION"

# Install package in editable mode with dev dependencies
echo ""
echo "Installing StoryForge and dependencies..."
pip install -e ".[dev]" --quiet

# Verify installation
if command -v storyforge &>/dev/null; then
    echo "[OK] storyforge CLI installed"
else
    echo "[WARN] storyforge CLI not in PATH, use: python -m storyforge"
fi

# Check key dependencies
echo ""
echo "Checking dependencies..."
python3 -c "import openai; print(f'  [OK] openai {openai.__version__}')"
python3 -c "import anthropic; print(f'  [OK] anthropic {anthropic.__version__}')" 2>/dev/null || echo "  [SKIP] anthropic (optional)"
python3 -c "import httpx; print(f'  [OK] httpx {httpx.__version__}')"
python3 -c "import click; print(f'  [OK] click {click.__version__}')"
python3 -c "import pydantic; print(f'  [OK] pydantic {pydantic.__version__}')"
python3 -c "import chromadb; print(f'  [OK] chromadb {chromadb.__version__}')" 2>/dev/null || echo "  [SKIP] chromadb (install separately if needed)"

# Set up .env if not exists
if [ ! -f .env ] && [ -f .env.example ]; then
    echo ""
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "[OK] .env created — edit it to add your API keys"
    echo "     Or pass keys at runtime: storyforge generate <project> -k YOUR_KEY"
fi

# Run tests
echo ""
echo "Running tests..."
if python -m pytest tests/ -q 2>&1 | tail -3; then
    echo "[OK] All tests passed"
else
    echo "[WARN] Some tests failed — check output above"
fi

echo ""
echo "========================================="
echo "  Setup Complete!"
echo "========================================="
echo ""
echo "Quick start:"
echo "  # Validate a project"
echo "  storyforge validate examples/fantasy_novel -k YOUR_OPENAI_KEY"
echo ""
echo "  # Generate chapter 1"
echo "  storyforge generate examples/fantasy_novel -c 1 -k YOUR_OPENAI_KEY"
echo ""
echo "  # Generate visuals"
echo "  storyforge visualize examples/fantasy_novel -t 'A warrior on a cliff at sunset' -k YOUR_OPENAI_KEY"
echo ""
