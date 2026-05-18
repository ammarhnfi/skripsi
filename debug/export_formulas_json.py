import json
import os
import sys

# Add debug directory to path to import formulas_dashboard
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from formulas_dashboard import FORMULAS

if __name__ == "__main__":
    output_path = r"d:\Skripsi\my\landing-page\public\formulas_substitusi.json"
    
    # Save the computed formulas list to JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(FORMULAS, f, indent=2)
        
    print(f"Successfully exported {len(FORMULAS)} formulas with substitutions to {output_path}")
