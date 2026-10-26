from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st


# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
FACTORS_PATH = DATA_DIR / "emission_factors.csv"


# Food conversion assumption
MILK_KG_PER_LITRE = 1.03

st.set_page_config(
    page_title="Carbon Footprint Tracker",
    page_icon="🌱",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    [data-testid="stMetric"] {
        background: #f5f8f6;
        border: 1px solid #e1eae4;
        padding: 16px;
        border-radius: 12px;
    }
    .small-note {
        color: #647067;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_factors():
    """Load emission factors and stop with a clear message if the file is invalid."""
    if not FACTORS_PATH.exists():
        st.error(f"Emission factor file not found: {FACTORS_PATH}")
        st.stop()

    frame = pd.read_csv(FACTORS_PATH)

    required_columns = {
        "activity",
        "factor_value",
        "factor_unit",
        "gas_metric",
        "geography",
        "factor_year",
        "source_name",
        "source_url",
        "notes",
    }

    missing_columns = required_columns.difference(frame.columns)
    if missing_columns:
        st.error(
            "The emission factor CSV is missing these columns: "
            + ", ".join(sorted(missing_columns))
        )
        st.stop()

    frame["factor_value"] = pd.to_numeric(
        frame["factor_value"],
        errors="coerce",
    )

    if frame["factor_value"].isna().any():
        st.error("One or more emission factor values are not numeric.")
        st.stop()

    return frame


factor_table = load_factors()
factor_records = factor_table.set_index("activity").to_dict(orient="index")

required_factors = {
    "grid_electricity",
    "intracity_bus",
    "rail_non_suburban",
    "rail_suburban",
    "food_beef",
    "food_milk",
    "food_peas",
    "food_poultry",
    "food_rice",
}

missing_factors = required_factors.difference(factor_records)
if missing_factors:
    st.error(
        "The factor CSV is missing these activities: "
        + ", ".join(sorted(missing_factors))
    )
    st.stop()


def factor_value(activity):
    return float(factor_records[activity]["factor_value"])


def load_history():
    """Return records saved in this browser session only."""
    history_key = "monthly_history_records"

    if history_key not in st.session_state:
        st.session_state[history_key] = []

    return pd.DataFrame(st.session_state[history_key])


def save_monthly_record(record):
    """Save or replace a month in this browser session only."""
    history_key = "monthly_history_records"

    if history_key not in st.session_state:
        st.session_state[history_key] = []

    records = st.session_state[history_key]

    # Keep only one record for each reporting month.
    records = [
        saved_record
        for saved_record in records
        if saved_record.get("report_month") != record["report_month"]
    ]

    records.append(record.copy())
    records.sort(key=lambda saved_record: saved_record["report_month"])

    st.session_state[history_key] = records
# Header
st.title("AI Carbon Footprint Tracker")
st.markdown(
    "Estimate the monthly footprint of selected activities, review the largest "
    "contributors, and track changes over time."
)

st.caption(
    "Educational estimate only. Results depend on the activity data and "
    "emission-factor assumptions shown below."
)

# Sidebar
with st.sidebar:
    st.header("Reporting period")
    report_date = st.date_input(
        "Select a date in the reporting month",
        value=date.today().replace(day=1),
    )
    report_month = report_date.strftime("%Y-%m")

    st.divider()
    st.subheader("Current coverage")
    st.write("• Electricity use")
    st.write("• Intracity bus and Indian Rail travel")
    st.write("• Selected food products")

# Activity input sections
st.header("Activity data")
st.write(f"Reporting month: **{report_month}**")

electricity_column, travel_column = st.columns(2)

with electricity_column:
    st.subheader("Home electricity")
    electricity_kwh = st.number_input(
        "Electricity consumed (kWh/month)",
        min_value=0.0,
        value=0.0,
        step=10.0,
        help="Use the kWh amount from your electricity bill when available.",
    )

with travel_column:
    st.subheader("Public transport")
    travel_mode = st.selectbox(
        "Travel mode",
        [
            "City bus (intracity)",
            "Indian Rail (suburban)",
            "Indian Rail (non-suburban)",
        ],
    )
    travel_km = st.number_input(
        "Passenger distance (km/month)",
        min_value=0.0,
        value=0.0,
        step=1.0,
        help="Enter the distance travelled by one passenger.",
    )

st.subheader("Selected food consumption")
st.caption(
    "Enter approximate monthly quantities. Food factors are global averages "
    "and may not represent Indian production."
)

food_col1, food_col2, food_col3, food_col4, food_col5 = st.columns(5)

with food_col1:
    rice_kg = st.number_input(
        "Rice (kg/month)",
        min_value=0.0,
        value=0.0,
        step=0.5,
    )

with food_col2:
    milk_litres = st.number_input(
        "Milk (litres/month)",
        min_value=0.0,
        value=0.0,
        step=1.0,
    )

with food_col3:
    peas_kg = st.number_input(
        "Peas (kg/month)",
        min_value=0.0,
        value=0.0,
        step=0.25,
    )

with food_col4:
    poultry_kg = st.number_input(
        "Poultry meat (kg/month)",
        min_value=0.0,
        value=0.0,
        step=0.25,
    )

with food_col5:
    beef_kg = st.number_input(
        "Beef (kg/month)",
        min_value=0.0,
        value=0.0,
        step=0.25,
    )

# Calculations
electricity_factor = factor_value("grid_electricity")
electricity_emissions = electricity_kwh * electricity_factor

travel_factor_id = {
    "City bus (intracity)": "intracity_bus",
    "Indian Rail (suburban)": "rail_suburban",
    "Indian Rail (non-suburban)": "rail_non_suburban",
}[travel_mode]

travel_factor = factor_value(travel_factor_id)
travel_emissions = travel_km * travel_factor

milk_kg = milk_litres * MILK_KG_PER_LITRE

food_components = {
    "Rice": rice_kg * factor_value("food_rice"),
    "Milk": milk_kg * factor_value("food_milk"),
    "Peas": peas_kg * factor_value("food_peas"),
    "Poultry meat": poultry_kg * factor_value("food_poultry"),
    "Beef": beef_kg * factor_value("food_beef"),
}

food_emissions = sum(food_components.values())

category_emissions = {
    "Home electricity": electricity_emissions,
    "Travel": travel_emissions,
    "Selected food": food_emissions,
}

total_emissions = sum(category_emissions.values())

# Results
st.divider()
st.header("Estimated monthly footprint")

metric1, metric2, metric3 = st.columns(3)
metric1.metric("Total estimate", f"{total_emissions:,.2f} kg CO₂e")
metric2.metric("Electricity", f"{electricity_emissions:,.2f} kg CO₂")
metric3.metric("Travel", f"{travel_emissions:,.2f} kg CO₂")

st.subheader("Category breakdown")

chart_data = pd.DataFrame(
    {
        "Category": list(category_emissions.keys()),
        "Estimated emissions (kg CO₂e)": list(category_emissions.values()),
    }
).set_index("Category")

st.bar_chart(chart_data)

if total_emissions > 0:
    category_shares = {
        category: value / total_emissions * 100
        for category, value in category_emissions.items()
    }

    st.subheader("Contribution by category")
    share_columns = st.columns(3)

    for column, (category, share) in zip(
        share_columns,
        category_shares.items(),
    ):
        column.metric(category, f"{share:.1f}%")

    highest_category = max(category_emissions, key=category_emissions.get)
    highest_value = category_emissions[highest_category]

    st.subheader("Highest estimated contributor")
    st.write(
        f"**{highest_category}** is currently the largest category "
        f"at **{highest_value:,.2f} kg CO₂e**."
    )

    recommendations = {
        "Home electricity": (
            "Review your electricity use and look for practical ways to reduce "
            "unused lighting and standby power."
        ),
        "Travel": (
            "Where practical, consider public transport, walking, or combining "
            "trips to reduce travel activity."
        ),
        "Selected food": (
            "Review the selected food quantities. The estimate only covers the "
            "food products listed in this prototype."
        ),
    }

    st.info(recommendations[highest_category])
else:
    st.info("Enter at least one activity amount above zero to see the breakdown.")
    highest_category = "No activity entered"

# Save current month
current_record = {
    "report_month": report_month,
    "electricity_kwh": electricity_kwh,
    "electricity_factor_kg_co2_per_kwh": electricity_factor,
    "electricity_kg_co2": electricity_emissions,
    "travel_mode": travel_mode,
    "travel_km": travel_km,
    "travel_factor_activity": travel_factor_id,
    "travel_factor_kg_co2_per_passenger_km": travel_factor,
    "travel_kg_co2": travel_emissions,
    "rice_kg": rice_kg,
    "milk_litres": milk_litres,
    "peas_kg": peas_kg,
    "poultry_kg": poultry_kg,
    "beef_kg": beef_kg,
    "food_kg_co2e": food_emissions,
    "total_kg_co2e": total_emissions,
    "highest_category": highest_category,
}

if st.button("Save or update this month", type="primary"):
    save_monthly_record(current_record)
    st.success(f"Monthly record saved for {report_month}.")

# Download current calculation
current_csv = pd.DataFrame([current_record]).to_csv(index=False).encode("utf-8")

st.download_button(
    "Download current month as CSV",
    data=current_csv,
    file_name=f"carbon_footprint_{report_month}.csv",
    mime="text/csv",
)

# History and trend analysis
st.divider()
st.header("Monthly history and trend analysis")

history = load_history()

if history.empty:
    st.info("Save a monthly record to start building your history.")
else:
    history["report_month"] = history["report_month"].astype(str)
    history = history.sort_values("report_month")

    display_columns = [
        "report_month",
        "electricity_kg_co2",
        "travel_kg_co2",
        "food_kg_co2e",
        "total_kg_co2e",
        "highest_category",
    ]
    available_columns = [
        column for column in display_columns if column in history.columns
    ]

    st.dataframe(
        history[available_columns],
        use_container_width=True,
        hide_index=True,
    )

    trend_data = history.copy()
    trend_data["report_month"] = pd.to_datetime(
        trend_data["report_month"],
        format="%Y-%m",
        errors="coerce",
    )
    trend_data["total_kg_co2e"] = pd.to_numeric(
        trend_data["total_kg_co2e"],
        errors="coerce",
    )
    trend_data = trend_data.dropna(
        subset=["report_month", "total_kg_co2e"]
    ).sort_values("report_month")

    if not trend_data.empty:
        total_trend = trend_data.set_index("report_month")[
            ["total_kg_co2e"]
        ]
        st.subheader("Total estimated emissions over time")
        st.line_chart(total_trend)

        if len(trend_data) >= 4:
            x_values = list(range(len(trend_data)))
            y = trend_data["total_kg_co2e"].astype(float).tolist()
            x_mean = sum(x_values) / len(x_values)
            y_mean = sum(y) / len(y)
            slope = sum(
                (x_value - x_mean) * (y_value - y_mean)
                for x_value, y_value in zip(x_values, y)
            ) / sum((x_value - x_mean) ** 2 for x_value in x_values)
            intercept = y_mean - slope * x_mean

            next_month_estimate = max(
                0.0,
                slope * len(trend_data) + intercept,
            )

            st.metric(
                "Experimental next-month trend projection",
                f"{next_month_estimate:,.2f} kg CO₂e",
            )
            st.caption(
                "This is a simple linear trend from your saved monthly records. "
                "It is not a validated forecast."
            )
        else:
            st.info(
                "Save at least four monthly records to see the experimental "
                "trend projection."
            )

    history_csv = history.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download full history as CSV",
        data=history_csv,
        file_name="carbon_footprint_history.csv",
        mime="text/csv",
    )

# Methodology and data sources
st.divider()

with st.expander("Methodology, sources, and limitations"):
    st.write(
        "Emissions are estimated as activity data multiplied by an emission "
        "factor. The electricity and travel factors report CO₂. Food factors "
        "report CO₂-equivalent emissions. CO₂ is included in the combined "
        "total on a one-to-one mass basis."
    )

    st.write(
        "Milk volume is converted to mass using an approximate density of "
        "1.03 kg per litre."
    )

    st.write(
        "The food factors are global averages from a 2018 meta-analysis with "
        "a median reference year around 2010. They are not India-specific and "
        "actual production footprints vary."
    )

    st.write(
        "The bus factor is for intracity bus service only. The rail factors "
        "are older study estimates. Car, motorcycle, other foods, shopping, "
        "waste, and supply-chain activities are not included."
    )

    st.write(
        "Recommendations are transparent rules based on the largest current "
        "category. The trend projection is a simple linear regression and "
        "requires at least four saved months."
    )

    st.subheader("Emission factor register")
    st.dataframe(
        factor_table[
            [
                "activity",
                "factor_value",
                "factor_unit",
                "gas_metric",
                "geography",
                "factor_year",
                "source_name",
                "source_url",
                "notes",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )