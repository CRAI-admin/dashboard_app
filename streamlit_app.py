import streamlit as st
import pandas as pd
import datetime
import os
import html
import copy
import re
import boto3
from botocore.exceptions import ClientError

# Import authentication functions
def check_authentication():
    """Check if user is authenticated"""
    return st.session_state.get('authenticated', False)

def show_logout_sidebar():
    """Show logout option in sidebar"""
    if st.session_state.get('authenticated', False):
        if st.sidebar.button("🚪 Logout"):
            # Clear authentication state
            for key in ['authenticated', 'access_token', 'user_attributes', 'username']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

def show_dashboard_login_sidebar():
    """Placeholder for dashboard login sidebar"""
    pass

# --- Page Configuration (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(page_title="CR-Score Dashboard (Construction View)", layout="wide")

# --- App Configuration ---

# Check if this is a health check request (must be before any other processing)
if st.query_params.get("health") == "check":
    st.write("OK")
    st.stop()

# Check if this is the login page specifically requested
if st.query_params.get("page") == "login":
    from cognito_auth import main as cognito_main
    cognito_main()
    st.stop()

# For the main dashboard URL, go directly to the dashboard if authenticated
# If not authenticated, redirect to login page

# --- Define the specific categories for this version of the dashboard ---
ALLOWED_IMPACT_CATEGORIES = ['cost']

PHASE_PROCESS_MAPPING = {
    "estimating": ["bidreview", "estimating", "compliance", "bidresults"],
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
    "estimating": {"title": "Estimating Phase Summary", "score_col": "phaseScore_estimating"},
    "preconstruction": {"title": "Preconstruction Phase Summary", "score_col": "phaseScore_preconstruction"},
    "construction": {"title": "Construction Phase Summary", "score_col": "phaseScore_construction"},
    "closeout": {"title": "Closeout Phase Summary", "score_col": "phaseScore_closeout"}
}

PHASE_DESCRIPTIONS = {
    "estimating": "Represents the adoption of Best Practices for all KPIs across 4 key processes of the Estimating Phase.",
    "preconstruction": "Represents the adoption of Best Practices for all KPIs across 4 key processes of the Preconstruction Phase.",
    "construction": "Represents the adoption of Best Practices for all KPIs across 5 key processes of the Construction Phase.",
    "closeout": "Represents the adoption of Best Practices for all KPIs across 4 key processes of the Closeout Phase."
}

# --- Filter the configuration dictionaries to match the allowed categories ---
IMPACT_CATEGORY_CONFIG = {
    "cost": {"multiplier": 0.20, "suffix": "improvement"}
}

PHASE_IMPACT_CONFIG = {
    "estimating": {
        "cost": {"multiplier": 0.06, "suffix": "improvement"}
    },
    "preconstruction": {
        "cost": {"multiplier": 0.05, "suffix": "improvement"}
    },
    "construction": {
        "cost": {"multiplier": 0.08, "suffix": "improvement"}
    },
    "closeout": {
        "cost": {"multiplier": 0.01, "suffix": "improvement"}
    }
}

# --- Procore item type to phase mapping ---
ITEM_TYPE_TO_PHASE = {
    "rfi": "construction",
    "submittal": "construction", 
    "observation": "construction",
    "incident": "construction",
    "punch_item": "closeout",
    "prime_contract_change_order": "preconstruction",
    "prime_contract_invoice_payment": "closeout"
}

