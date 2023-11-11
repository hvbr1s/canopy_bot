import json
import random

def convert_json_to_jsonl(json_file_path, jsonl_file_path):
    """
    Convert a JSON file to a JSONL file.

    Args:
    json_file_path (str): The path to the input JSON file.
    jsonl_file_path (str): The path to the output JSONL file.
    """
    try:
        # Read the JSON file
        with open(json_file_path, 'r') as json_file:
            data = json.load(json_file)

        # Write to a JSONL file
        with open(jsonl_file_path, 'w') as jsonl_file:
            for item in data:
                json.dump(item, jsonl_file)
                jsonl_file.write('\n')

        print(f"Conversion completed successfully. File saved as {jsonl_file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Go!
convert_json_to_jsonl("/home/dan/canopy/pinecone_pipeline/output_files/output.json", "/home/dan/canopy/pinecone_pipeline/output_files/output.jsonl")

def process_jsonl_file(jsonl_file_path):
    """
    Process a JSONL file to ensure unique IDs.

    Args:
    jsonl_file_path (str): The path to the JSONL file.
    """
    try:
        unique_ids = set()
        updated_lines = []

        with open(jsonl_file_path, 'r') as file:
            for line in file:
                data = json.loads(line)
                
                # Check if the ID is unique
                while data["id"] in unique_ids:
                    # Append a random number to make the ID unique
                    data["id"] += str(random.randint(0, 9))

                unique_ids.add(data["id"])
                updated_lines.append(json.dumps(data))

        # Write the updated data back to the file
        with open(jsonl_file_path, 'w') as file:
            for line in updated_lines:
                file.write(line + '\n')

        print("File processed successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Go!
process_jsonl_file("/home/dan/canopy/pinecone_pipeline/output_files/output.jsonl")

# Remove useless keys
def remove_specific_keys(jsonl_file_path, keys_to_remove):
    """
    Remove specific keys from each item in a JSONL file.

    Args:
    jsonl_file_path (str): The path to the JSONL file.
    keys_to_remove (list): A list of keys to remove from each item.
    """
    try:
        updated_lines = []

        with open(jsonl_file_path, 'r') as file:
            for line in file:
                data = json.loads(line)

                # Remove specified keys if they exist
                for key in keys_to_remove:
                    data.pop(key, None)

                updated_lines.append(json.dumps(data))

        # Write the updated data back to the file
        with open(jsonl_file_path, 'w') as file:
            for line in updated_lines:
                file.write(line + '\n')

        print("File updated successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Go!
remove_specific_keys("/home/dan/canopy/pinecone_pipeline/output_files/output.jsonl", ["source-type", "locale", "zd-article-id", "classification"])

