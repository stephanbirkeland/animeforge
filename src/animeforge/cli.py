"""CLI entry point using Typer."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    name="animeforge",
    help="Lo-fi Girl-style interactive anime scene engine.",
    no_args_is_help=False,
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
    backend: Annotated[
        str | None,
        typer.Option("--backend", "-b", help="Backend: comfyui, fal, or mock"),
    ] = None,
) -> None:
    """Generate a single anime image."""
    import asyncio

    from animeforge.backend.base import GenerationRequest
    from animeforge.config import load_config

    config = load_config()
    backend_name = backend or config.active_backend

    from animeforge.backend.comfyui import ComfyUIBackend
    from animeforge.backend.fal_backend import FalBackend
    from animeforge.backend.mock import MockBackend

    gen_backend: ComfyUIBackend | FalBackend | MockBackend
    if backend_name == "fal":
        gen_backend = FalBackend(config.fal, output_dir=output)
    elif backend_name == "mock":
        gen_backend = MockBackend(output_dir=output)
    else:
        gen_backend = ComfyUIBackend(config.comfyui, output_dir=output)

    request = GenerationRequest(
        prompt=prompt,
        negative_prompt=negative,
        width=width,
        height=height,
        steps=steps,
    )

    async def _run() -> None:
        await gen_backend.connect()
        try:
            available = await gen_backend.is_available()
            if not available:
                typer.echo(f"Error: {backend_name} backend is not available.", err=True)
                raise typer.Exit(1)

            typer.echo(f"Generating ({backend_name}): {prompt}")
            result = await gen_backend.generate(
                request,
                progress_callback=lambda step, total, status: typer.echo(
                    f"  {status} ({step}/{total})", nl=False
                ),
            )
            for img in result.images:
                typer.echo(f"Saved: {img}")
        finally:
            await gen_backend.disconnect()

    asyncio.run(_run())


@app.command()
def check() -> None:
    """Check backend connectivity and report status."""
    import asyncio

    from animeforge.config import load_config

    config = load_config()
    backend_name = config.active_backend

    async def _run() -> None:
        if backend_name == "fal":
            from animeforge.backend.fal_backend import FalBackend

            fal_backend = FalBackend(config.fal)
            await fal_backend.connect()
            try:
                available = await fal_backend.is_available()
                if available:
                    models = await fal_backend.get_models()
                    typer.echo("fal.ai: connected")
                    typer.echo(f"Endpoints: {', '.join(models)}")
                    typer.echo("Status: ready")
                else:
                    typer.echo("fal.ai: unavailable (check FAL_KEY)")
                    typer.echo("Status: offline")
                    raise typer.Exit(1)
            finally:
                await fal_backend.disconnect()
        elif backend_name == "mock":
            typer.echo("Mock backend: always available")
            typer.echo("Status: ready")
        else:
            from animeforge.backend.comfyui import ComfyUIBackend

            url = config.comfyui.base_url
            comfy_backend = ComfyUIBackend(config.comfyui)
            await comfy_backend.connect()
            try:
                available = await comfy_backend.is_available()
                if available:
                    models = await comfy_backend.get_models()
                    typer.echo(f"ComfyUI: connected ({url})")
                    typer.echo(f"Models: {len(models)} available")
                    typer.echo("Status: ready")
                else:
                    typer.echo(f"ComfyUI: unreachable ({url})")
                    typer.echo("Status: offline \u2014 start ComfyUI to generate assets")
                    raise typer.Exit(1)
            finally:
                await comfy_backend.disconnect()

    asyncio.run(_run())


@app.command()
def export(
    project_path: Annotated[Path, typer.Argument(help="Path to project directory or JSON")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output directory"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Validate export without writing files"),
    ] = False,
) -> None:
    """Export a project as a web package."""
    from animeforge.models.export import ExportConfig
    from animeforge.models.project import Project, ProjectLoadError

    try:
        project = Project.load(project_path)
    except ProjectLoadError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from None
    export_config = ExportConfig(output_dir=output or Path("output"))

    if dry_run:
        from animeforge.pipeline.export import validate_export

        result = validate_export(project, export_config)
        typer.echo("Dry run: export validation")
        for check in result.checks:
            symbol = "\u2713" if check.passed else "\u2717"
            typer.echo(f"  {symbol} {check.label}")
            if not check.passed and check.message:
                typer.echo(f"    {check.message}")
        typer.echo(f"Export would write to: {result.output_dir}/")
        typer.echo(f"Estimated files: {result.estimated_files}")
        if not result.valid:
            raise typer.Exit(1)
    else:
        from animeforge.pipeline.export import export_project

        export_project(project, export_config)
        typer.echo(f"Exported to {export_config.output_dir}")


@app.command()
def preview(
    prompt: Annotated[
        str, typer.Argument(help="Generation prompt")
    ] = "lo-fi anime girl studying, cozy room",
    port: Annotated[int, typer.Option("--port", "-p", help="HTTP port")] = 8765,
    ws_port: Annotated[int, typer.Option("--ws-port", help="WebSocket port")] = 8766,
    no_browser: Annotated[
        bool, typer.Option("--no-browser", help="Don't auto-open browser")
    ] = False,
) -> None:
    """Start a live preview server for mock generation."""
    import asyncio

    from animeforge.preview_server import PreviewServer

    server = PreviewServer(http_port=port, ws_port=ws_port)
    typer.echo(f"Preview server at http://localhost:{port}")
    typer.echo("Press Ctrl+C to stop")
    try:
        asyncio.run(server.run(prompt, open_browser=not no_browser))
    except KeyboardInterrupt:
        typer.echo("\nStopped.")


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