# --- KPI Tooltip Definitions ---
KPI_TOOLTIP_DEFINITIONS = {
    "RFI Avg Create Date": "Avg Date RFIs are created as percent of project completion. This measures if RFIs are created consistently throughout the entire project.",
    "RFI Avg Time to Resolution": "Avg number of days taken to close RFIs.",
    "RFI % On Time": "Percent of RFIs closed before the due date.",
    "RFI AverageLead Time": "Avg number of days given to close RFIs when they are created.",
    "RFI Usage Rate": "Number of RFIs divided by number of Project Days.",
    "RFI Documentation Quality": "Percent of critical details provided with RFIs including: Due Date, Close Date, Description, Assignees, etc.",
    "Submittals Avg Create Date": "Avg Date Submittals are created as a percent of project completion.",
    "Submittals Average Time to Resolution": "Avg number of days taken to close Submittals.",
    "Submittals % Resolved on Time": "Percent of Submittals closed before the due date.",
    "Submittals Average Lead Time": "Avg number of days given to close Submittals when they are created.",
    "Submittals Usage Rate": "Number of Submittals divided by number of Project Days.",
    "Submittals Documentation Quality": "Percent of critical details provided with Submittals including: Due Date, Close Date, Description, Assignees, etc.",
    "Daily Logs % with Issues": "Percent of Daily Logs indicating a negative event or situation",
    "Daily Logs Avg Create Date": "Avg Date Daily Logs are created as a percent of project completion",
    "Daily Logs Avg Days until Created": "Avg number of days lag until Daily Logs are created",
    "Daily Logs Rate": "Number of Daily Logs divided by number of Project Days.",
    "Meetings Rate": "Number of Meetings divided by number of Project Days.",
    "Meetings Documentation Quality": "Percent of critical details provided with Meetings including: Attendees, Topics, Notes, etc.",
    "Photos Usage": "Number of Photos divided by number of Project Days.",
    "Photos Avg Create Date": "Avg Date Photos are created as a percent of project completion.",
    "Photos Avg Documentation Score": "Percent of critical details provided with photos including description, type, etc.",
    "Budgets Revision Rate": "Percent of Budget Line Items with revisions",
    "Budgets Create Date": "Avg Date Budget Line Items are created as percent of project completion",
    "Budgets Usage Rate": "Number of Budget Line Items divided by number of Project Days.",
    "Prime Contract Change Orders Documentation Quality": "Percent of critical details provided with Prime Contract Change Orders including: Description, Reason, Cost Impact, Schedule Impact, etc.",
    "Prime Contract Change Orders Project Percentage": "Total value of Change Orders divided by Estimated Project Value",
    "Prime Contract Estimated Average Payment Cycle": "Avg number of days between invoice and payment",
    "Prime Contract Estimated Payment Ratio": "Total Payments divided by Total Invoices",
    "Prime Contract Invoices Rate": "Number of Prime Contract Invoices divided by number of Project Days.",
    "Prime Contract Late Payment Rate": "Percent of Payments made after more than 30 days past the invoice.",
    "Prime Contract Payment Error Rate": "Percent of Payments that are late or less than the invoice",
    "Prime Contract Payment Rate": "Number of Payments divided by number of Invoices.",
    "Prime Contract to Budget Ratio": "Prime Contract value divided by Total Budget value",
    "Prime Contract to Invoice Ratio": "Prime Contract value divided by Total Invoice value",
    "Prime Contract to Underpayment Rate": "Percent of Prime Contract payments that are less than the invoice",
    "Observations Average Days to Close": "Avg number of days taken to close Observations.",
    "Observations Average Lead Time": "Avg number of days given to close Observations when they are created.",
    "Observations % Closed on Time": "Percent of Observations closed before the due date.",
    "Observations Documentation Quality": "Percent of critical details provided with Observations including: Due Date, Close Date, Description, Contributing Behaviors/Conditions, Hazards, Assignees.",
    "Observations Rate": "Number of Observations divided by number of Project Days.",
    "Quality Inspection Rate": "Number of Quality Inspections divided by number of Project Days.",
    "Quality Inspections Conforming Rate": "Percent of Quality Inspection Items found Conforming.",
    "Safety Inspection Rate": "Number of Safety Inspections divided by number of Project Days.",
    "Safety Inspection Conforming Rate": "Percent of Safety Inspection Items found Conforming.",
    "Incident Detail Quality": "Percent of critical details provided with Incidents including: Description, Assignees, Contributing Behavior, Contributing Conditions, etc.",
    "Incident Rate": "Number of Incidents divided by number of Project Days.",
}

# --- Tooltip CSS Styling ---
TOOLTIP_CSS = """
<style>
.tooltip {
    position: relative;
    display: inline-block;
    cursor: help;
    border-bottom: 1px dotted #999;
}

.tooltip .tooltiptext {
    visibility: hidden;
    width: 300px;
    background-color: #333;
    color: #fff;
    text-align: left;
    border-radius: 6px;
    padding: 8px 12px;
    position: absolute;
    z-index: 1000;
    bottom: 125%;
    left: 50%;
    margin-left: -150px;
    opacity: 0;
    transition: opacity 0.3s;
    font-size: 12px;
    line-height: 1.4;
    box-shadow: 0px 2px 8px rgba(0,0,0,0.2);
}

.tooltip .tooltiptext::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    margin-left: -5px;
    border-width: 5px;
    border-style: solid;
    border-color: #333 transparent transparent transparent;
}

.tooltip:hover .tooltiptext {
    visibility: visible;
    opacity: 1;
}
</style>
"""

# --- S3 Configuration ---
S3_BUCKET = "haugland-pilot"
S3_PREFIX = "app-files/"

# --- Helper Functions for Filters ---
def parse_project_managers(project_managers_str):
    """Parse the project_managers column to extract individual manager names."""
    if pd.isna(project_managers_str) or project_managers_str == '':
        return []
    
    # Split by comma and clean up each name
    managers = []
    for manager in str(project_managers_str).split(','):
        manager = manager.strip()
        if manager:
            # Extract name from format like "Bowen (110-31100) James" -> "James Bowen"
            # or "McIntyre James" -> "James McIntyre"
            parts = manager.split()
            if len(parts) >= 2:
                # Check if format has parentheses (ID in middle)
                if '(' in manager and ')' in manager:
                    # Format: "LastName (ID) FirstName"
                    last_name = parts[0]
                    first_name = ' '.join(parts[2:]) if len(parts) > 2 else parts[-1]
                    full_name = f"{first_name} {last_name}".strip()
                else:
                    # Format: "LastName FirstName" -> "FirstName LastName"
                    if len(parts) == 2:
                        full_name = f"{parts[1]} {parts[0]}"
                    else:
                        full_name = manager
                managers.append(full_name)
    
    return managers

