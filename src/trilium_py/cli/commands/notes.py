"""Note-related commands for tpy-cli."""

import click
from pathlib import Path
from typing import Optional, Any
from trilium_py.client import ETAPI

from ..options import common_options
from ..utils import ensure_config

@click.group()
def notes() -> None:
    """Manage Trilium notes."""
    pass

def get_etapi(ctx: click.Context) -> ETAPI:
    """Get ETAPI client from context or environment.
    
    Args:
        ctx: Click context object
        
    Returns:
        ETAPI: Initialized ETAPI client
        
    Raises:
        click.UsageError: If configuration is missing
    """
    debug = ctx.obj.get("debug", False)
    server = ctx.obj.get("server")
    token = ctx.obj.get("token")
    
    if debug:
        click.echo(f"[DEBUG] Creating ETAPI client with server: {server[:10]}...", err=True)
    
    try:
        return ETAPI(server, token)
    except Exception as e:
        if debug:
            click.echo(f"[DEBUG] Failed to create ETAPI client: {e}", err=True)
        raise click.UsageError(
            "Failed to connect to Trilium. Please check your server URL and token."
        )

@notes.command()
@click.argument("query")
@click.pass_context
def search(ctx: click.Context, query: str) -> None:
    """Search for notes matching QUERY.
    
    Examples:
        tpy notes search "my search term"
    """
    try:
        ea = get_etapi(ctx)
        click.echo(f"Searching for: {click.style(query, fg='cyan')}")
        
        # Get search results using the direct query
        results = ea.search_note(query)
        
        # Extract notes from the response
        if isinstance(results, dict) and 'results' in results:
            notes = results['results']
        elif isinstance(results, list):
            notes = results
        else:
            click.echo("Error: Unexpected response format from server")
            if click.confirm('Show raw response?', default=False):
                click.echo(f"Raw response: {results}")
            return
            
        if not notes:
            click.echo("No matching notes found.")
            return
            
        click.echo(f"\nFound {click.style(str(len(notes)), fg='green')} notes:")
        
        for i, note in enumerate(notes, 1):
            if not isinstance(note, dict):
                click.echo(f"  {i}. [red]Invalid note format: {note}[/]")
                continue
                
            # Get note details with safe defaults
            note_id = note.get('noteId', 'N/A')
            title = note.get('title', 'Untitled')
            
            # Display note
            click.echo(f"  {i}. {click.style(title, fg='yellow')} ({note_id})")
            
            # Show content preview if available
            content = note.get('content')
            if content and isinstance(content, str):
                preview = content[:100].replace('\n', ' ')
                if len(content) > 100:
                    preview += "..."
                click.echo(f"     {preview}")
                
            click.echo()  # Add spacing between notes
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()

