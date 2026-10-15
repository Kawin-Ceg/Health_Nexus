"""Which syndrome a symptomatic reading points to. A reading can count toward more than one."""

SYNDROMES: dict[str, frozenset[str]] = {
    "febrile": frozenset({"fever", "body ache", "rash"}),
    "respiratory": frozenset({"cough", "breathlessness", "chest pain"}),
    "gastrointestinal": frozenset({"diarrhoea", "nausea", "thirst"}),
}

FEVER_C = 38.0
LOW_SPO2 = 93.0


def syndromes(symptoms: list[str] | tuple[str, ...], vitals: dict[str, float]) -> set[str]:
    reported = {s.strip().lower() for s in symptoms}
    found = {name for name, signs in SYNDROMES.items() if reported & signs}
    if vitals.get("temperature_c", 0) >= FEVER_C:
        found.add("febrile")
    spo2 = vitals.get("spo2")
    if spo2 is not None and spo2 <= LOW_SPO2:
        found.add("respiratory")
    return found
