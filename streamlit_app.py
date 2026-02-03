import streamlit as st
import pandas as pd
import datetime
import os
import html
import copy
import re

# --- Page Configuration (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(page_title="CR-Score Dashboard (Insurance View)", layout="wide")

# --- App Configuration ---

# --- Define the specific categories for this version of the dashboard ---
ALLOWED_IMPACT_CATEGORIES = ['GL Insurance', 'WC Insurance', 'BR Insurance', 'CA Insurance']

PHASE_PROCESS_MAPPING = {
    "bidding": ["bidreview", "estimating", "compliance", "bidresults"],
    "preconstruction": ["financialSetup", "designReview", "compliance", "subcontractorPlanning"],
    "construction": ["operations", "quality", "safety", "financial", "communication"],
    "closeout": ["finalDocumentation", "punchlistCompletion", "financialReconciliation", "clientHandover"]
}

PROCESS_DISPLAY_NAMES = {
    "bidreview": "Bid Review",
    "bidresults": "Bid Results",
    "finalDocumentation": "Final Documentation & As-Builts",
    "punchlistCompletion": "Punch List Completion",
    "financialReconciliation": "Financial Reconciliation",
    "clientHandover": "Client Handover & Satisfaction"
}

PHASE_INFO = {
    "bidding": {"title": "Bidding Phase Summary", "score_col": "phaseScore_bidding"},
    "preconstruction": {"title": "Preconstruction Phase Summary", "score_col": "phaseScore_precon"},
    "construction": {"title": "Construction Phase Summary", "score_col": "phaseScore_construction"},
    "closeout": {"title": "Closeout Phase Summary", "score_col": "phaseScore_closeout"}
}

# --- FIX: Added the missing PHASE_DESCRIPTIONS dictionary ---
PHASE_DESCRIPTIONS = {
    "bidding": "Represents the adoption of Best Practices for all KPIs across 4 key processes of the Bidding Phase.",
    "preconstruction": "Represents the adoption of Best Practices for all KPIs across 4 key processes of the Preconstruction Phase.",
    "construction": "Represents the adoption of Best Practices for all KPIs across 5 key processes of the Construction Phase.",
    "closeout": "Represents the adoption of Best Practices for all KPIs across 4 key processes of the Closeout Phase."
}


# --- Filter the configuration dictionaries to match the allowed categories ---
IMPACT_CATEGORY_CONFIG = {
    "GL Insurance": {"multiplier": 0.60, "suffix": "lower risk"},
    "WC Insurance": {"multiplier": 0.60, "suffix": "lower risk"},
    "BR Insurance": {"multiplier": 0.40, "suffix": "lower risk"},
    "CA Insurance": {"multiplier": 0.30, "suffix": "lower risk"}
}

PHASE_IMPACT_CONFIG = {
    "bidding": {
        "GL Insurance": {"multiplier": 0.06, "suffix": "lower risk"},
        "WC Insurance": {"multiplier": 0.03, "suffix": "lower risk"},
        "BR Insurance": {"multiplier": 0.015, "suffix": "lower risk"},
        "CA Insurance": {"multiplier": 0.02, "suffix": "lower risk"}
    },
    "preconstruction": {
        "GL Insurance": {"multiplier": 0.15, "suffix": "lower risk"},
        "WC Insurance": {"multiplier": 0.12, "suffix": "lower risk"},
        "BR Insurance": {"multiplier": 0.075, "suffix": "lower risk"},
        "CA Insurance": {"multiplier": 0.08, "suffix": "lower risk"}
    },
    "construction": {
        "GL Insurance": {"multiplier": 0.30, "suffix": "lower risk"},
        "WC Insurance": {"multiplier": 0.42, "suffix": "lower risk"},
        "BR Insurance": {"multiplier": 0.18, "suffix": "lower risk"},
        "CA Insurance": {"multiplier": 0.24, "suffix": "lower risk"}
    },
    "closeout": {
        "GL Insurance": {"multiplier": 0.09, "suffix": "lower risk"},
        "WC Insurance": {"multiplier": 0.03, "suffix": "lower risk"},
        "BR Insurance": {"multiplier": 0.03, "suffix": "lower risk"},
        "CA Insurance": {"multiplier": 0.06, "suffix": "lower risk"}
    }
}


# --- UI Helper Functions ---
def horizontal_risk_bar_html(score, height='1.25rem', font_size='0.9rem', top_offset='-1.3rem', width_percentage=100):
    score = int(score) if pd.notna(score) else 0
    indicator_position = f"{score}%"
    gradient = "linear-gradient(to right, #ef4444 0%, #facc15 50%, #16a34a 100%)"
    score_color = "black"
    html_content = f"""
    <div style="width: {width_percentage}%; position: relative; margin-top: 0.75rem; margin-bottom: 1.2rem;">
        <div style="width: 100%; background-color: #e5e7eb; border-radius: 9999px; height: {height}; position: relative;">
            <div style="height: 100%; border-radius: 9999px; background: {gradient};"></div>
            <div style="position: absolute; top: 0; bottom: 0; left: {indicator_position}; width: 3px; background-color: black; transform: translateX(-50%); z-index: 10;"></div>
            <span style="position: absolute; top: {top_offset}; left: {indicator_position}; transform: translateX(-50%); color: {score_color}; font-weight: bold; font-size: {font_size}; white-space: nowrap; z-index: 20; background-color: white; padding: 0 0.3rem; border-radius: 0.25rem;">
                {html.escape(str(score))}
            </span>
        </div>
        <span style="position: absolute; top: 100%; margin-top: 1px; font-size: 0.65rem; color: #777;">0</span>
        <span style="position: absolute; top: 100%; right: 0%; transform: translateX(50%);">100</span>
    </div>
    """
    return html_content

