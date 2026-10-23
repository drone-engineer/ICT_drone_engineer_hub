from io import BytesIO

import pandas as pd

COLS = ["일시", "질문", "경로", "페르소나", "계통", "결선주의", "답변요약"]


def to_excel_bytes(log):
    df = pd.DataFrame(log, columns=COLS)
    sheets = {
        "전체이력": df,
        "결선주의질의": df[df["결선주의"] == True],
        "비교검증질의": df[df["경로"] == "compare"],
    }
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, d in sheets.items():
            d.to_excel(xw, sheet_name=name, index=False)
            ws = xw.sheets[name]
            for col, width in zip("ABCDEFG", [20, 50, 10, 14, 24, 10, 60]):
                ws.column_dimensions[col].width = width
    return buf.getvalue()
