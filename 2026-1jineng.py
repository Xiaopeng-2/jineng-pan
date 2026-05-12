import os
import time
from datetime import datetime
from typing import List
import io
import base64

# 先设置pandas配置
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
    color: #000000 !important;
    border-radius:10px;
    height:40px;
    font-weight:700;
    margin:5px 0;
    width:100%;
}
div.stButton>button:hover{
    background-color:#4895ef !important;
    color:#ffffff !important;
}
.metric-card{
    background-color: #ffffff !important;
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
    background-color: #ffffff;
}
.heatmap-container::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
.heatmap-container::-webkit-scrollbar-thumb {
    background-color: #99c2ff;
    border-radius: 4px;
}
.heatmap-container::-webkit-scrollbar-track {
    background-color: #e6f7ff;
}
</style>
"""
st.markdown(PAGE_CSS, unsafe_allow_html=True)

# -------------------- 读取Excel --------------------
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
            st.sidebar.error("❌ 未找到jixiao.xlsx文件")
            return [], {}, "文件不存在"
        st.sidebar.info(f"🔄 正在读取: {file_path}")
        xpd = pd.ExcelFile(file_path, engine='openpyxl')
        sheet_frames = {}
        for sheet_name in xpd.sheet_names:
            try:
                df = pd.read_excel(xpd, sheet_name=sheet_name, engine='openpyxl')
                if df.empty:
                    continue
                required_cols = {"明细", "员工", "值"}
                if not required_cols.issubset(set(df.columns)):
                    continue
                # 全局过滤分数总和
                df = df[df["明细"] != "分数总和"]
                sheet_frames[sheet_name] = df
            except:
                continue
        if not sheet_frames:
            return [], {}, "无有效数据"
        sheets = list(sheet_frames.keys())
        return sheets, sheet_frames, f"数据({len(sheets)}个表)"
    except:
        return [], {}, "读取失败"

# -------------------- 初始化 --------------------
if 'sheet_frames' not in st.session_state:
    st.session_state.sheet_frames = {}
if 'sheets' not in st.session_state:
    st.session_state.sheets = []
if 'file_name' not in st.session_state:
    st.session_state.file_name = "未加载"
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

if not st.session_state.data_loaded:
    sheets, sheet_frames, source_name = load_data_from_gui()
    if sheets:
        st.session_state.sheets = sheets
        st.session_state.sheet_frames = sheet_frames
        st.session_state.file_name = source_name
        st.session_state.data_loaded = True
    else:
        st.session_state.sheet_frames = {
            "示例_2025_01": pd.DataFrame({
                "明细": ["任务A", "任务B", "任务C", "任务D"],
                "员工": ["张三", "李四", "王五", "赵六"],
                "值": [1, 1, 1, 1],
                "分组": ["A8", "B7", "VN", "A8"]
            }),
            "示例_2025_02": pd.DataFrame({
                "明细": ["任务A", "任务B", "任务C", "任务E"],
                "员工": ["张三", "王五", "赵六", "钱七"],
                "值": [1, 1, 1, 1],
                "分组": ["A8", "VN", "A8", "B7"]
            })
        }
        st.session_state.sheets = ["示例_2025_01", "示例_2025_02"]
        st.session_state.data_loaded = True

# -------------------- 下载链接 --------------------
def get_excel_download_link(dataframes, filename="数据.xlsx"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dataframes.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    b64 = base64.b64encode(output.read()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">📥 下载Excel</a>'
    return href

# -------------------- 侧边栏 --------------------
st.sidebar.markdown("📤 数据管理")
st.sidebar.markdown(f"来源: {st.session_state.file_name}")
st.sidebar.markdown(f"时间点: {len(st.session_state.sheets)}")

if st.sidebar.button("🔄 刷新数据", use_container_width=True):
    for k in ['sheet_frames','sheets','file_name','data_loaded']:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()

st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("上传Excel备用", type=['xlsx','xls'])
if uploaded_file is not None:
    try:
        engine = "openpyxl" if uploaded_file.name.endswith('.xlsx') else "xlrd"
        xpd = pd.ExcelFile(uploaded_file, engine=engine)
        sheet_frames = {}
        for sheet_name in xpd.sheet_names:
            df = pd.read_excel(xpd, sheet_name=sheet_name, engine=engine)
            if df.empty:
                continue
            if not {"明细","员工","值"}.issubset(df.columns):
                continue
            df = df[df["明细"] != "分数总和"]
            sheet_frames[sheet_name] = df
        if sheet_frames:
            st.session_state.sheets = list(sheet_frames.keys())
            st.session_state.sheet_frames = sheet_frames
            st.session_state.file_name = f"上传:{uploaded_file.name}"
            st.rerun()
    except:
        pass

if st.session_state.sheet_frames:
    st.sidebar.markdown("---")
    st.sidebar.markdown(get_excel_download_link(
        st.session_state.sheet_frames,
        f"数据_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    ), unsafe_allow_html=True)

# 新增时间点
st.sidebar.markdown("---")
st.sidebar.markdown("📅 新增时间点")
current_year = datetime.now().year
year = st.sidebar.selectbox("年份", list(range(current_year-2, current_year+2)), index=2)
mode = st.sidebar.radio("类型", ["月份","季度"], horizontal=True)
new_sheet_name = f"{year}_{st.sidebar.selectbox("月份",range(1,13)):02d}" if mode=="月份" else f"{year}_{st.sidebar.selectbox("季度",['Q1','Q2','Q3','Q4'])}"

if st.sidebar.button("📝 创建时间点"):
    if new_sheet_name in st.session_state.sheets:
        st.sidebar.error("已存在")
    else:
        prev_sheets = sorted([s for s in st.session_state.sheets if "_" in s and s < new_sheet_name])
        base_df = st.session_state.sheet_frames.get(prev_sheets[-1], pd.DataFrame(columns=["明细","员工","值","分组"])).copy() if prev_sheets else pd.DataFrame(columns=["明细","员工","值","分组"])
        base_df = base_df[base_df["明细"] != "分数总和"]
        st.session_state.sheet_frames[new_sheet_name] = base_df
        st.session_state.sheets.append(new_sheet_name)
        st.session_state.sheets.sort()
        st.rerun()

# 删除时间点
st.sidebar.markdown("---")
st.sidebar.markdown("🗑️ 删除时间点")
if st.session_state.sheets:
    sheet_to_delete = st.sidebar.selectbox("选择删除", st.session_state.sheets)
    if len(st.session_state.sheets) > 1:
        if "del_conf" not in st.session_state:
            st.session_state.del_conf = False
        if not st.session_state.del_conf:
            if st.sidebar.button("删除选中"):
                st.session_state.del_conf = True
        else:
            st.sidebar.warning("确认删除？")
            c1,c2 = st.sidebar.columns(2)
            with c1:
                if st.button("确认"):
                    del st.session_state.sheet_frames[sheet_to_delete]
                    st.session_state.sheets.remove(sheet_to_delete)
                    st.session_state.del_conf = False
                    st.rerun()
            with c2:
                if st.button("取消"):
                    st.session_state.del_conf = False

# 筛选
st.sidebar.markdown("---")
st.sidebar.markdown("🔍 筛选")
years_available = sorted({s.split("_")[0] for s in st.session_state.sheets if "_" in s})
year_choice = st.sidebar.selectbox("筛选年份", ["全部年份"]+years_available)
time_candidates = sorted(st.session_state.sheets) if year_choice=="全部年份" else sorted([s for s in st.session_state.sheets if s.startswith(year_choice)])
time_choice = st.sidebar.multiselect("选择时间点", time_candidates, default=time_candidates[:2] if len(time_candidates)>=2 else time_candidates)

# 分组
all_groups = []
for df in st.session_state.sheet_frames.values():
    if "分组" in df.columns:
        all_groups.extend(df["分组"].dropna().unique())
all_groups = list(set(all_groups))
selected_groups = st.sidebar.multiselect("选择分组", all_groups, default=all_groups)

# 视图
sections_names = ["人员完成任务数量排名","任务对比（堆叠柱状图）","任务-人员热力图"]
view = st.sidebar.radio("视图选择", ["编辑数据","大屏轮播","单页模式","显示所有视图","能力分析"])

# -------------------- 合并数据 全局过滤分数总和 --------------------
def get_merged_df(keys: List[str], groups: List[str]) -> pd.DataFrame:
    dfs = []
    for k in keys:
        df0 = st.session_state.sheet_frames.get(k)
        if df0 is not None:
            if groups and "分组" in df0.columns:
                df0 = df0[df0["分组"].isin(groups)]
            dfs.append(df0)
    if not dfs:
        return pd.DataFrame()
    merged_df = pd.concat(dfs, axis=0, ignore_index=True)
    # 永久过滤
    merged_df = merged_df[merged_df["明细"] != "分数总和"]
    return merged_df

df = get_merged_df(time_choice, selected_groups)

# -------------------- 图表函数 全部不限制任务数量 --------------------
def chart_total(df0):
    emp_stats = df0.groupby("员工")["值"].sum().sort_values(ascending=False).reset_index()
    fig = go.Figure(go.Bar(
        x=emp_stats["员工"], y=emp_stats["值"], text=emp_stats["值"],
        textposition="outside", marker_color='#3498db'
    ))
    fig.update_layout(height=600, template="plotly_white", xaxis_title="员工", yaxis_title="完成总值")
    return fig

def chart_stack(df0):
    # 取消50个任务限制，全部显示
    df_pivot = df0.pivot_table(index="明细", columns="员工", values="值", aggfunc="sum", fill_value=0)
    fig = go.Figure()
    colors = ['#3498db','#2ecc71','#e74c3c','#f39c12','#9b59b6','#1abc9c','#34495e']
    for idx, emp in enumerate(df_pivot.columns):
        fig.add_trace(go.Bar(x=df_pivot.index, y=df_pivot[emp], name=emp, marker_color=colors[idx%len(colors)]))
    fig.update_layout(barmode="stack", height=600, template="plotly_white", xaxis_title="任务", yaxis_title="完成值")
    return fig

def chart_heat(df0):
    # 取消30个任务限制，全部任务、全部员工都显示
    tasks = df0["明细"].unique().tolist()
    emps = df0["员工"].unique().tolist()
    data = []
    for i, t in enumerate(tasks):
        for j, e in enumerate(emps):
            v = int(df0[(df0["明细"]==t)&(df0["员工"]==e)]["值"].sum())
            data.append([j, i, v])
    return {
        "backgroundColor":"white",
        "tooltip":{"position":"top"},
        "grid":{"left":"10%","right":"5%","bottom":"15%","top":"10%"},
        "xAxis":{"type":"category","data":emps,"axisLabel":{"rotate":45}},
        "yAxis":{"type":"category","data":tasks},
        "visualMap":{"min":0,"max":max([d[2] for d in data]) if data else 1,"inRange":["#ecf0f1","#3498db","#2980b9"]},
        "series":[{"type":"heatmap","data":data,"itemStyle":{"borderColor":"#fff"}}]
    }

# -------------------- 指标卡片 --------------------
def show_cards(df0):
    if df0.empty:
        return
    total_tasks = df0["明细"].nunique()
    total_people = df0["员工"].nunique()
    ps = df0.groupby("员工")["值"].sum()
    top_person = ps.idxmax() if not ps.empty else ""
    avg_score = round(ps.mean(),1) if not ps.empty else 0
    total_value = int(df0["值"].sum())
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.markdown(f"<div class='metric-card'><div class='metric-value'>{total_tasks}</div><div class='metric-label'>任务总数</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><div class='metric-value'>{total_people}</div><div class='metric-label'>参与人数</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><div class='metric-value'>{total_value}</div><div class='metric-label'>总完成值</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='metric-card'><div class='metric-value'>{top_person[:8]}{'...' if len(top_person)>8 else ''}</div><div class='metric-label'>最佳贡献者</div></div>", unsafe_allow_html=True)
    c5.markdown(f"<div class='metric-card'><div class='metric-value'>{avg_score}</div><div class='metric-label'>人均完成值</div></div>", unsafe_allow_html=True)
    st.markdown("<hr/>", unsafe_allow_html=True)

BRIGHT_COLORS = ["#3498db","#2ecc71","#e74c3c","#f39c12","#9b59b6","#1abc9c","#d35400","#34495e"]

# -------------------- 主视图渲染 --------------------
st.markdown("<h1>📊 技能覆盖分析大屏</h1>", unsafe_allow_html=True)

if view == "编辑数据":
    if not time_choice:
        st.warning("请先选择时间点")
    elif len(time_choice)>1:
        st.warning("编辑仅支持单个时间点")
    else:
        show_cards(df)
        sheet_name = time_choice[0]
        original_df = st.session_state.sheet_frames[sheet_name].copy()
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
        col1,col2 = st.columns(2)
        with col1:
            if st.button("💾 保存修改", use_container_width=True):
                edited_df = edited_df[edited_df["明细"] != "分数总和"]
                if selected_groups and "分组" in original_df.columns:
                    original_df = original_df[~original_df["分组"].isin(selected_groups)].reset_index(drop=True)
                    final_df = pd.concat([original_df, edited_df], ignore_index=True)
                else:
                    final_df = edited_df.copy()
                st.session_state.sheet_frames[sheet_name] = final_df
                st.success("保存成功")
                st.rerun()
        with col2:
            if st.button("🔄 重置", use_container_width=True):
                st.rerun()

elif view == "大屏轮播":
    if not time_choice:
        st.warning("请选择时间点")
    else:
        st_autorefresh(interval=10000, key="aut")
        show_cards(df)
        secs = [("人员排名",chart_total(df)),("任务对比",chart_stack(df)),("热力图",chart_heat(df))]
        t,op = secs[int(time.time()/10)%len(secs)]
        st.subheader(f"📈 {t}")
        if isinstance(op, go.Figure):
            st.plotly_chart(op, use_container_width=True)
        else:
            st.markdown('<div class="heatmap-container">', unsafe_allow_html=True)
            st_echarts(op, height="600px")
            st.markdown('</div>', unsafe_allow_html=True)

elif view == "单页模式":
    if not time_choice:
        st.warning("请选择时间点")
    else:
        show_cards(df)
        choice = st.sidebar.selectbox("单页查看", sections_names)
        mapping = {
            "人员完成任务数量排名":chart_total(df),
            "任务对比（堆叠柱状图）":chart_stack(df),
            "任务-人员热力图":chart_heat(df)
        }
        op = mapping[choice]
        st.subheader(f"📊 {choice}")
        if isinstance(op, go.Figure):
            st.plotly_chart(op, use_container_width=True)
        else:
            st.markdown('<div class="heatmap-container">', unsafe_allow_html=True)
            st_echarts(op, height="600px")
            st.markdown('</div>', unsafe_allow_html=True)

elif view == "显示所有视图":
    if not time_choice:
        st.warning("请选择时间点")
    else:
        show_cards(df)
        st.subheader("人员完成任务数量排名")
        st.plotly_chart(chart_total(df), use_container_width=True)
        st.subheader("任务对比（堆叠柱状图）")
        st.plotly_chart(chart_stack(df), use_container_width=True)
        st.subheader("任务-人员热力图")
        st.markdown('<div class="heatmap-container">', unsafe_allow_html=True)
        st_echarts(chart_heat(df), height="600px")
        st.markdown('</div>', unsafe_allow_html=True)

elif view == "能力分析":
    if not time_choice:
        st.warning("请选择时间点")
    else:
        show_cards(df)
        st.subheader("📈 能力分析")
        employees = df["员工"].unique().tolist()
        selected_emps = st.sidebar.multiselect("选择员工", employees, default=employees[:5])
        tasks = df["明细"].unique().tolist()

        fig1,fig2,fig3 = go.Figure(),go.Figure(),go.Figure()
        sheet_color_map = {s:BRIGHT_COLORS[i%len(BRIGHT_COLORS)] for i,s in enumerate(time_choice)}
        emp_color_idx = 0

        for sheet in time_choice:
            df_sheet = get_merged_df([sheet], selected_groups)
            df_pivot = df_sheet.pivot(index="明细", columns="员工", values="值").fillna(0)
            for emp in selected_emps:
                if emp in df_pivot.columns:
                    fig1.add_trace(go.Scatter(
                        x=tasks, y=df_pivot[emp].reindex(tasks,fill_value=0),
                        mode="lines+markers", name=f"{sheet}-{emp}",
                        line=dict(color=BRIGHT_COLORS[emp_color_idx%len(BRIGHT_COLORS)])
                    ))
                    emp_color_idx += 1
            fig2.add_trace(go.Scatter(
                x=tasks, y=df_pivot.sum(axis=1).reindex(tasks,fill_value=0),
                mode="lines+markers", name=sheet, line=dict(color=sheet_color_map[sheet])
            ))
            fig3.add_trace(go.Bar(x=df_pivot.columns, y=df_pivot.sum(axis=0), name=sheet, marker_color=sheet_color_map[sheet]))

        for fig in [fig1,fig2,fig3]:
            fig.update_layout(height=600, template="plotly_white", legend=dict(orientation="h",y=-0.3))
        fig3.update_layout(barmode="group")
        st.plotly_chart(fig1, use_container_width=True)
        st.plotly_chart(fig2, use_container_width=True)
        st.plotly_chart(fig3, use_container_width=True)
