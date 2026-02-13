"""CLI interface for StoryForge."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from storyforge.utils.logging import setup_logging

console = Console()


def _run_async(coro):
    """Run an async function from sync CLI."""
    return asyncio.run(coro)


def _inject_api_keys(config, api_keys: dict[str, str]) -> None:
    """Inject runtime API keys into backend configs (never written to disk).

    ``api_keys`` maps provider names (e.g. "openai", "anthropic") to key
    strings.  Keys supplied here override env-var resolution so the user
    can pass them on the command line or via an interactive prompt.
    """
    for _name, backend_cfg in config.llm_backends.items():
        key = api_keys.get(backend_cfg.provider)
        if key:
            backend_cfg.api_key = key
    # Also inject into visual backends
    for _name, vb_cfg in config.visual_backends.items():
        key = api_keys.get(vb_cfg.provider)
        if key:
            vb_cfg.api_key = key


def _resolve_api_keys_for_config(config, cli_api_key: str | None) -> None:
    """Ensure every backend that needs an API key has one.

    Resolution order:
      1. Explicit ``--api-key`` CLI flag  (applied to all backends)
      2. Environment variable referenced by ``api_key_env``
      3. Interactive prompt (only for providers still missing a key)
    """
    # Collect which providers still need a key
    providers_needing_key: dict[str, str] = {}  # provider -> env var name
    for _name, backend_cfg in config.llm_backends.items():
        if backend_cfg.api_key:
            continue  # already resolved (env var or explicit)
        if backend_cfg.provider == "ollama":
            continue  # local models don't need API keys
        providers_needing_key.setdefault(
            backend_cfg.provider, backend_cfg.api_key_env or ""
        )
    # Also check visual backends
    for _name, vb_cfg in config.visual_backends.items():
        if vb_cfg.api_key:
            continue
        providers_needing_key.setdefault(
            vb_cfg.provider, vb_cfg.api_key_env or ""
        )

    if not providers_needing_key:
        return  # all keys already available

    if cli_api_key:
        # Apply the single CLI key to all providers that need one
        for provider in providers_needing_key:
            _inject_api_keys(config, {provider: cli_api_key})
        return

    # Interactive prompt for each provider still missing a key
    for provider, env_var in providers_needing_key.items():
        hint = f" (or set {env_var})" if env_var else ""
        key = click.prompt(
            f"Enter API key for {provider}{hint}",
            hide_input=True,
        )
        _inject_api_keys(config, {provider: key})


@click.group()
@click.version_option(version="0.1.0")
def main():
    """StoryForge — Multi-agent creative writing framework."""
    pass


@main.command()
@click.argument("project_dir", type=click.Path(exists=True))
@click.option("--chapter", "-c", type=int, help="Generate a specific chapter")
@click.option("--from-chapter", "from_ch", type=int, default=1, help="Start chapter")
@click.option("--to-chapter", "to_ch", type=int, help="End chapter (inclusive)")
@click.option("--parallel", "-p", type=int, default=1, help="Parallel chapter count (e.g. -p 3)")
@click.option("--api-key", "-k", type=str, default=None, help="LLM API key (avoids storing in files)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose logging")
def generate(
    project_dir: str,
    chapter: Optional[int],
    from_ch: int,
    to_ch: Optional[int],
    parallel: int,
    api_key: Optional[str],
    verbose: bool,
):
    """Generate novel chapters from a story project."""
    setup_logging(verbose)
    project_path = Path(project_dir)

    async def _generate():
        from storyforge.config import load_config

        config = load_config(project_path)
        _resolve_api_keys_for_config(config, api_key)
        console.print(
            f"[bold]StoryForge[/bold] — Generating "
            f"[cyan]{config.project.name}[/cyan]"
        )

        # Build the runtime
        runtime = await _build_runtime(project_path, config)
        pipeline = runtime["pipeline"]

        if chapter is not None:
            chapters_to_gen = [chapter]
        else:
            end = to_ch or config.project.target_chapters
            chapters_to_gen = list(range(from_ch, end + 1))

        if parallel <= 1:
            # Sequential mode
            for ch_num in chapters_to_gen:
                console.print(f"\n[bold yellow]>>> Chapter {ch_num}[/bold yellow]")
                result = await pipeline.generate_chapter(ch_num)
                word_count = len(result.split())
                console.print(
                    f"[green]✓ Chapter {ch_num} complete[/green] "
                    f"({word_count} words)"
                )
        else:
            # Parallel batch mode
            console.print(
                f"\n[bold cyan]Parallel mode:[/bold cyan] {parallel} chapters at a time"
            )
            for batch_start in range(0, len(chapters_to_gen), parallel):
                batch = chapters_to_gen[batch_start:batch_start + parallel]
                console.print(
                    f"\n[bold yellow]>>> Batch: Chapters "
                    f"{batch[0]}-{batch[-1]}[/bold yellow]"
                )

                async def _gen_one(ch_num):
                    result = await pipeline.generate_chapter(ch_num)
                    word_count = len(result.split())
                    console.print(
                        f"[green]✓ Chapter {ch_num} complete[/green] "
                        f"({word_count} words)"
                    )
                    return result

                await asyncio.gather(*[_gen_one(ch) for ch in batch])

        console.print(
            f"\n[bold green]Done![/bold green] "
            f"Output: {config.output.directory}"
        )

    _run_async(_generate())


@main.command()
@click.argument("project_dir", type=click.Path(exists=True))
@click.option("--api-key", "-k", type=str, default=None, help="LLM API key (avoids storing in files)")
@click.option("--verbose", "-v", is_flag=True)
def validate(project_dir: str, api_key: Optional[str], verbose: bool):
    """Validate project configuration and check LLM connectivity."""
    setup_logging(verbose)
    project_path = Path(project_dir)

    async def _validate():
        from storyforge.config import load_config
        from storyforge.llm.factory import LLMFactory

        try:
            config = load_config(project_path)
            _resolve_api_keys_for_config(config, api_key)
            console.print("[green]✓[/green] Configuration loaded successfully")
            console.print(f"  Project: {config.project.name}")
            console.print(f"  Genre: {config.project.genre}")
            console.print(
                f"  Target: {config.project.target_chapters} chapters, "
                f"{config.project.target_word_count} words"
            )
        except Exception as e:
            console.print(f"[red]✗ Configuration error:[/red] {e}")
            return

        # Check LLM backends
        console.print("\n[bold]LLM Backends:[/bold]")
        for name, backend_config in config.llm_backends.items():
            try:
                backend = LLMFactory.create_from_dict(
                    backend_config.model_dump()
                )
                healthy = await backend.health_check()
                status = "[green]✓[/green]" if healthy else "[red]✗[/red]"
                console.print(
                    f"  {status} {name}: {backend_config.provider}/"
                    f"{backend_config.model} ({backend_config.tier})"
                )
            except Exception as e:
                console.print(f"  [red]✗[/red] {name}: {e}")

        # Check character sheets
        console.print("\n[bold]Characters:[/bold]")
        for char_config in config.agents.characters:
            sheet_path = project_path / char_config.character_sheet
            if sheet_path.exists():
                console.print(
                    f"  [green]✓[/green] {char_config.name} ({sheet_path})"
                )
            else:
                console.print(
                    f"  [red]✗[/red] {char_config.name} — "
                    f"missing: {sheet_path}"
                )

    _run_async(_validate())


@main.command("export")
@click.argument("project_dir", type=click.Path(exists=True))
@click.option(
    "--format",
    "-f",
    "fmt",
    type=click.Choice(["markdown", "html"]),
    default="markdown",
)
def export_cmd(project_dir: str, fmt: str):
    """Export generated chapters to a book format."""
    project_path = Path(project_dir)

    async def _export():
        from storyforge.config import load_config
        from storyforge.output.formats import HtmlFormatter, MarkdownFormatter

        config = load_config(project_path)
        output_dir = project_path / config.output.directory
        chapters_dir = output_dir / "chapters"
        exports_dir = output_dir / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            "title": config.project.name,
            "author": config.project.author,
        }

        slug = config.project.name.lower().replace(" ", "_")
        if fmt == "markdown":
            formatter = MarkdownFormatter()
            out_path = exports_dir / f"{slug}.md"
        else:
            formatter = HtmlFormatter()
            out_path = exports_dir / f"{slug}.html"

        result = await formatter.export(chapters_dir, metadata, out_path)
        console.print(f"[green]✓[/green] Exported to: {result}")

    _run_async(_export())


@main.command()
@click.argument("project_dir", type=click.Path(exists=True))
def status(project_dir: str):
    """Show project status — chapters generated, word count, progress."""
    project_path = Path(project_dir)

    from storyforge.config import load_config

    config = load_config(project_path)
    output_dir = project_path / config.output.directory

    from storyforge.output.manager import OutputManager

    mgr = OutputManager(output_dir)

    table = Table(title=f"StoryForge — {config.project.name}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    chapter_count = mgr.get_chapter_count()
    word_count = mgr.get_total_word_count()

    table.add_row("Chapters generated", str(chapter_count))
    table.add_row("Target chapters", str(config.project.target_chapters))
    table.add_row(
        "Progress",
        f"{chapter_count / max(config.project.target_chapters, 1) * 100:.0f}%",
    )
    table.add_row("Words written", f"{word_count:,}")
    table.add_row("Target words", f"{config.project.target_word_count:,}")
    table.add_row("Genre", config.project.genre)

    console.print(table)


@main.command()
@click.argument("template", type=click.Choice(["fantasy", "mystery", "scifi"]))
@click.argument("output_dir", type=click.Path())
def init(template: str, output_dir: str):
    """Initialize a new story project from a template."""
    out_path = Path(output_dir)
    if out_path.exists():
        console.print(f"[red]Directory already exists:[/red] {out_path}")
        return

    # Copy from examples
    examples_dir = Path(__file__).parent.parent / "examples"
    template_map = {
        "fantasy": "fantasy_novel",
        "mystery": "fantasy_novel",  # reuse as starting point
        "scifi": "fantasy_novel",
    }
    template_dir = examples_dir / template_map[template]

    if template_dir.exists():
        shutil.copytree(template_dir, out_path)
        console.print(
            f"[green]✓[/green] Initialized {template} project at {out_path}"
        )
    else:
        # Create minimal structure
        out_path.mkdir(parents=True)
        (out_path / "characters").mkdir()
        (out_path / "output").mkdir()
        console.print(
            f"[green]✓[/green] Created project directory at {out_path}"
        )
        console.print(
            "  Edit project.yaml to configure your story"
        )


@main.command()
@click.argument("project_dir", type=click.Path(exists=True))
@click.option("-t", "--text", "text_input", type=str, default="", help="Input text to visualize")
@click.option("--text-file", type=click.Path(exists=True), help="Read input text from file")
@click.option("-i", "--image", "image_paths", multiple=True, type=click.Path(exists=True), help="Input image(s)")
@click.option("--image-url", "image_urls", multiple=True, type=str, help="Input image URL(s)")
@click.option("--no-image", is_flag=True, help="Skip image generation")
@click.option("--no-video", is_flag=True, help="Skip video generation")
@click.option("--video-duration", type=click.Choice(["4", "8", "12"]), default="8", help="Sora video duration in seconds")
@click.option("--image-size", type=str, default=None, help="Image size (e.g. 1024x1024)")
@click.option("--video-size", type=str, default=None, help="Video size (e.g. 1280x720)")
@click.option("--api-key", "-k", type=str, default=None, help="OpenAI API key")
@click.option("--verbose", "-v", is_flag=True, help="Verbose logging")
def visualize(
    project_dir: str,
    text_input: str,
    text_file: Optional[str],
    image_paths: tuple[str, ...],
    image_urls: tuple[str, ...],
    no_image: bool,
    no_video: bool,
    video_duration: str,
    image_size: Optional[str],
    video_size: Optional[str],
    api_key: Optional[str],
    verbose: bool,
):
    """Generate images and videos from text/image input using the visual pipeline."""
    setup_logging(verbose)
    project_path = Path(project_dir)

    # Resolve text input
    text = text_input
    if text_file:
        text = Path(text_file).read_text(encoding="utf-8")
    if not text and not image_paths and not image_urls:
        console.print("[red]Error:[/red] Provide --text, --text-file, --image, or --image-url")
        return

    async def _visualize():
        from storyforge.config import load_config

        config = load_config(project_path)
        _resolve_api_keys_for_config(config, api_key)

        console.print(
            f"[bold]StoryForge Visual[/bold] — "
            f"[cyan]{config.project.name}[/cyan]"
        )

        # Apply CLI overrides before building runtime
        if no_image:
            config.visual_pipeline.generate_images = False
        if no_video:
            config.visual_pipeline.generate_videos = False

        runtime = await _build_visual_runtime(project_path, config)
        pipeline = runtime["pipeline"]

        console.print("\n[bold yellow]>>> Stage 1: Extract[/bold yellow]")
        console.print(f"  Text length: {len(text)} chars")
        if image_paths:
            console.print(f"  Images: {len(image_paths)} file(s)")
        if image_urls:
            console.print(f"  Image URLs: {len(image_urls)}")

        manifest = await pipeline.run(
            text=text,
            image_paths=list(image_paths),
            image_urls=list(image_urls),
            image_size=image_size,
            video_size=video_size,
            video_duration=int(video_duration),
        )

        # Report results
        results = manifest.get("visual_results", [])
        console.print(f"\n[bold green]Done![/bold green] Generated {len(results)} scene(s)")
        for r in results:
            idx = r.get("scene_index", "?")
            if r.get("image", {}).get("path"):
                console.print(f"  [green]✓[/green] Scene {idx} image: {r['image']['path']}")
            if r.get("video", {}).get("path"):
                console.print(f"  [green]✓[/green] Scene {idx} video: {r['video']['path']}")
            if r.get("error"):
                console.print(f"  [red]✗[/red] Scene {idx}: {r['error']}")

        output_dir = project_path / config.output.directory
        console.print(f"\nOutput: {output_dir}")

    _run_async(_visualize())


async def _build_visual_runtime(project_path: Path, config) -> dict:
    """Build the visual pipeline runtime from configuration."""
    from storyforge.agents.base import AgentConfig
    from storyforge.agents.expansion import ExpansionAgent
    from storyforge.agents.extract import ExtractAgent
    from storyforge.agents.visual_agent import VisualAgent
    from storyforge.events.bus import EventBus
    from storyforge.events.middleware import EventLogger
    from storyforge.events.types import EventType
    from storyforge.llm.factory import LLMFactory
    from storyforge.memory.structured import StructuredMemory
    from storyforge.pipeline.visual import VisualPipeline
    from storyforge.visual.factory import VisualFactory
    from storyforge.visual.output import VisualOutputManager

    # Event bus
    event_bus = EventBus()
    event_bus.add_middleware(EventLogger())

    # LLM backends
    backends = {}
    for name, backend_config in config.llm_backends.items():
        backends[name] = LLMFactory.create_from_dict(backend_config.model_dump())

    # Visual backends — auto-create defaults if not configured
    if not config.visual_backends:
        from storyforge.config import VisualBackendConfig

        # Inherit the OpenAI API key from any configured LLM backend
        openai_key = None
        for _name, llm_cfg in config.llm_backends.items():
            if llm_cfg.provider == "openai" and llm_cfg.api_key:
                openai_key = llm_cfg.api_key
                break

        config.visual_backends = {
            "dalle3": VisualBackendConfig(
                provider="openai_image",
                model="dall-e-3",
                api_key=openai_key,
                default_size="1024x1024",
                default_quality="hd",
            ),
            "sora2": VisualBackendConfig(
                provider="openai_video",
                model="sora-2",
                api_key=openai_key,
                default_size="1280x720",
            ),
        }

    visual_backends = {}
    for name, vb_config in config.visual_backends.items():
        visual_backends[name] = VisualFactory.create_from_dict(vb_config.model_dump())

    # Visual agents config (use defaults if not configured)
    va_config = config.visual_agents
    if va_config is None:
        from storyforge.config import VisualAgentsConfig
        va_config = VisualAgentsConfig()

    # Prompt templates: prefer project-level, fall back to package-level
    prompt_dir = project_path / "prompts"
    pkg_prompt_dir = Path(__file__).parent / "prompts"  # storyforge/prompts/
    if not prompt_dir.exists():
        prompt_dir = Path(__file__).parent.parent / "prompts"

    def _resolve_prompt_dir(subdir: str) -> Path | None:
        """Find a prompt subdirectory, checking project then package."""
        if (prompt_dir / subdir).exists():
            return prompt_dir / subdir
        if (pkg_prompt_dir / subdir).exists():
            return pkg_prompt_dir / subdir
        return None

    # Shared memory store for visual agents
    data_dir = project_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # ExtractAgent
    extract_backend_name = va_config.extract.get("llm_backend", next(iter(backends)))
    extract_backend = backends[extract_backend_name]
    extract_memory = StructuredMemory(storage_path=data_dir / "extract_memory.json")
    extract_prompt_dir = _resolve_prompt_dir("extract")
    extract_agent = ExtractAgent(
        config=AgentConfig(
            name="extract",
            role="extract",
            llm_backend_id=extract_backend_name,
            system_prompt_template="system.jinja2" if extract_prompt_dir else "",
            max_context_tokens=extract_backend.config.max_tokens,
            temperature=0.4,
            subscriptions=[EventType.VISUAL_EXTRACT_REQUEST],
        ),
        llm=extract_backend,
        memory=extract_memory,
        event_bus=event_bus,
        prompt_dir=extract_prompt_dir,
    )
    await extract_agent.initialize()

    # ExpansionAgent
    expand_backend_name = va_config.expansion.get("llm_backend", next(iter(backends)))
    expand_backend = backends[expand_backend_name]
    expand_memory = StructuredMemory(storage_path=data_dir / "expansion_memory.json")
    expand_prompt_dir = _resolve_prompt_dir("expansion")
    expansion_agent = ExpansionAgent(
        config=AgentConfig(
            name="expansion",
            role="expansion",
            llm_backend_id=expand_backend_name,
            system_prompt_template="system.jinja2" if expand_prompt_dir else "",
            max_context_tokens=expand_backend.config.max_tokens,
            temperature=0.7,
            subscriptions=[EventType.VISUAL_EXPAND_REQUEST],
        ),
        llm=expand_backend,
        memory=expand_memory,
        event_bus=event_bus,
        prompt_dir=expand_prompt_dir,
    )
    await expansion_agent.initialize()

    # VisualAgent
    vis_cfg = va_config.visual
    vis_backend_name = vis_cfg.get("llm_backend", next(iter(backends)))
    vis_backend = backends[vis_backend_name]
    vis_memory = StructuredMemory(storage_path=data_dir / "visual_memory.json")

    image_backend = visual_backends.get(vis_cfg.get("image_backend", ""))
    video_backend = visual_backends.get(vis_cfg.get("video_backend", ""))

    vis_prompt_dir = _resolve_prompt_dir("visual")
    visual_agent = VisualAgent(
        config=AgentConfig(
            name="visual",
            role="visual",
            llm_backend_id=vis_backend_name,
            system_prompt_template="system.jinja2" if vis_prompt_dir else "",
            max_context_tokens=vis_backend.config.max_tokens,
            temperature=0.5,
            subscriptions=[EventType.VISUAL_GENERATE_REQUEST],
        ),
        llm=vis_backend,
        memory=vis_memory,
        event_bus=event_bus,
        image_backend=image_backend,
        video_backend=video_backend,
        prompt_dir=vis_prompt_dir,
    )
    await visual_agent.initialize()

    # Output manager
    output_dir = project_path / config.output.directory
    output_mgr = VisualOutputManager(output_dir)
    await output_mgr.initialize()

    # Pipeline config
    vp_config = config.visual_pipeline

    pipeline = VisualPipeline(
        extract_agent=extract_agent,
        expansion_agent=expansion_agent,
        visual_agent=visual_agent,
        output_manager=output_mgr,
        generate_images=vp_config.generate_images,
        generate_videos=vp_config.generate_videos,
        video_duration=vp_config.video_duration,
        parallel_scenes=vp_config.parallel_scenes,
        image_size=vp_config.default_image_size,
        video_size=vp_config.default_video_size,
    )

    return {
        "event_bus": event_bus,
        "extract_agent": extract_agent,
        "expansion_agent": expansion_agent,
        "visual_agent": visual_agent,
        "pipeline": pipeline,
        "output_manager": output_mgr,
    }


def _sanitize_collection_name(name: str) -> str:
    """Sanitize a name for use as a ChromaDB collection name (ASCII only)."""
    import re
    import hashlib
    # Try transliterating to ASCII-safe slug
    safe = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
    safe = safe.strip('_') or hashlib.md5(name.encode()).hexdigest()[:16]
    # ChromaDB requires 3-512 chars, starting/ending with alphanumeric
    if len(safe) < 3:
        safe = safe + "_col"
    return safe


async def _build_runtime(project_path: Path, config) -> dict:
    """Build the full runtime from configuration."""
    from storyforge.agents.character import CharacterAgent, CharacterSheet
    from storyforge.agents.base import AgentConfig
    from storyforge.agents.plot import PlotAgent
    from storyforge.agents.world import WorldAgent
    from storyforge.agents.writing import WritingAgent
    from storyforge.config import load_yaml_file
    from storyforge.events.bus import EventBus
    from storyforge.events.middleware import EventLogger
    from storyforge.events.types import EventType
    from storyforge.llm.factory import LLMFactory
    from storyforge.memory.structured import StructuredMemory
    from storyforge.memory.summary import MemorySummarizer
    from storyforge.memory.vector import VectorMemory
    from storyforge.output.manager import OutputManager
    from storyforge.pipeline.chapter import ChapterPipeline

    # Create event bus
    event_bus = EventBus()
    event_bus.add_middleware(EventLogger())

    # Create LLM backends
    backends = {}
    for name, backend_config in config.llm_backends.items():
        backends[name] = LLMFactory.create_from_dict(
            backend_config.model_dump()
        )

    # Create output manager
    output_dir = project_path / config.output.directory
    output_mgr = OutputManager(
        output_dir,
        versioning=config.output.versioning,
        save_intermediates=config.output.save_intermediates,
    )
    await output_mgr.initialize()

    # Prompt templates: prefer project-level, fall back to package-level
    prompt_dir = project_path / "prompts"
    if not prompt_dir.exists():
        prompt_dir = Path(__file__).parent.parent / "prompts"

    # Language setting for all agents
    language = getattr(config.project, "language", "English")
    lang_vars = {"language": language} if language.lower() != "english" else {}

    # Create WorldAgent
    world_cfg = config.agents.world
    world_backend = backends[world_cfg["llm_backend"]]
    world_memory = StructuredMemory(
        storage_path=project_path / "data" / "world_memory.json"
    )
    # Load world bible
    world_file = config.world.get("file")
    if world_file:
        world_path = project_path / world_file
        if world_path.exists():
            world_data = load_yaml_file(world_path)
            await world_memory.load_from_dict(world_data)

    world_prompt_dir = prompt_dir / "world" if (prompt_dir / "world").exists() else None
    world_agent = WorldAgent(
        config=AgentConfig(
            name="world",
            role="world",
            llm_backend_id=world_cfg["llm_backend"],
            system_prompt_template="system.jinja2" if world_prompt_dir else "",
            max_context_tokens=world_backend.config.max_tokens,
            temperature=0.6,
            prompt_variables=lang_vars,
            subscriptions=[
                EventType.WORLD_QUERY,
                EventType.SETTING_VALIDATION_REQUEST,
                EventType.LORE_CHECK,
                EventType.CONSISTENCY_CHECK_REQUEST,
            ],
        ),
        llm=world_backend,
        memory=world_memory,
        event_bus=event_bus,
        prompt_dir=world_prompt_dir,
    )
    await world_agent.initialize()

    # Create PlotAgent
    plot_cfg = config.agents.plot
    plot_backend = backends[plot_cfg["llm_backend"]]
    plot_memory = StructuredMemory(
        storage_path=project_path / "data" / "plot_memory.json"
    )
    # Load plot outline
    plot_file = config.plot.get("file")
    if plot_file:
        plot_path = project_path / plot_file
        if plot_path.exists():
            plot_data = load_yaml_file(plot_path)
            await plot_memory.store("plot_outline", plot_data)

    plot_prompt_dir = prompt_dir / "plot" if (prompt_dir / "plot").exists() else None
    plot_agent = PlotAgent(
        config=AgentConfig(
            name="plot",
            role="plot",
            llm_backend_id=plot_cfg["llm_backend"],
            system_prompt_template="system.jinja2" if plot_prompt_dir else "",
            max_context_tokens=plot_backend.config.max_tokens,
            temperature=0.7,
            prompt_variables=lang_vars,
            subscriptions=[
                EventType.CHAPTER_PLAN_REQUEST,
                EventType.PACING_CHECK_REQUEST,
                EventType.QUALITY_CHECK_REQUEST,
            ],
        ),
        llm=plot_backend,
        memory=plot_memory,
        event_bus=event_bus,
        prompt_dir=plot_prompt_dir,
    )
    await plot_agent.initialize()

    # Create WritingAgent
    writing_cfg = config.agents.writing
    writing_backend = backends[writing_cfg["llm_backend"]]
    writing_memory = StructuredMemory(
        storage_path=project_path / "data" / "writing_memory.json"
    )

    writing_prompt_dir = prompt_dir / "writing" if (prompt_dir / "writing").exists() else None
    writing_agent = WritingAgent(
        config=AgentConfig(
            name="writing",
            role="writing",
            llm_backend_id=writing_cfg["llm_backend"],
            system_prompt_template="system.jinja2" if writing_prompt_dir else "",
            max_context_tokens=writing_backend.config.max_tokens,
            temperature=0.8,
            prompt_variables=lang_vars,
            subscriptions=[
                EventType.SCENE_DRAFT_REQUEST,
                EventType.REVISION_REQUEST,
            ],
        ),
        llm=writing_backend,
        memory=writing_memory,
        event_bus=event_bus,
        prompt_dir=writing_prompt_dir,
    )
    await writing_agent.initialize()

    # Create CharacterAgents
    char_prompt_dir = prompt_dir / "character" if (prompt_dir / "character").exists() else None
    character_agents: dict[str, CharacterAgent] = {}
    for char_cfg in config.agents.characters:
        char_backend = backends[char_cfg.llm_backend]

        # Load character sheet
        sheet_path = project_path / char_cfg.character_sheet
        if sheet_path.exists():
            sheet_data = load_yaml_file(sheet_path)
            character_sheet = CharacterSheet.from_dict(sheet_data)
        else:
            character_sheet = CharacterSheet(name=char_cfg.name)

        # Create memory (vector for characters)
        if char_cfg.memory_type == "vector":
            data_dir = project_path / "data" / "memories"
            data_dir.mkdir(parents=True, exist_ok=True)
            safe_name = _sanitize_collection_name(char_cfg.name)
            char_memory = VectorMemory(
                collection_name=safe_name,
                persist_directory=str(data_dir / safe_name),
            )
        else:
            char_memory = StructuredMemory(
                storage_path=project_path / "data" / f"{char_cfg.name.lower()}_memory.json"
            )

        char_agent = CharacterAgent(
            config=AgentConfig(
                name=char_cfg.name,
                role="character",
                llm_backend_id=char_cfg.llm_backend,
                system_prompt_template="system.jinja2" if char_prompt_dir else "",
                max_context_tokens=char_backend.config.max_tokens,
                temperature=0.8,
                prompt_variables=lang_vars,
                subscriptions=[
                    EventType.CHARACTER_REACTION_REQUEST,
                    EventType.DIALOGUE_REQUEST,
                ],
            ),
            llm=char_backend,
            memory=char_memory,
            event_bus=event_bus,
            character_sheet=character_sheet,
            prompt_dir=char_prompt_dir,
        )
        await char_agent.initialize()
        character_agents[char_cfg.name] = char_agent

    # Create summarizer
    summarizer = MemorySummarizer(llm=plot_backend)

    # Create pipeline
    pipeline = ChapterPipeline(
        event_bus=event_bus,
        world_agent=world_agent,
        character_agents=character_agents,
        plot_agent=plot_agent,
        writing_agent=writing_agent,
        output_manager=output_mgr,
        summarizer=summarizer,
        max_revision_rounds=config.pipeline.max_revision_rounds,
        parallel_characters=config.pipeline.parallel_character_reactions,
    )

    return {
        "event_bus": event_bus,
        "world_agent": world_agent,
        "plot_agent": plot_agent,
        "writing_agent": writing_agent,
        "character_agents": character_agents,
        "pipeline": pipeline,
        "output_manager": output_mgr,
    }


if __name__ == "__main__":
    main()