def risk_reduction_bar_html(value, max_value, height='1.0rem', font_size='0.8rem'):
    """Create a horizontal bar chart for risk reduction percentages"""
    value = float(value) if pd.notna(value) else 0
    percentage = (value / max_value) * 100 if max_value > 0 else 0
    percentage = min(percentage, 100)  # Cap at 100%
    
    html_content = f"""
    <div style="width: 100%; position: relative; margin-top: 0.5rem; margin-bottom: 0.5rem;">
        <div style="width: 100%; background-color: #e5e7eb; border-radius: 4px; height: {height}; position: relative;">
            <div style="width: {percentage}%; height: 100%; background-color: #93c5fd; border-radius: 4px;"></div>
            <span style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: black; font-weight: bold; font-size: {font_size}; white-space: nowrap;">
                {value:.1f}%
            </span>
        </div>
    </div>
    """
    return html_content

def parse_value(val):
    if isinstance(val, str): val = val.replace('%', '').strip()
    return pd.to_numeric(val, errors='coerce')

def display_kpi_table(kpi_df):
    if kpi_df.empty:
        st.info("No KPI data for this process and selected impact category.")
        return
    kpi_df_copy = kpi_df.copy()
    kpi_df_copy['actual_numeric'] = kpi_df_copy['actual'].apply(parse_value)
    num_projects = kpi_df_copy['projectId'].nunique()
    is_averaged = num_projects > 1
    
    if is_averaged:
        display_df = kpi_df_copy.groupby('kpi_name').agg(
            actual_numeric=('actual_numeric', 'mean'), score=('score', 'mean'),
            unrealized_value=('unrealized_value', 'mean'), bp_range_display=('bp_range_display', 'first'),
            unit=('unit', 'first')).reset_index()
    else:
        display_df = kpi_df_copy.rename(columns={'actual_numeric': 'actual_numeric'})

    with st.container(border=True):
        header_cols = st.columns([0.4, 0.2, 0.15, 0.1, 0.15])
        header_cols[0].markdown("<span style='font-size: 1.5rem;'><strong>KPI Name</strong></span>", unsafe_allow_html=True)
        header_cols[1].markdown("<span style='font-size: 1.5rem;'><strong>Best Practice</strong></span>", unsafe_allow_html=True)
        header_cols[2].markdown("<span style='font-size: 1.5rem;'><strong>Actual (Avg)</strong></span>" if is_averaged else "<span style='font-size: 1.5rem;'><strong>Actual</strong></span>", unsafe_allow_html=True)
        header_cols[3].markdown("<span style='font-size: 1.5rem;'><strong>Score</strong></span>", unsafe_allow_html=True)
        header_cols[4].markdown("<span style='font-size: 1.5rem;'><strong>Potential</strong></span>", unsafe_allow_html=True)
        
        for _, row in display_df.iterrows():
            row_cols = st.columns([0.4, 0.2, 0.15, 0.1, 0.15])
            actual_val = row['actual_numeric']
            unit = row.get('unit', '')
            actual_display = f"{actual_val:.0%}" if unit == '%' else f"{actual_val:.1f}"
            row_cols[0].markdown(f"<span style='font-size: 1.5rem;'>{html.escape(str(row.get('kpi_name', 'N/A')))}</span>", unsafe_allow_html=True)
            row_cols[1].markdown(f"<span style='font-size: 1.5rem;'>{html.escape(str(row.get('bp_range_display', 'N/A')))}</span>", unsafe_allow_html=True)
            row_cols[2].markdown(f"<span style='font-size: 1.5rem;'>{actual_display}</span>", unsafe_allow_html=True)
            row_cols[3].markdown(f"<span style='font-size: 1.5rem;'>{row.get('score', 0):.0f}</span>", unsafe_allow_html=True)
            row_cols[4].markdown(f"<span style='font-size: 1.5rem;'>+{row.get('unrealized_value', 0):.1f}</span>", unsafe_allow_html=True)

def format_process_name(name):
    if name in PROCESS_DISPLAY_NAMES: return PROCESS_DISPLAY_NAMES[name]
    return re.sub(r"(\w)([A-Z])", r"\1 \2", name).title()

