"""EU/EEA-Laenderset fuer datenseitige Europa-Filterung.

Konsistent mit frontend/src/utils/countries.js EU_COUNTRIES.
"""

# EU-27 + EEA (NO, IS, LI) + Assoziierte (CH) + GB/UK + EL (CORDIS-Alias fuer GR)
EU_EEA_COUNTRIES: frozenset[str] = frozenset({
    # EU-27
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR",
    "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO",
    "SE", "SI", "SK",
    # EEA + Assoziierte
    "CH", "NO", "IS", "LI",
    # GB (Brexit, aber historisch im EU-Innovationsraum)
    "GB", "UK",
    # CORDIS-Alias
    "EL",
})


def is_european(code: str) -> bool:
    """Prueft ob ein Laendercode zum EU/EEA-Raum gehoert."""
    return code.upper().strip() in EU_EEA_COUNTRIES
