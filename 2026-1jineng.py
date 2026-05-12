import os
import time
from datetime import datetime
from typing import List, Tuple
import io
import base64
import pandas as pd
pd.set_option('io.excel.xlsx.reader', 'openpyxl')
pd.set_option('io.excel.xls.reader', 'xlrd')
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_echarts import st_echarts
import plotly.graph_objects as go

# -------------------- 页面配置 --------------------
st.set_page_config(
    page_title="技能覆盖分析大屏",
    layout="wide",
    page_icon="📊"
)

# -------------------- 样式 --------------------
PAGE_CSS = """
<style>
body, [data-testid="stAppViewContainer"]{
    background-color: #e6f7ff !important;
    color: #003366 !important;
}
[data-testid="stSidebar"]{
    background-color: #d1e7f5 !important;
    color: #003366 !important;
}
div.stButton>button{
    background-color: #4cc9f0 !important;
    color: #000 !important;
    border-radius:10px;
    height:40px;
    font-weight:700;
    margin:5px 0;
    width:100%;
}
div.stButton>button:hover{
    background-color:#4895ef !important;
    color:#fff !important;
}
.metric-card{
    background-color: #fff !important;
    padding:20px;
    border-radius:16px;
    text-align:center;
    box-shadow:0 0 15px rgba(0,0,0,0.08);
}
.metric-value{
    font-size:36px;
    font-weight:800;
    color: #0066cc !important;
}
.metric-label{
    font-size:14px;
    color: #336699 !important;
}
hr{
    border:none;
    border-top:1px solid #bbd9f7;
    margin:16px 0;
}
.heatmap-container {
    max-height: 700px;
    overflow-y: auto;
    overflow-x: auto;
    border-radius: 8px;
    background-color: #fff;
}
.heatmap-container::-webkit-scrollbar {width: 8px; height: 8px;}
.heatmap-container::-webkit-scrollbar-thumb {background:#99c2ff; border-radius:4px;}
.heatmap-container::-webkit-scrollbar-track {background:#e6f7ff;}
</style>
"""
st.markdown(PAGE_CSS, unsafe_allow_html=True)

# -------------------- GUIbit数据读取 --------------------
def load_data_from_gui():
    try:
        possible_paths = [
            "./guibit/jixiao.xlsx",
            "./jixiao.xlsx",
            "../guibit/jixiao.xlsx",
            "jixiao.xlsx",
        ]
        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                break
        if not file_path:
            st.sidebar.error("❌ 未找到jixiao.xlsx")
            for p in possible_paths:
                st.sidebar.info(f" • {p}")
            return [], {}, "文件不存在"
        
        st.sidebar.info(f"🔄 读取：{file_path}")
        xpd = pd.ExcelFile(file_path, engine='openpyxl')
        sheet_frames = {}
        for sheet_name in xpd.sheet_names:
            try:
                df = pd.read_excel(xpd, sheet_name=sheet_name, engine='openpyxl')
                if df.empty: continue
                required_cols = {"明细", "员工", "值"}
                if not required_cols.issubset(df.columns):
                    st.sidebar.warning(f"⚠️ {sheet_name} 缺少列，跳过")
                    continue
                if "数量总和" not in df.columns:
                    sum_df = df.groupby("明细", as_index=False)["值"].sum().rename(columns={"值":"数量总和"})
                    df = df.merge(sum_df, on="明细", how="left")
                sheet_frames[sheet_name] = df
                st.sidebar.success(f"✅ {sheet_name} ({len(df)}行)")
            except Exception as e:
                st.sidebar.error(f"⚠️ {sheet_name} 错误：{e}")
        if not sheet_frames:
            st.sidebar.error("❌ 无有效工作表")
            return [], {}, "无有效数据"
        return list(sheet_frames.keys()), sheet_frames, f"GUIbit({len(sheet_frames)}表)"
    except Exception as e:
        st.sidebar.error(f"❌ 读取失败：{e}")
        return [], {}, "读取失败"

# -------------------- Session --------------------
if 'sheet_frames' not in st.session_state:
    st.session_state.sheet_frames = {}
if 'sheets' not in st.session_state:
    st.session_state.sheets = []
