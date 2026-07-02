import pandas as pd
import os
import glob
import re
import json
import zipfile
import requests
from io import BytesIO
import streamlit as st

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(page_title="BW Lineage Analyzer", page_icon="🔗", layout="wide")

st.markdown("""
<style>
.block-container{padding-top:2rem;padding-bottom:2rem}
.section-header{font-size:12px;font-weight:700;color:#6c757d;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px}
.complexity-low{background:#d4edda;color:#155724;padding:3px 12px;border-radius:20px;font-weight:600;font-size:13px;display:inline-block}
.complexity-medium{background:#fff3cd;color:#856404;padding:3px 12px;border-radius:20px;font-weight:600;font-size:13px;display:inline-block}
.complexity-high{background:#f8d7da;color:#721c24;padding:3px 12px;border-radius:20px;font-weight:600;font-size:13px;display:inline-block}
.query-tag{background:#e8f4fd;color:#1a6ea8;padding:3px 10px;border-radius:6px;font-size:13px;font-weight:500;display:inline-block;margin-bottom:4px}
.info-box{background:#e8f4fd;border-left:4px solid #1a6ea8;padding:10px 14px;border-radius:4px;font-size:13px;color:#1a4a6e;margin-bottom:10px}
.ai-box{background:#f3f0ff;border-left:4px solid #6f42c1;padding:12px 16px;border-radius:6px;font-size:14px;color:#2d1b6e;margin:10px 0;line-height:1.6}
.risk-CRITICAL{background:#dc3545;border-left:6px solid #a71d2a;padding:12px 16px;border-radius:6px;font-size:13px;margin:8px 0;color:#ffffff !important}
.risk-CRITICAL *{color:#ffffff !important}
.risk-HIGH{background:#fd7e14;border-left:6px solid #c35a00;padding:12px 16px;border-radius:6px;font-size:13px;margin:8px 0;color:#ffffff !important}
.risk-HIGH *{color:#ffffff !important}
.risk-MEDIUM{background:#e6a817;border-left:6px solid #b07d00;padding:12px 16px;border-radius:6px;font-size:13px;margin:8px 0;color:#ffffff !important}
.risk-MEDIUM *{color:#ffffff !important}
.risk-LOW{background:#28a745;border-left:6px solid #1a6e2e;padding:12px 16px;border-radius:6px;font-size:13px;margin:8px 0;color:#ffffff !important}
.risk-LOW *{color:#ffffff !important}
.risk-overall-CRITICAL{background:#a71d2a;border:2px solid #dc3545;padding:14px 18px;border-radius:8px;font-size:14px;margin:8px 0;color:#ffffff !important}
.risk-overall-HIGH{background:#c35a00;border:2px solid #fd7e14;padding:14px 18px;border-radius:8px;font-size:14px;margin:8px 0;color:#ffffff !important}
.risk-overall-MEDIUM{background:#b07d00;border:2px solid #ffc107;padding:14px 18px;border-radius:8px;font-size:14px;margin:8px 0;color:#ffffff !important}
.risk-overall-LOW{background:#1a6e2e;border:2px solid #28a745;padding:14px 18px;border-radius:8px;font-size:14px;margin:8px 0;color:#ffffff !important}
.chat-user{background:#e8f4fd;border-radius:12px 12px 2px 12px;padding:10px 14px;margin:4px 0;font-size:13px;color:#1a4a6e}
.chat-ai{background:#f3f0ff;border-radius:2px 12px 12px 12px;padding:10px 14px;margin:4px 0;font-size:13px;color:#2d1b6e;line-height:1.6}
div[data-testid="metric-container"]{background:#f8f9fa;border:1px solid #e9ecef;border-radius:10px;padding:12px 16px}
.impact-hit{background:#fff8e1;border-left:4px solid #f9a825;padding:10px 14px;border-radius:6px;font-size:13px;margin:6px 0;color:#3e2400}
.impact-none{background:#d4edda;border-left:4px solid #28a745;padding:10px 14px;border-radius:6px;font-size:13px;color:#155724}
.dead-obj{background:#f8d7da;border-left:4px solid #dc3545;padding:10px 14px;border-radius:6px;font-size:13px;margin:6px 0;color:#491217}
.compare-box{background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);border-radius:8px;padding:14px;font-size:13px}
.compare-shared{background:#d4edda;border-left:4px solid #28a745;padding:6px 10px;border-radius:4px;font-size:12px;margin:3px 0;color:#155724}
.compare-unique{background:#e8f4fd;border-left:4px solid #1a6ea8;padding:6px 10px;border-radius:4px;font-size:12px;margin:3px 0;color:#0c2d6e}
.tool-section{background:var(--color-background-secondary);border:0.5px solid var(--color-border-tertiary);border-radius:10px;padding:16px;margin-bottom:16px}
</style>
""", unsafe_allow_html=True)

# =====================================================
# CONFIG
# =====================================================
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
META_FOLDER = os.path.join(BASE_DIR, "Meta_Data_File")

# =====================================================
# FILE HELPERS
# =====================================================

def read_file(path):
    if not path:
        return None
    try:
        if path.lower().endswith(".csv"):
            for enc in ["utf-8","utf-8-sig","cp1252","latin1","ISO-8859-1"]:
                try:
                    return pd.read_csv(path, encoding=enc, engine="python", on_bad_lines="skip")
                except:
                    pass
        elif path.lower().endswith((".xls",".xlsx")):
            return pd.read_excel(path)
    except Exception as e:
        print(e)
    return None


def read_uploaded(uf):
    try:
        name = uf.name.lower()
        if name.endswith(".csv"):
            for enc in ["utf-8","utf-8-sig","cp1252","latin1","ISO-8859-1"]:
                try:
                    uf.seek(0)
                    return pd.read_csv(uf, encoding=enc, engine="python", on_bad_lines="skip")
                except:
                    pass
        elif name.endswith((".xls",".xlsx")):
            uf.seek(0)
            return pd.read_excel(uf)
    except Exception as e:
        print(e)
    return None


def get_file(pattern):
    files = []
    for ext in [".csv",".xls",".xlsx"]:
        files.extend(glob.glob(os.path.join(META_FOLDER, pattern+ext)))
    return files[0] if files else None


# =====================================================
# LOAD & PREPARE METADATA
# =====================================================

@st.cache_data(show_spinner="Loading metadata…")
def load_from_folder():
    return {
        "query_df": read_file(get_file("*Query*")),
        "mp_df":    read_file(get_file("*MultiProvider*")),
        "trfn_df":  read_file(get_file("*TRANSFORMATION*")),
        "dtp_df":   read_file(get_file("*DTP*")),
        "cube_df":  read_file(get_file("*Infocube*")),
        "adso_df":  read_file(get_file("*ADSO*")),
        "ip_df":    read_file(get_file("*Infopackage*")),
    }


