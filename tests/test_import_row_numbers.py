"""Le rapport d'import doit citer le numéro de ligne réellement affiché dans Excel / le CSV,
même quand le fichier contient des lignes vides (avant l'en-tête ou entre les données)."""

import io

import pytest
from openpyxl import Workbook

from app.core.importer import read_table
from app.core.mapping import apply_mapping
from app.schemas import PERSONNEL

HEADER = ["Matricule", "Date d'embauche", "Date de départ", "Genre"]
MAPPING = {"matricule": "Matricule", "date_entree": "Date d'embauche",
           "date_sortie": "Date de départ", "sexe": "Genre"}


def _xlsx(cells):
    """`cells` : {numéro de ligne Excel: liste de valeurs}."""
    wb = Workbook()
    ws = wb.active
    for row, values in cells.items():
        for col, value in enumerate(values, start=1):
            ws.cell(row=row, column=col, value=value)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def _report(table):
    _, report = apply_mapping(table.frame, PERSONNEL, MAPPING, table.header_row,
                              table.excel_rows, table.multiline_cells)
    return report


def _errors(table):
    return _report(table).errors


def test_error_row_is_exact_with_blank_rows_before_and_between_data():
    content = _xlsx({
        1: ["Export du personnel"],
        # ligne 2 vide
        3: HEADER,
        4: ["A1", "2020-01-01", None, "F"],
        # lignes 5 et 6 vides
        7: ["A2", "2021-05-01", "2019-01-01", "H"],   # sortie avant entrée : ligne Excel 7
        8: ["A3", "2022-02-01", None, "F"],
        # ligne 9 vide
        10: ["A4", "pas une date", None, "F"],         # entrée invalide : ligne Excel 10
    })
    table = read_table(content, "export.xlsx")
    assert table.header_row == 2
    rows = sorted(e["row"] for e in _errors(table))
    assert rows == [7, 10]


def test_error_row_is_exact_in_a_compact_sheet():
    content = _xlsx({1: HEADER, 2: ["A1", "2020-01-01", None, "F"],
                     3: ["A2", "2021-05-01", "2019-01-01", "H"]})
    assert [e["row"] for e in _errors(read_table(content, "export.xlsx"))] == [3]


def test_error_row_is_exact_in_csv_with_blank_lines():
    text = ("Export\n\nMatricule;Date d'embauche;Date de départ;Genre\n"
            "A1;2020-01-01;;F\n\n"
            "A2;2021-05-01;2019-01-01;H\n")
    table = read_table(text.encode("utf-8"), "export.csv")
    assert [e["row"] for e in _errors(table)] == [6]


def test_every_error_code_has_a_label_in_both_languages():
    import json
    from pathlib import Path

    from app.core.mapping import ERROR_CODES

    locales = Path(__file__).resolve().parent.parent / "locales"
    for lang in ("fr", "en"):
        strings = json.loads((locales / f"{lang}.json").read_text(encoding="utf-8"))
        for code in ERROR_CODES:
            assert strings.get(f"import.err.{code}"), (lang, code)


def test_errors_carry_a_known_code():
    from app.core.mapping import ERROR_CODES

    content = _xlsx({1: HEADER, 2: ["A1", "2020-01-01", None, "F"],
                     3: ["A2", "2021-05-01", "2019-01-01", "H"]})
    errors = _errors(read_table(content, "export.xlsx"))
    assert errors and all(e["code"] in ERROR_CODES for e in errors)


# --- Même erreur, mêmes positions de lignes vides : CSV et Excel doivent citer la même ligne ---

BAD = ["A2", "2021-05-01", "2019-01-01", "H"]          # sortie avant entrée : ligne rejetée


def _same_file_in_both_formats(blank_before, blank_between, title):
    """Construit le même contenu en CSV et en .xlsx ; renvoie (csv, xlsx, ligne fautive)."""
    lines = (["Export du personnel"] if title else []) + [""] * blank_before
    lines += [";".join(HEADER), "A1;2020-01-01;;F"] + [""] * blank_between + [";".join(BAD)]
    cells = {i: [v or None for v in line.split(";")]
             for i, line in enumerate(lines, start=1) if line}
    return ("\n".join(lines) + "\n").encode("utf-8"), _xlsx(cells), len(lines)


@pytest.mark.parametrize("title", [False, True])
@pytest.mark.parametrize("blank_between", [0, 1, 3])
@pytest.mark.parametrize("blank_before", [0, 1, 3])
def test_csv_and_xlsx_report_the_same_row(blank_before, blank_between, title):
    csv_bytes, xlsx_bytes, bad_row = _same_file_in_both_formats(blank_before, blank_between, title)
    csv_rows = [e["row"] for e in _errors(read_table(csv_bytes, "export.csv"))]
    xlsx_rows = [e["row"] for e in _errors(read_table(xlsx_bytes, "export.xlsx"))]
    assert csv_rows == xlsx_rows == [bad_row]


# --- Cellule sur plusieurs lignes : le numéro suit Excel, et le rapport le signale (CSV) ---

MULTILINE_CSV = ("Matricule;Date d'embauche;Date de départ;Genre\n"
                 'A1;"2020-01-01";;F\n'
                 'A3;2020-03-01;;"F"\n'
                 'A4;"2020-04-01\n";;F\n'                    # retour à la ligne dans une cellule
                 "A2;2021-05-01;2019-01-01;H\n")              # ligne Excel 5, ligne 6 du texte


def test_multiline_csv_cell_counts_as_one_excel_row():
    table = read_table(MULTILINE_CSV.encode("utf-8"), "export.csv")
    assert table.multiline_cells == 1
    assert [e["row"] for e in _errors(table)] == [5]


def test_multiline_csv_cell_adds_a_notice():
    report = _report(read_table(MULTILINE_CSV.encode("utf-8"), "export.csv"))
    assert [(n["code"], n["n"]) for n in report.notices] == [("csv_multiline", 1)]
    assert report.as_dict()["notices"] and report.as_dict()["warnings"]


def test_multiline_xlsx_cell_has_same_row_and_no_notice():
    content = _xlsx({1: HEADER, 2: ["A1", "2020-01-01", None, "F"],
                     3: ["A3", "2020-03-01", None, "F"], 4: ["A4", "2020-04-01", None, "F\n"],
                     5: BAD})
    table = read_table(content, "export.xlsx")
    assert table.multiline_cells == 0
    report = _report(table)
    assert [e["row"] for e in report.errors] == [5]
    assert report.notices == []


def test_csv_without_line_breaks_in_cells_has_no_notice():
    csv_bytes, _, _ = _same_file_in_both_formats(0, 0, False)
    table = read_table(csv_bytes, "export.csv")
    assert table.multiline_cells == 0 and _report(table).notices == []


def test_every_notice_code_has_a_label_in_both_languages():
    import json
    from pathlib import Path

    from app.core.mapping import NOTICE_CODES

    locales = Path(__file__).resolve().parent.parent / "locales"
    for lang in ("fr", "en"):
        strings = json.loads((locales / f"{lang}.json").read_text(encoding="utf-8"))
        for code in NOTICE_CODES:
            assert "{n}" in strings.get(f"import.notice.{code}", ""), (lang, code)
