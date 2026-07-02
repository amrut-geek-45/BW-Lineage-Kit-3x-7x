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
        ai_sum_on  = st.toggle("✨ AI Summary",              value=True)
        ai_risk_on = st.toggle("🛡️ Migration Risk Analysis", value=True)
        ai_chat_on = st.toggle("💬 Chat with Lineage",       value=True)

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
        st.markdown(f"### 📋 Results — {len(active)} quer{'y' if len(active)==1 else 'ies'}")

        for q in active:
            with st.expander(f"🔍 {q}", expanded=True):
                render_query_result(q, dfs, ai_sum_on, ai_risk_on, ai_chat_on)

        # ── Bulk download
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

        if st.button("🔄 New Analysis"):
            for key in list(st.session_state.keys()):
                if key.startswith("__") or key == "active_queries":
                    del st.session_state[key]
            st.rerun()


if __name__ == "__main__":
    main()