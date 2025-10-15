#!/usr/bin/env python3
"""
Script to extract data from experimental entry_id_<index> directories and add them
to the cube_view_orchestrator.json evaluation file.

This script will:
1. Read the question from inputs.json
2. Format eval_notes using the FIRST artifact from results.json + expansion explanations
3. Add all unique artifacts from results.json as expected_outputs
"""

import json
import os
import sys

# Set the entry index to process (change this to match your CURRENT_INDEX)
ENTRY_INDEX = 0

# Expansion explanations template
EXPANSION_EXPLANATIONS = """
## Member Expansion Functions Explained:

1. .Base - Includes all members at the lowest level in the hierarchy, ignoring any parent or 
   intermediate categories. Base members are the most detailed and granular members in the 
   hierarchy. Base members will represent a single level of granularity at the lowest level 
   below the selected member.

2. .ChildrenInclusive - Includes the selected member and only its immediate child members 
   (the next level down). Children will represent a single level of granularity.

3. .Children - Only includes the immediate children of the selected member and not the 
   selected member itself. Does not include any grandchildren or other levels of the hierarchy.

4. .Tree - Includes the selected member and all members in every level below it.

Note: Expansion functions should NEVER be applied to Time dimension members or Dimension Member Groupings.
"""


def format_artifact_data_as_text(artifact_data: dict) -> str:
    """
    Format the artifact_data dict as a readable text representation.

    Args:
        artifact_data (dict): The artifact data from results.

    Returns:
        str: Formatted artifact data string.
    """
    if not artifact_data or "artifact_data" not in artifact_data:
        return ""

    data = artifact_data["artifact_data"]

    # Extract the key fields with proper indentation
    rows_str = json.dumps(data.get("rows", []), indent=2)
    columns_str = json.dumps(data.get("columns", []), indent=2)
    pov_str = json.dumps(data.get("pov", {}), indent=2)

    # Indent each line of the JSON dumps for consistent formatting
    rows_lines = rows_str.split("\n")
    rows_indented = "\n      ".join(rows_lines)

    columns_lines = columns_str.split("\n")
    columns_indented = "\n      ".join(columns_lines)

    pov_lines = pov_str.split("\n")
    pov_indented = "\n      ".join(pov_lines)

    formatted = f"""    Here is the ideal output in Artifact Form:
    <artifact_data>
    "rows": {rows_indented},
    "columns": {columns_indented},
    "pov": {pov_indented}
    </artifact_data>
    """

    return formatted


def load_json_file(file_path: str) -> dict:
    """Load JSON data from a file."""
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}: {e}")
        sys.exit(1)


def save_json_file(file_path: str, data: dict) -> None:
    """Save JSON data to a file."""
    with open(file_path, "w") as f:
        json.dump(data, f, indent=3, default=str)
    print(f"✅ Updated {file_path}")


def extract_entry_data(entry_dir: str) -> tuple:
    """
    Extract inputs and results data from an entry directory.

    Args:
        entry_dir: Path to the entry_id_<index> directory

    Returns:
        tuple: (inputs_data, results_data)
    """
    inputs_path = os.path.join(entry_dir, "inputs.json")
    results_path = os.path.join(entry_dir, "results.json")

    if not os.path.exists(inputs_path):
        print(f"Error: inputs.json not found in {entry_dir}")
        sys.exit(1)

    if not os.path.exists(results_path):
        print(f"Error: results.json not found in {entry_dir}")
        sys.exit(1)

    inputs_data = load_json_file(inputs_path)
    results_data = load_json_file(results_path)

    return inputs_data, results_data


def create_evaluation_entry(entry_index: int, inputs_data: dict, results_data: list) -> dict:
    """
    Create a new evaluation entry from the experimental data.

    Args:
        entry_index: The entry index number
        inputs_data: Data from inputs.json
        results_data: Data from results.json (list of artifacts)

    Returns:
        dict: Formatted evaluation entry
    """
    # Extract the question from inputs
    question = inputs_data.get("question", "")

    # Format eval_notes from the first artifact + expansion explanations
    eval_notes = ""
    if results_data and len(results_data) > 0:
        first_result = results_data[0]
        if first_result and first_result.get("artifact_data"):
            artifact_text = format_artifact_data_as_text(first_result["artifact_data"])
            eval_notes = artifact_text + "\n" + EXPANSION_EXPLANATIONS

    # Fallback if no artifact data
    if not eval_notes:
        eval_notes = EXPANSION_EXPLANATIONS

    # Create the entry structure
    entry = {
        "dataset": "golfstream_easy",
        "entry_index": entry_index,
        "inputs": {
            "orchestrator_settings": {"error_handling_active": False},
            "graph_state": {"user_input": question, "persona_id": None, "smart_cube_identification_setting": "off", "time_scope": "none"},
            "eval_notes": eval_notes,
        },
        "expected_outputs": [],
    }

    # Add unique results as expected outputs
    for result in results_data:
        if result is not None and result.get("artifact_data"):
            entry["expected_outputs"].append({"artifact_data": result["artifact_data"]})

    return entry


def add_entry_to_evaluation(entry_index: int, entry_dir: str, eval_file: str) -> None:
    """
    Add an experimental entry to the evaluation JSON file.

    Args:
        entry_index: The entry index number
        entry_dir: Path to the entry_id_<index> directory
        eval_file: Path to the cube_view_orchestrator.json file
    """
    print(f"📁 Processing entry_id_{entry_index} from {entry_dir}")

    # Extract data from experimental directory
    inputs_data, results_data = extract_entry_data(entry_dir)

    print(f"   - Question: {inputs_data.get('question', 'N/A')}")
    print(f"   - Results: {len(results_data)} artifacts")
    print(f"   - Eval notes: Generated from first artifact + expansion explanations")

    # Load existing evaluation file
    eval_data = load_json_file(eval_file)

    # Remove any existing entry with the same entry_index
    original_count = len(eval_data["entries"])
    eval_data["entries"] = [entry for entry in eval_data["entries"] if entry.get("entry_index") != entry_index]
    removed_count = original_count - len(eval_data["entries"])

    if removed_count > 0:
        print(f"   - Removed {removed_count} existing entry(ies) with entry_index {entry_index}")

    # Create new evaluation entry
    new_entry = create_evaluation_entry(entry_index, inputs_data, results_data)

    # Add to evaluation file
    eval_data["entries"].append(new_entry)

    # Save updated evaluation file
    save_json_file(eval_file, eval_data)

    print(f"✅ Added entry_index {entry_index} to evaluation file")


def main():
    """Main function to process the configured entry index."""
    # Paths
    base_dir = "/wernicke/experimentation/aiden_playground/FA"
    eval_file = "/wernicke/source/wernicke/tests/evaluations/finance_analyst/datasets/golfstream/golfstream_easy/cube_view_orchestrator.json"

    # Process the configured entry index
    entry_dir = os.path.join(base_dir, "eval_data", f"entry_id_{ENTRY_INDEX}")

    if not os.path.exists(entry_dir):
        print(f"❌ Directory not found: {entry_dir}")
        print(f"Make sure entry_id_{ENTRY_INDEX} exists in {base_dir}/eval_data/")
        sys.exit(1)

    print(f"🚀 Processing entry_id_{ENTRY_INDEX}")
    add_entry_to_evaluation(ENTRY_INDEX, entry_dir, eval_file)
    print(f"\n🎉 Successfully processed entry_id_{ENTRY_INDEX}!")


if __name__ == "__main__":
    main()