def prepare_dfs(raw):
    dfs = {k: (df.astype(str) if df is not None else None) for k,df in raw.items()}
    for key in ["trfn_df","ip_df","dtp_df","mp_df","cube_df"]:
        if dfs.get(key) is not None and "OBJVERS" in dfs[key].columns:
            dfs[key] = dfs[key][dfs[key]["OBJVERS"].str.upper().eq("A")]
    if dfs.get("trfn_df") is not None:
        for col in ["SOURCENAME","TARGETNAME"]:
            if col in dfs["trfn_df"].columns:
                dfs["trfn_df"][col] = dfs["trfn_df"][col].str.replace(r"GDVCLNT\d+","",regex=True).str.strip()
    if dfs.get("dtp_df") is not None:
        for col in ["SRC","TGT"]:
            if col in dfs["dtp_df"].columns:
                dfs["dtp_df"][col] = dfs["dtp_df"][col].str.replace(r"GDVCLNT\d+","",regex=True).str.strip()
    dfs["_mp_set"]   = set(dfs["mp_df"]["MULTIPROVIDER"].str.upper())  if dfs.get("mp_df")   is not None else set()
    dfs["_cube_set"] = set(dfs["cube_df"]["INFOCUBE"].str.upper())     if dfs.get("cube_df") is not None else set()
    dfs["_adso_set"] = set(dfs["adso_df"]["ADSO"].str.upper())         if dfs.get("adso_df") is not None else set()
    return dfs


# =====================================================
# OBJECT TYPE
# =====================================================

def get_object_type(obj, dfs):
    obj = str(obj).upper().strip()
    if obj in dfs["_mp_set"]:   return "MULTIPROVIDER"
    if obj in dfs["_cube_set"]: return "INFOCUBE"
    if obj in dfs["_adso_set"]: return "ADSO"
    if obj.endswith("_TR"):     return "INFOSOURCE"
    return "DATASOURCE"


# =====================================================
# BUILD LINEAGE
# =====================================================

def build_lineage(provider, dfs):
    visited = set()
    stats   = {"transformations":set(),"dtps":set(),"ip_count":0}
    trfn_df = dfs.get("trfn_df"); dtp_df = dfs.get("dtp_df")
    mp_df   = dfs.get("mp_df");   ip_df  = dfs.get("ip_df")

    def _proc(prov):
        pu = prov.upper()
        if pu in visited: return None
        visited.add(pu)
        node = {"provider":prov,"type":get_object_type(prov,dfs),"children":[],"dtps":[],"transformations":[],"infopackages":0}
        if dtp_df is not None:
            base = prov.replace("_TR","")
            dm = dtp_df[dtp_df["SRC"].str.upper().eq(base.upper()) & dtp_df["TGT"].str.upper().eq(pu)]
            if not dm.empty:
                dtps = dm["DTP"].dropna().astype(str).tolist()
                node["dtps"] = dtps; stats["dtps"].update(dtps)
        if trfn_df is not None:
            tm = trfn_df[trfn_df["TARGETNAME"].str.upper().eq(pu)]
            if not tm.empty:
                trs = tm["TRANID"].dropna().astype(str).tolist()
                node["transformations"] = trs; stats["transformations"].update(trs)
        if ip_df is not None:
            ipm = ip_df[ip_df["OLTPSOURCE"].str.contains(prov,case=False,na=False)]
            node["infopackages"] = len(ipm); stats["ip_count"] += len(ipm)
        if node["type"] == "MULTIPROVIDER" and mp_df is not None:
            for cube in mp_df[mp_df["MULTIPROVIDER"].str.upper().eq(pu)]["PARTPROVIDER"].dropna().unique():
                ch = _proc(str(cube).strip())
                if ch: node["children"].append(ch)
        if trfn_df is not None:
            for _,row in trfn_df[trfn_df["TARGETNAME"].str.upper().eq(pu)].iterrows():
                tranid = str(row["TRANID"]).strip(); source = str(row["SOURCENAME"]).strip()
                base_s = source.replace("_TR",""); stats["transformations"].add(tranid)
                dtp_list=[]; ip_cnt=0
                if dtp_df is not None:
                    dm2 = dtp_df[dtp_df["SRC"].str.upper().eq(base_s.upper()) & dtp_df["TGT"].str.upper().eq(pu)]
                    if not dm2.empty:
                        dtp_list = dm2["DTP"].dropna().astype(str).tolist(); stats["dtps"].update(dtp_list)
                if ip_df is not None:
                    ipm2 = ip_df[ip_df["OLTPSOURCE"].str.upper().eq(base_s.upper())]
                    ip_cnt = len(ipm2); stats["ip_count"] += ip_cnt
                node["children"].append({"transformation":tranid,"source":source,"lineage":_proc(source),"dtps":len(dtp_list),"dtp_list":dtp_list,"infopackages":ip_cnt})
        return node

    return _proc(str(provider).strip()), stats


# =====================================================
# COMPLEXITY
# =====================================================

def compute_complexity(stats):
    t=len(stats["transformations"]); d=len(stats["dtps"]); i=stats["ip_count"]
    score=(t*5)+(d*3)+i
    cx="LOW" if score<10 else ("MEDIUM" if score<30 else "HIGH")
    return t,d,i,score,cx


# =====================================================
# TREE TEXT
# =====================================================

def tree_lines(node, level=0):
    lines=[]; indent="    "*level; B,L,P="├── ","└── ","│   "
    if "provider" in node:
        lines.append(f"{indent}[{node['type']}]  {node['provider']}")
    if node.get("transformations"):
        lines.append(f"{indent}{B}Transformations : {len(node['transformations'])}")
        for i,tr in enumerate(node["transformations"]):
            lines.append(f"{indent}{P}  {'└── ' if i==len(node['transformations'])-1 else '├── '}{tr}")
    if node.get("dtps"):
        lines.append(f"{indent}{B}DTPs : {len(node['dtps'])}")
        for i,dtp in enumerate(node["dtps"]):
            lines.append(f"{indent}{P}  {'└── ' if i==len(node['dtps'])-1 else '├── '}{dtp}")
    if node.get("infopackages",0)>0:
        lines.append(f"{indent}{L}InfoPackages : {node['infopackages']} (count only)")
    for child in node.get("children",[]):
        if "transformation" in child:
            lines.append(f"{indent}{B}Transformation : {child['transformation']}")
            lines.append(f"{indent}{P}  {B}Source       : {child['source']}")
            lines.append(f"{indent}{P}  {B}DTPs         : {child.get('dtps',0)}")
            for dtp in child.get("dtp_list",[]): lines.append(f"{indent}{P}      └── {dtp}")
            lines.append(f"{indent}{P}  {L}InfoPackages : {child.get('infopackages',0)} (count only)")
            if child.get("lineage"): lines.extend(tree_lines(child["lineage"],level+1))
        else:
            lines.extend(tree_lines(child,level+1))
    return lines