def get_all_project_managers(df):
    """Extract all unique project manager names from the project_managers column."""
    all_managers = set()
    for managers_str in df['project_managers'].dropna():
        managers = parse_project_managers(managers_str)
        all_managers.update(managers)
    return sorted(list(all_managers))

def filter_by_project_manager(df, selected_manager):
    """Filter dataframe to show only projects where the selected manager is involved."""
    if selected_manager == 'All Project Managers':
        return df
    
    def manager_in_project(managers_str):
        if pd.isna(managers_str):
            return False
        managers = parse_project_managers(managers_str)
        return selected_manager in managers
    
    return df[df['project_managers'].apply(manager_in_project)]

# --- S3 Helper Functions ---
@st.cache_data(ttl=3600)  # Cache for 1 hour to reduce S3 calls
def download_file_from_s3(filename):
    """Download a file from S3 and return as pandas DataFrame with memory optimization."""
    try:
        s3_client = boto3.client('s3')
        s3_key = f"{S3_PREFIX}{filename}"
        
        # Download file content
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        
        # Read as DataFrame and handle duplicates immediately
        df = pd.read_csv(response['Body'])
        
        # Remove duplicate columns and rows, reset index to ensure clean data
        if not df.empty:
            df = df.loc[:, ~df.columns.duplicated()]  # Remove duplicate columns
            df = df.drop_duplicates()  # Remove duplicate rows
            df = df.reset_index(drop=True)  # Reset index to avoid duplicate labels
        
        return df
    except ClientError as e:
        st.error(f"Error downloading {filename} from S3: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Unexpected error loading {filename}: {e}")
        return pd.DataFrame()

# --- Load Procore action items data ---
@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_procore_action_items():
    """Load and process Procore itemized data for action items display."""
    try:
        procore_df = download_file_from_s3("procore-itemized-combined.csv")
        
        if procore_df.empty:
            st.warning("Procore data file 'procore-itemized-combined.csv' not found in S3. Using fallback data.")
            return pd.DataFrame()
        
        # Add phase mapping
        procore_df['phase'] = procore_df['item_type'].map(ITEM_TYPE_TO_PHASE).fillna('construction')
        
        # Clean up the risky_id field to extract just the item identifier
        procore_df['item_display'] = procore_df['risky_id'].str.extract(r'(\d+\s*-\s*.+?)(?:\s*-\s*[A-Za-z]|$)')[0]
        procore_df['item_display'] = procore_df['item_display'].fillna(procore_df['risky_id'])
        
        return procore_df
    except Exception as e:
        st.error(f"Error loading Procore data: {e}")
        return pd.DataFrame()

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

def create_kpi_tooltip(kpi_name):
    """Create a tooltip-enabled KPI name with definition."""
    definition = KPI_TOOLTIP_DEFINITIONS.get(kpi_name, "No definition available for this KPI.")
    
    tooltip_html = f"""
    <div class="tooltip">
        {html.escape(kpi_name)}
        <span class="tooltiptext">{html.escape(definition)}</span>
    </div>
    """
    return tooltip_html

def calculate_cost_improvement(phase_score, phase_key):
    """Calculate cost improvement percentage based on phase score and phase type."""
    if phase_score is None or pd.isna(phase_score):
        return 0.0
    
    # Special formula for construction phase
    if phase_key == 'construction':
        return 0.0228 * ((100 * phase_score) ** 0.4875)
    
    # Use different improvement factors for other phases
    improvement_factors = {
        'estimating': 0.06,      # 6% max improvement
        'preconstruction': 0.05, # 5% max improvement  
        'closeout': 0.01         # 1% max improvement
    }
    
    factor = improvement_factors.get(phase_key, 0.03)
    return phase_score * factor

def calculate_executive_cost_improvement(summary_df):
    """Calculate executive summary cost improvement as sum of all phase improvements."""
    if summary_df.empty:
        return 0.0
    
    # Get average phase scores
    estimating_score = summary_df['phaseScore_estimating'].mean()
    preconstruction_score = summary_df['phaseScore_preconstruction'].mean() 
    construction_score = summary_df['phaseScore_construction'].mean()
    closeout_score = summary_df['phaseScore_closeout'].mean()
    
    # Calculate improvement for each phase using the same logic as phase pages
    estimating_improvement = estimating_score * 0.06  # Same as estimating page
    preconstruction_improvement = preconstruction_score * 0.05  # Same as preconstruction page
    construction_improvement = 0.0228 * ((construction_score) ** 0.4875) * 100  # Same as construction page
    closeout_improvement = closeout_score * 0.01  # Same as closeout page
    
    # Return sum of all phase improvements
    return estimating_improvement + preconstruction_improvement + construction_improvement + closeout_improvement

