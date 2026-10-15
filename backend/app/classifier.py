"""Expense category suggestion: keyword rules first, then a text model trained on the organization's own entries.

The model (TF-IDF of character n-grams + logistic regression) is only used when there are enough labelled
expenses; every suggestion carries method, confidence and reason, and the user can always change it.
"""
import re
import unicodedata

CATEGORIES = ("MATERIAL", "LABOR", "FUEL", "EQUIPMENT", "SERVICE", "OTHER")
MIN_TRAINING = 20
RULES = [
    ("FUEL", r"\b(posto|combust|diesel|gasolina|etanol|abastec|oleo diesel|arla)"),
    ("EQUIPMENT", r"\b(munck|guindaste|loca[cç][aã]o|aluguel de (maquina|equip)|retro|escavadeira|betoneira|andaime|patrol|caminh[aã]o)"),
    ("LABOR", r"\b(pedreiro|servente|pintor|pintura|reboco|assentamento|eletricista|encanador|carpinteiro|armador|m[aã]o de obra|diaria|empreit|soldador|serralheir|moveleiro|ajudante)"),
    ("MATERIAL", r"\b(cimento|areia|brita|tijolo|bloco|ferro|vergalh|telha|cer[aâ]mica|argamassa|tinta|madeira|tubo|conex|fio|cabo|piso|rejunte|cal\b|pia|porta|vidro|box|material)"),
    ("SERVICE", r"\b(sondagem|projeto|consultoria|topograf|frete|transporte|instala[cç][aã]o|plotagem|laudo|servi[cç]o)"),
]


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", text).strip()


def by_rules(text: str) -> tuple[str, str] | None:
    plain = normalize(text)
    for category, pattern in RULES:
        match = re.search(normalize(pattern), plain)
        if match:
            return category, f"palavra-chave “{match.group(0).strip()}”"
    return None


class Classifier:
    def __init__(self, samples: list[tuple[str, str]]):
        self.model = None
        labelled = [(normalize(text), category) for text, category in samples if category in CATEGORIES and text]
        if len(labelled) >= MIN_TRAINING and len({c for _, c in labelled}) >= 2:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.linear_model import LogisticRegression
            from sklearn.pipeline import make_pipeline
            self.model = make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=1),
                                       LogisticRegression(max_iter=1000, class_weight="balanced"))
            self.model.fit([t for t, _ in labelled], [c for _, c in labelled])
        self.trained_on = len(labelled) if self.model else 0

    def suggest(self, text: str) -> dict:
        if self.model is not None:
            probabilities = self.model.predict_proba([normalize(text)])[0]
            best = int(probabilities.argmax())
            if probabilities[best] >= 0.55:
                return {"category": self.model.classes_[best], "confidence": round(float(probabilities[best]), 2),
                        "method": "modelo", "reason": f"aprendido com {self.trained_on} lançamentos da empresa"}
        rule = by_rules(text)
        if rule:
            return {"category": rule[0], "confidence": 0.7, "method": "regra", "reason": rule[1]}
        return {"category": "OTHER", "confidence": 0.0, "method": "padrão", "reason": "sem indício — revise"}
