"""
dashboard/app.py  —  City Congestion Tracker Dashboard
Run: streamlit run app.py

Expects env var (or Streamlit secret): API_BASE_URL
"""

import os
import requests
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────────────
def get_api_base():
    if "API_BASE_URL" in os.environ:
        return os.environ["API_BASE_URL"]
    try:
        if "API_BASE_URL" in st.secrets:
            return st.secrets["API_BASE_URL"]
    except Exception:
        pass
    return "http://localhost:8000"

API_BASE = get_api_base()

st.set_page_config(
    page_title="City Congestion Tracker",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 2rem; }
.block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ── API helpers ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def fetch(path: str, **params):
    try:
        r = requests.get(f"{API_BASE}{path}", params={k: v for k, v in params.items() if v is not None}, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error ({path}): {e}")
        return None

def post_json(path: str, payload: dict):
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=25)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error ({path}): {e}")
        return None

SEV_ICON  = {"severe": "🔴", "high": "🟠", "moderate": "🟡", "low": "🟢"}
SEV_COLOR = {"severe": "#d32f2f", "high": "#f57c00", "moderate": "#fbc02d", "low": "#388e3c"}

# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🚦 Congestion Tracker")
    st.caption("City Transportation Authority")
    st.divider()

    page = st.radio("Navigate", ["📍 Live Overview", "📈 Historical Trends", "🤖 AI Summary"])

    st.divider()
    locations_raw = fetch("/locations") or []
    zones_available = ["All"] + sorted(set(l["zone"] for l in locations_raw))
    zone_filter = st.selectbox("Filter by Zone", zones_available)
    hours_back  = st.slider("History window (hours)", 1, 168, 24)
    st.divider()
    st.caption(f"API: `{API_BASE}`")
    st.caption(f"Updated: {datetime.now().strftime('%H:%M:%S')}")

selected_zone = None if zone_filter == "All" else zone_filter

# ── Page: Live Overview ─────────────────────────────────────────────────────────
if page == "📍 Live Overview":
    st.title("📍 Live Congestion Overview")

    current = fetch("/congestion/current", zone=selected_zone)

    if current and current.get("data"):
        df = pd.DataFrame(current["data"])

        # Flatten locations join
        df["loc_name"] = df["locations"].apply(lambda x: x["name"]  if isinstance(x, dict) else "")
        df["zone"]     = df["locations"].apply(lambda x: x["zone"]  if isinstance(x, dict) else "")
        df["lat"]      = df["locations"].apply(lambda x: x.get("lat") if isinstance(x, dict) else None)
        df["lng"]      = df["locations"].apply(lambda x: x.get("lng") if isinstance(x, dict) else None)

        # ── KPI strip ──
        c1, c2, c3, c4 = st.columns(4)
        avg_lvl       = df["congestion_level"].mean()
        severe_count  = (df["severity"] == "severe").sum()
        high_count    = (df["severity"] == "high").sum()
        worst_name    = df.loc[df["congestion_level"].idxmax(), "loc_name"]

        c1.metric("📊 Avg Congestion Index", f"{avg_lvl:.1f}")
        c2.metric("🔴 Severe Spots",  int(severe_count))
        c3.metric("🟠 High Spots",    int(high_count))
        c4.metric("⚠️ Worst Spot",   worst_name[:24] + "…" if len(worst_name) > 24 else worst_name)

        st.divider()

        col_map, col_rank = st.columns([1.6, 1])

        # ── Map ──
        with col_map:
            st.subheader("🗺️ Congestion Map")
            map_df = df.dropna(subset=["lat", "lng"]).copy()
            if not map_df.empty:
                fig_map = px.scatter_mapbox(
                    map_df,
                    lat="lat", lon="lng",
                    color="severity",
                    size="congestion_level",
                    size_max=22,
                    hover_name="loc_name",
                    hover_data={"congestion_level": ":.1f", "zone": True,
                                "speed_mph": ":.1f", "vehicle_volume": True},
                    color_discrete_map=SEV_COLOR,
                    zoom=12, height=430,
                    mapbox_style="carto-positron",
                )
                fig_map.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0},
                                      legend_title="Severity")
                st.plotly_chart(fig_map, use_container_width=True)
            else:
                st.info("No lat/lng data available for map.")

        # ── Ranked list ──
        with col_rank:
            st.subheader("🏆 Current Rankings")
            for _, row in df.sort_values("congestion_level", ascending=False).iterrows():
                icon = SEV_ICON.get(row["severity"], "⚪")
                speed_str = f"{row['speed_mph']:.0f} mph" if pd.notna(row.get("speed_mph")) else "N/A"
                st.markdown(
                    f"{icon} **{row['loc_name']}**  \n"
                    f"&nbsp;&nbsp;Index: `{row['congestion_level']:.1f}` &nbsp;·&nbsp; "
                    f"{row['zone']} &nbsp;·&nbsp; {speed_str}"
                )

        # ── Bar chart ──
        st.subheader("📊 Congestion Index by Location")
        df_sorted = df.sort_values("congestion_level", ascending=True)
        fig_bar = px.bar(
            df_sorted, x="congestion_level", y="loc_name",
            color="severity", color_discrete_map=SEV_COLOR,
            orientation="h", height=400,
            labels={"congestion_level": "Congestion Index", "loc_name": "Location"},
        )
        fig_bar.update_layout(showlegend=True, margin={"t": 0, "b": 0})
        st.plotly_chart(fig_bar, use_container_width=True)

    else:
        st.info("No live readings found. Make sure the API is running and the database has recent data.")
        st.code(f"API endpoint: {API_BASE}/congestion/current")