def display_kpi_table(kpi_df):
    if kpi_df.empty:
        st.info("No KPI data for this process and selected impact category.")
        return
    
    # Inject tooltip CSS
    st.markdown(TOOLTIP_CSS, unsafe_allow_html=True)
    
    kpi_df_copy = kpi_df.copy()
    kpi_df_copy['actual_numeric'] = kpi_df_copy['actual'].apply(parse_value)
    num_projects = kpi_df_copy['projectId'].nunique()
    is_averaged = num_projects > 1
    
    if is_averaged:
        display_df = kpi_df_copy.groupby('kpi_name').agg(
            actual_numeric=('actual_numeric', 'mean'), score=('score', 'mean'),
            unrealized_value=('unrealized_value', 'mean'), bp_range_display=('bp_range_display', 'first'),
            unit=('unit', 'first')).reset_index()
        # Convert score from 0-1 to 0-100 for display
        display_df['score'] = display_df['score'] * 100
    else:
        display_df = kpi_df_copy.rename(columns={'actual_numeric': 'actual_numeric'})
        # Convert score from 0-1 to 0-100 for display
        display_df['score'] = display_df['score'] * 100

    with st.container(border=True):
        header_cols = st.columns([0.4, 0.2, 0.15, 0.1, 0.15])
        header_cols[0].markdown("**KPI Name**"); header_cols[1].markdown("**Best Practice**")
        header_cols[2].markdown("**Actual (Avg)**" if is_averaged else "**Actual**"); header_cols[3].markdown("**Score**"); header_cols[4].markdown("**Potential**")
        
        for _, row in display_df.iterrows():
            row_cols = st.columns([0.4, 0.2, 0.15, 0.1, 0.15])
            actual_val = row['actual_numeric']
            unit = row.get('unit', '')
            actual_display = f"{actual_val:.0%}" if unit == '%' else f"{actual_val:.1f}"
            
            # Use tooltip for KPI name
            kpi_name = str(row.get('kpi_name', 'N/A'))
            tooltip_html = create_kpi_tooltip(kpi_name)
            row_cols[0].markdown(tooltip_html, unsafe_allow_html=True)
            
            row_cols[1].write(html.escape(str(row.get('bp_range_display', 'N/A'))))
            row_cols[2].write(actual_display); row_cols[3].write(f"{row.get('score', 0):.0f}"); row_cols[4].write(f"+{row.get('unrealized_value', 0):.1f}")

def format_process_name(name):
    if name in PROCESS_DISPLAY_NAMES: return PROCESS_DISPLAY_NAMES[name]
    return re.sub(r"(\w)([A-Z])", r"\1 \2", name).title()