def build_report_text(q, provider, tree, stats, ai_sum="", risk_data=None):
    t,d,i,score,cx = compute_complexity(stats)
    sep="="*80
    lines=[sep,"  BW LINEAGE REPORT",sep,
           f"  Query        : {q}",f"  Provider     : {provider}",
           f"  Complexity   : {cx} (Score:{score})",
           f"  Transforms   : {t}  |  DTPs: {d}  |  InfoPkgs: {i:,}",sep,""]
    if ai_sum:
        lines+=["AI SUMMARY","-"*40, ai_sum,""]
    if risk_data and "overall_risk" in risk_data:
        lines+=["MIGRATION RISK","-"*40,json.dumps(risk_data,indent=2),""]
    lines+=["LINEAGE TREE","-"*40,""]+tree_lines(tree)+["",sep]
    return "\n".join(lines)


# =====================================================
# API KEY
# =====================================================

def get_api_key():
    try:
        k = st.secrets.get("ANTHROPIC_API_KEY","")
        if k: return k
    except:
        pass
    return st.session_state.get("api_key","").strip()


# =====================================================
# AI CALLS
# =====================================================

def call_claude(system, user, max_tokens=900):
    key = get_api_key()
    if not key:
        return "[ERROR: No API key — paste it in the sidebar]"
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":max_tokens,"system":system,
                  "messages":[{"role":"user","content":user}]},
            timeout=60
        )
        if r.status_code != 200:
            return f"[ERROR {r.status_code}: {r.text[:400]}]"
        return "".join(b.get("text","") for b in r.json().get("content",[]))
    except Exception as e:
        return f"[ERROR: {e}]"


def call_claude_chat(system, messages, max_tokens=600):
    key = get_api_key()
    if not key:
        return "[ERROR: No API key — paste it in the sidebar]"
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":max_tokens,"system":system,"messages":messages},
            timeout=60
        )
        if r.status_code != 200:
            return f"[ERROR {r.status_code}: {r.text[:400]}]"
        return "".join(b.get("text","") for b in r.json().get("content",[]))
    except Exception as e:
        return f"[ERROR: {e}]"


def make_context(q, provider, tree, stats):
    t,d,i,score,cx = compute_complexity(stats)
    lines = tree_lines(tree)[:200]
    return (f"BEx Query: {q}\nProvider: {provider}\nComplexity: {cx} (Score:{score})\n"
            f"Transformations:{t} | DTPs:{d} | InfoPackages:{i}\n\nLineage Tree:\n"+"\n".join(lines))


def do_ai_summary(q, provider, tree, stats):
    ctx = make_context(q, provider, tree, stats)
    return call_claude(
        "You are an SAP BW/4HANA expert. Explain lineage trees clearly to technical and business audiences.",
        f"Write a plain-English summary (5-8 sentences) of this BW lineage covering: what the query reports on, "
        f"the data flow path, key objects, and what drives the complexity.\n\n{ctx}",
        max_tokens=600
    )


def do_ai_risk(q, provider, tree, stats):
    ctx = make_context(q, provider, tree, stats)

    # Keep the prompt short so the RESPONSE has room — max_tokens=2000 covers large lineages
    prompt = (
        "Analyze this SAP BW lineage for BW/4HANA migration risks.\n"
        "Reply with ONLY a JSON object — no markdown, no prose, no code fences.\n"
        "JSON structure:\n"
        '{"overall_risk":"HIGH","summary":"one sentence","risks":['
        '{"level":"HIGH","object":"obj","issue":"issue","recommendation":"rec"}],'
        '"migration_effort_days":10,"key_actions":["a1","a2","a3"]}\n\n'
        "Levels: CRITICAL, HIGH, MEDIUM, LOW only.\n"
        "migration_effort_days: integer only.\n\n"
        f"Lineage:\n{ctx}"
    )

    raw = call_claude(
        "You are an SAP BW to BW/4HANA migration expert. "
        "You ALWAYS respond with only a valid JSON object and nothing else.",
        prompt,
        max_tokens=2000
    )

    if raw.startswith("[ERROR"):
        return {"_error": raw}

    # Clean markdown fences if present
    clean = raw.strip()
    if "```" in clean:
        clean = re.sub(r"```[a-z]*", "", clean).replace("```", "").strip()

    # Try direct parse
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass

    # Try to find the JSON object even if there's surrounding text
    m = re.search(r'\{[\s\S]*\}', clean)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass

    # If JSON is truncated (common when token limit hit mid-response), try to repair it
    try:
        # Count open braces/brackets to detect truncation
        trimmed = clean.rstrip()
        open_b  = trimmed.count("{") - trimmed.count("}")
        open_sq = trimmed.count("[") - trimmed.count("]")
        repaired = trimmed
        # Close any open arrays first then objects
        repaired += "]" * max(0, open_sq)
        repaired += "}" * max(0, open_b)
        return json.loads(repaired)
    except:
        pass

    return {"_error": f"Could not parse JSON (response may have been cut off).\n\nRaw response:\n{clean[:800]}"}



# =====================================================
# IMPACT ANALYSIS
# =====================================================

def collect_all_objects(dfs):
    """Return a dict: object_name -> set of query IDs that depend on it."""
    query_df = dfs.get("query_df")
    trfn_df  = dfs.get("trfn_df")
    dtp_df   = dfs.get("dtp_df")
    ip_df    = dfs.get("ip_df")

    obj_to_queries = {}  # object -> set of queries

    if query_df is None:
        return obj_to_queries

    for _, row in query_df.iterrows():
        qid      = str(row.get("QUERYID","")).strip()
        provider = str(row.get("INFOPROVIDER","")).strip()
        if not qid or not provider:
            continue

        # collect objects in this query's lineage
        visited = set()
        def _collect(prov):
            pu = prov.upper()
            if pu in visited:
                return
            visited.add(pu)
            obj_to_queries.setdefault(prov.upper(), set()).add(qid)
            if trfn_df is not None:
                for _, r in trfn_df[trfn_df["TARGETNAME"].str.upper().eq(pu)].iterrows():
                    src = str(r["SOURCENAME"]).strip()
                    obj_to_queries.setdefault(src.upper(), set()).add(qid)
                    _collect(src)
            if dfs.get("mp_df") is not None:
                for part in dfs["mp_df"][dfs["mp_df"]["MULTIPROVIDER"].str.upper().eq(pu)]["PARTPROVIDER"].dropna():
                    _collect(str(part).strip())
        _collect(provider)

    return obj_to_queries


