import pandas as pd
import re

D = (
    "/Users/user/github-repos/Hackathon_Salzburg/backend/"
    "datasets/upperaustria_denkmal_list.csv"
)

denkmal = pd.read_csv(D, sep=";")

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


def classify(title: object) -> str | None:
    t = str(title).lower()
    lead = t.split(",")[0].strip()
    if not re.search(ALWAYS_KEEP, t) and re.search(EXCLUDE_LEAD, lead):
        return None
    for category, pattern in CATEGORIES.items():
        if re.search(pattern, t):
            return category
    return None



denkmal["category"] = denkmal["Objekttitel"].map(classify)
touristic = denkmal[denkmal["category"].notna()].copy()

# Clean addresses for geocoding: drop the "#MIG-x#" markers and the position hints like 
# "(bei)", "(vor)", "(gegenüber)".
#
#POSITION_HINT = r"\s*\((bei|vor|gegenüber|hinter|neben|in der nähe)\)"
#
#touristic["address_clean"] = (
#    touristic["Adresse"]
#    .str.replace(r"\s*#MIG-\w+#", "", regex=True)
#    .str.replace(POSITION_HINT, "", regex=True, flags=re.IGNORECASE)
#    .str.replace(r"\s+,", ",", regex=True)
#    .str.strip()
# )
#
#touristic = touristic.dropna(subset=["Adresse"])
#print(len(touristic), "of", len(denkmal), "monuments kept")
#print(touristic["category"].value_counts())
#
#touristic[["HERIS-ID", "Gemeinde", "Objekttitel", "category", "Adresse"]].to_csv(
#    "/Users/user/github-repos/Hackathon_Salzburg/backend/"
#    "datasets/upperaustria_denkmal_touristic.csv",
#    sep=";",
#    index=False,
#)

touristic.to_csv("filtered_touristic.csv", sep=";")


