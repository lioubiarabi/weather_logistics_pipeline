import os
import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine
import plotly.express as px
import plotly.graph_objects as go

# ------------------------------------------------------------------------------
# 1. Page Configuration & Custom CSS
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Weather Logistics Dashboard",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern Custom CSS for Logistics Theme
st.markdown("""
    <style>
        .main-header {
            font-size: 2.2rem;
            font-weight: 700;
            color: #1E293B;
            margin-bottom: 0.2rem;
        }
        .sub-header {
            font-size: 1.05rem;
            color: #64748B;
            margin-bottom: 1.5rem;
        }
        .metric-card {
            background-color: #F8FAFC;
            border-left: 5px solid #3B82F6;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .hazard-box {
            padding: 0.85rem 1rem;
            border-radius: 6px;
            margin-bottom: 0.6rem;
            font-size: 0.95rem;
        }
        .hazard-red {
            background-color: #FEF2F2;
            border-left: 4px solid #EF4444;
            color: #991B1B;
        }
        .hazard-orange {
            background-color: #FFFBEB;
            border-left: 4px solid #F59E0B;
            color: #92400E;
        }
        .hazard-green {
            background-color: #F0FDF4;
            border-left: 4px solid #10B981;
            color: #065F46;
        }
    </style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# 2. Database Connection & Data Fetching
# ------------------------------------------------------------------------------
@st.cache_resource
def get_engine():
    return create_engine("postgresql://postgres:admin@localhost:5433/weather_logistics")


@st.cache_data(ttl=300)
def load_forecast_data():
    engine = get_engine()
    query = """
        SELECT 
            w.city_name,
            w.date,
            w.risk_score,
            w.risk_level,
            w.temp_max,
            w.temp_min,
            w.wind_gusts,
            w.precip_sum,
            w.temp_category,
            w.precip_category,
            w.wind_category,
            w.updated_at,
            COALESCE(c.lat, CASE WHEN w.city_name IN ('Fs', 'Fès') THEN 34.0433 END) AS lat,
            COALESCE(c.lng, CASE WHEN w.city_name IN ('Fs', 'Fès') THEN -5.0033 END) AS lon,
            COALESCE(c.admin_name, CASE WHEN w.city_name IN ('Fs', 'Fès') THEN 'Fès-Meknès' ELSE c.admin_name END) AS admin_name,
            c.population
        FROM weather_forecasts w
        LEFT JOIN cities c ON w.city_name = c.name
        ORDER BY w.date ASC, w.city_name ASC
    """
    df = pd.read_sql(query, engine)
    
    # Harmonize city names
    df['city_display'] = df['city_name'].replace({'Fs': 'Fès'})
    df['date'] = pd.to_datetime(df['date']).dt.date
    return df


try:
    df_raw = load_forecast_data()
except Exception as e:
    st.error(f"❌ Could not connect to PostgreSQL database on port 5433: {e}")
    st.info("Please ensure the PostgreSQL container is running (`docker-compose up -d`).")
    st.stop()


# ------------------------------------------------------------------------------
# 3. Sidebar Filtering
# ------------------------------------------------------------------------------
st.sidebar.image("https://img.icons8.com/isometric/100/cargo-ship.png", width=70)
st.sidebar.title("Fleet Operations Control")
st.sidebar.markdown("---")

# Date Filter
all_dates = sorted(df_raw['date'].unique())
selected_date = st.sidebar.selectbox("📅 Select Forecast Date", ["All Dates"] + [d.strftime("%Y-%m-%d") for d in all_dates])

# City Multi-Select
all_cities = sorted(df_raw['city_display'].unique())
selected_cities = st.sidebar.multiselect("🏙️ Filter by City", all_cities, default=all_cities)

# Risk Level Filter
all_risks = ["Low", "Medium", "High"]
selected_risks = st.sidebar.multiselect("⚠️ Filter by Risk Level", all_risks, default=all_risks)

# Emergency Filter
hazard_only = st.sidebar.checkbox("🚨 Show Severe Weather Only (Wind > 50 or Temp ≥ 35)", value=False)

# Apply filters
df = df_raw.copy()
if selected_date != "All Dates":
    target_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
    df = df[df['date'] == target_date]

if selected_cities:
    df = df[df['city_display'].isin(selected_cities)]

if selected_risks:
    df = df[df['risk_level'].isin(selected_risks)]

if hazard_only:
    df = df[(df['wind_gusts'] >= 50) | (df['temp_max'] >= 35) | (df['risk_score'] >= 50)]

st.sidebar.markdown("---")
st.sidebar.success(f"🟢 Database Connected (Port 5433)\n\n**{len(df)}** forecast records loaded.")
if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()


# ------------------------------------------------------------------------------
# 4. Header & High-Level Operational KPIs
# ------------------------------------------------------------------------------
st.markdown('<div class="main-header">🚚 Morocco Weather-Driven Logistics Intelligence</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Real-time weather analytics, freight hazard monitoring, and safe transit route optimization</div>', unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    monitored_cities = df['city_display'].nunique()
    st.metric("Monitored Cities", f"{monitored_cities}", help="Unique logistics nodes in current view")

with col2:
    avg_risk = df['risk_score'].mean() if not df.empty else 0
    st.metric("Average Risk Score", f"{avg_risk:.1f}/100", delta=None)

with col3:
    max_wind = df['wind_gusts'].max() if not df.empty else 0
    max_wind_city = df.loc[df['wind_gusts'].idxmax()]['city_display'] if not df.empty else "N/A"
    st.metric("Peak Wind Gust", f"{max_wind:.1f} km/h", f"{max_wind_city}", delta_color="inverse")

with col4:
    max_temp = df['temp_max'].max() if not df.empty else 0
    max_temp_city = df.loc[df['temp_max'].idxmax()]['city_display'] if not df.empty else "N/A"
    st.metric("Peak Temperature", f"{max_temp:.1f} °C", f"{max_temp_city}", delta_color="inverse")

with col5:
    reefer_alerts = len(df[df['temp_max'] >= 35])
    st.metric("Reefer Cooling Alerts", f"{reefer_alerts}", "Temp ≥ 35°C", delta_color="inverse" if reefer_alerts > 0 else "normal")

st.markdown("<br>", unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# 5. Interactive Tabs
# ------------------------------------------------------------------------------
tab_map, tab_trends, tab_alerts, tab_regions, tab_data = st.tabs([
    "🗺️ Geospatial Risk Map",
    "📈 Multi-City Weather Trends",
    "⚠️ Logistics Hazard Alerts",
    "📊 Regional Risk Profiles",
    "📋 Data Explorer & Export"
])


# ------------------------------------------------------------------------------
# Tab 1: Geospatial Fleet Map
# ------------------------------------------------------------------------------
with tab_map:
    st.subheader("Morocco Logistics Network Hazard Map")
    st.caption("Circle size represents Weather Risk Score. Circle color reflects Risk Level category.")

    if not df.empty:
        # Prepare map data
        map_df = df.copy()
        map_df['marker_size'] = map_df['risk_score'].apply(lambda x: max(x, 15))
        
        color_map = {
            'Low': '#10B981',      # Green
            'Medium': '#F59E0B',   # Amber
            'High': '#EF4444'       # Red
        }

        map_func = getattr(px, 'scatter_map', getattr(px, 'scatter_mapbox', None))
        map_kwargs = {
            "lat": "lat",
            "lon": "lon",
            "size": "marker_size",
            "color": "risk_level",
            "color_discrete_map": color_map,
            "hover_name": "city_display",
            "hover_data": {
                "lat": False,
                "lon": False,
                "marker_size": False,
                "date": True,
                "risk_score": True,
                "temp_max": ":.1f °C",
                "wind_gusts": ":.1f km/h",
                "precip_sum": ":.1f mm",
                "admin_name": True
            },
            "zoom": 5.3,
            "center": {"lat": 31.7917, "lon": -7.0926},
            "height": 540,
            "title": "Logistics Transit Nodes Risk Status"
        }
        if hasattr(px, 'scatter_map'):
            map_kwargs["map_style"] = "open-street-map"
        else:
            map_kwargs["mapbox_style"] = "open-street-map"

        fig_map = map_func(map_df, **map_kwargs)
        fig_map.update_layout(
            margin={"r": 0, "t": 40, "l": 0, "b": 0},
            legend_title_text="Risk Level"
        )
        st.plotly_chart(fig_map, use_container_width=True)
    else:
        st.warning("No data matches the current filter selection.")


# ------------------------------------------------------------------------------
# Tab 2: Forecast Trends
# ------------------------------------------------------------------------------
with tab_trends:
    st.subheader("Forecast Time-Series Analysis")
    
    col_metric, col_dummy = st.columns([2, 4])
    with col_metric:
        metric_choice = st.selectbox(
            "Select Metric to Plot",
            ["risk_score", "temp_max", "wind_gusts", "precip_sum"],
            format_func=lambda x: {
                "risk_score": "Weather Risk Score (0-100)",
                "temp_max": "Max Temperature (°C)",
                "wind_gusts": "Wind Gusts (km/h)",
                "precip_sum": "Precipitation (mm)"
            }[x]
        )

    if not df.empty:
        metric_labels = {
            "risk_score": "Risk Score",
            "temp_max": "Max Temperature (°C)",
            "wind_gusts": "Wind Gusts (km/h)",
            "precip_sum": "Precipitation (mm)"
        }
        
        fig_trend = px.line(
            df,
            x="date",
            y=metric_choice,
            color="city_display",
            markers=True,
            title=f"7-Day Forecast: {metric_labels[metric_choice]} by City",
            labels={"date": "Forecast Date", metric_choice: metric_labels[metric_choice], "city_display": "City"},
            height=450
        )
        fig_trend.update_layout(
            hovermode="x unified",
            xaxis=dict(tickformat="%b %d", dtick=86400000)
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.warning("No data available for trend chart.")


# ------------------------------------------------------------------------------
# Tab 3: Logistics Hazard Alerts
# ------------------------------------------------------------------------------
with tab_alerts:
    st.subheader("Logistics Dispatcher Warnings & Action Recommendations")
    
    col_alert1, col_alert2 = st.columns(2)
    
    with col_alert1:
        st.markdown("#### 💨 Wind Hazard & Trailer Rollover Risk")
        wind_hazards = df[df['wind_gusts'] >= 50].sort_values(by='wind_gusts', ascending=False)
        if not wind_hazards.empty:
            for _, row in wind_hazards.iterrows():
                level_class = "hazard-red" if row['wind_gusts'] >= 60 else "hazard-orange"
                st.markdown(f"""
                    <div class="hazard-box {level_class}">
                        <b>🚨 {row['city_display']} ({row['date']}):</b> Wind Gusts at <b>{row['wind_gusts']:.1f} km/h</b>.<br>
                        <i>Logistics Advisory:</i> {'High rollover hazard for empty / high-profile trailers. Consider route delay.' if row['wind_gusts'] >= 60 else 'Speed restrictions advised.'}
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<div class="hazard-box hazard-green">✅ No severe wind hazards detected in selected scope (All wind gusts < 50 km/h).</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 🌧️ Precipitation & Hydroplaning Risk")
        rain_hazards = df[df['precip_sum'] > 5].sort_values(by='precip_sum', ascending=False)
        if not rain_hazards.empty:
            for _, row in rain_hazards.iterrows():
                st.markdown(f"""
                    <div class="hazard-box hazard-orange">
                        <b>🌧️ {row['city_display']} ({row['date']}):</b> {row['precip_sum']:.1f} mm precipitation ({row['precip_category']}).<br>
                        <i>Logistics Advisory:</i> Wet pavement braking distance increased.
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<div class="hazard-box hazard-green">✅ Dry operating conditions across all selected routes.</div>', unsafe_allow_html=True)

    with col_alert2:
        st.markdown("#### 🌡️ Cold Chain Quality Assurance (Reefer Alert)")
        heat_hazards = df[df['temp_max'] >= 35].sort_values(by='temp_max', ascending=False)
        if not heat_hazards.empty:
            for _, row in heat_hazards.iterrows():
                st.markdown(f"""
                    <div class="hazard-box hazard-red">
                        <b>🔥 {row['city_display']} ({row['date']}):</b> Max Temp <b>{row['temp_max']:.1f} °C</b> ({row['temp_category']}).<br>
                        <i>Logistics Advisory:</i> Mandatory refrigerated units (reefers) required for pharmaceuticals and food.
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<div class="hazard-box hazard-green">✅ Moderate temperatures. Standard ambient transit acceptable.</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 🟢 Optimal Green-Flag Transit Windows")
        safe_windows = df[(df['risk_level'] == 'Low') & (df['wind_gusts'] < 40) & (df['precip_sum'] == 0)]
        if not safe_windows.empty:
            st.markdown(f"""
                <div class="hazard-box hazard-green">
                    <b>✅ {len(safe_windows)} Optimal Route Windows Available:</b><br>
                    Dry roads, calm winds (&lt; 40 km/h), and low overall risk. Best candidates for high-priority shipments.
                </div>
            """, unsafe_allow_html=True)
            safe_display = safe_windows[['date', 'city_display', 'admin_name', 'temp_max', 'wind_gusts']].head(5)
            st.dataframe(safe_display.rename(columns={'city_display': 'City', 'admin_name': 'Region', 'temp_max': 'Temp (°C)', 'wind_gusts': 'Wind (km/h)'}), hide_index=True, use_container_width=True)


# ------------------------------------------------------------------------------
# Tab 4: Regional Risk Profiles
# ------------------------------------------------------------------------------
with tab_regions:
    st.subheader("Regional Vulnerability Breakdown")
    
    if not df.empty:
        col_reg1, col_reg2 = st.columns(2)
        
        with col_reg1:
            # Average Risk by Region
            region_agg = df.groupby('admin_name').agg({
                'risk_score': 'mean',
                'wind_gusts': 'max',
                'temp_max': 'max'
            }).reset_index().sort_values(by='risk_score', ascending=False)
            
            fig_reg = px.bar(
                region_agg,
                x='admin_name',
                y='risk_score',
                color='risk_score',
                color_continuous_scale='Reds',
                title="Average Weather Risk Score by Administrative Region",
                labels={'admin_name': 'Region', 'risk_score': 'Avg Risk Score'},
                height=420
            )
            fig_reg.update_layout(xaxis_tickangle=-30)
            st.plotly_chart(fig_reg, use_container_width=True)

        with col_reg2:
            # Risk Level Distribution
            fig_pie = px.pie(
                df,
                names='risk_level',
                title="Proportion of Risk Categories Across Fleet Network",
                color='risk_level',
                color_discrete_map={'Low': '#10B981', 'Medium': '#F59E0B', 'High': '#EF4444'},
                hole=0.4,
                height=420
            )
            st.plotly_chart(fig_pie, use_container_width=True)


# ------------------------------------------------------------------------------
# Tab 5: Data Explorer & Export
# ------------------------------------------------------------------------------
with tab_data:
    st.subheader("Forecasts Master Table")
    
    display_cols = [
        'date', 'city_display', 'admin_name', 'risk_score', 'risk_level',
        'temp_max', 'temp_min', 'temp_category',
        'wind_gusts', 'wind_category', 'precip_sum', 'precip_category'
    ]
    
    df_export = df[display_cols].rename(columns={
        'city_display': 'City',
        'admin_name': 'Region',
        'date': 'Date',
        'risk_score': 'Risk Score',
        'risk_level': 'Risk Level',
        'temp_max': 'Max Temp (°C)',
        'temp_min': 'Min Temp (°C)',
        'temp_category': 'Temp Category',
        'wind_gusts': 'Wind Gust (km/h)',
        'wind_category': 'Wind Category',
        'precip_sum': 'Precipitation (mm)',
        'precip_category': 'Rain Category'
    })
    
    st.dataframe(
        df_export,
        use_container_width=True,
        hide_index=True
    )
    
    csv_data = df_export.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv_data,
        file_name=f"weather_logistics_export_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
