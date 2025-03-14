"""
Trilium ETAPI Token Manager

This script obtains and saves a Trilium ETAPI token for use with Trilium-py tools.
It supports both local and remote Trilium servers.

Usage:
    uv run get_etapi_token.py http://localhost:8080 your-password
    
The token will be saved to a .env file in the current directory or in ~/.trilium-py/.env
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
import click
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
import os
from dotenv import load_dotenv

from trilium_py.client import ETAPI

console = Console()


def get_token_from_server(server_url: str, password: str):
    """
    Connect to Trilium server and get an ETAPI token using password
    
    Returns:
        tuple: (token, app_info)
    """
    ea = ETAPI(server_url)
    token = ea.login(password)
    
    if not token:
        raise Exception("Failed to authenticate with the provided password")
    
    app_info = ea.app_info()
    return token, app_info


def save_token(token: str, server_url: str, save_path: Path):
    """
    Save the token and server URL to a .env file
    
    Args:
        token: The ETAPI token
        server_url: The Trilium server URL
        save_path: Path to save the .env file
        
    Returns:
        Path: The path where the token was saved
    """
    # Create parent directories if they don't exist
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load existing .env if it exists
    env_vars = {}
    if save_path.exists():
        load_dotenv(save_path)
        for key, value in os.environ.items():
            if key.startswith('TRILIUM_'):
                env_vars[key] = value
    
    # Update with new values
    env_vars['TRILIUM_SERVER'] = server_url
    env_vars['TRILIUM_TOKEN'] = token
    
    # Write to file
    with open(save_path, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    return save_path


@click.command(help="Get and save Trilium ETAPI token")
@click.argument("server_url")
@click.argument("password")
@click.option("--env-file", "-e", help="Path to .env file to save token", 
              type=click.Path(dir_okay=False, resolve_path=True))
@click.option("--global", "is_global", is_flag=True, help="Save token to global ~/.trilium-py/.env file")
def main(server_url: str, password: str, env_file: str, is_global: bool):
    """Get and save a Trilium ETAPI token."""
    try:
        # Get token from server
        console.print(f"Connecting to Trilium server at [bold]{server_url}[/bold]...")
        token, app_info = get_token_from_server(server_url, password)
        
        # Determine where to save the token
        if env_file:
            save_path = Path(env_file)
        elif is_global:
            save_path = Path.home() / '.trilium-py' / '.env'
        else:
            save_path = Path.cwd() / '.env'
        
        # Save token
        path = save_token(token, server_url, save_path)
        
        # Success message
        console.print(Panel.fit(
            f"[bold green]✓ Successfully obtained token from Trilium {app_info['appVersion']}[/bold green]\n\n"
            f"Token saved to: [bold]{path}[/bold]\n\n"
            "You can now use Trilium-py tools that require Trilium authentication.",
            title="Trilium Authentication Successful",
            border_style="green"
        ))
        
    except Exception as e:
        console.print(Panel.fit(
            f"[bold red]✗ Failed to get token: {str(e)}[/bold red]\n\n"
            "Please check:\n"
            "- Server URL is correct\n"
            "- Password is correct\n"
            "- Trilium server is running and accessible",
            title="Authentication Failed",
            border_style="red"
        ))
        sys.exit(1)


if __name__ == "__main__":
    main()
