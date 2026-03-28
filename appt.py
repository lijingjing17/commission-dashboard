import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np

# -------------------------- 页面配置 --------------------------
st.set_page_config(
    page_title="商户抽佣经营看板-剔除拼团/超客配",
    layout="wide",
    page_icon="📊"
)
st.title("📊 商户抽佣经营综合看板-剔除拼团/超客配")
st.divider()

# -------------------------- 数据加载（同时读取两个工作表） --------------------------
import os

# -------------------------- 默认文件路径配置 --------------------------
# 默认文件路径（相对路径，与脚本同目录）
DEFAULT_FILE = "抽佣看板（剔除拼团，超客配)2.xlsx"

# -------------------------- 数据加载（优先默认文件，再用户上传） --------------------------
@st.cache_data
def load_all_data(uploaded_file=None):
    """
    加载汇总表和商户明细表
    优先级：用户上传 > 默认文件
    """
    if uploaded_file is not None:
        # 用户已上传，直接读取
        sheets = pd.read_excel(uploaded_file, sheet_name=['汇总', '商户明细'])
        return sheets['汇总'], sheets['商户明细']
    
    # 尝试读取默认文件
    if os.path.exists(DEFAULT_FILE):
        try:
            sheets = pd.read_excel(DEFAULT_FILE, sheet_name=['汇总', '商户明细'])
            st.success(f"已加载默认文件：{DEFAULT_FILE}")
            return sheets['汇总'], sheets['商户明细']
        except Exception as e:
            st.error(f"读取默认文件失败：{e}")
            return None, None
    else:
        st.warning(f"默认文件不存在：{DEFAULT_FILE}")
        return None, None

# 文件上传组件（保留，允许用户覆盖）
uploaded_file = st.file_uploader(
    "上传 Excel 文件（需包含「汇总」和「商户明细」工作表）",
    type=["xlsx", "xls"],
    help="若不上传，将自动尝试读取指定路径的默认文件"
)

df_summary, df_merchant = load_all_data(uploaded_file)

if df_summary is None or df_merchant is None:
    st.error("未找到默认文件，且未上传有效文件。请上传包含「汇总」和「商户明细」工作表的 Excel 文件。")
    st.stop()
# -------------------------- 汇总表预处理 --------------------------
required_summary_cols = ["区县名称", "业务线", "毛交易额", "抽佣x+y总计", "商户抽佣基数", "业务类型计数"]
missing_summary = [col for col in required_summary_cols if col not in df_summary.columns]
if missing_summary:
    st.error(f"汇总表缺少必要字段：{', '.join(missing_summary)}")
    st.stop()

# 计算抽佣比率(%)（整体比率，基于汇总数据）
df_summary["抽佣比率(%)"] = (df_summary["抽佣x+y总计"] / df_summary["商户抽佣基数"] * 100).round(2)
# 计算单均抽佣
df_summary['单均抽佣'] = df_summary["抽佣x+y总计"] / df_summary["业务类型计数"]
# 处理空值
df_summary = df_summary.dropna(subset=required_summary_cols)

# -------------------------- 商户明细表预处理 --------------------------
required_merchant_cols = ["区县名称", "业务线", "商户ID", "商户名称", "抽佣x+y总计", "商户抽佣基数", "抽佣比率"]
missing_merchant = [col for col in required_merchant_cols if col not in df_merchant.columns]
if missing_merchant:
    st.error(f"商户明细表缺少必要字段：{', '.join(missing_merchant)}")
    st.stop()

# 清洗数据
df_merchant["抽佣比率"] = df_merchant["抽佣比率"].fillna(df_merchant["抽佣x+y总计"] / df_merchant["商户抽佣基数"])
df_merchant = df_merchant[df_merchant["商户抽佣基数"] > 0].copy()
df_merchant["抽佣比率(%)"] = (df_merchant["抽佣比率"] * 100).round(2)

