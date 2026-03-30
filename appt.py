import streamlit as st
import plotly.express as px
import pandas as pd
import numpy as np
import os
from pathlib import Path

# -------------------------- 全局配置 --------------------------
st.set_page_config(
    page_title="商户经营综合看板",
    layout="wide",
    page_icon="📊"
)

# -------------------------- 路径适配（本地/GitHub双环境） --------------------------
DEFAULT_FILE_NAME = "抽佣看板（剔除拼团，超客配)2.xlsx"
LOCAL_FILE_PATH = Path(__file__).parent / DEFAULT_FILE_NAME

# -------------------------- 侧边栏配置 --------------------------
st.sidebar.title("📋 看板导航")
selected_board = st.sidebar.radio(
    "选择查看的看板",
    ["商户抽佣经营看板", "商户利润看板"],
    index=0
)

# -------------------------- 文件上传/加载逻辑（核心适配） --------------------------
st.sidebar.divider()
st.sidebar.subheader("📁 文件上传")
uploaded_file = st.sidebar.file_uploader(
    "上传Excel文件（格式需匹配）",
    type=["xlsx"],
    help="请上传包含 汇总/商户明细/商户当月利润 工作表的Excel文件"
)

# 加载文件的通用函数
@st.cache_data
def load_excel_file(file_obj, sheet_name=None):
    """通用Excel加载函数，兼容上传文件和本地文件"""
    try:
        if sheet_name:
            df_dict = pd.read_excel(file_obj, sheet_name=sheet_name, engine="openpyxl")
        else:
            df_dict = pd.read_excel(file_obj, engine="openpyxl")
        st.success("✅ 数据加载成功！")
        return df_dict
    except Exception as e:
        st.error(f"❌ 数据读取失败：{str(e)}")
        st.error("请检查文件格式是否正确，是否包含所需工作表（汇总/商户明细/商户当月利润）")
        return None

# 确定最终使用的文件
if uploaded_file:
    FILE_OBJ = uploaded_file
else:
    if LOCAL_FILE_PATH.exists():
        FILE_OBJ = str(LOCAL_FILE_PATH)
        st.sidebar.info(f"使用本地文件：{LOCAL_FILE_PATH}")
    else:
        st.sidebar.warning(f"本地文件未找到：{LOCAL_FILE_PATH}")
        st.warning("⚠️ 未检测到上传文件且本地文件不存在，请在侧边栏上传Excel文件！")
        st.stop()

