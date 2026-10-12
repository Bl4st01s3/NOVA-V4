import re
def clean(startup_buffer):
    clean_start = startup_buffer.lstrip(' \n\r\t".,!?;:-')
    clean_start = re.sub(r'^([a-zA-Z])\s*[\n\r]+\s*', '', clean_start)
    clean_start = re.sub(r'^([a-zA-Z])\.\s+', '', clean_start)
    clean_start = re.sub(r'^([b-hj-zB-HJ-Z])\s+(?=[a-zA-Z])', '', clean_start)
    clean_start = clean_start.lstrip(' \n\r\t".,!?;:-')
    return clean_start

def process(stream):
    has_started_printing = False
    startup_buffer = ""
    output = []

    for token in stream:
        if not has_started_printing:
            startup_buffer += token

            if len(startup_buffer.strip()) < 3:
                continue

            clean_start = clean(startup_buffer)

            if not clean_start:
                startup_buffer = ""
                continue

            token = clean_start
            has_started_printing = True

        output.append(token)
    return "".join(output)

print("1:", repr(process(["g", "\n", "\n", "I", "'m"])))
print("2:", repr(process(["s", " ", "\n", "Y", "e", "s"])))
print("3:", repr(process(["I", "\n", "\n", "O", "k"])))
print("4:", repr(process(["W", "e", "l", "l"])))
