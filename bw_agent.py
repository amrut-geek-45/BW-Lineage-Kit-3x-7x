import streamlit as st
import pandas as pd
import requests
import json
import re
import io
import zipfile
from datetime import datetime
from collections import defaultdict, Counter

# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="BW System Agent",
    page_icon="🤖",
    layout="wide"
)

# =====================================================
# PASSWORD GATE
# =====================================================

def check_password():
    if st.session_state.get("authenticated"):
        return True
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            "<div style='text-align:center;font-size:32px;margin-bottom:4px'>🤖</div>"
            "<div style='text-align:center;font-size:20px;font-weight:600;"
            "color:#111827;margin-bottom:4px'>BW System Agent</div>"
            "<div style='text-align:center;font-size:13px;color:#64748b;"
            "margin-bottom:24px'>Enter your team password to continue</div>",
            unsafe_allow_html=True
        )
        pwd = st.text_input("Password", type="password",
                            placeholder="Enter password…", key="pwd_input",
                            label_visibility="collapsed")
        if st.button("Sign in", type="primary", use_container_width=True):
            try:
                correct = st.secrets.get("APP_PASSWORD", "")
            except:
                correct = ""
            if correct and pwd == correct:
                st.session_state.authenticated = True
                st.rerun()
            elif not correct:
                st.warning("⚠️ APP_PASSWORD not set in secrets.toml")
            else:
                st.error("❌ Incorrect password — please try again")
        st.markdown(
            "<div style='text-align:center;font-size:11px;color:#94a3b8;"
            "margin-top:16px'>Contact your admin for access</div>",
            unsafe_allow_html=True
        )
    st.stop()

check_password()

# =====================================================
# CSS
# =====================================================

st.markdown("""
<style>
.block-container{padding-top:1.5rem;padding-bottom:2rem}
.hero-title{font-size:36px;font-weight:700;color:white;margin-bottom:4px}
.hero-sub{font-size:15px;color:#A0A0A0;margin-bottom:1rem}
.agent-card{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:16px 20px;margin-bottom:10px}
.agent-card-title{font-size:14px;font-weight:600;color:white;margin-bottom:4px;display:flex;align-items:center;gap:8px}
.agent-card-desc{font-size:12px;color:#8b949e;line-height:1.6}
.status-ok{background:#0f2a1e;border-left:4px solid #3fb950;padding:8px 12px;border-radius:5px;font-size:13px;color:#7ee787;margin:4px 0}
.status-warn{background:#2d1a00;border-left:4px solid #e3b341;padding:8px 12px;border-radius:5px;font-size:13px;color:#f0c674;margin:4px 0}
.status-err{background:#3d0a0a;border-left:4px solid #f85149;padding:8px 12px;border-radius:5px;font-size:13px;color:#ffa198;margin:4px 0}
.status-info{background:#0d1f2d;border-left:4px solid #38bdf8;padding:8px 12px;border-radius:5px;font-size:13px;color:#7dd3fc;margin:4px 0}
.chat-user{background:#1f2937;border-radius:12px 12px 2px 12px;padding:10px 14px;margin:6px 0;font-size:13px;color:#c9d1d9}
.chat-agent{background:#0d1117;border:1px solid #30363d;border-radius:2px 12px 12px 12px;padding:10px 14px;margin:6px 0;font-size:13px;color:#c9d1d9;line-height:1.7}
.chat-tool{background:#162032;border-left:3px solid #38bdf8;padding:6px 10px;border-radius:4px;font-size:11px;color:#7dd3fc;margin:3px 0;font-family:monospace}
.metric-mini{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:10px 14px;text-align:center}
.metric-mini-val{font-size:22px;font-weight:700;color:white}
.metric-mini-lbl{font-size:11px;color:#8b949e;text-transform:uppercase;letter-spacing:.05em}
.wave-card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px 16px;margin:6px 0}
.wave-title{font-size:14px;font-weight:600;margin-bottom:6px}
.wave-q{background:#0d1117;padding:4px 8px;border-radius:4px;font-size:12px;color:#c9d1d9;margin:2px 0;font-family:monospace}
.risk-HIGH{color:#f85149}.risk-MEDIUM{color:#e3b341}.risk-LOW{color:#3fb950}.risk-CRITICAL{color:#ff6e6e}
.plan-step{display:flex;gap:10px;margin-bottom:8px}
div[data-testid="stDownloadButton"] button{background:#238636;color:white;border:none;border-radius:6px;font-weight:600;padding:8px 20px}
div[data-testid="metric-container"]{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:12px 16px}
</style>
""", unsafe_allow_html=True)

# =====================================================
# METADATA LOADERS
# =====================================================

def _read_df(uf):
    if uf is None:
        return None
    try:
        name = uf.name.lower()
        if name.endswith(".csv"):
            for enc in ["utf-8","utf-8-sig","cp1252","latin1"]:
                try:
                    uf.seek(0)
                    return pd.read_csv(uf, encoding=enc, engine="python", on_bad_lines="skip")
                except:
                    pass
        elif name.endswith((".xls",".xlsx")):
            uf.seek(0)
            return pd.read_excel(uf)
    except:
        pass
    return None

def _filter_active(df):
    if df is None:
        return None
    df = df.astype(str)
    if "OBJVERS" in df.columns:
        df = df[df["OBJVERS"].str.strip().str.upper() == "A"].copy()
    return df

def prepare_dfs(uploads):
    dfs = {}
    for key, uf in uploads.items():
        df = _filter_active(_read_df(uf))
        if df is not None and len(df) > 0:
            dfs[key] = df
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
# LINEAGE ENGINE
# =====================================================

