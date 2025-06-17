
import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# Set page configuration once at the top
st.set_page_config(page_title="Macro Compass", layout="wide", page_icon="🌏")

# Shared country dictionary and indicators
countries = {
    "Vietnam": "VN",
    "Indonesia": "ID",
    "Philippines": "PH",
    "Thailand": "TH",
    "Malaysia": "MY"
}

score_indicators = {
    "GDP Growth (%)": "NY.GDP.MKTP.KD.ZG",
    "Inflation (%)": "FP.CPI.TOTL.ZG",
    "Unemployment (%)": "SL.UEM.TOTL.ZS",
    "Gov Debt (% of GDP)": "GC.DOD.TOTL.GD.ZS"
}

explore_indicators = {
    "GDP (current $ Billion)": "NY.GDP.MKTP.CD",
    "Inflation (% annual)": "FP.CPI.TOTL.ZG",
    "Population": "SP.POP.TOTL",
    "Unemployment (% of labor force)": "SL.UEM.TOTL.ZS",
    "Interest Rate (proxy - deposit rate)": "FR.INR.DPST",
    "Exchange Rate (LCU per USD)": "PA.NUS.FCRF",
    "Government Debt (% of GDP)": "GC.DOD.TOTL.GD.ZS"
}

score_bands = {
    "GDP Growth (%)": [(6, "A"), (4, "B"), (2, "C"), (0, "D"), (-100, "E")],
    "Inflation (%)": [(0, "E"), (2, "D"), (4, "C"), (6, "B"), (100, "A")],
    "Unemployment (%)": [(0, "A"), (3, "B"), (5, "C"), (7, "D"), (100, "E")],
    "Gov Debt (% of GDP)": [(30, "A"), (50, "B"), (70, "C"), (90, "D"), (1000, "E")]
}

@st.cache_data
def fetch_data(country_code, indicator_code):
    url = f"http://api.worldbank.org/v2/country/{country_code}/indicator/{indicator_code}?format=json&per_page=100"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if len(data) > 1 and data[1]:
            df = pd.DataFrame(data[1])
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df = df.sort_values('date')
            return df[['date', 'value']].dropna()
    return pd.DataFrame()

def score_indicator(indicator, value):
    for threshold, grade in score_bands[indicator]:
        if (indicator == "Inflation (%)" and value <= threshold) or (indicator != "Inflation (%)" and value >= threshold):
            return grade
    return "N/A"

# Sidebar navigation
with st.sidebar:
    st.title("🌏 Macro Compass")
    view_mode = st.radio("Choose a view:", ["📈 Explorer", "🧮 Scorecard", "⚖️ Comparison"])
    st.markdown("**Built by Eastria Economics**  \\nPowered by World Bank Open Data")

# View: Explorer
if view_mode == "📈 Explorer":
    st.title("📈 Asia Macro Explorer")
    st.markdown("Compare macroeconomic indicators across countries.")

    selected_countries = st.sidebar.multiselect("Select up to 3 countries", list(countries.keys()), default=["Vietnam"])
    year_range = st.sidebar.slider("Year range", 2000, 2023, (2005, 2023))

    tabs = st.tabs(list(explore_indicators.keys()))
    for tab, (ind_name, ind_code) in zip(tabs, explore_indicators.items()):
        with tab:
            st.subheader(ind_name)
            combined_df = pd.DataFrame()
            for country in selected_countries[:3]:
                code = countries[country]
                df = fetch_data(code, ind_code)
                df = df[(df['date'].dt.year >= year_range[0]) & (df['date'].dt.year <= year_range[1])]
                df = df.rename(columns={"value": country}).set_index("date")
                if "GDP" in ind_name and "US$" in ind_name:
                    df[country] = df[country] / 1_000_000_000  # Convert to billions
                if combined_df.empty:
                    combined_df = df[[country]]
                else:
                    combined_df = combined_df.join(df[[country]], how="outer")
            if not combined_df.empty:
                combined_df = combined_df.sort_index()
                fig = px.line(combined_df, markers=True)
                fig.update_layout(dragmode=False, xaxis=dict(fixedrange=True), yaxis=dict(fixedrange=True))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No data available.")

