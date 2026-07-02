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
# LOAD METADATA
# =====================================================

query_df = read_file(get_file("*Query*"))
mp_df = read_file(get_file("*MultiProvider*"))
trfn_df = read_file(get_file("*TRANSFORMATION*"))
dtp_df = read_file(get_file("*DTP*"))
cube_df = read_file(get_file("*Infocube*"))
adso_df = read_file(get_file("*ADSO*"))
ip_df = read_file(get_file("*Infopackage*"))

for df_name in [
    "query_df",
    "mp_df",
    "trfn_df",
    "dtp_df",
    "cube_df",
    "adso_df",
    "ip_df"
]:
    if globals()[df_name] is not None:
        globals()[df_name] = globals()[df_name].astype(str)

if trfn_df is not None and "OBJVERS" in trfn_df.columns:
    trfn_df = trfn_df[
        trfn_df["OBJVERS"]
        .str.upper()
        .eq("A")
    ]
if ip_df is not None and "OBJVERS" in ip_df.columns:
    ip_df = ip_df[
        ip_df["OBJVERS"]
        .str.upper()
        .eq("A")
    ]

if dtp_df is not None and "OBJVERS" in dtp_df.columns:
    dtp_df = dtp_df[
        dtp_df["OBJVERS"]
        .str.upper()
        .eq("A")
    ]

if mp_df is not None and "OBJVERS" in mp_df.columns:
    mp_df = mp_df[
        mp_df["OBJVERS"]
        .str.upper()
        .eq("A")
    ]


if cube_df is not None and "OBJVERS" in cube_df.columns:
    cube_df = cube_df[
        cube_df["OBJVERS"]
        .str.upper()
        .eq("A")
    ]

# =====================================================
# CLEAN
# =====================================================

if trfn_df is not None:

    trfn_df["SOURCENAME"] = (
        trfn_df["SOURCENAME"]
        .str.replace(r"GDVCLNT\d+", "", regex=True)
        .str.strip()
    )

    trfn_df["TARGETNAME"] = (
        trfn_df["TARGETNAME"]
        .str.replace(r"GDVCLNT\d+", "", regex=True)
        .str.strip()
    )

if dtp_df is not None:

    dtp_df["SRC"] = (
        dtp_df["SRC"]
        .str.replace(r"GDVCLNT\d+", "", regex=True)
        .str.strip()
    )

    dtp_df["TGT"] = (
        dtp_df["TGT"]
        .str.replace(r"GDVCLNT\d+", "", regex=True)
        .str.strip()
    )

# =====================================================
# OBJECT TYPE
# =====================================================

def get_object_type(obj):

    obj = str(obj).upper().strip()

    if mp_df is not None:

        if not mp_df[
            mp_df["MULTIPROVIDER"]
            .str.upper()
            .eq(obj)
        ].empty:

            return "MULTIPROVIDER"

    if cube_df is not None:

        if not cube_df[
            cube_df["INFOCUBE"]
            .str.upper()
            .eq(obj)
        ].empty:

            return "INFOCUBE"

    if adso_df is not None:

        if not adso_df[
            adso_df["ADSO"]
            .str.upper()
            .eq(obj)
        ].empty:

            return "ADSO"
        # NEW BLOCK
    if obj.endswith("_TR"):
        return "INFOSOURCE"

    return "DATASOURCE"

# =====================================================
# BUILD LINEAGE
# =====================================================

visited = set()

stats = {
    "transformations": set(),
    "dtps": set(),
    "infopackages": set()
}


def build_lineage(provider):

    provider = str(provider).strip()

    provider = str(provider).strip()

    if provider.upper() in visited:
        return None

    visited.add(provider.upper())

    node = {
        "provider": provider,
        "type": get_object_type(provider),
        "children": []
    }

    # -----------------------------------------
    # DTP COLLECTION
    # -----------------------------------------

    node["dtps"] = []

    if dtp_df is not None:
        
        base_source = provider.replace("_TR", "")
        dtp_match = dtp_df[
            (
                dtp_df["SRC"]
                .str.upper()
                .eq(base_source.upper())
            )
            &
            (
                dtp_df["TGT"]
                .str.upper()
                .eq(provider.upper())
            )
        ]

        stats["dtps"].update(
            dtp_match["DTP"]
            .dropna()
            .unique()
        )


        if not dtp_match.empty:

            node["dtps"] = (
                dtp_match["DTP"]
                .dropna()
                .astype(str)
                .tolist()
            )

            stats["dtps"].update(
                node["dtps"]
            )

    # -----------------------------------------
    # TRANSFORMATION COLLECTION
    # -----------------------------------------

    node["transformations"] = []

    if trfn_df is not None:

        trfn_match = trfn_df[
            trfn_df["TARGETNAME"]
            .str.upper()
            .eq(provider.upper())
        ]

        if not trfn_match.empty:

            node["transformations"] = (
                trfn_match["TRANID"]
                .dropna()
                .astype(str)
                .tolist()
            )

            stats["transformations"].update(
                node["transformations"]
            )

    # INFOPACKAGE COUNT
    node["infopackages"] = 0

    if ip_df is not None:
        base_source = provider.replace("_TR", "")
        ip_match = ip_df[
            ip_df["OLTPSOURCE"]
            .str.contains(
                provider,
                case=False,
                na=False
            )
        ]

        node["infopackages"] = len(ip_match)

        if not ip_match.empty:

            stats["infopackages"].update(
                ip_match["LOGDPID"]
                .dropna()
                .unique()
            )

    # MULTIPROVIDER
    if node["type"] == "MULTIPROVIDER" and mp_df is not None:

        print("\nDEBUG MULTIPROVIDER =", provider)

        mp_match = mp_df[
            mp_df["MULTIPROVIDER"]
            .str.upper()
            .eq(provider.upper())
        ]

        print("Rows Found =", len(mp_match))

        if not mp_match.empty:
            print(
                mp_match[
                    ["MULTIPROVIDER", "PARTPROVIDER"]
                ].head(20)
            )

        for cube in mp_match["PARTPROVIDER"].unique():

            print("PART PROVIDER =", cube)

            child = build_lineage(cube)

            print("CHILD =", child)
            if child:
                node["children"].append(child)

    # TRANSFORMATIONS
    if trfn_df is not None:

        trfn_match = trfn_df[
            trfn_df["TARGETNAME"]
            .str.upper()
            .eq(provider.upper())
        ]
        for _, row in trfn_match.iterrows():

            tranid = str(row["TRANID"]).strip()
            source = str(row["SOURCENAME"]).strip()

            child_lineage = build_lineage(source)

            stats["transformations"].add(tranid)

            # Remove _TR suffix
            base_source = source.replace("_TR", "")

            dtp_match = pd.DataFrame()

            if dtp_df is not None:

                dtp_match = dtp_df[
                    dtp_df["SRC"]
                    .str.upper()
                    .eq(base_source.upper())
                    &
                    (
                    dtp_df["TGT"]
                    .str.upper()
                    .eq(provider.upper()))       
                ]

                stats["dtps"].update(
                    dtp_match["DTP"]
                    .dropna()
                    .unique()
                )

            ip_count = 0

            if ip_df is not None:

                ip_match = ip_df[
                    ip_df["OLTPSOURCE"]
                    .str.upper()
                    .eq(base_source.upper())
                ]

                ip_count = len(ip_match)

                stats["infopackages"].update(
                    ip_match["LOGDPID"]
                    .dropna()
                    .unique()
                )

            node["children"].append(
                {
                    "transformation": tranid,
                    "source": source,
                    "lineage": child_lineage,
                    "dtps": len(
                        dtp_match["DTP"]
                        .dropna()
                        .unique()
                    ) if not dtp_match.empty else 0,

                    "dtp_list": (
                        dtp_match["DTP"]
                        .dropna()
                        .unique()
                        .tolist()
                    ) if not dtp_match.empty else [],

                    "infopackages": ip_count,

                    "ip_list": (
                        ip_match["LOGDPID"]
                        .dropna()
                        .unique()
                        .tolist()
                    ) if ip_count > 0 else []
                }
            )


    return node

# =====================================================
# PRINT TREE
# =====================================================

def print_tree(node, level=0):

    indent = "    " * level

    # Provider Node
    if "provider" in node:

        print(
            f"{indent}{node['provider']} "
            f"({node['type']})"
        )

    # Transformations attached to provider
    if node.get("transformations"):

        print(
            f"{indent}├── Transformations : "
            f"{len(node['transformations'])}"
        )

        for tr in node["transformations"]:

            print(
                f"{indent}│   └── {tr}"
            )

    # DTPs attached to provider
    if node.get("dtps"):

        print(
            f"{indent}├── DTPs : "
            f"{len(node['dtps'])}"
        )

        for dtp in node["dtps"]:

            print(
                f"{indent}│   └── {dtp}"
            )

    # InfoPackages attached to provider
    if node.get("infopackages", 0) > 0:

        print(
            f"{indent}└── InfoPackages : "
            f"{node['infopackages']}"
        )

    # Children
    for child in node.get("children", []):

        # Transformation Child
        if "transformation" in child:

            print(
                f"{indent}├── Transformation : "
                f"{child['transformation']}"
            )

            print(
                f"{indent}│   Source : "
                f"{child['source']}"
            )

            print(
                f"{indent}│   DTPs : "
                f"{child.get('dtps', 0)}"
            )

            for dtp in child.get("dtp_list", []):

                print(
                    f"{indent}│   ├── {dtp}"
                )

            print(
                f"{indent}│   InfoPackages : "
                f"{child.get('infopackages', 0)}"
            )

            for ip in child.get("ip_list", []):

                print(
                    f"{indent}│   ├── {ip}"
                )

            # Recursively print upstream lineage
            if child.get("lineage"):

                print_tree(
                    child["lineage"],
                    level + 1
                )

        # MultiProvider -> InfoCube / ADSO child
        else:

            print_tree(
                child,
                level + 1
            )
# =====================================================
# INPUT
# =====================================================

query_input = input(
    "\nEnter Query Name / Query ID : "
).strip()

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

provider = row["INFOPROVIDER"]
print("\nROOT PROVIDER =", provider)

# =====================================================
# RUN
# =====================================================

print("ROOT TYPE =", get_object_type(provider))
tree = build_lineage(provider)

print("\n" + "=" * 100)
print("BW LINEAGE")
print("=" * 100)

print(f"\nBEx Query : {query_input}")
print(f"Root Provider : {provider}")

print("\n" + "=" * 100)
print("UPSTREAM LINEAGE")
print("=" * 100)

print_tree(tree)

# =====================================================
# COMPLEXITY
# =====================================================

trans_count = len(stats["transformations"])
dtp_count = len(stats["dtps"])
ip_count = len(stats["infopackages"])

score = (
    (trans_count * 5) +
    (dtp_count * 3) +
    ip_count
)

if score < 10:
    complexity = "LOW"
elif score < 30:
    complexity = "MEDIUM"
else:
    complexity = "HIGH"

print("\n" + "=" * 100)
print("MIGRATION COMPLEXITY")
print("=" * 100)

print(f"\nTransformations : {trans_count}")
print(f"DTPs            : {dtp_count}")
print(f"InfoPackages    : {ip_count}")
print(f"\nComplexity      : {complexity}")