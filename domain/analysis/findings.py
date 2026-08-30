"""Il verdetto dell'analisi: dataclass mai persistite (principio 2 del design).
Ogni finding porta la causale, la frase italiana già formattata e le quantità
— il verdetto è un numero verificabile, non un aggettivo."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping, NamedTuple


class Severity(StrEnum):
    HARD = "hard"            # rosso
    OPTIONAL = "optional"    # giallo: violabile solo con override globale
    PREFERENCE = "preference"  # verde


class FindingKey(NamedTuple):
    """L'identità di un finding. È una **tupla nominata** e non una tupla nuda
    per una ragione misurata: aggiungendo `subject` i due lettori che la
    spacchettavano per posizione — l'oracolo differenziale e il banco — si sono
    rotti insieme, e il difetto sarebbe stato invisibile a chi aggiunge il
    campo. Con i nomi, un campo in più è additivo: chi legge `.code` e
    `.resources` continua a funzionare, e resta vero che due chiavi uguali
    sono lo stesso verdetto."""

    code: str
    resources: tuple[int | str, ...]
    activities: tuple[int, ...]
    quantities: tuple[tuple[str, int], ...]
    subject: int | None
    group: str | None = None


@dataclass(frozen=True)
class Finding:
    code: str
    message: str
    severity: Severity
    resources: tuple[int | str, ...] = ()    # pk delle Resource o chiavi-atomo (ADR-017)
    activities: tuple[int, ...] = ()   # pk delle Activity coinvolte
    quantities: Mapping[str, int] = field(default_factory=dict)
    weeks: tuple[int, ...] = ()        # settimane in cui la violazione vale
    subject: int | None = None         # pk della Subject, quando la causale la nomina
    group: str | None = None           # il gruppo che la causale nomina: di elezione
                                       # (ADR-020) o d'allineamento (L5)

    @property
    def key(self):
        """Identità per il dedup fra firme di settimana: messaggio e settimane
        esclusi apposta.

        ⚠ Escludere il messaggio ha una conseguenza: **tutto ciò che distingue
        due verdetti dev'essere un campo**, o i due collassano in uno. È
        successo su `coverage_mismatch`, che nomina la materia solo nella
        frase: un'unità a cui mancano due materie per lo stesso numero di
        minuti — il caso normale, `atteso 60 / osservato 0` su ciascuna —
        produceva **un** finding, e *quale* delle due materie sopravvivesse
        dipendeva dall'ordine di iterazione. Da qui `subject`.

        ⚠ Da qui anche `group`: due gruppi in alternativa insoddisfatti sulla
        stessa unità hanno causale, risorsa e quantità identiche, ed è la
        stessa forma del difetto (ADR-020).

        ⚠ `subject_constraints` nomina anch'esso una materia e **non** ne ha
        bisogno: là la frase porta `subject_a`, che è la stessa per tutte le
        righe che potrebbero collidere, quindi due verdetti collassati dicono
        davvero la stessa cosa. Ciò che si perde là è *quale riga* di vincolo
        li ha generati, che è un limite già dichiarato in `blame.py` e di
        natura diversa."""
        return FindingKey(self.code, self.resources, self.activities,
                          tuple(sorted(self.quantities.items())), self.subject,
                          self.group)
