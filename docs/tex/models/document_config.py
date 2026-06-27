import yaml
from pydantic import BaseModel
from pylatex import Command, Document, NoEscape

from docs import ARTIFACT_DIR
from docs.tex import normalize_text
from docs.tex.models.document_content import DocumentContent


class GeometryOptions(BaseModel):
    top: str
    bottom: str
    left: str
    right: str


class RevisionEntry(BaseModel):
    version: str
    date: str
    description: list[str]

    @classmethod
    def render(cls, doc: Document, revisions: list["RevisionEntry"]) -> None:
        if revisions:
            doc.append(NoEscape(r"\vspace{1em}"))
            doc.append(NoEscape("\n"))
            doc.append(NoEscape(r"\begin{center}\textit{Revision History}\end{center}"))
            doc.append(NoEscape("\n"))
            doc.append(NoEscape(r"\begin{center}"))
            doc.append(NoEscape(r"\small"))
            doc.append(NoEscape(r"\renewcommand{\arraystretch}{1.75}"))
            doc.append(NoEscape(r"\begin{tabular}{@{}rll@{}}"))
            doc.append(
                NoEscape(r"\textit{Version} & \textit{Date} & \textit{Description} \\")
            )
            doc.append(NoEscape(r"\hline"))
            for rev in revisions:
                doc.append(
                    NoEscape(f"{rev.version} & {rev.date} & {rev.description[0]} \\\\")
                )
                for desc in rev.description[1:]:
                    doc.append(NoEscape(f"& & {desc} \\\\"))
            doc.append(NoEscape(r"\end{tabular}"))
            doc.append(NoEscape(r"\end{center}"))
            doc.append(NoEscape("\n"))
            doc.append(NoEscape(r"\newpage"))


class DocumentConfig(BaseModel):
    title: str
    author: list[str]
    affiliation: str
    email_domain: str | None = None
    output_file: str
    geometry_options: GeometryOptions
    preamble: list[str]
    content: list[str]
    abstract: str
    revision_history: list[RevisionEntry] = []

    @property
    def version(self) -> str:
        return self.revision_history[-1].version if self.revision_history else "0.0.0"

    def create_page_title(self, doc: Document) -> None:
        doc.preamble.append(Command("title", self.title))
        # Format authors: name (email)
        formatted_authors = []
        for a in self.author:
            # If author contains a pipe, split into name|alias
            if "|" in a:
                name, alias = a.split("|", 1)
                email = alias.strip()
                if self.email_domain:
                    email += "@" + self.email_domain
                formatted_authors.append(
                    r"\textit{" + name.strip() + r"} (" + email + ")"
                )
            else:
                formatted_authors.append(r"\textit{" + a + "}")

        authors = r" \and ".join(formatted_authors)
        doc.preamble.append(Command("author", NoEscape(authors)))

        # Include affiliation in the date field so it appears centered below authors
        date_content = (
            r"{\large \textit{"
            + self.affiliation
            + r"}}\\[2em]\textit{\today}\\[0.5em]\textit{Version "
            + self.version
            + "}"
        )
        doc.preamble.append(
            Command(
                "date",
                NoEscape(date_content),
            )
        )
        doc.append(NoEscape(r"\maketitle"))

    def execute(self) -> Document:
        doc = Document(
            documentclass="extarticle",
            document_options=["9pt"],
            geometry_options={
                "top": self.geometry_options.top,
                "bottom": self.geometry_options.bottom,
                "left": self.geometry_options.left,
                "right": self.geometry_options.right,
            },
        )
        for pre in self.preamble:
            doc.preamble.append(NoEscape(pre))

        # Set header left to document title (italic)
        doc.preamble.append(
            NoEscape(r"\fancyhead[L]{\small \textit{" + self.title + "}}")
        )
        self.create_page_title(doc)

        doc.append(NoEscape(r"\thispagestyle{empty}"))

        doc.append(NoEscape(r"\begin{abstract}\itshape"))
        doc.append(NoEscape(normalize_text(self.abstract.strip())))
        doc.append(NoEscape(r"\end{abstract}"))

        RevisionEntry.render(doc, self.revision_history)

        doc.append(NoEscape(r"\newpage"))
        # doc.append(NoEscape(r"\tableofcontents"))
        # doc.append(NoEscape(r"\newpage"))

        for cnt in self.content:
            if cnt == "__appendix__":
                doc.append(NoEscape(r"\newpage"))
                doc.append(NoEscape(r"\appendix"))
                continue
            with open(ARTIFACT_DIR / cnt) as f:
                content = DocumentContent.from_dic(**yaml.safe_load(f))
                content.execute(doc)

        return doc

    def to_markdown(self) -> str:
        lines: list[str] = []
        lines.append(f"# {self.title}")
        lines.append("")
        authors = ", ".join(
            a.split("|")[0].strip() if "|" in a else a for a in self.author
        )
        lines.append(f"*{authors} \u2014 {self.affiliation}*")
        lines.append("")
        if self.revision_history:
            lines.append(f"*Version {self.version}*")
            lines.append("")
        lines.append("## Abstract")
        lines.append("")
        lines.append(self.abstract.strip())
        lines.append("")
        lines.append("---")
        lines.append("")

        is_appendix = False
        for cnt in self.content:
            if cnt == "__appendix__" and not is_appendix:
                is_appendix = True
                lines.append("---")
                lines.append("")
                lines.append("# Appendix")
                lines.append("")
                continue
            with open(ARTIFACT_DIR / cnt) as f:
                content = DocumentContent.from_dic(**yaml.safe_load(f))
                lines.append(content.to_markdown())

        return "\n".join(lines)
