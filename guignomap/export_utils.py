from io import BytesIO
from typing import Optional
import pandas as pd

def df_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Export") -> bytes:
    """
    Serialize a DataFrame to an in-memory .xlsx (openpyxl). Returns raw bytes.
    Safe on Windows (no temp files).
    """
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return bio.getvalue()

def df_to_pdf_bytes(df: pd.DataFrame, title: str = "Export") -> Optional[bytes]:
    """
    Serialize a DataFrame to an in-memory PDF using reportlab.
    - Table autosize with simple styling
    - Falls back to None if reportlab is not available
    """
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
    except Exception:
        return None

    bio = BytesIO()
    doc = SimpleDocTemplate(bio, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
    story = []

    styles = getSampleStyleSheet()
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 12))

    # Build table data
    data = [list(df.columns)] + df.astype(str).values.tolist()

    tbl = Table(data, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#F0F0F0")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.HexColor("#000000")),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#CCCCCC")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#FAFAFA")]),
    ]))
    story.append(tbl)

    doc.build(story)
    return bio.getvalue()