@notes.command()
@click.argument("title")
@click.option(
    "--parent-id", 
    "parent_id", 
    required=True, 
    help="Parent note ID (use 'root' for root level)",
    default="root"
)
@click.option(
    "--type", 
    "note_type", 
    default="text", 
    help="Note type (text, code, book, etc.)",
    show_default=True
)
@click.option(
    "--mime", 
    default="text/html", 
    help="MIME type (e.g., text/html, text/x-markdown, text/plain)",
    show_default=True
)
@click.option(
    "--content", 
    default="", 
    help="Note content. Use @filename to read from a file."
)
@click.option(
    "--dry-run", 
    is_flag=True,
    help="Show what would be created without actually creating"
)
@click.pass_context
def create(
    ctx: click.Context,
    title: str,
    parent_id: str,
    note_type: str,
    mime: str,
    content: str,
    dry_run: bool,
) -> None:
    """Create a new note in Trilium.
    
    Examples:
        # Create a simple note
        tpy notes create "My Note" --parent-id root --content "Hello, World!"
        
        # Create a note from file content
        tpy notes create "From File" --parent-id root --content @note.md
        
        # Create a code note
        tpy notes create "My Script" --type code --mime text/x-python --parent-id root --content @script.py
    """
    
    print("forcing dry run. Create is not safe yet.")
    dry_run = True

    try:
        # Handle file content if content starts with @
        if content.startswith('@'):
            file_path = Path(content[1:]).expanduser()
            if not file_path.exists():
                raise click.BadParameter(f"File not found: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not mime and file_path.suffix == '.md':
                    mime = 'text/x-markdown'
                elif not mime and file_path.suffix == '.py':
                    mime = 'text/x-python'
        
        # Show preview in dry-run mode
        if dry_run:
            click.echo(click.style("=== DRY RUN ===", fg='yellow', bold=True))
            click.echo(f"Title:       {click.style(title, fg='cyan')}")
            click.echo(f"Parent ID:   {click.style(parent_id, fg='cyan')}")
            click.echo(f"Type:        {click.style(note_type, fg='cyan')}")
            click.echo(f"MIME:        {click.style(mime, fg='cyan')}")
            click.echo(f"Content size: {click.style(str(len(content)), fg='cyan')} chars")
            if content:
                preview = content[:200].replace('\n', '\\n')
                if len(content) > 200:
                    preview += "..."
                click.echo(f"Preview:     {preview}")
            return
        
        # Create the note
        ea = get_etapi(ctx)
        note = ea.create_note(
            title=title,
            parentNoteId=parent_id,
            type=note_type,
            mime=mime,
            content=content,
        )
        
        click.echo(click.style("✓ ", fg='green', bold=True) + 
                 f"Created note: {click.style(note['noteId'], fg='cyan')}")
        click.echo(f"Title: {click.style(note.get('title', 'Untitled'), fg='yellow')}")
        
    except Exception as e:
        if ctx.obj.get('debug', False):
            raise
        click.echo(click.style("Error creating note: ", fg='red') + str(e), err=True)
        raise click.Abort()

@notes.command()
@click.option(
    "--root", 
    default="root", 
    help="Root note ID to start the tree from (default: root)",
    show_default=True
)
@click.option(
    "--max-depth", 
    type=int, 
    default=3,
    help="Maximum depth to display in the tree",
    show_default=True
)
@click.option(
    "--show-ids",
    is_flag=True,
    help="Show note IDs in the tree"
)
@click.pass_context
def tree(ctx: click.Context, root: str, max_depth: int, show_ids: bool) -> None:
    """Display notes in a tree structure.
    
    Examples:
        # Show full tree starting from root
        tpy notes tree
        
        # Show tree starting from a specific note
        tpy notes tree --root abc123xyz
        
        # Show deeper tree with note IDs
        tpy notes tree --max-depth 5 --show-ids
    """
    try:
        ea = get_etapi(ctx)
        
        def print_note(note_id: str, prefix: str = "", depth: int = 0) -> None:
            if depth > max_depth:
                return
                
            try:
                note = ea.get_note(note_id)
                title = note.get('title', 'Untitled')
                
                # Build the line with appropriate prefix and styling
                line_parts = []
                if prefix:
                    line_parts.append(click.style(prefix, fg='bright_black'))
                
                line_parts.append(click.style(title, fg='cyan' if depth == 0 else 'white'))
                
                if show_ids:
                    line_parts.append(click.style(f"({note_id})", fg='bright_black'))
                
                click.echo("".join(line_parts))
                
                # Get and display child notes
                children = ea.get_child_notes(note_id)
                for i, child in enumerate(children):
                    is_last = i == len(children) - 1
                    child_prefix = "    " + ("    " * depth)
                    
                    if is_last:
                        child_prefix += "└── "
                    else:
                        child_prefix += "├── "
                    
                    print_note(child['noteId'], child_prefix, depth + 1)
                    
            except Exception as e:
                if ctx.obj.get('debug', False):
                    click.echo(f"Error processing note {note_id}: {e}", err=True)
        
        click.echo(click.style(f"Note Tree (max depth: {max_depth}):", bold=True))
        print_note(root)
        
    except Exception as e:
        if ctx.obj.get('debug', False):
            raise
        click.echo(click.style("Error: ", fg='red') + str(e), err=True)
        raise click.Abort()


# Add more note commands here as needed
