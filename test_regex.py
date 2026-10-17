import re

tests = [
    "c\n",
    "c ",
    "c\n\nYes sir",
    "i\nI have checked",
    "g\n\n",
    "A\n",
    "B\n",
    "c\nYes",
    ". c\n",
]

for t in tests:
    clean = t.lstrip(' \n\r\t".,!?;:-')
    clean = re.sub(r'^([a-zA-Z])\s*[\n\r]+\s*', '', clean)
    clean = re.sub(r'^([a-zA-Z])\.\s*', '', clean)
    clean = re.sub(r'^([a-z])[\s\n\r]+', '', clean)
    clean = re.sub(r'^([B-HJ-Z])[\s\n\r]+', '', clean)
    clean = clean.lstrip(' \n\r\t".,!?;:-')
    print(f"Original: {repr(t)} -> Cleaned: {repr(clean)}")
