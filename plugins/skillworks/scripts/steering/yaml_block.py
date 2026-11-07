# Only the last block counts, because a Steering file's settings sit at its end and a block above them is an example.
def last_yaml_span(lines):
    fences = [at for at, line in enumerate(lines) if line.strip().startswith("```")]
    opens = [at for at in fences if lines[at].strip() == "```yaml"]
    if not opens:
        return None
    start = opens[-1] + 1
    return start, next((at for at in fences if at > start), len(lines))
