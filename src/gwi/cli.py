import asyncio
import typer
from rich import print
from rich.console import Console
from pathlib import Path
from typing import Optional

from .ingester import GridWorksIngester
from .config import IngesterSettings

app = typer.Typer(
    help="GridWorks Ingester - Telemetry data persistence service",
    no_args_is_help=True
)
console = Console()

@app.command()
def run(
    env_file: Optional[Path] = typer.Option(
        None,
        "--env-file", "-e",
        help="Path to .env file"
    ),
    debug: bool = typer.Option(
        False,
        "--debug", "-d",
        help="Enable debug logging"
    )
):
    """Run the GridWorks Ingester"""
    console.print("[bold green]Starting GridWorks Ingester...[/bold green]")
    
    # Load settings
    settings = IngesterSettings()
    if env_file:
        settings = IngesterSettings(_env_file=env_file)
    
    if debug:
        settings.log_level = "DEBUG"
    
    # Run ingester
    ingester = GridWorksIngester(settings)
    try:
        asyncio.run(ingester.run())
    except KeyboardInterrupt:
        console.print("\n[bold red]Shutting down...[/bold red]")

@app.command()
def config():
    """Show current configuration"""
    settings = IngesterSettings()
    console.print(settings.model_dump_json(indent=2))

@app.command()
def init():
    """Initialize configuration files"""
    env_file = Path(".env")
    if env_file.exists():
        console.print("[yellow]Warning: .env file already exists[/yellow]")
        if not typer.confirm("Overwrite?"):
            return
    
    env_content = """# GridWorks Ingester Configuration

# MQTT Settings
GWI_MQTT_BROKER_HOST=localhost
GWI_MQTT_BROKER_PORT=1883
GWI_MQTT_USERNAME=mep_user
GWI_MQTT_PASSWORD=your_password_here

# PostgreSQL Settings
GWI_POSTGRES_ENABLED=true
GWI_POSTGRES_HOST=localhost
GWI_POSTGRES_DATABASE=gridworks_telemetry
GWI_POSTGRES_USER=gridworks
GWI_POSTGRES_PASSWORD=your_password_here

# S3 Settings
GWI_S3_ENABLED=false
GWI_S3_BUCKET=gridworks-telemetry
GWI_AWS_ACCESS_KEY_ID=your_key_here
GWI_AWS_SECRET_ACCESS_KEY=your_secret_here

# Local Storage
GWI_LOCAL_STORAGE_ENABLED=true
GWI_LOCAL_STORAGE_PATH=/tmp/gridworks/data
"""
    
    env_file.write_text(env_content)
    console.print(f"[green]Created .env file at {env_file.absolute()}[/green]")

if __name__ == "__main__":
    app()