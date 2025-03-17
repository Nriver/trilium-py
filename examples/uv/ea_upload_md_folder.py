"""
Trilium-py Bulk Markdown Uploader

This script uploads a folder of Markdown files to Trilium, preserving the folder structure.
It supports various Markdown applications like VNote, Joplin, Logseq, and Obsidian.

Usage:
    uv run ea_upload_md_folder --folder ~/path/to/markdown/folder --parent-note noteTitle
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
from pathlib import Path
from typing import List, Optional, Tuple
import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from dotenv import load_dotenv
from datetime import datetime

from trilium_py.client import ETAPI

console = Console()


def load_env_file(env_file: Optional[Path] = None, is_global: bool = False) -> Tuple[Optional[str], Optional[str], Optional[Path]]:
    """
    Load environment variables from .env file.
    
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


def detect_markdown_app(folder_path: Path) -> str:
    """
    Attempt to detect which Markdown application the folder is from
    
    Args:
        folder_path: Path to the Markdown folder
        
    Returns:
        str: Detected application name or "generic"
    """
    # Check for VNote
    if (folder_path / "vx_notebook").exists() or (folder_path / "vx_images").exists():
        return "vnote"
    
    # Check for Logseq
    if (folder_path / "logseq").exists() or (folder_path / "pages").exists():
        return "logseq"
    
    # Check for Joplin
    if (folder_path / "_resources").exists():
        return "joplin"
    
    # Check for Obsidian
    if (folder_path / ".obsidian").exists():
        return "obsidian"
    
    # Default to generic
    return "generic"


def get_ignore_folders(app_type: str) -> List[str]:
    """
    Get the list of folders to ignore based on the Markdown application type
    
    Args:
        app_type: Type of Markdown application
        
    Returns:
        List[str]: List of folder names to ignore
    """
    ignore_folders = {
        "vnote": ['vx_notebook', 'vx_recycle_bin', 'vx_images', '_v_images'],
        "logseq": ['assets', 'logseq', '.git', 'journals', 'bak'],
        "joplin": ['_resources'],
        "obsidian": ['.obsidian', '.git', '.trash'],
        "generic": ['.git', '.svn', 'node_modules']
    }
    
    
    return ignore_folders.get(app_type, ignore_folders["generic"])


def find_folders_matching_md_files(folder_path: Path) -> List[str]:
    """
    Find folders that have the same name as Markdown files (without extension).
    
    Args:
        folder_path: Path to the folder containing Markdown files
        
    Returns:
        List[str]: List of folder names that match Markdown file names
    """
    matching_folders = []
    md_file_basenames = set()
    
    # First pass: collect all markdown file basenames
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.md') or file.endswith('.mdx'):
                md_file_basenames.add(os.path.splitext(file)[0])
    
    # Second pass: find directories that match the basenames
    for root, dirs, _ in os.walk(folder_path):
        for dir_name in dirs:
            if dir_name in md_file_basenames:
                matching_folders.append(dir_name)
    
    return matching_folders


