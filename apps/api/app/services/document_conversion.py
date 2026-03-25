from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
import logging
from pathlib import Path
import tempfile
import time
from typing import Any

from pypdf import PdfReader


LOGGER = logging.getLogger(__name__)
logging.getLogger("pypdf").setLevel(logging.ERROR)


@dataclass(slots=True)
class ConvertedTable:
    page_numbers: list[int] = field(default_factory=list)
    text: str = ""
    row_count: int = 0
    column_count: int = 0


@dataclass(slots=True)
class ConvertedPage:
    page_number: int
    text: str
    tables: list[ConvertedTable] = field(default_factory=list)


@dataclass(slots=True)
class ConvertedDocument:
    backend: str
    ocr_mode: str
    pages: list[ConvertedPage]
    diagnostics: dict[str, Any] = field(default_factory=dict)

    @property
    def page_texts(self) -> list[str]:
        return [page.text for page in self.pages]

    @property
    def table_count(self) -> int:
        return sum(len(page.tables) for page in self.pages)


def _table_to_markdown(rows: list[list[Any] | tuple[Any, ...]]) -> str:
    cleaned_rows: list[list[str]] = []
    for row in rows:
        cleaned = ["" if value is None else str(value).strip() for value in row]
        if any(cell for cell in cleaned):
            cleaned_rows.append(cleaned)
    if not cleaned_rows:
        return ""

    column_count = max(len(row) for row in cleaned_rows)
    normalized = [row + [""] * (column_count - len(row)) for row in cleaned_rows]
    header = normalized[0]
    separator = ["---"] * column_count
    body = normalized[1:] if len(normalized) > 1 else []
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _convert_with_pypdf(pdf_bytes: bytes) -> ConvertedDocument:
    started_at = time.perf_counter()
    reader = PdfReader(BytesIO(pdf_bytes))
    pages: list[ConvertedPage] = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").replace("\x00", " ").strip()
        pages.append(ConvertedPage(page_number=index, text=text))
    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
    return ConvertedDocument(
        backend="pypdf",
        ocr_mode="off",
        pages=pages,
        diagnostics={
            "page_count": len(pages),
            "text_characters": sum(len(page.text) for page in pages),
            "table_count": 0,
            "elapsed_ms": elapsed_ms,
        },
    )


def _convert_with_pdfplumber(pdf_bytes: bytes) -> ConvertedDocument:
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError("pdfplumber is not installed in this environment.") from exc

    started_at = time.perf_counter()
    pages: list[ConvertedPage] = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            base_text = (page.extract_text(layout=True) or "").replace("\x00", " ").strip()
            table_objects: list[ConvertedTable] = []
            table_markdowns: list[str] = []
            for raw_table in page.extract_tables() or []:
                markdown = _table_to_markdown(raw_table)
                if not markdown:
                    continue
                row_count = len([row for row in raw_table if row])
                column_count = max((len(row) for row in raw_table if row), default=0)
                table = ConvertedTable(
                    page_numbers=[index],
                    text=markdown,
                    row_count=row_count,
                    column_count=column_count,
                )
                table_objects.append(table)
                table_markdowns.append(markdown)
            page_text = "\n\n".join(part for part in [base_text, *table_markdowns] if part)
            pages.append(ConvertedPage(page_number=index, text=page_text, tables=table_objects))

    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
    return ConvertedDocument(
        backend="pdfplumber",
        ocr_mode="off",
        pages=pages,
        diagnostics={
            "page_count": len(pages),
            "text_characters": sum(len(page.text) for page in pages),
            "table_count": sum(len(page.tables) for page in pages),
            "elapsed_ms": elapsed_ms,
        },
    )


def _docling_table_markdown(table: Any, document: Any) -> str:
    export_markdown = getattr(table, "export_to_markdown", None)
    if callable(export_markdown):
        try:
            return str(export_markdown(doc=document) or "").strip()
        except TypeError:
            return str(export_markdown() or "").strip()
    return ""


