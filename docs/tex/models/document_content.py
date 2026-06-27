import re

import yaml
from pydantic import BaseModel
from pylatex import Document, NoEscape

from docs import ARTIFACT_DIR
from docs.tex import normalize_text


def _md_clean(text: str) -> str:
    """Strip LaTeX-only markup from text for markdown output."""
    # \$ -> $
    text = text.replace(r"\$", "$")
    # ~ (non-breaking space) -> regular space
    text = text.replace("~", " ")
    # --- -> em-dash
    text = text.replace("---", "\u2014")
    # -- -> en-dash
    text = text.replace("--", "\u2013")
    # ``text'' -> "text"
    text = re.sub(r"``(.+?)''", r'"\1"', text)
    # \ref{...} -> [ref]
    text = re.sub(r"\\ref\{([^}]+)\}", r"[\1]", text)
    # \$\ref{...} -> [ref]
    text = re.sub(r"\\\$\\ref\{([^}]+)\}", r"[\1]", text)
    # \subsection*{...} -> just the text (used inline in paragraph)
    text = re.sub(r"\\subsection\*\{(.+?)\}", r"\1", text)
    # $\sim$ -> ~
    text = text.replace(r"$\sim$", "~")
    # \% -> %
    text = text.replace(r"\\%", "%")
    text = text.replace(r"\%", "%")
    # Collapse multiple spaces
    text = re.sub(r"  +", " ", text)
    return text.strip()


class TextContent(BaseModel):
    text: str
    section: str | None = None
    subsection: str | None = None
    subsubsection: str | None = None
    label: str | None = None
    newline: bool = True

    def to_markdown(self) -> str:
        lines: list[str] = []
        if self.section:
            lines.append(f"## {_md_clean(self.section)}")
            lines.append("")
        if self.subsection:
            lines.append(f"### {_md_clean(self.subsection)}")
            lines.append("")
        if self.subsubsection:
            lines.append(f"#### {_md_clean(self.subsubsection)}")
            lines.append("")
        lines.append(_md_clean(self.text))
        lines.append("")
        return "\n".join(lines)

    def execute(self, doc: Document) -> None:
        if self.section:
            doc.append(NoEscape(r"\section{" + normalize_text(self.section) + "}"))
        if self.subsection:
            doc.append(
                NoEscape(r"\subsection{" + normalize_text(self.subsection) + "}")
            )
        if self.subsubsection:
            doc.append(
                NoEscape(r"\subsubsection{" + normalize_text(self.subsubsection) + "}")
            )
        if self.label:
            doc.append(NoEscape(r"\label{" + self.label + "}"))
        doc.append(NoEscape(normalize_text(self.text)))
        if self.newline:
            doc.append(NoEscape(r"\par\vspace{\baselineskip}"))


class VerbatimContent(BaseModel):
    text: str
    newline: bool = True
    font_size: str = "small"

    def to_markdown(self) -> str:
        return f"```\n{self.text}\n```\n"

    def execute(self, doc: Document) -> None:
        verbatim_block = (
            "{\\" + self.font_size + "\n"
            r"\begin{verbatim}" + "\n" + self.text + "\n" + r"\end{verbatim}}"
        )
        doc.append(NoEscape(verbatim_block))
        if self.newline:
            doc.append(NoEscape(r"\vspace{\baselineskip}"))


class ItemizeContent(BaseModel):
    items: list[str]
    newline: bool = True

    def to_markdown(self) -> str:
        lines = [f"- {_md_clean(item)}" for item in self.items]
        lines.append("")
        return "\n".join(lines)

    def execute(self, doc: Document) -> None:
        doc.append(NoEscape(r"\begin{itemize}[topsep=0pt]"))
        for item in self.items:
            doc.append(NoEscape(r"\item " + normalize_text(item)))
        doc.append(NoEscape(r"\end{itemize}"))
        if self.newline:
            doc.append(NoEscape(r"\vspace{\baselineskip}"))


class EnumerateContent(BaseModel):
    items: list[str]
    newline: bool = True

    def to_markdown(self) -> str:
        lines = [f"{i}. {_md_clean(item)}" for i, item in enumerate(self.items, 1)]
        lines.append("")
        return "\n".join(lines)

    def execute(self, doc: Document) -> None:
        doc.append(NoEscape(r"\begin{enumerate}[topsep=0pt]"))
        for item in self.items:
            doc.append(NoEscape(r"\item " + normalize_text(item)))
        doc.append(NoEscape(r"\end{enumerate}"))
        if self.newline:
            doc.append(NoEscape(r"\vspace{\baselineskip}"))


