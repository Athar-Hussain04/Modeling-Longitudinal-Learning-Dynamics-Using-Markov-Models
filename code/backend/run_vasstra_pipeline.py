from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import OneHotEncoder


RSEED = 2026
STATE_COUNT = 3
TRAJECTORY_COUNT = 3
CLUSTER_COLUMNS = [
    "Freq_Course_View",
    "Freq_Forum_Consume",
    "Freq_Forum_Contribute",
    "Freq_Lecture_View",
    "Regularity_Course_View",
    "Session_Count",
    "Total_Duration",
    "Active_Days",
]
STATE_NAMES = ["Disengaged", "Average", "Active"]
FEATURE_LABELS = {
    "Freq_Course_View": "Course Views",
    "Freq_Forum_Consume": "Forum Reading",
    "Freq_Forum_Contribute": "Forum Posting",
    "Freq_Lecture_View": "Lecture Views",
    "Regularity_Course_View": "Course-View Regularity",
    "Session_Count": "Session Count",
    "Total_Duration": "Total Duration",
    "Active_Days": "Active Days",
}


def project_paths() -> dict[str, Path]:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    data_raw_dir = project_root / "data" / "raw"
    data_processed_dir = project_root / "data" / "processed"
    output_dir = project_root / "outputs" / "backend"
    models_dir = output_dir / "models"

    data_processed_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)

    return {
        "project_root": project_root,
        "data_raw_dir": data_raw_dir,
        "data_processed_dir": data_processed_dir,
        "output_dir": output_dir,
        "models_dir": models_dir,
    }


def standardize_within_course(dataframe: pd.DataFrame) -> pd.DataFrame:
    standardized = dataframe.copy()
    for column in CLUSTER_COLUMNS:
        course_mean = standardized.groupby("CourseID")[column].transform("mean")
        course_std = standardized.groupby("CourseID")[column].transform("std").replace(0, np.nan)
        standardized[column] = ((standardized[column] - course_mean) / course_std).fillna(0.0)
    return standardized


def evaluate_state_models(features: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int]] = []
    for component_count in range(2, 6):
        model = GaussianMixture(
            n_components=component_count,
            covariance_type="diag",
            random_state=RSEED,
            n_init=10,
        )
        model.fit(features)
        rows.append(
            {
                "components": component_count,
                "bic": round(float(model.bic(features)), 2),
                "aic": round(float(model.aic(features)), 2),
            }
        )
    return pd.DataFrame(rows)


def assign_states(standardized: pd.DataFrame) -> tuple[pd.DataFrame, GaussianMixture]:
    model = GaussianMixture(
        n_components=STATE_COUNT,
        covariance_type="diag",
        random_state=RSEED,
        n_init=15,
    )
    feature_frame = standardized[CLUSTER_COLUMNS]
    model.fit(feature_frame)

    raw_components = model.predict(feature_frame)
    probabilities = model.predict_proba(feature_frame)
    component_order = np.argsort(model.means_.mean(axis=1))
    mapping = {component: STATE_NAMES[index] for index, component in enumerate(component_order)}

    assigned = standardized.copy()
    assigned["State"] = [mapping[component] for component in raw_components]
    assigned["StateID"] = assigned["State"].map({name: idx + 1 for idx, name in enumerate(STATE_NAMES)})
    for index, state_name in enumerate(STATE_NAMES):
        component_index = component_order[index]
        assigned[f"Prob_{state_name}"] = probabilities[:, component_index]

    return assigned, model


def create_state_sequences(assigned: pd.DataFrame) -> pd.DataFrame:
    pivot = (
        assigned.sort_values(["UserID", "Sequence"])
        .pivot_table(index="UserID", columns="Sequence", values="State", aggfunc="first")
    )
    expected_columns = list(range(1, 9))
    pivot = pivot.reindex(columns=expected_columns)
    pivot.columns = [f"step_{column}" for column in expected_columns]
    return pivot.reset_index().fillna("Average")


