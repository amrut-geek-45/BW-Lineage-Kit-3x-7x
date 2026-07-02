import pandas as pd
import re
import os

ZTABLE_FOLDER = "Z_Cust_Table"
ZTAB_FILE = "Z_Cust_Tables.csv"


def get_ztable_info(code):

    file_path = os.path.join(
        ZTABLE_FOLDER,
        ZTAB_FILE
    )

    if not os.path.exists(
        file_path
    ):

        return []

    try:

        # -------------------------
        # Read CSV
        # -------------------------

        df = pd.read_csv(
            file_path
        )

        df.columns = [

            col.strip().upper()

            for col in df.columns

        ]

        # -------------------------
        # Extract Z names from code
        # -------------------------

        detected_tables = sorted(

            set(

                re.findall(
                    r'\bZ[A-Z0-9_]+\b',
                    code.upper()
                )

            )

        )

        results = []

        # -------------------------
        # Match against CSV only
        # -------------------------

        for table in detected_tables:

            match = df[

                df[
                    "TABLENAME"
                ]
                .str.upper()
                == table

            ]

            if not match.empty:

                description = (

                    match.iloc[0][
                        "DESCRIPTION"
                    ]
                )

                fields = (

                    match[
                        "FIELDNAME"
                    ]
                    .head(10)
                    .tolist()
                )

                datatypes = (

                    match[
                        "DATATYPE"
                    ]
                    .head(10)
                    .tolist()
                )

                overview=[]

                for f,d in zip(
                    fields,
                    datatypes
                ):

                    overview.append(
                        f"{f} ({d})"
                    )

                results.append({

                    "table":table,
                    "description":description,
                    "overview":", ".join(
                        overview
                    )

                })

        return results

    except Exception as e:

        print(e)

        return []