'''Bulk upload Markdown files to Trilium

A script for uploading Markdown files to Trilium while preserving folder structure.

Usage:
    uv run ea_upload_md_folder.py --folder ~/path/to/markdown/folder --parent-note noteTitle
'''
# /// script
# dependencies = [
#   "trilium-py",
#   "python-dotenv",
#   "click",
#   "rich",
# ]
# ///

import os
import sys
from pathlib import Path
from typing import Optional
import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from dotenv import load_dotenv
from datetime import datetime

from trilium_py.client import ETAPI

# Initialize console for rich output
console = Console()

def load_env_file(env_file: Optional[Path], is_global: bool = False) -> tuple:
    """
    Load environment variables from the appropriate .env file
    
    Args:
        env_file: Path to a specific .env file
        is_global: Whether to use global .env file
        
    Returns:
        tuple: (server_url, token, source_path) or (None, None, None) if not found
    """
    source_path = None
    
    # Determine which .env file to load
    if env_file and Path(env_file).exists():
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

def find_folders_matching_md_files(folder_path: Path) -> list:
    """Identify folders with same name as Markdown file, to avoid duplicately named nodes.
    
    Avoids situation where this input:
        source_dir/
            Foobaz.md
            Foobaz/hero-image.jpg
            Foobaz/another-pic.jpg
    
    Would create in Trilium:
        destination_note/
            Foobaz
                hero-image.jpg
                another-pic.jpg
            Foobaz
                (empty)

    Note: any content in the sub-folder that is not linked to from the .md will be left behind.

    Args:
        folder_path: Path to the folder containing Markdown files
        
    Returns:
        list: List of folder names that match Markdown file names
    """
    matching_folders = []
    md_files = list(folder_path.glob("**/*.md"))
    
    for md_file in md_files:
        # Get the file name without extension
        base_name = md_file.stem
        # Check if a folder with the same name exists in the same directory
        potential_folder = md_file.parent / base_name
        if potential_folder.is_dir():
            matching_folders.append(base_name)
    
    return matching_folders

@click.command(help="Bulk upload Markdown files to Trilium")
@click.option("--folder", "-f", required=True, help="Path to folder containing Markdown files",
              type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option("--parent-note", "-p", required=True, help="Title of the parent note to upload files to")
@click.option("--env-file", "-e", help="Path to .env file with token", 
              type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--global", "is_global", is_flag=True, help="Use global ~/.trilium-py/.env file")
@click.option("--ignore-folders", "-if", help="Additional folders to ignore (comma-separated)",
              default="")
@click.option("--ignore-folder-list", "-ifl", help="Path to a text file with folders to ignore (one per line)",
              type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--ignore-files", "-ig", help="Files to ignore (comma-separated)",
              default="")
@click.option("--include-pattern", "-ip", help="File patterns to include (comma-separated)",
              default=".md")

def main(folder: str, parent_note: str, env_file: Optional[str], is_global: bool,
         ignore_folders: str, ignore_folder_list: str, ignore_files: str, include_pattern: str) -> None:
    """Bulk upload Markdown files to Trilium."""
    try:
        # Load environment variables
        env_file_path = Path(env_file) if env_file else None
        server_url, token, source_path = load_env_file(env_file_path, is_global)
        
        if not server_url or not token:
            console.print("[bold red]Error: TRILIUM_SERVER and TRILIUM_TOKEN must be set in .env file[/bold red]")
            sys.exit(1)
        
        # Mask token for display
        masked_token = token[:5] + "*" * (len(token) - 10) + token[-5:]
        console.print(f"[bold]Server URL:[/bold] {server_url}")
        console.print(f"[bold]Token:[/bold] {masked_token}")
        console.print(f"[bold]Config source:[/bold] {source_path}")
        
        # Convert folder path to Path object
        folder_path = Path(folder)
        
        # Find folders with the same name as Markdown files
        matching_folders = find_folders_matching_md_files(folder_path)
        
        # Process ignore folders
        ignore_folders_list = [f.strip() for f in ignore_folders.split(",")] if ignore_folders else []
        if matching_folders:
            console.print(f"[yellow]Found folders with same name as Markdown files: {', '.join(matching_folders)}[/yellow]")
            console.print("[yellow]These folders will be ignored to prevent conflicts[/yellow]")
            ignore_folders_list.extend(matching_folders)
        
        # Process ignore folder list
        if ignore_folder_list:
            with open(ignore_folder_list, 'r') as f:
                ignore_folders_list.extend([line.strip() for line in f.readlines()])
        
        # Process ignore files
        ignore_files_list = [f.strip() for f in ignore_files.split(",")] if ignore_files else []
        
        # Process include patterns
        include_patterns = [p.strip() for p in include_pattern.split(",")] if include_pattern else [".md"]
        
        # Connect to Trilium
        console.print("Connecting to Trilium server...")
        ea = ETAPI(server_url, token)
        
        # Find parent note ID by title
        parent_note_id = None
        
        # Special case for root note
        if parent_note.lower() == "root":
            parent_note_id = "root"
            console.print("[green]Using root note as parent[/green]")
        else:
            console.print(f"Searching for note with title: {parent_note}")
            search_results = ea.search_note(f"note.title = '{parent_note}'")
            
            if search_results and search_results.get('results'):
                parent_note_id = search_results['results'][0]['noteId']
                console.print(f"[green]Found note with ID: {parent_note_id}[/green]")
            else:
                console.print(f"[yellow]Note with title '{parent_note}' not found[/yellow]")
                
                # Offer to create the parent note
                if Confirm.ask(f"Would you like to create a new note titled '{parent_note}'?", default=True):
                    try:
                        # Special case for root note
                        if parent_note.lower() == "root":
                            parent_note_id = "root"
                            console.print("[green]Using root note as parent[/green]")
                        else:
                            console.print(f"Searching for parent note with title: {parent_note}")
                            search_results = ea.search_note(f"note.title = '{parent_note}'")
                            
                            if search_results and search_results.get('results'):
                                parent_note_id = search_results['results'][0]['noteId']
                                console.print(f"[green]Found parent note with ID: {parent_note_id}[/green]")
                            else:
                                console.print(f"[yellow]Parent note with title '{parent_note}' not found, using root[/yellow]")
                                parent_note_id = "root"
                        
                        res = ea.create_note(
                            parentNoteId=parent_note_id,
                            title=parent_note,
                            type="text",
                            content=f"Imported from <tt>{folder_path}</tt><br>by <tt>{sys.argv[0]}</tt><br>on <tt>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</tt>",
                        )
                        parent_note_id = res['note']['noteId']
                        console.print(f"[green]Created new parent note with ID: {parent_note_id}[/green]")
                    except Exception as e:
                        console.print(f"[bold red]Failed to create parent note: {str(e)}[/bold red]")
                        sys.exit(1)
                else:
                    console.print(f"[bold red]Upload cancelled: Parent note not found[/bold red]")
                    sys.exit(1)
        
        # Show upload configuration
        config_info = [
            f"[bold]Folder to upload:[/bold] {folder_path}",
            f"[bold]Parent note title:[/bold] {parent_note}"
        ]
        
        config_info.extend([
            f"[bold]Folders to ignore:[/bold] {', '.join(ignore_folders_list)}",
            f"[bold]Files to ignore:[/bold] {', '.join(ignore_files_list)}",
            f"[bold]Include patterns:[/bold] {', '.join(include_patterns)}",
        ])
        
        # Show ignore folder list file if specified
        if ignore_folder_list:
            config_info.append(f"[bold]Ignore folder list file:[/bold] {ignore_folder_list}")
            
        console.print(Panel.fit(
            "\n".join(config_info),
            title="Upload Configuration",
            border_style="green"
        ))
        
        # Confirm before proceeding
        if not Confirm.ask("Proceed with upload?", default=True):
            console.print("[bold yellow]Upload cancelled by user[/bold yellow]")
            sys.exit(0)
        
        # Perform the upload
        console.print("[bold]Starting upload...[/bold]")
        try:
            result = ea.upload_md_folder(
                parentNoteId=parent_note_id,
                mdFolder=str(folder_path),
                ignoreFolder=ignore_folders_list,
                ignoreFile=ignore_files_list,
                includePattern=include_patterns
            )
            
            if result:
                console.print(f"[bold green]✓ Successfully uploaded Markdown files to '{parent_note}'[/bold green]")
            else:
                console.print(f"[bold yellow]⚠ Upload completed with some warnings[/bold yellow]")
                
        except Exception as e:
            console.print(f"[bold red]✗ Upload failed: {str(e)}[/bold red]")
            sys.exit(1)
        
    except Exception as e:
        console.print(f"[bold red]✗ Error: {str(e)}[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
