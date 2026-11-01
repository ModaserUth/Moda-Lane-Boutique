
from pathlib import Path

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Moda Lane | Business Intelligence",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main {
        background-color: #F8F9FC;
    }
    [data-testid="stMetric"] {
        background-color: white;
        border: 1px solid #E8EAF0;
        padding: 18px;
        border-radius: 12px;
    }
    h1, h2, h3 {
        color: #20243A;
    }
    .subtitle {
        color: #73798C;
        font-size: 15px;
    }
    .insight {
        background-color: white;
        border-left: 4px solid #7357D9;
        padding: 14px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)


# =========================================================
# DATA LOADING
# =========================================================

@st.cache_data
def load_data(file):
    if file is not None:
        df = pd.read_csv(file)
    else:
        candidates = [
            Path("Data - Sheet1(1).csv"),
            Path("Data - Sheet1.csv"),
            Path("data.csv")
        ]

        data_path = next(
            (p for p in candidates if p.exists()),
            None
        )

        if data_path is None:
            return None

        df = pd.read_csv(data_path)

    return df


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.title("Moda Lane")
st.sidebar.caption("Business Intelligence Dashboard")
st.sidebar.divider()

uploaded_file = st.sidebar.file_uploader(
    "Upload Dataset",
    type=["csv"]
)

try:
    raw_df = load_data(uploaded_file)
except Exception as e:
    st.error(f"Could not read the dataset: {e}")
    st.stop()

if raw_df is None:
    st.title("Moda Lane Business Intelligence")
    st.warning(
        "Please upload the Moda Lane CSV dataset "
        "or place it beside app.py."
    )
    st.stop()


required_columns = [
    "Date",
    "Season",
    "Channel",
    "Service Type",
    "Customer Type",
    "Ad Spend",
    "Conversions",
    "Revenue"
]

missing_columns = [
    col for col in required_columns
    if col not in raw_df.columns
]

if missing_columns:
    st.error(
        "The uploaded dataset is missing required columns: "
        + ", ".join(missing_columns)
    )
    st.stop()


# =========================================================
# DATA PREPARATION
# =========================================================

df = raw_df.copy()

df["Date"] = pd.to_datetime(
    df["Date"],
    errors="coerce"
)

numeric_columns = [
    "Ad Spend",
    "Conversions",
    "Revenue"
]

for col in numeric_columns:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

categorical_columns = [
    "Season",
    "Channel",
    "Service Type",
    "Customer Type"
]

for col in categorical_columns:
    df[col] = df[col].astype("string").str.strip()

df = df.dropna(subset=required_columns)

df = df[
    (df["Ad Spend"] >= 0) &
    (df["Conversions"] >= 0) &
    (df["Revenue"] >= 0)
].copy()

df["Month"] = df["Date"].dt.to_period("M").astype(str)
df["Year"] = df["Date"].dt.year
df["Weekday"] = df["Date"].dt.day_name()

df["ROAS"] = np.where(
    df["Ad Spend"] > 0,
    df["Revenue"] / df["Ad Spend"],
    np.nan
)

df["CPA"] = np.where(
    df["Conversions"] > 0,
    df["Ad Spend"] / df["Conversions"],
    np.nan
)

df["Revenue per Conversion"] = np.where(
    df["Conversions"] > 0,
    df["Revenue"] / df["Conversions"],
    np.nan
)


# =========================================================
# FILTERS
# =========================================================

st.sidebar.subheader("Dashboard Filters")

seasons = sorted(df["Season"].dropna().unique().tolist())
channels = sorted(df["Channel"].dropna().unique().tolist())
services = sorted(df["Service Type"].dropna().unique().tolist())
customers = sorted(df["Customer Type"].dropna().unique().tolist())

selected_seasons = st.sidebar.multiselect(
    "Season",
    seasons,
    default=seasons
)

selected_channels = st.sidebar.multiselect(
    "Marketing Channel",
    channels,
    default=channels
)

selected_services = st.sidebar.multiselect(
    "Service Type",
    services,
    default=services
)

selected_customers = st.sidebar.multiselect(
    "Customer Type",
    customers,
    default=customers
)

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

filtered = df[
    df["Season"].isin(selected_seasons) &
    df["Channel"].isin(selected_channels) &
    df["Service Type"].isin(selected_services) &
    df["Customer Type"].isin(selected_customers)
].copy()

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
    filtered = filtered[
        filtered["Date"].dt.date.between(start_date, end_date)
    ]

if filtered.empty:
    st.warning("No records match the selected filters.")
    st.stop()


# =========================================================
# CALCULATIONS
# =========================================================

total_revenue = filtered["Revenue"].sum()
total_ad_spend = filtered["Ad Spend"].sum()
total_conversions = filtered["Conversions"].sum()
total_records = len(filtered)

