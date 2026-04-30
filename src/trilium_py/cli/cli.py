"""Main CLI module for tpy-cli."""

import os
import click
from typing import Optional, Any
from pathlib import Path

from .. import __version__
from . import utils
from . import options
from .utils import load_environment, ensure_config
from .options import common_options, env_file_option

# Import command groups here to avoid circular imports
from .commands import info as info_commands

# Commands are registered using the @main.command() decorator

@click.group()
@click.version_option(version=__version__)
@env_file_option()  # This is a decorator factory, so we call it
@click.option(
    "--debug", is_flag=True, help="Enable debug output"
)
@click.pass_context
def main(ctx: click.Context, env_file: Optional[Path] = None, debug: bool = False, **kwargs: Any) -> None:
    """Trilium-py CLI - Command line interface for trilium-py.
    
    Configuration is loaded in this order:
      1. Command line arguments
      2. Environment variables
      3. Local .env file
      4. Global ~/.trilium-py/.env file
    """
    # Store debug flag in context
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    
    # Skip configuration check for config commands
    if ctx.invoked_subcommand == "config":
        return
        
    # Load environment from specified file if provided
    if env_file:
        if debug:
            click.echo(f"[DEBUG] Loading environment from {env_file}", err=True)
        load_environment(env_file, debug=debug)
    
    # Initialize context object with server and token
    try:
        # Only try to load config if this is not the info command
        if ctx.invoked_subcommand != "info":
            ctx.obj["server"], ctx.obj["token"] = ensure_config(debug=debug)
    except click.UsageError as e:
        if debug:
            click.echo(f"[DEBUG] Configuration error: {e}", err=True)
        # Allow info commands to run even without config
        if ctx.invoked_subcommand != "info":
            raise

# Import and register commands after main is defined to avoid circular imports
from .commands import notes, config

# Register command groups
main.add_command(notes.notes, name="notes")
main.add_command(config.config, name="config")
main.add_command(info_commands.info, name="info")

if __name__ == "__main__":
    main()
