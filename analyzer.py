from scoring import calculate_score

from gemini_engine import (

    generate_reason,
    generate_functional_overview,
    generate_ztable_overview

)

from ztable_lookup import get_ztable_info


def analyze_code(
    code,
    summary=None
):

    score=calculate_score(
        code
    )

    if score<=40:

        complexity="LOW"

    elif score<=70:

        complexity="MEDIUM"

    else:

        complexity="HIGH"


    # -------------------------
    # Z table lookup
    # -------------------------

    ztable_details=get_ztable_info(
        code
    )


    # -------------------------
    # AI analysis
    # -------------------------

    reason=generate_reason(

        code,
        complexity,
        score

    )

    overview=generate_functional_overview(

        code

    )

    ztable_summary=generate_ztable_overview(

        ztable_details

    )


    return{

        "complexity":complexity,

        "score":score,

        "reason":reason,

        "overview":overview,

        "ztables":ztable_details,

        "ztable_summary":ztable_summary

    }