def get_object_type(obj, dfs):
    obj = str(obj).upper().strip()
    if obj in dfs["_mp_set"]:   return "MULTIPROVIDER"
    if obj in dfs["_cube_set"]: return "INFOCUBE"
    if obj in dfs["_adso_set"]: return "ADSO"
    if obj.endswith("_TR"):     return "INFOSOURCE"
    return "DATASOURCE"

def build_lineage(provider, dfs):
    visited = set()
    stats   = {"transformations":set(),"dtps":set(),"ip_count":0}
    trfn_df = dfs.get("trfn_df"); dtp_df = dfs.get("dtp_df")
    mp_df   = dfs.get("mp_df");   ip_df  = dfs.get("ip_df")

    def _proc(prov):
        pu = prov.upper()
        if pu in visited: return None
        visited.add(pu)
        node = {"provider":prov,"type":get_object_type(prov,dfs),"children":[],"dtps":[],"transformations":[],"ip_nodes":[],"infopackages":0}
        if dtp_df is not None and "SRC" in dtp_df.columns:
            base = prov.replace("_TR","")
            dm = dtp_df[dtp_df["SRC"].str.upper().eq(base.upper())&dtp_df["TGT"].str.upper().eq(pu)]
            if not dm.empty:
                dtps = dm["DTP"].dropna().astype(str).tolist()
                node["dtps"]=dtps; stats["dtps"].update(dtps)
        if trfn_df is not None and "TARGETNAME" in trfn_df.columns:
            tm = trfn_df[trfn_df["TARGETNAME"].str.upper().eq(pu)]
            if not tm.empty:
                trs = tm["TRANID"].dropna().astype(str).tolist()
                node["transformations"]=trs; stats["transformations"].update(trs)
        if ip_df is not None and "OLTPSOURCE" in ip_df.columns:
            base = prov.replace("_TR","")
            ip_rows = ip_df[ip_df["OLTPSOURCE"].str.upper().eq(base.upper())]
            node["infopackages"]=len(ip_rows); stats["ip_count"]+=len(ip_rows)
            for _,irow in ip_rows.iterrows():
                ip_id = str(irow.get("LOGDPID","")).strip()
                if ip_id and ip_id.lower()!="nan": node["ip_nodes"].append(ip_id)
        if node["type"]=="MULTIPROVIDER" and mp_df is not None:
            for cube in mp_df[mp_df["MULTIPROVIDER"].str.upper().eq(pu)]["PARTPROVIDER"].dropna().unique():
                ch=_proc(str(cube).strip())
                if ch: node["children"].append(ch)
        if trfn_df is not None and "TARGETNAME" in trfn_df.columns:
            for _,row in trfn_df[trfn_df["TARGETNAME"].str.upper().eq(pu)].iterrows():
                tranid=str(row["TRANID"]).strip(); source=str(row["SOURCENAME"]).strip()
                base_s=source.replace("_TR",""); stats["transformations"].add(tranid)
                dtp_list=[]
                if dtp_df is not None and "SRC" in dtp_df.columns:
                    dm2=dtp_df[dtp_df["SRC"].str.upper().eq(base_s.upper())&dtp_df["TGT"].str.upper().eq(pu)]
                    if not dm2.empty: dtp_list=dm2["DTP"].dropna().astype(str).tolist(); stats["dtps"].update(dtp_list)
                ip_list=[]
                if ip_df is not None and "OLTPSOURCE" in ip_df.columns:
                    ipm2=ip_df[ip_df["OLTPSOURCE"].str.upper().eq(base_s.upper())]
                    stats["ip_count"]+=len(ipm2)
                    for _,irow in ipm2.iterrows():
                        ip_id=str(irow.get("LOGDPID","")).strip()
                        if ip_id and ip_id.lower()!="nan": ip_list.append(ip_id)
                node["children"].append({"transformation":tranid,"source":source,"lineage":_proc(source),"dtp_list":dtp_list,"dtps":len(dtp_list),"ip_list":ip_list,"infopackages":len(ip_list)})
        return node
    return _proc(str(provider).strip()), stats

def compute_complexity(stats):
    t=len(stats["transformations"]); d=len(stats["dtps"]); i=stats["ip_count"]
    score=(t*5)+(d*3)+i
    cx="LOW" if score<10 else ("MEDIUM" if score<30 else "HIGH")
    return t,d,i,score,cx

def tree_to_text(tree):
    lines=[]
    def _walk(node,level=0):
        if not node: return
        pad="    "*level
        lines.append(f"{pad}[{node['type']}] {node['provider']}")
        for child in node.get("children",[]):
            if "transformation" in child:
                lines.append(f"{pad}  └─ TRFN: {child['transformation']}")
                lines.append(f"{pad}     └─ SRC: {child['source']}")
                if child.get("lineage"): _walk(child["lineage"],level+2)
            else: _walk(child,level+1)
    _walk(tree)
    return "\n".join(lines)

# =====================================================
# SYSTEM METRICS
# =====================================================

def compute_system_metrics(dfs):
    query_df = dfs.get("query_df")
    trfn_df  = dfs.get("trfn_df")
    dtp_df   = dfs.get("dtp_df")
    ip_df    = dfs.get("ip_df")
    cube_df  = dfs.get("cube_df")
    adso_df  = dfs.get("adso_df")
    mp_df    = dfs.get("mp_df")

    metrics = {
        "total_queries":       len(query_df)   if query_df  is not None else 0,
        "total_transformations":len(trfn_df)   if trfn_df   is not None else 0,
        "total_dtps":          len(dtp_df)     if dtp_df    is not None else 0,
        "total_infopackages":  len(ip_df)      if ip_df     is not None else 0,
        "total_infocubes":     len(cube_df)    if cube_df   is not None else 0,
        "total_adsos":         len(adso_df)    if adso_df   is not None else 0,
        "total_multiproviders":len(mp_df)      if mp_df     is not None else 0,
    }

    # Provider distribution
    if query_df is not None and "INFOPROVIDER" in query_df.columns:
        metrics["provider_counts"] = query_df["INFOPROVIDER"].value_counts().head(10).to_dict()
    else:
        metrics["provider_counts"] = {}

    # DataSource distribution
    if ip_df is not None and "OLTPSOURCE" in ip_df.columns:
        metrics["datasource_counts"] = ip_df["OLTPSOURCE"].value_counts().head(10).to_dict()
    else:
        metrics["datasource_counts"] = {}

    return metrics

