from pathlib import Path

import typer
from typing import Optional
from .deploy import deploy_component
from .executor import ssh_connection

app = typer.Typer()


@app.command()
def lv2_analyze(
    lv2_dir: Path = typer.Argument(
        ..., help="Path to the LV2 plugins directory", exists=True
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Path to write full JSON report"
    ),
):
    """Analyze pre-compiled LV2 plugins for dynamic library version requirements."""
    from .lv2_analyze import analyze

    analyze(lv2_dir, output)


@app.command()
def deploy(
    target: Optional[str] = typer.Argument(
        None, help="Component name, directory, Git URL, or Tarball URL"
    ),
    ssh: Optional[str] = typer.Option(
        None, "--ssh", help="SSH host (e.g., pistomp@pistomp.local) to run on"
    ),
    branch: Optional[str] = typer.Option(
        None, help="Git branch to checkout (overrides target#branch)"
    ),
    restart: bool = typer.Option(
        True, help="Restart associated services after installation"
    ),
):
    """
    Deploy a component to the system (local or remote).
    """

    # Wrapper for main logic to handle SSH context
    if ssh:
        with ssh_connection(ssh):
            deploy_component(target, branch, restart)
    else:
        deploy_component(target, branch, restart)


if __name__ == "__main__":
    app()
