import pandas as pd
from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import numpy as np

# ====================== 读取文件 ======================
file_path = r"D:\打包\Desktop\测试1.xlsx"
print(f"✅ 已加载文件：{file_path}")

try:
    df = pd.read_excel(file_path, sheet_name="商户当月利润", engine="openpyxl")
except:
    df = pd.read_excel(file_path, sheet_name=0, engine="openpyxl")

# ====================== 数据处理 ======================
if "结算金额" in df.columns and "估算成本" in df.columns:
    df["当月利润"] = (df["结算金额"] + df["估算成本"]).round(2)
    df["利润率(%)"] = np.where(
        df["结算金额"] != 0,
        (df["当月利润"] / df["结算金额"] * 100).round(2),
        0.00
    )
else:
    df["当月利润"] = 0.00
    df["利润率(%)"] = 0.00

df["利润等级"] = pd.cut(
    df["当月利润"].fillna(0),
    bins=[-np.inf, 0, 1000, 5000, 10000, np.inf],
    labels=["亏损", "微利", "中等", "良好", "优秀"]
)

for col in df.select_dtypes(include=[np.number]).columns:
    df[col] = df[col].round(2)

# ====================== 启动APP ======================
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "商户利润看板"

# ====================== 界面布局 ======================
app.layout = dbc.Container([
    html.H1("💰 商户利润数据分析看板", className="text-center my-4"),
    
    # 筛选栏
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("区县名称", className="fw-bold mb-2"),
                    dcc.Dropdown(id="county_filter", multi=True)
                ], width=4),
                dbc.Col([
                    html.Label("商户ID", className="fw-bold mb-2"),
                    dcc.Dropdown(id="merchant_filter", multi=True)
                ], width=4),
                dbc.Col([
                    html.Label("利润等级", className="fw-bold mb-2"),
                    dcc.Dropdown(id="level_filter", multi=True)
                ], width=4)
            ])
        ])
    ], className="mb-4"),

    # ========== 4 张汇总卡片 · 完美一行显示 ==========
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("总商户数"),
            dbc.CardBody(html.H4(id="total_merchant", className="text-center"))
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardHeader("总结算金额"),
            dbc.CardBody(html.H4(id="total_amount", className="text-center"))
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardHeader("总利润"),
            dbc.CardBody(html.H4(id="total_profit", className="text-center"))
        ]), width=3),
        dbc.Col(dbc.Card([
            dbc.CardHeader("平均利润率"),
            dbc.CardBody(html.H4(id="avg_profit_rate", className="text-center"))
        ]), width=3)
    ], className="mb-4 g-3"),

    # ========== 6 条数据洞察 · 3行 × 2条（真正实现） ==========
    html.H4("📝 数据洞察及运营建议", className="mt-4 mb-3"),
    dbc.Card([
        dbc.CardBody([
            # 第 1 行
            dbc.Row([
                dbc.Col(html.P(id="i1", className="p-2"), width=6),
                dbc.Col(html.P(id="i2", className="p-2"), width=6),
            ]),
            # 第 2 行
            dbc.Row([
                dbc.Col(html.P(id="i3", className="p-2"), width=6),
                dbc.Col(html.P(id="i4", className="p-2"), width=6),
            ]),
            # 第 3 行
            dbc.Row([
                dbc.Col(html.P(id="i5", className="p-2"), width=6),
                dbc.Col(html.P(id="i6", className="p-2"), width=6),
            ]),
        ])
    ], className="mb-4"),

    # 表格
    html.H4("📋 商户利润明细", className="mt-4 mb-3"),
    html.Div(id="table_container", style={"maxHeight": "500px", "overflowY": "auto"})

], fluid=True, style={"padding": "20px"})

# ====================== 加载选项 ======================
@app.callback(
    [Output("county_filter","options"),
     Output("merchant_filter","options"),
     Output("level_filter","options")],
    Input("county_filter","value")
)
def load(_):
    c = [{"label":str(x),"value":x} for x in df["区县名称"].dropna().unique()] if "区县名称" in df.columns else []
    m = [{"label":str(x),"value":x} for x in df["商户ID"].dropna().unique()] if "商户ID" in df.columns else []
    l = [{"label":x,"value":x} for x in ["亏损","微利","中等","良好","优秀"]]
    return c,m,l

# ====================== 主更新 ======================
@app.callback(
    [Output("total_merchant","children"),
     Output("total_amount","children"),
     Output("total_profit","children"),
     Output("avg_profit_rate","children"),
     Output("i1","children"),Output("i2","children"),
     Output("i3","children"),Output("i4","children"),
     Output("i5","children"),Output("i6","children"),
     Output("table_container","children")],
    [Input("county_filter","value"),
     Input("merchant_filter","value"),
     Input("level_filter","value")]
)
def update(county, merchant, level):
    dff = df.copy()
    if county and "区县名称" in dff.columns:
        dff = dff[dff["区县名称"].isin(county)]
    if merchant and "商户ID" in dff.columns:
        dff = dff[dff["商户ID"].isin(merchant)]
    if level:
        dff = dff[dff["利润等级"].isin(level)]

    # 统计
    total_mch = len(dff)
    total_amt = dff["结算金额"].sum().round(2) if "结算金额" in dff.columns else 0
    total_pft = dff["当月利润"].sum().round(2) if "当月利润" in dff.columns else 0
    avg_rate = dff["利润率(%)"].mean().round(2) if "利润率(%)" in dff.columns else 0

    amt_str = f"¥ {total_amt:,.2f}"
    pft_str = f"¥ {total_pft:,.2f}"
    rate_str = f"{avg_rate}%"

    # 洞察指标
    good = len(dff[dff["利润等级"]=="优秀"])
    loss = len(dff[dff["当月利润"]<0])
    top10 = dff.nlargest(min(10,len(dff)),"当月利润")["当月利润"].mean().round(2) if len(dff) else 0

    # 6条洞察（3行×2条）
    i1 = f"✅ 当前商户总数：{total_mch} 家"
    i2 = f"📊 优秀利润商户：{good} 家"
    i3 = f"⚠️ 亏损商户数量：{loss} 家"
    i4 = f"💡 头部商户平均利润：¥ {top10:,.2f}"
    i5 = f"{'📈' if avg_rate>=5 else '📉'} 平均利润率：{avg_rate}%"
    i6 = "🎯 建议：优化亏损商户，推广优秀模式"

    # 表格
    table = dbc.Table.from_dataframe(dff.head(200),striped=True,bordered=True,hover=True,responsive=True) if not dff.empty else html.Div("暂无数据",className="text-center p-4")

    return total_mch, amt_str, pft_str, rate_str, i1,i2,i3,i4,i5,i6, table

# ====================== 启动 ======================
if __name__ == "__main__":
    app.run(debug=False)
