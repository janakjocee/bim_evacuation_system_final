"""Build and evaluate a transparent IFC space-use classification experiment."""
from __future__ import annotations

import csv
import hashlib
import io
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

INDEPENDENT_REVIEW_FIELDS = (
    "record_id",
    "source_file",
    "source_sha256",
    "source_model_family",
    "ifc_schema",
    "ifc_global_id",
    "name",
    "long_name",
    "normalized_text",
    "independent_label",
    "reviewer_confidence",
    "reviewer_notes",
    "reviewer_confirmation_reference",
    "review_status",
)


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


def build_blinded_label_review_pack(rows: Iterable[Dict[str, str]]) -> list[Dict[str, str]]:
    """Remove silver labels so a reviewer can label without anchoring on them."""
    pack = []
    for row in rows:
        pack.append({
            "record_id": row["record_id"],
            "source_file": row["source_file"],
            "source_sha256": row["source_sha256"],
            "source_model_family": row["source_model_family"],
            "ifc_schema": row["ifc_schema"],
            "ifc_global_id": row["ifc_global_id"],
            "name": row["name"],
            "long_name": row["long_name"],
            "normalized_text": row["normalized_text"],
            "independent_label": "",
            "reviewer_confidence": "",
            "reviewer_notes": "",
            "reviewer_confirmation_reference": "",
            "review_status": "unreviewed",
        })
    return pack


def write_label_review_pack(rows: Iterable[Dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INDEPENDENT_REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def serialise_label_review_pack(rows: Iterable[Dict[str, str]]) -> str:
    """Return a portable CSV representation for browser download."""
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=INDEPENDENT_REVIEW_FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()


def parse_label_review_pack_csv(value: str) -> list[Dict[str, str]]:
    """Parse an uploaded review pack with required-column validation."""
    reader = csv.DictReader(io.StringIO(value))
    rows = list(reader)
    fieldnames = set(reader.fieldnames or [])
    missing = set(INDEPENDENT_REVIEW_FIELDS) - fieldnames
    if missing:
        raise ValueError("Review pack is missing columns: " + ", ".join(sorted(missing)))
    if not rows:
        raise ValueError("Review pack contains no data rows")
    return rows


def validate_label_review_pack(
    rows: Iterable[Dict[str, str]],
    max_invalid_details: int = 10,
) -> Dict[str, Any]:
    """Validate reviewer-supplied labels without verifying reviewer identity."""
    rows = list(rows)
    allowed_labels = set(LABEL_RULES)
    invalid_records = []
    for row in rows:
        problems = []
        if row.get("independent_label") not in allowed_labels:
            problems.append("missing_or_invalid_independent_label")
        try:
            confidence = int(row.get("reviewer_confidence", ""))
            if confidence not in range(1, 6):
                raise ValueError
        except (TypeError, ValueError):
            problems.append("reviewer_confidence_must_be_1_to_5")
        if not row.get("reviewer_confirmation_reference", "").strip():
            problems.append("missing_reviewer_confirmation_reference")
        if row.get("review_status") != "reviewer_confirmed":
            problems.append("review_status_must_be_reviewer_confirmed")
        if problems:
            invalid_records.append({"record_id": row.get("record_id", ""), "problems": problems})

    family_count = len({row.get("source_model_family", "") for row in rows if row.get("source_model_family")})
    label_count = len({row.get("independent_label", "") for row in rows if row.get("independent_label") in allowed_labels})
    complete = bool(rows) and not invalid_records

    return {
        "record_count": len(rows),
        "valid_record_count": len(rows) - len(invalid_records),
        "invalid_record_count": len(invalid_records),
        "invalid_records": invalid_records[:max_invalid_details],
        "invalid_record_details_truncated": len(invalid_records) > max_invalid_details,
        "source_model_family_count": family_count,
        "label_count": label_count,
        "status": "complete_reviewer_supplied_labels" if complete else "incomplete",
        "eligible_for_grouped_model_evaluation": complete and family_count >= 2 and label_count >= 2,
        "eligible_for_runtime_promotion_evaluation": complete and family_count >= 3 and label_count >= 2,
        "reviewer_identity_verified_by_software": False,
        "reviewer_qualification_verified_by_software": False,
    }


def evaluate_classifier(
    dataset_path: Path,
    random_state: int = 42,
    label_field: str = "silver_label",
) -> Dict[str, Any]:
    """Compare grouped ML predictions with the current deterministic baseline."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
    from sklearn.model_selection import LeaveOneGroupOut
    from sklearn.pipeline import Pipeline

    rows = load_records(dataset_path)
    texts = [row["normalized_text"] for row in rows]
    if not rows or any(not row.get(label_field) for row in rows):
        raise ValueError(f"Every dataset row must provide {label_field}")
    labels = [row[label_field] for row in rows]
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
    independent_label_evidence = (
        label_field == "independent_label"
        and validate_label_review_pack(rows)["eligible_for_grouped_model_evaluation"]
    )
    ml_eligible = (
        independent_label_evidence
        and validate_label_review_pack(rows)["eligible_for_runtime_promotion_evaluation"]
        and ml_metrics["macro_f1"] >= 0.70
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
        "label_field": label_field,
        "ground_truth_status": (
            "reviewer_supplied_labels_identity_not_verified_by_software"
            if independent_label_evidence
            else "rule_seeded_silver_labels_not_independent_human_ground_truth"
        ),
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
            (
                "Reviewer-supplied labels are present, but reviewer identity and competence are not verified by software."
                if independent_label_evidence
                else "Labels are transparent rule-seeded silver labels and are not independent ground truth."
            ),
            f"Only {len(unique_groups)} source model families are available; generalisation evidence is limited.",
            "Classes absent from a training family cannot be learned in that fold.",
            "The experiment classifies space metadata only and does not make fire-engineering decisions.",
        ],
    }


def write_json(report: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
