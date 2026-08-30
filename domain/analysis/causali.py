"""Il catalogo delle causali nominate: codice → frase italiana, ripreso quasi
alla lettera dal catalogo EDT (AffSco_UtilDiagnostic, docs/edt/diagnostica.md).
Solo i codici che i checker emettono davvero. Segnaposto ammessi:
{resource}, {subject}, {unit}."""

CAUSALI: dict[str, str] = {
    # occupazione (Task 3)
    "resource_occupied": "{resource} è già occupata in un'attività",
    "resource_occupied_locked": "{resource} è già occupata in un'attività bloccata",
    "resource_peak": "{resource} ha raggiunto il suo picco d'occupazione",
    # indisponibilità (Task 3)
    "unavailability": "{resource} ha una indisponibilità",
    "unavailability_optional": "{resource} ha un'indisponibilità opzionale",
    "preference": "{resource} ha una preferenza",
    # griglia e sedi (Task 4)
    "slot_out_of_grid": "L'attività esce dalla griglia oraria",
    "break_straddled": "Intervallo non rispettato",
    "holiday": "Giorno festivo",
    "site_transition": "Tempo insufficiente per il trasferimento di sede",
    # vincoli orari sulla risorsa (Task 5)
    "min_distribution": "{resource}, distribuzione minima non rispettata",
    "max_hours_day": "{resource}, massimo di ore nella giornata superato",
    "max_hours_morning": "{resource}, massimo di ore nella mattinata superato",
    "max_hours_afternoon": "{resource}, massimo di ore nel pomeriggio superato",
    "max_presence": "Massimo di ore di presenza superato",
    "max_presence_days": "Massimo di giorni di presenza superato",
    "arrival_departure": "{resource} non rispetta le entrate/uscite richieste",
    "free_guaranteed": "{resource} non ha più giorni e 1/2 giornate libere",
    "max_half_days": "Massimo di 1/2 giornate di lavoro superate",
    "only_half_day": "{resource} lavora entrambe le mezze giornate",
    "max_site_changes": "Numero di cambi di sede superiore al limite fissato",
    "max_gap": "Durata tollerata dei buchi superata",
    # vincoli di materia (Task 6)
    "subject_same_half_day": "{subject}, troppe attività nella mezza giornata",
    "subject_same_day": "{subject}, troppe attività nella giornata",
    "subject_two_days": "{subject}, troppe attività su 2 giorni",
    "subject_forbidden_sequence": "{subject}, sequenza indesiderata di attività",
    "subject_max_hours_half_day": "{subject}, troppe ore nella mezza giornata",
    "subject_max_hours_day": "{subject}, troppe ore nella giornata",
    "subject_weekly_order": "{subject}, ordine settimanale non rispettato",
    "subject_imposed_succession": "{subject}, sequenza imposta non rispettata",
    "subject_half_day_gap": "{subject}, numero di mezze giornate insufficiente",
    "subject_parts_order": ("{subject}, ordine delle attività in gruppo rispetto "
                            "alle attività a classe intera non rispettato"),
    # peso didattico e copertura (Task 7)
    "weight_day": "Limite dei pesi didattici superato nella giornata",
    "weight_morning": "Limite dei pesi didattici superato nella mattinata",
    "weight_afternoon": "Limite dei pesi didattici superato nel pomeriggio",
    "weight_week": "Limite settimanale dei pesi didattici superato",
    "coverage_mismatch": "{unit}, {subject}: monte ore delle attività diverso dal servizio",
    "ambiguous_study_plan": ("{unit}: due parti della stessa combinazione "
                             "dichiarano piani di studi diversi"),
    "election_mismatch": ("{unit}, {group}: le materie seguite fra quelle in "
                          "alternativa non sono una"),
    # lo scarto (pezzo 3, ondata 1)
    "activity_unplaced": "{subject}, l'attività non è piazzata",
    # l'allineamento: 📦 l'ident genera l'attività complessa (XSD)
    "alignment_split": "Attività allineate su collocazioni diverse",
    # le aule contate dalla fase 1 (ADR-021)
    "room_group_peak": "Il gruppo di aule {resource} ha raggiunto il suo picco d'occupazione",
    # assegnazione delle aule (seconda fase)
    "room_unassigned": "{subject}, nessuna aula assegnata",
}


def message(code: str, **kwargs) -> str:
    return CAUSALI[code].format(**kwargs)