if 'file_name' not in st.session_state:
    st.session_state.file_name = "未加载"
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

# -------------------- 自动加载 --------------------
if not st.session_state.data_loaded:
    with st.spinner("加载数据..."):
        sheets, sheet_frames, source = load_data_from_gui()
        if sheets:
            st.session_state.sheets = sheets
            st.session_state.sheet_frames = sheet_frames
            st.session_state.file_name = source
            st.session_state.data_loaded = True
            st.success(f"✅ 加载完成：{len(sheets)}个时间点")
        else:
            st.session_state.sheet_frames = {
                "示例_2025_01": pd.DataFrame({
                    "明细":["任务A","任务B","任务C","任务D"],
                    "数量总和":[3,2,5,4],
                    "员工":["张三","李四","王五","赵六"],
                    "值":[1,1,1,1], "分组":["A8","B7","VN","A8"]
                }),
                "示例_2025_02": pd.DataFrame({
                    "明细":["任务A","任务B","任务C","任务E"],
                    "数量总和":[4,3,2,5],
                    "员工":["张三","王五","赵六","钱七"],
                    "值":[1,1,1,1], "分组":["A8","VN","A8","B7"]
                })
            }
            st.session_state.sheets = ["示例_2025_01","示例_2025_02"]
            st.session_state.data_loaded = True
            st.warning("⚠️ 使用示例数据")

# -------------------- 下载 --------------------
def get_excel_download_link(dfs, fn="技能覆盖数据.xlsx"):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as w:
        for s, d in dfs.items():
            d.to_excel(w, sheet_name=s, index=False)
    out.seek(0)
    b64 = base64.b64encode(out.read()).decode()
    return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{fn}">📥 下载Excel</a>'

# -------------------- 侧边栏 --------------------
st.sidebar.markdown("### 📤 数据管理")
st.sidebar.markdown(f"**来源：** {st.session_state.file_name}")
st.sidebar.markdown(f"**时间点：** {len(st.session_state.sheets)}")

if st.sidebar.button("🔄 刷新数据", use_container_width=True):
    for k in ['sheet_frames','sheets','file_name','data_loaded']:
        if k in st.session_state: del st.session_state[k]
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📁 备用上传")
uf = st.sidebar.file_uploader("上传Excel", type=['xlsx','xls'])
if uf:
    try:
        eng = "openpyxl" if uf.name.endswith("xlsx") else "xlrd"
        xpd = pd.ExcelFile(uf, engine=eng)
        sf = {}
        for sn in xpd.sheet_names:
            d = pd.read_excel(xpd, sheet_name=sn, engine=eng)
            if d.empty: continue
            if not {"明细","员工","值"}.issubset(d.columns): continue
            if "数量总和" not in d.columns:
                s = d.groupby("明细", as_index=False)["值"].sum().rename(columns={"值":"数量总和"})
                d = d.merge(s, on="明细")
            sf[sn] = d
        if sf:
            st.session_state.sheets = list(sf.keys())
            st.session_state.sheet_frames = sf
            st.session_state.file_name = f"上传：{uf.name}"
            st.sidebar.success("✅ 上传成功")
            st.rerun()
    except Exception as e:
        st.sidebar.error(f"❌ 失败：{e}")