# ── Page: Historical Trends ─────────────────────────────────────────────────────
elif page == "📈 Historical Trends":
    st.title("📈 Historical Congestion Trends")

    tab1, tab2, tab3 = st.tabs(["📌 By Location", "🏙️ By Zone", "🕐 By Hour of Day"])

    # ── By Location ──
    with tab1:
        if locations_raw:
            loc_map = {l["name"]: l["id"] for l in locations_raw}
            sel_name = st.selectbox("Select location", list(loc_map.keys()))
            sel_id   = loc_map[sel_name]

            hist = fetch("/congestion/history",
                         location_id=sel_id,
                         hours_back=hours_back,
                         limit=2000)

            if hist and hist.get("data"):
                df_h = pd.DataFrame(hist["data"])
                df_h["timestamp"] = pd.to_datetime(df_h["timestamp"])
                df_h = df_h.sort_values("timestamp")

                fig_line = px.line(
                    df_h, x="timestamp", y="congestion_level",
                    color_discrete_sequence=["#1565C0"],
                    labels={"congestion_level": "Congestion Index", "timestamp": "Time"},
                    title=f"{sel_name} — last {hours_back}h",
                )
                # Severity bands (adjusted for your data range)
                fig_line.add_hrect(y0=12,  y1=df_h["congestion_level"].max()+1,
                                   fillcolor="red",    opacity=0.08, line_width=0, annotation_text="Severe")
                fig_line.add_hrect(y0=8,   y1=12,
                                   fillcolor="orange", opacity=0.08, line_width=0, annotation_text="High")
                fig_line.add_hrect(y0=4,   y1=8,
                                   fillcolor="yellow", opacity=0.06, line_width=0, annotation_text="Moderate")
                fig_line.update_layout(height=380)
                st.plotly_chart(fig_line, use_container_width=True)

                c1, c2, c3 = st.columns(3)
                c1.metric("Avg Index",  f"{df_h['congestion_level'].mean():.2f}")
                c2.metric("Peak Index", f"{df_h['congestion_level'].max():.2f}")
                c3.metric("Readings",   len(df_h))
            else:
                st.info("No history found for this location in the selected window.")

    # ── By Zone ──
    with tab2:
        stats_zone = fetch("/congestion/stats", hours_back=hours_back, group_by="zone")
        if stats_zone and stats_zone.get("data"):
            df_z = pd.DataFrame(stats_zone["data"])
            fig_z = px.bar(
                df_z, x="group", y="avg_congestion",
                color="severity", color_discrete_map=SEV_COLOR,
                error_y=None,
                labels={"group": "Zone", "avg_congestion": "Avg Congestion Index"},
                title=f"Average congestion by zone — last {hours_back}h",
                height=380,
            )
            st.plotly_chart(fig_z, use_container_width=True)
            st.dataframe(
                df_z[["group", "avg_congestion", "max_congestion", "reading_count", "severity"]],
                use_container_width=True, hide_index=True
            )

    # ── By Hour ──
    with tab3:
        stats_hour = fetch("/congestion/stats",
                           hours_back=min(hours_back, 168),
                           group_by="hour")
        if stats_hour and stats_hour.get("data"):
            df_hr = pd.DataFrame(stats_hour["data"]).sort_values("group")
            fig_hr = px.bar(
                df_hr, x="group", y="avg_congestion",
                color="avg_congestion",
                color_continuous_scale=["#388e3c", "#fbc02d", "#f57c00", "#d32f2f"],
                labels={"group": "Hour of Day", "avg_congestion": "Avg Congestion Index"},
                title=f"Congestion by hour of day — last {min(hours_back,168)}h",
                height=380,
            )
            fig_hr.update_coloraxes(showscale=False)
            st.plotly_chart(fig_hr, use_container_width=True)
            st.caption("Typical peaks: 7–9 AM (morning rush) and 5–7 PM (evening rush)")