# --- Data Loading Function ---
@st.cache_data
def load_data():
    base_path = "."; data = {}
    try:
        summary_df = pd.read_csv(os.path.join(base_path, "executive_summary.csv"))
        data['executive_summary'] = summary_df[summary_df['impact_category'].isin(ALLOWED_IMPACT_CATEGORIES)]
        
        for phase in ['bidding', 'preconstruction', 'construction', 'closeout']:
            processes_file = os.path.join(base_path, f"{phase}_processes.csv")
            kpis_file = os.path.join(base_path, f"{phase}_kpis.csv")
            if os.path.exists(processes_file) and os.path.exists(kpis_file):
                df_p = pd.read_csv(processes_file)
                df_k = pd.read_csv(kpis_file)
                
                df_k['phase'] = phase.capitalize()

                if 'project_id' in df_p.columns: df_p.rename(columns={'project_id': 'projectId'}, inplace=True)
                if 'project_id' in df_k.columns: df_k.rename(columns={'project_id': 'projectId'}, inplace=True)
                
                data[phase] = {'processes': df_p, 'kpis': df_k}
        return data
    except FileNotFoundError as e:
        st.warning(f"A data file was not found: {e.filename}"); return data
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}"); return None

# --- Display Functions ---
def display_executive_summary(data, summary_for_impact_calc, impact_category_filter):
    st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>CR-Score Card</h1>", unsafe_allow_html=True); st.markdown("<h2 style='text-align: center; margin-top: 0; margin-bottom: 0.5rem; font-size: 1.5rem;'>Company ABC (Insurance View)</h2>", unsafe_allow_html=True)
    
    summary_df = data['executive_summary']
    all_kpis_df = pd.DataFrame()
    if all(phase in data for phase in PHASE_INFO.keys()):
        all_kpis_df = pd.concat([data[phase]['kpis'] for phase in PHASE_INFO.keys()]).drop_duplicates()

    if summary_df.empty: st.info("No project data matches the selected filters."); return
    
    st.markdown("<hr style='margin-top: 0.5rem; margin-bottom: 1rem;'>", unsafe_allow_html=True)
    col_cr_score, col_impact_categories = st.columns(2)
    with col_cr_score:
        st.markdown("<h2 style='text-align: center; margin-bottom: 0.25rem; font-size: 1.5rem;'>CR-Score</h2>", unsafe_allow_html=True); st.markdown("<p style='text-align: center; max-width: 100%; margin: 0.25rem auto 0.5rem auto; font-size:1.62em;'>Represents the adoption of Best Practices for all KPIs across all 4 Phases of Operations.</p>", unsafe_allow_html=True)
        st.markdown(f"<div style='margin-top: 3.0rem;'>{horizontal_risk_bar_html(summary_df['score'].mean(), height='1.95rem', font_size='2.7rem', top_offset='-3.15rem', width_percentage=90)}</div>", unsafe_allow_html=True)
    
    with col_impact_categories:
        st.markdown("<h2 style='text-align: center; margin-bottom: 0.25rem; font-size: 1.5rem;'>CR-Score Impact Categories</h2>", unsafe_allow_html=True); st.markdown(f"<p style='text-align: center; max-width: 100%; margin: 0.25rem auto 1.5rem auto; font-size:1.62em;'>The estimated correlation between the CR-Score and key business outcomes.</p>", unsafe_allow_html=True)
        
        impact_scores = summary_for_impact_calc.groupby('impact_category')['score'].mean()

        for category, config in IMPACT_CATEGORY_CONFIG.items():
            score = impact_scores.get(category, 0)
            percentage_value = score * config['multiplier']
            text_col1, text_col2 = st.columns([0.5, 0.5])
            with text_col1:
                st.markdown(f"<p style='text-align: right; margin-bottom: 0.1rem; font-size: 1.62rem;'>{html.escape(category)}:</p>", unsafe_allow_html=True)
            with text_col2:
                st.markdown(f"<p style='font-weight: 600; color: #2563eb; text-align: left; margin-bottom: 0.1rem; font-size: 1.62rem;'>{percentage_value:.1f}% {html.escape(config['suffix'])}</p>", unsafe_allow_html=True)
    
    st.markdown("<hr style='margin-top: 1rem; margin-bottom: 0.75rem;'>", unsafe_allow_html=True)
    col_components, col_actions = st.columns(2)
    with col_components:
        st.markdown("<h2 style='text-align: center; margin-bottom: 0.1rem; font-size: 1.5rem;'>CR-Score Components</h2>", unsafe_allow_html=True); st.markdown("<h3 style='text-align: center; margin-top: 0; margin-bottom: 0.5rem;'>4 Phases of Operations</h3>", unsafe_allow_html=True)
        phase_definitions = {"Bidding": {"col": "phaseScore_bidding", "desc": "selecting what jobs to bid on and building estimates"},"Precon": {"col": "phaseScore_precon", "desc": "For bids that are won, all the project preparation"},"Construction": {"col": "phaseScore_construction", "desc": "executing the plan and completing the project"},"Closeout": {"col": "phaseScore_closeout", "desc": "wrap up of all work and handoff to the customer"}}
        for name, info in phase_definitions.items():
            st.markdown(f"<div style='font-size: 1.5rem; margin-bottom: 1.5rem;'><strong>{html.escape(name)}</strong> - <em>{html.escape(info['desc'])}</em></div>", unsafe_allow_html=True)
            st.markdown(horizontal_risk_bar_html(summary_df[info["col"]].mean(), width_percentage=90, height='1.65rem', font_size='1.2rem', top_offset='-1.8rem'), unsafe_allow_html=True)
    with col_actions:
        st.markdown("<h2 style='text-align: center; margin-bottom: 0.25rem; font-size: 1.5rem;'>Top Priority KPIs</h2>", unsafe_allow_html=True)
        if not all_kpis_df.empty:
            kpis_for_actions = all_kpis_df[all_kpis_df['impact_category'] == impact_category_filter]
            
            action_items = kpis_for_actions.groupby(['kpi_name', 'phase', 'process_name'])['phase_level_unrealized_value'].mean().reset_index()
            action_items = action_items.sort_values(by='phase_level_unrealized_value', ascending=False).head(5).reset_index(drop=True)
            
            with st.container(border=True):
                if action_items.empty or action_items['phase_level_unrealized_value'].sum() == 0:
                    st.markdown("<p style='text-align:center; color:#555; font-size: 1.5rem;'>No KPIs found.</p>", unsafe_allow_html=True)
                else:
                    header_cols = st.columns([0.1, 0.2, 0.25, 0.25, 0.2])
                    header_cols[0].markdown("<span style='font-size: 1.5rem;'><strong>Rank</strong></span>", unsafe_allow_html=True)
                    header_cols[1].markdown("<span style='font-size: 1.5rem;'><strong>Phase</strong></span>", unsafe_allow_html=True)
                    header_cols[2].markdown("<span style='font-size: 1.5rem;'><strong>Process</strong></span>", unsafe_allow_html=True)
                    header_cols[3].markdown("<span style='font-size: 1.5rem;'><strong>KPI to Improve</strong></span>", unsafe_allow_html=True)
                    header_cols[4].markdown("<span style='font-size: 1.5rem;'><strong>Potential CR-Score Increase</strong></span>", unsafe_allow_html=True)

                    for i, row in action_items.iterrows():
                        row_cols = st.columns([0.1, 0.2, 0.25, 0.25, 0.2])
                        row_cols[0].markdown(f"<span style='font-size: 1.5rem;'><strong>{i+1}</strong></span>", unsafe_allow_html=True)
                        row_cols[1].markdown(f"<span style='font-size: 1.5rem;'>{html.escape(row['phase'])}</span>", unsafe_allow_html=True)
                        row_cols[2].markdown(f"<span style='font-size: 1.5rem;'>{format_process_name(row['process_name'])}</span>", unsafe_allow_html=True)
                        row_cols[3].markdown(f"<span style='font-size: 1.5rem;'>{html.escape(row['kpi_name'])}</span>", unsafe_allow_html=True)
                        row_cols[4].markdown(f"<span style='font-size: 1.5rem;'><strong>+{row['phase_level_unrealized_value']:.1f}</strong></span>", unsafe_allow_html=True)
        else: st.info("No KPI data for current selection.")