def do_impact_analysis(obj_name, dfs):
    """Find all queries impacted if obj_name changes/is removed."""
    obj_to_queries = collect_all_objects(dfs)
    key = obj_name.upper().strip()
    impacted = sorted(obj_to_queries.get(key, set()))

    # Also search partial matches
    partial = {}
    for obj, queries in obj_to_queries.items():
        if key in obj and obj != key:
            partial[obj] = sorted(queries)

    # AI commentary
    ctx = (
        f"Object being analysed: {obj_name}\n"
        f"Direct matches — queries impacted: {len(impacted)}\n"
        f"Impacted query IDs: {', '.join(impacted[:30]) or 'None'}\n"
        f"Partial name matches found: {list(partial.keys())[:10]}\n"
    )
    ai_comment = call_claude(
        "You are an SAP BW/4HANA expert. Explain impact analysis results clearly.",
        f"An analyst is checking what breaks if this SAP BW object is changed or removed.\n\n"
        f"{ctx}\n\n"
        f"Write 3-5 sentences: what this object likely is, which queries are at risk, "
        f"and what precautions to take before changing it.",
        max_tokens=400
    )
    return {"object": obj_name, "impacted": impacted, "partial": partial, "ai": ai_comment}


# =====================================================
# QUERY COMPARISON
# =====================================================

def do_query_comparison(q1, q2, dfs):
    """Compare two queries — shared objects, unique objects, AI narrative."""
    def get_objects(q):
        query_df = dfs.get("query_df")
        if query_df is None:
            return None, set()
        m = query_df[
            query_df["QUERYID"].str.contains(q, case=False, na=False) |
            query_df["QUERYNAME"].str.contains(q, case=False, na=False)
        ]
        if m.empty:
            return None, set()
        provider = m.iloc[0]["INFOPROVIDER"]
        tree, stats = build_lineage(provider, dfs)

        # Collect all object names from tree
        objects = set()
        def _walk(node):
            if not node:
                return
            objects.add(node.get("provider","").upper())
            for child in node.get("children", []):
                if "transformation" in child:
                    objects.add(child.get("source","").upper())
                    objects.add(child.get("transformation","").upper())
                    _walk(child.get("lineage"))
                else:
                    _walk(child)
        _walk(tree)
        return provider, objects, tree, stats

    r1 = get_objects(q1)
    r2 = get_objects(q2)

    if r1[0] is None:
        return {"error": f"Query '{q1}' not found"}
    if r2[0] is None:
        return {"error": f"Query '{q2}' not found"}

    prov1, objs1, tree1, stats1 = r1
    prov2, objs2, tree2, stats2 = r2

    shared  = sorted(objs1 & objs2)
    only_q1 = sorted(objs1 - objs2)
    only_q2 = sorted(objs2 - objs1)

    t1,d1,i1,sc1,cx1 = compute_complexity(stats1)
    t2,d2,i2,sc2,cx2 = compute_complexity(stats2)

    ctx = (
        f"Query 1: {q1} | Provider: {prov1} | Complexity: {cx1} (score {sc1}) | "
        f"Transforms: {t1} | DTPs: {d1} | InfoPkgs: {i1}\n"
        f"Query 2: {q2} | Provider: {prov2} | Complexity: {cx2} (score {sc2}) | "
        f"Transforms: {t2} | DTPs: {d2} | InfoPkgs: {i2}\n\n"
        f"Shared objects ({len(shared)}): {', '.join(shared[:20])}\n"
        f"Only in {q1} ({len(only_q1)}): {', '.join(only_q1[:15])}\n"
        f"Only in {q2} ({len(only_q2)}): {', '.join(only_q2[:15])}\n"
    )

    ai_comment = call_claude(
        "You are an SAP BW/4HANA expert specialising in query migration and consolidation.",
        f"Compare these two BEx queries and provide a concise analysis (5-7 sentences) covering:\n"
        f"1. How similar/different they are and why\n"
        f"2. Whether shared objects create migration dependency risks\n"
        f"3. Consolidation opportunities — could these queries share more, or be merged?\n"
        f"4. Which query is harder to migrate and why\n\n{ctx}",
        max_tokens=500
    )

    return {
        "q1": q1, "q2": q2,
        "prov1": prov1, "prov2": prov2,
        "stats1": (t1,d1,i1,sc1,cx1),
        "stats2": (t2,d2,i2,sc2,cx2),
        "shared": shared, "only_q1": only_q1, "only_q2": only_q2,
        "ai": ai_comment
    }


# =====================================================
# DEAD OBJECT DETECTOR
# =====================================================

def do_dead_object_detection(dfs):
    """Find objects that exist in metadata but are consumed by NO active query."""
    query_df = dfs.get("query_df")
    trfn_df  = dfs.get("trfn_df")
    dtp_df   = dfs.get("dtp_df")
    ip_df    = dfs.get("ip_df")
    mp_df    = dfs.get("mp_df")
    cube_df  = dfs.get("cube_df")
    adso_df  = dfs.get("adso_df")

    # All objects referenced by at least one query
    obj_to_queries = collect_all_objects(dfs)
    active_objects = set(obj_to_queries.keys())

    dead = []

    # Check Transformations
    if trfn_df is not None and "TARGETNAME" in trfn_df.columns:
        for obj in trfn_df["TARGETNAME"].dropna().str.upper().unique():
            if obj.strip() and obj.strip() not in active_objects:
                dead.append({"type": "TRANSFORMATION TARGET", "object": obj.strip()})

    # Check DTPs
    if dtp_df is not None and "DTP" in dtp_df.columns:
        for obj in dtp_df["DTP"].dropna().str.upper().unique():
            if obj.strip() and obj.strip() not in active_objects:
                dead.append({"type": "DTP", "object": obj.strip()})

    # Check InfoCubes
    if cube_df is not None and "INFOCUBE" in cube_df.columns:
        for obj in cube_df["INFOCUBE"].dropna().str.upper().unique():
            if obj.strip() and obj.strip() not in active_objects:
                dead.append({"type": "INFOCUBE", "object": obj.strip()})

    # Check ADSOs
    if adso_df is not None and "ADSO" in adso_df.columns:
        for obj in adso_df["ADSO"].dropna().str.upper().unique():
            if obj.strip() and obj.strip() not in active_objects:
                dead.append({"type": "ADSO", "object": obj.strip()})

    # Check InfoPackages (DataSources with no active query)
    if ip_df is not None and "OLTPSOURCE" in ip_df.columns:
        for obj in ip_df["OLTPSOURCE"].dropna().str.upper().unique():
            if obj.strip() and obj.strip() not in active_objects:
                dead.append({"type": "INFOPACKAGE/DATASOURCE", "object": obj.strip()})

    # Deduplicate
    seen = set()
    deduped = []
    for d in dead:
        k = d["object"]
        if k not in seen:
            seen.add(k)
            deduped.append(d)

    # Group by type for summary
    from collections import Counter
    type_counts = Counter(d["type"] for d in deduped)

    ctx = (
        f"Total dead objects found: {len(deduped)}\n"
        f"Breakdown: {dict(type_counts)}\n"
        f"Sample dead objects: {[d['object'] for d in deduped[:20]]}\n"
        f"Total active objects in use: {len(active_objects)}\n"
        f"Total queries scanned: {len(query_df) if query_df is not None else 0}\n"
    )

    ai_comment = call_claude(
        "You are an SAP BW/4HANA housekeeping and migration expert.",
        f"Dead object analysis results for an SAP BW system:\n\n{ctx}\n\n"
        f"Write 4-6 sentences covering: what these dead objects are, why they accumulate, "
        f"the risk of deleting them, recommended steps before deletion, and migration impact.",
        max_tokens=450
    )

    return {"dead": deduped, "type_counts": dict(type_counts), "active_count": len(active_objects), "ai": ai_comment}


