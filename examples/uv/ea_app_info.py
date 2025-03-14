"""
Trilium App Info Viewer

This script reads the saved Trilium ETAPI token from a .env file and displays
information about the connected Trilium server.

Usage:
    uv run ea_app_info.py
    
The script will look for .env files in the following locations (in order):
1. Current directory
2. ~/.trilium-py/.env (if --global flag is used)
3. Custom path specified with --env-file
"""
# /// script
# dependencies = [
#   "trilium-py",
#   "python-dotenv",
#   "click",
#   "rich",
# ]
# ///

import sys
import os
import click
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

from trilium_py.client import ETAPI

console = Console()


def load_env_file(env_file: Path = None, is_global: bool = False) -> tuple:
    """
    Load environment variables from .env file
    
    Args:
        env_file: Path to custom .env file
        is_global: Whether to use global .env file
        
    Returns:
        tuple: (server_url, token, source_path) or (None, None, None) if not found
    """
    source_path = None
    
    # Determine which .env file to load
    if env_file and env_file.exists():
        load_dotenv(env_file)
        source_path = env_file
    elif is_global:
        global_env = Path.home() / '.trilium-py' / '.env'
        if global_env.exists():
            load_dotenv(global_env)
            source_path = global_env
    else:
        local_env = Path.cwd() / '.env'
        if local_env.exists():
            load_dotenv(local_env)
            source_path = local_env
        else:
            return None, None, None
    
    # Get values from environment
    server_url = os.environ.get('TRILIUM_SERVER')
    token = os.environ.get('TRILIUM_TOKEN')
    
    return server_url, token, source_path


def display_app_info(app_info: dict):
    """
    Display application information in a formatted table
    
    Args:
        app_info: Dictionary containing application information
    """
    table = Table(title=f"Trilium Server Information")
    
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    for key, value in app_info.items():
        table.add_row(key, str(value))
    
    console.print(table)


@click.command(help="Display Trilium server information")
@click.option("--env-file", "-e", help="Path to .env file with token", 
              type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--global", "is_global", is_flag=True, help="Use global ~/.trilium-py/.env file")
def main(env_file: str, is_global: bool):
    """Display information about the connected Trilium server."""
    try:
        # Load environment variables
        env_path = Path(env_file) if env_file else None
        server_url, token, source_path = load_env_file(env_path, is_global)
        
        if not server_url or not token:
            console.print(Panel.fit(
                "No Trilium configuration found. Please run get_etapi_token.py first to set up your connection.",
                title="Configuration Not Found",
                border_style="yellow"
            ))
            sys.exit(0)
        
        # Connect to server
        console.print(Panel.fit(
            f"[bold]Configuration Source:[/bold] {source_path}\n"
            f"[bold]Server URL:[/bold] {server_url}\n"
            f"[bold]Token:[/bold] {'*' * 8}...{token[-4:] if token else ''}",
            title="Connection Information",
            border_style="blue"
        ))
        
        console.print(f"Connecting to Trilium server...")
        ea = ETAPI(server_url, token)
        
        # Get and display app info
        app_info = ea.app_info()
        display_app_info(app_info)
        
    except Exception as e:
        console.print(Panel.fit(
            f"[bold red]✗ Failed to connect: {str(e)}[/bold red]\n\n"
            "Please check:\n"
            "- Server URL is correct\n"
            "- Token is valid\n"
            "- Trilium server is running and accessible",
            title="Connection Failed",
            border_style="red"
        ))
        sys.exit(1)


if __name__ == "__main__":
    main()
