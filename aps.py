import streamlit as st
import pandas as pd

from analyzer import analyze_code
from transformation_code import process_transformation
from lineage import generate_lineage


# -----------------------------------
# PAGE CONFIG
# -----------------------------------

st.set_page_config(

    page_title="BW Transformation Analyzer",
    layout="wide"

)


# -----------------------------------
# CUSTOM CSS
# -----------------------------------

st.markdown("""

<style>

.title{

font-size:48px;
font-weight:700;
color:white;

}

.subtitle{

font-size:18px;
color:#A0A0A0;
margin-bottom:30px;

}

.metric-card{

background:#161B22;
padding:20px;
border-radius:15px;
border:1px solid #30363D;
text-align:center;

}

</style>

""", unsafe_allow_html=True)


# -----------------------------------
# HEADER
# -----------------------------------

st.markdown(

"""
<div class='title'>
BW Transformation Analyzer
</div>
""",

unsafe_allow_html=True

)


st.markdown(

"""
<div class='subtitle'>
AI-powered BW Transformation Analysis
</div>
""",

unsafe_allow_html=True

)


# -----------------------------------
# Upload File
# -----------------------------------

uploaded_file=st.file_uploader(

    "Upload Excel File",

    type=[

        "xlsx",
        "xls"

    ]

)


# -----------------------------------
# Processing
# -----------------------------------

if uploaded_file:

    try:

        with st.spinner(

            "Analyzing..."

        ):


            data=process_transformation(

                uploaded_file

            )


            result=analyze_code(

                data["code"],
                data["summary"]

            )


        # --------------------------------
        # Complexity
        # --------------------------------

        col1,col2,col3=st.columns(

            [1,1,1]

        )


        with col2:


            st.markdown(

f"""

<div class='metric-card'>

<h3>Complexity</h3>

<h2>{result["complexity"]}</h2>

</div>

""",

unsafe_allow_html=True

)


        st.write("")


        # --------------------------------
        # Functional Overview
        # --------------------------------

        st.subheader(

            "Functional Overview"

        )


        st.info(

            result["overview"]

        )


        st.divider()


        # --------------------------------
        # AI Analysis
        # --------------------------------

        st.subheader(

            "AI Analysis"

        )


        st.markdown(

            result["reason"]

        )


        st.divider()


        # --------------------------------
        # Z table
        # --------------------------------

        if result.get(

            "ztables"

        ):


            st.subheader(

                "Custom Z Table Overview"

            )


            st.info(

                result["ztable_summary"]

            )


            st.divider()


        # --------------------------------
        # Transformation Summary
        # --------------------------------

        if data.get(

            "summary"

        ) is not None:


            st.subheader(

                "Transformation Summary"

            )


            st.dataframe(

                data["summary"],

                use_container_width=True

            )


            st.divider()


# ==================================
# BW LINEAGE
# ==================================

st.subheader(
    "BW Lineage"
)

query_name = st.text_input(
    "Enter BEx Query Name"
)

if query_name:

    lineage = generate_lineage(
        query_name
    )

    if lineage:

        st.markdown("### 📊 BW Lineage")

        tree_text = ""

        for i, (obj_type, obj_name) in enumerate(lineage):

            indent = "  " * i

            tree_text += (
                f"{indent}- **{obj_type}**\n"
                f"{indent}  - {obj_name}\n"
            )

        st.markdown(tree_text)

    else:

        st.warning(
            "No lineage found"
        )


        # --------------------------------
        # Download report
        # --------------------------------

        report=pd.DataFrame([{

            "Complexity":

            result["complexity"],

            "Overview":

            result["overview"],

            "AI Analysis":

            result["reason"],

            "Z Tables":

            result.get(

                "ztable_summary",
                ""

            )

        }])


        report_file="bw_analysis_report.xlsx"


        report.to_excel(

            report_file,
            index=False

        )


        with open(

            report_file,
            "rb"

        ) as file:


            st.download_button(

                label="📥 Download Report",

                data=file,

                file_name=report_file,

                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

            )


    except Exception as e:


        st.error(

            f"Application Error: {str(e)}"

        )