def do_chat(question, ctx, history):
    system = ("You are an SAP BW/4HANA lineage expert. Answer questions about the lineage concisely. "
              "If info isn't in the context, say so.")
    messages = []
    for h in history:
        messages.append({"role":"user",      "content": h["user"]})
        messages.append({"role":"assistant", "content": h["ai"]})
    messages.append({"role":"user","content": f"Lineage Context:\n{ctx}\n\nQuestion: {question}"})
    return call_claude_chat(system, messages, max_tokens=600)


# =====================================================
# PROCESS ONE QUERY — returns dict stored in session state
# =====================================================

def process_query(q, dfs):
    qdf = dfs.get("query_df")
    if qdf is None:
        return None, "Query metadata not loaded."
    m = qdf[qdf["QUERYID"].str.contains(q,case=False,na=False)|qdf["QUERYNAME"].str.contains(q,case=False,na=False)]
    if m.empty:
        return None, f"No query found matching '{q}'"
    provider = m.iloc[0]["INFOPROVIDER"]
    tree, stats = build_lineage(provider, dfs)
    return {"query":q,"provider":provider,"tree":tree,"stats":stats,"ctx":make_context(q,provider,tree,stats)}, None


# =====================================================
# RENDER — reads entirely from session state
# =====================================================

def render_query_result(q, dfs, ai_sum_on, ai_risk_on, ai_chat_on):
    """Render one query card. All state lives in st.session_state under keys prefixed by q."""

    sk = lambda suffix: f"__{q}__{suffix}"  # namespaced session key

    # ── Load or compute lineage
    if sk("result") not in st.session_state:
        with st.spinner(f"Building lineage for {q}…"):
            result, err = process_query(q, dfs)
        if err:
            st.error(f"❌ {err}")
            return
        st.session_state[sk("result")] = result

    result = st.session_state[sk("result")]
    provider = result["provider"]
    tree     = result["tree"]
    stats    = result["stats"]
    ctx      = result["ctx"]
    t,d,i,score,cx = compute_complexity(stats)

    # ── Header
    c1,c2 = st.columns([3,1])
    with c1:
        st.markdown(f'<div class="query-tag">📍 Provider: {provider}</div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="complexity-{cx.lower()}">⚡ {cx}</div>', unsafe_allow_html=True)

    m1,m2,m3,m4 = st.columns(4)
    m1.metric("🔁 Transformations", t)
    m2.metric("📦 DTPs", d)
    m3.metric("📬 InfoPackages", f"{i:,}")
    m4.metric("🎯 Score", f"{score:,}")

    st.markdown("")

    if sk("chat_history") not in st.session_state:
        st.session_state[sk("chat_history")] = []

    # ── Tabs
    tab_tree, tab_sum, tab_risk, tab_chat = st.tabs(
        ["🌲 Lineage Tree","✨ AI Summary","🛡️ Risk Analysis","💬 Chat"]
    )

    # ── TREE
    with tab_tree:
        lines = tree_lines(tree)
        if len(lines) > 3000:
            lines = lines[:3000]+["","… truncated at 3,000 lines"]
        st.code("\n".join(lines), language=None)

        report = build_report_text(q, provider, tree, stats,
            ai_sum=st.session_state.get(sk("ai_sum"),""),
            risk_data=st.session_state.get(sk("ai_risk")))
        st.session_state[sk("report")] = report
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in q)
        st.download_button("⬇️ Download report (.txt)", data=report.encode(), file_name=f"lineage_{safe}.txt",
                           mime="text/plain", key=sk("dl"))

    # ── AI SUMMARY
    with tab_sum:
        if not ai_sum_on:
            st.info("Enable 'AI Summary' in the sidebar.")
        else:
            txt = st.session_state.get(sk("ai_sum"), None)
            if txt is None:
                st.markdown('<div class="info-box">Click the button below to generate an AI summary of this lineage.</div>', unsafe_allow_html=True)
                if st.button("✨ Generate AI Summary", key=sk("gen_sum"), type="primary"):
                    with st.spinner("✨ Generating AI summary…"):
                        result = do_ai_summary(q, provider, tree, stats)
                    st.session_state[sk("ai_sum")] = result
                    st.rerun()
            elif txt.startswith("[ERROR"):
                st.error(txt)
                if st.button("🔄 Try Again", key=sk("regen_sum")):
                    st.session_state.pop(sk("ai_sum"), None)
                    st.rerun()
            else:
                st.markdown(f'<div class="ai-box">✨ <b>AI Summary</b><br><br>{txt}</div>', unsafe_allow_html=True)
                if st.button("🔄 Regenerate", key=sk("regen_sum")):
                    st.session_state.pop(sk("ai_sum"), None)
                    st.rerun()

    # ── RISK
    with tab_risk:
        if not ai_risk_on:
            st.info("Enable 'Migration Risk Analysis' in the sidebar.")
        else:
            rd = st.session_state.get(sk("ai_risk"), None)
            if rd is None:
                st.markdown('<div class="info-box">Click the button below to run an AI migration risk analysis.</div>', unsafe_allow_html=True)
                if st.button("🛡️ Run Risk Analysis", key=sk("gen_risk"), type="primary"):
                    with st.spinner("🛡️ Analyzing migration risks…"):
                        result = do_ai_risk(q, provider, tree, stats)
                    st.session_state[sk("ai_risk")] = result
                    st.rerun()
            elif "_error" in rd:
                st.error(f"⚠️ {rd['_error']}")
                if st.button("🔄 Try Again", key=sk("retry_risk")):
                    st.session_state.pop(sk("ai_risk"), None)
                    st.rerun()
            else:
                overall = rd.get("overall_risk", "?")
                effort  = rd.get("migration_effort_days", "?")
                summary = rd.get("summary", "")

                ICONS = {"CRITICAL":"🔴","HIGH":"🟠","MEDIUM":"🟡","LOW":"🟢"}
                icon  = ICONS.get(overall, "⚪")

                # Overall risk banner
                rc1, rc2 = st.columns([3, 1])
                with rc1:
                    st.markdown(
                        f'<div class="risk-overall-{overall}">'                        f'<span style="font-size:20px">{icon}</span> '                        f'<b style="font-size:16px"> Overall Migration Risk: {overall}</b>'                        f'<br><span style="opacity:0.92;font-size:13px">{summary}</span></div>',
                        unsafe_allow_html=True
                    )
                with rc2:
                    st.metric("⏱️ Migration Effort", f"{effort} days")

                st.markdown("---")
                st.markdown("#### 🔍 Identified Risks")

                for r in rd.get("risks", []):
                    lvl    = r.get("level", "MEDIUM")
                    r_icon = ICONS.get(lvl, "⚪")
                    st.markdown(
                        f'<div class="risk-{lvl}">'                        f'<b>{r_icon} [{lvl}] &nbsp; {r.get("object","")}</b>'                        f'<br>🔍 &nbsp;{r.get("issue","")}'                        f'<br>✅ &nbsp;<i>{r.get("recommendation","")}</i>'                        f'</div>',
                        unsafe_allow_html=True
                    )

                acts = rd.get("key_actions", [])
                if acts:
                    st.markdown("---")
                    st.markdown("#### 📋 Key Migration Actions")
                    for idx_a, a in enumerate(acts):
                        st.markdown(f"**{idx_a+1}.** {a}")

                st.markdown("")
                if st.button("🔄 Re-analyse", key=sk("regen_risk")):
                    st.session_state.pop(sk("ai_risk"), None)
                    st.rerun()

    # ── CHAT
    with tab_chat:
        if not ai_chat_on:
            st.info("Enable 'Chat with Lineage' in the sidebar.")
            return

        history = st.session_state[sk("chat_history")]

        st.markdown('<div class="info-box">💬 Ask anything about this lineage — data flow, objects, migration steps, etc.</div>', unsafe_allow_html=True)

        # ── Render history
        for turn in history:
            st.markdown(f'<div class="chat-user">👤 <b>You:</b> {turn["user"]}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="chat-ai">🤖 <b>AI:</b> {turn["ai"]}</div>', unsafe_allow_html=True)

        # ── Suggestion buttons (shown only when no history)
        if not history:
            st.markdown("**Suggested questions:**")
            suggestions = [
                f"Summarise the data flow for {q}",
                "How many transformation layers exist?",
                "What DataSources feed this query?",
                "What should I migrate first?",
            ]
            cols = st.columns(2)
            for si, sug in enumerate(suggestions):
                if cols[si%2].button(sug, key=sk(f"sug{si}")):
                    with st.spinner("🤖 Thinking…"):
                        ans = do_chat(sug, ctx, history)
                    st.session_state[sk("chat_history")].append({"user":sug,"ai":ans})
                    st.rerun()

        st.markdown("")

        # ── Input: use st.chat_input (Streamlit 1.23+) — survives reruns perfectly
        user_msg = st.chat_input("Ask a question about this lineage…", key=sk("chat_input"))
        if user_msg:
            with st.spinner("🤖 Thinking…"):
                ans = do_chat(user_msg, ctx, st.session_state[sk("chat_history")])
            st.session_state[sk("chat_history")].append({"user":user_msg,"ai":ans})
            st.rerun()

        if history:
            if st.button("🗑️ Clear chat", key=sk("clear_chat")):
                st.session_state[sk("chat_history")] = []
                st.rerun()



