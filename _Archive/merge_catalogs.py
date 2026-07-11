import json
import glob
import os

def merge_json_files():
    # Find all batch JSON files in the current directory
    files = glob.glob("*_batch_*.json")
    unified_catalog = []
    
    print(f"Found {len(files)} files to merge.")
    
    total_entries = 0
    for file in files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Ensure data is a list
                if isinstance(data, list):
                    for item in data:
                        # Standardize structure if needed, or just append
                        # We can add an internal tracking ID if we want
                        unified_catalog.append(item)
                    
                    total_entries += len(data)
                    print(f"Loaded {len(data)} entries from {file}")
        except Exception as e:
            print(f"Error processing {file}: {str(e)}")
            
    # Basic deduplication (if any exact duplicates exist based on source + reference)
    seen = set()
    deduped_catalog = []
    
    for item in unified_catalog:
        source = item.get('source', 'Unknown')
        ref = item.get('reference', 'Unknown')
        
        unique_key = f"{source}-{ref}"
        
        if unique_key not in seen:
            seen.add(unique_key)
            deduped_catalog.append(item)
            
    print(f"\nTotal entries before deduplication: {total_entries}")
    print(f"Total entries after deduplication: {len(deduped_catalog)}")
    
    # Save the unified catalog
    output_file = "unified_raw_catalog.json"
    with open(output_file, 'w', encoding='utf-8') as out_f:
        json.dump(deduped_catalog, out_f, indent=2, ensure_ascii=False)
        
    print(f"Successfully saved merged catalog to {output_file}")

if __name__ == "__main__":
    merge_json_files()