def evaluate_trajectory_clusters(sequence_table: pd.DataFrame) -> tuple[pd.DataFrame, OneHotEncoder, np.ndarray]:
    step_columns = [column for column in sequence_table.columns if column.startswith("step_")]
    encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    encoded = encoder.fit_transform(sequence_table[step_columns])

    rows: list[dict[str, float | int]] = []
    for cluster_count in range(2, 6):
        labels = AgglomerativeClustering(n_clusters=cluster_count, linkage="ward").fit_predict(encoded)
        rows.append(
            {
                "clusters": cluster_count,
                "silhouette": round(float(silhouette_score(encoded, labels)), 4),
            }
        )

    return pd.DataFrame(rows), encoder, encoded


def name_trajectories(profiles: list[dict[str, object]]) -> dict[int, str]:
    active_sorted = sorted(profiles, key=lambda item: item["active_share"], reverse=True)
    active_cluster = active_sorted[0]["trajectory"]
    remaining = [item for item in profiles if item["trajectory"] != active_cluster]
    disengaged_cluster = sorted(remaining, key=lambda item: item["disengaged_share"], reverse=True)[0]["trajectory"]
    average_cluster = [item for item in profiles if item["trajectory"] not in {active_cluster, disengaged_cluster}][0]["trajectory"]
    return {
        active_cluster: "Mostly active",
        average_cluster: "Mostly average",
        disengaged_cluster: "Mostly disengaged",
    }