# =====================================================
# RENDER — IMPACT ANALYSIS
# =====================================================

def render_impact_analysis(dfs):
    st.markdown('<div class="tool-section">', unsafe_allow_html=True)
    st.markdown("#### 🔎 Impact Analysis")
    st.markdown("Enter any object name (DataSource, InfoCube, ADSO, Transformation) to see every query that depends on it.")

    ia_input = st.text_input("Object name", placeholder="e.g. 2LIS_03_BX or 0IC_C03",
                              key="ia_input", label_visibility="collapsed")

    if st.button("🔎 Analyse Impact", key="ia_run", type="primary") and ia_input.strip():
        with st.spinner(f"Scanning all queries for '{ia_input}'…"):
            result = do_impact_analysis(ia_input.strip(), dfs)
        st.session_state["ia_result"] = result

    res = st.session_state.get("ia_result")
    if res:
        obj     = res["object"]
        impacted = res["impacted"]
        partial  = res["partial"]
        ai_txt   = res["ai"]

        # AI commentary
        st.markdown(f'<div class="ai-box">🔎 <b>Impact of changing: {obj}</b><br><br>{ai_txt}</div>',
                    unsafe_allow_html=True)

        # Direct hits
        st.markdown(f"**Direct matches — {len(impacted)} quer{'y' if len(impacted)==1 else 'ies'} impacted:**")
        if impacted:
            for q in impacted:
                st.markdown(f'<div class="impact-hit">⚠️ <b>{q}</b> — directly depends on <code>{obj}</code></div>',
                            unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="impact-none">✅ No active queries directly depend on <b>{obj}</b></div>',
                        unsafe_allow_html=True)

        # Partial matches
        if partial:
            st.markdown(f"**Partial name matches ({len(partial)} related objects):**")
            for rel_obj, rel_queries in list(partial.items())[:10]:
                with st.expander(f"📦 {rel_obj} — used by {len(rel_queries)} quer{'y' if len(rel_queries)==1 else 'ies'}"):
                    for q in sorted(rel_queries):
                        st.markdown(f"- `{q}`")

        # Download
        lines = [f"IMPACT ANALYSIS — {obj}", "="*60, ""]
        lines += [f"Direct hits: {len(impacted)}"] + [f"  - {q}" for q in impacted]
        lines += ["", f"Partial matches: {len(partial)}"]
        for po, pq in partial.items():
            lines += [f"  {po}: {', '.join(sorted(pq))}"]
        lines += ["", "AI Commentary:", ai_txt]
        report_text = "\n".join(lines)
        st.download_button("⬇️ Download impact report", report_text.encode(),
                           file_name=f"impact_{obj}.txt", mime="text/plain", key="ia_dl")

    st.markdown('</div>', unsafe_allow_html=True)


# =====================================================
# RENDER — QUERY COMPARISON
# =====================================================