def display_top_action_items(page_key, project_filter=None, office_name_filter=None, program_manager_filter=None):
    """Displays the 'Top Priority Action Items' section with real Procore data."""
    procore_df = load_procore_action_items()
    
    if procore_df.empty:
        st.markdown("<h2 style='text-align: center; margin-bottom: 0.25rem; font-size: 1.5rem; margin-top: 1.5rem;'>Top Priority Action Items</h2>", unsafe_allow_html=True)
        with st.container(border=True):
            st.info("No Procore action items data available.")
        return

    # Store original count for debugging
    original_count = len(procore_df)

    # Apply project filter if specified
    if project_filter and project_filter != 'All Projects':
        if 'projectId' in procore_df.columns:
            procore_df = procore_df[procore_df['projectId'].astype(str) == str(project_filter)]

    # Apply office name filter if specified
    if office_name_filter and office_name_filter != 'All Office Names':
        if 'office_name' in procore_df.columns:
            procore_df = procore_df[procore_df['office_name'].astype(str) == str(office_name_filter)]

    # Apply program manager filter if specified
    if program_manager_filter and program_manager_filter != 'All Program Managers':
        if 'program_manager' in procore_df.columns:
            procore_df = procore_df[procore_df['program_manager'].astype(str) == str(program_manager_filter)]

    # Check if any data remains after filtering
    filtered_count = len(procore_df)
    
    if procore_df.empty:
        st.markdown("<h2 style='text-align: center; margin-bottom: 0.25rem; font-size: 1.5rem; margin-top: 1.5rem;'>Top Priority Action Items</h2>", unsafe_allow_html=True)
        with st.container(border=True):
            st.info(f"No Procore action items found for the selected filters. (Filtered from {original_count} to {filtered_count} items)")
        return

    st.markdown("<h2 style='text-align: center; margin-bottom: 0.25rem; font-size: 1.5rem; margin-top: 1.5rem;'>Top Priority Action Items</h2>", unsafe_allow_html=True)
    
    # Filter data based on the current page
    if page_key == "executive_summary":
        # Show top 5 highest risk items across all phases
        top_items = procore_df.nlargest(5, 'risk_value')
        headers = ["Rank", "Project ID", "Item Type", "Item", "Required Action"]
        
        with st.container(border=True):
            header_cols = st.columns([0.08, 0.32, 0.15, 0.30, 0.15])
            for col, header in zip(header_cols, headers):
                col.markdown(f"**{header}**")
            
            for idx, (_, row) in enumerate(top_items.iterrows(), 1):
                item_cols = st.columns([0.08, 0.32, 0.15, 0.30, 0.15])
                item_cols[0].write(f"**{idx}**")
                # Show full projectId without truncation
                item_cols[1].write(html.escape(str(row['projectId'])))
                item_cols[2].write(row['item_type'].replace('_', ' ').title())
                # Show full item_display without truncation
                item_cols[3].write(html.escape(str(row['item_display'])))
                item_cols[4].write(html.escape(str(row['required_action'])))
    else:
        # Show items specific to the current phase
        phase_items = procore_df[procore_df['phase'] == page_key].nlargest(5, 'risk_value')
        
        if phase_items.empty:
            with st.container(border=True):
                st.info(f"No action items found for {page_key} phase.")
            return
            
        headers = ["Rank", "Project ID", "Item Type", "Item", "Required Action"]
        
        with st.container(border=True):
            header_cols = st.columns([0.08, 0.32, 0.15, 0.30, 0.15])
            for col, header in zip(header_cols, headers):
                col.markdown(f"**{header}**")
            
            for idx, (_, row) in enumerate(phase_items.iterrows(), 1):
                item_cols = st.columns([0.08, 0.32, 0.15, 0.30, 0.15])
                item_cols[0].write(f"**{idx}**")
                # Show full projectId without truncation
                item_cols[1].write(html.escape(str(row['projectId'])))
                item_cols[2].write(row['item_type'].replace('_', ' ').title())
                # Show full item_display without truncation
                item_cols[3].write(html.escape(str(row['item_display'])))
                item_cols[4].write(html.escape(str(row['required_action'])))

# --- Memory-Efficient Data Filtering ---
def filter_data_efficiently(original_data, selected_project, selected_office_name, selected_program_manager, selected_project_manager, selected_project_stage, selected_impact_category):
    """Memory-efficient data filtering without deepcopy"""
    if not original_data:
        return None
        
    try:
        # Start with executive summary filtering
        summary_df = original_data['executive_summary'].copy()
        
        # Apply filters efficiently
        if selected_project != 'All Projects':
            summary_df = summary_df[summary_df['projectId'].astype(str) == selected_project]
        if selected_office_name != 'All Office Names':
            summary_df = summary_df[summary_df['office_name'].astype(str) == selected_office_name]
        if selected_program_manager != 'All Program Managers':
            summary_df = summary_df[summary_df['program_manager'].astype(str) == selected_program_manager]
        if selected_project_manager != 'All Project Managers':
            summary_df = filter_by_project_manager(summary_df, selected_project_manager)
        if selected_project_stage != 'All Project Stages':
            summary_df = summary_df[summary_df['project_stage'].astype(str) == selected_project_stage]
        
        # Filter by impact category
        summary_df = summary_df[summary_df['impact_category'] == selected_impact_category]
        
        # Get filtered project IDs
        final_filtered_project_ids = summary_df['projectId'].unique()
        
        # Create filtered data structure
        filtered_data = {
            'executive_summary': summary_df
        }
        
        # Filter phase data efficiently
        for phase in PHASE_INFO.keys():
            if phase in original_data:
                processes_df = original_data[phase]['processes']
                kpis_df = original_data[phase]['kpis']
                
                if len(final_filtered_project_ids) > 0:
                    # Use pandas filtering instead of deepcopy
                    processes_filtered = processes_df[processes_df['projectId'].isin(final_filtered_project_ids)].copy()
                    kpis_filtered = kpis_df[kpis_df['projectId'].isin(final_filtered_project_ids)].copy()
                    
                    filtered_data[phase] = {
                        'processes': processes_filtered.reset_index(drop=True),
                        'kpis': kpis_filtered.reset_index(drop=True)
                    }
                else:
                    # No matching projects
                    filtered_data[phase] = {
                        'processes': pd.DataFrame(),
                        'kpis': pd.DataFrame()
                    }
        
        return filtered_data
        
    except Exception as e:
        st.error(f"Error filtering data: {str(e)}")
        return original_data

