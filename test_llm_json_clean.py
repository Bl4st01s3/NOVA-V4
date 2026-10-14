def process(stream):
    has_started_printing = False
    startup_buffer = ""
    output = []

    for token in stream:
        if not has_started_printing:
            startup_buffer += token

            if len(startup_buffer.strip()) < 3:
                continue

            import re
            clean_start = startup_buffer.lstrip(' \n\r\t".,!?;:-')
            clean_start = re.sub(r'^([a-zA-Z])\s*[\n\r]+\s*', '', clean_start)
            clean_start = re.sub(r'^([a-zA-Z])\.\s+', '', clean_start)
            clean_start = re.sub(r'^([a-z])\s+(?=[a-zA-Z])', '', clean_start)
            clean_start = re.sub(r'^([B-HJ-ZB-HJ-Z])\s+(?=[a-zA-Z])', '', clean_start)
            clean_start = clean_start.lstrip(' \n\r\t".,!?;:-')

            if not clean_start:
                startup_buffer = ""
                continue

            token = clean_start
            has_started_printing = True

            if not token.strip('. ,!?;:-\n\r\t"'):
                has_started_printing = False
                startup_buffer = ""
                continue

        output.append(token)
    return "".join(output)

print(repr(process(["e", "\n", "\n", "I", "'m"])))
print(repr(process(["e", " ", "\n", "I", "'m"])))
print(repr(process(["e", " ", "I", "'m"])))
print(repr(process(["e", "I", "'m"])))