# =====================================================
# WAVE PLANNER
# =====================================================

def build_wave_plan(dfs, max_queries=200):
    query_df = dfs.get("query_df")
    if query_df is None:
        return []

    # Score every query
    scored = []
    sample = query_df.head(max_queries)
    for _, row in sample.iterrows():
        qid  = str(row.get("QUERYID","")).strip()
        prov = str(row.get("INFOPROVIDER","")).strip()
        if not qid or not prov or qid.lower()=="nan":
            continue
        try:
            _, stats = build_lineage(prov, dfs)
            t,d,i,score,cx = compute_complexity(stats)
        except:
            score=0; cx="LOW"; t=d=i=0
        scored.append({"query":qid,"provider":prov,"complexity":cx,"score":score,"t":t,"d":d,"ip":i})

    # Sort by score ascending (easiest first)
    scored.sort(key=lambda x: x["score"])

    # Group into 3 waves
    waves = [
        {"wave":1,"label":"Wave 1 — Quick Wins","colour":"#3fb950","desc":"LOW complexity, no shared objects, migrate first","queries":[]},
        {"wave":2,"label":"Wave 2 — Core Objects","colour":"#e3b341","desc":"MEDIUM complexity, some shared providers","queries":[]},
        {"wave":3,"label":"Wave 3 — Complex Objects","colour":"#f85149","desc":"HIGH complexity, many transformations/DTPs","queries":[]},
    ]
    for q in scored:
        if   q["complexity"]=="LOW":    waves[0]["queries"].append(q)
        elif q["complexity"]=="MEDIUM": waves[1]["queries"].append(q)
        else:                           waves[2]["queries"].append(q)

    return waves

# =====================================================
# DEAD OBJECTS
# =====================================================

def collect_all_objects(dfs):
    query_df=dfs.get("query_df"); trfn_df=dfs.get("trfn_df"); obj_map={}
    if query_df is None: return obj_map
    for _,row in query_df.iterrows():
        qid=str(row.get("QUERYID","")).strip(); provider=str(row.get("INFOPROVIDER","")).strip()
        if not qid or not provider: continue
        visited=set()
        def _collect(prov):
            pu=prov.upper()
            if pu in visited: return
            visited.add(pu); obj_map.setdefault(pu,set()).add(qid)
            if trfn_df is not None and "TARGETNAME" in trfn_df.columns:
                for _,r in trfn_df[trfn_df["TARGETNAME"].str.upper().eq(pu)].iterrows():
                    src=str(r["SOURCENAME"]).strip(); obj_map.setdefault(src.upper(),set()).add(qid); _collect(src)
            if dfs.get("mp_df") is not None and "PARTPROVIDER" in dfs["mp_df"].columns:
                for part in dfs["mp_df"][dfs["mp_df"]["MULTIPROVIDER"].str.upper().eq(pu)]["PARTPROVIDER"].dropna():
                    _collect(str(part).strip())
        _collect(provider)
    return obj_map

def find_dead_objects(dfs):
    active=set(collect_all_objects(dfs).keys()); dead=[]; seen=set()
    checks=[("trfn_df","TARGETNAME","TRANSFORMATION"),("dtp_df","DTP","DTP"),
            ("cube_df","INFOCUBE","INFOCUBE"),("adso_df","ADSO","ADSO"),("ip_df","OLTPSOURCE","DATASOURCE")]
    for df_key,col,label in checks:
        df=dfs.get(df_key)
        if df is not None and col in df.columns:
            for obj in df[col].dropna().str.upper().unique():
                obj=obj.strip()
                if obj and obj not in active and obj not in seen:
                    seen.add(obj); dead.append({"type":label,"object":obj})
    return dead, len(active)

# =====================================================
# AI HELPERS
# =====================================================

def get_api_key():
    try:
        k=st.secrets.get("ANTHROPIC_API_KEY","")
        if k: return k
    except: pass
    return st.session_state.get("api_key","").strip()

def call_claude(system, user, max_tokens=900):
    key=get_api_key()
    if not key: return "[ERROR: No API key]"
    try:
        r=requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":max_tokens,"system":system,"messages":[{"role":"user","content":user}]},
            timeout=60
        )
        if r.status_code!=200: return f"[ERROR {r.status_code}]"
        return "".join(b.get("text","") for b in r.json().get("content",[]))
    except Exception as e: return f"[ERROR: {e}]"

def call_claude_chat(system, messages, max_tokens=800):
    key=get_api_key()
    if not key: return "[ERROR: No API key]"
    try:
        r=requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json","x-api-key":key,"anthropic-version":"2023-06-01"},
            json={"model":"claude-sonnet-4-6","max_tokens":max_tokens,"system":system,"messages":messages},
            timeout=60
        )
        if r.status_code!=200: return f"[ERROR {r.status_code}]"
        return "".join(b.get("text","") for b in r.json().get("content",[]))
    except Exception as e: return f"[ERROR: {e}]"

# =====================================================
# AGENT TOOL FUNCTIONS
# =====================================================