# --- Data Loading Function with Memory Optimization ---
@st.cache_data(ttl=3600)  # Cache for 1 hour to reduce S3 calls
def load_data():
    """Load all dashboard data from S3 with memory optimization."""
    data = {}
    try:
        # Load executive summary
        summary_df = download_file_from_s3("executive_summary.csv")
        if not summary_df.empty:
            # Filter for only cost impact category (lowercase)
            data['executive_summary'] = summary_df[summary_df['impact_category'] == 'cost']
        else:
            st.warning("Executive summary data not found in S3.")
            data['executive_summary'] = pd.DataFrame()
        
        # Load phase data efficiently - only when needed
        for phase in ['estimating', 'preconstruction', 'construction', 'closeout']:
            processes_file = f"{phase}_processes.csv"
            kpis_file = f"{phase}_kpis.csv"
            
            try:
                df_p = download_file_from_s3(processes_file)
                df_k = download_file_from_s3(kpis_file)
                
                if not df_p.empty and not df_k.empty:
                    # Add phase column to KPIs
                    df_k = df_k.copy()
                    df_k['phase'] = phase.capitalize()

                    # Standardize column names
                    if 'project_id' in df_p.columns: 
                        df_p.rename(columns={'project_id': 'projectId'}, inplace=True)
                    if 'project_id' in df_k.columns: 
                        df_k.rename(columns={'project_id': 'projectId'}, inplace=True)
                    
                    data[phase] = {'processes': df_p, 'kpis': df_k}
                else:
                    st.warning(f"Data for {phase} phase not found in S3.")
                    
            except Exception as e:
                st.warning(f"Error loading {phase} phase: {str(e)}")
                continue
        
        return data
    except Exception as e:
        st.error(f"An unexpected error occurred loading data from S3: {e}")
        return None

# --- Display Functions ---
def display_executive_summary(data, summary_for_impact_calc, impact_category_filter, filters):
    st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>CR-Score Card</h1>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center; margin-top: 0; margin-bottom: 0.5rem; font-size: 1.5rem;'>Haugland Companies (Construction View)</h2>", unsafe_allow_html=True)
    
    summary_df = data['executive_summary']
    all_kpis_df = pd.DataFrame()
    if all(phase in data for phase in PHASE_INFO.keys()):
        all_kpis_df = pd.concat([data[phase]['kpis'] for phase in PHASE_INFO.keys()]).drop_duplicates()

    if summary_df.empty: 
        st.info("No project data matches the selected filters.")
        return
    
    st.markdown("<hr style='margin-top: 0.5rem; margin-bottom: 1rem;'>", unsafe_allow_html=True)
    col_cr_score, col_impact_categories = st.columns(2)
    with col_cr_score:
        st.markdown("<h2 style='text-align: center; margin-bottom: 0.25rem; font-size: 1.5rem;'>CR-Score</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; max-width: 100%; margin: 0.25rem auto 0.5rem auto; font-size:1.08em;'>Represents the adoption of Best Practices for all KPIs across all 4 Phases of Operations.</p>", unsafe_allow_html=True)
        st.markdown(f"<div style='margin-top: 2.0rem;'>{horizontal_risk_bar_html(summary_df['score'].mean(), height='1.3rem', font_size='1.8rem', top_offset='-2.1rem', width_percentage=90)}</div>", unsafe_allow_html=True)
    
    with col_impact_categories:
        st.markdown("<h2 style='text-align: center; margin-bottom: 0.25rem; font-size: 1.5rem;'>CR-Score Impact Categories</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; max-width: 100%; margin: 0.25rem auto 1.5rem auto; font-size:1.08em;'>The estimated correlation between the CR-Score and key business outcomes.</p>", unsafe_allow_html=True)
        
        impact_scores = summary_for_impact_calc.groupby('impact_category')['score'].mean()

        for category, config in IMPACT_CATEGORY_CONFIG.items():
            if category == 'cost':
                percentage_value = calculate_executive_cost_improvement(summary_for_impact_calc)
            else:
                score = impact_scores.get(category, 0)
                percentage_value = score * config['multiplier']
            text_col1, text_col2 = st.columns([0.5, 0.5])
            with text_col1:
                st.markdown(f"<p style='text-align: right; margin-bottom: 0.1rem; font-size: 1.08rem;'>{html.escape(category.capitalize())}:</p>", unsafe_allow_html=True)
            with text_col2:
                st.markdown(f"<p style='font-weight: 600; color: #2563eb; text-align: left; margin-bottom: 0.1rem; font-size: 1.08rem;'>{percentage_value:.1f}% {html.escape(config['suffix'])}</p>", unsafe_allow_html=True)
    
    st.markdown("<hr style='margin-top: 1rem; margin-bottom: 0.75rem;'>", unsafe_allow_html=True)
    col_components, col_actions = st.columns(2)
    with col_components:
        st.markdown("<h2 style='text-align: center; margin-bottom: 0.1rem; font-size: 1.5rem;'>CR-Score Components</h2>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; margin-top: 0; margin-bottom: 0.5rem;'>4 Phases of Operations</h3>", unsafe_allow_html=True)
        phase_definitions = {
            "Estimating": {"col": "phaseScore_estimating", "desc": "selecting what jobs to bid on and building estimates"},
            "Precon": {"col": "phaseScore_preconstruction", "desc": "For bids that are won, all the project preparation"}, 
            "Construction": {"col": "phaseScore_construction", "desc": "executing the plan and completing the project"},
            "Closeout": {"col": "phaseScore_closeout", "desc": "wrap up of all work and handoff to the customer"}
        }
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
                    header_cols = st.columns([0.15, 0.55, 0.3])
                    header_cols[0].markdown("**Rank**")
                    header_cols[1].markdown("**KPI to Improve**")
                    header_cols[2].markdown("**Potential CR-Score Increase**")
                    for i, row in action_items.iterrows():
                        row_cols = st.columns([0.15, 0.55, 0.3])
                        row_cols[0].markdown(f"**{i+1}**")
                        row_cols[1].markdown(html.escape(row['kpi_name']))
                        row_cols[2].markdown(f"**+{row['phase_level_unrealized_value']:.1f}**")
        else: 
            st.info("No KPI data for current selection.")

        # --- NEW: Display the new Action Items section ---
        display_top_action_items("executive_summary", filters['project'], filters['office_name'], filters['program_manager'])

