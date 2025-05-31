"""Commands for displaying Trilium server information."""

import click
from typing import Optional, Any
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from trilium_py.client import ETAPI

# Import utils here to avoid circular imports
from .. import utils

console = Console()

@click.group()
def info() -> None:
    """Display information about the Trilium server."""
    pass

@info.command()
@click.pass_context
def server(ctx: click.Context) -> None:
    """Display information about the connected Trilium server."""
    try:
        # Get ETAPI client using the utility function
        ea = utils.get_etapi(ctx)
        
        # Get and display app info
        console.print("Fetching server information...")
        app_info = ea.app_info()
        
        # Display connection info
        server_url = ea.server_url
        token = ea.token

        # keys are in camelCase, convert to Space Separated Words and format each line
        def format_key(key: str) -> str:
            # Split words on capitals, then capitalize first letter of each word
            import re
            words = re.sub('([A-Z][a-z]+)', r' \1', re.sub('([A-Z]+)', r' \1', key)).split()
            return ' '.join(word.capitalize() for word in words)
            
        # Build formatted lines with consistent alignment
        formatted_lines = []
        
        # Connection info
        formatted_lines.append(f"[bold]Server[/]{''.ljust(18)}: {server_url}")
        formatted_lines.append(f"[bold]Token [/]{''.ljust(18)}: {token[-4:]}{'.'*(len(server_url)-8)}{token[:4]}")
        
        # App info
        for key, value in app_info.items():
            # Format the key with color and alignment
            formatted_key = f"[cyan]{format_key(key).ljust(24)}[/]"
            # Convert value to string and handle None
            formatted_value = str(value) if value is not None else "-"
            formatted_lines.append(f"{formatted_key}: {formatted_value}")
        
        # Display in a panel with consistent formatting
        console.print(Panel.fit(
            "\n".join(formatted_lines),
            title="[bold blue]Trilium Server Information[/]",
            border_style="blue"
        ))
        
    except Exception as e:
        console.print(Panel.fit(
            f"[bold red]✗ Failed to connect: {str(e)}[/bold red]\n\n"
            "Please check your configuration and ensure:\n"
            "- Server URL is correct\n"
            "- Token is valid\n"
            "- Trilium server is running and accessible",
            title="Connection Failed",
            border_style="red"
        ))
        raise click.Abort()
