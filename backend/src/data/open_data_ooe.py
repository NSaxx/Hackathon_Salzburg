import pandas as pd

def landesmuseen() -> pd.DataFrame:
    return pd.read_csv(
        "https://e-gov.ooe.gv.at/at.gv.ooe.ogd2-citi/api/file/eb1MKuyzLjiztYufybYPnQ/Standorte_der_Oberoesterreichischen_Landesmuseen.csv",
        encoding="latin-1",
        sep=";",
    ).drop(columns=["Staats-ID"])