def display_phase_summary_page(phase_key, data, impact_category_filter, filters):
    if phase_key not in data:
        st.error(f"Data for the {phase_key} phase could not be loaded. Please ensure `{phase_key}_processes.csv` and `{phase_key}_kpis.csv` files are present.")
        return

    info = PHASE_INFO.get(phase_key)
    if not info: 
        st.error("Invalid phase selected.")
        return
    
    st.markdown(f"<h1 style='text-align: center; color: #333333;'>{info['title']}</h1>", unsafe_allow_html=True)
    
    summary_df = data['executive_summary']
    processes_df_all_categories = data[phase_key]['processes']
    kpis_df = data[phase_key]['kpis'][data[phase_key]['kpis']['impact_category'] == impact_category_filter]
    
    if summary_df.empty: 
        st.info("No project data matches the selected filters.")
        return

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
                # Apply special formula for construction phase cost improvement
                if phase_key == "construction" and category == "cost":
                    percentage_value = 0.0228 * ((phase_score) ** 0.4875) * 100
                else:
                    percentage_value = phase_score * config['multiplier']
                
                text_col1, text_col2 = st.columns([0.5, 0.5])
                with text_col1:
                    st.markdown(f"<p style='text-align: right; margin-bottom: 0.1rem; font-size: 1.08rem;'>{html.escape(category.capitalize())}:</p>", unsafe_allow_html=True)
                with text_col2:
                    st.markdown(f"<p style='font-weight: 600; color: #2563eb; text-align: left; margin-bottom: 0.1rem; font-size: 1.08rem;'>{percentage_value:.1f}% {html.escape(config['suffix'])}</p>", unsafe_allow_html=True)
    
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
                    header_cols = st.columns([0.15, 0.55, 0.3])
                    header_cols[0].markdown("**Rank**")
                    header_cols[1].markdown("**KPI to Improve**")
                    header_cols[2].markdown("**Potential Score Increase**")
                    for i, row in action_items.iterrows():
                        potential_gain = row['process_level_unrealized_value']
                        row_cols = st.columns([0.15, 0.55, 0.3])
                        row_cols[0].markdown(f"**{i+1}**")
                        row_cols[1].markdown(html.escape(row['kpi_name']))
                        row_cols[2].markdown(f"**+{potential_gain:.1f}**")
        else: 
            st.info("No KPI data for current selection.")

        # --- NEW: Display the new Action Items section ---
        display_top_action_items(phase_key, filters['project'], filters['office_name'], filters['program_manager'])

# --- Import the dashboard login page ---
# Note: Import this in the main function to avoid page config conflicts

