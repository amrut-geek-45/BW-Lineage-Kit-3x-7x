import pandas as pd
import os
import glob

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

META_FOLDER = os.path.join(
    BASE_DIR,
    "Meta_Data_File"
)


# --------------------------------
# Read CSV safely
# --------------------------------

def read_file(file_path):

    encodings=[

        "utf-8",
        "latin1",
        "cp1252",
        "ISO-8859-1"

    ]

    for enc in encodings:

        try:

            return pd.read_csv(

                file_path,
                encoding=enc,
                engine="python",
                on_bad_lines="skip"

            )

        except:

            continue

    return None


# --------------------------------
# Find files
# --------------------------------

def get_file(pattern):

    files=glob.glob(

        os.path.join(

            META_FOLDER,
            pattern

        )

    )

    return files[0] if files else None


# --------------------------------
# Generate lineage
# --------------------------------

def generate_lineage(query_input):

    lineage=[]


    # ------------------------
    # Query
    # ------------------------

    query_file=get_file(
        "*Query*.csv"
    )

    query_df=read_file(
        query_file
    )

    query_df=query_df.astype(
        str
    )


    result=query_df[

        (

            query_df["QUERYNAME"]

            .str.contains(

                query_input,
                case=False,
                na=False

            )

        )

        |

        (

            query_df["QUERYID"]

            .str.contains(

                query_input,
                case=False,
                na=False

            )

        )

    ]


    if result.empty:

        return []


    query_name=result.iloc[0][
        "QUERYNAME"
    ]


    provider=result.iloc[0][
        "INFOPROVIDER"
    ]


    lineage.append(

        (

            "BEx Query",
            query_name

        )

    )


    lineage.append(

        (

            "InfoProvider",
            provider

        )

    )


    # ------------------------
    # MultiProvider
    # ------------------------

    mp_file=get_file(
        "*MultiProvider*.csv"
    )

    if mp_file:

        mp_df=read_file(
            mp_file
        )

        mp_df=mp_df.astype(
            str
        )


        match=mp_df.apply(

            lambda x:

            x.str.contains(

                provider,
                case=False,
                na=False

            )

        )


        res=mp_df[
            match.any(axis=1)
        ]


        if not res.empty:

            lineage.append(

                (

                    "MultiProvider",
                    res.iloc[0,0]

                )

            )


    # ------------------------
    # InfoCube
    # ------------------------

    cube_file=get_file(
        "*Infocube*.csv"
    )

    if cube_file:

        cube_df=read_file(
            cube_file
        )

        lineage.append(

            (

                "InfoCube",
                cube_df.iloc[0,0]

            )

        )


    # ------------------------
    # ADSO
    # ------------------------

    adso_file=get_file(
        "*ADSO*.csv"
    )

    if adso_file:

        adso_df=read_file(
            adso_file
        )

        lineage.append(

            (

                "ADSO",
                adso_df.iloc[0,0]

            )

        )


    # ------------------------
    # Transformation
    # ------------------------

    trans_file=get_file(
        "*TRANSFORMATION*.csv"
    )

    if trans_file:

        trans_df=read_file(
            trans_file
        )

        lineage.append(

            (

                "Transformation",
                trans_df.iloc[0,0]

            )

        )


    # ------------------------
    # InfoPackage
    # ------------------------

    ip_file=get_file(
        "*InfoPackage*.csv"
    )

    if ip_file:

        ip_df=read_file(
            ip_file
        )

        lineage.append(

            (

                "InfoPackage",
                ip_df.iloc[0,0]

            )

        )


        if len(ip_df.columns)>1:

            lineage.append(

                (

                    "Source System",
                    ip_df.iloc[0,1]

                )

            )


    return lineage