def agent_system_summary(dfs):
    """Agent tool: system-level health summary."""
    metrics = compute_system_metrics(dfs)
    dead, active = find_dead_objects(dfs)
    dead_pct = round(len(dead)/(len(dead)+active)*100) if (len(dead)+active)>0 else 0
    ctx = (
        f"SAP BW System Metadata Summary:\n"
        f"- Queries: {metrics['total_queries']}\n"
        f"- Transformations: {metrics['total_transformations']}\n"
        f"- DTPs: {metrics['total_dtps']}\n"
        f"- InfoPackages: {metrics['total_infopackages']}\n"
        f"- InfoCubes: {metrics['total_infocubes']}\n"
        f"- ADSOs: {metrics['total_adsos']}\n"
        f"- MultiProviders: {metrics['total_multiproviders']}\n"
        f"- Dead objects: {len(dead)} ({dead_pct}% of total)\n"
        f"- Active objects: {active}\n"
        f"Top providers: {list(metrics['provider_counts'].items())[:5]}\n"
        f"Top DataSources: {list(metrics['datasource_counts'].items())[:5]}"
    )
    return call_claude(
        "You are an SAP BW/4HANA system expert.",
        f"Analyse this SAP BW system metadata and provide a comprehensive health assessment.\n\n{ctx}\n\n"
        "Cover: system size, complexity level, migration readiness, top concerns, and 3-5 recommended actions. "
        "Be specific and use the numbers provided.",
        max_tokens=700
    ), metrics, len(dead)

def agent_wave_plan_ai(waves, dfs):
    """Agent tool: AI narrative for migration wave plan."""
    metrics = compute_system_metrics(dfs)
    w1=len(waves[0]["queries"]) if waves else 0
    w2=len(waves[1]["queries"]) if len(waves)>1 else 0
    w3=len(waves[2]["queries"]) if len(waves)>2 else 0
    ctx = (
        f"Migration Wave Plan:\n"
        f"Wave 1 (LOW complexity): {w1} queries\n"
        f"Wave 2 (MEDIUM complexity): {w2} queries\n"
        f"Wave 3 (HIGH complexity): {w3} queries\n"
        f"Total: {w1+w2+w3} queries analysed\n"
        f"Total in system: {metrics.get('total_queries',0)}\n"
    )
    if waves and waves[0]["queries"]:
        ctx += f"Wave 1 sample: {[q['query'] for q in waves[0]['queries'][:5]]}\n"
    if len(waves)>2 and waves[2]["queries"]:
        ctx += f"Wave 3 hardest: {sorted(waves[2]['queries'],key=lambda x:x['score'],reverse=True)[:3]}\n"
    return call_claude(
        "You are an SAP BW/4HANA migration project manager.",
        f"Write a migration wave plan narrative for this BW system.\n\n{ctx}\n\n"
        "Include: recommended sequence, estimated effort per wave (person-days), dependencies to watch, "
        "parallel workstreams possible, and key risks per wave. 6-8 sentences.",
        max_tokens=600
    )

def agent_monitoring_report(dfs):
    """Agent tool: monitoring / health check report."""
    metrics = compute_system_metrics(dfs)
    dead, active = find_dead_objects(dfs)
    dead_by_type = dict(Counter(d["type"] for d in dead))
    ip_df = dfs.get("ip_df")
    ds_list = []
    if ip_df is not None and "OLTPSOURCE" in ip_df.columns:
        ds_list = ip_df["OLTPSOURCE"].dropna().str.upper().unique().tolist()[:20]
    lis_count  = sum(1 for d in ds_list if d.startswith("2LIS"))
    fi_count   = sum(1 for d in ds_list if d.startswith("0FI") or d.startswith("0CO"))
    cust_count = sum(1 for d in ds_list if d.startswith("Z"))
    ctx = (
        f"BW System Health Check:\n"
        f"Objects: Q={metrics['total_queries']} T={metrics['total_transformations']} "
        f"DTP={metrics['total_dtps']} IP={metrics['total_infopackages']}\n"
        f"Dead objects: {len(dead)} — breakdown: {dead_by_type}\n"
        f"DataSource types: LIS={lis_count} FI/CO={fi_count} Custom(Z)={cust_count}\n"
        f"InfoCubes: {metrics['total_infocubes']} (need ADSO conversion in BW/4HANA)\n"
        f"MultiProviders: {metrics['total_multiproviders']} (deprecated in BW/4HANA)\n"
    )
    return call_claude(
        "You are an SAP BW system monitoring expert.",
        f"Generate a system monitoring and health report for this BW system.\n\n{ctx}\n\n"
        "Cover: object inventory status, deprecated objects that need attention, "
        "housekeeping recommendations, data load risk areas, "
        "and 5 specific action items with priority (HIGH/MEDIUM/LOW). "
        "Format as a professional report.",
        max_tokens=700
    ), dead_by_type

