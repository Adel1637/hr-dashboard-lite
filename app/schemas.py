"""Schéma canonique des jeux de données.

Chaque fichier client est relié à ces champs par l'assistant de correspondance.
Les synonymes servent à proposer automatiquement une correspondance ; ils sont
comparés après normalisation (minuscules, sans accents ni ponctuation).
Pour ajouter un champ, ajoutez simplement une entrée `Field` ici.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    key: str
    type: str  # "str" | "date" | "number" | "sex"
    required: bool = False
    synonyms: tuple[str, ...] = ()


@dataclass(frozen=True)
class DatasetSchema:
    key: str
    fields: tuple[Field, ...]

    @property
    def required_keys(self) -> list[str]:
        return [f.key for f in self.fields if f.required]

    def field(self, key: str) -> Field:
        for f in self.fields:
            if f.key == key:
                return f
        raise KeyError(key)


PERSONNEL = DatasetSchema(
    key="personnel",
    fields=(
        Field("matricule", "str", True,
              ("matricule", "mat", "id", "id employe", "id salarie", "code salarie",
               "numero", "employee id", "employee number", "emp id")),
        Field("nom", "str", False, ("nom", "nom prenom", "nom et prenom", "name", "full name")),
        Field("sexe", "sex", False, ("sexe", "genre", "gender", "sex")),
        Field("date_naissance", "date", False,
              ("date naissance", "date de naissance", "naissance", "birth date",
               "date of birth", "dob", "birthdate")),
        Field("date_entree", "date", True,
              ("date entree", "date d entree", "date embauche", "date d embauche",
               "date recrutement", "hire date", "start date", "entry date")),
        Field("date_sortie", "date", False,
              ("date sortie", "date de sortie", "date depart", "date de depart",
               "exit date", "termination date", "end date")),
        Field("motif_sortie", "str", False,
              ("motif sortie", "motif de sortie", "motif depart", "raison depart",
               "exit reason", "termination reason")),
        Field("service", "str", False,
              ("service", "departement", "direction", "department", "division", "structure")),
        Field("site", "str", False,
              ("site", "etablissement", "lieu", "localisation", "location", "unite", "agence")),
        Field("categorie", "str", False,
              ("categorie", "csp", "categorie socio professionnelle", "categorie professionnelle",
               "grade", "category", "job level")),
        Field("type_contrat", "str", False,
              ("type contrat", "type de contrat", "contrat", "nature contrat",
               "contract type", "contract")),
    ),
)


SCHEMAS: dict[str, DatasetSchema] = {PERSONNEL.key: PERSONNEL}
