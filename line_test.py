import os
import pandas as pd
import networkx as nx
from pyvis.network import Network


# ----------------------------------------
# PATH
# ----------------------------------------

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATA_FOLDER = os.path.join(
    BASE_DIR,
    "Meta_Data_File"
)


# ----------------------------------------
# SAFE FILE READER
# ----------------------------------------

def read_file(file_path):

    try:

        extension = os.path.splitext(
            file_path
        )[1].lower()


        # CSV

        if extension == ".csv":

            encodings = [

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


        # XLS

        elif extension == ".xls":

            return pd.read_excel(

                file_path,
                engine="xlrd"

            )


        # XLSX

        elif extension == ".xlsx":

            return pd.read_excel(

                file_path,
                engine="openpyxl"

            )


    except Exception as e:

        print(
            f"Read Error: {e}"
        )

    return None


# ----------------------------------------
# GRAPH
# ----------------------------------------

G = nx.DiGraph()


# ----------------------------------------
# READ FILES
# ----------------------------------------

for file_name in os.listdir(DATA_FOLDER):

    if file_name.endswith(

        (".csv",".xls",".xlsx")

    ):

        file_path = os.path.join(

            DATA_FOLDER,
            file_name

        )

        df = read_file(
            file_path
        )

        if df is None:

            continue


        df = df.astype(str)

        print(
            f"Processing: {file_name}"
        )


        # --------------------------------
        # QUERY
        # --------------------------------

        if (

            "QUERYNAME" in df.columns
            and
            "INFOPROVIDER" in df.columns

        ):

            for _,row in df.iterrows():

                G.add_edge(

                    row["QUERYNAME"],
                    row["INFOPROVIDER"],
                    label="USES"

                )


        # --------------------------------
        # DTP
        # --------------------------------

        if (

            "DTP" in df.columns
            and
            "SRC" in df.columns
            and
            "TGT" in df.columns

        ):

            for _,row in df.iterrows():

                G.add_edge(

                    row["SRC"],
                    row["DTP"],
                    label="LOADS"

                )


                G.add_edge(

                    row["DTP"],
                    row["TGT"],
                    label="TARGET"

                )


        # --------------------------------
        # TRANSFORMATION
        # --------------------------------

        if (

            "TRANID" in df.columns
            and
            "SOURCENAME" in df.columns
            and
            "TARGETNAME" in df.columns

        ):

            for _,row in df.iterrows():

                G.add_edge(

                    row["SOURCENAME"],
                    row["TRANID"],
                    label="SOURCE"

                )

                G.add_edge(

                    row["TRANID"],
                    row["TARGETNAME"],
                    label="TARGET"

                )


        # --------------------------------
        # INFOPACKAGE
        # --------------------------------

        if (

            "LOGSYS" in df.columns
            and
            "OLTPSOURCE" in df.columns

        ):

            for _,row in df.iterrows():

                G.add_edge(

                    row["OLTPSOURCE"],
                    row["LOGSYS"],
                    label="SOURCE_SYSTEM"

                )


# ----------------------------------------
# USER INPUT
# ----------------------------------------

query_object = input(

    "\nEnter BEx Query : "

)


# ----------------------------------------
# LINEAGE NODES
# ----------------------------------------

lineage_nodes=set()


if query_object in G:

    lineage_nodes.add(

        query_object

    )

    descendants=nx.descendants(

        G,
        query_object

    )


    lineage_nodes.update(

        descendants

    )

else:

    print(

        "\nQuery not found"

    )


subgraph=G.subgraph(

    lineage_nodes

)


# ----------------------------------------
# VISUALIZE
# ----------------------------------------

net=Network(

    height="800px",
    width="100%",
    directed=True,
    bgcolor="#222222",
    font_color="white"

)

net.from_nx(

    subgraph

)

net.repulsion()


net.save_graph(

    "lineage.html"

)


print(

    "\nLineage generated"

)

print(

    "Open lineage.html"

)