def render_query_comparison(dfs):
    st.markdown('<div class="tool-section">', unsafe_allow_html=True)
    st.markdown("#### ⚖️ Query Comparison")
    st.markdown("Compare two BEx queries side by side — shared objects, diverging paths, and consolidation opportunities.")

    cc1, cc2 = st.columns(2)
    with cc1:
        qc1 = st.text_input("Query 1", placeholder="e.g. ZQUERY_SALES_001", key="qc1", label_visibility="collapsed")
    with cc2:
        qc2 = st.text_input("Query 2", placeholder="e.g. ZQUERY_SALES_002", key="qc2", label_visibility="collapsed")

    if st.button("⚖️ Compare Queries", key="qc_run", type="primary") and qc1.strip() and qc2.strip():
        with st.spinner("Comparing lineages…"):
            result = do_query_comparison(qc1.strip(), qc2.strip(), dfs)
        st.session_state["qc_result"] = result

    res = st.session_state.get("qc_result")
    if res:
        if "error" in res:
            st.error(res["error"])
        else:
            t1,d1,i1,sc1,cx1 = res["stats1"]
            t2,d2,i2,sc2,cx2 = res["stats2"]

            # Side-by-side stats
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f'<div class="compare-box"><b>🔍 {res["q1"]}</b><br>'
                            f'Provider: <code>{res["prov1"]}</code><br>'
                            f'Complexity: <b>{cx1}</b> (score {sc1})<br>'
                            f'Transformations: {t1} | DTPs: {d1} | InfoPkgs: {i1}</div>',
                            unsafe_allow_html=True)
            with col_b:
                st.markdown(f'<div class="compare-box"><b>🔍 {res["q2"]}</b><br>'
                            f'Provider: <code>{res["prov2"]}</code><br>'
                            f'Complexity: <b>{cx2}</b> (score {sc2})<br>'
                            f'Transformations: {t2} | DTPs: {d2} | InfoPkgs: {i2}</div>',
                            unsafe_allow_html=True)

            # AI narrative
            st.markdown(f'<div class="ai-box">⚖️ <b>AI Comparison Analysis</b><br><br>{res["ai"]}</div>',
                        unsafe_allow_html=True)

            # Shared / unique objects
            oc1, oc2, oc3 = st.columns(3)
            with oc1:
                st.markdown(f"**🤝 Shared objects ({len(res['shared'])})**")
                for o in res["shared"][:30]:
                    st.markdown(f'<div class="compare-shared">✅ {o}</div>', unsafe_allow_html=True)
                if len(res["shared"]) > 30:
                    st.caption(f"… and {len(res['shared'])-30} more")
            with oc2:
                st.markdown(f"**📦 Only in {res['q1']} ({len(res['only_q1'])})**")
                for o in res["only_q1"][:30]:
                    st.markdown(f'<div class="compare-unique">🔵 {o}</div>', unsafe_allow_html=True)
                if len(res["only_q1"]) > 30:
                    st.caption(f"… and {len(res['only_q1'])-30} more")
            with oc3:
                st.markdown(f"**📦 Only in {res['q2']} ({len(res['only_q2'])})**")
                for o in res["only_q2"][:30]:
                    st.markdown(f'<div class="compare-unique">🔵 {o}</div>', unsafe_allow_html=True)
                if len(res["only_q2"]) > 30:
                    st.caption(f"… and {len(res['only_q2'])-30} more")

            # Download
            lines = [
                f"QUERY COMPARISON: {res['q1']} vs {res['q2']}", "="*60, "",
                f"{res['q1']}: Provider={res['prov1']} Complexity={cx1} Score={sc1}",
                f"{res['q2']}: Provider={res['prov2']} Complexity={cx2} Score={sc2}", "",
                f"Shared objects ({len(res['shared'])}):",
            ] + [f"  {o}" for o in res["shared"]] + [
                "", f"Only in {res['q1']}:",
            ] + [f"  {o}" for o in res["only_q1"]] + [
                "", f"Only in {res['q2']}:",
            ] + [f"  {o}" for o in res["only_q2"]] + [
                "", "AI Analysis:", res["ai"]
            ]
            safe1 = "".join(c if c.isalnum() else "_" for c in res["q1"])
            safe2 = "".join(c if c.isalnum() else "_" for c in res["q2"])
            cmp_text = "\n".join(lines)
            st.download_button("⬇️ Download comparison report", cmp_text.encode(),
                               file_name=f"compare_{safe1}_vs_{safe2}.txt", mime="text/plain", key="qc_dl")

    st.markdown('</div>', unsafe_allow_html=True)


# =====================================================
# RENDER — DEAD OBJECT DETECTOR
# =====================================================

def render_dead_object_detector(dfs):
    st.markdown('<div class="tool-section">', unsafe_allow_html=True)
    st.markdown("#### 🧹 Dead Object Detector")
    st.markdown("Scans all metadata to find objects not consumed by any active BEx query — safe-to-delete candidates.")

    if st.button("🧹 Scan for Dead Objects", key="dead_run", type="primary"):
        with st.spinner("Scanning entire metadata for unreferenced objects…"):
            result = do_dead_object_detection(dfs)
        st.session_state["dead_result"] = result

    res = st.session_state.get("dead_result")
    if res:
        dead        = res["dead"]
        type_counts = res["type_counts"]
        active_cnt  = res["active_count"]
        ai_txt      = res["ai"]

        # Summary metrics
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("💀 Dead Objects", len(dead))
        mc2.metric("✅ Active Objects", active_cnt)
        mc3.metric("🗑️ Cleanup Potential", f"{round(len(dead)/(len(dead)+active_cnt)*100) if (len(dead)+active_cnt)>0 else 0}%")

        # AI commentary
        st.markdown(f'<div class="ai-box">🧹 <b>AI Dead Object Analysis</b><br><br>{ai_txt}</div>',
                    unsafe_allow_html=True)

        if dead:
            # Group by type
            from collections import defaultdict
            grouped = defaultdict(list)
            for d in dead:
                grouped[d["type"]].append(d["object"])

            for obj_type, objects in sorted(grouped.items()):
                with st.expander(f"💀 {obj_type} — {len(objects)} dead object{'s' if len(objects)>1 else ''}"):
                    for o in objects[:100]:
                        st.markdown(f'<div class="dead-obj">🗑️ <code>{o}</code> — not referenced by any active query</div>',
                                    unsafe_allow_html=True)
                    if len(objects) > 100:
                        st.caption(f"… and {len(objects)-100} more. Download the full report.")
        else:
            st.success("✅ No dead objects found — all metadata objects are referenced by at least one active query!")

        # Download
        lines = ["DEAD OBJECT DETECTION REPORT", "="*60, "",
                 f"Dead objects: {len(dead)}", f"Active objects: {active_cnt}", "",
                 "AI Commentary:", ai_txt, "", "Dead Objects by Type:", "-"*40]
        for d in dead:
            lines.append(f"[{d['type']}]  {d['object']}")
        dead_text = "\n".join(lines)
        st.download_button("⬇️ Download full dead object report", dead_text.encode(),
                           file_name="dead_objects.txt", mime="text/plain", key="dead_dl")

    st.markdown('</div>', unsafe_allow_html=True)


# =====================================================
# MAIN
# =====================================================