# ======================== 商户抽佣经营看板 ========================
if selected_board == "商户抽佣经营看板":
    st.title("📊 商户抽佣经营综合看板-剔除拼团/超客配")
    st.divider()
    # 加载抽佣数据（汇总+商户明细）
    sheets = load_excel_file(FILE_OBJ, sheet_name=['汇总', '商户明细'])
    if sheets is None:
        st.stop()
    df_summary, df_merchant = sheets['汇总'], sheets['商户明细']

    # -------------------------- 汇总表预处理（强制小数处理） --------------------------
    required_summary_cols = ["区县名称", "业务线", "毛交易额", "抽佣x+y总计", "商户抽佣基数", "业务类型计数"]
    missing_summary = [col for col in required_summary_cols if col not in df_summary.columns]
    if missing_summary:
        st.error(f"汇总表缺少字段：{', '.join(missing_summary)}")
        st.stop()
    # 强制转浮点数，避免整数类型
    for col in ["毛交易额", "抽佣x+y总计", "商户抽佣基数", "业务类型计数"]:
        df_summary[col] = pd.to_numeric(df_summary[col], errors='coerce').astype(float)
    # 抽佣比率：强制两位小数（字符串格式化，云端必显）
    df_summary["抽佣比率(%)"] = (df_summary["抽佣x+y总计"] / df_summary["商户抽佣基数"] * 100).apply(lambda x: f"{x:.2f}")
    # 单均抽佣：强制两位小数
    df_summary['单均抽佣'] = (df_summary["抽佣x+y总计"] / df_summary["业务类型计数"]).apply(lambda x: f"{x:.2f}")
    df_summary = df_summary.dropna(subset=required_summary_cols)

    # -------------------------- 商户明细表预处理（强制小数处理） --------------------------
    required_merchant_cols = ["区县名称", "业务线", "商户ID", "商户名称", "抽佣x+y总计", "商户抽佣基数", "抽佣比率"]
    missing_merchant = [col for col in required_merchant_cols if not col in df_merchant.columns]
    if missing_merchant:
        st.error(f"商户明细缺少字段：{', '.join(missing_merchant)}")
        st.stop()
    # 强制转浮点数
    for col in ["抽佣x+y总计", "商户抽佣基数", "抽佣比率"]:
        df_merchant[col] = pd.to_numeric(df_merchant[col], errors='coerce').astype(float)
    # 填充并计算抽佣比率，强制两位小数
    df_merchant["抽佣比率"] = df_merchant["抽佣比率"].fillna(df_merchant["抽佣x+y总计"] / df_merchant["商户抽佣基数"])
    df_merchant = df_merchant[df_merchant["商户抽佣基数"] > 0].copy()
    df_merchant["抽佣比率(%)"] = (df_merchant["抽佣比率"] * 100).apply(lambda x: f"{x:.2f}")

    # ======================== 模块1：核心总计数据（强制两位小数） ========================
    st.subheader("一、核心总计数据")
    total_transaction = df_summary["毛交易额"].sum()
    total_orders = df_summary['业务类型计数'].sum()
    total_commission = df_summary["抽佣x+y总计"].sum()
    merchant_total_commission = df_merchant["抽佣x+y总计"].sum()
    merchant_total_base = df_merchant["商户抽佣基数"].sum()
    
    # 所有指标强制计算+两位小数格式化
    avg_commission_rate = (merchant_total_commission / merchant_total_base * 100) if merchant_total_base !=0 else 0
    avg_order_commission = (total_commission / total_orders) if total_orders !=0 else 0
    total_transaction_wan = total_transaction / 10000
    total_commission_wan = total_commission / 10000

    col1, col2, col3 = st.columns(3, gap="large")
    with col1:
        st.metric("总订单量", f"{total_orders // 10000} 万笔")
    with col2:
        st.metric("总交易额", f"{total_transaction_wan:.2f} 万元")
    with col3:
        st.metric("总抽佣x+y总计", f"{total_commission_wan:.2f} 万元")

    # 第二行 2 个指标（居中显示）
    col4, col5, _ = st.columns(3, gap="large")
    with col4:
        st.metric("平均抽佣比率", f"{avg_commission_rate:.2f}%")
    with col5:
        st.metric("单均抽佣", f"¥{avg_order_commission:.2f}")

    # ======================== 模块2：核心数据洞察分析（强制小数） ========================
    st.subheader("二、核心数据洞察分析")
    with st.expander("展开查看详细洞察", expanded=True):
        top3_cities = df_summary.groupby("区县名称")["毛交易额"].sum().nlargest(3).index.tolist()
        top3_amount = df_summary[df_summary['区县名称'].isin(top3_cities)]['毛交易额'].sum()
        top3_pct = (top3_amount/total_transaction*100) if total_transaction !=0 else 0
        st.write(f"1. **交易额TOP3区县**：{', '.join(top3_cities)}，合计贡献{top3_pct:.2f}%总交易额")
        
        business_amount = df_summary.groupby("业务线")["毛交易额"].sum()
        top_business = business_amount.nlargest(1).index[0] if not business_amount.empty else ""
        top_business_pct = (business_amount[top_business]/total_transaction*100) if total_transaction !=0 else 0
        st.write(f"2. **贡献最高业务线**：{top_business}，占总交易额{top_business_pct:.2f}%")
        
        avg_transaction_per_order = (total_transaction / total_orders) if total_orders !=0 else 0
        avg_commission_per_order = (total_commission / total_orders) if total_orders !=0 else 0
        st.write(f"3. **单均指标**：单均交易额¥{avg_transaction_per_order:.2f}，单均抽佣¥{avg_commission_per_order:.2f}")

    # ========== 新增：抽佣看板3条核心洞察+经营建议（强制小数） ==========
    st.subheader("三、抽佣核心经营洞察与优化建议")
    with st.expander("📌 点击查看洞察与建议", expanded=True):
        # 洞察1：抽佣率离散度分析
        # 转回数值计算标准差/中位数，再格式化
        df_merchant['抽佣比率_数值'] = pd.to_numeric(df_merchant["抽佣比率(%)"], errors='coerce')
        commission_std = df_merchant['抽佣比率_数值'].std() if not df_merchant.empty else 0
        commission_median = df_merchant['抽佣比率_数值'].median() if not df_merchant.empty else 0
        st.markdown(f"### 洞察1：商户抽佣率离散度较高，存在费率不统一问题")
        st.write(f"全体商户抽佣率中位数为**{commission_median:.2f}%**，标准差达**{commission_std:.2f}**，说明不同商户间抽佣费率差异显著，部分商户费率偏离均值过大。")
        st.markdown(f"**优化建议**：梳理高费率商户的合作条款，对优质高交易额商户适当下调费率提升粘性；对低费率且交易额偏低的商户，重新评估合作价值并统一费率标准。")
        st.divider()

        # 洞察2：区县抽佣效率差异
        city_commission_eff = df_summary.groupby("区县名称").apply(
            lambda x: (x["抽佣x+y总计"].sum()/x["毛交易额"].sum())*100 if x["毛交易额"].sum() !=0 else 0
        )
        max_eff_city = city_commission_eff.idxmax() if not city_commission_eff.empty else ""
        min_eff_city = city_commission_eff.idxmin() if not city_commission_eff.empty else ""
        max_eff = city_commission_eff.max() if not city_commission_eff.empty else 0
        min_eff = city_commission_eff.min() if not city_commission_eff.empty else 0
        st.markdown(f"### 洞察2：各区县抽佣效率差异悬殊，资源分配不均")
        st.write(f"抽佣效率（抽佣/交易额）最高的区县为**{max_eff_city}（{max_eff:.2f}%）**，最低为**{min_eff_city}（{min_eff:.2f}%）**，二者相差**{(max_eff-min_eff):.2f}个百分点**。")
        st.markdown(f"**优化建议**：向{max_eff_city}学习商户运营策略，向{min_eff_city}派驻运营人员优化商户结构；优先在高抽佣效率区县拓展新商户，提升资源投入回报率。")
        st.divider()

        # 洞察3：FML业务线低费率商户占比
        fml_df = df_merchant[df_merchant["业务线"]=="FML"]
        fml_total = len(fml_df)
        fml_low_rate = len(fml_df[pd.to_numeric(fml_df["抽佣比率(%)"], errors='coerce')<23])
        fml_low_rate_pct = (fml_low_rate/fml_total*100) if fml_total>0 else 0.00
        st.markdown(f"### 洞察3：FML业务线低费率商户占比{fml_low_rate_pct:.2f}%，营收流失风险")
        st.write(f"FML业务线共{fml_total}家商户，其中抽佣率低于23%的有{fml_low_rate}家，占比{fml_low_rate_pct:.2f}%，该部分商户拉低了整体业务线抽佣收益。")
        st.markdown(f"**优化建议**：对FML低费率商户进行分层，对交易额低的低费率商户限期调整费率；对高交易额低费率商户，通过增值服务（如流量扶持）弥补费率缺口，逐步提升抽佣率。")

    st.divider()

    # ======================== 模块3：全量区县经营数据（强制小数） ========================
    st.subheader("四、全量区县经营数据（可筛选）")
    selected_cities = st.multiselect(
        "选择区县（默认全选）",
        options=df_summary["区县名称"].unique(),
        default=df_summary["区县名称"].unique()
    )
    # 分组聚合+强制小数处理
    city_df = df_summary[df_summary["区县名称"].isin(selected_cities)].groupby("区县名称").agg({
        "毛交易额": "sum",
        "抽佣x+y总计": "sum",
        "抽佣比率(%)": lambda x: pd.to_numeric(x, errors='coerce').mean(),
        "单均抽佣": lambda x: pd.to_numeric(x, errors='coerce').mean()
    }).reset_index()
    # 所有数值列强制两位小数
    city_df["总交易额(元)"] = city_df["毛交易额"].apply(lambda x: f"{x:.2f}")
    city_df["总抽佣(元)"] = city_df["抽佣x+y总计"].apply(lambda x: f"{x:.2f}")
    city_df["平均抽佣比率(%)"] = city_df["抽佣比率(%)"].apply(lambda x: f"{x:.2f}")
    city_df["单均抽佣"] = city_df["单均抽佣"].apply(lambda x: f"{x:.2f}")
    # 保留需要的列
    city_df = city_df[["区县名称", "总交易额(元)", "总抽佣(元)", "平均抽佣比率(%)", "单均抽佣"]]

    # 绘图（转回数值绘图，不影响显示）
    city_df_plot = city_df.copy()
    for col in ["总交易额(元)", "总抽佣(元)", "平均抽佣比率(%)"]:
        city_df_plot[col] = pd.to_numeric(city_df_plot[col], errors='coerce')
    fig_city = px.bar(city_df_plot, x="区县名称", y=["总交易额(元)", "总抽佣(元)"], barmode="group", title="各区县交易额与抽佣对比")
    fig_city.add_scatter(x=city_df_plot["区县名称"], y=city_df_plot["平均抽佣比率(%)"], yaxis="y2", name="平均抽佣比率(%)", marker_color="red", mode="lines+markers")
    fig_city.update_layout(yaxis2=dict(title="平均抽佣比率(%)", overlaying="y", side="right"), xaxis=dict(tickangle=-45), height=600)
    st.plotly_chart(fig_city, width="stretch")

    st.dataframe(
        city_df,
        width="stretch",
        hide_index=True
    )
    st.divider()

    # ======================== 模块4：区县业务线经营看板（强制小数） ========================
    st.subheader("五、区县业务线经营看板")
    selected_district = st.multiselect(
        "选择区县",
        df_summary["区县名称"].unique(),
        df_summary["区县名称"].unique(),
        key="district_business_filter"
    )
    # 分组聚合+强制小数
    business_df = df_summary[df_summary["区县名称"].isin(selected_district)].groupby(["区县名称","业务线"]).agg({
        "毛交易额":"sum",
        "商户抽佣基数":"sum",
        "抽佣x+y总计":"sum",
        "抽佣比率(%)": lambda x: pd.to_numeric(x, errors='coerce').mean()
    }).reset_index()
    # 强制两位小数格式化
    business_df["总交易额(元)"] = business_df["毛交易额"].apply(lambda x: f"{x:.2f}")
    business_df["总抽佣基数(元)"] = business_df["商户抽佣基数"].apply(lambda x: f"{x:.2f}")
    business_df["总抽佣(元)"] = business_df["抽佣x+y总计"].apply(lambda x: f"{x:.2f}")
    business_df["平均抽佣比率(%)"] = business_df["抽佣比率(%)"].apply(lambda x: f"{x:.2f}")
    # 保留需要的列
    business_df = business_df[["区县名称","业务线","总交易额(元)","总抽佣基数(元)","总抽佣(元)","平均抽佣比率(%)"]]

    # 绘图（转回数值）
    business_df_plot = business_df.copy()
    business_df_plot["总交易额(元)"] = pd.to_numeric(business_df_plot["总交易额(元)"], errors='coerce')
    fig_business = px.sunburst(business_df_plot, path=["区县名称","业务线"], values="总交易额(元)", title="区县+业务线交易额占比")
    st.plotly_chart(fig_business, width="stretch")
    
    st.dataframe(
        business_df,
        width="stretch",
        hide_index=True
    )
    st.divider()

    # ======================== 商户分析（强制小数） ========================
    st.subheader("📈 熠威商户抽佣明细分析")
    with st.expander("核心洞察", expanded=True):
        total_c = df_merchant["抽佣x+y总计"].sum()
        total_b = df_merchant["商户抽佣基数"].sum()
        overall = (total_c/total_b*100) if total_b !=0 else 0
        median_rate = df_merchant['抽佣比率_数值'].median() if not df_merchant.empty else 0
        st.markdown(f"- 整体抽佣率：**{overall:.2f}%**\n- 商户中位数：**{median_rate:.2f}%**")
        
        biz = df_merchant.groupby("业务线").agg({
            "抽佣x+y总计":"sum",
            "商户抽佣基数":"sum",
            "商户名称":"count"
        }).reset_index()
        biz.columns = ["业务线","总抽佣","总基数","商户数"]
        biz["抽佣率(%)"] = (biz["总抽佣"]/biz["总基数"]*100).apply(lambda x: f"{x:.2f}" if biz["总基数"].iloc[0] !=0 else "0.00")
        
        st.dataframe(
            biz,
            width="stretch",
            hide_index=True
        )

    st.subheader("🏆熠威抽佣率 TOP500商户")
    # 取 TOP500，强制小数
    df_merchant['抽佣比率_数值'] = pd.to_numeric(df_merchant["抽佣比率(%)"], errors='coerce')
    top500 = df_merchant.nlargest(500, "抽佣比率_数值")[
        ["区县名称","业务线","商户名称","抽佣比率(%)","抽佣x+y总计","商户抽佣基数"]
    ].sort_values("抽佣比率_数值", ascending=False)
    # 金额列强制两位小数
    top500["抽佣x+y总计"] = top500["抽佣x+y总计"].apply(lambda x: f"{x:.2f}")
    top500["商户抽佣基数"] = top500["商户抽佣基数"].apply(lambda x: f"{x:.2f}")
    # 展示
    st.dataframe(
        top500,
        hide_index=True,
        use_container_width=True
    )

    st.subheader("🔍 FML 业务线抽佣率 <23% 商户")
    fml_low = df_merchant[(df_merchant["业务线"]=="FML") & (df_merchant['抽佣比率_数值']<23)]
    # 强制小数格式化
    if not fml_low.empty:
        fml_low["抽佣x+y总计"] = fml_low["抽佣x+y总计"].apply(lambda x: f"{x:.2f}")
        fml_low["商户抽佣基数"] = fml_low["商户抽佣基数"].apply(lambda x: f"{x:.2f}")
    
    if fml_low.empty:
        st.info("无符合条件商户")
    else:
        st.dataframe(
            fml_low[["区县名称","商户名称","抽佣比率(%)","抽佣x+y总计","商户抽佣基数"]],
            width="stretch",
            hide_index=True
        )