def build_trajectory_profiles(sequence_table: pd.DataFrame, labels: np.ndarray, user_grades: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    working = sequence_table.copy()
    working["trajectory"] = labels + 1
    step_columns = [column for column in working.columns if column.startswith("step_")]
    long_states = working.melt(id_vars=["UserID", "trajectory"], value_vars=step_columns, value_name="State")

    raw_profiles: list[dict[str, object]] = []
    for trajectory_id in sorted(working["trajectory"].unique()):
        trajectory_frame = working[working["trajectory"] == trajectory_id]
        long_frame = long_states[long_states["trajectory"] == trajectory_id]
        state_shares = long_frame["State"].value_counts(normalize=True)
        prototype = []
        for column in step_columns:
            prototype.append(trajectory_frame[column].mode().iat[0])

        raw_profiles.append(
            {
                "trajectory": int(trajectory_id),
                "size": int(len(trajectory_frame)),
                "prototype_sequence": prototype,
                "active_share": float(state_shares.get("Active", 0.0)),
                "average_share": float(state_shares.get("Average", 0.0)),
                "disengaged_share": float(state_shares.get("Disengaged", 0.0)),
            }
        )

    trajectory_names = name_trajectories(raw_profiles)
    profiles = pd.DataFrame(raw_profiles)
    profiles["trajectory_label"] = profiles["trajectory"].map(trajectory_names)

    assignments = working[["UserID", "trajectory"]].copy()
    assignments["trajectory_label"] = assignments["trajectory"].map(trajectory_names)
    assignments = assignments.merge(user_grades, on="UserID", how="left")

    profiles = profiles.merge(
        assignments.groupby("trajectory", as_index=False)["Final_Grade"].mean().rename(columns={"Final_Grade": "mean_final_grade"}),
        on="trajectory",
        how="left",
    )

    return profiles, assignments


def build_dashboard_payload(
    original_data: pd.DataFrame,
    state_selection: pd.DataFrame,
    state_model_selection: pd.DataFrame,
    state_profiles: pd.DataFrame,
    trajectory_validation: pd.DataFrame,
    trajectory_profiles: pd.DataFrame,
    trajectory_assignments: pd.DataFrame,
    sequence_table: pd.DataFrame,
) -> dict[str, object]:
    step_columns = [column for column in sequence_table.columns if column.startswith("step_")]
    samples = trajectory_assignments.merge(sequence_table, on="UserID", how="left")
    samples["state_sequence"] = samples[step_columns].apply(lambda row: " -> ".join(row.tolist()), axis=1)
    samples = samples[["UserID", "trajectory_label", "Final_Grade", "state_sequence"]].head(180)

    return {
        "project": {
            "title": "Modeling Longitudinal Learning Dynamics Using Markov Models",
            "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "backend": "Python",
            "method": "VaSSTra (Variables-States-Trajectories), implemented in Python",
            "source_notebook": "notebook/vasstra_python.ipynb",
        },
        "overview": {
            "total_records": int(len(original_data)),
            "unique_students": int(original_data["UserID"].nunique()),
            "chosen_states": STATE_COUNT,
            "chosen_trajectories": TRAJECTORY_COUNT,
            "average_final_grade": round(float(original_data["Final_Grade"].mean()), 2),
        },
        "state_model_selection": json.loads(state_model_selection.to_json(orient="records")),
        "trajectory_validation": json.loads(trajectory_validation.to_json(orient="records")),
        "state_profiles": json.loads(state_profiles.round(3).to_json(orient="records")),
        "trajectory_profiles": json.loads(trajectory_profiles.round(3).to_json(orient="records")),
        "manual_demo": {
            "states": STATE_NAMES,
            "field_schema": [
                {"name": f"step_{index}", "label": f"Course Sequence {index}", "default": STATE_NAMES[1]}
                for index in range(1, 9)
            ],
            "prototype_sequences": {
                row["trajectory_label"]: row["prototype_sequence"]
                for row in json.loads(trajectory_profiles.to_json(orient="records"))
            },
        },
        "feature_columns": CLUSTER_COLUMNS,
        "feature_labels": FEATURE_LABELS,
        "samples": json.loads(samples.to_json(orient="records")),
    }


def run_pipeline() -> dict[str, object]:
    paths = project_paths()
    data_path = paths["data_raw_dir"] / "LongitudinalEngagement.csv"
    if not data_path.exists():
        raise FileNotFoundError("Expected local LongitudinalEngagement.csv in data/raw before running the backend.")

    original_data = pd.read_csv(data_path)
    standardized = standardize_within_course(original_data)
    state_model_selection = evaluate_state_models(standardized[CLUSTER_COLUMNS])
    state_selection, _ = assign_states(standardized)

    state_profiles = (
        state_selection.groupby("State", as_index=False)[CLUSTER_COLUMNS].mean()
        .assign(StateID=lambda frame: frame["State"].map({name: idx + 1 for idx, name in enumerate(STATE_NAMES)}))
    )

    user_grades = original_data.groupby("UserID", as_index=False)["Final_Grade"].mean()
    sequence_table = create_state_sequences(state_selection)
    trajectory_validation, _, encoded = evaluate_trajectory_clusters(sequence_table)
    trajectory_labels = AgglomerativeClustering(n_clusters=TRAJECTORY_COUNT, linkage="ward").fit_predict(encoded)
    trajectory_profiles, trajectory_assignments = build_trajectory_profiles(sequence_table, trajectory_labels, user_grades)

    state_selection.to_csv(paths["data_processed_dir"] / "state_assignments.csv", index=False)
    sequence_table.to_csv(paths["data_processed_dir"] / "state_sequences.csv", index=False)
    state_model_selection.to_csv(paths["output_dir"] / "state_model_selection.csv", index=False)
    trajectory_validation.to_csv(paths["output_dir"] / "trajectory_validation.csv", index=False)
    state_profiles.to_csv(paths["output_dir"] / "state_profiles.csv", index=False)
    trajectory_profiles.to_csv(paths["output_dir"] / "trajectory_profiles.csv", index=False)
    trajectory_assignments.to_csv(paths["output_dir"] / "trajectory_assignments.csv", index=False)

    payload = build_dashboard_payload(
        original_data,
        state_selection,
        state_model_selection,
        state_profiles,
        trajectory_validation,
        trajectory_profiles,
        trajectory_assignments,
        sequence_table,
    )
    (paths["output_dir"] / "dashboard.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    payload = run_pipeline()
    print(json.dumps(payload["overview"], indent=2))