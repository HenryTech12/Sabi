import json

path = r"C:\Users\DELL\Documents\SABI\sabi\data\amazon_reviews_processed.jsonl"
with open(path, 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if i >= 3: break  # Look at the first 3 lines
        data = json.loads(line)
        print(f"--- Entry {i} ---")
        print(data.keys())
        # Print the first user's ID to see how it's stored
        print(f"Sample ID: {data.get('reviewer_id', 'KEY_NOT_FOUND')}")