import json

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
