"""Le rapport d'import doit citer le numéro de ligne réellement affiché dans Excel / le CSV,
même quand le fichier contient des lignes vides (avant l'en-tête ou entre les données)."""

import io

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


def _errors(table):
    _, report = apply_mapping(table.frame, PERSONNEL, MAPPING, table.header_row,
                              table.excel_rows)
    return report.errors


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