def agent_answer_question(question, dfs, chat_history):
    """Agent tool: answer any question about the BW system."""
    metrics = compute_system_metrics(dfs)
    dead, active = find_dead_objects(dfs)

    # Build rich context
    system_ctx = (
        f"SAP BW System Context:\n"
        f"Queries:{metrics['total_queries']} Transformations:{metrics['total_transformations']} "
        f"DTPs:{metrics['total_dtps']} InfoPackages:{metrics['total_infopackages']} "
        f"InfoCubes:{metrics['total_infocubes']} ADSOs:{metrics['total_adsos']} "
        f"MultiProviders:{metrics['total_multiproviders']} Dead objects:{len(dead)}\n"
        f"Top providers: {list(metrics['provider_counts'].items())[:8]}\n"
        f"Top DataSources: {list(metrics['datasource_counts'].items())[:8]}\n"
    )

    # Detect if question is about a specific query
    query_df = dfs.get("query_df")
    specific_ctx = ""
    if query_df is not None:
        mask = pd.Series(False, index=query_df.index)
        if "QUERYID"   in query_df.columns: mask = mask | query_df["QUERYID"].str.contains(question[:30], case=False, na=False)
        if "QUERYNAME" in query_df.columns: mask = mask | query_df["QUERYNAME"].str.contains(question[:30], case=False, na=False)
        matches = query_df[mask]
        if not matches.empty:
            prov = str(matches.iloc[0]["INFOPROVIDER"]).strip()
            try:
                _, stats = build_lineage(prov, dfs)
                t,d,i,score,cx = compute_complexity(stats)
                specific_ctx = f"\nSpecific query found: {matches.iloc[0].get('QUERYID','')} on {prov} — Complexity:{cx} Score:{score} T:{t} D:{d} IP:{i}"
            except:
                pass

    system_prompt = (
        "You are an expert SAP BW/4HANA system agent. You have full knowledge of the BW system metadata. "
        "Answer questions accurately using the system context provided. "
        "If asked about specific objects, use the context to give precise answers. "
        "If you don't have enough information, say so clearly."
    )

    messages = []
    for h in chat_history:
        messages.append({"role":"user","content":h["user"]})
        messages.append({"role":"assistant","content":h["ai"]})
    messages.append({
        "role":"user",
        "content":f"System Context:\n{system_ctx}{specific_ctx}\n\nQuestion: {question}"
    })
    return call_claude_chat(system_prompt, messages, max_tokens=800)

# =====================================================
# SESSION STATE
# =====================================================

defaults = {
    "meta_uploaded":{}, "meta_ready":False, "dfs_cache":None,
    "agent_chat":[], "agent_summary":None, "agent_waves":None,
    "agent_wave_ai":None, "agent_monitor":None, "agent_monitor_dead":None,
    "active_mode":"chat",
}
for k,v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =====================================================
# METADATA FILES CONFIG
# =====================================================

META_FILES = {
    "query_df": {"label":"📋 Query File",         "desc":"QUERYID · QUERYNAME · INFOPROVIDER",   "required":True},
    "trfn_df":  {"label":"🔁 Transformation File", "desc":"TRANID · SOURCENAME · TARGETNAME",     "required":True},
    "dtp_df":   {"label":"📦 DTP File",            "desc":"DTP · SRC · TGT",                     "required":True},
    "ip_df":    {"label":"📬 InfoPackage File",    "desc":"LOGDPID · OLTPSOURCE",                "required":True},
    "cube_df":  {"label":"🧊 InfoCube File",       "desc":"INFOCUBE column",                     "required":False},
    "adso_df":  {"label":"🗄️ ADSO File",           "desc":"ADSO column",                         "required":False},
    "mp_df":    {"label":"🔀 MultiProvider File",  "desc":"MULTIPROVIDER · PARTPROVIDER",        "required":False},
}

# =====================================================
# HEADER
# =====================================================

st.markdown("<div class='hero-title'>🤖 BW System Agent</div>", unsafe_allow_html=True)
st.markdown("<div class='hero-sub'>AI-powered SAP BW Migration · Monitoring · Analysis Agent</div>", unsafe_allow_html=True)
st.markdown("---")

# =====================================================
# METADATA UPLOAD GATE
# =====================================================

if not st.session_state.meta_ready:
    st.markdown("### 📁 Upload BW Metadata Files")
    st.markdown("Upload your SAP BW metadata exports. Required files must be uploaded to start the agent.")
    st.markdown("")

    req_keys = [k for k,v in META_FILES.items() if v["required"]]
    opt_keys = [k for k,v in META_FILES.items() if not v["required"]]

    st.markdown("##### ★ Required")
    rc = st.columns(2)
    for i,key in enumerate(req_keys):
        meta=META_FILES[key]
        with rc[i%2]:
            already = st.session_state.meta_uploaded.get(key)
            st.markdown(f"**{meta['label']}** <span style='color:#f85149;font-size:11px'>★</span> — `{meta['desc']}`", unsafe_allow_html=True)
            uf = st.file_uploader(meta["label"], type=["csv","xls","xlsx"], key=f"m_{key}", label_visibility="collapsed")
            if uf:
                st.session_state.meta_uploaded[key]=uf; st.success(f"✅ {uf.name}")
            elif already:
                st.success(f"✅ {already.name}")

    st.markdown("##### Optional")
    oc = st.columns(3)
    for i,key in enumerate(opt_keys):
        meta=META_FILES[key]
        with oc[i%3]:
            already=st.session_state.meta_uploaded.get(key)
            st.markdown(f"**{meta['label']}** — `{meta['desc']}`")
            uf=st.file_uploader(meta["label"],type=["csv","xls","xlsx"],key=f"m_{key}",label_visibility="collapsed")
            if uf:
                st.session_state.meta_uploaded[key]=uf; st.success(f"✅ {uf.name}")
            elif already:
                st.success(f"✅ {already.name}")

    st.markdown("---")
    uploaded_keys = set(st.session_state.meta_uploaded.keys())
    required_done = all(k in uploaded_keys for k in req_keys)
    missing = [META_FILES[k]["label"] for k in req_keys if k not in uploaded_keys]

    c1,c2,c3 = st.columns([3,1,1])
    with c1:
        if required_done: st.success(f"✅ All required files ready — {len(uploaded_keys)}/7 total")
        else:             st.warning(f"⚠️ Still needed: {' · '.join(missing)}")
    with c2:
        if st.button("▶️ Start Agent", type="primary", disabled=not required_done, use_container_width=True):
            with st.spinner("Loading metadata…"):
                st.session_state.dfs_cache  = prepare_dfs(st.session_state.meta_uploaded)
                st.session_state.meta_ready = True
            st.rerun()
    with c3:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.meta_uploaded={}; st.session_state.meta_ready=False
            st.session_state.dfs_cache=None; st.rerun()
    st.stop()

