<p align="center">
  <h1 align="center">📖 NovelAgent / StoryForge</h1>
  <p align="center">
    <strong>Multi-agent creative writing framework powered by LLMs</strong>
  </p>
  <p align="center">
    <a href="#-quick-start">Quick Start</a> •
    <a href="#-architecture">Architecture</a> •
    <a href="#-configuration">Configuration</a> •
    <a href="#-cli-reference">CLI Reference</a> •
    <a href="#-examples">Examples</a>
  </p>
</p>

---

StoryForge is an AI-powered multi-agent system that automatically generates novel chapters. It breaks creative writing into specialized agent roles — **World**, **Plot**, **Character**, and **Writing** — that collaborate through an async event bus to produce coherent, long-form fiction.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🤖 **Multi-Agent Pipeline** | Specialized agents for world-building, plot planning, character voice, and prose composition |
| 🔌 **Multi-Provider LLM** | Swap between **OpenAI**, **Anthropic Claude**, and **Ollama** (local) per agent |
| 🧠 **Persistent Memory** | Vector (ChromaDB) + structured (JSON) memory that persists across chapters |
| ⚡ **Parallel Generation** | Generate multiple chapters and character reactions concurrently |
| 🔄 **Review Loop** | Automated consistency and quality checks with revision rounds |
| 🌍 **Multi-Language** | Full support for non-English novels (Chinese xuanhuan example included) |
| 🔑 **Secure API Keys** | Runtime key injection via CLI flag or interactive prompt — never stored in files |
| 📝 **Version History** | Every chapter version is tracked with metadata snapshots |

---

## 📋 Table of Contents