# ======================== 模块1：核心总计数据（基于汇总表） ========================
st.subheader("一、核心总计数据")
total_transaction = df_summary["毛交易额"].sum()
total_orders = df_summary['业务类型计数'].sum()
total_commission = df_summary["抽佣x+y总计"].sum()
avg_commission_rate = (total_commission / df_summary["商户抽佣基数"].sum() * 100).round(2)
avg_order_commission = (total_commission / total_orders).round(2)

col1, col2, col3, col4, col5 = st.columns(5, gap="large")
with col1:
    st.metric("总订单量", f"{total_orders:,} 笔")
with col2:
    st.metric("总交易额", f"¥{total_transaction:,.2f}")
with col3:
    st.metric("总抽佣x+y总计", f"¥{total_commission:,.2f}")
with col4:
    st.metric("平均抽佣比率", f"{avg_commission_rate:.2f}%")
with col5:
    st.metric("单均抽佣", f"¥{avg_order_commission:.2f}")

# ======================== 模块2：核心数据洞察（基于汇总表） ========================
st.subheader("二、核心数据洞察分析")
with st.expander("展开查看详细洞察", expanded=True):
    # 洞察1：交易额TOP3区县
    top3_cities = df_summary.groupby("区县名称")["毛交易额"].sum().nlargest(3).index.tolist()
    top3_amount = df_summary[df_summary['区县名称'].isin(top3_cities)]['毛交易额'].sum()
    st.write(f"1. **交易额TOP3区县名称**：{', '.join(top3_cities)}，合计贡献{top3_amount/total_transaction*100:.1f}%总交易额")
    
    # 洞察2：业务线占比
    business_amount = df_summary.groupby("业务线")["毛交易额"].sum()
    top_business = business_amount.nlargest(1).index[0]
    st.write(f"2. **贡献最高业务线**：{top_business}，占总交易额{business_amount[top_business]/total_transaction*100:.1f}%")
    
    # 洞察3：单均指标
    avg_transaction_per_order = total_transaction / total_orders
    avg_commission_per_order = total_commission / total_orders
    st.write(f"4. **单均指标**：单均交易额¥{avg_transaction_per_order:.2f}，单均抽佣¥{avg_commission_per_order:.2f}")
st.divider()

# ======================== 模块3：全量区县经营数据（基于汇总表） ========================
st.subheader("三、全量区县名称经营数据（可筛选区县名称）")
selected_cities = st.multiselect(
    label="选择要查看的区县名称（默认全选）",
    options=df_summary["区县名称"].unique(),
    default=df_summary["区县名称"].unique()
)

city_df = df_summary[df_summary["区县名称"].isin(selected_cities)].groupby("区县名称").agg({
    "毛交易额": "sum",
    "抽佣x+y总计": "sum",
    "抽佣比率(%)": "mean",      # 平均抽佣比率（简单平均，仅供参考）
    "单均抽佣": "mean"
}).round(2).reset_index()
city_df.columns = ["区县名称", "总交易额(元)", "总抽佣(元)", "平均抽佣比率(%)", "单均抽佣"]

# 双轴图
fig_city = px.bar(
    city_df,
    x="区县名称",
    y=["总交易额(元)", "总抽佣(元)"],
    barmode="group",
    title="各区县名称毛交易额与抽佣x+y总计对比",
    hover_data={"平均抽佣比率(%)": ":,.2f%"},
    labels={"value": "金额(元)", "variable": "指标类型"}
)
fig_city.add_scatter(
    x=city_df["区县名称"],
    y=city_df["平均抽佣比率(%)"],
    yaxis="y2",
    name="平均抽佣比率(%)",
    marker_color="red",
    mode="lines+markers"
)
fig_city.update_layout(
    yaxis2=dict(title="平均抽佣比率(%)", overlaying="y", side="right"),
    xaxis=dict(tickangle=-45),
    height=600
)
st.plotly_chart(fig_city, use_container_width=True)

