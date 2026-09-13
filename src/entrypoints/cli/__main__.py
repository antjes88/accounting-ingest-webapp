import click
from dotenv import load_dotenv
import warnings

from src.entrypoints.cli.create_transaction import (
    create_transaction,
    create_transactions,
)

warnings.filterwarnings("ignore", category=UserWarning)


@click.group()
def cli():
    pass


cli.add_command(create_transaction)
cli.add_command(create_transactions)

if __name__ == "__main__":
    load_dotenv(dotenv_path="./.env", override=True)
    cli()