dfs = st.session_state.dfs_cache

# =====================================================
# SIDEBAR
# =====================================================

with st.sidebar:
    st.markdown("### 🤖 Agent Mode")
    mode = st.radio("", ["💬 Ask Agent","📊 System Health","🗺️ Wave Planner","🔍 Monitoring"],
                    key="mode_radio", label_visibility="collapsed")
    st.session_state.active_mode = mode

    st.markdown("---")
    st.markdown("### 📁 Metadata")
    for key,meta in META_FILES.items():
        df=dfs.get(key)
        if df is not None:   st.success(f"✅ {meta['label']} ({len(df):,})")
        elif meta["required"]: st.error(f"❌ {meta['label']}")
        else:                  st.warning(f"⚠️ {meta['label']}")
    if st.button("🔄 Re-upload", use_container_width=True):
        st.session_state.meta_ready=False; st.session_state.dfs_cache=None
        st.session_state.meta_uploaded={}
        for k in list(st.session_state.keys()):
            if k not in ("meta_uploaded","meta_ready","dfs_cache","api_key"):
                del st.session_state[k]
        st.rerun()

    st.markdown("---")
    st.markdown("### 🔑 API Key")
    try:    has_secret=bool(st.secrets.get("ANTHROPIC_API_KEY",""))
    except: has_secret=False
    if has_secret:
        st.success("✅ Key from secrets")
    else:
        st.text_input("Anthropic API key",type="password",placeholder="sk-ant-...",key="api_key")
        if st.session_state.get("api_key",""): st.success("✅ Key set")
        else: st.warning("⚠️ No key — AI disabled")

    st.markdown("---")
    # Quick stats
    query_df=dfs.get("query_df")
    st.markdown("### 📊 Quick Stats")
    st.metric("Queries",  len(query_df)           if query_df          is not None else 0)
    st.metric("InfoCubes",len(dfs.get("cube_df")) if dfs.get("cube_df") is not None else 0)
    st.metric("ADSOs",    len(dfs.get("adso_df")) if dfs.get("adso_df") is not None else 0)
    st.metric("DTPs",     len(dfs.get("dtp_df"))  if dfs.get("dtp_df")  is not None else 0)

# =====================================================
# MODE: 💬 ASK AGENT
# =====================================================

if mode == "💬 Ask Agent":
    st.markdown("#### 💬 Ask the BW System Agent")
    st.caption("Ask anything about your BW system — queries, objects, migration, housekeeping, analysis. The agent knows your full metadata.")

    # Suggested questions
    if not st.session_state.agent_chat:
        st.markdown("**Suggested questions:**")
        suggs = [
            "How many queries does this system have and what is the complexity distribution?",
            "Which InfoCubes need to be converted to ADSO for BW/4HANA migration?",
            "What are the top 5 most complex queries and why?",
            "How many dead objects are there and which types?",
            "Which DataSources are LIS-based and need S/4HANA equivalents?",
            "Give me a high-level migration readiness assessment.",
        ]
        s_cols = st.columns(2)
        for si,sug in enumerate(suggs):
            if s_cols[si%2].button(sug, key=f"sugg_{si}"):
                with st.spinner("🤖 Agent thinking…"):
                    ans = agent_answer_question(sug, dfs, st.session_state.agent_chat)
                st.session_state.agent_chat.append({"user":sug,"ai":ans,"tool":"system_analysis"})
                st.rerun()

    # Chat history
    for turn in st.session_state.agent_chat:
        st.markdown(f'<div class="chat-user">👤 <b>You:</b> {turn["user"]}</div>', unsafe_allow_html=True)
        if turn.get("tool"):
            st.markdown(f'<div class="chat-tool">🔧 Tool used: {turn["tool"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="chat-agent">🤖 <b>Agent:</b> {turn["ai"]}</div>', unsafe_allow_html=True)

    # Input
    user_q = st.chat_input("Ask anything about your BW system…", key="agent_inp")
    if user_q:
        with st.spinner("🤖 Agent thinking…"):
            ans = agent_answer_question(user_q, dfs, st.session_state.agent_chat)
        st.session_state.agent_chat.append({"user":user_q,"ai":ans,"tool":"system_analysis"})
        st.rerun()

    if st.session_state.agent_chat:
        if st.button("🗑️ Clear conversation", key="clr_chat"):
            st.session_state.agent_chat = []; st.rerun()

# =====================================================
# MODE: 📊 SYSTEM HEALTH
# =====================================================