1. [Prerequisites](#-prerequisites)
2. [Installation](#-installation)
3. [Quick Start](#-quick-start)
4. [Architecture](#-architecture)
5. [Configuration](#-configuration)
6. [CLI Reference](#-cli-reference)
7. [Examples](#-examples)
8. [Project Structure](#-project-structure)
9. [Development](#-development)
10. [License](#-license)

---

## 📦 Prerequisites

- **Python** >= 3.9
- **API Key** for at least one LLM provider:
  - [OpenAI API Key](https://platform.openai.com/api-keys) — for GPT-4o / GPT-4o-mini
  - [Anthropic API Key](https://console.anthropic.com/) — for Claude models
  - [Ollama](https://ollama.com/) — for free local models (no API key needed)

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/Skylanding/NovelAgent.git
cd NovelAgent
```

### 2. Install the package

```bash
# Basic installation
pip install -e .

# With development tools (pytest, coverage)
pip install -e ".[dev]"

# With export support
pip install -e ".[epub,pdf]"
```

### 3. Set up API keys (choose one method)

**Option A — Environment variable (recommended for local development):**

```bash
cp .env.example .env
# Edit .env and fill in your API key(s)
export OPENAI_API_KEY="sk-your-key-here"
```

**Option B — Pass at runtime (recommended for shared environments):**

```bash
# Via CLI flag
storyforge generate examples/fantasy_novel --api-key "sk-your-key-here"

# Or let it prompt you interactively (key is hidden)
storyforge generate examples/fantasy_novel
# > Enter API key for openai (or set OPENAI_API_KEY): ****
```

> ⚠️ **Security Note:** API keys are never written to any tracked file. The `.env` file is in `.gitignore`.

---

## ⚡ Quick Start

### Generate your first chapter

```bash
# Generate chapter 1 of the fantasy example
storyforge generate examples/fantasy_novel --chapter 1 --api-key "sk-your-key"

# Generate all chapters sequentially
storyforge generate examples/fantasy_novel

# Generate chapters 1-5 with 3 running in parallel
storyforge generate examples/fantasy_novel --from-chapter 1 --to-chapter 5 --parallel 3
```

### Validate your project setup

```bash
storyforge validate examples/fantasy_novel --api-key "sk-your-key"
```

This checks configuration, LLM connectivity, and character sheet files.

### Check project progress

```bash
storyforge status examples/fantasy_novel
```

---

## 🏗️ Architecture

StoryForge uses a multi-agent pipeline where each agent specializes in one aspect of storytelling:

```
┌─────────────────────────────────────────────────────────┐
│                    Chapter Pipeline                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Stage 1: 📋 Planning                                  │
│  └─ PlotAgent creates chapter outline & scene plans     │
│                                                         │
│  Stage 2: 🌍 World Validation  +  👥 Character React   │
│  └─ WorldAgent enriches setting │ CharacterAgents react │
│     (runs in parallel)          │ with emotions/skills  │
│                                                         │
│  Stage 3: ✍️  Composition                               │
│  └─ WritingAgent composes scenes with dialogue          │
│                                                         │
│  Stage 4: 📎 Assembly                                   │
│  └─ Scenes concatenated into full chapter               │
│                                                         │
│  Stage 5: 🔍 Review Loop (configurable rounds)          │
│  └─ WorldAgent checks consistency                       │
│  └─ PlotAgent checks quality                            │
│  └─ WritingAgent revises if issues found                │
│                                                         │
│  Stage 6: 💾 Finalization                               │
│  └─ Save chapter, update memories, version snapshot     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Agent Roles

| Agent | Role | Memory Type |
|-------|------|-------------|
| 🌍 **WorldAgent** | Maintains lore, setting consistency, world rules | Structured JSON |
| 📋 **PlotAgent** | Plans chapters, scenes, pacing, plot arcs | Structured JSON |
| ✍️ **WritingAgent** | Composes polished prose from structured inputs | Structured JSON |
| 👤 **CharacterAgent** | Per-character voice, emotions, dialogue, relationships | Vector (ChromaDB) |

### Communication

Agents communicate via an **async event bus** with request-response patterns, correlation IDs, and configurable timeouts. An event logging middleware tracks all inter-agent messages.

---

## ⚙️ Configuration

Each project is defined by a `project.yaml` file. Here's the structure:

### Project Metadata

```yaml
project:
  name: "The Shattered Crown"
  author: "Your Name"
  genre: "Epic Fantasy"
  language: "English"           # or "Chinese (中文)" etc.
  target_word_count: 50000
  target_chapters: 12
```

### LLM Backends

Define one or more backends and assign them to agents:

```yaml
llm_backends:
  openai_main:
    provider: "openai"          # "openai" | "anthropic" | "ollama"
    model: "gpt-4o-mini"        # model identifier
    tier: "medium"              # "small" | "medium" | "large"
    api_key_env: "OPENAI_API_KEY"
    max_tokens: 8192
    context_window: 128000
    requests_per_minute: 500
    default_temperature: 0.7

  local_llama:
    provider: "ollama"
    model: "llama3.1:8b"
    tier: "small"
    base_url: "http://localhost:11434"   # optional
    max_tokens: 4096
    context_window: 8192
```

### Agent Assignments

```yaml
agents:
  world:
    llm_backend: "openai_main"
    system_prompt: "world/system.jinja2"

  plot:
    llm_backend: "openai_main"
    system_prompt: "plot/system.jinja2"

  writing:
    llm_backend: "openai_main"
    system_prompt: "writing/system.jinja2"

  characters:
    - name: "Kael"
      llm_backend: "local_llama"        # each character can use a different backend
      character_sheet: "characters/kael.yaml"
      memory_type: "vector"             # "vector" (ChromaDB) or "structured" (JSON)
```

### Pipeline & Output

```yaml
pipeline:
  max_revision_rounds: 3        # 0 to disable review loop
  parallel_character_reactions: true

output:
  directory: "output/"
  formats: ["markdown"]
  versioning: true
  save_intermediates: true      # save outlines, drafts, reviews
```

---

## 🖥️ CLI Reference

```
storyforge [command] [options]
```

### `generate` — Generate chapters

```bash
storyforge generate <project_dir> [options]
```

| Option | Short | Description |
|--------|-------|-------------|
| `--chapter N` | `-c N` | Generate a single specific chapter |
| `--from-chapter N` | | Start from chapter N (default: 1) |
| `--to-chapter N` | | End at chapter N (inclusive) |
| `--parallel N` | `-p N` | Generate N chapters concurrently |
| `--api-key KEY` | `-k KEY` | Provide API key at runtime |
| `--verbose` | `-v` | Enable detailed logging |

**Examples:**

```bash
# Single chapter
storyforge generate my_novel -c 5

# Range with parallelism
storyforge generate my_novel --from-chapter 1 --to-chapter 10 -p 3

# With runtime API key
storyforge generate my_novel -k "sk-..."
```

### `validate` — Check project setup

```bash
storyforge validate <project_dir> [-k KEY] [-v]
```

Verifies config syntax, LLM backend connectivity, and character sheet files.

### `status` — View progress

```bash
storyforge status <project_dir>
```

Displays a table with chapters generated, word count, and progress percentage.

### `export` — Export to book format

```bash
storyforge export <project_dir> --format markdown|html
```

### `init` — Create new project from template

```bash
storyforge init fantasy|mystery|scifi <output_dir>
```

---

## 📚 Examples

Two complete example projects are included:

### 🏰 Fantasy Novel — *The Shattered Crown*

```bash
storyforge generate examples/fantasy_novel --chapter 1
```

- 5 characters (Kael, Sera, Theron, Mira, Voss)
- Epic fantasy genre, English language
- 3 target chapters, 5,000 words

### ⚔️ Xuanhuan Novel — *逆天炼魂 (Against Heaven: Soul Refining)*

```bash
storyforge generate examples/xuanhuan_novel --chapter 1
```

- 5 characters (林焱, 萧冰凝, 药尘, 韩枫, 云岚)
- Chinese xuanhuan fantasy genre
- 30 target chapters, 100,000 words
- Demonstrates full multi-language support

---

## 📁 Project Structure

```
NovelAgent/
├── storyforge/                  # 🔧 Core framework
│   ├── cli.py                   #    CLI entry point
│   ├── config.py                #    Configuration & validation
│   ├── agents/                  #    Agent implementations
│   │   ├── base.py              #      Abstract base agent
│   │   ├── world.py             #      🌍 WorldAgent
│   │   ├── plot.py              #      📋 PlotAgent
│   │   ├── writing.py           #      ✍️  WritingAgent
│   │   ├── character.py         #      👤 CharacterAgent (legacy)
│   │   └── character/           #      👤 Enhanced character system
│   │       ├── agent.py         #        Agent with type awareness
│   │       ├── sheet.py         #        Character sheet model
│   │       ├── emotional_state.py #      Emotion state machine
│   │       ├── relationships.py #        Relationship tracking
│   │       ├── skills.py        #        Skill system & triggers
│   │       ├── constraints.py   #        Behavior constraints
│   │       └── types.py         #        Character archetypes
│   ├── llm/                     #    LLM provider backends
│   │   ├── anthropic.py         #      Anthropic Claude
│   │   ├── openai.py            #      OpenAI GPT
│   │   ├── ollama.py            #      Ollama (local)
│   │   ├── factory.py           #      Backend factory
│   │   └── rate_limiter.py      #      Token bucket rate limiter
│   ├── memory/                  #    Memory systems
│   │   ├── vector.py            #      ChromaDB vector search
│   │   ├── structured.py        #      JSON key-value store
│   │   ├── summary.py           #      LLM-based summarization
│   │   └── context_window.py    #      Token budget management
│   ├── events/                  #    Event-driven communication
│   │   ├── bus.py               #      Async event bus
│   │   ├── types.py             #      Event type definitions
│   │   └── middleware.py        #      Logging middleware
│   ├── pipeline/                #    Chapter generation pipeline
│   │   ├── chapter.py           #      Pipeline orchestrator
│   │   └── stages.py            #      Stage definitions
│   └── output/                  #    Output & export
│       ├── manager.py           #      Versioned file management
│       └── formats.py           #      Markdown/HTML export
├── prompts/                     # 📝 Jinja2 prompt templates
│   ├── character/               #    Per-archetype prompts
│   ├── plot/                    #    Plot planning prompts
│   ├── world/                   #    World-building prompts
│   └── writing/                 #    Composition prompts
├── examples/                    # 📚 Example projects
│   ├── fantasy_novel/           #    English fantasy example
│   └── xuanhuan_novel/          #    Chinese xuanhuan example
├── tests/                       # 🧪 Test suite (58 tests)
├── pyproject.toml               # 📦 Package config
├── .env.example                 # 🔑 API key template
└── .gitignore
```

---

## 🛠️ Development

### Run tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

### Create a new project

```bash
storyforge init fantasy my_new_novel
cd my_new_novel
# Edit project.yaml, characters/*.yaml, world.yaml, plot_outline.yaml
storyforge generate . --chapter 1
```

### Add a custom LLM provider

```python
from storyforge.llm.base import LLMBackend, LLMConfig
from storyforge.llm.factory import LLMFactory

class MyCustomBackend(LLMBackend):
    async def generate(self, messages, **kwargs):
        # Your implementation
        ...

LLMFactory.register_provider("my_provider", MyCustomBackend)
```

### Character sheet format

Character sheets are YAML files placed in the project's `characters/` directory:

```yaml
name: "Kael"
role: "protagonist"
age: 22
personality: "Determined, loyal, struggles with self-doubt"
background: "Former apprentice blacksmith who discovered latent magical abilities"
goals:
  - "Master the ancient forge-magic"
  - "Protect his hometown from the Shadow Court"
skills:
  - name: "Forge Magic"
    proficiency_level: 3
    scene_triggers: ["combat", "crafting"]
relationships:
  - target_character: "Sera"
    relationship_type: "ally"
    trust_level: 7
```

---

## 📄 License

This project is open source. See the repository for license details.

---

<p align="center">
  Built with 🤖 multi-agent collaboration
</p>
