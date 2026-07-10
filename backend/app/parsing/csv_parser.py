import io

from app.models.enums import SourceType
from app.parsing.base import ParsedDocument, TextBlock, register

# Group N rows per text block so each chunk stays table-aware but bounded.
_ROWS_PER_BLOCK = 25


@register(SourceType.csv)
class CsvParser:
    def parse(self, *, data: bytes | None, url: str | None, filename: str) -> ParsedDocument:
        import pandas as pd

        if data is None:
            raise ValueError("CSV parser requires file bytes")
        df = pd.read_csv(io.BytesIO(data))
        headers = list(df.columns)
        blocks: list[TextBlock] = []
        for start in range(0, len(df), _ROWS_PER_BLOCK):
            window = df.iloc[start : start + _ROWS_PER_BLOCK]
            lines = []
            for _, row in window.iterrows():
                cells = [f"{h}: {row[h]}" for h in headers]
                lines.append("; ".join(cells))
            blocks.append(TextBlock(text="\n".join(lines)))
        return ParsedDocument(
            blocks=blocks, meta={"parser": "pandas", "columns": headers, "rows": len(df)}
        )
