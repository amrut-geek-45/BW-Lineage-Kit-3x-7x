import streamlit as st
from lineage import generate_lineage

st.set_page_config(
    page_title="BW Lineage",
    layout="wide"
)

st.title("BW Lineage Explorer")

query_name = st.text_input(
    "Enter Query Name / Query ID"
)

if query_name:

    lineage = generate_lineage(query_name)

    if lineage:

        st.subheader("Lineage")

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