from pathlib import Path

import pandas as pd
import re


# https://www.bda.gv.at/service/unterschutzstellung/denkmalverzeichnis/denkmalliste-gemaess-3-dmsg.html
DATASET_DIR = Path(__file__).resolve().parents[2] / "datasets"
DEFAULT_INPUT = DATASET_DIR / "upperaustria_denkmal_list.csv"
DEFAULT_OUTPUT = DATASET_DIR / "upperaustria_denkmal_touristic.csv"

# Keyword filter: keep monuments a visitor would actually go and see.
# Categories are checked in order, the first match wins.

CATEGORIES = {
        "museum_memorial": (
            r"(?<!ehem\. )museum|gedenkstätte|memorial|besucherzentrum"
            r"|konzentrationslager|kz-|geburtshaus|sterbehaus"
        ),
        "abbey": (
            r"\bstift\b|stiftskirche|stiftspfarrkirche|kloster|abtei"
            r"|basilika|\bdom\b|domkirche"
        ),
        "castle": (
            r"schloss|schloß|schlössl|\bburg\b|burgruine|herzogsburg"
            r"|\bruine|festung|palais|residenz|\bansitz"
        ),
        "archaeology": (
            r"römer|römisch|lauriacum|legionslager|kastell|vicus|fundzone"
            r"|gräberfeld|hügelgr|ringwall|pfahlbau|höhensiedlung"
            r"|burgstall|hallstattkultur|felszeichnung|befunde"
        ),
        "pilgrimage": (r"wallfahrt"),
        "fortification": (
            r"stadtmauer|marktmauer|befestigung|stadttor|\btor\b|torturm"
            r"|torbau|bastion|zwinger|wehrturm|\bturm\b|stadtturm|\bfort\b"
        ),
        "landmark": (
            r"rathaus|pranger|mariensäule|pestsäule|dreifaltigkeitssäule"
            r"|marktbrunnen|stadtbrunnen|(?<!krieger)denkmal|lichtsäule"
            r"|totenleuchte"
        ),
        "technical": (
            r"soleleitung|hammer|sensenwerk|pferdeeisenbahn|seilbahn"
            r"|lokalbahn|pöstlingbergbahn|klause|glockengießerei"
            r"|salzstadel|salzturm|innerberger stadel|stollen"
        ),
        "culture_venue": (
            r"theater|brucknerhaus|kurhaus|trinkhalle|kaiservilla"
            r"|musikpavillon|botanischer garten|lehár|stadthalle"
        ),
    }


# If the main (first) part of the title is an everyday building, drop it,
# even when a later part says e.g. "ehem. Schloss" or "Teil der Stadtmauer".

EXCLUDE_LEAD = (
    r"^(ehem\.\s+|alte[rs]?\s+)?(bürger|wohn|miet|doppelwohn"
    r"|arbeiter|kommunal|ackerbürger|pfarrhof|pfarrheim|pfarrhaus"
    r"|pfarrzentrum|stadtpfarrhof|dechanthof|mesner|benefiziat"
    r"|kaplan|.*schule\b|.*gymnasium|kindergarten"
    r"|(markt)?gemeindeamt|amtsgebäude|bank|sparkasse|nationalbank"
    r"|bezirksgericht|kreisgericht|bezirkshauptmannschaft|bh\s"
    r"|amt der|landesregierung|.*kammer|kaserne|krankenhaus"
    r"|wirtschaftsgebäude|bauern|meierhof|stiftsmeierhof"
    r"|.*stiftshaus|stiftshof|freihaus|erdkeller|keller|gasthaus"
    r"|gasthof|hotel|lagergebäude|verwaltung|forsthaus|forsthube"
    r"|stadel|schüttkasten|friedhof|aufbahrungshalle|grenzstein"
    r"|.*bildstock|figur|kruzifix|kriegerdenkmal|gedenk(tafel"
    r"|stein)|wegkapelle|flur|hofkapelle|nischenkapelle|kath\."
    r"|evang\.|\w*kirche|\w*kapelle|karner|kalvarienberg"
    r"|\w*kreuzweg)"
)

# Always keep these, whatever the first part of the title says
# (e.g. "Wohnhaus, Bruckner-Geburtshaus", "Troadkasten, Heimatmuseum",
# "Kath. Pfarrkirche, Wallfahrtskirche ...").

ALWAYS_KEEP = (
    r"(?<!ehem\. )museum|gedenkstätte|memorial|konzentrationslager"
    r"|kz-|geburtshaus|wallfahrt|basilika|\bdom\b|stiftskirche"
    r"|stiftspfarrkirche|klosterkirche|klosterbauten"
)

# Street names and unrelated compounds that contain a category keyword
# (e.g. "Römerstraße 2", "Schlossgärtnerei", "Klosterneuburg"); removed
# before the category keywords are matched.

NOISE = r"\w*(?:gasse|straße|strasse|weg|platz|allee)\b(?:\s+\d+)?|schlossgärtnerei|klosterneuburg"


def classify(title: object) -> str | None:
    t = str(title).lower()
    lead = t.split(",")[0].strip()
    if not re.search(ALWAYS_KEEP, t) and re.search(EXCLUDE_LEAD, lead):
        return None
    t = re.sub(NOISE, " ", t)
    for category, pattern in CATEGORIES.items():
        if re.search(pattern, t):
            return category
    return None

def filter_csv(filepath: str | Path = DEFAULT_INPUT) -> pd.DataFrame:
    denkmal = pd.read_csv(filepath, sep=";")

    denkmal["category"] = denkmal["Objekttitel"].map(classify)
    touristic = denkmal[denkmal["category"].notna()].copy()

    return touristic


def get_filtered_csv(df: pd.DataFrame, filepath: str | Path = DEFAULT_OUTPUT) -> None:
    df.to_csv(filepath, sep=";", index=False)
