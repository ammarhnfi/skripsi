import re
import json
import os

def clean_latex_title(text):
    # Remove \textit{...} and keep the inside text
    text = re.sub(r'\\textit\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\\textit\s*([a-zA-Z0-9]+)', r'\1', text)
    # Remove \textbf{...} and keep the inside text
    text = re.sub(r'\\textbf\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\\textbf\s*([a-zA-Z0-9]+)', r'\1', text)
    # Replace \_ with a space
    text = text.replace(r'\_', ' ')
    text = text.replace(r'_', ' ')
    # Remove any stray curly braces
    text = text.replace('{', '').replace('}', '')
    # Remove stray backslashes
    text = text.replace('\\', '')
    # Normalize spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

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
            # Match nested braces up to 1 level (e.g. \textit{Dendrogram})
            secs = re.findall(r'\\(?:section|subsection)\{(?:\\normalsize\s+)?((?:[^{}]|\{[^{}]*\})*)\}', preceding_text)
            section = secs[-1] if secs else "General"
            section = clean_latex_title(section)
            
            eq_content = match.group(1).strip()
            # Clean up labels from the content for display
            display_content = re.sub(r'\\label\{.*?\}', '', eq_content).strip()
            
            if eq_type == 'align':
                latex_str = f"\\[ \\begin{{aligned}} {display_content} \\end{{aligned}} \\]"
            elif eq_type == 'gather':
                latex_str = f"\\[ \\begin{{gathered}} {display_content} \\end{{gathered}} \\]"
            else:
                latex_str = f"\\[ {display_content} \\]"
                
            all_eqs.append({
                'section': section,
                'latex': latex_str,
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