# View: Scorecard
elif view_mode == "🧮 Scorecard":
    st.title("🧮 Macro Scorecard")
    selected_country = st.selectbox("Select a country", list(countries.keys()))
    code = countries[selected_country]
    results = {}

    st.subheader(f"Macro Scores – {selected_country}")
    cols = st.columns(4)

    for i, (ind_name, ind_code) in enumerate(score_indicators.items()):
        df = fetch_data(code, ind_code)
        if not df.empty:
            latest = df.dropna().iloc[-1]
            val = round(latest['value'], 2)
            grade = score_indicator(ind_name, val)
            results[ind_name] = {"value": val, "grade": grade}
            cols[i].metric(label=ind_name, value=f"{val}", delta=f"Grade: {grade}")
        else:
            results[ind_name] = {"value": "N/A", "grade": "N/A"}
            cols[i].warning(f"{ind_name}: No data")

    st.subheader("📋 Summary Insight")
    if all(v["grade"] != "N/A" for v in results.values()):
        strengths = [k for k, v in results.items() if v["grade"] in ["A", "B"]]
        risks = [k for k, v in results.items() if v["grade"] in ["D", "E"]]
        summary = f"**{selected_country}** shows macroeconomic **strength** in: {', '.join(strengths)}"
        summary += f"; and potential **risk** areas in: {', '.join(risks)}." if risks else "."
        st.markdown(summary)
    else:
        st.info("Summary unavailable due to missing data.")

    grades = [v["grade"] for v in results.values() if v["grade"] in ["A", "B", "C", "D", "E"]]
    if grades:
        avg_score = sum(["ABCDE".index(g) for g in grades]) / len(grades)
        overall = "ABCDE"[round(avg_score)]
        st.markdown(f"<div style='font-size:26px; font-weight:bold; color:#0B1F3A;'>🏅 {selected_country}: {overall} Grade</div>", unsafe_allow_html=True)

    with st.expander("📘 How We Score Each Macro Indicator"):
        st.markdown("""
| Indicator | Grade A | B | C | D | E |
|-----------|---------|---|---|---|---|
| **GDP Growth (%)** | ≥ 6% | 4–6% | 2–4% | 0–2% | < 0% |
| **Inflation (% YoY)** | 4–6% | 2–4% | 0–2% | >6% | ≤ 0% |
| **Unemployment (%)** | < 3% | 3–5% | 5–7% | 7–10% | > 10% |
| **Gov Debt (% of GDP)** | < 30% | 30–50% | 50–70% | 70–90% | > 90% |
        """)

# View: Comparison
elif view_mode == "⚖️ Comparison":
    st.title("⚖️ Country Scorecard Comparison")
    col1, col2 = st.columns(2)
    with col1:
        country_a = st.selectbox("Select Country A", list(countries.keys()), index=0)
    with col2:
        country_b = st.selectbox("Select Country B", list(countries.keys()), index=1)

    if country_a == country_b:
        st.warning("Please select two different countries for comparison.")
        st.stop()

    code_a = countries[country_a]
    code_b = countries[country_b]

    def display_country_results(name, code):
        results = {}
        for ind_name, ind_code in score_indicators.items():
            df = fetch_data(code, ind_code)
            if not df.empty:
                latest = df.dropna().iloc[-1]
                val = round(latest["value"], 2)
                grade = score_indicator(ind_name, val)
                results[ind_name] = {"value": val, "grade": grade}
            else:
                results[ind_name] = {"value": "N/A", "grade": "N/A"}
        return results

    results_a = display_country_results(country_a, code_a)
    results_b = display_country_results(country_b, code_b)

    for ind in score_indicators.keys():
        col1, col2, col3 = st.columns([3, 1, 3])
        val_a, grade_a = results_a[ind]["value"], results_a[ind]["grade"]
        val_b, grade_b = results_b[ind]["value"], results_b[ind]["grade"]
        with col1:
            st.metric(label=f"{country_a} – {ind}", value=val_a, delta=f"Grade: {grade_a}")
        with col2:
            st.markdown("<div style='text-align: center; font-weight: bold; padding-top: 20px;'>vs</div>", unsafe_allow_html=True)
        with col3:
            st.metric(label=f"{country_b} – {ind}", value=val_b, delta=f"Grade: {grade_b}")

    def get_grade_score(g):
        return "ABCDE".index(g) if g in "ABCDE" else None

    avg_a = [get_grade_score(v["grade"]) for v in results_a.values() if get_grade_score(v["grade"]) is not None]
    avg_b = [get_grade_score(v["grade"]) for v in results_b.values() if get_grade_score(v["grade"]) is not None]

    if avg_a and avg_b:
        mean_a = sum(avg_a) / len(avg_a)
        mean_b = sum(avg_b) / len(avg_b)
        overall_a = "ABCDE"[round(mean_a)]
        overall_b = "ABCDE"[round(mean_b)]

        st.markdown("### 🏅 Overall Rating")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"<div style='font-size:26px; font-weight:bold; color:#0B1F3A;'>{country_a}: {overall_a} Grade</div>", unsafe_allow_html=True)
        with col_b:
            st.markdown(f"<div style='font-size:26px; font-weight:bold; color:#0B1F3A;'>{country_b}: {overall_b} Grade</div>", unsafe_allow_html=True)
