def report_agent(name, tagline, pitch, audience, brand):
    return {
        "name": name,
        "tagline": tagline,
        "pitch": pitch,
        "audience": audience,
        "problem": pitch.split('.')[0] if '.' in pitch else pitch,
        "solution": pitch.split('.')[1] if '.' in pitch else "",
        "brand": brand
    }
