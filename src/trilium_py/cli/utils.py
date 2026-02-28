"""Utility functions for tpy-cli."""

import os
import click
from pathlib import Path
from typing import Optional, Tuple, Any, Dict

from dotenv import load_dotenv
from trilium_py.client import ETAPI

# Configuration file paths
ENV_FILE = Path(".env")  # Local .env file


def load_environment(env_file: Optional[Path] = None, debug: bool = False) -> bool:
    """Load environment variables from .env file or environment.
    
    Order of precedence:
    1. Environment variables
    2. Specified .env file (if provided and exists)
    3. Local .env file (if exists)
    
    Args:
        env_file: Optional path to a custom .env file
        debug: If True, print debug information
        
    Returns:
        bool: True if the environment was loaded successfully
    """
    def debug_print(msg: str) -> None:
        if debug:
            click.echo(f"[DEBUG] {msg}", err=True)
    
    # Try to load from specified env file if provided
    if env_file is not None:
        if env_file.exists():
            debug_print(f"Loading environment from {env_file}")
            return load_dotenv(env_file, override=True)
        debug_print(f"Specified .env file not found: {env_file}")
        return False
    
    # Try local .env file
    if ENV_FILE.exists():
        debug_print(f"Loading environment from {ENV_FILE}")
        return load_dotenv(ENV_FILE, override=True)
    
    debug_print("No .env file found")
    return False


def get_etapi(ctx: click.Context) -> ETAPI:
    """Get an ETAPI client from the Click context.
    
    Args:
        ctx: Click context object containing server and token
        
    Returns:
        ETAPI: Configured ETAPI client
        
    Raises:
        click.UsageError: If server or token is missing
    """
    server = ctx.obj.get("server")
    token = ctx.obj.get("token")
    debug = ctx.obj.get("debug", False)
    
    if not server or not token:
        # Try to get from environment
        server, token = ensure_config(debug=debug)
        if not server or not token:
            raise click.UsageError(
                "Missing server or token. Please configure with:\n"
                "  tpy config set --server URL --token TOKEN"
            )
    
    if debug:
        click.echo(f"[DEBUG] Creating ETAPI client for {server}", err=True)
    
    try:
        return ETAPI(server, token)
    except Exception as e:
        if debug:
            click.echo(f"[DEBUG] Failed to create ETAPI client: {e}", err=True)
        raise click.UsageError(
            "Failed to connect to Trilium. Please check your server URL and token."
        )


def get_config(debug: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """Get server URL and token from environment or .env file.
    
    Args:
        debug: If True, print debug information
        
    Returns:
        tuple: (server_url, token) - either or both may be None if not found
    """
    # Try to load from environment variables first
    server_url = os.getenv("TRILIUM_SERVER")
    token = os.getenv("TRILIUM_TOKEN")
    
    # If not found, try loading from .env file
    if not (server_url and token):
        load_environment(debug=debug)
        server_url = os.getenv("TRILIUM_SERVER")
        token = os.getenv("TRILIUM_TOKEN")
    
    return server_url, token


def ensure_config(server: Optional[str] = None, token: Optional[str] = None, 
                 debug: bool = False) -> Tuple[str, str]:
    """Ensure we have server URL and token, either from args or environment.
    
    Args:
        server: Optional server URL from command line
        token: Optional token from command line
        debug: If True, print debug information
        
    Returns:
        tuple: (server_url, token)
        
    Raises:
        click.UsageError: If configuration is missing or invalid
    """
    def debug_print(msg: str) -> None:
        if debug:
            click.echo(f"[DEBUG] {msg}", err=True)
    
    # Check command line arguments first
    if server:
        debug_print(f"Using server from command line: {server[:10]}...")
    if token:
        debug_print("Using token from command line: [REDACTED]")
    
    # Then check environment variables
    if not server or not token:
        env_server, env_token = get_config(debug=debug)
        server = server or env_server
        token = token or env_token
        
        if env_server and not server:
            debug_print("Using server from environment")
        if env_token and not token:
            debug_print("Using token from environment")
    
    # Final validation
    if not server or not token:
        debug_print("Configuration not found in any source")
        
        # Build helpful error message
        msg = [
            "Missing configuration. Please use one of these methods:",
            "  1. Command line: tpy --server URL --token TOKEN [command]",
            "  2. Environment variables: TRILIUM_SERVER and TRILIUM_TOKEN",
            "  3. .env file in the current directory"
        ]
        
        # Check if we're in the right directory
        cwd = Path.cwd()
        if str(cwd) != str(Path.home()):
            msg.append(f"\nCurrent directory: {cwd}")
        
        # Check for common issues
        issues = []
        if server and not token:
            issues.append("Server URL is set but token is missing")
        elif token and not server:
            issues.append("Token is set but server URL is missing")
            
        if issues:
            msg.append("\nIssues found:")
            for issue in issues:
                msg.append(f"  • {issue}")
        
        # Add example
        msg.extend([
            "",
            "Example .env file:",
            "  TRILIUM_SERVER=https://your-trillium-instance.com",
            "  TRILIUM_TOKEN=your-api-token-here",
            "",
            "To configure, run:",
            "  tpy config set --server URL --token TOKEN"
        ])
        
        raise click.UsageError("\n".join(msg))
    
    # Basic URL validation
    if not server.startswith(('http://', 'https://')):
        debug_print("Server URL should start with http:// or https://")
        raise click.UsageError("Server URL must start with http:// or https://")
    
    debug_print("Configuration loaded successfully")
    return server, token