elif mode == "📊 System Health":
    st.markdown("#### 📊 System Health Dashboard")
    st.caption("Full inventory, complexity breakdown and AI health assessment of your BW system.")

    if st.button("🔄 Generate Health Report", type="primary", key="gen_health"):
        with st.spinner("🤖 Analysing system…"):
            summary_ai, metrics, dead_count = agent_system_summary(dfs)
            st.session_state.agent_summary = {"ai":summary_ai,"metrics":metrics,"dead":dead_count}
        st.rerun()

    res = st.session_state.agent_summary
    if res:
        m = res["metrics"]

        # Metric cards row 1
        mc = st.columns(4)
        mc[0].metric("📋 Queries",        m["total_queries"])
        mc[1].metric("🔁 Transformations", m["total_transformations"])
        mc[2].metric("📦 DTPs",            m["total_dtps"])
        mc[3].metric("📬 InfoPackages",    m["total_infopackages"])

        # Metric cards row 2
        mc2 = st.columns(4)
        mc2[0].metric("🧊 InfoCubes",       m["total_infocubes"])
        mc2[1].metric("🗄️ ADSOs",           m["total_adsos"])
        mc2[2].metric("🔀 MultiProviders",  m["total_multiproviders"])
        mc2[3].metric("💀 Dead Objects",    res["dead"])
        st.markdown("")

        # AI Health Assessment
        st.markdown("##### 🤖 AI Health Assessment")
        ai_text = res["ai"]
        if ai_text.startswith("[ERROR"):
            st.error(ai_text)
        else:
            st.markdown(
                f'<div style="background:#0d1117;border-left:4px solid #6f42c1;padding:14px 18px;'
                f'border-radius:6px;color:#c9d1d9;font-size:14px;line-height:1.7">{ai_text}</div>',
                unsafe_allow_html=True
            )

        # Top Providers
        if m.get("provider_counts"):
            st.markdown("##### 📊 Top InfoProviders by Query Count")
            prov_df = pd.DataFrame(list(m["provider_counts"].items()), columns=["InfoProvider","Queries"])
            st.dataframe(prov_df, use_container_width=True, hide_index=True)

        # Top DataSources
        if m.get("datasource_counts"):
            st.markdown("##### 📡 Top DataSources by InfoPackage Count")
            ds_df = pd.DataFrame(list(m["datasource_counts"].items()), columns=["DataSource","InfoPackages"])
            st.dataframe(ds_df, use_container_width=True, hide_index=True)

        # Download report
        report_lines = [
            "BW SYSTEM HEALTH REPORT",
            "="*60,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "OBJECT COUNTS:",
            f"  Queries:          {m['total_queries']}",
            f"  Transformations:  {m['total_transformations']}",
            f"  DTPs:             {m['total_dtps']}",
            f"  InfoPackages:     {m['total_infopackages']}",
            f"  InfoCubes:        {m['total_infocubes']}",
            f"  ADSOs:            {m['total_adsos']}",
            f"  MultiProviders:   {m['total_multiproviders']}",
            f"  Dead Objects:     {res['dead']}",
            "",
            "AI HEALTH ASSESSMENT:",
            ai_text,
        ]
        st.download_button("⬇️ Download Health Report (.txt)",
                           data="\n".join(report_lines).encode(),
                           file_name="bw_health_report.txt", mime="text/plain")

# =====================================================
# MODE: 🗺️ WAVE PLANNER
# =====================================================

elif mode == "🗺️ Wave Planner":
    st.markdown("#### 🗺️ Migration Wave Planner")
    st.caption("AI groups your queries into migration waves based on complexity, dependencies and effort.")

    max_q = st.slider("Max queries to analyse (larger = slower)", 50, 500, 200, 50, key="wave_max")

    if st.button("▶️ Build Wave Plan", type="primary", key="gen_waves"):
        with st.spinner(f"Analysing up to {max_q} queries…"):
            waves = build_wave_plan(dfs, max_queries=max_q)
            st.session_state.agent_waves = waves
            st.session_state.agent_wave_ai = None
        st.rerun()

    waves = st.session_state.agent_waves
    if waves:
        total = sum(len(w["queries"]) for w in waves)
        wc = st.columns(3)
        for wi,w in enumerate(waves):
            with wc[wi]:
                with wc[wi]:
                    colour = w["colour"]
                    label  = w["label"]
                    qcount = len(w["queries"])
                    desc   = w["desc"]
                    html_card = (
                        f"<div class='wave-card'>"
                        f"<div class='wave-title' style='color:{colour}'>{label}</div>"
                        f"<div style='font-size:28px;font-weight:700;color:{colour}'>{qcount}</div>"
                        f"<div style='font-size:12px;color:#8b949e;margin-top:4px'>{desc}</div>"
                        f"</div>"
                    )
                    st.markdown(html_card, unsafe_allow_html=True)

        st.markdown(f"**{total} queries analysed** across {len(waves)} waves")
        st.markdown("")

        # AI narrative
        if st.session_state.agent_wave_ai is None:
            if st.button("🤖 Generate AI Migration Narrative", key="gen_wave_ai"):
                with st.spinner("🤖 Writing migration plan…"):
                    st.session_state.agent_wave_ai = agent_wave_plan_ai(waves, dfs)
                st.rerun()
        else:
            ai_text = st.session_state.agent_wave_ai
            if not ai_text.startswith("[ERROR"):
                st.markdown(
                    f'<div style="background:#0d1117;border-left:4px solid #6f42c1;padding:14px 18px;'
                    f'border-radius:6px;color:#c9d1d9;font-size:14px;line-height:1.7;margin-bottom:12px">'
                    f'🗺️ <b>Migration Plan</b><br><br>{ai_text}</div>',
                    unsafe_allow_html=True
                )

        # Wave details
        for w in waves:
            if w["queries"]:
                with st.expander(f"{w['label']} — {len(w['queries'])} queries", expanded=(w['wave']==1)):
                    wave_df = pd.DataFrame([
                        {"Query":q["query"],"Provider":q["provider"],
                         "Complexity":q["complexity"],"Score":q["score"],
                         "Transforms":q["t"],"DTPs":q["d"],"InfoPkgs":q["ip"]}
                        for q in w["queries"]
                    ])
                    st.dataframe(wave_df, use_container_width=True, hide_index=True)

        # Download wave plan
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf,"w",zipfile.ZIP_DEFLATED) as zf:
            for w in waves:
                if w["queries"]:
                    lines = [w["label"],"="*60]
                    for q in w["queries"]:
                        lines.append(f"{q['query']} | {q['provider']} | {q['complexity']} | Score:{q['score']}")
                    zf.writestr(f"wave_{w['wave']}.txt","\n".join(lines))
            if st.session_state.agent_wave_ai:
                zf.writestr("migration_narrative.txt",
                            f"MIGRATION WAVE PLAN NARRATIVE\n{'='*60}\n\n{st.session_state.agent_wave_ai}")
        zip_buf.seek(0)
        st.download_button("⬇️ Download Wave Plan (.zip)", data=zip_buf,
                           file_name="bw_wave_plan.zip", mime="application/zip")

