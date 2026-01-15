import streamlit as st
import pandas as pd
import datetime
import os
import html
import copy
import re

# --- Page Configuration (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(page_title="CR-Score Dashboard (Construction View)", layout="wide")

# --- AUTHENTICATION LAYER ---
def check_password():
    """Returns `True` if the user entered the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Get password from Streamlit secrets (works locally and in Streamlit Cloud)
        try:
            correct_password = st.secrets.get("DASHBOARD_PASSWORD", os.environ.get("DASHBOARD_PASSWORD", "DemoPassword2026!"))
        except:
            correct_password = os.environ.get("DASHBOARD_PASSWORD", "DemoPassword2026!")
        
        if st.session_state["password"] == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    # Return True if password is already validated
    if st.session_state.get("password_correct", False):
        return True

    # Show login form
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1>🔒 CR-Score Dashboard</h1>
        <h3>Construction View - Demo Access</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.text_input(
            "Enter Password",
            type="password",
            on_change=password_entered,
            key="password",
            placeholder="Enter your password"
        )

        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("😕 Password incorrect. Please try again.")
        
        st.markdown("""
        <div style="text-align: center; margin-top: 2rem; color: #666;">
            <p>For access, please contact your Construction Risk AI representative.</p>
        </div>
        """, unsafe_allow_html=True)

    return False

# Check authentication before showing the dashboard
if not check_password():
    st.stop()

# --- DASHBOARD CODE (ONLY RUNS IF AUTHENTICATED) ---

# --- App Configuration ---

# --- Define the specific categories for this version of the dashboard ---
ALLOWED_IMPACT_CATEGORIES = ['Schedule', 'Cost', 'Safety']

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

PHASE_DESCRIPTIONS = {
    "bidding": "Represents the adoption of Best Practices for all KPIs across 4 key processes of the Bidding Phase.",
    "preconstruction": "Represents the adoption of Best Practices for all KPIs across 4 key processes of the Preconstruction Phase.",
    "construction": "Represents the adoption of Best Practices for all KPIs across 5 key processes of the Construction Phase.",
    "closeout": "Represents the adoption of Best Practices for all KPIs across 4 key processes of the Closeout Phase."
}


# --- Filter the configuration dictionaries to match the allowed categories ---
IMPACT_CATEGORY_CONFIG = {
    "Schedule": {"multiplier": 0.40, "suffix": "improvement"},
    "Cost": {"multiplier": 0.20, "suffix": "improvement"},
    "Safety": {"multiplier": 0.80, "suffix": "improvement"}
}

PHASE_IMPACT_CONFIG = {
    "bidding": {
        "Schedule": {"multiplier": 0.02, "suffix": "improvement"},
        "Cost": {"multiplier": 0.06, "suffix": "improvement"},
        "Safety": {"multiplier": 0.08, "suffix": "improvement"}
    },
    "preconstruction": {
        "Schedule": {"multiplier": 0.16, "suffix": "improvement"},
        "Cost": {"multiplier": 0.05, "suffix": "improvement"},
        "Safety": {"multiplier": 0.20, "suffix": "improvement"}
    },
    "construction": {
        "Schedule": {"multiplier": 0.20, "suffix": "improvement"},
        "Cost": {"multiplier": 0.08, "suffix": "improvement"},
        "Safety": {"multiplier": 0.48, "suffix": "improvement"}
    },
    "closeout": {
        "Schedule": {"multiplier": 0.02, "suffix": "improvement"},
        "Cost": {"multiplier": 0.01, "suffix": "improvement"},
        "Safety": {"multiplier": 0.04, "suffix": "improvement"}
    }
}

# --- NEW: Dummy data for the new "Top Priority Action Items" section ---
DUMMY_ACTION_ITEMS = {
    "executive_summary": {
        "headers": ["Phase", "Item", "Required Action"],
        "items": [
            ("Construction", "RFI #103 - Structural", "High risk, needs immediate response"),
            ("Bidding", "Bid Pkg #01-456 - Concrete", "Waiting on 3 sub quotes"),
            ("Preconstruction", "Permits", "Awaiting city approval for foundation"),
            ("Closeout", "Punch #08 - HVAC", "High risk item outstanding"),
            ("Construction", "Submittal #45 - Glazing", "Late and pending approval")
        ]
    },
    "bidding": {
        "headers": ["Bid Package Number", "Item Name", "Required Action"],
        "items": [
            ("01-456", "Concrete", "Waiting on quotes from subs"),
            ("02-789", "Structural Steel", "Finalize compliance items"),
            ("00-123", "Site Work", "Bid is 2 days late"),
            ("03-101", "Plumbing", "Needs final review before submission"),
            ("04-112", "Electrical", "Awaiting GC approval")
        ]
    },
    "preconstruction": {
        "headers": ["Item", "Required Action"],
        "items": [
            ("Permits", "Finalize and submit foundation permit"),
            ("Budget", "Needs to be completed and approved"),
            ("Prime Contract", "Legal review pending"),
            ("BIM Clash Detection", "12 clashes in sector A need resolution"),
            ("Structural Steel Subcontract", "Scope of work requires clarification")
        ]
    },
    "construction": {
        "headers": ["Item", "Required Action"],
        "items": [
            ("RFI #103 - Structural", "High risk RFI, needs immediate response"),
            ("Submittal #45 - Glazing", "Late and pending approval"),
            ("Observation #212 - Safety", "High risk observation, needs to be closed"),
            ("Change Order #12", "High value change order needs client approval"),
            ("Invoice - Trade Partner X", "Invoice for May is late")
        ]
    },
    "closeout": {
        "headers": ["Item", "Required Action"],
        "items": [
            ("Punch #08 - HVAC", "High risk punch item outstanding"),
            ("Final Payment - Prime", "Awaiting client final payment"),
            ("Final Payment - Elec. Sub", "Awaiting final invoice from subcontractor"),
            ("As-Built Drawings", "Need to be finalized and submitted"),
            ("O&M Manuals", "Incomplete, awaiting vendor data")
        ]
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
        header_cols[0].markdown("**KPI Name**"); header_cols[1].markdown("**Best Practice**")
        header_cols[2].markdown("**Actual (Avg)**" if is_averaged else "**Actual**"); header_cols[3].markdown("**Score**"); header_cols[4].markdown("**Potential**")
        
        for _, row in display_df.iterrows():
            row_cols = st.columns([0.4, 0.2, 0.15, 0.1, 0.15])
            actual_val = row['actual_numeric']
            unit = row.get('unit', '')
            actual_display = f"{actual_val:.0%}" if unit == '%' else f"{actual_val:.1f}"
            row_cols[0].write(html.escape(str(row.get('kpi_name', 'N/A'))))
            row_cols[1].write(html.escape(str(row.get('bp_range_display', 'N/A'))))
            row_cols[2].write(actual_display); row_cols[3].write(f"{row.get('score', 0):.0f}"); row_cols[4].write(f"+{row.get('unrealized_value', 0):.1f}")

def format_process_name(name):
    if name in PROCESS_DISPLAY_NAMES: return PROCESS_DISPLAY_NAMES[name]
    return re.sub(r"(\w)([A-Z])", r"\1 \2", name).title()

def display_top_action_items(page_key):
    """Displays the new 'Top Priority Action Items' section with dummy data."""
    action_item_data = DUMMY_ACTION_ITEMS.get(page_key)
    if not action_item_data:
        return

    st.markdown("<h2 style='text-align: center; margin-bottom: 0.25rem; font-size: 1.5rem; margin-top: 1.5rem;'>Top Priority Action Items</h2>", unsafe_allow_html=True)
    
    with st.container(border=True):
        headers = action_item_data["headers"]
        items = action_item_data["items"]
        
        # Create dynamic columns based on the number of headers
        header_cols = st.columns(len(headers))
        for col, header in zip(header_cols, headers):
            col.markdown(f"**{header}**")
        
        for item in items:
            item_cols = st.columns(len(item))
            for col, value in zip(item_cols, item):
                col.write(html.escape(str(value)))


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
    st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>CR-Score Card</h1>", unsafe_allow_html=True); st.markdown("<h2 style='text-align: center; margin-top: 0; margin-bottom: 0.5rem; font-size: 1.5rem;'>Company ABC (Construction View)</h2>", unsafe_allow_html=True)
    
    summary_df = data['executive_summary']
    all_kpis_df = pd.DataFrame()
    if all(phase in data for phase in PHASE_INFO.keys()):
        all_kpis_df = pd.concat([data[phase]['kpis'] for phase in PHASE_INFO.keys()]).drop_duplicates()

    if summary_df.empty: st.info("No project data matches the selected filters."); return
    
    st.markdown("<hr style='margin-top: 0.5rem; margin-bottom: 1rem;'>", unsafe_allow_html=True)
    col_cr_score, col_impact_categories = st.columns(2)
    with col_cr_score:
        st.markdown("<h2 style='text-align: center; margin-bottom: 0.25rem; font-size: 1.5rem;'>CR-Score</h2>", unsafe_allow_html=True); st.markdown("<p style='text-align: center; max-width: 100%; margin: 0.25rem auto 0.5rem auto; font-size:1.08em;'>Represents the adoption of Best Practices for all KPIs across all 4 Phases of Operations.</p>", unsafe_allow_html=True)
        st.markdown(f"<div style='margin-top: 2.0rem;'>{horizontal_risk_bar_html(summary_df['score'].mean(), height='1.3rem', font_size='1.8rem', top_offset='-2.1rem', width_percentage=90)}</div>", unsafe_allow_html=True)
    
    with col_impact_categories:
        st.markdown("<h2 style='text-align: center; margin-bottom: 0.25rem; font-size: 1.5rem;'>CR-Score Impact Categories</h2>", unsafe_allow_html=True); st.markdown(f"<p style='text-align: center; max-width: 100%; margin: 0.25rem auto 1.5rem auto; font-size:1.08em;'>The estimated correlation between the CR-Score and key business outcomes.</p>", unsafe_allow_html=True)
        
        impact_scores = summary_for_impact_calc.groupby('impact_category')['score'].mean()

        for category, config in IMPACT_CATEGORY_CONFIG.items():
            score = impact_scores.get(category, 0)
            percentage_value = score * config['multiplier']
            text_col1, text_col2 = st.columns([0.5, 0.5])
            with text_col1:
                st.markdown(f"<p style='text-align: right; margin-bottom: 0.1rem; font-size: 1.08rem;'>{html.escape(category)}:</p>", unsafe_allow_html=True)
            with text_col2:
                st.markdown(f"<p style='font-weight: 600; color: #2563eb; text-align: left; margin-bottom: 0.1rem; font-size: 1.08rem;'>{percentage_value:.1f}% {html.escape(config['suffix'])}</p>", unsafe_allow_html=True)
    
    st.markdown("<hr style='margin-top: 1rem; margin-bottom: 0.75rem;'>", unsafe_allow_html=True)
    col_components, col_actions = st.columns(2)
    with col_components:
        st.markdown("<h2 style='text-align: center; margin-bottom: 0.1rem; font-size: 1.5rem;'>CR-Score Components</h2>", unsafe_allow_html=True); st.markdown("<h3 style='text-align: center; margin-top: 0; margin-bottom: 0.5rem;'>4 Phases of Operations</h3>", unsafe_allow_html=True)
        phase_definitions = {"Bidding": {"col": "phaseScore_bidding", "desc": "selecting what jobs to bid on and building estimates"},"Precon": {"col": "phaseScore_precon", "desc": "For bids that are won, all the project preparation"},"Construction": {"col": "phaseScore_construction", "desc": "executing the plan and completing the project"},"Closeout": {"col": "phaseScore_closeout", "desc": "wrap up of all work and handoff to the customer"}}
        for name, info in phase_definitions.items():
            st.markdown(f"<div style='font-size: 1.0rem;'><strong>{html.escape(name)}</strong> - <em>{html.escape(info['desc'])}</em></div>", unsafe_allow_html=True)
            st.markdown(horizontal_risk_bar_html(summary_df[info["col"]].mean(), width_percentage=90, height='1.1rem', font_size='0.8rem', top_offset='-1.2rem'), unsafe_allow_html=True)
    with col_actions:
        # --- UPDATED: Renamed section ---
        st.markdown("<h2 style='text-align: center; margin-bottom: 0.25rem; font-size: 1.5rem;'>Top Priority KPIs to Improve</h2>", unsafe_allow_html=True)
        if not all_kpis_df.empty:
            kpis_for_actions = all_kpis_df[all_kpis_df['impact_category'] == impact_category_filter]
            action_items = kpis_for_actions.groupby(['kpi_name'])['phase_level_unrealized_value'].mean().nlargest(5).reset_index()
            with st.container(border=True):
                if action_items.empty or action_items['phase_level_unrealized_value'].sum() == 0:
                    st.markdown("<p style='text-align:center; color:#555;'>No action items found.</p>", unsafe_allow_html=True)
                else:
                    header_cols = st.columns([0.15, 0.55, 0.3]); header_cols[0].markdown("**Rank**"); header_cols[1].markdown("**KPI to Improve**"); header_cols[2].markdown("**Potential CR-Score Increase**")
                    for i, row in action_items.iterrows():
                        row_cols = st.columns([0.15, 0.55, 0.3]); row_cols[0].markdown(f"**{i+1}**"); row_cols[1].markdown(html.escape(row['kpi_name'])); row_cols[2].markdown(f"**+{row['phase_level_unrealized_value']:.1f}**")
        else: st.info("No KPI data for current selection.")

        # --- NEW: Display the new Action Items section ---
        display_top_action_items("executive_summary")


def display_phase_summary_page(phase_key, data, impact_category_filter):
    if phase_key not in data:
        st.error(f"Data for the {phase_key} phase could not be loaded. Please ensure `{phase_key}_processes.csv` and `{phase_key}_kpis.csv` files are present.")
        return

    info = PHASE_INFO.get(phase_key)
    if not info: st.error("Invalid phase selected."); return
    
    st.markdown(f"<h1 style='text-align: center; color: #333333;'>{info['title']}</h1>", unsafe_allow_html=True)
    
    summary_df = data['executive_summary']
    processes_df_all_categories = data[phase_key]['processes']
    kpis_df = data[phase_key]['kpis'][data[phase_key]['kpis']['impact_category'] == impact_category_filter]
    
    if summary_df.empty: st.info("No project data matches the selected filters."); return

    phase_score = summary_df[info['score_col']].mean()
    process_scores = processes_df_all_categories.groupby('process_name')['score'].mean()
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"<h2 style='text-align: center; font-size: 1.5rem;'>{phase_key.capitalize()} Phase Score</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-size:1.08em;'>{PHASE_DESCRIPTIONS.get(phase_key, '')}</p>", unsafe_allow_html=True)
        st.markdown(horizontal_risk_bar_html(phase_score, height='1.3rem', font_size='1.8rem', top_offset='-2.1rem', width_percentage=90), unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"<h2 style='text-align: center; font-size: 1.5rem;'>Impact Categories</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; max-width: 100%; margin: 0.25rem auto 1.5rem auto; font-size:1.08em;'>The estimated correlation between the {phase_key.capitalize()} Score and key business outcomes.</p>", unsafe_allow_html=True)
        config_for_phase = PHASE_IMPACT_CONFIG.get(phase_key, {})
        if not config_for_phase:
            st.info("No impact category configuration for this phase.")
        else:
            for category, config in config_for_phase.items():
                percentage_value = phase_score * config['multiplier']
                text_col1, text_col2 = st.columns([0.5, 0.5])
                with text_col1:
                    st.markdown(f"<p style='text-align: right; margin-bottom: 0.1rem; font-size: 1.08rem;'>{html.escape(category)}:</p>", unsafe_allow_html=True)
                with text_col2:
                    st.markdown(f"<p style='font-weight: 600; color: #2563eb; text-align: left; margin-bottom: 0.1rem; font-size: 1.08rem;'>{percentage_value:.1f}% {html.escape(config['suffix'])}</p>", unsafe_allow_html=True)

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
                st.markdown(f"<strong>{process_display_name}</strong>", unsafe_allow_html=True)
                st.markdown(horizontal_risk_bar_html(score, width_percentage=95, height='1.1rem', font_size='0.8rem', top_offset='-1.2rem'), unsafe_allow_html=True)
            with p_col2:
                st.button(button_label, key=f"btn_{state_key}", on_click=lambda s_key=state_key: st.session_state.update({s_key: not st.session_state.get(s_key, False)}), use_container_width=True)
            if st.session_state.get(state_key, False):
                display_kpi_table(kpis_df[kpis_df['process_name'] == process_key])

    with col_actions:
        # --- UPDATED: Renamed section ---
        st.markdown(f"<h2 style='text-align: center; font-size: 1.5rem;'>Top Priority KPIs to Improve</h2>", unsafe_allow_html=True)
        if not kpis_df.empty:
            action_items = kpis_df.groupby('kpi_name')['process_level_unrealized_value'].mean().nlargest(5).reset_index()
            with st.container(border=True):
                if action_items.empty or action_items['process_level_unrealized_value'].sum() == 0:
                    st.markdown("<p style='text-align:center; color:#555;'>No action items found.</p>", unsafe_allow_html=True)
                else:
                    header_cols = st.columns([0.15, 0.55, 0.3]); header_cols[0].markdown("**Rank**"); header_cols[1].markdown("**KPI to Improve**"); header_cols[2].markdown("**Potential Score Increase**")
                    for i, row in action_items.iterrows():
                        potential_gain = row['process_level_unrealized_value']
                        row_cols = st.columns([0.15, 0.55, 0.3]); row_cols[0].markdown(f"**{i+1}**"); row_cols[1].markdown(html.escape(row['kpi_name'])); row_cols[2].markdown(f"**+{potential_gain:.1f}**")
        else: st.info("No KPI data for current selection.")

        # --- NEW: Display the new Action Items section ---
        display_top_action_items(phase_key)

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
    if impact_categories and 'Schedule' in impact_categories:
        default_index = impact_categories.index('Schedule')
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
    
    nav_options = ["Executive Summary", "Bidding", "Preconstruction", "Construction", "Closeout"]
    page_selection = st.sidebar.radio("Page Navigation", nav_options, label_visibility="collapsed")

    if page_selection == "Executive Summary":
        display_executive_summary(filtered_data, summary_for_impact_calc, filters['impact_category'])
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