st.subheader("区县名称经营明细表格")
st.dataframe(
    city_df.style.format({
        "总交易额(元)": "¥{:,.2f}",
        "总抽佣(元)": "¥{:,.2f}",
        "平均抽佣比率(%)": "{:.2f}%",
        "单均抽佣": "¥{:,.2f}"
    }),
    use_container_width=True,
    hide_index=True
)
st.divider()

# ======================== 模块4：区县业务线经营看板（基于汇总表） ========================
st.subheader("四、区县业务线经营看板（可筛选区县名称）")
selected_district = st.multiselect(
    label="选择要查看的区县名称（默认全选）",
    options=df_summary["区县名称"].unique(),
    default=df_summary["区县名称"].unique(),
    key="district_business_filter"
)

business_df = df_summary[df_summary["区县名称"].isin(selected_district)].groupby(["区县名称", "业务线"]).agg({
    "毛交易额": "sum",
    "商户抽佣基数": "sum",
    "抽佣x+y总计": "sum",
    "抽佣比率(%)": "mean"
}).round(2).reset_index()
business_df.columns = ["区县名称", "业务线", "总交易额(元)", "总抽佣基数(元)", "总抽佣(元)", "平均抽佣比率(%)"]

# 旭日图
fig_business_pie = px.sunburst(
    business_df,
    path=["区县名称", "业务线"],
    values="总交易额(元)",
    title="各区县 + 业务线交易额占比（钻取图表）",
    hover_data={"平均抽佣比率(%)": ":,.2f%"}
)
st.plotly_chart(fig_business_pie, use_container_width=True)

st.subheader("区县业务线经营明细表格")
st.dataframe(
    business_df.style.format({
        "总交易额(元)": "¥{:,.2f}",
        "总抽佣基数(元)": "¥{:,.2f}",
        "总抽佣(元)": "¥{:,.2f}",
        "平均抽佣比率(%)": "{:.2f}%"
    }),
    use_container_width=True,
    hide_index=True
)
st.divider()

# ======================== 商户分析部分（基于商户明细表） ========================

# 1. 核心数据洞察（商户明细）
st.subheader("📈 核心数据洞察（商户明细）")
with st.expander("点击查看详细分析结论", expanded=True):
    total_commission = df_merchant["抽佣x+y总计"].sum()
    total_base = df_merchant["商户抽佣基数"].sum()
    overall_rate = (total_commission / total_base * 100).round(2)

    biz_summary = df_merchant.groupby("业务线").agg({
        "抽佣x+y总计": "sum",
        "商户抽佣基数": "sum",
        "商户名称": "count"
    }).reset_index()
    biz_summary.columns = ["业务线", "总抽佣(元)", "总抽佣基数(元)", "商户数"]
    biz_summary["业务线抽佣率(%)"] = (biz_summary["总抽佣(元)"] / biz_summary["总抽佣基数(元)"] * 100).round(2)

    median_by_biz = df_merchant.groupby("业务线")["抽佣比率(%)"].median().round(2).reset_index()
    median_by_biz.columns = ["业务线", "中位数抽佣率(%)"]
    biz_summary = biz_summary.merge(median_by_biz, on="业务线", how="left")

    top_biz = biz_summary.loc[biz_summary["业务线抽佣率(%)"].idxmax(), "业务线"]
    top_rate = biz_summary["业务线抽佣率(%)"].max()

    st.markdown(f"""
    **洞察1：整体抽佣率特征**  
    - 整体平均抽佣率（总抽佣/总基数）：**{overall_rate:.2f}%**  
    - 商户抽佣率中位数：**{df_merchant['抽佣比率(%)'].median():.2f}%**  
    - 最高商户抽佣率：**{df_merchant['抽佣比率(%)'].max():.2f}%**  
    - 最低商户抽佣率：**{df_merchant['抽佣比率(%)'].min():.2f}%**  
    """)

    st.markdown(f"""
    **洞察2：不同业务线抽佣率对比**  
    - 抽佣率最高的业务线：**{top_biz}**（{top_rate:.2f}%）  
    - 各业务线详细统计如下：
    """)
    display_cols = ["业务线", "业务线抽佣率(%)", "中位数抽佣率(%)", "商户数"]
    st.dataframe(
        biz_summary[display_cols].style.format({
            "业务线抽佣率(%)": "{:.2f}%",
            "中位数抽佣率(%)": "{:.2f}%"
        }),
        use_container_width=True,
        hide_index=True
    )

    fig_box = px.box(
        df_merchant, x="业务线", y="抽佣比率(%)",
        title="各业务线商户抽佣率分布（箱线图）",
        points="outliers", color="业务线"
    )
    st.plotly_chart(fig_box, use_container_width=True)

