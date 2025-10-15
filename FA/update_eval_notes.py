"""
Script to update eval_notes in cube_view_orchestrator.json to include artifact data and expansion explanations.
"""

import json
import sys
from pathlib import Path

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


def format_artifact_data_as_text(artifact_data):
    """
    Format the artifact_data dict as a readable text representation.

    Args:
        artifact_data (dict): The artifact data from expected_outputs.

    Returns:
        str: Formatted artifact data string.
    """
    if not artifact_data or "artifact_data" not in artifact_data:
        return ""

    # Navigate to the nested artifact_data that contains rows, columns, pov
    # Structure is: expected_output -> artifact_data -> artifact_data -> {rows, columns, pov}
    outer_artifact = artifact_data["artifact_data"]
    if not outer_artifact or "artifact_data" not in outer_artifact:
        return ""

    data = outer_artifact["artifact_data"]

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


def update_eval_notes(entry, force_update=False):
    """
    Update the eval_notes field for an entry with artifact data and expansion explanations.

    Args:
        entry (dict): An entry from the entries array.
        force_update (bool): If True, update even if expansion explanations already exist.

    Returns:
        dict: Updated entry with new eval_notes.
    """
    # Get the original eval notes (if they exist, preserve them at the top)
    original_eval_notes = entry["inputs"].get("eval_notes", "")

    # Check if it already has the expansion explanations
    if "## Member Expansion Functions Explained:" in original_eval_notes and not force_update:
        print(f"  Entry {entry.get('entry_index', '?')} already has expansion explanations, skipping...")
        return entry

    # Clean up any existing artifact data or expansion explanations to avoid duplication
    # Extract only the original instructions (before any artifact data or expansions)

    # List of markers that indicate start of sections we want to remove
    markers = ["Here is the ideal output in Artifact Form:", "Here is the Idea output in Artifact Form:", "## Member Expansion Functions Explained:"]

    # Find the earliest marker
    earliest_pos = len(original_eval_notes)
    for marker in markers:
        pos = original_eval_notes.find(marker)
        if pos != -1 and pos < earliest_pos:
            earliest_pos = pos

    # Keep only content before the earliest marker
    if earliest_pos < len(original_eval_notes):
        original_eval_notes = original_eval_notes[:earliest_pos].rstrip()

    # Get the first expected output's artifact data
    expected_outputs = entry.get("expected_outputs", [])
    if not expected_outputs:
        print(f"  Entry {entry.get('entry_index', '?')} has no expected outputs, skipping...")
        return entry

    first_output = expected_outputs[0]
    artifact_text = format_artifact_data_as_text(first_output)

    # Build the new eval_notes (artifact data + expansion explanations only)
    new_eval_notes = artifact_text + "\n" + EXPANSION_EXPLANATIONS

    entry["inputs"]["eval_notes"] = new_eval_notes
    return entry


def main():
    """Main function to update the JSON file."""
    # Check for --force flag
    force_update = "--force" in sys.argv

    # Path to the JSON file
    json_path = (
        Path(__file__).parent.parent.parent.parent
        / "source/wernicke/tests/evaluations/finance_analyst/datasets/golfstream/golfstream_easy/cube_view_orchestrator.json"
    )

    if not json_path.exists():
        print(f"Error: File not found at {json_path}")
        sys.exit(1)

    print(f"Reading from: {json_path}")
    if force_update:
        print("Force update mode enabled - will re-update all entries")

    # Read the JSON file
    with open(json_path, "r") as f:
        data = json.load(f)

    # Update each entry
    entries = data.get("entries", [])
    print(f"Found {len(entries)} entries to process")

    for i, entry in enumerate(entries):
        print(f"Processing entry {entry.get('entry_index', i)}...")
        entries[i] = update_eval_notes(entry, force_update=force_update)

    data["entries"] = entries

    # Write back to the file
    print(f"\nWriting updated data back to: {json_path}")
    with open(json_path, "w") as f:
        json.dump(data, f, indent=3)

    print("✅ Successfully updated all eval_notes!")


if __name__ == "__main__":
    main()