overall_roas = (
    total_revenue / total_ad_spend
    if total_ad_spend > 0 else np.nan
)

overall_cpa = (
    total_ad_spend / total_conversions
    if total_conversions > 0 else np.nan
)

revenue_per_conversion = (
    total_revenue / total_conversions
    if total_conversions > 0 else np.nan
)


def format_currency(value):
    return f"${value:,.2f}"


def grouped_metrics(column):
    result = (
        filtered.groupby(column, dropna=False)
        .agg(
            Revenue=("Revenue", "sum"),
            Ad_Spend=("Ad Spend", "sum"),
            Conversions=("Conversions", "sum"),
            Records=("Revenue", "size")
        )
        .reset_index()
    )

    result["ROAS"] = np.where(
        result["Ad_Spend"] > 0,
        result["Revenue"] / result["Ad_Spend"],
        np.nan
    )

    result["CPA"] = np.where(
        result["Conversions"] > 0,
        result["Ad_Spend"] / result["Conversions"],
        np.nan
    )

    result["Revenue Contribution (%)"] = (
        result["Revenue"] /
        result["Revenue"].sum() * 100
        if result["Revenue"].sum() > 0
        else 0
    )

    return result


# =========================================================
# NAVIGATION
# =========================================================

pages = [
    "Overview",
    "Sales Analytics",
    "Customer Analytics",
    "Marketing Channels",
    "Service Analysis",
    "Seasonal Analysis",
    "Recommendation Center",
    "Data Quality & Limitations"
]

page = st.sidebar.radio(
    "Navigation",
    pages
)


# =========================================================
# HEADER
# =========================================================

st.title("Moda Lane Boutique")
st.markdown(
    '<p class="subtitle">'
    'Sales Performance | Customer Analytics | Marketing Intelligence'
    '</p>',
    unsafe_allow_html=True
)

st.caption(
    f"Analysis period: {filtered['Date'].min().date()} "
    f"to {filtered['Date'].max().date()} | "
    f"{len(filtered):,} records"
)

st.divider()


# =========================================================
# OVERVIEW
# =========================================================

if page == "Overview":

    st.subheader("Business Performance Overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Revenue",
        format_currency(total_revenue)
    )

    c2.metric(
        "Advertising Spend",
        format_currency(total_ad_spend)
    )

    c3.metric(
        "Total Conversions",
        f"{total_conversions:,.0f}"
    )

    c4.metric(
        "Overall ROAS",
        f"{overall_roas:.2f}x"
        if pd.notna(overall_roas) else "N/A"
    )

    c5, c6, c7 = st.columns(3)

    c5.metric(
        "Average Revenue / Conversion",
        format_currency(revenue_per_conversion)
        if pd.notna(revenue_per_conversion) else "N/A"
    )

    c6.metric(
        "Average CPA",
        format_currency(overall_cpa)
        if pd.notna(overall_cpa) else "N/A"
    )

    c7.metric(
        "Records Analyzed",
        f"{total_records:,}"
    )

    st.divider()

    left, right = st.columns(2)

    with left:
        monthly = (
            filtered.groupby("Month")
            .agg(Revenue=("Revenue", "sum"))
            .reset_index()
        )

        fig = px.line(
            monthly,
            x="Month",
            y="Revenue",
            markers=True,
            title="Monthly Revenue Trend"
        )

        st.plotly_chart(fig, use_container_width=True)

    with right:
        channel_data = grouped_metrics("Channel")

        fig = px.bar(
            channel_data.sort_values("Revenue", ascending=False),
            x="Channel",
            y="Revenue",
            color="Revenue",
            title="Revenue by Marketing Channel"
        )

        st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)

    with left:
        customer_data = grouped_metrics("Customer Type")

        fig = px.pie(
            customer_data,
            names="Customer Type",
            values="Revenue",
            hole=0.45,
            title="Revenue Contribution by Customer Type"
        )

        st.plotly_chart(fig, use_container_width=True)

    with right:
        season_data = grouped_metrics("Season")

        fig = px.bar(
            season_data,
            x="Season",
            y="Revenue",
            color="Season",
            title="Seasonal Revenue Performance"
        )

        st.plotly_chart(fig, use_container_width=True)


# =========================================================
# SALES ANALYTICS
# =========================================================