# --- Main Application ---
def main():
    # Check for authentication token in URL parameters first
    access_token = st.query_params.get("access_token")
    if access_token:
        # Validate the token with Cognito
        try:
            from cognito_auth import CognitoAuth
            cognito_auth = CognitoAuth()
            if cognito_auth.verify_token(access_token):
                # Token is valid, set authentication state
                st.session_state['authenticated'] = True
                st.session_state['access_token'] = access_token
                st.session_state['user_attributes'] = cognito_auth.get_user_attributes(access_token)
                # Clear the URL parameter for security
                st.query_params.clear()
                st.rerun()
        except Exception as e:
            st.error(f"Token validation failed: {str(e)}")
    
    # Check authentication - if not authenticated, redirect to login page
    if not check_authentication():
        # Redirect to login page instead of showing login form here
        login_url = "https://login.cr-ai-dashboard.com/?page=login"
        st.markdown(f"""
        <script>
            window.location.href = '{login_url}';
        </script>
        """, unsafe_allow_html=True)
        st.info("Redirecting to login page...")
        st.stop()
    
    # User is authenticated - show the dashboard
    # Show logout option in sidebar
    show_logout_sidebar()
    
    try:
        original_data = load_data()
        if not original_data: 
            st.error("Could not load data from S3")
            st.stop()
        
        st.sidebar.title("Global Filters")
        unfiltered_summary_df = original_data.get('executive_summary', pd.DataFrame())
        if not unfiltered_summary_df.empty:
            # Convert to string and filter out NaN values to prevent sorting errors
            project_ids = sorted([str(x) for x in unfiltered_summary_df['projectId'].unique() if pd.notna(x)])
            office_names = sorted([str(x) for x in unfiltered_summary_df['office_name'].unique() if pd.notna(x)])
            program_managers = sorted([str(x) for x in unfiltered_summary_df['program_manager'].unique() if pd.notna(x)])
            project_managers = get_all_project_managers(unfiltered_summary_df)
            project_stages = sorted([str(x) for x in unfiltered_summary_df['project_stage'].unique() if pd.notna(x)])
            impact_categories = sorted([str(x) for x in unfiltered_summary_df['impact_category'].unique() if pd.notna(x)])
        else:
            project_ids, office_names, program_managers, project_managers, project_stages, impact_categories = [], [], [], [], [], []

        default_index = 0
        if impact_categories and 'cost' in impact_categories:
            default_index = impact_categories.index('cost')
        elif impact_categories:
            default_index = 0

        filters = {
            "project": st.sidebar.selectbox("Select Project", ['All Projects'] + project_ids),
            "office_name": st.sidebar.selectbox("Office Name", ['All Office Names'] + office_names),
            "program_manager": st.sidebar.selectbox("Program Manager", ['All Program Managers'] + program_managers),
            "project_manager": st.sidebar.selectbox("Project Manager", ['All Project Managers'] + project_managers),
            "project_stage": st.sidebar.selectbox("Project Stage", ['All Project Stages'] + project_stages),
            "impact_category": st.sidebar.selectbox("Select Impact Category", impact_categories, index=default_index)
        }
        
        summary_for_impact_calc = original_data['executive_summary'].copy()
        if filters['project'] != 'All Projects': 
            summary_for_impact_calc = summary_for_impact_calc[summary_for_impact_calc['projectId'].astype(str) == filters['project']]
        if filters['office_name'] != 'All Office Names': 
            summary_for_impact_calc = summary_for_impact_calc[summary_for_impact_calc['office_name'].astype(str) == filters['office_name']]
        if filters['program_manager'] != 'All Program Managers': 
            summary_for_impact_calc = summary_for_impact_calc[summary_for_impact_calc['program_manager'].astype(str) == filters['program_manager']]
        if filters['project_manager'] != 'All Project Managers':
            summary_for_impact_calc = filter_by_project_manager(summary_for_impact_calc, filters['project_manager'])
        if filters['project_stage'] != 'All Project Stages':
            summary_for_impact_calc = summary_for_impact_calc[summary_for_impact_calc['project_stage'].astype(str) == filters['project_stage']]

        # Use efficient filtering instead of deepcopy
        filtered_data = filter_data_efficiently(
            original_data, 
            filters['project'], 
            filters['office_name'], 
            filters['program_manager'],
            filters['project_manager'],
            filters['project_stage'],
            filters['impact_category']
        )
        
        if not filtered_data:
            st.error("Error filtering data")
            st.stop()

        st.sidebar.caption(f"Last updated: {datetime.date.today().strftime('%m/%d/%Y')}")
        st.sidebar.markdown("---")
        
        # Add dashboard login option for external users
        show_dashboard_login_sidebar()
        
        st.sidebar.title("Navigation")
        
        nav_options = ["Executive Summary", "Estimating", "Preconstruction", "Construction", "Closeout"]
        page_selection = st.sidebar.radio("Page Navigation", nav_options, label_visibility="collapsed")

        if page_selection == "Executive Summary":
            display_executive_summary(filtered_data, summary_for_impact_calc, filters['impact_category'], filters)
        else:
            display_phase_summary_page(page_selection.lower(), filtered_data, filters['impact_category'], filters)

        st.markdown(f"""
        <div style="text-align: center; color: #6b7280; font-size: 0.875rem; margin-top: 1rem; padding-bottom: 1rem;">
             <p style="margin-bottom:0.25rem;">&copy; {datetime.date.today().year} Construction Risk AI. All rights reserved.</p>
             <p style-top:0;">Data provided for informational purposes only. Consult with experts for detailed analysis.</p>
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.stop()
    except MemoryError:
        st.error("Out of memory - please try selecting fewer phases or items")
        st.stop()

if __name__ == "__main__":
    main()