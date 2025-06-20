
import streamlit as st
import requests
import pandas as pd
import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Macro Compass", layout="wide", page_icon="🌏")

countries = {
    "Vietnam": "VN", "Indonesia": "ID", "Philippines": "PH",
    "Thailand": "TH", "Malaysia": "MY"
}

score_indicators = {
    "GDP Growth (%)": "NY.GDP.MKTP.KD.ZG",
    "Inflation (%)": "FP.CPI.TOTL.ZG",
    "Unemployment (%)": "SL.UEM.TOTL.ZS",
    "Interest Rate (%)": "FR.INR.DPST"
}

explore_indicators = {
    "GDP (current US$)": "NY.GDP.MKTP.CD",
    "Inflation (% annual)": "FP.CPI.TOTL.ZG",
    "Population": "SP.POP.TOTL",
    "Unemployment (% of labor force)": "SL.UEM.TOTL.ZS",
    "Interest Rate (proxy - deposit rate)": "FR.INR.DPST",
    "Exchange Rate (LCU per USD)": "PA.NUS.FCRF"
}

score_bands = {
    "GDP Growth (%)": [(6, "A"), (4, "B"), (2, "C"), (0, "D"), (-100, "E")],
    "Inflation (%)": [(0, "E"), (2, "D"), (4, "C"), (6, "B"), (100, "A")],
    "Unemployment (%)": [(0, "A"), (3, "B"), (5, "C"), (7, "D"), (100, "E")],
    "Interest Rate (%)": [(0, "A"), (2, "B"), (4, "C"), (6, "D"), (100, "E")]
}

@st.cache_data
def fetch_all_data(indicator_codes, countries_dict):
    base = {}
    for name, code in countries_dict.items():
        base[name] = {}
        for label, ind_code in indicator_codes.items():
            url = f"http://api.worldbank.org/v2/country/{code}/indicator/{ind_code}?format=json&per_page=100"
            r = requests.get(url)
            if r.status_code == 200:
                data = r.json()
                if len(data) > 1 and data[1]:
                    df = pd.DataFrame(data[1])
                    df["date"] = pd.to_datetime(df["date"], errors="coerce")
                    df = df.sort_values("date").dropna(subset=["value"])
                    base[name][label] = df[["date", "value"]].reset_index(drop=True)
                else:
                    base[name][label] = pd.DataFrame()
            else:
                base[name][label] = pd.DataFrame()
    return base

full_data = fetch_all_data({**score_indicators, **explore_indicators}, countries)

with st.sidebar:
    st.title("🌏 Macro Compass")
    view_mode = st.radio("Choose a view:", ["📈 Explorer", "🧮 Scorecard", "⚖️ Comparison"])
    year_range = st.slider("Year range", 2000, 2023, (2010, 2023))
    selected_year = year_range[1]
    st.markdown("**Built by Eastria Economics**  \nPowered by World Bank Open Data")


def grade_indicator(ind_name, val):
    for threshold, grade in score_bands[ind_name]:
        if (ind_name == "Inflation (%)" and val <= threshold) or (ind_name != "Inflation (%)" and val >= threshold):
            return grade
    return "N/A"

# --- EXPLORER ---
if view_mode == "📈 Explorer":
    st.title("📈 Asia Macro Explorer")
    selected_countries = st.sidebar.multiselect("Select up to 3 countries", list(countries.keys()), default=["Vietnam"])
    tabs = st.tabs(list(explore_indicators.keys()))
    for tab, (ind_name, ind_code) in zip(tabs, explore_indicators.items()):
        with tab:
            st.subheader(ind_name)
            combined_df = pd.DataFrame()
            for country in selected_countries[:3]:
                df = full_data[country].get(ind_name, pd.DataFrame())
                if not df.empty:
                    df = df[(df['date'].dt.year >= year_range[0]) & (df['date'].dt.year <= year_range[1])]
                    df = df.rename(columns={"value": country}).set_index("date")
                    if "GDP" in ind_name and "US$" in ind_name:
                        df[country] = df[country] / 1_000_000_000
                    if combined_df.empty:
                        combined_df = df[[country]]
                    else:
                        combined_df = combined_df.join(df[[country]], how="outer")
            if not combined_df.empty:
                fig = px.line(combined_df, markers=True)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No data available.")

