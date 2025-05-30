"""An unofficial Python wrapper for the ETAPI of trilium
.. moduleauthor:: Nriver
"""

from .version import __version__

# Import the main CLI function
from .cli.cli import main as cli_main

# For backward compatibility
def main():
    """CLI entry point."""
    return cli_main()

__all__ = ['__version__', 'main', 'cli_main']
