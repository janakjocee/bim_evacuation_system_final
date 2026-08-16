"""Build and evaluate a transparent IFC space-use classification experiment."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple


LABEL_RULES = {
    "circulation": (
        "corridor", "hallway", "hallyway", "foyer", "lobby", "vestibule", "stair",
    ),
    "residential": ("bedroom", "living room", "dormitory", "residential"),
    "sanitary": ("bathroom", "toilet", "washroom", "shower", "lavatory", " wc"),
    "kitchen": ("kitchen", "food preparation"),
    "service_storage": (
        "storage", "store room", "storeroom", "utility", "mechanical", "electrical",
        "equipment", "plant room", "roof", "janitor", "housekeeping", "trash", "boiler",
        "telecom", "receiving",
    ),
    "clinical": (
        "exam", "treatment", "trmt", "clinical", "dental", "pharm", "laboratory", " lab",
        "x-ray", "radiograph", "immun", "specimen", "blood draw", "optometry", "med gas",
    ),
    "assembly": (
        "waiting", "activity", "classroom", "training", "library", "lounge", "conference",
        "dining", "multipurpose", "playroom", "group therapy",
    ),
    "workplace": (
        "office", "administration", "admin ", "reception", "workstation", "cubicle",
        "records", "staff room", "provider station", "nurse station",
    ),
}


def normalise_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9/ -]+", " ", value.lower())).strip()


def silver_label(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Return a rule-seeded silver label and the exact matching term."""
    padded = f" {normalise_text(text)} "
    for label, terms in LABEL_RULES.items():
        for term in terms:
            if term in padded:
                return label, term.strip()
    return None, None


def deterministic_baseline(text: str) -> str:
    """Map the current IFCParser keyword behavior to the evaluation taxonomy."""
    value = normalise_text(text)
    if "office" in value:
        return "workplace"
    if "corridor" in value or "hall" in value or "stair" in value or "lobby" in value:
        return "circulation"
    if "bedroom" in value or "dorm" in value or "residential" in value:
        return "residential"
    if any(term in value for term in (
        "storage", "store", "plant", "utility", "mechanical", "electrical", "equipment",
        "roof", "janitor", "housekeeping",
    )):
        return "service_storage"
    if "toilet" in value or "bathroom" in value or "washroom" in value or re.search(r"\bwc\b", value):
        return "sanitary"
    if "kitchen" in value:
        return "kitchen"
    if any(term in value for term in (
        "exam", "treatment", "trmt", "clinical", "dental", "pharm", "laboratory", " lab",
        "x-ray", "radiograph", "specimen",
    )):
        return "clinical"
    if any(term in value for term in (
        "waiting", "classroom", "training", "library", "lounge", "conference", "activity",
    )):
        return "assembly"
    return "unknown"


def infer_family(path: Path) -> str:
    value = path.name.lower()
    if "clinic" in value:
        return "clinic"
    if "duplex" in value:
        return "duplex"
    return path.stem.lower().replace(" ", "_")


def extract_silver_records(ifc_paths: Iterable[Path]) -> list[Dict[str, Any]]:
    """Extract labelled space metadata from real IFC files."""
    import ifcopenshell

    records = []
    for path in sorted(Path(item) for item in ifc_paths):
        source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        model = ifcopenshell.open(str(path))
        family = infer_family(path)
        for space in model.by_type("IfcSpace"):
            name = str(getattr(space, "Name", "") or "")
            long_name = str(getattr(space, "LongName", "") or "")
            description = str(getattr(space, "Description", "") or "")
            text = normalise_text(" ".join((name, long_name, description)))
            label, rule = silver_label(text)
            if not label:
                continue
            records.append({
                "record_id": hashlib.sha256(f"{source_hash}:{space.GlobalId}".encode()).hexdigest()[:16],
                "source_file": path.name,
                "source_sha256": source_hash,
                "source_model_family": family,
                "ifc_schema": str(model.schema),
                "ifc_global_id": str(space.GlobalId),
                "name": name,
                "long_name": long_name,
                "normalized_text": text,
                "silver_label": label,
                "label_rule": rule,
                "label_provenance": "codex_assisted_rule_seeded_silver",
                "independent_ground_truth": "false",
                "review_status": "requires_project_author_review",
            })
    return records


