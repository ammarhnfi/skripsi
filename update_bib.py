import re

with open(r'd:\Skripsi\my\pustaka.bib', 'r', encoding='utf-8') as f:
    text = f.read()

updates = {
    'anselin1988': r',\n  url       = {https://link.springer.com/book/10.1007/978-94-015-7799-1}\n}',
    'pearson1901': r',\n  doi       = {10.1080/14786440109462720}\n}',
    'macqueen1967': r',\n  url       = {https://projecteuclid.org/journals/berkeley-symposium-on-mathematical-statistics-and-probability/volume-1/issue-1/Some-methods-for-classification-and-analysis-of-multivariate-observations/10.15115/D3S307.full}\n}',
    'johnson2007': r',\n  url       = {https://www.pearson.com/en-us/subject-catalog/p/applied-multivariate-statistical-analysis/P200000003290}\n}',
    'hair2019': r',\n  url       = {https://www.cengage.uk/c/multivariate-data-analysis-8e-hair-black-babin-anderson/9781473756540/}\n}',
    'anton2013': r',\n  url       = {https://www.wiley.com/en-us/Elementary+Linear+Algebra%3A+Applications+Version%2C+11th+Edition-p-9781118434413}\n}'
}

for key, val in updates.items():
    # Replace the last newline and brace of the entry with the new field and brace
    pattern = r'(@\w+\{' + key + r'.*?)\n\}'
    text = re.sub(pattern, lambda m: m.group(1) + val, text, flags=re.DOTALL)

with open(r'd:\Skripsi\my\pustaka.bib', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated pustaka.bib")