elif page == "Sales Analytics":

    st.subheader("Sales Performance Analysis")

    monthly = (
        filtered.groupby("Month")
        .agg(
            Revenue=("Revenue", "sum"),
            Ad_Spend=("Ad Spend", "sum"),
            Conversions=("Conversions", "sum")
        )
        .reset_index()
    )

    monthly["ROAS"] = np.where(
        monthly["Ad_Spend"] > 0,
        monthly["Revenue"] / monthly["Ad_Spend"],
        np.nan
    )

    fig = px.line(
        monthly,
        x="Month",
        y="Revenue",
        markers=True,
        title="Revenue Development Over Time"
    )

    st.plotly_chart(fig, use_container_width=True)

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=monthly["Month"],
            y=monthly["Revenue"],
            name="Revenue"
        )
    )

    fig.add_trace(
        go.Scatter(
            x=monthly["Month"],
            y=monthly["Ad_Spend"],
            name="Ad Spend"
        )
    )

    fig.update_layout(
        title="Revenue vs Advertising Spend",
        xaxis_title="Month",
        yaxis_title="Amount"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Monthly Performance Table")

    st.dataframe(
        monthly.round(2),
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "Download Monthly Sales Report",
        monthly.to_csv(index=False).encode("utf-8"),
        "monthly_sales_report.csv",
        "text/csv"
    )


# =========================================================
# CUSTOMER ANALYTICS
# =========================================================

elif page == "Customer Analytics":

    st.subheader("Customer Type Analysis")

    customer_data = grouped_metrics("Customer Type")

    left, right = st.columns(2)

    with left:
        fig = px.bar(
            customer_data,
            x="Customer Type",
            y="Revenue",
            color="Customer Type",
            title="Revenue by Customer Type"
        )

        st.plotly_chart(fig, use_container_width=True)

    with right:
        fig = px.bar(
            customer_data,
            x="Customer Type",
            y="Records",
            color="Customer Type",
            title="Record Distribution"
        )

        st.plotly_chart(fig, use_container_width=True)

    fig = px.bar(
        customer_data,
        x="Customer Type",
        y="Revenue Contribution (%)",
        color="Customer Type",
        title="Revenue Contribution (%)"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        customer_data.round(2),
        use_container_width=True,
        hide_index=True
    )

    st.info(
        "The dataset contains New and Returning customer categories, "
        "but does not include Customer IDs or individual purchase histories. "
        "Therefore, individual retention, churn, RFM, and customer lifetime "
        "value cannot be calculated reliably."
    )


# =========================================================
# MARKETING CHANNELS
# =========================================================

elif page == "Marketing Channels":

    st.subheader("Marketing Channel Performance")

    channel_data = grouped_metrics("Channel")

    c1, c2 = st.columns(2)

    with c1:
        fig = px.bar(
            channel_data.sort_values("Revenue", ascending=False),
            x="Channel",
            y="Revenue",
            color="Channel",
            title="Revenue by Channel"
        )

        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = px.bar(
            channel_data.sort_values("ROAS", ascending=False),
            x="Channel",
            y="ROAS",
            color="Channel",
            title="ROAS by Channel"
        )

        st.plotly_chart(fig, use_container_width=True)

    fig = px.scatter(
        channel_data,
        x="Ad_Spend",
        y="Revenue",
        size="Conversions",
        color="Channel",
        hover_name="Channel",
        title="Advertising Spend vs Revenue"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Channel Performance Details")

    st.dataframe(
        channel_data.round(2),
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "ROAS = Revenue / Advertising Spend. "
        "It is not profit or net ROI because product costs and operating "
        "expenses are not available."
    )


# =========================================================
# SERVICE ANALYSIS
# =========================================================

elif page == "Service Analysis":

    st.subheader("Service Type Performance")

    service_data = grouped_metrics("Service Type")

    left, right = st.columns(2)

    with left:
        fig = px.bar(
            service_data,
            x="Service Type",
            y="Revenue",
            color="Service Type",
            title="Revenue by Service Type"
        )

        st.plotly_chart(fig, use_container_width=True)

    with right:
        fig = px.bar(
            service_data,
            x="Service Type",
            y="Conversions",
            color="Service Type",
            title="Conversions by Service Type"
        )

        st.plotly_chart(fig, use_container_width=True)

    fig = px.bar(
        service_data,
        x="Service Type",
        y="ROAS",
        color="Service Type",
        title="ROAS by Service Type"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        service_data.round(2),
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# SEASONAL ANALYSIS
# =========================================================

elif page == "Seasonal Analysis":

    st.subheader("Seasonal Business Performance")

    season_data = grouped_metrics("Season")

    fig = px.bar(
        season_data,
        x="Season",
        y="Revenue",
        color="Season",
        title="Revenue by Season"
    )

    st.plotly_chart(fig, use_container_width=True)

    fig = px.bar(
        season_data,
        x="Season",
        y="ROAS",
        color="Season",
        title="Seasonal ROAS"
    )

    st.plotly_chart(fig, use_container_width=True)

    fig = px.scatter(
        filtered,
        x="Ad Spend",
        y="Revenue",
        color="Season",
        title="Advertising Spend and Revenue by Season"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        season_data.round(2),
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# RECOMMENDATION CENTER
# =========================================================

elif page == "Recommendation Center":

    st.subheader("Business Recommendation Center")

    channel_data = grouped_metrics("Channel")
    service_data = grouped_metrics("Service Type")
    season_data = grouped_metrics("Season")

    best_channel = channel_data.sort_values(
        "ROAS", ascending=False
    ).iloc[0]

    best_service = service_data.sort_values(
        "Revenue", ascending=False
    ).iloc[0]

    best_season = season_data.sort_values(
        "Revenue", ascending=False
    ).iloc[0]

    best_customer = grouped_metrics(
        "Customer Type"
    ).sort_values(
        "Revenue", ascending=False
    ).iloc[0]

    st.markdown("### Performance Highlights")

    st.markdown(
        f"""
        <div class="insight">
        <b>Top ROAS Channel:</b> {best_channel['Channel']}
        <br>
        ROAS: {best_channel['ROAS']:.2f}x
        </div>

        <div class="insight">
        <b>Highest Revenue Service Type:</b>
        {best_service['Service Type']}
        <br>
        Revenue: {format_currency(best_service['Revenue'])}
        </div>

        <div class="insight">
        <b>Highest Revenue Season:</b> {best_season['Season']}
        <br>
        Revenue: {format_currency(best_season['Revenue'])}
        </div>

        <div class="insight">
        <b>Leading Customer Category by Revenue:</b>
        {best_customer['Customer Type']}
        <br>
        Revenue: {format_currency(best_customer['Revenue'])}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("### Suggested Actions")

    recommendations = []

    recommendations.append(
        f"Review the {best_channel['Channel']} channel because "
        f"it currently has the highest observed ROAS. "
        "Validate the result across additional periods before increasing budget."
    )

    recommendations.append(
        f"Investigate what drives the revenue performance of "
        f"{best_service['Service Type']} and test related offers."
    )

    recommendations.append(
        f"Plan seasonal campaigns around {best_season['Season']}, "
        "while checking whether the pattern repeats in other years."
    )

    recommendations.append(
        f"Compare the needs and purchasing patterns of "
        f"{best_customer['Customer Type']} customers using customer-level "
        "data before designing targeted loyalty campaigns."
    )

    for i, recommendation in enumerate(recommendations, 1):
        st.markdown(f"**{i}.** {recommendation}")

    st.warning(
        "These are descriptive, rule-based suggestions, not causal findings. "
        "A high ROAS alone does not prove profitability."
    )

    st.markdown("### Detailed Comparison")

    st.dataframe(
        channel_data.round(2),
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# DATA QUALITY AND LIMITATIONS
# =========================================================

elif page == "Data Quality & Limitations":

    st.subheader("Dataset Quality Overview")

    quality = pd.DataFrame({
        "Metric": [
            "Number of Records",
            "Number of Columns",
            "Missing Values",
            "Duplicate Rows",
            "Invalid Dates",
            "Zero Revenue Records",
            "Zero Conversion Records"
        ],
        "Value": [
            len(raw_df),
            len(raw_df.columns),
            int(raw_df.isna().sum().sum()),
            int(raw_df.duplicated().sum()),
            int(raw_df["Date"].isna().sum()),
            int((raw_df["Revenue"] == 0).sum()),
            int((raw_df["Conversions"] == 0).sum())
        ]
    })

    st.dataframe(
        quality,
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### Important Data Limitations")

    limitations = [
        (
            "Customer ID",
            "Required for individual customer analysis, RFM, and retention."
        ),
        (
            "Order or Transaction ID",
            "Required to distinguish individual transactions and calculate "
            "purchase frequency."
        ),
        (
            "Product ID and Quantity",
            "Required for product-level performance and basket analysis."
        ),
        (
            "Impressions, Clicks, and Sessions",
            "Required for reliable marketing funnel and click-through analysis."
        ),
        (
            "Cost of Goods and Operating Expenses",
            "Required for gross profit, net profit, and actual ROI."
        ),
        (
            "Customer Acquisition Date",
            "Required for cohort analysis and customer lifetime calculations."
        )
    ]

    for title, description in limitations:
        st.markdown(f"**{title}:** {description}")

    st.info(
        "The current dashboard reports only metrics supported by the "
        "available dataset. It does not fabricate customer-level or "
        "product-level measurements."
    )

    st.markdown("### Export Filtered Dataset")

    st.download_button(
        "Download Filtered Dataset",
        filtered.to_csv(index=False).encode("utf-8"),
        "moda_lane_filtered_data.csv",
        "text/csv"
    )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "Moda Lane Boutique | Business Intelligence & "
    "Rule-Based Recommendation System"
)
