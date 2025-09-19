import streamlit as st
import pandas as pd
import datetime
import os
import html
import copy
import re
import boto3
from botocore.exceptions import ClientError

# --- Page Configuration (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(page_title="CR-Score Dashboard (Construction View)", layout="wide")

# --- App Configuration ---

# --- Define the specific categories for this version of the dashboard ---
ALLOWED_IMPACT_CATEGORIES = ['Schedule', 'Cost', 'Safety']

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
    "Schedule": {"multiplier": 0.40, "suffix": "improvement"},
    "Cost": {"multiplier": 0.20, "suffix": "improvement"},
    "Safety": {"multiplier": 0.80, "suffix": "improvement"}
}

PHASE_IMPACT_CONFIG = {
    "estimating": {
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

# --- Procore item type to phase mapping ---
ITEM_TYPE_TO_PHASE = {
    "rfi": "construction",
    "submittal": "construction", 
    "observation": "construction",
    "incident": "construction",
    "punch_item": "closeout",
    "prime_contract_change_order": "construction",
    "prime_contract_invoice_payment": "construction"
}

# --- KPI Tooltip Definitions ---
KPI_TOOLTIP_DEFINITIONS = {
    "RFI Avg Create Date": "Avg Date RFIs are created as percent of project completion. This measures if RFIs are created consistently throughout the entire project.",
    "RFI Avg Time to Resolution": "Avg number of days taken to close RFIs.",
    "RFI % On Time": "Percent of RFIs closed before the due date.",
    "RFI AverageLead Time": "Avg number of days given to close RFIs when they are created.",
    "RFI Usage Rate": "Number of RFIs divided by number of Project Days.",
    "RFI Documentation Quality": "Percent of critical details provided with RFIs including: Due Date, Close Date, Description, Assignees, etc.",
    "RFIs Avg Create Date": "Avg Date RFIs are created as percent of project completion. This measures if RFIs are created consistently throughout the entire project.",
    "RFIs Avg Days to Close": "Avg number of days taken to close RFIs.",
    "RFIs Closed on Time": "Percent of RFIs closed before the due date.",
    "RFIs Lead Time": "Avg number of days given to close RFIs when they are created.",
    "RFIs Usage Rate": "Number of RFIs divided by number of Project Days.",
    "Submittals Avg Create Date": "Avg Date Submittals are created as a percent of project completion.",
    "Submittals Average Time to Resolution": "Avg number of days taken to close Submittals.",
    "Submittals % Resolved on Time": "Percent of Submittals closed before the due date.",
    "Submittals Average Lead Time": "Avg number of days given to close Submittals when they are created.",
    "Submittals Usage Rate": "Number of Submittals divided by number of Project Days.",
    "Submittals Documentation Quality": "Percent of critical details provided with Submittals including: Due Date, Close Date, Description, Assignees, etc.",
    "Submittals Avg Days to Close": "Avg number of days taken to close Submittals.",
    "Submittals Closed on Time": "Percent of Submittals closed before the due date.",
    "Submittals Lead Time": "Avg number of days given to close Submittals when they are created.",
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
    "Budget Revision Rate": "Percent of Budget Items that have revisions.",
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
    "Observations Avg Days to Close": "Avg number of days taken to close Observations.",
    "Observations Avg Lead Time": "Avg number of days given to close Observations when they are created.",
    "Observations Closed on Time": "Percent of Observations closed before the due date.",
    "Quality Inspection Rate": "Number of Quality Inspections divided by number of Project Days.",
    "Quality Inspections Conforming Rate": "Percent of Quality Inspection Items found Conforming.",
    "Quality Inspections Deficiency Rate": "Percent of Quality Inspection Items found Deficient.",
    "Safety Inspection Rate": "Number of Safety Inspections divided by number of Project Days.",
    "Safety Inspection Conforming Rate": "Percent of Safety Inspection Items found Conforming.",
    "Safety Inspection Deficiency Rate": "Percent of Safety Inspection Items found Deficient.",
    "Incident Detail Quality": "Percent of critical details provided with Incidents including: Description, Assignees, Contributing Behavior, Contributing Conditions, etc.",
    "Incident Rate": "Number of Incidents divided by number of Project Days.",
    "Change Order Time to Close": "Avg Time to complete Change Orders.",
    "Change Order to Budget Ratio": "Percent increase in Project Costs due to Change Orders.",
    "Contract to Budget Ratio (Deviation)": "Contract Total to Budget Total, this should be very near 1 to 1.",
    "Invoice to Contract Ratio (Deviation)": "Invoice Total to Contract Total, this should roughly correspond to the percent of project completion and by the end of the project be 1 to 1.",
    "Payments to Invoices Ratio (Deviation)": "Payment Total to Invoice Total, this should be 1 to 1 by the end of the project."
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

# --- S3 Helper Functions ---
@st.cache_data(ttl=60)  # Cache for 1 minute only
def download_file_from_s3(filename):
    """Download a file from S3 and return as pandas DataFrame."""
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
@st.cache_data(ttl=60)  # Cache for 1 minute only
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

def create_column_header_tooltip(header_text, tooltip_text):
    """Create a tooltip-enabled column header."""
    tooltip_html = f"""
    <div class="tooltip">
        <strong>{html.escape(header_text)}</strong>
        <span class="tooltiptext">{html.escape(tooltip_text)}</span>
    </div>
    """
    return tooltip_html

def score_to_grade(score):
    """Convert numerical score to letter grade."""
    if score >= 80:
        return 'A'
    elif score >= 60:
        return 'B'
    elif score >= 40:
        return 'C'
    elif score >= 20:
        return 'D'
    else:
        return 'F'

def grade_to_color(grade):
    """Get color for grade based on score bar colors."""
    grade_colors = {
        'A': '#006400',  # Dark green (right side of score bars)
        'B': '#90EE90',  # Light green (yellow + dark green mix)
        'C': '#FFD700',  # Yellow (like score bars)
        'D': '#FF8C00',  # Orange (red + yellow mix)
        'F': '#DC143C'   # Red (left side of score bars)
    }
    return grade_colors.get(grade, '#000000')

def create_styled_grade(score):
    """Create styled grade HTML with color and black outline."""
    grade = score_to_grade(score)
    color = grade_to_color(grade)
    
    return f"""
    <div style="
        display: inline-block;
        font-weight: bold;
        font-size: 1.1rem;
        color: {color};
        text-shadow: 
            -1px -1px 0 #000,
            1px -1px 0 #000,
            -1px 1px 0 #000,
            1px 1px 0 #000;
        text-align: center;
        padding: 2px 8px;
    ">{grade}</div>
    """

def display_kpi_table(kpi_df):
    if kpi_df.empty:
        st.info("No KPI data for this process and selected impact category.")
        return
    
    # Inject tooltip CSS
    st.markdown(TOOLTIP_CSS, unsafe_allow_html=True)
    
    kpi_df_copy = kpi_df.copy()
    kpi_df_copy['actual_numeric'] = kpi_df_copy['actual'].apply(parse_value)
    
    # Comment out KPIs with zero weight that confuse users
    # TODO: May want to re-enable these in the future with proper weights
    kpi_df_copy = kpi_df_copy[~kpi_df_copy['kpi_name'].isin([
        'Prime Contract Late Payment Rate',
        'Prime Contract Underpayment Rate'
    ])]
    
    num_projects = kpi_df_copy['projectId'].nunique()
    is_averaged = num_projects > 1
    
    # Calculate % of Projects for each KPI (dynamic based on current filters)
    total_filtered_projects = num_projects
    kpi_project_coverage = kpi_df_copy.groupby('kpi_name').apply(
        lambda x: (x['actual_numeric'].notna().sum() / total_filtered_projects) * 100
    ).reset_index(name='percent_of_projects')
    
    if is_averaged:
        display_df = kpi_df_copy.groupby('kpi_name').agg(
            actual_numeric=('actual_numeric', 'mean'), score=('score', 'mean'),
            unrealized_value=('unrealized_value', 'mean'), bp_range_display=('bp_range_display', 'first'),
            unit=('unit', 'first')).reset_index()
        
        # Merge the % of Projects data
        display_df = display_df.merge(kpi_project_coverage, on='kpi_name', how='left')
        # Convert score from 0-1 to 0-100 for display
        display_df['score'] = display_df['score'] * 100
    else:
        display_df = kpi_df_copy.rename(columns={'actual_numeric': 'actual_numeric'})
        # For single project, merge the % of Projects data
        display_df = display_df.merge(kpi_project_coverage, on='kpi_name', how='left')
        # Convert score from 0-1 to 0-100 for display
        display_df['score'] = display_df['score'] * 100

    # Add Priority ranking based on unrealized_value (highest = 1, next = 2, etc.)
    display_df = display_df.sort_values('unrealized_value', ascending=False).reset_index(drop=True)
    display_df['priority'] = range(1, len(display_df) + 1)

    with st.container(border=True):
        header_cols = st.columns([0.08, 0.32, 0.12, 0.2, 0.13, 0.15])
        
        # Create tooltipped headers
        priority_header = create_column_header_tooltip("Priority", "rank of kpis based on which ones have the biggest opportunity to improve the score")
        kpi_name_header = create_column_header_tooltip("KPI Name", "measure of correct and valuable use of software to improve an operational metric")
        percent_projects_header = create_column_header_tooltip("% of Projects", "percentage of filtered projects that have data for this KPI")
        best_practice_header = create_column_header_tooltip("Best Practice", "ideal target for the kpi - where contractor behavior is optimized")
        actual_header = create_column_header_tooltip("Actual (Avg)" if is_averaged else "Actual", "the kpi value for the projects selected in the filter")
        grade_header = create_column_header_tooltip("Grade", "Assessment of the Actual KPI value against the Best Practice")
        
        header_cols[0].markdown(priority_header, unsafe_allow_html=True)
        header_cols[1].markdown(kpi_name_header, unsafe_allow_html=True)
        header_cols[2].markdown(percent_projects_header, unsafe_allow_html=True)
        header_cols[3].markdown(best_practice_header, unsafe_allow_html=True)
        header_cols[4].markdown(actual_header, unsafe_allow_html=True)
        header_cols[5].markdown(grade_header, unsafe_allow_html=True)
        
        for _, row in display_df.iterrows():
            row_cols = st.columns([0.08, 0.32, 0.12, 0.2, 0.13, 0.15])
            actual_val = row['actual_numeric']
            unit = row.get('unit', '')
            actual_display = f"{actual_val:.0%}" if unit == '%' else f"{actual_val:.1f}"
            
            # Priority column (first) - shows ranking instead of potential value
            row_cols[0].write(f"{row['priority']}")
            
            # Use tooltip for KPI name (second)
            kpi_name = str(row.get('kpi_name', 'N/A'))
            tooltip_html = create_kpi_tooltip(kpi_name)
            row_cols[1].markdown(tooltip_html, unsafe_allow_html=True)
            
            # % of Projects column (third)
            percent_projects = row.get('percent_of_projects', 0)
            row_cols[2].write(f"{percent_projects:.0f}%")
            
            # Rest of the columns
            row_cols[3].write(html.escape(str(row.get('bp_range_display', 'N/A'))))
            row_cols[4].write(actual_display)
            
            # Grade column with styled letter grade
            score_value = row.get('score', 0)
            styled_grade = create_styled_grade(score_value)
            row_cols[5].markdown(styled_grade, unsafe_allow_html=True)

def format_process_name(name):
    if name in PROCESS_DISPLAY_NAMES: return PROCESS_DISPLAY_NAMES[name]
    return re.sub(r"(\w)([A-Z])", r"\1 \2", name).title()

def display_top_action_items(page_key, project_filter=None, region_filter=None, pm_filter=None):
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

    # Apply region filter if specified
    if region_filter and region_filter != 'All Regions':
        if 'region' in procore_df.columns:
            procore_df = procore_df[procore_df['region'].astype(str) == str(region_filter)]

    # Apply project manager filter if specified
    if pm_filter and pm_filter != 'All PMs':
        if 'projectManager' in procore_df.columns:
            procore_df = procore_df[procore_df['projectManager'].astype(str) == str(pm_filter)]

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


# --- Data Loading Function ---
@st.cache_data(ttl=60)  # Cache for 1 minute only
def load_data():
    """Load all dashboard data from S3."""
    data = {}
    try:
        # Load executive summary
        summary_df = download_file_from_s3("executive_summary.csv")
        if not summary_df.empty:
            # Additional safety check for duplicates (already handled in download function)
            data['executive_summary'] = summary_df[summary_df['impact_category'].isin(ALLOWED_IMPACT_CATEGORIES)]
        else:
            st.warning("Executive summary data not found in S3.")
            data['executive_summary'] = pd.DataFrame()
        
        # Load phase data
        for phase in ['estimating', 'preconstruction', 'construction', 'closeout']:
            processes_file = f"{phase}_processes.csv"
            kpis_file = f"{phase}_kpis.csv"
            
            df_p = download_file_from_s3(processes_file)
            df_k = download_file_from_s3(kpis_file)
            
            if not df_p.empty and not df_k.empty:
                # Add phase column to KPIs
                df_k = df_k.copy()
                df_k['phase'] = phase.capitalize()

                # Standardize column names
                if 'project_id' in df_p.columns: df_p.rename(columns={'project_id': 'projectId'}, inplace=True)
                if 'project_id' in df_k.columns: df_k.rename(columns={'project_id': 'projectId'}, inplace=True)
                
                data[phase] = {'processes': df_p, 'kpis': df_k}
            else:
                st.warning(f"Data for {phase} phase not found in S3.")
        
        return data
    except Exception as e:
        st.error(f"An unexpected error occurred loading data from S3: {e}")
        return None

# --- Display Functions ---
def display_executive_summary(data, summary_for_impact_calc, impact_category_filter, filters):
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
        phase_definitions = {"Estimating": {"col": "phaseScore_estimating", "desc": "selecting what jobs to bid on and building estimates"},"Precon": {"col": "phaseScore_preconstruction", "desc": "For bids that are won, all the project preparation"},"Construction": {"col": "phaseScore_construction", "desc": "executing the plan and completing the project"},"Closeout": {"col": "phaseScore_closeout", "desc": "wrap up of all work and handoff to the customer"}}
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
        display_top_action_items("executive_summary", filters['project'], filters['region'], filters['pm'])


def display_phase_summary_page(phase_key, data, impact_category_filter, filters):
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
        display_top_action_items(phase_key, filters['project'], filters['region'], filters['pm'])

# --- Main Application ---
def main():
    original_data = load_data()
    if not original_data: st.stop()
    
    # Debug: Show all KPI definitions
    st.sidebar.title("🔍 KPI Definitions Debug")
    
    if st.sidebar.button("Clear All Caches"):
        st.cache_data.clear()
        st.success("All caches cleared! Please refresh the page.")
    
    if st.sidebar.button("Show All KPI Definitions"):
        st.markdown("## All KPI Definitions")
        st.markdown("**Total KPIs defined:** " + str(len(KPI_TOOLTIP_DEFINITIONS)))
        
        # Create two columns for KPI name and definition
        col1, col2 = st.columns([0.4, 0.6])
        with col1:
            st.markdown("**KPI Name**")
        with col2:
            st.markdown("**Definition**")
        
        for kpi_name, definition in KPI_TOOLTIP_DEFINITIONS.items():
            col1, col2 = st.columns([0.4, 0.6])
            with col1:
                st.text(kpi_name)
            with col2:
                st.text(definition)
        
        st.markdown("---")
    
    st.sidebar.title("Global Filters")
    unfiltered_summary_df = original_data.get('executive_summary', pd.DataFrame())
    if not unfiltered_summary_df.empty:
        # Convert to string and filter out NaN values to prevent sorting errors
        project_ids = sorted([str(x) for x in unfiltered_summary_df['projectId'].unique() if pd.notna(x)])
        regions = sorted([str(x) for x in unfiltered_summary_df['region'].unique() if pd.notna(x)])
        pms = sorted([str(x) for x in unfiltered_summary_df['projectManager'].unique() if pd.notna(x)])
        impact_categories = sorted([str(x) for x in unfiltered_summary_df['impact_category'].unique() if pd.notna(x)])
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
    if filters['project'] != 'All Projects': 
        summary_for_impact_calc = summary_for_impact_calc[summary_for_impact_calc['projectId'].astype(str) == filters['project']]
    if filters['region'] != 'All Regions': 
        summary_for_impact_calc = summary_for_impact_calc[summary_for_impact_calc['region'].astype(str) == filters['region']]
    if filters['pm'] != 'All PMs': 
        summary_for_impact_calc = summary_for_impact_calc[summary_for_impact_calc['projectManager'].astype(str) == filters['pm']]

    summary_df = summary_for_impact_calc.copy()
    summary_df = summary_df[summary_df['impact_category'] == filters['impact_category']]
    
    filtered_data = copy.deepcopy(original_data)
    filtered_data['executive_summary'] = summary_df
    
    final_filtered_project_ids = summary_df['projectId'].unique()
    for phase in PHASE_INFO.keys():
        if phase in filtered_data:
            # Get copies of the data
            processes_df = filtered_data[phase]['processes'].copy()
            kpis_df = filtered_data[phase]['kpis'].copy()
            
            if len(final_filtered_project_ids) > 0:
                # Clean and prepare the data - handle duplicates and missing values carefully
                processes_df = processes_df.drop_duplicates().reset_index(drop=True)
                kpis_df = kpis_df.drop_duplicates().reset_index(drop=True)
                
                # Use simple filtering approach that avoids multidimensional indexing
                processes_filtered = processes_df[processes_df['projectId'].isin(final_filtered_project_ids)].copy()
                kpis_filtered = kpis_df[kpis_df['projectId'].isin(final_filtered_project_ids)].copy()
                
                # Reset indices to ensure clean sequential indexing
                filtered_data[phase]['processes'] = processes_filtered.reset_index(drop=True)
                filtered_data[phase]['kpis'] = kpis_filtered.reset_index(drop=True)

    st.sidebar.caption(f"Last updated: {datetime.date.today().strftime('%m/%d/%Y')}")
    st.sidebar.markdown("---")
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

if __name__ == "__main__":
    main()