def write_records(records: list[Dict[str, Any]], output_path: Path) -> None:
    if not records:
        raise ValueError("No confidently labelled IfcSpace records were found")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def load_records(path: Path) -> list[Dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def evaluate_classifier(dataset_path: Path, random_state: int = 42) -> Dict[str, Any]:
    """Compare grouped ML predictions with the current deterministic baseline."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
    from sklearn.model_selection import LeaveOneGroupOut
    from sklearn.pipeline import Pipeline

    rows = load_records(dataset_path)
    texts = [row["normalized_text"] for row in rows]
    labels = [row["silver_label"] for row in rows]
    groups = [row["source_model_family"] for row in rows]
    unique_labels = sorted(set(labels))
    unique_groups = sorted(set(groups))
    if len(unique_groups) < 2:
        raise ValueError("Grouped evaluation requires at least two independent model families")

    ml_predictions = [None] * len(rows)
    fold_details = []
    splitter = LeaveOneGroupOut()
    for train_indices, test_indices in splitter.split(texts, labels, groups):
        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
            ("classifier", LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                random_state=random_state,
            )),
        ])
        train_texts = [texts[index] for index in train_indices]
        train_labels = [labels[index] for index in train_indices]
        test_texts = [texts[index] for index in test_indices]
        predictions = pipeline.fit(train_texts, train_labels).predict(test_texts)
        for index, prediction in zip(test_indices, predictions):
            ml_predictions[index] = prediction

        held_out = sorted({groups[index] for index in test_indices})
        train_classes = set(train_labels)
        test_classes = {labels[index] for index in test_indices}
        fold_details.append({
            "held_out_family": held_out[0],
            "train_records": len(train_indices),
            "test_records": len(test_indices),
            "train_classes": sorted(train_classes),
            "test_classes": sorted(test_classes),
            "unseen_test_classes": sorted(test_classes - train_classes),
            "macro_f1": round(f1_score(
                [labels[index] for index in test_indices],
                list(predictions),
                labels=unique_labels,
                average="macro",
                zero_division=0,
            ), 4),
        })

    baseline_predictions = [deterministic_baseline(text) for text in texts]

    def metrics(predictions: list[str]) -> Dict[str, Any]:
        return {
            "accuracy": round(accuracy_score(labels, predictions), 4),
            "macro_f1": round(f1_score(labels, predictions, labels=unique_labels, average="macro", zero_division=0), 4),
            "weighted_f1": round(f1_score(labels, predictions, labels=unique_labels, average="weighted", zero_division=0), 4),
            "classification_report": classification_report(
                labels,
                predictions,
                labels=unique_labels,
                output_dict=True,
                zero_division=0,
            ),
            "confusion_matrix": confusion_matrix(labels, predictions, labels=unique_labels).tolist(),
        }

    ml_metrics = metrics(ml_predictions)
    baseline_metrics = metrics(baseline_predictions)
    ml_eligible = (
        ml_metrics["macro_f1"] >= 0.70
        and ml_metrics["macro_f1"] > baseline_metrics["macro_f1"]
        and all(not fold["unseen_test_classes"] for fold in fold_details)
    )
    return {
        "experiment": "ifc_space_use_text_classification_v1",
        "dataset": str(dataset_path),
        "dataset_sha256": hashlib.sha256(Path(dataset_path).read_bytes()).hexdigest(),
        "record_count": len(rows),
        "model_family_count": len(unique_groups),
        "model_families": unique_groups,
        "class_distribution": dict(sorted(Counter(labels).items())),
        "labels": unique_labels,
        "validation": "leave-one-source-model-family-out",
        "random_state": random_state,
        "ground_truth_status": "rule_seeded_silver_labels_not_independent_human_ground_truth",
        "baseline": baseline_metrics,
        "ml_model": {
            "type": "TF-IDF word 1-2 grams plus class-balanced logistic regression",
            **ml_metrics,
        },
        "folds": fold_details,
        "ml_eligible_for_runtime_default": ml_eligible,
        "runtime_recommendation": (
            "ML met the experimental promotion gate; independent expert-labelled validation is still required."
            if ml_eligible
            else "Keep deterministic classification as runtime default; ML did not satisfy the promotion gate."
        ),
        "limitations": [
            "Labels are transparent rule-seeded silver labels and are not independent ground truth.",
            "Only two source model families are available; generalisation evidence is therefore limited.",
            "Classes absent from a training family cannot be learned in that fold.",
            "The experiment classifies space metadata only and does not make fire-engineering decisions.",
        ],
    }


def write_json(report: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