class TableContent(BaseModel):
    headers: list[str]
    rows: list[list[str]]
    caption: str | None = None
    label: str | None = None
    column_spec: str | None = None
    subsection: str | None = None
    subsubsection: str | None = None
    array_stretch: float | None = None
    tab_col_sep: str | None = None
    newline: bool = True

    def to_markdown(self) -> str:
        lines: list[str] = []
        if self.subsection:
            lines.append(f"### {_md_clean(self.subsection)}")
            lines.append("")
        if self.subsubsection:
            lines.append(f"#### {_md_clean(self.subsubsection)}")
            lines.append("")
        hdr = [_md_clean(h) for h in self.headers]
        lines.append("| " + " | ".join(hdr) + " |")
        lines.append("| " + " | ".join(["---"] * len(hdr)) + " |")
        for row in self.rows:
            cells = [_md_clean(c) for c in row]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
        if self.caption:
            lines.append(f"*{_md_clean(self.caption)}*")
            lines.append("")
        return "\n".join(lines)

    def execute(self, doc: Document) -> None:
        if self.subsection:
            doc.append(
                NoEscape(r"\subsection{" + normalize_text(self.subsection) + "}")
            )
        if self.subsubsection:
            doc.append(
                NoEscape(r"\subsubsection{" + normalize_text(self.subsubsection) + "}")
            )
        n = len(self.headers)
        spec = self.column_spec or ("|" + "|".join(["l"] * n) + "|")
        doc.append(NoEscape(r"\begin{table}[htbp]"))
        doc.append(NoEscape(r"\centering"))
        if self.array_stretch:
            doc.append(
                NoEscape(
                    r"\renewcommand{\arraystretch}{" + str(self.array_stretch) + "}"
                )
            )
        if self.tab_col_sep:
            doc.append(NoEscape(r"\setlength{\tabcolsep}{" + self.tab_col_sep + "}"))
        doc.append(NoEscape(r"\begin{tabular}{" + spec + "}"))
        doc.append(NoEscape(r"\hline"))
        header_line = " & ".join(
            r"\textit{" + normalize_text(h) + "}" for h in self.headers
        )
        doc.append(NoEscape(header_line + r" \\"))
        doc.append(NoEscape(r"\hline"))
        for row in self.rows:
            cells = " & ".join(normalize_text(c) for c in row)
            doc.append(NoEscape(cells + r" \\"))
            doc.append(NoEscape(r"\hline"))
        doc.append(NoEscape(r"\end{tabular}"))
        if self.caption:
            doc.append(NoEscape(r"\caption{" + normalize_text(self.caption) + "}"))
        if self.label:
            doc.append(NoEscape(r"\label{" + self.label + "}"))
        doc.append(NoEscape(r"\end{table}"))
        if self.newline:
            doc.append(NoEscape(r"\vspace{\baselineskip}"))


class ImageContent(BaseModel):
    src: str
    caption: str
    label: str | None = None
    width: str = "0.8\\textwidth"
    placement: str = "htbp"  # h=here, t=top, b=bottom, p=page; use "H" for exact

    def to_markdown(self) -> str:
        return f"![{_md_clean(self.caption)}]({self.src})\n"

    def execute(self, doc: Document) -> None:
        doc.append(NoEscape(r"\begin{figure}[" + self.placement + "]"))
        doc.append(
            NoEscape(
                r"\centering" + f"\n\\includegraphics[width={self.width}]{{{self.src}}}"
            )
        )
        doc.append(NoEscape(r"\caption{" + normalize_text(self.caption) + "}"))
        if self.label:
            doc.append(NoEscape(r"\label{" + self.label + "}"))
        doc.append(NoEscape(r"\end{figure}"))
        doc.append(NoEscape(r"\vspace{\baselineskip}"))


class EmbededContent(BaseModel):
    src: str

    def to_markdown(self) -> str:
        with open(ARTIFACT_DIR / self.src) as f:
            raw = yaml.safe_load(f)
            return DocumentContent.from_dic(**raw).to_markdown()

    def execute(self, doc: Document) -> None:
        with open(ARTIFACT_DIR / self.src) as f:
            raw = yaml.safe_load(f)
            DocumentContent.from_dic(**raw).execute(doc)


class DocumentContent(BaseModel):
    title: str | None = None
    label: str | None = None
    content: list[
        TextContent
        | ItemizeContent
        | EnumerateContent
        | TableContent
        | ImageContent
        | VerbatimContent
        | EmbededContent
    ] = []
    newpage: bool = False

    def to_markdown(self) -> str:
        lines: list[str] = []
        if self.title:
            lines.append(f"## {_md_clean(self.title)}")
            lines.append("")
        for cnt in self.content:
            lines.append(cnt.to_markdown())
        return "\n".join(lines)

    def execute(self, doc: Document) -> None:
        if self.title:
            doc.append(NoEscape(r"\section{" + normalize_text(self.title) + "}"))
        if self.label:
            doc.append(NoEscape(r"\label{" + self.label + "}"))
        for cnt in self.content:
            cnt.execute(doc)

        if self.newpage:
            doc.append(NoEscape(r"\newpage"))

    @classmethod
    def from_dic(cls, **data) -> "DocumentContent":
        content = data.get("content", [])
        del data["content"]
        doc = cls(**data)

        for c in content:
            type = c.pop("type")
            if type == "embed":
                doc.content.append(EmbededContent(**c))
            elif type == "paragraph":
                doc.content.append(TextContent(**c))
            elif type == "itemize":
                doc.content.append(ItemizeContent(**c))
            elif type == "enumerate":
                doc.content.append(EnumerateContent(**c))
            elif type == "table":
                doc.content.append(TableContent(**c))
            elif type == "image":
                doc.content.append(ImageContent(**c))
            elif type == "code":
                doc.content.append(VerbatimContent(**c))
        return doc