if st.session_state.sheet_frames:
    st.sidebar.markdown("---")
    st.sidebar.markdown(get_excel_download_link(
        st.session_state.sheet_frames,
        f"技能覆盖_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    ), unsafe_allow_html=True)

# -------------------- 新增时间点 --------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 📅 新增时间点")
cy = datetime.now().year
y = st.sidebar.selectbox("年份", list(range(cy-2,cy+2)), index=2)
m = st.sidebar.radio("类型", ["月份","季度"], horizontal=True)
if m=="月份":
    mon = st.sidebar.selectbox("月份", range(1,13))
    new_sheet = f"{y}_{mon:02d}"
else:
    q = st.sidebar.selectbox("季度", ["Q1","Q2","Q3","Q4"])
    new_sheet = f"{y}_{q}"

if st.sidebar.button("📝 创建"):
    if new_sheet in st.session_state.sheets:
        st.sidebar.error("已存在")
    else:
        pre = sorted([s for s in st.session_state.sheets if "_" in s and s < new_sheet])
        base = st.session_state.sheet_frames[pre[-1]].copy() if pre else pd.DataFrame(columns=["明细","数量总和","员工","值","分组"])
        st.session_state.sheet_frames[new_sheet] = base
        st.session_state.sheets.append(new_sheet)
        st.session_state.sheets.sort()
        st.sidebar.success(f"✅ {new_sheet}")
        st.rerun()

# -------------------- 删除 --------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 🗑️ 删除时间点")
if st.session_state.sheets:
    del_sel = st.sidebar.selectbox("选择", st.session_state.sheets)
    if len(st.session_state.sheets)==1:
        st.sidebar.warning("至少保留1个")
    else:
        if "del_cfm" not in st.session_state: st.session_state.del_cfm=False
        if not st.session_state.del_cfm:
            if st.sidebar.button("🗑️ 删除"): st.session_state.del_cfm=True
        else:
            st.sidebar.warning(f"确认删除 {del_sel}？")
            c1,c2=st.sidebar.columns(2)
            with c1:
                if st.button("✅ 确认"):
                    del st.session_state.sheet_frames[del_sel]
                    st.session_state.sheets.remove(del_sel)
                    st.session_state.del_cfm=False
                    st.rerun()
            with c2:
                if st.button("❌ 取消"): st.session_state.del_cfm=False

# -------------------- 数据修复 --------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔧 数据修复")
if st.sidebar.button("🧮 一键更新数量总和"):
    def fix(dfs):
        r={}
        for s,d in dfs.items():
            if "明细" in d.columns and "值" in d.columns:
                su=d.groupby("明细",as_index=False)["值"].sum().rename(columns={"值":"数量总和"})
                d=d.drop(columns=["数量总和"],errors="ignore")
                d=d.merge(su,on="明细")
            r[s]=d
        return r
    st.session_state.sheet_frames = fix(st.session_state.sheet_frames)
    st.sidebar.success("✅ 更新完成")
    st.rerun()

# -------------------- 筛选 --------------------
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 筛选")
ys = sorted({s.split("_")[0] for s in st.session_state.sheets if "_" in s})
yc = st.sidebar.selectbox("年份", ["全部年份"]+ys)
cand = sorted(st.session_state.sheets) if yc=="全部年份" else sorted([s for s in st.session_state.sheets if s.startswith(yc)])
time_choice = st.sidebar.multiselect("时间点", cand, default=cand[:2] if len(cand)>=2 else cand[:1])

# 分组
all_g=[]
for d in st.session_state.sheet_frames.values():
    if "分组" in d.columns:
        all_g.extend(d["分组"].dropna().unique())
all_g=sorted(list(set(all_g)))
sel_g=st.sidebar.multiselect("分组", all_g, default=all_g)

# 视图
st.sidebar.markdown("---")
st.sidebar.markdown("### 👁️ 视图")
views = ["编辑数据","大屏轮播","单页模式","显示所有视图","能力分析"]
view = st.sidebar.radio("切换", views)

# -------------------- 合并数据 --------------------
def merge(keys: List[str], groups: List[str]):
    arr=[]
    for k in keys:
        d=st.session_state.sheet_frames.get(k)
        if d is not None:
            if groups and "分组" in d.columns:
                d=d[d["分组"].isin(groups)]
            arr.append(d)
    if not arr: return pd.DataFrame()
    return pd.concat(arr, ignore_index=True)

df = merge(time_choice, sel_g)

# -------------------- 图表：完全不限制数量 + 过滤分数总和 --------------------
def chart_total(df0):
    df0 = df0[df0["明细"] != "分数总和"].copy()
    emp = df0.groupby("员工")["值"].sum().sort_values(ascending=False).reset_index()
    fig = go.Figure(go.Bar(x=emp["员工"], y=emp["值"], text=emp["值"], textposition="outside", marker_color="#3498db"))
    fig.update_layout(template="plotly_white", xaxis_title="员工", yaxis_title="完成值", height=600)
    return fig

def chart_stack(df0):
    df0 = df0[df0["明细"] != "分数总和"].copy()
    # 完全不限制任务数量
    df_pivot = df0.pivot_table(index="明细", columns="员工", values="值", aggfunc="sum", fill_value=0)
    fig = go.Figure()
    cs = ["#3498db","#2ecc71","#e74c3c","#f39c12","#9b59b6","#1abc9c","#34495e"]
    for i,e in enumerate(df_pivot.columns):
        fig.add_trace(go.Bar(x=df_pivot.index, y=df_pivot[e], name=e, marker_color=cs[i%len(cs)]))
    fig.update_layout(barmode="stack", template="plotly_white", xaxis_title="任务", yaxis_title="完成值", height=600)
    return fig

def chart_heat(df0):
    df0 = df0[df0["明细"] != "分数总和"].copy()
    # 完全不限制任务、员工数量
    tasks = df0["明细"].unique().tolist()
    emps = df0["员工"].unique().tolist()
    data = []
    for i,t in enumerate(tasks):
        for j,e in enumerate(emps):
            v = int(df0[(df0["明细"]==t) & (df0["员工"]==e)]["值"].sum())
            data.append([j,i,v])
    return {
        "backgroundColor":"white",
        "tooltip":{"position":"top"},
        "grid":{"left":"10%","right":"5%","bottom":"15%","top":"10%"},
        "xAxis":{"type":"category","data":emps,"axisLabel":{"rotate":45}},
        "yAxis":{"type":"category","data":tasks},
        "visualMap":{"min":0,"max":max([d[2] for d in data]) if data else 1,"inRange":{"color":["#ecf0f1","#3498db","#2980b9"]}},
        "series":[{"type":"heatmap","data":data,"itemStyle":{"borderColor":"#fff","borderWidth":1}}]
    }

# -------------------- 指标卡片 --------------------
def show_cards(df0):
    df0 = df0[df0["明细"] != "分数总和"].copy()
    if df0.empty: return
    t_task = df0["明细"].nunique()
    t_emp = df0["员工"].nunique()
    s = df0.groupby("员工")["值"].sum()
    top = s.idxmax() if not s.empty else ""
    avg = round(s.mean(),1) if not s.empty else 0
    total_v = int(df0["值"].sum())
    c1,c2,c3,c4,c5=st.columns(5)
    c1.markdown(f"<div class='metric-card'><div class='metric-value'>{t_task}</div><div class='metric-label'>📋 任务总数</div></div>",unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><div class='metric-value'>{t_emp}</div><div class='metric-label'>👥 参与人数</div></div>",unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><div class='metric-value'>{total_v}</div><div class='metric-label'>🎯 总完成值</div></div>",unsafe_allow_html=True)
    c4.markdown(f"<div class='metric-card'><div class='metric-value'>{top[:8]}{'...' if len(top)>8 else ''}</div><div class='metric-label'>🏆 最佳贡献者</div></div>",unsafe_allow_html=True)
    c5.markdown(f"<div class='metric-card'><div class='metric-value'>{avg}</div><div class='metric-label'>📈 人均完成值</div></div>",unsafe_allow_html=True)
    st.markdown("<hr/>",unsafe_allow_html=True)

# -------------------- 主界面 --------------------
st.markdown("# 📊 技能覆盖分析大屏")

# 编辑
if view == "编辑数据":
    if not time_choice:
        st.warning("请选时间点")
    elif len(time_choice)>1:
        st.warning("仅支持单选编辑")
    else:
        show_cards(df)
        st.info("📝 直接编辑表格后保存")
        sheet = time_choice[0]
        ori = st.session_state.sheet_frames[sheet].copy()
        ed = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        c1,c2=st.columns(2)
        with c1:
            if st.button("💾 保存", use_container_width=True):
                if sel_g and "分组" in ori.columns:
                    ori = ori[~ori["分组"].isin(sel_g)].reset_index(drop=True)
                    final = pd.concat([ori, ed], ignore_index=True)
                else:
                    final = ed.copy()
                if "明细" in final and "值" in final:
                    su = final.groupby("明细",as_index=False)["值"].sum().rename(columns={"值":"数量总和"})
                    final = final.drop(columns=["数量总和"],errors="ignore")
                    final = final.merge(su,on="明细")
                st.session_state.sheet_frames[sheet] = final
                st.success("✅ 已保存")
                st.rerun()
        with c2:
            if st.button("🔄 重置", use_container_width=True):
                st.rerun()

# 轮播
elif view == "大屏轮播":
    if not time_choice: st.warning("请选时间点")
    else:
        st_autorefresh(interval=10000, key="aut")
        show_cards(df)
        parts = [("排名",chart_total(df)),("堆叠对比",chart_stack(df)),("热力图",chart_heat(df))]
        title, obj = parts[int(time.time()//10) % len(parts)]
        st.subheader(f"📈 {title}")
        if isinstance(obj, go.Figure):
            st.plotly_chart(obj, use_container_width=True)
        else:
            st.markdown('<div class="heatmap-container">',unsafe_allow_html=True)
            st_echarts(obj, height=600)
            st.markdown('</div>',unsafe_allow_html=True)

# 单页
elif view == "单页模式":
    if not time_choice: st.warning("请选时间点")
    else:
        show_cards(df)
        sel_view = st.sidebar.selectbox("查看", ["人员完成任务数量排名","任务对比（堆叠柱状图）","任务-人员热力图"])
        st.subheader(f"📊 {sel_view}")
        if sel_view == "人员完成任务数量排名":
            st.plotly_chart(chart_total(df), use_container_width=True)
        elif sel_view == "任务对比（堆叠柱状图）":
            st.plotly_chart(chart_stack(df), use_container_width=True)
        elif sel_view == "任务-人员热力图":
            st.markdown('<div class="heatmap-container">',unsafe_allow_html=True)
            st_echarts(chart_heat(df), height=600)
            st.markdown('</div>',unsafe_allow_html=True)

# 全部视图
elif view == "显示所有视图":
    if not time_choice: st.warning("请选时间点")
    else:
        show_cards(df)
        st.subheader("📊 人员完成任务数量排名")
        st.plotly_chart(chart_total(df), use_container_width=True)
        st.subheader("📊 任务对比（堆叠柱状图）")
        st.plotly_chart(chart_stack(df), use_container_width=True)
        st.subheader("📊 任务-人员热力图")
        st.markdown('<div class="heatmap-container">',unsafe_allow_html=True)
        st_echarts(chart_heat(df), height=600)
        st.markdown('</div>',unsafe_allow_html=True)

# 能力分析
elif view == "能力分析":
    if not time_choice: st.warning("请选时间点")
    else:
        show_cards(df)
        st.subheader("📈 能力分析")
        emps = df["员工"].unique().tolist()
        sel_emp = st.sidebar.multiselect("选择员工", emps, default=emps[:min(5, len(emps))])
        tasks = df["明细"].unique().tolist()
        f1,f2,f3 = go.Figure(), go.Figure(), go.Figure()
        colors = ["#3498db","#2ecc71","#e74c3c","#f39c12","#9b59b6","#1abc9c"]
        for i,s in enumerate(time_choice):
            d = merge([s], sel_g)
            d = d[d["明细"]!="分数总和"]
            if d.empty: continue
            p = d.pivot(index="明细", columns="员工", values="值").fillna(0)
            for e in sel_emp:
                if e in p.columns:
                    f1.add_trace(go.Scatter(x=tasks, y=p[e].reindex(tasks, fill_value=0),
                                           mode="lines+markers", name=f"{s}-{e}", line=dict(width=2.5)))
            f2.add_trace(go.Scatter(x=tasks, y=p.sum(axis=1).reindex(tasks, fill_value=0),
                                   mode="lines+markers", name=s, line=dict(width=2.5)))
            f3.add_trace(go.Bar(x=p.columns, y=p.sum(axis=0), name=s, width=0.25))
        f1.update_layout(title="员工任务完成", template="plotly_white", height=600)
        f2.update_layout(title="任务整体趋势", template="plotly_white", height=600)
        f3.update_layout(title="员工对比", barmode="group", template="plotly_white", height=600)
        st.plotly_chart(f1, use_container_width=True)
        st.plotly_chart(f2, use_container_width=True)
        st.plotly_chart(f3, use_container_width=True)