# ── Page: AI Summary ────────────────────────────────────────────────────────────
elif page == "🤖 AI Summary":
    st.title("🤖 AI Congestion Analyst")
    st.caption("Powered by OpenAI GPT-4o-mini")

    col_l, col_r = st.columns([1, 2])

    with col_l:
        st.subheader("Query parameters")
        ai_hours = st.slider("Hours of data to analyse", 1, 72, 24)
        ai_zone  = st.selectbox("Zone focus", ["All zones"] + [z for z in zones_available if z != "All"])
        ai_zone_param = None if ai_zone == "All zones" else ai_zone

        loc_options = ["All locations"] + [l["name"] for l in locations_raw]
        ai_loc = st.selectbox("Location focus (optional)", loc_options)
        ai_loc_id = None
        if ai_loc != "All locations":
            ai_loc_id = next((l["id"] for l in locations_raw if l["name"] == ai_loc), None)

        st.divider()
        generate = st.button("🧠 Generate AI Summary", type="primary", use_container_width=True)

    with col_r:
        st.subheader("AI-generated report")

        if generate:
            with st.spinner("Fetching data and generating analysis…"):
                payload = {
                    "hours_back":  ai_hours,
                    "zone":        ai_zone_param,
                    "location_id": ai_loc_id,
                }
                result = post_json("/congestion/summary", payload)

            if result and result.get("summary"):
                st.success("Analysis complete!")
                st.markdown(f"""
<div style="background:#f0f4ff;padding:20px;border-radius:10px;
            border-left:4px solid #1565C0;font-size:1.05rem;line-height:1.8">
{result['summary']}
</div>
""", unsafe_allow_html=True)

                st.divider()
                ctx = result.get("data_context", {})
                st.subheader("📊 Data snapshot used")
                c1, c2, c3 = st.columns(3)
                c1.metric("Readings analysed",  ctx.get("total_readings", "—"))
                c2.metric("Avg congestion index", ctx.get("avg_congestion", "—"))
                c3.metric("Severe count", ctx.get("severity_breakdown", {}).get("severe", 0))

                if ctx.get("top_locations"):
                    st.markdown("**Top congested locations:**")
                    for i, (name, avg, peak) in enumerate(ctx["top_locations"][:6], 1):
                        icon = SEV_ICON.get(
                            "severe" if avg >= 12 else "high" if avg >= 8
                            else "moderate" if avg >= 4 else "low", "⚪"
                        )
                        st.markdown(f"{i}. {icon} **{name}** — avg `{avg}`, peak `{peak}`")
        else:
            st.info("Set parameters on the left and click **Generate AI Summary**.")
            st.markdown("""
**What the AI analyst can tell you:**
- 🔍 Which intersections are currently worst
- 📅 How today compares to historical patterns
- ⏰ Peak hour breakdown for your selected zone
- 🛣️ Which routes to avoid and suggested alternatives
            """)
