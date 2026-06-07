import csv
import json
import os

def process_csv_to_jsonl():
    input_csv = "amazon_reviews.csv"
    output_jsonl = "data/amazon_reviews_processed.jsonl"
    os.makedirs('data', exist_ok=True)

    print(f"Reading {input_csv}...")

    with open(input_csv, 'r', encoding='utf-8', errors='replace') as f:
        # Use csv.reader for better handling of malformed lines
        reader = csv.reader(f)
        header = next(reader)  # Skip the header row
        
        count = 0
        with open(output_jsonl, 'w', encoding='utf-8') as out:
            for row in reader:
                try:
                    # Adjust these indices [0], [1], etc., 
                    # based on the column order in your specific CSV file
                    # Change the mapping in process_csv.py to this:
                    # Update this section inside your process_csv.py script
                    record = {
                        "reviewer_id": row[1],         # Profile Link
                        "product_id": "prod_unknown",
                        "rating": 3.0,                 # We can refine this later if you need the actual stars
                        "text": row[7],                # Column 7 is the actual Review Text
                        "review_title": row[6],        # Column 6 is the Review Title
                        "product_category": "General"
                    }
                    out.write(json.dumps(record) + "\n")
                    count += 1
                except IndexError:
                    # Skip lines that are too short/malformed
                    continue
                    
        print(f"Success! {count} records saved to {output_jsonl}")

if __name__ == "__main__":
    process_csv_to_jsonl()