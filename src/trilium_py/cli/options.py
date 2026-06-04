"""Common CLI options for tpy-cli."""

import click
from typing import Callable, Any, TypeVar, Optional
from pathlib import Path

F = TypeVar('F', bound=Callable[..., Any])

def server_option() -> Callable[[F], F]:
    """Decorator to add --server option to a command."""
    return click.option(
        "--server",
        envvar="TRILIUM_SERVER",
        help="Trilium server URL (e.g., http://localhost:8080)",
        required=False,
    )

def token_option() -> Callable[[F], F]:
    """Decorator to add --token option to a command."""
    return click.option(
        "--token",
        envvar="TRILIUM_TOKEN",
        help="Trilium ETAPI token",
        required=False,
    )

def common_options(func: F) -> F:
    """Decorator to add common options to a command."""
    func = server_option()(func)
    func = token_option()(func)
    return func

def env_file_option() -> Callable[[F], F]:
    """Decorator to add --env-file option to a command."""
    return click.option(
        "--env-file",
        type=click.Path(exists=True, dir_okay=False, path_type=Path),
        help="Path to .env file to load",
    )
