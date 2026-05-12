import os
from datetime import datetime
from typing import List
import io
import base64

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_echarts import st_echarts
import plotly.graph_objects as go

# ===================== 页面配置 =====================
st.set_page_config(
    page_title="技能覆盖分析大屏",
    layout="wide",
    page_icon="📊"
)

# ===================== 样式 =====================
CSS = """
<style>
.heatmap-container {
    width: 100%;
    height: 700px;
    overflow: auto;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ===================== 读取数据 =====================
def load_excel_data():
    paths = ["./jixiao.xlsx", "jixiao.xlsx"]
    file_path = None
    for p in paths:
        if os.path.exists(p):
            file_path = p
            break
    if not file_path:
        return {}
    try:
        xl = pd.ExcelFile(file_path)
        sheets_dict = {}
        for name in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name=name)
            if {"明细", "员工", "值"}.issubset(df.columns):
                # 过滤分数总和
                df = df[df["明细"] != "分数总和"]
                sheets_dict[name] = df
        return sheets_dict
    except:
        return {}

# ===================== 初始化缓存 =====================
if "data_dict" not in st.session_state:
    st.session_state.data_dict = load_excel_data()
if "sel_time" not in st.session_state:
    st.session_state.sel_time = []
if "sel_group" not in st.session_state:
    st.session_state.sel_group = []

data_dict = st.session_state.data_dict
sheet_list = list(data_dict.keys()) if data_dict else []

# ===================== 侧边栏筛选 =====================
st.sidebar.title("筛选设置")

# 时间点选择
if sheet_list:
    st.session_state.sel_time = st.sidebar.multiselect(
        "选择时间点", sheet_list, default=sheet_list[:1]
    )
else:
    st.warning("未找到 jixiao.xlsx 有效数据")
    st.stop()

# 分组选择
all_group = []
for d in data_dict.values():
    if "分组" in d.columns:
        all_group.extend(d["分组"].dropna().unique())
all_group = list(set(all_group))
st.session_state.sel_group = st.sidebar.multiselect(
    "选择分组", all_group, default=all_group
)

# 视图选择
view_type = st.sidebar.radio(
    "选择视图",
    ["人员排名", "任务对比柱状图", "任务人员热力图"]
)

# ===================== 合并筛选后数据 =====================
def merge_data(time_list: List[str], group_list: List[str]) -> pd.DataFrame:
    dfs = []
    for t in time_list:
        df = data_dict.get(t, pd.DataFrame())
        if df.empty:
            continue
        if group_list and "分组" in df.columns:
            df = df[df["分组"].isin(group_list)]
        dfs.append(df)
    if not dfs:
        return pd.DataFrame()
    res = pd.concat(dfs, ignore_index=True)
    res = res[res["明细"] != "分数总和"]
    return res

df = merge_data(st.session_state.sel_time, st.session_state.sel_group)

if df.empty:
    st.info("当前筛选无数据")
    st.stop()

# ===================== 1. 人员排名柱状图 =====================
def plot_user_rank(data):
    gp = data.groupby("员工")["值"].sum().sort_values(ascending=False).reset_index()
    fig = go.Figure(go.Bar(
        x=gp["员工"],
        y=gp["值"],
        text=gp["值"],
        textposition="outside"
    ))
    fig.update_layout(height=600, title="员工任务完成排名")
    return fig

# ===================== 2. 任务对比堆叠柱状图（无数量限制） =====================
def plot_task_stack(data):
    pv = data.pivot_table(
        index="明细",
        columns="员工",
        values="值",
        aggfunc="sum",
        fill_value=0
    )
    fig = go.Figure()
    colors = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd"]
    for i, col in enumerate(pv.columns):
        fig.add_trace(go.Bar(
            x=pv.index,
            y=pv[col],
            name=col,
            marker_color=colors[i % len(colors)]
        ))
    fig.update_layout(barmode="stack", height=600, title="任务人员分布对比")
    return fig

# ===================== 3. 热力图（全部任务+全部员工，无限制） =====================
def plot_heatmap(data):
    tasks = data["明细"].unique().tolist()
    users = data["员工"].unique().tolist()
    data_list = []
    for y, task in enumerate(tasks):
        for x, user in enumerate(users):
            val = data[(data["明细"]==task) & (data["员工"]==user)]["值"].sum()
            data_list.append([x, y, int(val)])
    opt = {
        "tooltip": {"position": "top"},
        "xAxis": {"type": "category", "data": users, "axisLabel": {"rotate": 45}},
        "yAxis": {"type": "category", "data": tasks},
        "visualMap": {"min": 0, "max": max([d[2] for d in data_list]) if data_list else 5},
        "series": [{
            "type": "heatmap",
            "data": data_list,
            "itemStyle": {"borderColor": "#fff", "borderWidth": 1}
        }]
    }
    return opt

# ===================== 主页面渲染 =====================
st.title("📊 技能覆盖分析大屏")

if view_type == "人员排名":
    st.plotly_chart(plot_user_rank(df), use_container_width=True)

elif view_type == "任务对比柱状图":
    st.plotly_chart(plot_task_stack(df), use_container_width=True)

elif view_type == "任务人员热力图":
    opt = plot_heatmap(df)
    st.markdown("<div class='heatmap-container'>", unsafe_allow_html=True)
    st_echarts(opt, height="700px")
    st.markdown("</div>", unsafe_allow_html=True)
