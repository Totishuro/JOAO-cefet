import pandas as pd
from pathlib import Path
import unicodedata, re

def _slugify(text: str) -> str:
    if text is None:
        return ""
    # remove accents
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    # lower + non-alnum to underscore
    text = re.sub(r"[^0-9a-zA-Z]+", "_", text).strip("_").lower()
    # dedupe underscores
    text = re.sub(r"_+", "_", text)
    return text

def _load_mapping(path: str):
    fp = Path(path)
    if not fp.exists():
        return None, {}, {}
    df = pd.read_csv(fp)
    # expected columns: coluna_original,classe,rotulo_publico,nome_tecnico
    required = {"coluna_original","classe","rotulo_publico","nome_tecnico"}
    if not required.issubset(set(map(str.lower, df.columns))):
        # try to align by case-insensitive matching
        cols = {c.lower(): c for c in df.columns}
        df = df.rename(columns={cols.get("coluna_original","coluna_original"): "coluna_original",
                                cols.get("classe","classe"): "classe",
                                cols.get("rotulo_publico","rotulo_publico"): "rotulo_publico",
                                cols.get("nome_tecnico","nome_tecnico"): "nome_tecnico"})
    mapping = {}
    labels  = {}
    classes = {}
    for _, r in df.iterrows():
        orig = str(r["coluna_original"])
        tech = str(r["nome_tecnico"])
        lab  = str(r["rotulo_publico"])
        cls  = str(r["classe"])
        if orig and tech:
            mapping[orig] = tech
            labels[tech] = lab if lab else orig
            classes[tech] = cls if cls else ""
    return mapping, labels, classes

def _infer_mapping_from_df(df: pd.DataFrame):
    mapping, labels, classes = {}, {}, {}
    for col in df.columns:
        tech = _slugify(col)
        mapping[col] = tech
        labels[tech] = str(col)
        classes[tech] = ""
    return mapping, labels, classes

def apply_column_mapping(df: pd.DataFrame, mapping_path: str = "columns_classification.csv"):
    mapping, labels, classes = _load_mapping(mapping_path)
    if mapping is None:
        mapping, labels, classes = _infer_mapping_from_df(df)
    df2 = df.rename(columns=mapping)
    return df2, labels, classes