# 📖 NovelAgent

**Multi-agent novel writing framework powered by LLMs.**

Four specialized agents — **World**, **Plot**, **Character**, **Writing** — collaborate via an async event bus to generate coherent, long-form fiction chapter by chapter.

---

## ✨ Features

- 🤖 **Multi-Agent Pipeline** — world-building, plot planning, character voice, prose composition
- 🔌 **Multi-Provider** — OpenAI, Ollama (local models), extensible to other providers
- 🧠 **Persistent Memory** — vector (ChromaDB) + structured (JSON) across chapters
- ⚡ **Parallel Generation** — concurrent chapters and character reactions
- 🔄 **Review Loop** — automated consistency and quality checks
- 🌍 **Multi-Language** — English, Chinese, and more
- 🔑 **Secure API Keys** — runtime injection via CLI flag or prompt, never stored in files

---

## 📋 Table of Contents

1. [Installation](#-installation)
2. [Quick Start](#-quick-start)
3. [Configuration](#-configuration)
4. [CLI Reference](#-cli-reference)
5. [Examples](#-examples)
6. [Project Structure](#-project-structure)
7. [Development](#-development)

---

## 🚀 Installation

```bash
git clone https://github.com/Skylanding/NovelAgent.git
cd NovelAgent
pip install -e .
```

**Set up API keys** (pick one):

```bash
# Option A: environment variable
export OPENAI_API_KEY="sk-your-key-here"

# Option B: pass at runtime
storyforge generate examples/fantasy_novel --api-key "sk-your-key"

# Option C: interactive prompt (key is hidden)
storyforge generate examples/fantasy_novel
# > Enter API key for openai: ****
```

> The `.env` file is gitignored. Keys are never written to tracked files.

---

## ⚡ Quick Start

```bash
# Generate a single chapter
storyforge generate examples/fantasy_novel -c 1 -k "sk-your-key"

# Generate chapters 1-5 with 3 in parallel
storyforge generate examples/fantasy_novel --from-chapter 1 --to-chapter 5 -p 3

# Validate project setup & LLM connectivity
storyforge validate examples/fantasy_novel

# Check progress
storyforge status examples/fantasy_novel
```

---

## 🏗️ Architecture

```
Pipeline Stages
─────────────────────────────────────────────
1. 📋 Planning        → PlotAgent outlines scenes
2. 🌍 World + 👥 Characters  → validate setting & react (parallel)
3. ✍️  Composition     → WritingAgent composes prose
4. 📎 Assembly        → concatenate scenes
5. 🔍 Review          → consistency & quality checks → revise
6. 💾 Finalize        → save, version, update memories
```

| Agent | Role | Memory |
|-------|------|--------|
| 🌍 WorldAgent | Lore, setting, consistency | Structured JSON |
| 📋 PlotAgent | Chapter plans, pacing, arcs | Structured JSON |
| ✍️ WritingAgent | Prose composition | Structured JSON |
| 👤 CharacterAgent | Voice, emotions, dialogue (one per character) | Vector (ChromaDB) |

---

## ⚙️ Configuration

Each project is a directory with a `project.yaml`:

```yaml
project:
  name: "The Shattered Crown"
  genre: "Epic Fantasy"
  language: "English"
  target_word_count: 50000
  target_chapters: 12

llm_backends:
  main:
    provider: "openai"              # "openai" | "ollama"
    model: "gpt-4o-mini"
    api_key_env: "OPENAI_API_KEY"
    max_tokens: 8192

agents:
  world:
    llm_backend: "main"
  plot:
    llm_backend: "main"
  writing:
    llm_backend: "main"
  characters:
    - name: "Kael"
      llm_backend: "main"
      character_sheet: "characters/kael.yaml"
      memory_type: "vector"

pipeline:
  max_revision_rounds: 3            # 0 to disable
  parallel_character_reactions: true

output:
  directory: "output/"
  formats: ["markdown"]
  versioning: true
```

---

## 🖥️ CLI Reference

| Command | Description |
|---------|-------------|
| `storyforge generate <dir>` | Generate chapters |
| `storyforge validate <dir>` | Check config & LLM connectivity |
| `storyforge status <dir>` | Show progress |
| `storyforge export <dir> -f html\|markdown` | Export chapters |
| `storyforge init fantasy\|mystery\|scifi <dir>` | Scaffold new project |

### `generate` options

| Flag | Short | Description |
|------|-------|-------------|
| `--chapter N` | `-c` | Single chapter |
| `--from-chapter N` | | Start chapter (default: 1) |
| `--to-chapter N` | | End chapter (inclusive) |
| `--parallel N` | `-p` | Concurrent chapters |
| `--api-key KEY` | `-k` | Runtime API key |
| `--verbose` | `-v` | Detailed logging |

---

## 📚 Examples

### 🏰 Fantasy — *The Shattered Crown*

```bash
storyforge generate examples/fantasy_novel -c 1
```

5 characters, English, 3 chapters.

### ⚔️ Xuanhuan — *逆天炼魂*

```bash
storyforge generate examples/xuanhuan_novel -c 1
```

5 characters, Chinese, 30 chapters.

---

## 📁 Project Structure

```
NovelAgent/
├── storyforge/              # Core framework
│   ├── cli.py               # CLI entry point
│   ├── config.py            # Config & validation
│   ├── agents/              # World, Plot, Writing, Character agents
│   ├── llm/                 # OpenAI, Ollama backends + factory
│   ├── memory/              # Vector (ChromaDB) & structured memory
│   ├── events/              # Async event bus
│   ├── pipeline/            # Chapter generation orchestrator
│   └── output/              # Export & versioning
├── prompts/                 # Jinja2 prompt templates
├── examples/                # Example projects
├── tests/                   # Test suite (58 tests)
├── pyproject.toml
└── .env.example
```

---

## 🛠️ Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

Create a new project:

```bash
storyforge init fantasy my_novel
# Edit project.yaml, characters/*.yaml, world.yaml, plot_outline.yaml
storyforge generate my_novel -c 1
```
