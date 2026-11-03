import io

import pandas as pd
import pytest

from app.core.importer import ImportError_, read_table
from app.core.mapping import MappingError, apply_mapping, columns_signature, suggest_mapping
from app.schemas import PERSONNEL


def test_suggest_mapping_recognises_french_and_english_headers():
    columns = ["Mat.", "Nom et prénom", "Gender", "Date d'embauche", "Date de départ",
               "Direction", "CSP", "Hire location"]
    mapping = suggest_mapping(columns, PERSONNEL)
    assert mapping["matricule"] == "Mat."
    assert mapping["sexe"] == "Gender"
    assert mapping["date_entree"] == "Date d'embauche"
    assert mapping["date_sortie"] == "Date de départ"
    assert mapping["service"] == "Direction"
    assert mapping["categorie"] == "CSP"


def test_each_column_is_used_once():
    mapping = suggest_mapping(["Matricule", "ID", "Date entrée", "Date"], PERSONNEL)
    used = [c for c in mapping.values() if c]
    assert len(used) == len(set(used))


def test_signature_ignores_order_and_accents():
    assert columns_signature(["Date d'entrée", "Matricule"]) == \
        columns_signature(["matricule", "date d entree"])


def _frame(rows):
    return pd.DataFrame(rows, columns=["id", "entree", "sortie", "genre", "naissance"])


MAPPING = {"matricule": "id", "date_entree": "entree", "date_sortie": "sortie",
           "sexe": "genre", "date_naissance": "naissance"}


def test_types_are_converted_and_bad_rows_reported():
    frame = _frame([
        ["A1", "15/03/2020", "", "Femme", 30000],          # date Excel en nombre
        ["A2", "2019-01-07", "2024-02-01", "M", "1990-05-01"],
        ["A3", "pas une date", "", "H", ""],                 # entrée invalide → rejet
        ["", "2021-01-01", "", "F", ""],                     # matricule vide → rejet
        ["A5", "2022-06-01", "2021-01-01", "F", ""],         # sortie avant entrée → rejet
        ["A6", "2022-06-01", "", "inconnu", ""],             # sexe invalide → ignoré
    ])
    clean, report = apply_mapping(frame, PERSONNEL, MAPPING)
    assert report.rows_accepted == 3
    assert report.rows_rejected == 3
    assert clean.loc[0, "date_entree"] == pd.Timestamp("2020-03-15")
    assert clean.loc[0, "date_naissance"] == pd.Timestamp("1982-02-18")  # série Excel 30000
    assert list(clean["sexe"].fillna("?")) == ["F", "H", "?"]
    rows = {(e["row"], e["field"]) for e in report.errors}
    assert (4, "date_entree") in rows        # ligne 4 dans Excel (en-tête en ligne 1)
    assert (5, "matricule") in rows
    assert (6, "date_sortie") in rows


def test_missing_required_mapping_raises():
    with pytest.raises(MappingError):
        apply_mapping(_frame([["A1", "2020-01-01", "", "F", ""]]), PERSONNEL,
                      {"matricule": "id"})


def test_duplicate_matricules_keep_last_line():
    frame = _frame([["A1", "2020-01-01", "", "F", ""], ["A1", "2021-01-01", "", "F", ""]])
    clean, report = apply_mapping(frame, PERSONNEL, MAPPING)
    assert len(clean) == 1
    assert clean.loc[0, "date_entree"] == pd.Timestamp("2021-01-01")
    assert report.warnings


def test_header_row_is_detected_below_a_title():
    buffer = io.BytesIO()
    data = pd.DataFrame({"Matricule": ["A1", "A2"], "Date entrée": ["2020-01-01", "2021-01-01"]})
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        data.to_excel(writer, index=False, startrow=3)
        writer.sheets["Sheet1"]["A1"] = "Export du personnel"
    table = read_table(buffer.getvalue(), "export.xlsx")
    assert list(table.frame.columns) == ["Matricule", "Date entrée"]
    assert len(table.frame) == 2


def test_csv_semicolon_and_cp1252():
    content = "Matricule;Date d'entrée\nA1;01/02/2020\nA2;03/04/2021\n".encode("cp1252")
    table = read_table(content, "export.csv")
    assert list(table.frame.columns) == ["Matricule", "Date d'entrée"]


@pytest.mark.parametrize("name,content,message", [
    ("data.pdf", b"%PDF", "Format"),
    ("data.xlsx", b"not a zip", "Excel"),
    ("data.csv", b"", "vide"),
])
def test_rejected_files(name, content, message):
    with pytest.raises(ImportError_, match=message):
        read_table(content, name)


def test_size_limit():
    with pytest.raises(ImportError_, match="volumineux"):
        read_table(b"a;b\n" * 1000, "big.csv", max_bytes=100)
