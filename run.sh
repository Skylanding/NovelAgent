#!/usr/bin/env bash
# StoryForge — Run Script
# Convenience wrapper for common storyforge commands.
#
# Usage:
#   ./run.sh generate <project_dir> [options]
#   ./run.sh visualize <project_dir> [options]
#   ./run.sh validate <project_dir> [options]
#   ./run.sh status <project_dir>
#   ./run.sh export <project_dir> [options]
#   ./run.sh test
#   ./run.sh help

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Load .env if it exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

COMMAND="${1:-help}"
shift 2>/dev/null || true

case "$COMMAND" in
    generate)
        echo ">>> StoryForge Generate"
        storyforge generate "$@"
        ;;
    visualize|visual)
        echo ">>> StoryForge Visualize"
        storyforge visualize "$@"
        ;;
    validate|check)
        echo ">>> StoryForge Validate"
        storyforge validate "$@"
        ;;
    status)
        echo ">>> StoryForge Status"
        storyforge status "$@"
        ;;
    export)
        echo ">>> StoryForge Export"
        storyforge export "$@"
        ;;
    init)
        echo ">>> StoryForge Init"
        storyforge init "$@"
        ;;
    test|tests)
        echo ">>> Running Tests"
        python -m pytest tests/ -v "$@"
        ;;
    help|--help|-h)
        echo "StoryForge Run Script"
        echo ""
        echo "Usage: ./run.sh <command> [options]"
        echo ""
        echo "Commands:"
        echo "  generate <project_dir> [opts]   Generate novel chapters"
        echo "    -c N                           Generate specific chapter"
        echo "    --from-chapter N --to-chapter N Chapter range"
        echo "    -p N                           Parallel chapters"
        echo "    -k KEY                         API key"
        echo "    -v                             Verbose"
        echo ""
        echo "  visualize <project_dir> [opts]  Generate images/videos"
        echo "    -t TEXT                        Input text"
        echo "    --text-file PATH               Input text file"
        echo "    -i IMAGE                       Input image(s)"
        echo "    --no-image                     Skip image generation"
        echo "    --no-video                     Skip video generation"
        echo "    -k KEY                         API key"
        echo ""
        echo "  validate <project_dir> [-k KEY] Check project config"
        echo "  status <project_dir>            Show project progress"
        echo "  export <project_dir> [-f FMT]   Export to markdown/html"
        echo "  init <template> <dir>           Create new project"
        echo "  test                            Run test suite"
        echo ""
        echo "Environment:"
        echo "  API keys can be set in .env or passed with -k flag"
        echo "  OPENAI_API_KEY     OpenAI backends"
        echo "  ANTHROPIC_API_KEY  Anthropic backends"
        echo ""
        echo "Examples:"
        echo "  ./run.sh generate examples/fantasy_novel -c 1 -k sk-..."
        echo "  ./run.sh visualize examples/fantasy_novel -t 'A dark forest' -k sk-..."
        echo "  ./run.sh test"
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Run './run.sh help' for usage"
        exit 1
        ;;
esac
