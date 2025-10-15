"""
Script to remove duplicate entries from cube_view_orchestrator.json based on entry_index.
Keeps the first occurrence of each entry_index.
"""

import json
from pathlib import Path


def remove_duplicate_entries(data):
    """
    Remove duplicate entries based on entry_index, keeping the first occurrence.

    Args:
        data (dict): The JSON data containing entries.

    Returns:
        dict: Data with duplicates removed.
    """
    entries = data.get("entries", [])
    seen_indices = set()
    unique_entries = []

    for entry in entries:
        entry_index = entry.get("entry_index")
        if entry_index not in seen_indices:
            seen_indices.add(entry_index)
            unique_entries.append(entry)
            print(f"Keeping entry_index: {entry_index}")
        else:
            print(f"Removing duplicate entry_index: {entry_index}")

    data["entries"] = unique_entries
    return data


def main():
    """Main function to remove duplicates from the JSON file."""
    # Path to the JSON file
    json_path = (
        Path(__file__).parent.parent.parent.parent
        / "source/wernicke/tests/evaluations/finance_analyst/datasets/golfstream/golfstream_easy/cube_view_orchestrator.json"
    )

    print(f"Reading from: {json_path}")

    # Read the JSON file
    with open(json_path, "r") as f:
        data = json.load(f)

    original_count = len(data.get("entries", []))
    print(f"\nOriginal entry count: {original_count}")

    # Remove duplicates
    data = remove_duplicate_entries(data)

    new_count = len(data.get("entries", []))
    print(f"\nNew entry count: {new_count}")
    print(f"Removed {original_count - new_count} duplicate entries")

    # Write back to the file
    print(f"\nWriting cleaned data back to: {json_path}")
    with open(json_path, "w") as f:
        json.dump(data, f, indent=3)

    print("✅ Successfully removed duplicate entries!")


if __name__ == "__main__":
    main()