# --- SCORECARD ---
elif view_mode == "🧮 Scorecard":
    st.title("🧮 Macro Scorecard")
    selected_country = st.selectbox("Select a country", list(countries.keys()))
    results = {}
    st.subheader(f"Macro Scores – {selected_country} ({selected_year})")
    cols = st.columns(4)
    for i, (ind_name, _) in enumerate(score_indicators.items()):
        df = full_data[selected_country].get(ind_name, pd.DataFrame())
        if not df.empty:
            df_year = df[df["date"].dt.year == selected_year]
            if not df_year.empty:
                val = round(df_year["value"].values[0], 2)
                grade = grade_indicator(ind_name, val)
                results[ind_name] = {"value": val, "grade": grade}
                cols[i].metric(label=ind_name, value=f"{val}", delta=f"Grade: {grade}")
            else:
                results[ind_name] = {"value": "N/A", "grade": "N/A"}
                cols[i].warning(f"{ind_name}: No data ({selected_year})")
        else:
            results[ind_name] = {"value": "N/A", "grade": "N/A"}
            cols[i].warning(f"{ind_name}: No data")

    st.subheader("📋 Summary Insight")
    grades = [v["grade"] for v in results.values() if v["grade"] != "N/A"]
    if grades:
        avg_score = sum(["ABCDE".index(g) for g in grades]) / len(grades)
        overall = "ABCDE"[round(avg_score)]
        st.markdown(f"<div style='font-size:26px; font-weight:bold;'>🏅 {selected_country}: {overall} Grade</div>", unsafe_allow_html=True)

        strong = [k for k, v in results.items() if v["grade"] in ["A", "B"]]
        weak = [k for k, v in results.items() if v["grade"] in ["D", "E"]]
        summary = f"{selected_country} shows strong macroeconomic fundamentals in: **{', '.join(strong)}**."
        if weak:
            summary += f" However, potential weaknesses exist in: **{', '.join(weak)}**."
        st.markdown(f"🧠 _AI Summary_: {summary}")
    else:
        st.info("Summary unavailable due to missing data.")

# --- COMPARISON ---
elif view_mode == "⚖️ Comparison":
    st.title("⚖️ Country Scorecard Comparison")
    col1, col2 = st.columns(2)
    country_a = col1.selectbox("Select Country A", list(countries.keys()), index=0)
    country_b = col2.selectbox("Select Country B", list(countries.keys()), index=1)

    if country_a == country_b:
        st.warning("Please select two different countries.")
        st.stop()

    def get_country_results(country):
        scores = {}
        for ind_name in score_indicators.keys():
            df = full_data[country].get(ind_name, pd.DataFrame())
            if not df.empty:
                df_year = df[df["date"].dt.year == selected_year]
                if not df_year.empty:
                    val = round(df_year["value"].values[0], 2)
                    grade = grade_indicator(ind_name, val)
                    scores[ind_name] = {"value": val, "grade": grade}
                else:
                    scores[ind_name] = {"value": "N/A", "grade": "N/A"}
            else:
                scores[ind_name] = {"value": "N/A", "grade": "N/A"}
        return scores

    results_a = get_country_results(country_a)
    results_b = get_country_results(country_b)

    for ind in score_indicators.keys():
        c1, c2, c3 = st.columns([3, 1, 3])
        val_a, grade_a = results_a[ind]["value"], results_a[ind]["grade"]
        val_b, grade_b = results_b[ind]["value"], results_b[ind]["grade"]
        with c1:
            st.metric(label=f"{country_a} – {ind}", value=val_a, delta=f"Grade: {grade_a}")
        with c2:
            st.markdown("<div style='text-align:center;padding-top:20px;'>vs</div>", unsafe_allow_html=True)
        with c3:
            st.metric(label=f"{country_b} – {ind}", value=val_b, delta=f"Grade: {grade_b}")

    def grade_score(g):
        return "ABCDE".index(g) if g in "ABCDE" else None

    avg_a = [grade_score(v["grade"]) for v in results_a.values() if grade_score(v["grade"]) is not None]
    avg_b = [grade_score(v["grade"]) for v in results_b.values() if grade_score(v["grade"]) is not None]

    if avg_a and avg_b:
        mean_a = sum(avg_a) / len(avg_a)
        mean_b = sum(avg_b) / len(avg_b)
        overall_a = "ABCDE"[round(mean_a)]
        overall_b = "ABCDE"[round(mean_b)]
        st.markdown("### 🏅 Overall Rating")
        ca, cb = st.columns(2)
        ca.markdown(f"<div style='font-size:26px; font-weight:bold;'>{country_a}: {overall_a} Grade</div>", unsafe_allow_html=True)
        cb.markdown(f"<div style='font-size:26px; font-weight:bold;'>{country_b}: {overall_b} Grade</div>", unsafe_allow_html=True)

