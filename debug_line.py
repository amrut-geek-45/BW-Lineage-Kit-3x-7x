import pandas as pd
import os
import glob

# =====================================================
# CONFIG
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

META_FOLDER = os.path.join(
    BASE_DIR,
    "Meta_Data_File"
)

# =====================================================
# FILE LOADER
# =====================================================

def read_file(file_path):

    if not file_path:
        return None

    try:

        if file_path.lower().endswith(".csv"):

            for enc in [
                "utf-8",
                "utf-8-sig",
                "cp1252",
                "latin1",
                "ISO-8859-1"
            ]:

                try:
                    return pd.read_csv(
                        file_path,
                        encoding=enc,
                        engine="python",
                        on_bad_lines="skip"
                    )
                except:
                    pass

        elif file_path.lower().endswith(
            (".xls", ".xlsx")
        ):

            return pd.read_excel(file_path)

    except Exception as e:
        print(e)

    return None


# =====================================================
# FIND FILE
# =====================================================

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


# =====================================================
# LOAD FILES
# =====================================================

query_df = read_file(
    get_file("*Query*")
)

mp_df = read_file(
    get_file("*MultiProvider*")
)

trfn_df = read_file(
    get_file("*TRANSFORMATION*")
)

dtp_df = read_file(
    get_file("*DTP*")
)
adso_df = read_file(
    get_file("*ADSO*")
)

cube_df = read_file(
    get_file("*Infocube*")
)

ip_df = read_file(
    get_file("*Infopackage*")
)


#
adso_df = read_file(get_file("*ADSO*"))
cube_df = read_file(get_file("*Infocube*"))
ip_df = read_file(get_file("*Infopackage*"))


# =====================================================
# STRING CONVERSION
# =====================================================

if query_df is not None:
    query_df = query_df.astype(str)

if mp_df is not None:
    mp_df = mp_df.astype(str)

if trfn_df is not None:
    trfn_df = trfn_df.astype(str)

if dtp_df is not None:
    dtp_df = dtp_df.astype(str)

adso_df = adso_df.astype(str) if adso_df is not None else None
cube_df = cube_df.astype(str) if cube_df is not None else None
ip_df = ip_df.astype(str) if ip_df is not None else None

# =====================================================
# CLEAN BW VALUES
# =====================================================

if trfn_df is not None:

    trfn_df["SOURCENAME"] = (
        trfn_df["SOURCENAME"]
        .str.replace(
            r"GDVCLNT\d+",
            "",
            regex=True
        )
        .str.strip()
    )

    trfn_df["TARGETNAME"] = (
        trfn_df["TARGETNAME"]
        .str.replace(
            r"GDVCLNT\d+",
            "",
            regex=True
        )
        .str.strip()
    )

if dtp_df is not None:

    dtp_df["SRC"] = (
        dtp_df["SRC"]
        .str.replace(
            r"GDVCLNT\d+",
            "",
            regex=True
        )
        .str.strip()
    )

    dtp_df["TGT"] = (
        dtp_df["TGT"]
        .str.replace(
            r"GDVCLNT\d+",
            "",
            regex=True
        )
        .str.strip()
    )
# =====================================================
# OBJECT TYPE DETECTION
# =====================================================
def get_object_type(obj):

    obj = str(obj).upper().strip()

    if mp_df is not None:

        found = mp_df[
            mp_df["MULTIPROVIDER"]
            .str.upper()
            .eq(obj)
        ]

        if not found.empty:
            return "MULTIPROVIDER"

    if cube_df is not None:

        found = cube_df[
            cube_df["INFOCUBE"]
            .str.upper()
            .eq(obj)
        ]

        if not found.empty:
            return "INFOCUBE"

    if adso_df is not None:

        found = adso_df[
            adso_df["ADSO"]
            .str.upper()
            .eq(obj)
        ]

        if not found.empty:
            return "ADSO"

    return "DATASOURCE / SOURCE OBJECT"
# =====================================================
# TRACE FUNCTIONS
# =====================================================

visited = set()

visited = set()

unique_transformations = set()
unique_dtps = set()
unique_infopackages = set()

total_transformations = 0
total_dtps = 0
total_infopackages = 0


def show_dtp(provider, level=0):

    global total_dtps

    indent = "   " * level

    dtp_match = dtp_df[
        (
            dtp_df["SRC"]
            .str.upper()
            .eq(provider.upper())
        )
        |
        (
            dtp_df["TGT"]
            .str.upper()
            .eq(provider.upper())
        )
    ]

    if not dtp_match.empty:

        total_dtps += len(dtp_match)

        print(f"\n{indent}DTPs")

        print(
            dtp_match[
                ["DTP", "SRC", "TGT"]
            ]
            .to_string(index=False)
        )


def trace_provider(provider, level=0):

    global visited
    global total_transformations
    global total_infopackages

    indent = "   " * level

    provider = str(provider).strip()

    if provider.upper() in visited:
        return

    visited.add(provider.upper())

    print(f"\n{indent}Provider : {provider}")

    show_dtp(provider, level)

    trfn_match = pd.DataFrame()

    if trfn_df is not None:

        trfn_match = trfn_df[
            trfn_df["TARGETNAME"]
            .str.upper()
            .eq(provider.upper())
        ]

    if not trfn_match.empty:
        for _, row in trfn_match.iterrows():
            unique_transformations.add(
                str(row["SOURCENAME"]).strip()
    )

        print(
            f"{indent}Type : Transformation Target"
        )

        for _, row in trfn_match.iterrows():

            source = str(
                row["SOURCENAME"]
            ).strip()

            print(
                f"{indent}|-- {source}"
            )

            trace_provider(
                source,
                level + 1
            )

        return

    if ip_df is not None:

        ip_match = ip_df[
            ip_df["OLTPSOURCE"]
            .str.contains(
                provider,
                case=False,
                na=False
            )
        ]

        if not ip_match.empty:
            total_infopackages += len(ip_match)

            print(
                f"\n{indent}Related InfoPackages"
            )

            print(
                ip_match[
                    ["LOGDPID", "OLTPSOURCE"]
                ]
                .head(20)
                .to_string(index=False)
            )

    print(
        f"{indent}Object Type : "
        f"{get_object_type(provider)}"
    )

    print(
        f"{indent}End Of Available Lineage"
    )

# =====================================================
# INPUT
# =====================================================

query_input = input(
    "\nEnter Query Name / Query ID : "
).strip()

# =====================================================
# QUERY SEARCH
# =====================================================

query_match = query_df[
    (
        query_df["QUERYID"]
        .str.contains(
            query_input,
            case=False,
            na=False
        )
    )
    |
    (
        query_df["QUERYNAME"]
        .str.contains(
            query_input,
            case=False,
            na=False
        )
    )
]

if query_match.empty:

    print("\nNo Query Found")
    exit()

row = query_match.iloc[0]

query_name = row["QUERYNAME"]
provider = row["INFOPROVIDER"]

# =====================================================
# OUTPUT
# =====================================================

print("\n")
print("=" * 100)
print("BW LINEAGE")
print("=" * 100)

print(f"\nBEx Query : {query_input}")
print(f"Root Provider : {provider}")

print("\n")
print("=" * 100)
print("UPSTREAM LINEAGE")
print("=" * 100)

trace_provider(provider)

print("\n")
print("=" * 100)
print("MIGRATION COMPLEXITY")
print("=" * 100)

print(f"\nQuery Name         : {query_input}")
print(f"InfoProvider       : {provider}")

trans_count = len(unique_transformations)
dtp_count = len(unique_dtps)
ip_count = total_infopackages

print(f"\nTransformations    : {trans_count}")
print(f"DTPs               : {dtp_count}")
print(f"InfoPackages       : {ip_count}")

score = (
    trans_count +
    dtp_count +
    ip_count
)

if score < 10:
    complexity = "LOW"
elif score < 30:
    complexity = "MEDIUM"
else:
    complexity = "HIGH"

print(f"\nComplexity Rating  : {complexity}")

print("\nComplexity Drivers")
print("-" * 20)

if total_transformations > 1:
    print("✓ Multiple Transformations")

if total_dtps > 5:
    print("✓ Multiple DTP Chains")

if total_infopackages > 5:
    print("✓ Multiple InfoPackages")

print("\nMigration Effort")
print("-" * 20)

if complexity == "LOW":
    print("Estimated Effort : Low")
elif complexity == "MEDIUM":
    print("Estimated Effort : Medium")
else:
    print("Estimated Effort : High")
