def calculate_score(code):

    code = code.upper()

    score = 0

    score += code.count("SELECT") * 3
    score += code.count("LOOP AT") * 2
    score += code.count("CALL FUNCTION") * 5
    score += code.count("READ TABLE") * 3
    score += code.count("IF ") * 1
    score += code.count("CASE") * 1
    score += code.count("WHILE") * 3
    score += code.count("MODIFY") * 1
    score += code.count("DELETE") * 1

    return score