def _docling_page_numbers(table: Any) -> list[int]:
    page_numbers: list[int] = []
    for item in list(getattr(table, "prov", None) or []):
        page_no = getattr(item, "page_no", None)
        if page_no is None and isinstance(item, dict):
            page_no = item.get("page_no")
        if isinstance(page_no, int) and page_no not in page_numbers:
            page_numbers.append(page_no)
    return page_numbers


def _convert_with_docling(pdf_bytes: bytes, *, ocr_mode: str) -> ConvertedDocument:
    started_at = time.perf_counter()
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError("Docling is not installed in this environment.") from exc

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_table_structure = True
    pipeline_options.do_ocr = ocr_mode != "off"
    pipeline_options.document_timeout = 180.0
    if ocr_mode != "off":
        pipeline_options.ocr_options = RapidOcrOptions(force_full_page_ocr=False)

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as handle:
        handle.write(pdf_bytes)
        temp_path = Path(handle.name)

    try:
        result = converter.convert(str(temp_path))
        document = result.document
        tables_by_page: dict[int, list[ConvertedTable]] = {}
        for table in list(getattr(document, "tables", None) or []):
            page_numbers = _docling_page_numbers(table)
            markdown = _docling_table_markdown(table, document)
            converted = ConvertedTable(
                page_numbers=page_numbers,
                text=markdown,
                row_count=markdown.count("\n") + 1 if markdown else 0,
                column_count=max((line.count("|") - 1 for line in markdown.splitlines()), default=0),
            )
            for page_number in page_numbers or [1]:
                tables_by_page.setdefault(page_number, []).append(converted)

        page_numbers = sorted(
            key
            for key in (
                list(getattr(document, "pages", {}).keys())
                if getattr(document, "pages", None)
                else []
            )
            if isinstance(key, int)
        )
        if not page_numbers:
            page_numbers = list(range(1, max(len(list(getattr(result, "pages", None) or [])), 1) + 1))

        pages: list[ConvertedPage] = []
        for page_number in page_numbers:
            page_text = ""
            export_markdown = getattr(document, "export_to_markdown", None)
            if callable(export_markdown):
                try:
                    page_text = str(
                        export_markdown(
                            page_no=page_number,
                            page_break_placeholder="",
                            compact_tables=False,
                        )
                        or ""
                    ).strip()
                except TypeError:
                    page_text = str(export_markdown() or "").strip()
            page_tables = tables_by_page.get(page_number, [])
            if page_tables and all(table.text not in page_text for table in page_tables):
                page_text = "\n\n".join([page_text, *[table.text for table in page_tables if table.text]]).strip()
            pages.append(
                ConvertedPage(
                    page_number=page_number,
                    text=page_text,
                    tables=page_tables,
                )
            )

        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return ConvertedDocument(
            backend="docling" if ocr_mode == "off" else "docling_ocr",
            ocr_mode=ocr_mode,
            pages=pages,
            diagnostics={
                "page_count": len(pages),
                "text_characters": sum(len(page.text) for page in pages),
                "table_count": sum(len(page.tables) for page in pages),
                "elapsed_ms": elapsed_ms,
            },
        )
    finally:
        temp_path.unlink(missing_ok=True)


def convert_pdf_document(
    pdf_bytes: bytes,
    *,
    backend: str,
    ocr_mode: str = "off",
) -> ConvertedDocument:
    normalized_backend = backend.strip().lower()
    if normalized_backend == "pypdf":
        return _convert_with_pypdf(pdf_bytes)
    if normalized_backend == "pdfplumber":
        return _convert_with_pdfplumber(pdf_bytes)
    if normalized_backend == "docling":
        return _convert_with_docling(pdf_bytes, ocr_mode="off")
    if normalized_backend == "docling_ocr":
        return _convert_with_docling(pdf_bytes, ocr_mode=ocr_mode if ocr_mode != "off" else "auto")
    raise ValueError(f"Unsupported document conversion backend: {backend}")