# =====================================================
# MODE: 🔍 MONITORING
# =====================================================

elif mode == "🔍 Monitoring":
    st.markdown("#### 🔍 System Monitoring & Housekeeping")
    st.caption("Detect deprecated objects, dead metadata, deprecated DataSource types, and get a full housekeeping report.")

    if st.button("🔍 Run Monitoring Scan", type="primary", key="gen_monitor"):
        with st.spinner("🔍 Scanning system…"):
            ai_report, dead_by_type = agent_monitoring_report(dfs)
            dead_objects, active_count = find_dead_objects(dfs)
            st.session_state.agent_monitor = {
                "ai": ai_report,
                "dead_by_type": dead_by_type,
                "dead_objects": dead_objects,
                "active": active_count,
            }
        st.rerun()

    res = st.session_state.agent_monitor
    if res:
        dead_count = len(res["dead_objects"])
        total      = dead_count + res["active"]
        dead_pct   = round(dead_count/total*100) if total>0 else 0

        # Summary metrics
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("💀 Dead Objects",  dead_count)
        m2.metric("✅ Active Objects", res["active"])
        m3.metric("🗑️ Cleanup %",     f"{dead_pct}%")
        m4.metric("🔄 Types Found",   len(res["dead_by_type"]))
        st.markdown("")

        # AI Report
        ai_text = res["ai"]
        if ai_text.startswith("[ERROR"):
            st.error(ai_text)
        else:
            st.markdown("##### 🤖 AI Monitoring Report")
            st.markdown(
                f'<div style="background:#0d1117;border-left:4px solid #6f42c1;padding:14px 18px;'
                f'border-radius:6px;color:#c9d1d9;font-size:14px;line-height:1.7">{ai_text}</div>',
                unsafe_allow_html=True
            )

        # Dead objects by type
        st.markdown("##### 💀 Dead Objects by Type")
        grp = defaultdict(list)
        for d in res["dead_objects"]: grp[d["type"]].append(d["object"])

        for otype, objs in sorted(grp.items()):
            with st.expander(f"💀 {otype} — {len(objs)} objects"):
                for o in objs[:100]:
                    st.markdown(
                        f'<div style="background:#3d0a0a;border-left:3px solid #f85149;padding:4px 10px;'
                        f'border-radius:4px;font-size:12px;color:#ffa198;margin:2px 0;font-family:monospace">'
                        f'🗑️ {o}</div>',
                        unsafe_allow_html=True
                    )
                if len(objs)>100:
                    st.caption(f"… and {len(objs)-100} more in download")

        # Deprecated object checks
        st.markdown("##### ⚠️ Deprecated Object Checks")
        cube_df = dfs.get("cube_df")
        mp_df   = dfs.get("mp_df")
        ip_df   = dfs.get("ip_df")

        if cube_df is not None:
            cube_count = len(cube_df)
            st.markdown(
                f'<div class="status-warn">⚠️ <b>{cube_count} Classic InfoCubes</b> — '
                f'InfoCubes are deprecated in BW/4HANA. Each must be converted to an ADSO.</div>',
                unsafe_allow_html=True
            )
        if mp_df is not None:
            mp_count = len(mp_df["MULTIPROVIDER"].unique()) if "MULTIPROVIDER" in mp_df.columns else 0
            st.markdown(
                f'<div class="status-warn">⚠️ <b>{mp_count} MultiProviders</b> — '
                f'MultiProviders are deprecated in BW/4HANA. Must be replaced with CompositeProviders.</div>',
                unsafe_allow_html=True
            )
        if ip_df is not None and "OLTPSOURCE" in ip_df.columns:
            lis_ds = ip_df[ip_df["OLTPSOURCE"].str.upper().str.startswith("2LIS")]["OLTPSOURCE"].nunique()
            if lis_ds > 0:
                st.markdown(
                    f'<div class="status-err">🔴 <b>{lis_ds} LIS DataSources</b> (2LIS_*) — '
                    f'Logistics extraction via LIS is not supported in S/4HANA. '
                    f'Must migrate to CDS views or SAP Extractors.</div>',
                    unsafe_allow_html=True
                )

        st.markdown(
            f'<div class="status-ok">✅ OBJVERS = A filter applied — only active object versions analysed.</div>',
            unsafe_allow_html=True
        )

        # Download
        report_lines = [
            "BW SYSTEM MONITORING REPORT",
            "="*60,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Dead Objects: {dead_count} | Active: {res['active']} | Cleanup: {dead_pct}%",
            "",
            "DEAD OBJECTS BY TYPE:",
        ]
        for otype, objs in sorted(grp.items()):
            report_lines.append(f"\n{otype} ({len(objs)}):")
            for o in objs: report_lines.append(f"  {o}")
        report_lines += ["","AI REPORT:",ai_text]
        st.download_button("⬇️ Download Monitoring Report (.txt)",
                           data="\n".join(report_lines).encode(),
                           file_name="bw_monitoring_report.txt", mime="text/plain")

# =====================================================
# FOOTER
# =====================================================
st.markdown("---")
st.caption("BW System Agent · AI-powered · SAP BW/4HANA Migration Toolkit · Gyansys © 2026")