import json
from pathlib import Path

import click

from .ingest import ingest_file


@click.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option("--preview", type=int, default=400, show_default=True, help="Print first N characters")
@click.option("--json", "as_json", is_flag=True, help="Output full JSON instead of preview")
def main(file_path: Path, preview: int, as_json: bool) -> None:
	"""Parse a document and show a quick preview or JSON."""
	doc = ingest_file(file_path)
	if as_json:
		click.echo(json.dumps({"text": doc.text, "meta": doc.meta}, ensure_ascii=False))
		return
	click.echo(f"File: {doc.meta.get('filename')}")
	click.echo(f"Type: {doc.meta.get('suffix')} (parser={doc.meta.get('parser')})")
	if "num_pages" in doc.meta:
		click.echo(f"Pages: {doc.meta['num_pages']}")
	text = doc.text
	preview_text = text[:preview]
	click.echo("--- Preview ---")
	click.echo(preview_text)
	if len(text) > preview:
		click.echo("\n... (truncated) ...")


if __name__ == "__main__":
	main()
