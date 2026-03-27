import re
import json
import os

def extract_equations(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all sections/subsections to give context
    sections = re.split(r'\\(section|subsection)\{.*?\}', content)
    section_names = re.findall(r'\\(?:section|subsection)\{(?:\\normalsize\s+)?(.*?)\}', content)
    
    # Simple extraction of equations
    # We look for \begin{equation} ... \end{equation}
    # and also \begin{definition} ... \end{definition} since they often contain math
    
    equations = []
    
    # Pattern for equations
    eq_pattern = re.compile(r'\\begin\{equation\}(.*?)\\end\{equation\}', re.DOTALL)
    
    # Pattern for definitions/theorems (optional, but good for context)
    def_pattern = re.compile(r'\\begin\{(definition|theorem|remark)\}(.*?)\\end\{\1\}', re.DOTALL)

    # Let's just find everything between \section to keep it organized
    current_section = "General"
    
    # Iterate through lines to find equations and track section
    lines = content.split('\n')
    for line in lines:
        sec_match = re.match(r'\\(?:section|subsection)\{(?:\\normalsize\s+)?(.*?)\}', line)
        if sec_match:
            current_section = sec_match.group(1).replace('{', '').replace('}', '')
            
    # Actually, a better way is to regex find all matches and their positions
    all_eqs = []
    
    # Find equations
    for match in eq_pattern.finditer(content):
        # find what section this is in
        preceding_text = content[:match.start()]
        secs = re.findall(r'\\(?:section|subsection)\{(?:\\normalsize\s+)?(.*?)\}', preceding_text)
        section = secs[-1] if secs else "General"
        section = section.replace('{', '').replace('}', '')
        
        all_eqs.append({
            'section': section,
            'latex': f"\\[ {match.group(1).strip()} \\]",
            'type': 'equation'
        })

    return all_eqs

if __name__ == "__main__":
    bab2_path = r"d:\Skripsi\my\bab2.tex"
    output_path = r"d:\Skripsi\my\landing-page\public\equations.json"
    
    if os.path.exists(bab2_path):
        eqs = extract_equations(bab2_path)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(eqs, f, indent=2)
        print(f"Extracted {len(eqs)} equations to {output_path}")
    else:
        print(f"File not found: {bab2_path}")
