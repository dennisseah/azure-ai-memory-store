import argparse
import os
import pathlib

import yaml

from docs.tex.models.document_config import DocumentConfig

CURRENT_DIR = pathlib.Path(os.path.dirname(__file__)) / "artifacts"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--format",
        choices=["pdf", "markdown"],
        default="pdf",
        help="Output format (default: pdf)",
    )
    args = parser.parse_args()

    with open(CURRENT_DIR / "doc.yaml") as f:
        cfg = DocumentConfig(**yaml.safe_load(f))

    if args.format == "markdown":
        md = cfg.to_markdown()
        output_path = f"{cfg.output_file}.md"
        with open(output_path, "w") as f:
            f.write(md)
        print(f"Markdown written to {output_path}")
    else:
        doc = cfg.execute()
        doc.generate_pdf(cfg.output_file, clean_tex=False)


if __name__ == "__main__":
    main()
