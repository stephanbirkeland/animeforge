"""CLI entry point using Typer."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    name="animeforge",
    help="Lo-fi Girl-style interactive anime scene engine.",
    no_args_is_help=True,
)


@app.command()
def create(
    name: Annotated[str, typer.Argument(help="Project name")],
    directory: Annotated[
        Path | None,
        typer.Option("--dir", "-d", help="Project directory"),
    ] = None,
) -> None:
    """Create a new AnimeForge project."""
    from animeforge.config import load_config
    from animeforge.models.character import Character
    from animeforge.models.project import Project
    from animeforge.models.scene import Scene

    config = load_config()
    project_dir = directory or config.projects_dir / name
    project = Project(
        name=name,
        scene=Scene(name=f"{name}-scene"),
        character=Character(name="Character", description="anime character"),
        project_dir=project_dir,
    )
    save_path = project.save()
    typer.echo(f"Created project '{name}' at {save_path}")


@app.command()
def generate(
    prompt: Annotated[str, typer.Argument(help="Generation prompt")],
    negative: Annotated[str, typer.Option("--negative", "-n", help="Negative prompt")] = "",
    width: Annotated[int, typer.Option("--width", "-W", help="Image width")] = 1024,
    height: Annotated[int, typer.Option("--height", "-H", help="Image height")] = 1024,
    steps: Annotated[int, typer.Option("--steps", "-s", help="Sampling steps")] = 30,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output directory"),
    ] = None,
) -> None:
    """Generate a single anime image via ComfyUI."""
    import asyncio

    from animeforge.backend.base import GenerationRequest
    from animeforge.backend.comfyui import ComfyUIBackend
    from animeforge.config import load_config

    config = load_config()
    backend = ComfyUIBackend(config.comfyui, output_dir=output)

    request = GenerationRequest(
        prompt=prompt,
        negative_prompt=negative,
        width=width,
        height=height,
        steps=steps,
    )

    async def _run() -> None:
        await backend.connect()
        try:
            available = await backend.is_available()
            if not available:
                typer.echo("Error: ComfyUI is not available. Is it running?", err=True)
                raise typer.Exit(1)

            typer.echo(f"Generating: {prompt}")
            result = await backend.generate(
                request,
                progress_callback=lambda step, total, status: typer.echo(
                    f"  {status} ({step}/{total})", nl=False
                ),
            )
            for img in result.images:
                typer.echo(f"Saved: {img}")
        finally:
            await backend.disconnect()

    asyncio.run(_run())


@app.command()
def export(
    project_path: Annotated[Path, typer.Argument(help="Path to project directory or JSON")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output directory"),
    ] = None,
) -> None:
    """Export a project as a web package."""
    from animeforge.models.export import ExportConfig
    from animeforge.models.project import Project, ProjectLoadError
    from animeforge.pipeline.export import export_project

    try:
        project = Project.load(project_path)
    except ProjectLoadError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from None
    export_config = ExportConfig(output_dir=output or Path("output"))
    export_project(project, export_config)
    typer.echo(f"Exported to {export_config.output_dir}")


@app.command()
def serve(
    directory: Annotated[
        Path, typer.Argument(help="Directory to serve")
    ] = Path("output"),
    port: Annotated[int, typer.Option("--port", "-p", help="Port number")] = 3000,
) -> None:
    """Serve an exported web package locally."""
    import http.server
    import os
    import socketserver

    os.chdir(directory)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        typer.echo(f"Serving {directory} at http://localhost:{port}")
        typer.echo("Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            typer.echo("\nStopped.")


@app.command()
def tui() -> None:
    """Launch the interactive TUI."""
    from animeforge.app import AnimeForgeApp

    app_instance = AnimeForgeApp()
    app_instance.run()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool, typer.Option("--version", "-v", help="Show version")
    ] = False,
) -> None:
    """AnimeForge - Lo-fi Girl-style interactive anime scene engine."""
    if version:
        from animeforge import __version__

        typer.echo(f"animeforge {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        # Default to TUI when no subcommand
        from animeforge.app import AnimeForgeApp

        app_instance = AnimeForgeApp()
        app_instance.run()