def display_phase_summary_page(phase_key, data, impact_category_filter):
    if phase_key not in data:
        st.error(f"Data for the {phase_key} phase could not be loaded. Please ensure `{phase_key}_processes.csv` and `{phase_key}_kpis.csv` files are present.")
        return

    info = PHASE_INFO.get(phase_key)
    if not info: st.error("Invalid phase selected."); return
    
    st.markdown(f"<h1 style='text-align: center; color: #333333;'>{info['title']}</h1>", unsafe_allow_html=True)
    
    summary_df = data['executive_summary']
    
    # --- FIX: Filter processes by project/pm/region first, then calculate scores ---
    processes_df_all_categories = data[phase_key]['processes']
    process_scores = processes_df_all_categories.groupby('process_name')['score'].mean()
    
    # Now filter kpis by impact category
    kpis_df = data[phase_key]['kpis'][data[phase_key]['kpis']['impact_category'] == impact_category_filter]
    
    if summary_df.empty: st.info("No project data matches the selected filters."); return

    phase_score = summary_df[info['score_col']].mean()
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"<h2 style='text-align: center; font-size: 1.5rem;'>{phase_key.capitalize()} Phase Score</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-size:1.62em;'>{PHASE_DESCRIPTIONS.get(phase_key, '')}</p>", unsafe_allow_html=True)
        st.markdown(f"<div style='margin-top: 2.0rem;'>{horizontal_risk_bar_html(phase_score, height='1.95rem', font_size='2.7rem', top_offset='-3.15rem', width_percentage=90)}</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"<h2 style='text-align: center; font-size: 1.5rem;'>Impact Categories</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; max-width: 100%; margin: 0.25rem auto 1.5rem auto; font-size:1.62em;'>The estimated correlation between the {phase_key.capitalize()} Score and key business outcomes.</p>", unsafe_allow_html=True)
        config_for_phase = PHASE_IMPACT_CONFIG.get(phase_key, {})
        if not config_for_phase:
            st.info("No impact category configuration for this phase.")
        else:
            for category, config in config_for_phase.items():
                percentage_value = phase_score * config['multiplier']
                text_col1, text_col2 = st.columns([0.5, 0.5])
                with text_col1:
                    st.markdown(f"<p style='text-align: right; margin-bottom: 0.1rem; font-size: 1.62rem;'>{html.escape(category)}:</p>", unsafe_allow_html=True)
                with text_col2:
                    st.markdown(f"<p style='font-weight: 600; color: #2563eb; text-align: left; margin-bottom: 0.1rem; font-size: 1.62rem;'>{percentage_value:.1f}% {html.escape(config['suffix'])}</p>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)
    
    col_processes, col_actions = st.columns(2)
    with col_processes:
        st.markdown(f"<h2 style='text-align: center; font-size: 1.5rem;'>{phase_key.capitalize()} Processes</h2>", unsafe_allow_html=True)
        for process_key in PHASE_PROCESS_MAPPING.get(phase_key, []):
            score = process_scores.get(process_key, 0)
            process_display_name = format_process_name(process_key)
            state_key = f"show_kpis_{phase_key}_{process_key}"
            button_label = "Hide KPIs" if st.session_state.get(state_key, False) else "Show KPIs"
            
            p_col1, p_col2 = st.columns([0.75, 0.25])
            with p_col1:
                st.markdown(f"<span style='font-size: 1.5rem;'><strong>{process_display_name}</strong></span>", unsafe_allow_html=True)
                st.markdown(horizontal_risk_bar_html(score, width_percentage=95, height='1.65rem', font_size='1.2rem', top_offset='-1.8rem'), unsafe_allow_html=True)
            with p_col2:
                st.button(button_label, key=f"btn_{state_key}", on_click=lambda s_key=state_key: st.session_state.update({s_key: not st.session_state.get(s_key, False)}), use_container_width=True)
            if st.session_state.get(state_key, False):
                display_kpi_table(kpis_df[kpis_df['process_name'] == process_key])

    with col_actions:
        st.markdown(f"<h2 style='text-align: center; font-size: 1.5rem;'>Top {phase_key.capitalize()} KPIs</h2>", unsafe_allow_html=True)
        if not kpis_df.empty:
            action_items = kpis_df.groupby('kpi_name')['process_level_unrealized_value'].mean().nlargest(5).reset_index()
            with st.container(border=True):
                if action_items.empty or action_items['process_level_unrealized_value'].sum() == 0:
                    st.markdown("<p style='text-align:center; color:#555; font-size: 1.5rem;'>No KPIs found.</p>", unsafe_allow_html=True)
                else:
                    header_cols = st.columns([0.15, 0.55, 0.3])
                    header_cols[0].markdown("<span style='font-size: 1.5rem;'><strong>Rank</strong></span>", unsafe_allow_html=True)
                    header_cols[1].markdown("<span style='font-size: 1.5rem;'><strong>KPI to Improve</strong></span>", unsafe_allow_html=True)
                    header_cols[2].markdown("<span style='font-size: 1.5rem;'><strong>Potential Score Increase</strong></span>", unsafe_allow_html=True)
                    for i, row in action_items.iterrows():
                        potential_gain = row['process_level_unrealized_value']
                        row_cols = st.columns([0.15, 0.55, 0.3])
                        row_cols[0].markdown(f"<span style='font-size: 1.5rem;'><strong>{i+1}</strong></span>", unsafe_allow_html=True)
                        row_cols[1].markdown(f"<span style='font-size: 1.5rem;'>{html.escape(row['kpi_name'])}</span>", unsafe_allow_html=True)
                        row_cols[2].markdown(f"<span style='font-size: 1.5rem;'><strong>+{potential_gain:.1f}</strong></span>", unsafe_allow_html=True)
        else: st.info("No KPI data for current selection.")

def display_scoreboard(summary_for_impact_calc):
    """Display portfolio scoreboard with segment analysis"""
    st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>Portfolio Scoreboard</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; margin-top: 0; margin-bottom: 1rem; font-size: 1.5rem;'>Segment Performance Analysis</h2>", unsafe_allow_html=True)
    
    if summary_for_impact_calc.empty:
        st.info("No portfolio data available.")
        return
    
    st.markdown("<hr style='margin-top: 0.5rem; margin-bottom: 1.5rem;'>", unsafe_allow_html=True)
    
    # Segment selector
    col_selector, col_spacer = st.columns([0.3, 0.7])
    with col_selector:
        segment_by = st.selectbox(
            "Segment Portfolio By:",
            ["Project", "Region", "Project Manager"],
            help="Select how to group the portfolio for analysis"
        )
    
    # Map selection to column name
    segment_column_map = {
        "Project": "projectId",
        "Region": "region",
        "Project Manager": "projectManager"
    }
    segment_col = segment_column_map[segment_by]
    
    # Calculate scoreboard data
    scoreboard_data = []
    
    for segment_value in sorted(summary_for_impact_calc[segment_col].unique()):
        segment_df = summary_for_impact_calc[summary_for_impact_calc[segment_col] == segment_value]
        
        # Calculate average score
        avg_score = segment_df['score'].mean()
        
        # Calculate risk reduction by category
        gl_reduction = 0
        wc_reduction = 0
        br_reduction = 0
        ca_reduction = 0
        
        for category in ALLOWED_IMPACT_CATEGORIES:
            category_data = segment_df[segment_df['impact_category'] == category]
            if not category_data.empty:
                category_score = category_data['score'].mean()
                multiplier = IMPACT_CATEGORY_CONFIG[category]['multiplier']
                reduction = category_score * multiplier
                
                if category == 'GL Insurance':
                    gl_reduction = reduction
                elif category == 'WC Insurance':
                    wc_reduction = reduction
                elif category == 'BR Insurance':
                    br_reduction = reduction
                elif category == 'CA Insurance':
                    ca_reduction = reduction
        
        scoreboard_data.append({
            'Segment': segment_value,
            'CR-Score': avg_score,
            'GL Risk Reduction': gl_reduction,
            'WC Risk Reduction': wc_reduction,
            'BR Risk Reduction': br_reduction,
            'CA Risk Reduction': ca_reduction
        })
    
    # Create DataFrame and sort by CR-Score (highest first)
    scoreboard_df = pd.DataFrame(scoreboard_data)
    
    if scoreboard_df.empty:
        st.info("No data available for selected segment.")
        return
    
    # Sort by CR-Score descending (highest first)
    scoreboard_df = scoreboard_df.sort_values(by='CR-Score', ascending=False).reset_index(drop=True)
    
    # Display scoreboard table
    st.markdown(f"<h3 style='text-align: center; margin-bottom: 1rem;'>Portfolio Segmented by {segment_by}</h3>", unsafe_allow_html=True)
    
    with st.container(border=True):
        # Header row
        header_cols = st.columns([0.20, 0.20, 0.15, 0.15, 0.15, 0.15])
        header_cols[0].markdown(f"<span style='font-size: 1.5rem;'><strong>{segment_by}</strong></span>", unsafe_allow_html=True)
        header_cols[1].markdown("<span style='font-size: 1.5rem;'><strong>CR-Score</strong></span>", unsafe_allow_html=True)
        header_cols[2].markdown("<span style='font-size: 1.5rem;'><strong>GL Risk Reduction</strong></span>", unsafe_allow_html=True)
        header_cols[3].markdown("<span style='font-size: 1.5rem;'><strong>WC Risk Reduction</strong></span>", unsafe_allow_html=True)
        header_cols[4].markdown("<span style='font-size: 1.5rem;'><strong>BR Risk Reduction</strong></span>", unsafe_allow_html=True)
        header_cols[5].markdown("<span style='font-size: 1.5rem;'><strong>CA Risk Reduction</strong></span>", unsafe_allow_html=True)
        
        # Data rows
        for _, row in scoreboard_df.iterrows():
            row_cols = st.columns([0.20, 0.20, 0.15, 0.15, 0.15, 0.15])
            
            # Segment name
            row_cols[0].markdown(f"<span style='font-size: 1.5rem;'><strong>{html.escape(str(row['Segment']))}</strong></span>", unsafe_allow_html=True)
            
            # Score with horizontal risk bar (increased font size from 0.85rem to 1.275rem)
            score = row['CR-Score']
            row_cols[1].markdown(horizontal_risk_bar_html(score, height='1.65rem', font_size='1.275rem', top_offset='-1.8rem', width_percentage=95), unsafe_allow_html=True)
            
            # Risk reduction bars with appropriate max values (increased font size from 0.8rem to 1.2rem, height from 1.0rem to 1.5rem)
            row_cols[2].markdown(risk_reduction_bar_html(row['GL Risk Reduction'], 60, height='1.5rem', font_size='1.2rem'), unsafe_allow_html=True)
            row_cols[3].markdown(risk_reduction_bar_html(row['WC Risk Reduction'], 60, height='1.5rem', font_size='1.2rem'), unsafe_allow_html=True)
            row_cols[4].markdown(risk_reduction_bar_html(row['BR Risk Reduction'], 40, height='1.5rem', font_size='1.2rem'), unsafe_allow_html=True)
            row_cols[5].markdown(risk_reduction_bar_html(row['CA Risk Reduction'], 30, height='1.5rem', font_size='1.2rem'), unsafe_allow_html=True)

def display_uw_report(original_data):
    """Display Underwriter Report with full portfolio score and risk guidance"""
    st.markdown("<h1 style='text-align: center; margin-bottom: 1rem;'>Underwriter Report</h1>", unsafe_allow_html=True)
    
    # Get full portfolio CR-Score (no filters applied)
    full_portfolio_df = original_data.get('executive_summary', pd.DataFrame())
    
    if full_portfolio_df.empty:
        st.info("No portfolio data available.")
        return
    
    # Calculate overall portfolio score
    portfolio_score = full_portfolio_df['score'].mean()
    
    st.markdown("<hr style='margin-top: 0.5rem; margin-bottom: 1.5rem;'>", unsafe_allow_html=True)
    
    # Display score with label
    st.markdown("<h2 style='text-align: center; margin-bottom: 0.5rem; font-size: 1.8rem;'>Operational Performance Score</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; margin-bottom: 3.5rem; font-size: 1.2rem; color: #666;'>Overall portfolio risk assessment based on operational best practices</p>", unsafe_allow_html=True)
    
    # Center the score bar
    col1, col2, col3 = st.columns([0.1, 0.8, 0.1])
    with col2:
        st.markdown(horizontal_risk_bar_html(portfolio_score, height='2.5rem', font_size='3.0rem', top_offset='-3.8rem', width_percentage=100), unsafe_allow_html=True)
    
    st.markdown("<hr style='margin-top: 2rem; margin-bottom: 1.5rem;'>", unsafe_allow_html=True)
    
    # Risk guidance with color-coded sections
    st.markdown("<h2 style='text-align: center; margin-bottom: 1rem; font-size: 1.8rem;'>Underwriting Risk Guidance</h2>", unsafe_allow_html=True)
    
    # Color-coded risk guidance boxes
    col_low, col_mid, col_high = st.columns(3)
    
    with col_low:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #fde047 0%, #facc15 100%); padding: 1.5rem; border-radius: 0.5rem; height: 280px;'>
            <h3 style='color: #1f2937; text-align: center; margin-bottom: 0.75rem; font-size: 1.5rem;'>Score: 0-20</h3>
            <h4 style='color: #1f2937; text-align: center; margin-bottom: 0.75rem; font-size: 1.2rem; font-weight: 600;'>Average Risk</h4>
            <p style='color: #1f2937; font-size: 1.1rem; line-height: 1.6;'>
                <strong>Profile:</strong> Industry standard performance<br><br>
                <strong>Recommendation:</strong> Standard coverage limits, deductibles, and pricing. Monitor closely for improvement opportunities.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_mid:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #86efac 0%, #4ade80 100%); padding: 1.5rem; border-radius: 0.5rem; height: 280px;'>
            <h3 style='color: #1f2937; text-align: center; margin-bottom: 0.75rem; font-size: 1.5rem;'>Score: 20-50</h3>
            <h4 style='color: #1f2937; text-align: center; margin-bottom: 0.75rem; font-size: 1.2rem; font-weight: 600;'>Good Performance</h4>
            <p style='color: #1f2937; font-size: 1.1rem; line-height: 1.6;'>
                <strong>Profile:</strong> Above industry average, demonstrates good operational controls<br><br>
                <strong>Recommendation:</strong> Consider improved coverage limits, lower deductibles, and favorable pricing terms.
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_high:
        st.markdown("""
        <div style='background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%); padding: 1.5rem; border-radius: 0.5rem; height: 280px;'>
            <h3 style='color: white; text-align: center; margin-bottom: 0.75rem; font-size: 1.5rem;'>Score: 50-100</h3>
            <h4 style='color: white; text-align: center; margin-bottom: 0.75rem; font-size: 1.2rem; font-weight: 600;'>Best-in-Class</h4>
            <p style='color: white; font-size: 1.1rem; line-height: 1.6;'>
                <strong>Profile:</strong> Industry leading performance, lowest risk profile<br><br>
                <strong>Recommendation:</strong> Offer best available coverage limits, lowest deductibles, and most competitive pricing.
            </p>
        </div>
        """, unsafe_allow_html=True)

def display_loss_control(filtered_data, impact_category_filter):
    """Display Loss Control page with filtered operational score and top KPIs to improve"""
    st.markdown("<h1 style='text-align: center; margin-bottom: 1rem;'>Loss Control</h1>", unsafe_allow_html=True)
    
    summary_df = filtered_data.get('executive_summary', pd.DataFrame())
    
    if summary_df.empty:
        st.info("No project data matches the selected filters.")
        return
    
    # Calculate filtered portfolio score
    filtered_score = summary_df['score'].mean()
    
    st.markdown("<hr style='margin-top: 0.5rem; margin-bottom: 1.5rem;'>", unsafe_allow_html=True)
    
    # Display score with label
    st.markdown("<h2 style='text-align: center; margin-bottom: 0.5rem; font-size: 1.8rem;'>Operational Performance Score</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; margin-bottom: 3.5rem; font-size: 1.2rem; color: #666;'>Current portfolio risk assessment based on operational best practices</p>", unsafe_allow_html=True)
    
    # Center the score bar
    col1, col2, col3 = st.columns([0.1, 0.8, 0.1])
    with col2:
        st.markdown(horizontal_risk_bar_html(filtered_score, height='2.5rem', font_size='3.0rem', top_offset='-3.8rem', width_percentage=100), unsafe_allow_html=True)
    
    st.markdown("<hr style='margin-top: 2rem; margin-bottom: 1.5rem;'>", unsafe_allow_html=True)
    
    # Top 5 KPIs to improve
    st.markdown("<h2 style='text-align: center; margin-bottom: 1.5rem; font-size: 1.8rem;'>Top 5 Priority KPIs for Improvement</h2>", unsafe_allow_html=True)
    
    # KPI data
    kpis = [
        {"rank": 1, "name": "Submittal Rate", "definition": "Submittal Count divided by number of project days", "score_increase": "+8.5"},
        {"rank": 2, "name": "Observation Close Out Rate", "definition": "Observations closed out divided by Observation count", "score_increase": "+7.2"},
        {"rank": 3, "name": "RFI Response Time", "definition": "Average days between RFI creation and RFI close out", "score_increase": "+6.8"},
        {"rank": 4, "name": "Subcontractor Prequal Rate", "definition": "Count of Subs with preferable Prequal characteristics divided by total Count of Subs", "score_increase": "+5.4"},
        {"rank": 5, "name": "Change Order Documentation Quality", "definition": "Average percent of critical details included with Change Orders", "score_increase": "+4.9"}
    ]
    
    # Display KPIs in a clean format
    for kpi in kpis:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**#{kpi['rank']} - {kpi['name']}**")
            st.markdown(f"*{kpi['definition']}*")
        with col2:
            st.markdown(f"**{kpi['score_increase']}** Score Increase")

# --- Main Application ---
def main():
    original_data = load_data()
    if not original_data: st.stop()
    
    st.sidebar.title("Global Filters")
    unfiltered_summary_df = original_data.get('executive_summary', pd.DataFrame())
    if not unfiltered_summary_df.empty:
        project_ids = sorted(unfiltered_summary_df['projectId'].unique())
        regions = sorted(unfiltered_summary_df['region'].unique())
        pms = sorted(unfiltered_summary_df['projectManager'].unique())
        impact_categories = sorted(unfiltered_summary_df['impact_category'].unique())
    else:
        project_ids, regions, pms, impact_categories = [], [], [], []

    default_index = 0
    if impact_categories and 'BR Insurance' in impact_categories:
        default_index = impact_categories.index('BR Insurance')
    elif impact_categories:
        default_index = 0

    filters = {
        "project": st.sidebar.selectbox("Select Project", ['All Projects'] + project_ids),
        "region": st.sidebar.selectbox("Select Region", ['All Regions'] + regions),
        "pm": st.sidebar.selectbox("Select Project Manager", ['All PMs'] + pms),
        "impact_category": st.sidebar.selectbox("Select Impact Category", impact_categories, index=default_index)
    }
    
    summary_for_impact_calc = original_data['executive_summary'].copy()
    if filters['project'] != 'All Projects': summary_for_impact_calc = summary_for_impact_calc[summary_for_impact_calc['projectId'] == filters['project']]
    if filters['region'] != 'All Regions': summary_for_impact_calc = summary_for_impact_calc[summary_for_impact_calc['region'] == filters['region']]
    if filters['pm'] != 'All PMs': summary_for_impact_calc = summary_for_impact_calc[summary_for_impact_calc['projectManager'] == filters['pm']]

    summary_df = summary_for_impact_calc.copy()
    summary_df = summary_df[summary_df['impact_category'] == filters['impact_category']]
    
    filtered_data = copy.deepcopy(original_data)
    filtered_data['executive_summary'] = summary_df
    
    final_filtered_project_ids = summary_df['projectId'].unique()
    for phase in PHASE_INFO.keys():
        if phase in filtered_data:
            filtered_data[phase]['processes'] = filtered_data[phase]['processes'][filtered_data[phase]['processes']['projectId'].isin(final_filtered_project_ids)]
            filtered_data[phase]['kpis'] = filtered_data[phase]['kpis'][filtered_data[phase]['kpis']['projectId'].isin(final_filtered_project_ids)]

    st.sidebar.caption(f"Last updated: {datetime.date.today().strftime('%m/%d/%Y')}")
    st.sidebar.markdown("---")
    st.sidebar.title("Navigation")
    
    nav_options = ["Executive Summary", "Scoreboard", "Bidding", "Preconstruction", "Construction", "Closeout", "UW Report", "Loss Control"]
    page_selection = st.sidebar.radio("Page Navigation", nav_options, label_visibility="collapsed")

    if page_selection == "Executive Summary":
        display_executive_summary(filtered_data, summary_for_impact_calc, filters['impact_category'])
    elif page_selection == "Scoreboard":
        display_scoreboard(summary_for_impact_calc)
    elif page_selection == "UW Report":
        display_uw_report(original_data)
    elif page_selection == "Loss Control":
        display_loss_control(filtered_data, filters['impact_category'])
    else:
        display_phase_summary_page(page_selection.lower(), filtered_data, filters['impact_category'])

    st.markdown(f"""
    <div style="text-align: center; color: #6b7280; font-size: 0.875rem; margin-top: 1rem; padding-bottom: 1rem;">
         <p style="margin-bottom:0.25rem;">&copy; {datetime.date.today().year} Construction Risk AI. All rights reserved.</p>
         <p style-top:0;">Data provided for informational purposes only. Consult with experts for detailed analysis.</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
