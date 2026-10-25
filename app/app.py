"""Quickr dashboard. Launch with: python -m streamlit run app/app.py."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
import plotly.express as px
import streamlit as st
from quickr.config import ANALYTICS, DATASET_ID, GROUPS, TABLES
from quickr.database import connection, read_summary
from ml.features import NUMERIC, CATEGORICAL
from ml.predict import load_model, predict_duration

st.set_page_config(page_title="Quickr | Food Delivery Intelligence", page_icon="Q", layout="wide")

# Keep CSS limited to surfaces and typography not exposed by Streamlit's theme.
st.markdown("""
<style>
    .block-container {max-width: 1440px; padding-top: 2.5rem; padding-bottom: 3rem;}
    h1, h2, h3 {letter-spacing: -0.025em;}
    [data-testid="stCaptionContainer"] {color: #667085;}
    [data-testid="stMetric"] {
        background: #FFFFFF; border: 1px solid #E5E7EB;
        border-radius: 10px; padding: 1rem; min-height: 132px;
    }
    [data-testid="stMetricLabel"] {color: #667085; white-space: normal;}
    [data-testid="stMetricValue"] {font-size: clamp(1.5rem, 2.5vw, 2rem);}
    [data-testid="stForm"], [data-testid="stExpander"] {border-color: #E5E7EB; border-radius: 10px;}
    [data-testid="stSidebar"] {border-right: 1px solid #E5E7EB;}
</style>
""", unsafe_allow_html=True)

# One blue hue, with varied lightness for distinct categories and a restrained lift.
SLATE = "#326496"
BLUE_GRAY = "#8CB2D9"
CHART_COLORS = ["#4080BF", "#24476B", "#6699CC", SLATE,
                BLUE_GRAY, "#3973AC", "#538CC6"]


def style_chart(fig):
    """Shared presentation only; retain each chart's data and hover behavior."""
    fig.update_layout(
        template="plotly_white", colorway=CHART_COLORS,
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        font=dict(family="Arial, sans-serif", size=13, color="#202733"),
        title=dict(font=dict(size=17, color="#202733"), x=0.03),
        margin=dict(l=20, r=20, t=65, b=35),
        legend=dict(title_text="", font=dict(color="#667085")),
    )
    fig.update_xaxes(gridcolor="#E5E7EB", zeroline=False, automargin=True,
                     tickfont=dict(color="#667085"), title_font=dict(color="#667085"))
    fig.update_yaxes(gridcolor="#E5E7EB", zeroline=False, automargin=True,
                     tickfont=dict(color="#667085"), title_font=dict(color="#667085"))
    return fig


@st.cache_data
def read_csv(path, modified):
    return pd.read_csv(path)


def csv_file(path):
    return read_csv(str(path), path.stat().st_mtime_ns)


def summary(name):
    if name not in TABLES:
        raise ValueError("Unknown analytics summary")
    return csv_file(ANALYTICS / f"{name}.csv")


def json_file(name, directory=None):
    directory = directory if directory is not None else ROOT / "models"
    return json.loads((directory / name).read_text(encoding="utf-8"))


@st.cache_resource
def cached_model(backend, modified):
    return load_model(backend)


def bar_chart(frame, category, value, title):
    fig = px.bar(frame, x=category, y=value, color=category,
                 color_discrete_sequence=CHART_COLORS,
                 hover_data=[c for c in ["delivery_count", "total_duration_min"] if c in frame],
                 title=title, template="plotly_white",
                 labels={category: category.replace("_", " ").title(),
                         value: "Average duration (minutes)" if value == "average_duration_min" else "Deliveries"})
    fig.update_layout(showlegend=False)
    st.plotly_chart(style_chart(fig), use_container_width=True)


ANALYSES = {"Traffic": "traffic_summary", "Weather": "weather_summary",
            "City category": "city_summary", "Vehicle": "vehicle_type_summary",
            "Festival": "festival_summary", "Distance band": "distance_band_summary",
            "Order type": "order_type_summary", "Age band": "age_band_summary"}


def analysis_frame(name):
    """Reuse the saved summaries and keep distance intervals in natural order."""
    frame = summary(name)
    if name == "distance_band_summary":
        ordering = {"[0,5) km": 0, "[5,10) km": 1, "[10,15) km": 2,
                    "[15,20) km": 3, "[20,+) km": 4}
        frame = frame.assign(_order=frame.distance_band.map(ordering)).sort_values("_order").drop(columns="_order")
    return frame


def dashboard():
    st.header("Dashboard")
    st.caption("Delivery performance across historical orders.")
    info = summary("overall_summary").iloc[0]
    clean = csv_file(ROOT / "data/processed/quickr_clean.csv")
    cards = st.columns(4 if "distance_km" in clean else 3)
    cards[0].metric("Total Deliveries", f"{int(info.total_deliveries):,}")
    cards[1].metric("Average Delivery Time", f"{info.average_duration_min:.2f} min")
    cards[2].metric("Deliveries Exceeding 30 Minutes", f"{int(info.deliveries_exceeding_threshold):,}",
                    help=f"{info.percent_exceeding_threshold:.2f}% of valid-duration deliveries")
    if "distance_km" in clean:
        distance = pd.to_numeric(clean.distance_km, errors="coerce").mean()
        cards[3].metric("Average Distance", f"{distance:.2f} km" if pd.notna(distance) else "Unavailable")
    st.caption(f"{info.percent_exceeding_threshold:.2f}% exceed the 30-minute analytical threshold; "
               "this is not a confirmed delivery deadline. Distance is straight-line.")
    main_views = [("Traffic", "Traffic vs. Delivery Time"), ("Weather", "Weather vs. Delivery Time"),
                  ("Distance band", "Distance vs. Delivery Time"), ("Festival", "Festival Impact")]
    for index in range(0, len(main_views), 2):
        for column, (label, title) in zip(st.columns(2), main_views[index:index + 2]):
            with column:
                name = ANALYSES[label]
                bar_chart(analysis_frame(name), GROUPS[name], "average_duration_min", title)
    with st.expander("More Analytics"):
        selected = st.selectbox("Additional analysis", ["City category", "Vehicle", "Order type", "Age band"])
        name = ANALYSES[selected]
        frame = analysis_frame(name)
        key = GROUPS.get(name, "order_type")
        if name == "order_type_summary" and st.radio("Order chart style", ["Bar", "Donut"], horizontal=True) == "Donut":
            st.plotly_chart(style_chart(px.pie(
                frame, names="order_type", values="delivery_count", hole=.55,
                color_discrete_sequence=CHART_COLORS, title="Order mix")), use_container_width=True)
        else:
            metric = "delivery_count" if name == "order_type_summary" else "average_duration_min"
            bar_chart(frame, key, metric, selected)
    with st.expander("Summary records and downloads"):
        selected = st.selectbox("Summary", list(ANALYSES))
        name = ANALYSES[selected]
        frame = analysis_frame(name)
        st.dataframe(frame, hide_index=True, width="stretch")
        st.download_button("Download this summary", frame.to_csv(index=False),
                           file_name=f"{name}.csv", mime="text/csv")
    st.caption("Historical PySpark summaries. Unknown groups remain visible; small groups need caution. "
               "Cassandra is optional for this page.")


def prediction(resource):
    metadata = json_file("feature_info.json", resource["directory"])
    st.write("Enter information available when assigning the courier, before pickup. "
             "The model estimates duration in minutes; it does not predict actual lateness.")
    values = {}
    labels = {"distance_km": "Straight-line distance (km)", "delivery_person_age": "Courier age",
              "delivery_person_rating": "Courier rating (0–5)", "vehicle_condition": "Vehicle condition code",
              "order_hour": "Order hour (0–23)", "order_day_of_week": "Weekday (Monday=0, Sunday=6)",
              "traffic": "Traffic", "weather": "Weather", "city": "Settlement category",
              "vehicle_type": "Vehicle type", "festival": "Festival", "order_type": "Order type"}
    bounds = {"distance_km": (0., 100.), "delivery_person_age": (1, 120),
              "delivery_person_rating": (0., 5.), "vehicle_condition": (0, 3),
              "order_hour": (0, 23), "order_day_of_week": (0, 6)}
    with st.form("prediction_inputs"):
        left, right = st.columns(2)
        with left:
            st.subheader("Route & courier")
            st.caption("Distance, courier details and dispatch timing")
            for name in NUMERIC:
                low, high = bounds[name]
                default = metadata["numeric_training_medians"][name]
                default = float(default) if isinstance(low, float) else int(default)
                value = st.number_input(labels[name], min_value=low, max_value=high,
                                        value=default, key=name)
                missing = name != "distance_km" and st.checkbox("Unknown: use training median", key=name + "_unknown")
                values[name] = None if missing else value
        with right:
            st.subheader("Delivery conditions")
            st.caption("Traffic, weather, vehicle and order context")
            for name in CATEGORICAL:
                choices = sorted(set(metadata["category_values"][name] + ["unknown"]))
                values[name] = st.selectbox(labels[name], choices, key=name)
        submitted = st.form_submit_button("Predict Delivery Time", type="primary")
    if submitted:
        try:
            with st.spinner("Estimating delivery time..."):
                result = predict_duration(values, resource)
            st.metric("Estimated delivery duration", f"{result:.1f} minutes")
            st.caption("Estimate only. Traffic changes, road routes and operational delays can change actual duration.")
        except Exception as exc:
            st.error(f"Prediction unavailable: {exc}")
    st.caption("This form uses the model's exact 12 inputs. Unknown numeric inputs use training-fitted medians. "
               "Vehicle-condition codes have no confirmed semantic labels. Distances outside historical coverage are less reliable.")


def database():
    st.subheader("Cassandra database insights")
    st.caption("Reads stored historical PySpark summaries using CQL. These are not live delivery events.")
    table = st.selectbox("Summary table", list(TABLES))
    st.code(f"SELECT * FROM quickr_bda.{table} WHERE dataset_id = '{DATASET_ID}';", language="sql")
    try:
        with st.spinner("Checking local Cassandra…"):
            with connection() as session:
                rows = read_summary(session, table)
        st.caption("Connected to Cassandra · 127.0.0.1:9042 · quickr_bda")
        if not rows:
            st.warning("Connected, but this partition is empty. Run the analytics loader.")
        else:
            frame = pd.DataFrame(rows)
            st.metric("Stored summary rows retrieved", len(frame))
            st.dataframe(frame, hide_index=True, width="stretch")
            if table in GROUPS:
                bar_chart(frame, GROUPS[table], "average_duration_min", "Stored Cassandra summary")
    except Exception as exc:
        st.warning("Cassandra unavailable · other dashboard pages remain usable")
        with st.expander("Connection details and setup commands"):
            st.error(str(exc))
            st.code("cassandra\n# In a second terminal:\npy -2 C:\\cassandra\\bin\\cqlsh.py\n"
                    ".\\.venv-app\\Scripts\\python.exe scripts/init_cassandra.py\n"
                    ".\\.venv-app\\Scripts\\python.exe scripts/load_analytics.py")


def performance(resource):
    st.subheader("Model performance")
    st.caption("Held-out deliveries · active prediction backend")
    metrics = json_file("metrics.json", resource["directory"])
    a, b, c = st.columns(3)
    a.metric("MAE", f"{metrics['mae_min']:.3f} min")
    b.metric("RMSE", f"{metrics['rmse_min']:.3f} min")
    c.metric("R²", f"{metrics['r2']:.4f}")
    st.caption(f"Random Forest · {metrics['train_rows']:,} training rows · {metrics['test_rows']:,} "
             f"held-out rows · 80/20 split · random_state={metrics['random_state']}")
    st.caption(f"Training-median baseline MAE: {metrics['baseline_mae_min']:.3f} minutes. "
               "MAE is average absolute error; RMSE penalizes larger errors; R² compares explained variance against a constant prediction.")
    with st.expander("Model diagnostics and limitations"):
        evaluated = csv_file(resource["directory"] / "test_predictions.csv")
        plotted = evaluated.sample(min(2000, len(evaluated)), random_state=42)
        fig = px.scatter(plotted, x="actual_duration_min", y="predicted_duration_min", opacity=.35,
                         color_discrete_sequence=[CHART_COLORS[0]],
                         title=f"Actual vs predicted ({len(plotted):,} held-out records displayed)",
                         labels={"actual_duration_min": "Actual duration (minutes)",
                                 "predicted_duration_min": "Predicted duration (minutes)"}, template="plotly_white")
        low = min(plotted.actual_duration_min.min(), plotted.predicted_duration_min.min())
        high = max(plotted.actual_duration_min.max(), plotted.predicted_duration_min.max())
        fig.add_shape(type="line", x0=low, y0=low, x1=high, y1=high, line=dict(color=BLUE_GRAY, dash="dash"))
        st.plotly_chart(style_chart(fig), use_container_width=True)
        importance = csv_file(resource["directory"] / "feature_importance.csv").head(12).sort_values("importance")
        st.plotly_chart(style_chart(px.bar(
            importance, x="importance", y="feature", orientation="h", color="feature",
            color_discrete_sequence=CHART_COLORS, title="Top transformed feature importances",
            labels={"importance": "Feature importance", "feature": "Transformed feature"}
        ).update_layout(showlegend=False)), use_container_width=True)
        st.info("Preprocessing was fitted on training rows only. The random test split can share couriers and "
                "restaurants with training and is not evidence of performance on future dates or new locations.")


def quality():
    st.subheader("Data quality and provenance")
    raw = csv_file(ROOT / "data/raw/food_delivery.csv")
    clean = csv_file(ROOT / "data/processed/quickr_clean.csv")
    a, b, c = st.columns(3)
    a.metric("Raw records", f"{len(raw):,}")
    b.metric("Clean records", f"{len(clean):,}")
    c.metric("Removed records", f"{len(raw) - len(clean):,}")
    st.write("Whitespace and missing placeholders were normalized. Unusable GPS routes were excluded; "
             "numeric/time nulls were preserved, categories use unknown, and unusual ages have review flags. "
             "The ML pipeline fills numeric nulls using training-only medians.")
    missing = clean.isna().sum().rename_axis("column").reset_index(name="missing_values")
    st.dataframe(missing[missing.missing_values > 0], hide_index=True, width="stretch")
    with st.expander("Full cleaning decisions, removal reasons and limitations"):
        st.markdown((ROOT / "reports/data_cleaning.md").read_text(encoding="utf-8"))


def prediction_page():
    st.header("Delivery Time Prediction")
    st.caption("Estimate delivery duration from information available at dispatch.")
    # Spark is initialized only on this page, once per process; never by other pages.
    fallback = st.checkbox("Use scikit-learn fallback (preserved baseline)", value=False)
    backend = "sklearn" if fallback else "spark"
    directory = ROOT / ("models/sklearn_backup" if fallback else "models/spark")
    try:
        message = "Loading preserved fallback..." if fallback else "Loading Spark model; the first load can take several minutes..."
        with st.spinner(message):
            resource = cached_model(backend, (directory / "metrics.json").stat().st_mtime_ns)
    except Exception as exc:
        st.warning("The selected prediction backend is unavailable. "
                   "If Spark failed, select the explicitly labeled scikit-learn fallback above.")
        with st.expander("Backend initialization details"):
            st.write(str(exc))
        return
    st.caption("Active backend: " + ("scikit-learn fallback (preserved baseline)" if fallback else "PySpark MLlib Random Forest (primary)"))
    prediction(resource)
    st.divider()
    st.caption("Random Forest Regression estimates delivery duration from dispatch-time inputs. Metrics below belong to the active backend.")
    performance(resource)


def system_insights():
    st.header("Data & System Insights")
    st.caption("Dataset → Preprocessing → PySpark → Cassandra → Streamlit")
    with st.expander("Prediction pipeline"):
        st.code("Preprocessing → cleaned dataset → ML pipeline → Streamlit prediction", language=None)
    quality()
    st.divider()
    database()


st.sidebar.title("Quickr")
st.sidebar.caption("Food delivery intelligence")
pages = {"Dashboard": dashboard, "Delivery Time Prediction": prediction_page,
         "Data & System Insights": system_insights}
page = st.sidebar.radio("Navigate", list(pages))
st.sidebar.divider()
st.sidebar.caption("Historical summaries · Local Cassandra\nRDD MapReduce · Random Forest")
try:
    pages[page]()
except Exception as exc:
    st.error(f"This page could not load: {type(exc).__name__}: {exc}")
    st.info("Check the project data and model artifacts. See README.md for generation commands.")