@click.command(help="Bulk upload Markdown files to Trilium")
@click.option("--folder", "-f", required=True, help="Path to folder containing Markdown files",
              type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option("--parent-title", "-p", required=True, help="Title of the parent note to upload files to")
@click.option("--parent-parent-title", "-pp", help="If parent note needs to be created, use this as its parent (defaults to root)", default="root")
@click.option("--env-file", "-e", help="Path to .env file with token", 
              type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--global", "is_global", is_flag=True, help="Use global ~/.trilium-py/.env file")
@click.option("--app-type", "-a", help="Markdown application type (vnote, logseq, joplin, obsidian, generic)",
              type=click.Choice(["vnote", "logseq", "joplin", "obsidian", "generic"]))
@click.option("--ignore-folders", "-i", help="Additional folders to ignore (comma-separated)",
              default="")
@click.option("--ignore-files", "-if", help="Files to ignore (comma-separated)",
              default="")
@click.option("--include-pattern", "-ip", help="File patterns to include (comma-separated)",
              default=".md")
def main(folder: str, parent_title: str, parent_parent_title: str, env_file: Optional[str], is_global: bool, 
         app_type: Optional[str], ignore_folders: str, ignore_files: str, include_pattern: str) -> None:
    """
    Bulk upload Markdown files to Trilium.
    
    This function handles the process of uploading a folder of Markdown files to Trilium
    while preserving the folder structure. It supports automatic detection of different
    Markdown applications and applies appropriate folder ignore rules.
    """
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
        
        # Process folder path
        folder_path = Path(folder)
        
        # Auto-detect app type if not specified
        if not app_type:
            detected_app = detect_markdown_app(folder_path)
            app_type = detected_app
            console.print(f"[bold]Detected Markdown application:[/bold] {app_type}")
        
        # Get ignore folders based on app type
        base_ignore_folders = get_ignore_folders(app_type)
        
        # Find folders with the same name as Markdown files
        matching_folders = find_folders_matching_md_files(folder_path)
        if matching_folders:
            console.print(f"[yellow]Found folders with same name as Markdown files: {', '.join(matching_folders)}[/yellow]")
            console.print("[yellow]These folders will be ignored to prevent conflicts[/yellow]")
            base_ignore_folders.extend(matching_folders)
        
        # Add user-specified ignore folders
        if ignore_folders:
            additional_ignore_folders = [f.strip() for f in ignore_folders.split(",")]
            base_ignore_folders.extend(additional_ignore_folders)
        
        # Process ignore files
        ignore_files_list = [f.strip() for f in ignore_files.split(",")] if ignore_files else []
        
        # Process include patterns
        include_patterns = [p.strip() for p in include_pattern.split(",")] if include_pattern else [".md"]
        
        # Show upload configuration
        config_info = [
            f"[bold]Folder to upload:[/bold] {folder_path}",
            f"[bold]Application type:[/bold] {app_type}",
            f"[bold]Parent note title:[/bold] {parent_title}"
        ]
        
        # Only show parent-parent title if it's not the default "root"
        if parent_parent_title.lower() != "root":
            config_info.append(f"[bold]Parent of parent note title:[/bold] {parent_parent_title}")
            
        config_info.extend([
            f"[bold]Folders to ignore:[/bold] {', '.join(base_ignore_folders)}",
            f"[bold]Files to ignore:[/bold] {', '.join(ignore_files_list)}",
            f"[bold]Include patterns:[/bold] {', '.join(include_patterns)}"
        ])
        
        console.print(Panel.fit(
            "\n".join(config_info),
            title="Upload Configuration",
            border_style="green"
        ))
        
        # Confirm before proceeding
        # Default to Y on [enter]
        if not Confirm.ask("Do you want to proceed with the upload?", default=True):
            console.print("[yellow]Upload cancelled by user[/yellow]")
            sys.exit(0)
        
        # Connect to Trilium
        console.print("Connecting to Trilium server...")
        ea = ETAPI(server_url, token)
        
        # Find parent note ID by title
        parent_note_id = None
        
        # Special case for root note
        if parent_title.lower() == "root":
            parent_note_id = "root"
            console.print("[green]Using root note as parent[/green]")
        else:
            console.print(f"Searching for note with title: {parent_title}")
            search_results = ea.search_note(f"note.title = '{parent_title}'")
            
            if search_results and search_results.get('results'):
                parent_note_id = search_results['results'][0]['noteId']
                console.print(f"[green]Found note with ID: {parent_note_id}[/green]")
            else:
                console.print(f"[yellow]Note with title '{parent_title}' not found[/yellow]")
                
                # Offer to create the parent note
                if Confirm.ask(f"Would you like to create a new note titled '{parent_title}' under '{parent_parent_title}'?", default=True):
                    try:
                        # Create the parent note under parent_parent_title
                        if parent_parent_title.lower() == "root":
                            parent_parent_note_id = "root"
                        else:
                            parent_parent_note_id = None
                            console.print(f"Searching for note with title: {parent_parent_title}")
                            search_results = ea.search_note(f"note.title = '{parent_parent_title}'")
                            
                            if search_results and search_results.get('results'):
                                parent_parent_note_id = search_results['results'][0]['noteId']
                                console.print(f"[green]Found note with ID: {parent_parent_note_id}[/green]")
                            else:
                                console.print(f"[yellow]Note with title '{parent_parent_title}' not found[/yellow]")
                                parent_parent_note_id = "root"
                        
                        # Create the parent note under parent_parent_title
                        res = ea.create_note(
                            parentNoteId=parent_parent_note_id,
                            title=parent_title,
                            type="text",
                            content=f"Created as parent for Markdown upload on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                        )
                        parent_note_id = res['note']['noteId']
                        console.print(f"[green]Created new parent note with ID: {parent_note_id}[/green]")
                    except Exception as e:
                        console.print(Panel.fit(
                            f"[bold red]✗ Failed to create parent note: {str(e)}[/bold red]",
                            title="Error Creating Parent Note",
                            border_style="red"
                        ))
                        sys.exit(1)
                else:
                    console.print(Panel.fit(
                        f"[bold red]✗ Parent note with title '{parent_title}' not found and creation was declined[/bold red]\n\n"
                        "Please check the title and try again, or allow the script to create the parent note.",
                        title="Parent Note Not Found",
                        border_style="red"
                    ))
                    sys.exit(1)
        
        # Perform the upload
        console.print("[bold]Starting upload...[/bold]")
        try:
            result = ea.upload_md_folder(
                parentNoteId=parent_note_id,
                mdFolder=str(folder_path),
                includePattern=include_patterns,
                ignoreFolder=base_ignore_folders,
                ignoreFile=ignore_files_list,
            )
            
            # Check for errors in the log
            import logging
            log_handler = logging.getLogger("trilium_py.client")
            has_errors = any(record.levelno >= logging.ERROR for record in log_handler.handlers[0].records) if log_handler.handlers else False
            
            if result and not has_errors:
                console.print(Panel.fit(
                    "[bold green]✓ Successfully uploaded Markdown files to Trilium[/bold green]\n\n"
                    f"Files from [bold]{folder_path}[/bold] have been uploaded to note with ID [bold]{parent_note_id}[/bold]",
                    title="Upload Successful",
                    border_style="green"
                ))
            else:
                console.print(Panel.fit(
                    "[bold yellow]⚠ Upload completed with some errors[/bold yellow]\n\n"
                    "Some files may not have been uploaded correctly. Check the logs for details.",
                    title="Upload Completed with Warnings",
                    border_style="yellow"
                ))
        except KeyError as e:
            if str(e) == "'note'":
                console.print(Panel.fit(
                    "[bold yellow]⚠ Upload completed with a known issue[/bold yellow]\n\n"
                    "There was a KeyError: 'note' error in the trilium-py library.\n"
                    "This typically happens when a folder has the same name as a Markdown file.\n\n"
                    "Possible solutions:\n"
                    "1. Add the folder to the ignore list using --ignore-folders\n"
                    "2. Rename either the folder or the Markdown file\n"
                    "3. Use the --app-type generic option which automatically ignores such folders",
                    title="Known Issue Detected",
                    border_style="yellow"
                ))
                sys.exit(1)
            else:
                raise
        except Exception as e:
            console.print(Panel.fit(
                f"[bold red]✗ Upload failed: {str(e)}[/bold red]\n\n"
                "Please check:\n"
                "- Server URL is correct\n"
                "- Token is valid\n"
                "- Trilium server is running and accessible\n"
                "- The folder path exists and contains Markdown files",
                title="Upload Failed",
                border_style="red"
            ))
            sys.exit(1)
        
    except Exception as e:
        console.print(Panel.fit(
            f"[bold red]✗ Upload failed: {str(e)}[/bold red]\n\n"
            "Please check:\n"
            "- Server URL is correct\n"
            "- Token is valid\n"
            "- Trilium server is running and accessible\n"
            "- The folder path exists and contains Markdown files",
            title="Upload Failed",
            border_style="red"
        ))
        sys.exit(1)


if __name__ == "__main__":
    main()
