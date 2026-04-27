import re
import json
import os

def extract_equations(file_path):
    if not os.path.exists(file_path):
        return []
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all math environments
    # 1. \begin{equation} ... \end{equation}
    # 2. \begin{align} ... \end{align}
    # 3. \begin{gather} ... \end{gather}
    # 4. \[ ... \]
    
    environments = [
        (r'\\begin\{equation\}(.*?)\\end\{equation\}', 'equation'),
        (r'\\begin\{align\}(.*?)\\end\{align\}', 'align'),
        (r'\\begin\{gather\}(.*?)\\end\{gather\}', 'gather'),
        (r'\\\[(.*?)\\\]', 'displaymath')
    ]
    
    all_eqs = []
    
    for pattern, eq_type in environments:
        for match in re.finditer(pattern, content, re.DOTALL):
            # find what section this is in
            preceding_text = content[:match.start()]
            secs = re.findall(r'\\(?:section|subsection)\{(?:\\normalsize\s+)?(.*?)\}', preceding_text)
            section = secs[-1] if secs else "General"
            section = section.replace('{', '').replace('}', '').strip()
            
            eq_content = match.group(1).strip()
            # Clean up labels from the content for display
            display_content = re.sub(r'\\label\{.*?\}', '', eq_content).strip()
            
            all_eqs.append({
                'section': section,
                'latex': f"\\[ {display_content} \\]",
                'type': eq_type,
                'raw': eq_content
            })

    return all_eqs

if __name__ == "__main__":
    bab2_path = r"d:\Skripsi\my\bab2.tex"
    output_path = r"d:\Skripsi\my\landing-page\public\equations.json"
    
    if os.path.exists(bab2_path):
        eqs = extract_equations(bab2_path)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(eqs, f, indent=2)
        print(f"Extracted {len(eqs)} equations from {bab2_path} to {output_path}")
    else:
        print(f"File not found: {bab2_path}")
