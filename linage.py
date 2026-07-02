import pandas as pd
import os
import glob

# ==================================================
# Paths
# ==================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

META_FOLDER = os.path.join(
    BASE_DIR,
    "Meta_Data_File"
)

# ==================================================
# Read File
# ==================================================

def read_file(file_path):

    try:

        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".csv":

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

        elif ext == ".xls":

            return pd.read_excel(
                file_path,
                engine="xlrd"
            )

        elif ext == ".xlsx":

            return pd.read_excel(
                file_path,
                engine="openpyxl"
            )

    except Exception as e:

        print(f"Read Error : {e}")

    return None


# ==================================================
# Find File
# ==================================================

def get_file(pattern):

    files = []

    for ext in [
        ".csv",
        ".xls",
        ".xlsx"
    ]:

        files.extend(
            glob.glob(
                os.path.join(
                    META_FOLDER,
                    pattern + ext
                )
            )
        )

    return files[0] if files else None


# ==================================================
# Generate Lineage
# ==================================================

def generate_lineage(search_value):

    lineage = []

    # ==========================================
    # QUERY
    # ==========================================

    query_file = get_file("*Query*")

    if not query_file:

        print("Query file not found")
        return []

    query_df = read_file(query_file)

    if query_df is None:
        return []

    query_df = query_df.astype(str)

    query_match = query_df[
        (
            query_df["QUERYNAME"]
            .str.contains(
                search_value,
                case=False,
                na=False
            )
        )
        |
        (
            query_df["QUERYID"]
            .str.contains(
                search_value,
                case=False,
                na=False
            )
        )
    ]

    if query_match.empty:

        print("No Query Found")
        return []

    query_name = query_match.iloc[0]["QUERYNAME"]
    provider = query_match.iloc[0]["INFOPROVIDER"]

    lineage.append(
        ("BEx Query", query_name)
    )

    lineage.append(
        ("InfoProvider", provider)
    )

    # ==========================================
    # TRANSFORMATION
    # ==========================================

    trfn_file = get_file("*TRANSFORMATION*")

    if trfn_file:

        trfn_df = read_file(trfn_file)

        if trfn_df is not None:

            trfn_df = trfn_df.astype(str)

            trfn_match = trfn_df[
                trfn_df.apply(
                    lambda x:
                    x.str.contains(
                        provider,
                        case=False,
                        na=False
                    )
                ).any(axis=1)
            ]

            if not trfn_match.empty:

                col = trfn_df.columns[0]

                lineage.append(
                    (
                        "Transformation",
                        trfn_match.iloc[0][col]
                    )
                )

    # ==========================================
    # DTP Traversal
    # ==========================================

    dtp_file = get_file("*DTP*")

    source = ""

    if dtp_file:

        dtp_df = read_file(dtp_file)

        if dtp_df is not None:

            dtp_df = dtp_df.astype(str)

            current_target = provider

            visited = []

            while True:

                match = dtp_df[
                    dtp_df.apply(
                        lambda x:
                        x.str.contains(
                            current_target,
                            case=False,
                            na=False
                        )
                    ).any(axis=1)
                ]

                if match.empty:
                    break

                dtp_name = match.iloc[0]["DTP"]
                source = match.iloc[0]["SRC"]

                if dtp_name in visited:
                    break

                visited.append(dtp_name)

                lineage.append(
                    (
                        "DTP",
                        dtp_name
                    )
                )

                lineage.append(
                    (
                        "Source Object",
                        source
                    )
                )

                if source.startswith("DTP_"):
                    current_target = source
                else:
                    break

    # ==========================================
    # INFOPACKAGE
    # ==========================================

    ip_file = get_file("*InfoPackage*")

    if ip_file and source:

        ip_df = read_file(ip_file)

        if ip_df is not None:

            ip_df = ip_df.astype(str)

            ip_match = ip_df[
                ip_df.apply(
                    lambda x:
                    x.str.contains(
                        source,
                        case=False,
                        na=False
                    )
                ).any(axis=1)
            ]

            if not ip_match.empty:

                if "LOGDPID" in ip_df.columns:

                    lineage.append(
                        (
                            "InfoPackage",
                            ip_match.iloc[0]["LOGDPID"]
                        )
                    )

                if "LOGSYS" in ip_df.columns:

                    lineage.append(
                        (
                            "Source System",
                            ip_match.iloc[0]["LOGSYS"]
                        )
                    )

    return lineage


# ==================================================
# Display
# ==================================================

def print_lineage(lineage):

    print("\n")
    print("=" * 70)
    print("SAP BW LINEAGE")
    print("=" * 70)

    for i, (obj, name) in enumerate(lineage):

        print(f"\n{obj}")
        print(f"   {name}")

        if i < len(lineage) - 1:
            print("      ↓")


# ==================================================
# Main
# ==================================================

if __name__ == "__main__":

    search_value = input(
        "\nEnter Query Name / Query ID : "
    )

    lineage = generate_lineage(
        search_value
    )

    if lineage:
        print_lineage(lineage)
    else:
        print("\nNo lineage found.")