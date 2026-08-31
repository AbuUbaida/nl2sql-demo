from typing import Iterable


TOWN_CODE_TO_NAME: dict[str, str] = {
    "NIGHT/ MS/MW": "Night / Main Sewerage / Main Water",
    "Ravi Town": "Ravi Town",
    "DGBT": "Data Ganj Bakhsh Town",
    "Shalamar Town": "Shalamar Town",
    "NT": "Nishtar Town",
    "SBT (Sik)": "Sikandarabad Town",
    "Gulberg Town": "Gulberg Town",
    "Rajgarh Centre C2": "Rajgarh Centre C2",
    "Rajgarh Centre C1": "Rajgarh Centre C1",
    "AIT": "Ayubia Industrial Town",
    "Badami Bagh Ravi": "Badami Bagh Ravi",
    "MBS MULTAN": "Multan",
    "Raiwind": "Raiwind",
    "Admin": "Administration",
    "RING ROAD": "Lahore Ring Road",
    "LANDFILL": "Lahore Landfill",
    "Lakhodair": "Lakhodair",
    "Wahga Town": "Wagah Town",
    "P&P North": "Parks & Plantation North",
    "ABT": "Aziz Bhatti Town",
    "MIS": "Management Information System",
    "MB Wagha": "Mochi Bagh / Wagah",
    "Chung": "Chung",
    "Kahna NT": "Kahna Nishtar Town",
    "P&P South": "Parks & Plantation South",
    "P&P Child": "Parks & Plantation Child",
    "Singhpura GT": "Singhpura Grand Trunk Road",
    "Bedian": "Bedian",
    "Jallo Yard": "Jallo Yard",
    "Manga": "Manga",
    "Peco NT": "Peco Nishtar Town",
    "P&P Sik": "Parks & Plantation Sikandarabad",
    "Shahdra RT": "Shahdara Ravi Town",
    "P&P Val": "Parks & Plantation Valley",
    "Barki Yard": "Barki Yard",
    "Admin Yards": "Administration Yards",
    "SINGHPURA GT": "Singhpura Grand Trunk Road",
    "COMPOST PLANT": "Compost Plant",
    "Ravi Saggiyan": "Ravi Saggiyan"
}

CATEGORY_TO_CLEAN: dict[str, str] = {
    "Vacuume Sweeper": "Vacuum Sweeper",
    "Chain Arm Roll": "Chain Arm Roll",
    "Dumper": "Dumper",
    "Mechnical Washer": "Mechanical Washer",
    "Tractor Loader": "Tractor Loader",
    "Foton": "Foton",
    "Compactor": "Compactor",
    "Mini Dumper": "Mini Dumper",
    "Loader Rikshaw": "Loader Rickshaw",
    "Washer Rikshaw": "Washer Rickshaw",
    "Water Bouzer": "Water Bowser",
    "Mechnical Sweeper": "Mechanical Sweeper",
    "Loader": "Loader",
    "Generator": "Generator",
    "Rikshaw": "Rickshaw",
    "rikshaw": "Rickshaw",
    "Pick up": "Pickup",
    "Trolley": "Trolley",
    "Washer Rikshaw Yard": "Washer Rickshaw Yard",
    "Gully Sucker": "Gully Sucker",
    "Arm Roll": "Arm Roll",
    "Tractor Trolley": "Tractor Trolley",
    "Tractor trolley": "Tractor Trolley",
    "Helix": "Helix",
    "helix": "Helix",
    "CRV Generator": "CRV Generator",
    "Loader Rickshaw (Admin)": "Loader Rickshaw (Admin)",
    "enginer overhaul": "Engine Overhaul",
    "Crane": "Crane",
    "GENERAL ASSIGNMENT": "General Assignment",
}

lowercase_category_mapping = {k.lower(): v for k, v in CATEGORY_TO_CLEAN.items()}


def resolve_town_name(town_code: str) -> str:
    """
    Resolve the town name from the given town code.
    If the town code is not found in the mapping, return the original town code.
    """
    striped_code = town_code.strip()
    return TOWN_CODE_TO_NAME.get(striped_code, striped_code)


def find_unmapped_codes(codes: Iterable[str]) -> set[str]:
    """
    Find and return a set of town codes that are not mapped in TOWN_CODE_TO_NAME.
    """
    unmapped_codes = {code.strip() for code in codes if code.strip() not in TOWN_CODE_TO_NAME}
    return unmapped_codes


def resolve_category(raw: str) -> str:
    """
    Resolve the category name from the given raw category string.
    If the raw category is not found in the mapping, return the original raw category. make the lookup case-insensitive — build a lowercased version of the mapping once at module load and search that.
    """
    return lowercase_category_mapping.get(raw.strip().lower(), raw.strip())


def find_unmapped_categories(categories: Iterable[str]) -> set[str]:
    """
    Find and return a set of category names that are not mapped in CATEGORY_TO_CLEAN.
    The lookup is case-insensitive.
    """
    unmapped_categories = {cat.strip() for cat in categories if cat.strip().lower() not in lowercase_category_mapping}
    return unmapped_categories