st.divider()

# 2. 平均抽佣 Top50 商户（商户明细）
st.subheader("🏆 平均抽佣率 Top50 商户")
top50 = df_merchant.nlargest(50, "抽佣比率")[["区县名称", "业务线", "商户名称", "抽佣比率(%)", "抽佣x+y总计", "商户抽佣基数"]].copy()
top50["抽佣比率(%)"] = top50["抽佣比率(%)"].round(2)
top50["抽佣x+y总计"] = top50["抽佣x+y总计"].round(2)
top50["商户抽佣基数"] = top50["商户抽佣基数"].round(2)

st.dataframe(
    top50.style.format({
        "抽佣比率(%)": "{:.2f}%",
        "抽佣x+y总计": "¥{:,.2f}",
        "商户抽佣基数": "¥{:,.2f}"
    }),
    use_container_width=True,
    hide_index=True
)

fig_top50 = px.bar(
    top50,
    x="商户名称",
    y="抽佣比率(%)",
    color="业务线",
    title="Top50 商户抽佣率（%）",
    text="抽佣比率(%)",
    hover_data=["区县名称", "抽佣x+y总计"]
)
fig_top50.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
fig_top50.update_layout(xaxis_tickangle=-45)
st.plotly_chart(fig_top50, use_container_width=True)

st.divider()

# 3. FML 业务线抽佣率 <23% 的商户（商户明细）
st.subheader("🔍 FML 业务线中抽佣率低于23%的商户")
fml_low = df_merchant[(df_merchant["业务线"] == "FML") & (df_merchant["抽佣比率"] < 0.23)].copy()
if fml_low.empty:
    st.info("未找到符合条件的 FML 业务线商户（抽佣率 < 23%）")
else:
    fml_low = fml_low.sort_values("抽佣比率", ascending=True)
    fml_low["抽佣比率(%)"] = fml_low["抽佣比率(%)"].round(2)
    fml_low["抽佣x+y总计"] = fml_low["抽佣x+y总计"].round(2)
    fml_low["商户抽佣基数"] = fml_low["商户抽佣基数"].round(2)
    
    st.write(f"共找到 **{len(fml_low)}** 家商户，其抽佣率低于23%")
    st.dataframe(
        fml_low[["区县名称", "商户名称", "抽佣比率(%)", "抽佣x+y总计", "商户抽佣基数"]].style.format({
            "抽佣比率(%)": "{:.2f}%",
            "抽佣x+y总计": "¥{:,.2f}",
            "商户抽佣基数": "¥{:,.2f}"
        }),
        use_container_width=True,
        hide_index=True
    )
    
    fig_scatter = px.scatter(
        fml_low,
        x="商户抽佣基数",
        y="抽佣比率(%)",
        color="区县名称",
        size="抽佣x+y总计",
        hover_name="商户名称",
        title="FML 低抽佣商户：抽佣基数 vs 抽佣率",
        labels={"商户抽佣基数": "商户抽佣基数（元）", "抽佣比率(%)": "抽佣率（%）"}
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()
st.caption("注：模块1-4基于「汇总」工作表，商户分析基于「商户明细」工作表。抽佣率 = 抽佣x+y总计 / 商户抽佣基数 × 100%。数据来源账单分析3.1-3.24数据")