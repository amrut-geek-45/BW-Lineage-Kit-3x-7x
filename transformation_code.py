import pandas as pd
import os

REFERENCE_FOLDER = "Reference_Folder_Trans_Id"
OUTPUT_FOLDER = "output_txt_files"

os.makedirs(
    OUTPUT_FOLDER,
    exist_ok=True
)


def process_transformation(uploaded_file):

    # -----------------------------------
    # Read uploaded Excel
    # -----------------------------------

    df = pd.read_excel(
        uploaded_file
    )

    # -----------------------------------
    # Get CODEID
    # -----------------------------------

    code_id = str(
        df.iloc[1, 0]
    ).strip()

    # -----------------------------------
    # Extract D Column
    # -----------------------------------

    d_column_data = (

        df.iloc[:, 3]
        .dropna()
        .astype(str)

    )

    text_content = "\n".join(
        d_column_data
    )

    # -----------------------------------
    # Save TXT
    # -----------------------------------

    txt_file_path = os.path.join(

        OUTPUT_FOLDER,
        f"{code_id}.txt"

    )

    with open(

        txt_file_path,
        "w",
        encoding="utf-8"

    ) as f:

        f.write(
            text_content
        )

    # -----------------------------------
    # Read Reference File
    # -----------------------------------

    reference_file = os.path.join(

        REFERENCE_FOLDER,
        "ZBW_TRFN_COMPLEXITY_LOG.txt"

    )

    result_df = None

    if os.path.exists(
        reference_file
    ):

        with open(
            reference_file,
            "r",
            encoding="utf-8"
        ) as f:

            lines = f.readlines()

        header_index = None

        for i, line in enumerate(lines):

            if "VALUE / CODEID" in line:

                header_index = i
                break

        if header_index is not None:

            ref_df = pd.read_csv(

                reference_file,
                sep="|",
                skiprows=header_index,
                dtype=str,
                engine="python"

            )

            # --------------------------
            # Clean column names
            # --------------------------

            ref_df.columns = [

                col.strip()

                for col in ref_df.columns

            ]

            ref_df = ref_df.fillna("")

            # --------------------------
            # Find CODEID column
            # --------------------------

            codeid_column = None

            for col in ref_df.columns:

                if "VALUE / CODEID" in col:

                    codeid_column = col
                    break

            # --------------------------
            # Match CODEID
            # --------------------------

            if codeid_column:

                matched_df = ref_df[

                    ref_df[
                        codeid_column
                    ].str.contains(

                        code_id,
                        case=False,
                        na=False

                    )

                ]

                # --------------------------
                # Select required columns
                # --------------------------

                if not matched_df.empty:

                    result_df = matched_df[[

                        "SOURCE NAME",
                        "SOURCE FIELD NAME",
                        "SOURCE TYPE",
                        "TARGET NAME",
                        "TARGET FIELD NAME",
                        "TARGET TYPE"

                    ]]

                    # Rename columns

                    result_df.columns = [

                        "SOURCE NAME",
                        "SOURCE FIELD NAME",
                        "SOURCE TYPE",
                        "TARGET NAME",
                        "TARGET FIELD NAME",
                        "TARGET TYPE"

                    ]

    # -----------------------------------
    # Return
    # -----------------------------------

    return {

        "code": text_content,

        "code_id": code_id,

        "summary": result_df

    }