def main():
    st.markdown("## 🔗 BW Lineage Analyzer  ✨ AI-Powered")
    st.markdown("Upload metadata, enter BEx queries, get lineage trees with AI summaries, risk analysis and chat.")
    st.markdown("---")

    # ── Sidebar
    with st.sidebar:
        st.markdown("### 📁 Metadata Files")
        uploaded_meta = st.file_uploader("Metadata files", type=["csv","xls","xlsx"],
                                         accept_multiple_files=True, label_visibility="collapsed")
        KEY_MAP   = {"query_df":"query","mp_df":"multiprovider","trfn_df":"transformation",
                     "dtp_df":"dtp","cube_df":"infocube","adso_df":"adso","ip_df":"infopackage"}
        LABEL_MAP = {"query_df":"Query","mp_df":"MultiProvider","trfn_df":"Transformation",
                     "dtp_df":"DTP","cube_df":"InfoCube","adso_df":"ADSO","ip_df":"InfoPackage"}
        if uploaded_meta:
            raw = {k:None for k in KEY_MAP}
            for uf in uploaded_meta:
                nl = uf.name.lower()
                for key,kw in KEY_MAP.items():
                    if kw in nl:
                        raw[key] = read_uploaded(uf); break
        else:
            raw = load_from_folder()
        dfs = prepare_dfs(raw)

        st.markdown("---")
        for key,label in LABEL_MAP.items():
            df = dfs.get(key)
            if df is not None: st.success(f"✅ {label}  ({len(df):,} rows)")
            else:              st.warning(f"⚠️ {label}  — not loaded")

        st.markdown("---")
        st.markdown("### 🔑 API Key")
        try:
            has_secret = bool(st.secrets.get("ANTHROPIC_API_KEY",""))
        except:
            has_secret = False
        if has_secret:
            st.success("✅ API key from secrets")
        else:
            st.text_input("Anthropic API key", type="password", placeholder="sk-ant-...",
                          key="api_key", help="Get key at console.anthropic.com")
            if st.session_state.get("api_key",""):
                st.success("✅ Key set for this session")
            else:
                st.warning("⚠️ No key — AI features disabled")

        st.markdown("---")
        st.markdown("### 🤖 AI Features")
        ai_sum_on    = st.toggle("✨ AI Summary",              value=True)
        ai_risk_on   = st.toggle("🛡️ Migration Risk Analysis", value=True)
        ai_chat_on   = st.toggle("💬 Chat with Lineage",       value=True)
        st.markdown("### 🛠️ AI Tools")
        ai_impact_on = st.toggle("🔎 Impact Analysis",         value=True)
        ai_compare_on= st.toggle("⚖️ Query Comparison",        value=True)
        ai_dead_on   = st.toggle("🧹 Dead Object Detector",    value=True)

    # ── Query inputs
    col_l, col_r = st.columns([1,1], gap="large")

    with col_l:
        st.markdown('<div class="section-header">✏️ Enter Query Names / IDs</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-box">One query per row. Partial names work (contains match).</div>', unsafe_allow_html=True)

        if "query_list" not in st.session_state:
            st.session_state.query_list = [""]

        ca,cc = st.columns([1,1])
        with ca:
            if st.button("➕ Add row"):
                st.session_state.query_list.append(""); st.rerun()
        with cc:
            if st.button("🗑️ Clear all"):
                st.session_state.query_list = [""]; st.rerun()

        updated = []
        for i,val in enumerate(st.session_state.query_list):
            cols = st.columns([10,1])
            with cols[0]:
                v = st.text_input(f"q{i}", value=val, placeholder=f"Query {i+1}",
                                  key=f"qi_{i}", label_visibility="collapsed")
                updated.append(v)
            with cols[1]:
                if len(st.session_state.query_list) > 1:
                    if st.button("✕", key=f"del_{i}"):
                        st.session_state.query_list.pop(i); st.rerun()
        st.session_state.query_list = updated

    with col_r:
        st.markdown('<div class="section-header">📄 Upload Query List File</div>', unsafe_allow_html=True)
        st.markdown('<div class="info-box">CSV/Excel with <code>QUERYID</code> or <code>QUERYNAME</code> column.</div>', unsafe_allow_html=True)
        qfile = st.file_uploader("Query list", type=["csv","xls","xlsx"], label_visibility="collapsed")
        file_queries = []
        if qfile:
            qf = read_uploaded(qfile)
            if qf is not None:
                qf = qf.astype(str)
                if   "QUERYID"   in qf.columns: file_queries = qf["QUERYID"].dropna().str.strip().tolist()
                elif "QUERYNAME" in qf.columns: file_queries = qf["QUERYNAME"].dropna().str.strip().tolist()
                else:                            file_queries = qf.iloc[:,0].dropna().str.strip().tolist()
                file_queries = [q for q in file_queries if q and q.lower()!="nan"]
                st.success(f"✅ {len(file_queries)} quer{'y' if len(file_queries)==1 else 'ies'} loaded")
                with st.expander("Preview"):
                    for q in file_queries[:30]: st.markdown(f"- `{q}`")
                    if len(file_queries)>30: st.markdown(f"_… and {len(file_queries)-30} more_")

    st.markdown("---")

    if st.button("▶️  Run Analysis", type="primary"):
        manual = [q.strip() for q in st.session_state.query_list if q.strip()]
        all_q  = list(dict.fromkeys(manual + file_queries))
        if not all_q:
            st.warning("Enter or upload at least one query.")
        else:
            st.session_state["active_queries"] = all_q

    # ── Render results — ALWAYS rendered if active_queries exists (survives any rerun)
    active = st.session_state.get("active_queries", [])
    if active:
        # Main tabs: Per-Query Results | AI Tools
        main_tab1, main_tab2 = st.tabs(["📋 Query Results", "🛠️ AI Tools"])

        with main_tab1:
            st.markdown(f"#### {len(active)} quer{'y' if len(active)==1 else 'ies'} analysed")
            for q in active:
                with st.expander(f"🔍 {q}", expanded=True):
                    render_query_result(q, dfs, ai_sum_on, ai_risk_on, ai_chat_on)

        with main_tab2:
            st.markdown("Use these tools across your entire metadata — not tied to a specific query.")
            st.markdown("")
            if ai_impact_on:
                render_impact_analysis(dfs)
            if ai_compare_on:
                render_query_comparison(dfs)
            if ai_dead_on:
                render_dead_object_detector(dfs)

        # ── Bulk download + reset (outside tabs so always visible)
        reports = {q: st.session_state.get(f"__{q}__report","") for q in active if st.session_state.get(f"__{q}__report")}
        if len(reports) > 1:
            st.markdown("---")
            zip_buf = BytesIO()
            with zipfile.ZipFile(zip_buf,"w",zipfile.ZIP_DEFLATED) as zf:
                for q,txt in reports.items():
                    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in q)
                    zf.writestr(f"lineage_{safe}.txt", txt)
            zip_buf.seek(0)
            st.download_button(f"⬇️ Download all {len(reports)} reports as ZIP",
                               data=zip_buf, file_name="bw_lineage_reports.zip",
                               mime="application/zip", key="dl_all")

        st.markdown("")
        if st.button("🔄 New Analysis"):
            for key in list(st.session_state.keys()):
                if key.startswith("__") or key in ("active_queries","ia_result","qc_result","dead_result"):
                    del st.session_state[key]
            st.rerun()


if __name__ == "__main__":
    main()