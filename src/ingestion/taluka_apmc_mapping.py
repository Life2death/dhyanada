"""Mapping of talukas to APMC slugs for weather data queries.

This allows weather queries to be personalized to a farmer's taluka,
instead of hardcoding to specific APMCs like "parner".
"""

TALUKA_TO_APMC = {
    # Ahmednagar District
    "ahmednagar": "ahmednagar",
    "sangamner": "sangamner",
    "rahuri": "rahuri",
    "shrirampur": "shrirampur",
    "pathardi": "pathardi",
    "kadus": "kadus",
    "newasa": "newasa",
    "parner": "parner",
    "goregaon": "goregaon_parner",
    "wadegaon": "wadegaon_parner",

    # Pune District
    "pune": "pune",
    "baramati": "baramati",
    "indapur": "indapur",
    "purandar": "purandar",
    "daund": "daund",
    "bhor": "bhor",
    "ambegaon": "ambegaon",
    "shirur": "shirur",
    "khed": "khed",

    # Nashik District
    "nashik": "nashik",
    "manmad": "manmad",
    "yeola": "yeola",
    "kopargaon": "kopargaon",
    "nandgaon": "nandgaon",
    "sinnar": "sinnar",
    "surgana": "surgana",
    "igatpuri": "igatpuri",
    "trimbakeshwar": "trimbakeshwar",

    # Solapur District
    "solapur": "solapur",
    "sangola": "sangola",
    "malshiras": "malshiras",
    "pandharpur": "pandharpur",
    "mohol": "mohol",

    # Satara District
    "satara": "satara",
    "koregaon": "koregaon",
    "phaltan": "phaltan",

    # Sangli District
    "sangli": "sangli",
    "miraj": "miraj",
    "walva": "walva",

    # Kolhapur District
    "kolhapur": "kolhapur",
    "radhanagari": "radhanagari",

    # Aurangabad District
    "aurangabad": "aurangabad",
    "paithan": "paithan",

    # Jalgaon District
    "jalgaon": "jalgaon",
    "yawal": "yawal",

    # Nanded District
    "nanded": "nanded",

    # Wardha District
    "wardha": "wardha",

    # Nagpur District
    "nagpur": "nagpur",

    # Buldana District
    "buldana": "buldana",

    # Akola District
    "akola": "akola",

    # Yavatmal District
    "yavatmal": "yavatmal",

    # Latur District
    "latur": "latur",

    # Osmanaband District
    "osmanaband": "osmanaband",
    "usmanabad": "osmanaband",
}


def get_apmc_for_taluka(taluka: str | None) -> str | None:
    """
    Get APMC slug for a given taluka.

    Args:
        taluka: Taluka name (case-insensitive)

    Returns:
        APMC slug (e.g., "parner") or None if not found
    """
    if not taluka:
        return None

    slug = TALUKA_TO_APMC.get(taluka.lower().strip())
    return slug


def get_default_weather_apmcs(taluka: str | None) -> list[str]:
    """
    Get weather APMCs for a taluka.

    For now, returns a list with a single APMC per taluka.
    In the future, could return multiple APMCs if a taluka has
    multiple weather stations.

    Args:
        taluka: Taluka name

    Returns:
        List of APMC slugs to query for weather
    """
    apmc = get_apmc_for_taluka(taluka)
    return [apmc] if apmc else []