# ======================== 商户利润看板（全量强制小数） ========================
elif selected_board == "商户利润看板":
    st.title("💰 商户利润数据分析看板")
    st.divider()
    # 加载利润数据
    df = load_excel_file(FILE_OBJ, sheet_name="商户当月利润")
    if df is None:
        st.stop()

    # 安全计算利润+强制小数处理
    if "毛交易额" in df.columns and "估算成本" in df.columns and "利润" in df.columns:
        # 全量数值列强制转浮点数
        df["毛交易额"] = pd.to_numeric(df["毛交易额"], errors='coerce').astype(float)
        df["估算成本"] = pd.to_numeric(df["估算成本"], errors='coerce').astype(float)
        df["当月利润"] = pd.to_numeric(df["利润"], errors='coerce').astype(float)
        df["结算金额"] = pd.to_numeric(df.get("结算金额", df["毛交易额"]), errors='coerce').astype(float)
        # 利润率：强制两位小数（字符串型）
        df["利润率(%)"] = np.where(
            df["结算金额"] != 0,
            (df["当月利润"] / df["毛交易额"] * 100).apply(lambda x: f"{x:.2f}"),
            "0.00"
        )
        
        # 利润等级划分
        def get_profit_level(profit):
            if pd.isna(profit):
                return "未知"
            elif profit >= 10000:
                return "高利润(≥1万)"
            elif profit >= 5000:
                return "中高利润(5千-1万)"
            elif profit >= 0:
                return "微利(0-5千)"
            elif profit >= -5000:
                return "小幅亏损(-5千-0)"
            else:
                return "大幅亏损(<-5千)"
        
        def get_profit_rate_level(rate):
            if pd.isna(rate) or rate == "0.00":
                return "未知"
            rate = float(rate)
            if rate >= 20:
                return "高利润率(≥20%)"
            elif rate >= 10:
                return "中高利润率(10%-20%)"
            elif rate >= 0:
                return "正利润率(0%-10%)"
            else:
                return "负利润率(<0%)"
        
        df["利润等级"] = df["当月利润"].apply(get_profit_level)
        df["利润率等级"] = df["利润率(%)"].apply(get_profit_rate_level)

    # 筛选
    st.subheader("🔍 筛选条件")
    cols = st.columns(4)
    with cols[0]:
        districts = st.multiselect("区县", df["区县名称"].unique() if "区县名称" in df.columns else [], 
                                  placeholder="选择区县...")
    with cols[1]:
        mch_ids = st.multiselect("商户ID", df["商户ID"].unique() if "商户ID" in df.columns else [],
                                placeholder="选择商户ID...")
    with cols[2]:
        profit_levels = st.multiselect(
            "利润等级", 
            df["利润等级"].unique() if "利润等级" in df.columns else [],
            placeholder="选择利润等级...",
            key="profit_level_filter"
        )
    with cols[3]:
        profit_rate_levels = st.multiselect(
            "利润率等级", 
            df["利润率等级"].unique() if "利润率等级" in df.columns else [],
            placeholder="选择利润率等级...",
            key="profit_rate_level_filter"
        )

    dff = df.copy()
    if districts:
        dff = dff[dff["区县名称"].isin(districts)]
    if mch_ids:
        dff = dff[dff["商户ID"].isin(mch_ids)]
    if profit_levels and "利润等级" in dff.columns:
        dff = dff[dff["利润等级"].isin(profit_levels)]
    if profit_rate_levels and "利润率等级" in dff.columns:
        dff = dff[dff["利润率等级"].isin(profit_rate_levels)]

    # 核心指标（强制两位小数）
    st.subheader("📊 核心指标")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("商户数", dff["商户ID"].nunique() if "商户ID" in dff.columns else len(dff))
    
    total_settle = dff['毛交易额'].sum() / 10000 if "毛交易额" in dff.columns else 0.00
    total_profit = dff['当月利润'].sum() / 10000 if "当月利润" in dff.columns else 0.00
    c2.metric("总毛交易额", f"{total_settle:.2f} 万元")
    c3.metric("总利润", f"{total_profit:.2f} 万元")
    
    if total_settle != 0 and "当月利润" in dff.columns and "毛交易额" in dff.columns:
        profit_rate = (total_profit / total_settle * 100)
    else:
        profit_rate = 0.00
    c4.metric("平均利润率", f"{profit_rate:.2f}%")

    # ========== 新增：利润看板3条核心洞察+经营建议（强制小数） ==========
    st.subheader("三、利润核心经营洞察与优化建议")
    with st.expander("📌 点击查看洞察与建议", expanded=True):
        if "利润等级" in dff.columns and "毛交易额" in dff.columns and not dff.empty:
            # 洞察1：利润与交易额匹配度分析
            high_profit_df = dff[dff["利润等级"].isin(["高利润(≥1万)","中高利润(5千-1万)"])]
            high_profit_amt = high_profit_df["毛交易额"].sum()
            total_amt = dff["毛交易额"].sum()
            high_profit_pct = (high_profit_amt/total_amt*100) if total_amt>0 else 0.00
            high_profit_mer_pct = (len(high_profit_df)/len(dff)*100) if len(dff)>0 else 0.00
            st.markdown(f"### 洞察1：高利润商户贡献{high_profit_pct:.2f}%交易额，头部效应显著")
            st.write(f"高/中高利润商户仅占全体商户的**{high_profit_mer_pct:.2f}%**，却贡献了{high_profit_pct:.2f}%的总交易额，利润与交易额高度正相关。")
            st.markdown(f"**优化建议**：建立高利润商户专属扶持计划，提供流量倾斜、佣金减免等福利；提炼高利润商户的经营模式，向微利/亏损商户进行复制培训。")
            st.divider()

            # 洞察2：亏损商户结构分析
            loss_merchant = dff[dff["利润等级"].isin(["小幅亏损(-5千-0)","大幅亏损(<-5千)"])]
            loss_amt = loss_merchant["当月利润"].sum() if "当月利润" in loss_merchant.columns else 0
            loss_merchant_pct = (len(loss_merchant)/len(dff)*100) if len(dff)>0 else 0.00
            st.markdown(f"### 洞察2：{loss_merchant_pct:.2f}%商户处于亏损状态，合计亏损{(loss_amt/10000):.2f}万元")
            st.write(f"全量筛选商户中，亏损商户共{len(loss_merchant)}家，其中大幅亏损商户{len(dff[dff['利润等级']=='大幅亏损(<-5千)'])}家，部分商户亏损额远超营收。")
            st.markdown(f"**优化建议**：对小幅亏损商户进行成本优化指导（如降低配送/采购成本）；对大幅亏损且持续3个月以上的商户，评估合作必要性，及时止损；对高交易额亏损商户，重点优化定价策略。")
            st.divider()

            # 洞察3：利润率与交易额协同性分析
            dff['毛交易额_数值'] = dff['毛交易额']
            high_amt_quantile = dff['毛交易额_数值'].quantile(0.75) if not dff.empty else 0
            low_rate_high_amt = dff[(dff["利润率等级"]=="负利润率(<0%)") & (dff["毛交易额_数值"] > high_amt_quantile)]
            st.markdown(f"### 洞察3：{len(low_rate_high_amt)}家高交易额商户利润率为负，营收潜力未释放")
            st.write(f"交易额前25%（≥¥{high_amt_quantile:.2f}）的商户中，有{len(low_rate_high_amt)}家利润率为负，该类商户具备高交易基础，利润提升空间巨大。")
            st.markdown(f"**优化建议**：为高交易额负利润商户配备专属运营顾问，一对一优化成本结构和定价体系；通过批量采购、物流整合等方式降低其运营成本，将交易额优势转化为利润优势。")
        else:
            st.info("暂无足够数据生成利润洞察，请选择有效筛选条件或补充数据后查看")

    st.divider()

    # 利润等级分布（强制小数）
    if "利润等级" in dff.columns and not dff.empty:
        st.subheader("四、利润等级分布")
        profit_level_dist = dff["利润等级"].value_counts().reset_index()
        profit_level_dist.columns = ["利润等级", "商户数量"]
        
        fig_profit_level = px.pie(
            profit_level_dist,
            values="商户数量",
            names="利润等级",
            title="各利润等级商户数量分布",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig_profit_level, width="stretch")
        
        # 利润等级汇总，强制两位小数
        profit_level_summary = dff.groupby("利润等级").agg({
            "商户ID": "nunique",
            "毛交易额": "sum",
            "当月利润": "sum",
            "利润率(%)": lambda x: pd.to_numeric(x, errors='coerce').mean()
        }).reset_index()
        profit_level_summary.columns = ["利润等级", "商户数", "总交易额(元)", "总利润(元)", "平均利润率(%)"]
        # 强制小数格式化
        profit_level_summary["总交易额(元)"] = profit_level_summary["总交易额(元)"].apply(lambda x: f"{x:.2f}")
        profit_level_summary["总利润(元)"] = profit_level_summary["总利润(元)"].apply(lambda x: f"{x:.2f}")
        profit_level_summary["平均利润率(%)"] = profit_level_summary["平均利润率(%)"].apply(lambda x: f"{x:.2f}")
        
        st.dataframe(
            profit_level_summary,
            width="stretch",
            hide_index=True
        )

    # 利润率等级分布
    if "利润率等级" in dff.columns and not dff.empty:
        st.subheader("五、利润率等级分布")
        profit_rate_dist = dff["利润率等级"].value_counts().reset_index()
        profit_rate_dist.columns = ["利润率等级", "商户数量"]
        
        fig_profit_rate = px.bar(
            profit_rate_dist,
            x="利润率等级",
            y="商户数量",
            title="各利润率等级商户数量分布",
            color="利润率等级",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_profit_rate.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_profit_rate, width="stretch")

    # 明细数据（修复：去掉Styler，避免超大表格报错，强制小数）
    st.subheader("六、明细数据")
    display_cols = df.columns.tolist()
    if "利润等级" in display_cols and "利润率等级" in display_cols:
        display_cols.remove("利润等级")
        display_cols.remove("利润率等级")
        display_cols = ["区县名称", "商户ID", "商户名称", "利润等级", "利润率等级"] + [col for col in display_cols if col not in ["区县名称", "商户ID", "商户名称"]]
    
    # 明细数据金额列强制两位小数
    dff_display = dff[display_cols].copy()
    for col in dff_display.columns:
        if col in ["毛交易额", "估算成本", "当月利润", "结算金额"] and col in dff_display.columns:
            dff_display[col] = dff_display[col].apply(lambda x: f"{x:.2f}")
    
    st.dataframe(
        dff_display,
        width="stretch",
        height=500,
        hide_index=True
    )
