import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import datetime
import os
import html
import copy
import re
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Page Configuration (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(page_title="CR-Score Dashboard (Construction View)", layout="wide")

# Style primary buttons as professional blue with bold labels.
st.markdown(
    """
    <style>
    div[data-testid="stAppViewContainer"] > section[data-testid="stMain"] > div[data-testid="stMainBlockContainer"] {
        padding-top: 1rem !important;
    }
    .block-container {
        padding-top: 1rem !important;
    }
    div.stButton > button[kind="primary"] {
        background-color: #1d4ed8;
        color: white;
        font-weight: 700;
        border: 1px solid #1e40af;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #1e40af;
        color: white;
        border: 1px solid #1e3a8a;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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

PROCESS_DESCRIPTIONS = {
    # Bidding
    "bidreview": "Go/no-go rigor and scope discipline at the bid review stage directly shape downstream project margins. Indicators here reflect how thoroughly opportunities are vetted before resources are committed.",
    "bidresults": "Winning the right work at the right price is central to sustainable growth. Performance here reveals how accurately bid estimates translate into profitable outcomes across win rate, cost variance, and margin.",
    "estimating": "Estimate accuracy is a leading indicator of project financial health. Coverage of sub-trade pricing and variance across trades signal whether scope is fully understood before submission.",
    "compliance": "Unqualified subcontractors introduce legal, financial, and safety exposure across the project. Licensing, insurance, and prequalification adherence across the sub pool is measured here.",
    # Preconstruction
    "financialSetup": "A project's financial trajectory is largely set before a shovel hits the ground. How closely preconstruction budgets align with original bids — and whether contingency reserves are adequately established — are measured here.",
    "designReview": "Coordination conflicts caught in preconstruction cost a fraction of what they cost in the field. Clash detection rates, BIM alignment, and drawing standardization reflect coordination effectiveness before construction begins.",
    "subcontractorPlanning": "Delayed contract execution cascades into mobilization setbacks and compounding schedule risk. Speed from awarded scope to signed contracts and field-ready subcontractors is what this section quantifies.",
    # Construction
    "operations": "Slow field coordination compounds schedule pressure and raises the risk of costly rework. RFI and submittal cycle times, observation completion rates, and overall field responsiveness are measured here.",
    "quality": "Quality deficiencies caught late are exponentially more expensive to correct. Inspection frequency, punch list trends, and adherence to quality control protocols on active sites are reflected in this score.",
    "safety": "A proactive safety culture prevents incidents before they occur. Leading indicators — inspection rates, near-miss documentation, and hazard identification frequency — are weighted alongside lagging incident data here.",
    "financial": "Financial performance on active projects hinges on timely change order processing and invoice cycle discipline. Cost control effectiveness and cash flow management during construction are assessed in this section.",
    "communication": "Consistent documentation is the backbone of defensible project management. Reliability of daily field logs, meeting records, and internal reporting cadence are reflected here.",
    # Closeout
    "finalDocumentation": "Complete closeout documentation protects the owner and reduces post-occupancy risk. How thoroughly as-built drawings, O&M manuals, and project records are assembled before final handover is measured here.",
    "punchlistCompletion": "An unresolved punch list is a direct barrier to final payment and owner acceptance. Efficiency in identifying, assigning, and closing outstanding items prior to substantial completion is quantified in this section.",
    "financialReconciliation": "Closing financial obligations cleanly is a hallmark of well-run projects. Promptness of final invoice receipt and subcontractor payment issuance following project completion are assessed here.",
    "clientHandover": "The owner's experience at handover shapes long-term relationship value and future referrals. Satisfaction at turnover and the completeness of operational training delivered before the team demobilizes are reflected in this score."
}


# --- Filter the configuration dictionaries to match the allowed categories ---
IMPACT_CATEGORY_CONFIG = {
    "Schedule": {"multiplier": 0.61, "suffix": "Avg reduction in Schedule overrage"},
    "Cost": {"multiplier": 0.65, "suffix": "Avg reduction in Cost overrage"},
    "Safety": {"multiplier": 0.70, "suffix": "Avg reduction in Incidents"}
}

PHASE_IMPACT_CONFIG = {
    "bidding": {
        "Schedule": {"multiplier": 0.02, "suffix": "Avg reduction in Schedule overrage"},
        "Cost": {"multiplier": 0.06, "suffix": "Avg reduction in Cost overrage"},
        "Safety": {"multiplier": 0.08, "suffix": "Avg reduction in Incidents"}
    },
    "preconstruction": {
        "Schedule": {"multiplier": 0.16, "suffix": "Avg reduction in Schedule overrage"},
        "Cost": {"multiplier": 0.05, "suffix": "Avg reduction in Cost overrage"},
        "Safety": {"multiplier": 0.20, "suffix": "Avg reduction in Incidents"}
    },
    "construction": {
        "Schedule": {"multiplier": 0.20, "suffix": "Avg reduction in Schedule overrage"},
        "Cost": {"multiplier": 0.08, "suffix": "Avg reduction in Cost overrage"},
        "Safety": {"multiplier": 0.48, "suffix": "Avg reduction in Incidents"}
    },
    "closeout": {
        "Schedule": {"multiplier": 0.02, "suffix": "Avg reduction in Schedule overrage"},
        "Cost": {"multiplier": 0.01, "suffix": "Avg reduction in Cost overrage"},
        "Safety": {"multiplier": 0.04, "suffix": "Avg reduction in Incidents"}
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
def horizontal_risk_bar_html(score, height='1.65rem', font_size='1.2rem', top_offset='-1.8rem', width_percentage=100, box_height=None):
    score = int(score) if pd.notna(score) else 0
    indicator_position = f"{score}%"
    gradient = "linear-gradient(to right, #ef4444 0%, #facc15 50%, #16a34a 100%)"
    score_color = "black"
    box_height_style = f"height: {box_height}; line-height: 1; overflow: visible;" if box_height else ""
    html_content = f"""
    <div style="width: {width_percentage}%; position: relative; margin-top: 0.75rem; margin-bottom: 1.2rem;">
        <div style="width: 100%; background-color: #e5e7eb; border-radius: 9999px; height: {height}; position: relative;">
            <div style="height: 100%; border-radius: 9999px; background: {gradient};"></div>
            <div style="position: absolute; top: 0; bottom: 0; left: {indicator_position}; width: 3px; background-color: black; transform: translateX(-50%); z-index: 10;"></div>
            <span style="position: absolute; top: {top_offset}; left: {indicator_position}; transform: translateX(-50%); color: {score_color}; font-weight: bold; font-size: {font_size}; white-space: nowrap; z-index: 20; background-color: white; padding: 0 0.3rem; border-radius: 0.25rem; border: 1px solid #d1d5db; display: inline-flex; align-items: center; justify-content: center; {box_height_style}">
                {html.escape(str(score))}
            </span>
        </div>
        <span style="position: absolute; top: 100%; left: 0; margin-top: 1px; font-weight:700;">0</span>
        <span style="position: absolute; top: 100%; right: 0%; transform: translateX(50%); font-weight:700;">100</span>
    </div>
    """
    return html_content

def circular_score_meter_html(score, size=220):
    score = float(score) if pd.notna(score) else 0
    score = max(0, min(score, 100))

    def polar_to_cartesian(cx, cy, radius, angle_deg):
        angle_rad = math.radians(angle_deg)
        return cx + radius * math.cos(angle_rad), cy - radius * math.sin(angle_rad)

    def arc_path(cx, cy, radius, start_angle, end_angle):
        start_x, start_y = polar_to_cartesian(cx, cy, radius, start_angle)
        end_x, end_y = polar_to_cartesian(cx, cy, radius, end_angle)
        large_arc_flag = 1 if abs(end_angle - start_angle) > 180 else 0
        sweep_flag = 1 if end_angle < start_angle else 0
        return f"M {start_x:.2f} {start_y:.2f} A {radius:.2f} {radius:.2f} 0 {large_arc_flag} {sweep_flag} {end_x:.2f} {end_y:.2f}"

    cx, cy = 110, 122
    radius = 74
    start_angle = 210
    total_sweep = 240
    segment_span = total_sweep / 5
    gap = 3.0
    segment_colors = ["#ef4444", "#f97316", "#fbbf24", "#86efac", "#16a34a"]

    segment_paths = []
    for index, color in enumerate(segment_colors):
        seg_start = start_angle - (index * segment_span)
        seg_end = seg_start - (segment_span - gap)
        segment_paths.append(
            f'<path d="{arc_path(cx, cy, radius, seg_start, seg_end)}" fill="none" stroke="{color}" stroke-width="24" stroke-linecap="butt"></path>'
        )

    tick_labels = []
    for value in range(0, 101, 20):
        angle = start_angle - ((value / 100.0) * total_sweep)
        label_x, label_y = polar_to_cartesian(cx, cy, radius + 28, angle)
        tick_labels.append(
            f'<text x="{label_x:.2f}" y="{label_y:.2f}" text-anchor="middle" dominant-baseline="middle" font-size="16" font-weight="800" fill="#111827">{value}</text>'
        )

    needle_angle = start_angle - ((score / 100.0) * total_sweep)
    needle_x, needle_y = polar_to_cartesian(cx, cy, radius - 22, needle_angle)

    html_content = f"""
    <div style="display:flex; justify-content:center; align-items:center; width:100%; margin:0.25rem 0 0 0;">
        <svg width="{size}" height="{int(size * 0.82)}" viewBox="0 0 220 220">
            {''.join(segment_paths)}
            {''.join(tick_labels)}
            <circle cx="{cx}" cy="{cy}" r="48" fill="white" stroke="#d1d5db" stroke-width="2"></circle>
            <line x1="{cx}" y1="{cy}" x2="{needle_x:.2f}" y2="{needle_y:.2f}" stroke="#1f2937" stroke-width="4" stroke-linecap="round"></line>
            <circle cx="{cx}" cy="{cy}" r="6" fill="#1f2937"></circle>
            <text x="{cx}" y="{cy + 29}" text-anchor="middle" font-size="34" font-weight="800" fill="#111827">{score:.0f}</text>
        </svg>
    </div>
    """
    return html_content

def risk_reduction_bar_html(value, max_value, height='1.0rem', font_size='0.8rem'):
    """Create a horizontal bar chart for improvement percentages"""
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

def format_kpi_name(kpi_name):
    return str(kpi_name or "N/A").upper()

KPI_GUIDANCE_MAP = {
    '% of bids targeted': 'Tighten go/no-go criteria by market, client, and margin profile so bid effort focuses on highest win-probability opportunities.',
    'as-built drawing accuracy': 'Run weekly as-built QA checks with field engineers and require redline updates before each pay-app cycle.',
    'avg days to submit bid': 'Standardize bid kickoff templates and intermediate deadlines to compress estimating cycle time without reducing quality.',
    'avg number of sub quotes per trade': 'Expand bidder lists per trade and set minimum quote coverage targets before final estimate lock.',
    'avg selected sub emr': 'Prioritize subcontractors with stronger safety records and require mitigation plans when EMR exceeds target.',
    'avg sub quote variance': 'Normalize scope sheets across bidders and hold scope leveling reviews to reduce spread caused by assumptions.',
    'avg sub response rate': 'Issue bid invites earlier and automate reminder cadences to increase subcontractor response participation.',
    'avg time to close punch item': 'Assign trade owner and due date to each punch item, then track aging in daily closeout huddles.',
    'avg time to submit bid': 'Preload historical assemblies and vendor pricing to cut estimate build time for repeat project types.',
    'bid package completeness rate': 'Use package completeness checklists before release to eliminate missing scope and addenda gaps.',
    'bid rate per $1m of acv': 'Improve bid efficiency by reusing estimate components and limiting bids with low strategic fit.',
    'bid win rate': 'Perform bid debriefs by segment and refine pricing strategy where losses consistently exceed threshold.',
    'budgets create date': 'Set a post-award budget creation SLA and enforce it through project startup readiness gates.',
    'budgets usage rate': 'Make budget adherence visible in weekly cost reviews and require explanations for off-budget commitments.',
    'change order time to close': 'Create a fast-lane review workflow for pending change orders with clear owner and approval SLA.',
    'change order to budget ratio': 'Reduce scope churn by validating design and owner decisions earlier in preconstruction.',
    'client satisfaction score': 'Close client feedback loops monthly and assign action plans to recurring service pain points.',
    'client training completion': 'Schedule owner training milestones before turnover and require signoff for each trained system.',
    'compliance matrix completion rate': 'Track matrix completion weekly and escalate unresolved compliance items ahead of critical gates.',
    'contract to budget ratio (deviation)': 'Reconcile contract values to control budget early and review deviations before procurement starts.',
    'cost variance': 'Run variance-to-budget review weekly and trigger corrective action when any cost code drifts beyond threshold.',
    'daily logs delay': 'Set same-day log submission standards and alert superintendents when logs are missing or late.',
    'daily logs rate': 'Increase reporting consistency with mobile log prompts and end-of-day completion checks.',
    'final payment received time': 'Submit complete closeout packages earlier and track owner payment blockers to resolution.',
    'incident detail quality': 'Use a structured incident template and supervisor review to improve root-cause quality in reports.',
    'incident rate': 'Focus on pre-task planning, high-risk activity controls, and rapid closure of corrective actions.',
    'invoice to contract ratio (deviation)': 'Audit billing against contract milestones to prevent over/under billing drift.',
    'licensing & certification compliance rate': 'Maintain a rolling credential register and block assignments for expired certifications.',
    'meetings documentation': 'Standardize meeting minutes with decisions, owners, and due dates published within 24 hours.',
    'meetings rate': 'Set recurring coordination cadence and enforce attendance for critical project functions.',
    'near miss detail quality': 'Capture near-miss narratives with clear causal factors to improve preventive action quality.',
    'near miss rate': 'Encourage reporting and trend near misses by activity type to target preventive controls.',
    'o&m manuals submitted timely': 'Track O&M submittals by system and require trade turnover checklists ahead of handoff.',
    'observation rate': 'Increase field observation frequency with scheduled safety walks and supervisor accountability.',
    'observations closed on time': 'Assign close dates during observation entry and escalate overdue items in safety meetings.',
    'payments to invoices ratio (deviation)': 'Align payment release workflow to approved invoices and resolve disputed line items quickly.',
    'profit variance': 'Review forecasted margin monthly and intervene early on labor productivity or procurement overrun trends.',
    'punch list items closed rate': 'Use zone-based closeout plans and trade-specific closure targets to maintain turnover pace.',
    'quality insp. attach. rate': 'Require photo/document evidence on all quality inspections before closeout approval.',
    'quality inspection rate': 'Set minimum inspection coverage by work package and track completion against plan.',
    'rfis closed on time': 'Publish RFI aging dashboards and enforce turnaround SLAs with design and consultant teams.',
    'rfis lead time': 'Prioritize critical-path RFIs and route them through expedited review with clear ownership.',
    'rfis rate': 'Reduce avoidable RFIs via pre-install coordination and design clarification workshops.',
    'safety insp. attach. rate': 'Require visual proof and corrective evidence for all safety inspections to ensure closure quality.',
    'safety inspection rate': 'Increase planned safety inspection frequency and tie completion to supervisor KPIs.',
    'safety training': 'Close training gaps with role-based refreshers and track completion before high-risk work starts.',
    'schedule variance': 'Use look-ahead planning and constraint removal to recover tasks drifting off baseline.',
    'sub prequal rate': 'Broaden and maintain a prequalified vendor pool to improve competition and reduce procurement risk.',
    'subcontractor final payments': 'Link final payment release to complete closeout deliverables and verified lien documentation.',
    'submittals closed on time': 'Track submittal aging by reviewer and escalate overdue approvals before they hit critical path.',
    'submittals lead time': 'Submit long-lead packages first and lock reviewer turnaround commitments upfront.',
    'submittals rate': 'Improve planning by mapping required submittals to upcoming work packages earlier.',
    'avg insurance acquired cycle': 'Pre-collect insurance requirements and automate follow-ups to shorten policy acquisition cycle time.',
    'avg permit approval cycle': 'Engage permitting authorities early and submit complete packages to reduce review rework.',
    'avg sub coi received time': 'Set COI deadlines at award and automate reminders until compliant certificates are received.',
    'budget to bid variance': 'Improve estimate handoff quality and scope alignment to reduce budget drift after award.',
    'clash detection rate': 'Run model coordination at fixed intervals and require closure of high-severity clashes before release.',
    'contingency adequacy': 'Calibrate contingency by risk register trends and adjust allowances as uncertainty resolves.',
    'days until sub contracts executed': 'Use contract execution trackers and pre-negotiate key terms to accelerate signature turnaround.',
    'drawings usage': 'Drive adoption of current drawing sets through mobile access and version-control checks in the field.',
    'equipment cost variance': 'Track equipment utilization versus plan and redeploy underused assets to cut variance.',
    'gantt chart completion rate': 'Enforce schedule update discipline weekly so plan progress reflects real execution status.',
    'labor cost variance': 'Monitor labor productivity by crew and shift resources where earned-value trends deteriorate.',
    'materials cost variance': 'Lock buyout pricing early and monitor material quantity deltas against takeoff baselines.',
    'permit submission timeliness': 'Build permit deliverables into preconstruction milestones and enforce submit-by dates.',
    'photos usage': 'Standardize photo capture requirements by activity to strengthen documentation and quality validation.',
    'prime contract to budget variance': 'Align scope interpretation between prime contract and control budget during startup.',
    'schedule to bid variance': 'Validate bid assumptions against detailed execution logic before final baseline approval.',
    'specifications usage': 'Improve spec compliance by requiring scope teams to reference spec sections during planning and QA.'
}

KPI_STRENGTH_MAP = {
    '% of bids targeted': 'A strong result shows the team is focusing effort on the right opportunities instead of spreading resources across low-fit pursuits.',
    'as-built drawing accuracy': 'A strong result shows field conditions are being documented correctly, which lowers rework, warranty, and turnover risk.',
    'avg days to submit bid': 'A strong result shows the estimating team can respond quickly without delaying pipeline decisions.',
    'avg number of sub quotes per trade': 'A strong result shows good market coverage, which improves pricing confidence and reduces buyout risk.',
    'avg selected sub emr': 'A strong result shows safer subcontractor selection, which lowers incident exposure during execution.',
    'avg sub quote variance': 'A strong result shows scope alignment across bidders, which reduces pricing uncertainty and missed scope risk.',
    'avg sub response rate': 'A strong result shows healthy subcontractor engagement, which improves estimate quality and procurement flexibility.',
    'avg time to close punch item': 'A strong result shows the team resolves finish issues quickly, reducing turnover delays and owner dissatisfaction.',
    'avg time to submit bid': 'A strong result shows the preconstruction process is efficient and responsive under deadline pressure.',
    'bid package completeness rate': 'A strong result shows scope packages are well prepared, which lowers bidder confusion and post-award scope gaps.',
    'bid rate per $1m of acv': 'A strong result shows bid effort is being used efficiently relative to available contract value.',
    'bid win rate': 'A strong result shows the company is pursuing and pricing work effectively, which indicates strong market discipline.',
    'budgets create date': 'A strong result shows projects are financially organized early, reducing startup confusion and cost control risk.',
    'budgets usage rate': 'A strong result shows the budget is actively guiding decisions, which supports stronger cost governance.',
    'change order time to close': 'A strong result shows scope changes are resolved quickly, reducing revenue leakage and schedule disruption.',
    'change order to budget ratio': 'A strong result shows scope is stable and well controlled, which lowers commercial and execution risk.',
    'client satisfaction score': 'A strong result shows the project team is delivering a positive client experience, lowering relationship and repeat-work risk.',
    'client training completion': 'A strong result shows the owner is prepared to operate the asset, reducing turnover friction and support issues.',
    'compliance matrix completion rate': 'A strong result shows required obligations are being tracked and completed, reducing legal and contractual risk.',
    'contract to budget ratio (deviation)': 'A strong result shows the control budget accurately reflects contract scope, lowering downstream cost surprises.',
    'cost variance': 'A strong result shows the project is staying close to plan financially, which is a direct sign of healthy cost control.',
    'daily logs delay': 'A strong result shows field records are entered promptly, improving decision quality and reducing documentation gaps.',
    'daily logs rate': 'A strong result shows disciplined field reporting, which improves visibility into project conditions and issues.',
    'final payment received time': 'A strong result shows closeout and billing are being completed effectively, improving cash flow reliability.',
    'incident detail quality': 'A strong result shows safety events are documented clearly, which improves learning and corrective action quality.',
    'incident rate': 'A strong result shows the project is controlling hazardous work well, reducing harm and operational disruption.',
    'invoice to contract ratio (deviation)': 'A strong result shows billing stays aligned with contract value, reducing commercial and collection risk.',
    'licensing & certification compliance rate': 'A strong result shows work is being performed by properly qualified parties, lowering regulatory and safety risk.',
    'meetings documentation': 'A strong result shows decisions and action items are captured well, reducing coordination failures and ambiguity.',
    'meetings rate': 'A strong result shows the team maintains consistent coordination rhythm, which lowers communication breakdowns.',
    'near miss detail quality': 'A strong result shows the team documents weak signals well, improving prevention before incidents occur.',
    'near miss rate': 'A strong result shows hazards are being surfaced and monitored, which supports proactive risk reduction.',
    'o&m manuals submitted timely': 'A strong result shows turnover requirements are under control, reducing late closeout and owner readiness risk.',
    'observation rate': 'A strong result shows the team is actively looking for unsafe conditions, which strengthens leading-indicator safety management.',
    'observations closed on time': 'A strong result shows issues are being acted on quickly, lowering the chance that known risks remain open.',
    'payments to invoices ratio (deviation)': 'A strong result shows payment execution is staying aligned with invoicing, reducing cash-flow and dispute risk.',
    'profit variance': 'A strong result shows the project is protecting expected margin, which indicates solid operational and financial control.',
    'punch list items closed rate': 'A strong result shows closeout execution is disciplined, reducing turnover delay and reputational risk.',
    'quality insp. attach. rate': 'A strong result shows inspections are backed by evidence, improving accountability and quality assurance confidence.',
    'quality inspection rate': 'A strong result shows the team is checking work consistently, which lowers defect escape and rework risk.',
    'rfis closed on time': 'A strong result shows information gaps are resolved quickly enough to avoid delaying field execution.',
    'rfis lead time': 'A strong result shows questions are being answered within planned windows, reducing waiting and coordination risk.',
    'rfis rate': 'A strong result shows design and field coordination are healthy, reducing confusion that can slow production.',
    'safety insp. attach. rate': 'A strong result shows safety inspections are supported by evidence, improving trust in field verification.',
    'safety inspection rate': 'A strong result shows safety oversight is active and consistent, which lowers exposure to uncontrolled conditions.',
    'safety training': 'A strong result shows workers are being prepared for risk, which supports safer and more reliable execution.',
    'schedule variance': 'A strong result shows the project is performing close to plan, reducing delay risk and recovery pressure.',
    'sub prequal rate': 'A strong result shows the team has a strong vetted subcontractor pool, reducing performance and compliance risk.',
    'subcontractor final payments': 'A strong result shows trade closeout is being completed cleanly, reducing lingering contractual disputes.',
    'submittals closed on time': 'A strong result shows review workflows are supporting production instead of delaying material and equipment release.',
    'submittals lead time': 'A strong result shows submittal cycles are staying within needed time windows, reducing procurement and schedule risk.',
    'submittals rate': 'A strong result shows the team is actively moving required submittals through the pipeline, supporting execution readiness.',
    'avg insurance acquired cycle': 'A strong result shows insurance compliance is secured quickly, reducing startup delay and exposure risk.',
    'avg permit approval cycle': 'A strong result shows regulatory approvals are moving efficiently, reducing schedule uncertainty before work starts.',
    'avg sub coi received time': 'A strong result shows subcontractor insurance documentation is being collected promptly, lowering compliance exposure.',
    'budget to bid variance': 'A strong result shows the handoff from estimate to operating budget is accurate, reducing financial surprises after award.',
    'clash detection rate': 'A strong result shows design coordination issues are being found early, reducing field conflicts and rework.',
    'contingency adequacy': 'A strong result shows the project has realistic protection against uncertainty, lowering downside financial risk.',
    'days until sub contracts executed': 'A strong result shows subcontract agreements are being finalized quickly, reducing procurement and mobilization risk.',
    'drawings usage': 'A strong result shows teams are using current drawings in the field, reducing installation errors and confusion.',
    'equipment cost variance': 'A strong result shows equipment spending is under control, indicating disciplined planning and utilization.',
    'gantt chart completion rate': 'A strong result shows schedule data is being maintained reliably, improving planning and recovery decisions.',
    'labor cost variance': 'A strong result shows labor productivity is tracking to plan, which is a strong indicator of execution health.',
    'materials cost variance': 'A strong result shows procurement and consumption are being controlled well, reducing cost overrun risk.',
    'permit submission timeliness': 'A strong result shows approvals are being pursued on schedule, reducing preventable startup delays.',
    'photos usage': 'A strong result shows project conditions are being documented visually, improving transparency and issue resolution.',
    'prime contract to budget variance': 'A strong result shows scope and budget are aligned early, lowering downstream commercial risk.',
    'schedule to bid variance': 'A strong result shows execution planning is consistent with bid assumptions, reducing delivery risk after award.',
    'specifications usage': 'A strong result shows teams are relying on technical requirements during execution, lowering quality and compliance risk.'
}

def get_kpi_guidance(kpi_name):
    name = str(kpi_name or "").strip()
    lowered = name.lower()

    if lowered in KPI_GUIDANCE_MAP:
        return KPI_GUIDANCE_MAP[lowered]

    if "rfi" in lowered and "lead time" in lowered:
        return "Set a 48-hour response SLA, assign an RFI owner per trade, and triage high-impact RFIs in daily coordination huddles."
    if "rfi" in lowered and "closed on time" in lowered:
        return "Track overdue RFIs by age bucket, escalate >7-day items to PM leadership, and require closeout notes for every late item."
    if "rfi" in lowered and "rate" in lowered:
        return "Reduce avoidable RFIs by tightening design coordination, running pre-install reviews, and validating scopes before field release."
    if "submittal" in lowered and "lead time" in lowered:
        return "Submit long-lead packages first, pre-coordinate reviewer calendars, and enforce target turnaround windows by submittal type."
    if "submittal" in lowered and "rate" in lowered:
        return "Increase first-pass approval rates by using a pre-submittal checklist and peer QA before formal submission."
    if "submittal" in lowered and "closed on time" in lowered:
        return "Create weekly aging reports, prioritize safety/critical-path submittals, and escalate stalled approvals after agreed thresholds."
    if "incident" in lowered or "safety" in lowered:
        return "Focus on leading indicators: complete weekly hazard observations, close corrective actions within 48 hours, and coach repeat-risk crews."
    if "change order" in lowered:
        return "Standardize change order documentation, pre-price scope changes early, and set approval SLAs with owners and subcontractors."
    if "punch" in lowered:
        return "Run rolling punch walks by zone, assign responsible trade/date for each item, and verify closure with photo evidence."
    if "quality" in lowered:
        return "Use hold-point inspections, trend recurring defects by trade, and deploy corrective training to the highest-defect work packages."
    if "cost" in lowered or "budget" in lowered:
        return "Review cost variance weekly, lock procurement assumptions early, and trigger recovery actions when variance exceeds thresholds."
    if "schedule" in lowered or "timeline" in lowered:
        return "Protect critical path tasks with look-ahead planning, resolve handoff blockers early, and track PPC for weekly commitments."
    return "Define a clear owner, set a weekly target, and review variance-to-target in operations meetings until performance stabilizes."

def get_kpi_strength_detail(kpi_name):
    lowered = str(kpi_name or "").strip().lower()
    if lowered in KPI_STRENGTH_MAP:
        return KPI_STRENGTH_MAP[lowered]
    return "Strong performance here reflects reliable execution and lower risk exposure in this process area."

def build_top_performing_kpis(kpi_df):
    if kpi_df.empty:
        return pd.DataFrame(columns=['kpi_name', 'score_weighted'])
    weight_col = next((c for c in ['KPI wt', 'kpi_wt', 'kpi_weight', 'importance_weight'] if c in kpi_df.columns), None)
    working_df = kpi_df.copy()
    working_df['score_numeric'] = pd.to_numeric(working_df.get('score', 0), errors='coerce').fillna(0)
    if weight_col:
        working_df['kpi_weight_numeric'] = pd.to_numeric(working_df[weight_col], errors='coerce').fillna(0)
    else:
        working_df['kpi_weight_numeric'] = 1.0
    working_df['score_weighted'] = working_df['score_numeric'] * working_df['kpi_weight_numeric']
    return working_df.groupby('kpi_name', as_index=False).agg(
        score_weighted=('score_weighted', 'mean')
    ).sort_values('score_weighted', ascending=False).head(5).reset_index(drop=True)

def build_top_priority_kpis(kpi_df):
    if kpi_df.empty:
        return pd.DataFrame(columns=['kpi_name', 'priority_metric'])
    metric_col = next((c for c in ['process_level_unrealized_value', 'phase_level_unrealized_value', 'unrealized_value'] if c in kpi_df.columns), None)
    if not metric_col:
        return pd.DataFrame(columns=['kpi_name', 'priority_metric'])
    working_df = kpi_df.copy()
    working_df['priority_metric'] = pd.to_numeric(working_df[metric_col], errors='coerce').fillna(0)
    return working_df.groupby('kpi_name', as_index=False).agg(
        priority_metric=('priority_metric', 'mean')
    ).sort_values('priority_metric', ascending=False).head(5).reset_index(drop=True)

def render_kpi_summary_section(title, rows_df, detail_func, detail_header, state_key=None, subtitle=None, accent_color=None):
    marker_class = f"kpi-accent-{''.join(c for c in (accent_color or 'default') if c.isalnum())}"
    if accent_color:
        h = accent_color.lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        title_bg = f"rgba({r},{g},{b},0.30)"
        header_sep = f"rgba({r},{g},{b},0.3)"
    else:
        title_bg = "transparent"
        header_sep = "#e5e7eb"
    badge_color = accent_color or "#6b7280"
    tbl_class = f"kpi-tbl-{marker_class}"
    with st.container(border=True):
        if accent_color and not state_key:
            st.markdown(f"""<style>
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.{marker_class}) {{
                    border-top: 4px solid {accent_color} !important;
                    border-radius: 0.5rem !important;
                }}
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.{marker_class}) > div[data-testid="stVerticalBlock"] {{
                    padding-top: 0 !important;
                }}
            </style><span class='{marker_class}' style='display:none;'></span>""", unsafe_allow_html=True)

        title_color = "#111"
        if state_key:
            btn_key = f"btn_{state_key}"
            st.markdown(f"""<style>
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-{btn_key}) {{
                    border-top: 4px solid {accent_color} !important;
                    border-radius: 0.5rem !important;
                    background: {title_bg} !important;
                    padding-bottom: 0 !important;
                    overflow-x: hidden !important;
                    overflow-y: visible !important;
                }}
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-{btn_key}) > div[data-testid="stVerticalBlock"] {{
                    padding-top: 0 !important;
                    padding-bottom: 0 !important;
                    gap: 0 !important;
                    background: transparent !important;
                }}
                div.st-key-{btn_key} {{
                    margin-top: -3.2rem !important;
                    margin-bottom: -0.7rem !important;
                    display: flex !important;
                    justify-content: flex-end !important;
                    padding-right: 0.5rem !important;
                    padding-bottom: 0.4rem !important;
                    width: 100% !important;
                    flex-shrink: 0 !important;
                }}
                div.st-key-{btn_key} > div[data-testid="stButton"] {{
                    width: fit-content !important;
                    margin-bottom: 0 !important;
                    flex-shrink: 0 !important;
                    white-space: nowrap !important;
                }}
                div.st-key-{btn_key} > div[data-testid="stButton"] > button {{
                    width: fit-content !important;
                    margin-bottom: 0 !important;
                    white-space: nowrap !important;
                }}
            </style>""", unsafe_allow_html=True)
            st.markdown(f"<h2 style='text-align: center; font-size: clamp(1rem, 3vw, 1.8rem); font-weight: 700; margin: -2rem -1rem 0 -1rem; padding: 0.748rem 9rem 0.748rem 1rem; background: {title_bg}; color: #111; border-radius: 0.5rem 0.5rem 0 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{title}</h2>", unsafe_allow_html=True)
            button_label = "Hide Details" if st.session_state.get(state_key, True) else "Show Details"
            st.button(button_label, key=btn_key, on_click=lambda s_key=state_key: st.session_state.update({s_key: not st.session_state.get(s_key, True)}), type="primary")
            if not st.session_state.get(state_key, True):
                return
        else:
            st.markdown(f"<h2 style='text-align: center; font-size: 1.8rem; font-weight: 700; margin: -2rem -1rem 0.748rem -1rem; padding: 0.748rem 1rem; background: {title_bg}; color: #111; border-radius: 0.5rem 0.5rem 0 0;'>{title}</h2>", unsafe_allow_html=True)

        if rows_df.empty:
            st.info("No KPI data for current selection.")
            return

        st.markdown(f"""<style>
            .{tbl_class} {{ width:100%; border-collapse:separate; border-spacing:0 0.35rem; font-size:0.95rem; }}
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.{tbl_class}) {{
                padding-top: 0 !important;
            }}
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.{tbl_class}) > div[data-testid="stVerticalBlock"] {{
                padding-top: 0 !important;
                gap: 0 !important;
            }}
            .{tbl_class} th {{ text-align:left; padding:0.5rem 0.6rem; background:#f3f4f6; color:#374151; font-weight:700; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.05em; border-bottom:none; }}
            .{tbl_class} th:not(:last-child) {{ border-right:1px solid {header_sep}; }}
            .{tbl_class} th:first-child {{ border-radius:0.375rem 0 0 0.375rem; }}
            .{tbl_class} th:last-child  {{ border-radius:0 0.375rem 0.375rem 0; }}
            .{tbl_class} td {{ padding:0.6rem 0.6rem; background:#f9fafb; vertical-align:top; border-right:none; height:4.5rem; }}
            .{tbl_class} td:first-child {{ border-radius:0.375rem 0 0 0.375rem; }}
            .{tbl_class} td:last-child  {{ border-radius:0 0.375rem 0.375rem 0; }}
            .{tbl_class} td.rank {{ width:3rem; }}
            .{tbl_class} td.kpi-name {{ font-weight:700; text-transform:uppercase; color:#111; width:28%; vertical-align:middle; text-align:center; }}
            .{tbl_class} td.guidance {{ color:#374151; }}
            .{tbl_class} .kpi-badge {{ display:inline-flex; align-items:center; justify-content:center; width:1.8rem; height:1.8rem; background:{badge_color}; color:white; border-radius:0.3rem; font-weight:700; font-size:0.9rem; }}
            /* Equal height KPI boxes */
            div[data-testid="stHorizontalBlock"]:has(.{tbl_class}) {{ align-items:stretch !important; }}
            div[data-testid="stHorizontalBlock"]:has(.{tbl_class}) > div[data-testid="stColumn"] {{ display:flex !important; flex-direction:column !important; }}
            div[data-testid="stHorizontalBlock"]:has(.{tbl_class}) > div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] {{ flex:1 !important; display:flex; flex-direction:column; }}
            div[data-testid="stHorizontalBlock"]:has(.{tbl_class}) > div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {{ flex:1; display:flex; flex-direction:column; }}
            div[data-testid="stHorizontalBlock"]:has(.{tbl_class}) > div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] > div[data-testid="stVerticalBlock"] {{ flex:1; }}
        </style>""", unsafe_allow_html=True)

        rows_html = ""
        for i, row in rows_df.iterrows():
            kpi_name_display = html.escape(format_kpi_name(row['kpi_name']))
            detail_text = html.escape(detail_func(row['kpi_name']))
            rows_html += f"""<tr>
                <td class='rank'><span class='kpi-badge'>{i+1}</span></td>
                <td class='kpi-name'>{kpi_name_display}</td>
                <td class='guidance'>{detail_text}</td>
            </tr>"""

        st.markdown(f"""<div style='overflow-x: auto;'><table class='{tbl_class}'>
            <thead><tr>
                <th>Rank</th><th>KPI Name</th><th>{html.escape(detail_header)}</th>
            </tr></thead>
            <tbody>{rows_html}</tbody>
        </table></div>""", unsafe_allow_html=True)

def build_kpi_tooltip(kpi_name):
    name = str(kpi_name or "").strip()
    lowered = name.lower()

    definition_overrides = {
        # Bidding - bidresults
        'bid win rate': 'Percentage of submitted bids that result in a contract award. Reflects the effectiveness of targeting, estimating, and proposal quality.',
        'cost variance': 'Difference between estimated and actual project costs. Persistent variance signals estimation gaps, scope creep, or poor cost control.',
        'profit variance': 'Difference between projected and actual profit margin. Reveals how well pricing and cost controls held up through execution.',
        'schedule variance': 'Difference between planned and actual project completion timeline. Indicates schedule discipline and execution predictability.',
        # Bidding - bidreview
        '% of bids targeted': 'Percentage of identified opportunities intentionally pursued. High targeting rates signal disciplined go/no-go decision-making.',
        'avg days to submit bid': 'Average elapsed time from bid invitation to submission. Shorter cycles with quality output indicate an efficient estimating process.',
        'avg time to submit bid': 'Average elapsed time from bid invitation to completed submission. Tracks estimating team responsiveness and capacity under deadline pressure.',
        'bid rate per $1m of acv': 'Number of bids submitted per $1M of annual contract value. Balances bid volume against revenue targets to avoid over- or under-bidding.',
        # Bidding - compliance
        'bid package completeness rate': 'Percentage of bid packages submitted with all required documents. Incomplete packages risk disqualification and signal process gaps.',
        'compliance matrix completion rate': 'Percentage of compliance checklist items completed per bid. Tracks adherence to internal and client bidding requirements.',
        'licensing & certification compliance rate': 'Percentage of required licenses and certifications held and current across the team. Non-compliance creates legal, safety, and operational risk.',
        'sub prequal rate': 'Percentage of subcontractors that have passed prequalification screening. Higher rates reduce execution risk from unvetted or underqualified partners.',
        # Bidding - estimating
        'avg number of sub quotes per trade': 'Average number of competitive subcontractor bids received per trade. More quotes improve pricing accuracy and reduce cost and risk exposure.',
        'avg selected sub emr': 'Average Experience Modification Rate of selected subcontractors. Lower EMR indicates a safer, less risky subcontractor pool with better safety track records.',
        'avg sub quote variance': 'Spread between the highest and lowest subcontractor quotes per trade. High variance signals unclear scope, inconsistent takeoffs, or market uncertainty.',
        'avg sub response rate': 'Percentage of subcontractors invited to bid who actually submit a quote. Low response rates may indicate scope issues, timing conflicts, or weak relationships.',
        # Preconstruction - compliance
        'avg insurance acquired cycle': 'Average days to obtain required insurance certificates after contract award. Delays can hold up project start and create uninsured liability gaps.',
        'avg permit approval cycle': 'Average days from permit submission to regulatory approval. Longer cycles delay project start and indicate scope complexity or process inefficiency.',
        'avg sub coi received time': 'Average time to receive Certificates of Insurance from subcontractors after request. Slow COI receipt exposes the project to periods of uninsured risk.',
        'permit submission timeliness': 'Percentage of permits submitted within the required timeframe ahead of planned start. Late submissions cascade into downstream schedule risk.',
        # Preconstruction - designReview
        'clash detection rate': 'Frequency of design clashes identified during BIM or drawing coordination. Early detection prevents costly field conflicts and rework during construction.',
        'drawings usage': 'Extent to which current drawing sets are actively referenced by project teams. Low usage signals document control gaps or teams working off outdated information.',
        'photos usage': 'Rate of photo documentation captured and attached to field records. Supports accountability, dispute resolution, and quality verification throughout the project.',
        'specifications usage': 'Extent to which technical specifications are actively referenced during work. Low usage increases risk of non-compliant installations and failed inspections.',
        # Preconstruction - financialSetup
        'budget to bid variance': 'Difference between the awarded contract amount and the internal project budget. Large gaps indicate estimation errors or scope changes made post-award.',
        'contingency adequacy': 'Assessment of whether the contingency reserve is sized appropriately for the project risk profile. Underfunded contingency is a leading predictor of budget overruns.',
        'days until sub contracts executed': 'Average days from subcontractor award to fully executed subcontract agreements. Delays leave scope, pricing, and liability undefined during early mobilization.',
        'prime contract to budget variance': 'Difference between the prime contract value and the internal cost budget. Tracks whether margin integrity is preserved from contract execution through planning.',
        # Preconstruction - subcontractorPlanning
        'equipment cost variance': 'Difference between planned and actual equipment costs at close. Identifies gaps in equipment planning assumptions or unexpected field conditions.',
        'gantt chart completion rate': 'Percentage of scheduled tasks marked complete on time in the master schedule. Reflects schedule discipline and the accuracy of preconstruction planning.',
        'labor cost variance': 'Difference between planned and actual labor costs. Persistent variance signals productivity shortfalls, scope creep, or inaccurate labor estimating.',
        'materials cost variance': 'Difference between planned and actual materials costs. High variance indicates procurement inefficiency, price escalation, or uncontrolled scope changes.',
        'schedule to bid variance': 'Difference between the bid schedule duration and the actual execution schedule at completion. Tracks whether initial timeline commitments were realistic and maintained.',
        # Construction - communication
        'daily logs rate': 'Frequency and consistency of daily field log completion by site supervisors. Gaps in logging create accountability, documentation, and dispute risk.',
        'daily logs delay': 'Lag between the field activity date and the daily log submission date. Delayed logs reduce accuracy and limit the ability to reconstruct events accurately.',
        'meetings documentation': 'Completeness and timeliness of meeting records, decisions, and assigned actions. Poor documentation leads to unresolved issues, missed commitments, and disputes.',
        'meetings rate': 'Frequency of planned coordination and production meetings held on schedule. Consistent meetings drive issue resolution, alignment, and proactive risk management.',
        # Construction - financial
        'budgets create date': 'Elapsed time to create the baseline project budget after project kickoff. Late budget creation delays cost control visibility and performance benchmarking.',
        'budgets usage rate': 'Frequency with which project budgets are actively accessed and updated during execution. Low usage suggests cost tracking is disconnected from daily field operations.',
        'change order time to close': 'Average days to fully execute a change order from identification to written approval. Slow closure ties up cash flow and allows scope ambiguity to persist.',
        'change order to budget ratio': 'Total change order value relative to the original budget. High ratios indicate scope instability, owner-driven changes, or ineffective change management.',
        'contract to budget ratio (deviation)': 'Deviation between contract value and the working cost budget. Reveals whether the project is being managed within its contracted and estimated scope.',
        'invoice to contract ratio (deviation)': 'Deviation between amounts invoiced and contract values over time. Persistent over- or under-invoicing signals billing process breakdowns or disputes.',
        'payments to invoices ratio (deviation)': 'Deviation between payments received and invoices submitted. Tracks cash flow health and whether the client is paying in accordance with contract terms.',
        # Construction - operations
        'rfis closed on time': 'Percentage of Requests for Information resolved within the required response window. Delays in RFI closure directly stall field productivity and sequence downstream work.',
        'rfis lead time': 'Average elapsed time from RFI submission to design team response. Long lead times indicate design bottlenecks, unclear scope, or insufficient staffing.',
        'rfis rate': 'Number of RFIs generated per unit of project time. Elevated rates may signal design gaps, scope ambiguity, or inadequate preconstruction coordination.',
        'submittals closed on time': 'Percentage of submittals reviewed and approved within the required timeframe. Late approvals constrain procurement schedules and delay material deliveries.',
        'submittals lead time': 'Average time from submittal submission to design team review completion. Long cycles compress the procurement schedule and create installation delays.',
        'submittals rate': 'Frequency of submittals generated and processed per time period. Tracks whether the submittal pipeline is aligned with and supporting the construction schedule.',
        # Construction - quality
        'observation rate': 'Frequency of quality observations logged per project day by field supervisors. Higher rates reflect proactive quality monitoring and a culture of continuous inspection.',
        'observations closed on time': 'Percentage of quality observations resolved and closed within the required timeframe. Unresolved items accumulate and increase the probability of rework and defects.',
        'quality insp. attach. rate': 'Percentage of quality inspections with supporting photos or documents attached. Attachments validate compliance, support approvals, and protect against disputes.',
        'quality inspection rate': 'Frequency of formal quality inspections conducted per project day. Consistent inspections catch defects early when correction costs are lowest.',
        # Construction - safety
        'incident detail quality': 'Completeness and accuracy of incident report documentation. Poor quality reports limit root cause analysis, corrective action, and regulatory compliance.',
        'incident rate': 'Number of recordable safety incidents per hours worked on site. A key lagging indicator of safety culture, site conditions, and hazard control effectiveness.',
        'near miss detail quality': 'Quality and completeness of near-miss event documentation. Well-documented near misses enable pattern recognition and prevention of future incidents.',
        'near miss rate': 'Frequency of near-miss events reported per project period. Higher reporting rates often reflect a stronger safety culture where workers feel safe raising concerns.',
        'safety insp. attach. rate': 'Percentage of safety inspections with supporting photos or documents attached. Documentation provides evidence of hazard identification and corrective action taken.',
        'safety inspection rate': 'Frequency of formal safety inspections per project day. Regular inspections identify hazards before they escalate into recordable incidents.',
        'safety training': 'Percentage of required safety training completed by field personnel on time. Undertrained workers are at significantly higher risk of incident involvement.',
        # Closeout - clientHandover
        'client satisfaction score': 'Client-rated satisfaction score collected at project completion. Reflects overall delivery quality, communication, and relationship management throughout the project.',
        'client training completion': 'Percentage of required owner and end-user training sessions completed before handover. Incomplete training increases post-handover support burden and client frustration.',
        # Closeout - finalDocumentation
        'as-built drawing accuracy': 'Degree to which final as-built drawings match actual installed field conditions. Inaccurate as-builts create long-term facility management and renovation risk for the owner.',
        'o&m manuals submitted timely': 'Percentage of Operations & Maintenance manuals submitted by required turnover deadlines. Late delivery delays the client\'s ability to operate and maintain the facility.',
        # Closeout - financialReconciliation
        'final payment received time': 'Days elapsed from project completion milestone to receipt of final payment. Delays indicate unresolved disputes, billing errors, or client cash flow issues.',
        'subcontractor final payments': 'Percentage of subcontractors paid in full within required timeframes after closeout. Delayed final payments damage subcontractor relationships and create lien exposure.',
        # Closeout - punchlistCompletion
        'avg time to close punch item': 'Average days to resolve and formally close a punch list item. Long resolution times delay final acceptance, certificate of occupancy, and final payment.',
        'punch list items closed rate': 'Percentage of punch list items closed relative to total items identified. Low rates signal resource constraints, scope disputes, or poor closeout planning.',
    }

    return definition_overrides.get(lowered, f"Operational performance metric tracking {name} across projects.")

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

    display_df['unrealized_value'] = pd.to_numeric(display_df.get('unrealized_value', 0), errors='coerce').fillna(0)
    display_df = display_df.sort_values(by='unrealized_value', ascending=False).reset_index(drop=True)

    def assign_impact_labels(df):
        labels = ['Average'] * len(df)
        n = len(df)
        if n == 0:
            return labels
        if n >= 5:
            high_count, low_count = 2, 2
        elif n >= 2:
            high_count, low_count = 1, 1
        else:
            high_count, low_count = 1, 0
        for i in range(high_count):
            labels[i] = 'High'
        for i in range(low_count):
            labels[n - 1 - i] = 'Low'
        return labels

    display_df['impact_label'] = assign_impact_labels(display_df)

    priority_styles = {
        'High': 'background:#dcfce7; color:#166534;',
        'Average': 'background:#ecfccb; color:#3f6212;',
        'Low': 'background:#fef9c3; color:#854d0e;'
    }

    actual_header = "Actual (Avg)" if is_averaged else "Actual"
    tbl_id = f"proc-tbl-{id(kpi_df)}"

    rows_html = ""
    for _, row in display_df.iterrows():
        actual_val = row['actual_numeric']
        unit = row.get('unit', '')
        actual_display = f"{actual_val:.0%}" if unit == '%' else f"{actual_val:.1f}"
        kpi_name = str(row.get('kpi_name', 'N/A'))
        kpi_name_display = html.escape(format_kpi_name(kpi_name))
        tooltip_text = html.escape(build_kpi_tooltip(kpi_name), quote=True)
        priority_label = row.get('impact_label', 'Average')
        priority_style = priority_styles.get(priority_label, priority_styles['Average'])
        rows_html += f"""<tr>
            <td style='padding:0.6rem; background:#f9fafb; border-radius:0.375rem 0 0 0.375rem; font-size:1.235rem;'>
                {kpi_name_display} <span class='kpi-tip-wrap'><span style='font-size:1.04rem; color:#6b7280; font-weight:600;'>[?]</span><span class='kpi-tip-box'>{tooltip_text}</span></span>
            </td>
            <td style='padding:0.6rem; background:#f9fafb; text-align:center; font-size:1.235rem;'>{html.escape(str(row.get('bp_range_display', 'N/A')))}</td>
            <td style='padding:0.6rem; background:#f9fafb; text-align:center; font-size:1.235rem;'>{actual_display}</td>
            <td style='padding:0.6rem; background:#f9fafb; text-align:center; font-size:1.235rem;'>{row.get('score', 0):.0f}</td>
            <td style='padding:0.6rem; background:#f9fafb; border-radius:0 0.375rem 0.375rem 0; text-align:center;'>
                <span style='display:inline-block; min-width:5rem; text-align:center; padding:0.2rem 0.6rem; border-radius:9999px; font-size:1.1rem; font-weight:700; {priority_style}'>{priority_label}</span>
            </td>
        </tr>"""

    st.markdown(f"""<style>
        .{tbl_id} {{ width:100%; border-collapse:separate; border-spacing:0 0.35rem; font-size:1.235rem; }}
        .{tbl_id} th {{ text-align:left; padding:0.5rem 0.6rem; background:#f3f4f6; color:#374151; font-weight:700; font-size:1.04rem; text-transform:uppercase; letter-spacing:0.05em; }}
        .{tbl_id} th:first-child {{ border-radius:0.375rem 0 0 0.375rem; }}
        .{tbl_id} th:last-child  {{ border-radius:0 0.375rem 0.375rem 0; }}
        .{tbl_id} th:not(:last-child) {{ border-right:1px solid #e5e7eb; }}
        .{tbl_id} th:nth-child(2), .{tbl_id} th:nth-child(3), .{tbl_id} th:nth-child(4), .{tbl_id} th:nth-child(5) {{ text-align:center; }}
        .kpi-tip-wrap {{ display:inline-block; cursor:help; }}
        .kpi-tip-box {{ display:none; position:fixed; background:#1e293b; color:#f8fafc; padding:0.55rem 0.8rem; border-radius:0.4rem; font-size:1.23rem; font-weight:400; line-height:1.5; width:420px; z-index:99999; pointer-events:none; white-space:normal; box-shadow:0 4px 12px rgba(0,0,0,0.3); }}
    </style>""", unsafe_allow_html=True)
    components.html("""<script>
    (function() {
        function initTooltips() {
            var doc = window.parent.document;
            doc.querySelectorAll('.kpi-tip-wrap').forEach(function(wrap) {
                if (wrap._tipInit) return;
                wrap._tipInit = true;
                var box = wrap.querySelector('.kpi-tip-box');
                if (!box) return;
                wrap.addEventListener('mouseenter', function() {
                    box.style.display = 'block';
                    var rect = wrap.getBoundingClientRect();
                    var tipH = box.offsetHeight;
                    var tipW = box.offsetWidth;
                    var top = rect.top - tipH - 8;
                    if (top < 8) top = rect.bottom + 8;
                    var left = rect.left;
                    if (left + tipW > window.innerWidth - 8) left = window.innerWidth - tipW - 8;
                    if (left < 8) left = 8;
                    box.style.top = top + 'px';
                    box.style.left = left + 'px';
                });
                wrap.addEventListener('mouseleave', function() {
                    box.style.display = 'none';
                });
            });
        }
        initTooltips();
        new MutationObserver(initTooltips).observe(window.parent.document.body, { childList: true, subtree: true });
    })();
    </script>""", height=0)
    st.markdown(f"""<div style='overflow-x: auto;'><table class='{tbl_id}'>
        <thead><tr>
            <th>KPI Name</th>
            <th>Best Practice</th>
            <th>{actual_header}</th>
            <th>Score/100</th>
            <th>Priority</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
    </table></div>""", unsafe_allow_html=True)

def format_process_name(name):
    if name in PROCESS_DISPLAY_NAMES: return PROCESS_DISPLAY_NAMES[name]
    return re.sub(r"(\w)([A-Z])", r"\1 \2", name).title()

def display_top_action_items(page_key, action_items_df):
    """Displays the 'Top Priority Action Items' section with real data from CSV."""
    if action_items_df.empty:
        st.markdown("<h2 style='text-align: center; margin-bottom: 0.25rem; font-size: 1.5rem; margin-top: 1.5rem;'>Top Priority Action Items</h2>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<p style='text-align:center; color:#555; font-size: 1.5rem;'>No action items found.</p>", unsafe_allow_html=True)
        return

    # Sort by weight descending and take top 5
    top_items = action_items_df.nlargest(5, 'weight')
    
    if top_items.empty:
        st.markdown("<h2 style='text-align: center; margin-bottom: 0.25rem; font-size: 1.5rem; margin-top: 1.5rem;'>Top Priority Action Items</h2>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<p style='text-align:center; color:#555; font-size: 1.5rem;'>No action items found.</p>", unsafe_allow_html=True)
        return

    st.markdown("<h2 style='text-align: center; margin-bottom: 0.25rem; font-size: 1.5rem; margin-top: 1.5rem;'>Top Priority Action Items</h2>", unsafe_allow_html=True)
    
    with st.container(border=True):
        # Headers
        header_cols = st.columns([0.25, 0.45, 0.30])
        header_cols[0].markdown("<span style='font-size: 1.5rem;'><strong>Type</strong></span>", unsafe_allow_html=True)
        header_cols[1].markdown("<span style='font-size: 1.5rem;'><strong>Description</strong></span>", unsafe_allow_html=True)
        header_cols[2].markdown("<span style='font-size: 1.5rem;'><strong>Required Action</strong></span>", unsafe_allow_html=True)
        
        # Data rows
        for _, row in top_items.iterrows():
            item_cols = st.columns([0.25, 0.45, 0.30])
            item_cols[0].markdown(f"<span style='font-size: 1.5rem;'>{html.escape(str(row['action_item_type']))}</span>", unsafe_allow_html=True)
            item_cols[1].markdown(f"<span style='font-size: 1.5rem;'>{html.escape(str(row['description']))}</span>", unsafe_allow_html=True)
            item_cols[2].markdown(f"<span style='font-size: 1.5rem;'>{html.escape(str(row['required_action']))}</span>", unsafe_allow_html=True)


# --- Data Loading Function ---
@st.cache_data
def load_data():
    base_path = "."; data = {}
    try:
        summary_df = pd.read_csv(os.path.join(base_path, "executive_summary.csv"))
        data['executive_summary'] = summary_df[summary_df['impact_category'].isin(ALLOWED_IMPACT_CATEGORIES)]
        
        # Load action items data
        action_items_file = os.path.join(base_path, "procore-itemized-combined.csv")
        if os.path.exists(action_items_file):
            action_items_df = pd.read_csv(action_items_file)
            # Filter to only Construction categories (Schedule, Cost, Safety)
            data['action_items'] = action_items_df[action_items_df['impact_category'].isin(ALLOWED_IMPACT_CATEGORIES)]
        else:
            data['action_items'] = pd.DataFrame()
        
        for phase in ['bidding', 'preconstruction', 'construction', 'closeout']:
            processes_file = os.path.join(base_path, f"{phase}_processes.csv")
            kpis_file = os.path.join(base_path, f"{phase}_kpis.csv")
            if os.path.exists(processes_file) and os.path.exists(kpis_file):
                df_p = pd.read_csv(processes_file)
                df_k = pd.read_csv(kpis_file)

                # Remove low-value near-miss KPIs from Construction/Safety views.
                if phase == 'construction' and {'process_name', 'kpi_name'}.issubset(set(df_k.columns)):
                    excluded_kpis = {'near miss rate', 'near miss detail quality'}
                    is_safety_process = df_k['process_name'].astype(str).str.strip().str.lower() == 'safety'
                    is_excluded_kpi = df_k['kpi_name'].astype(str).str.strip().str.lower().isin(excluded_kpis)
                    df_k = df_k[~(is_safety_process & is_excluded_kpi)].copy()
                
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
    cr_score = summary_df['score'].mean()
    cost_estimate = (cr_score / 100.0) * 0.18 * 100
    schedule_estimate = (cr_score / 100.0) * 0.30 * 100
    safety_estimate = (cr_score / 100.0) * 0.60 * 100

    def _ratio_color(actual, possible):
        ratio = actual / possible if possible else 0
        if ratio < 0.2: return "#ef4444"
        elif ratio < 0.4: return "#f97316"
        elif ratio < 0.6: return "#fbbf24"
        elif ratio < 0.8: return "#86efac"
        else: return "#16a34a"

    cost_color = "#2563eb"
    schedule_color = "#2563eb"
    safety_color = "#2563eb"

    top_row_left, top_row_right = st.columns(2)
    with top_row_left:
        with st.container(border=True):
            st.markdown("<h2 style='display:block; width:100%; text-align: center; margin-bottom: 0.25rem; font-size: 1.8rem; font-weight: 700; color: #111; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.375rem;'>CR-Score</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; max-width: 100%; margin: 0.1rem auto 0.15rem auto; font-size:1.25rem; color:#6b7280; font-weight:400;'>Represents the adoption of Best Practices for all KPIs across all 4 Phases of Operations.</p>", unsafe_allow_html=True)
            st.markdown(circular_score_meter_html(cr_score, size=420), unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("<h3 style='display:block; width:100%; text-align: center; margin-bottom: 0.5rem; font-size: 1.8rem; font-weight: 700; color: #111; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.375rem;'>Estimated Impact of Operational Performance</h3>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style='font-size:1.4rem; display:table; width:100%; border-spacing:0 0.3rem; border-collapse:separate;'>
                <div style='display:table-row;'>
                    <span style='display:table-cell; text-align:right; padding:0.45rem 0.75rem 0.45rem 0; width:50%;'>Improvement in Project Costs:</span>
                    <span style='display:table-cell; text-align:left; padding:0.45rem 0 0.45rem 0.75rem; width:50%;'><span style='color:{cost_color}; font-weight:700;'>{cost_estimate:.1f}%</span> out of <span style='color:#2563eb; font-weight:700;'>18.0%</span> possible</span>
                </div>
                <div style='display:table-row;'>
                    <span style='display:table-cell; text-align:right; padding:0.45rem 0.75rem 0.45rem 0;'>Improvement in Project Timeline:</span>
                    <span style='display:table-cell; text-align:left; padding:0.45rem 0 0.45rem 0.75rem;'><span style='color:{schedule_color}; font-weight:700;'>{schedule_estimate:.1f}%</span> out of <span style='color:#2563eb; font-weight:700;'>30.0%</span> possible</span>
                </div>
                <div style='display:table-row;'>
                    <span style='display:table-cell; text-align:right; padding:0.45rem 0.75rem 0.45rem 0;'>Reduction in Incidents:</span>
                    <span style='display:table-cell; text-align:left; padding:0.45rem 0 0.45rem 0.75rem;'><span style='color:{safety_color}; font-weight:700;'>{safety_estimate:.1f}%</span> out of <span style='color:#2563eb; font-weight:700;'>60.0%</span> possible</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with top_row_right:
        phase_definitions = {"Bidding": {"col": "phaseScore_bidding", "desc": "selecting what jobs to bid on and building estimates"},"Precon": {"col": "phaseScore_precon", "desc": "For bids that are won, all the project preparation"},"Construction": {"col": "phaseScore_construction", "desc": "executing the plan and completing the project"},"Closeout": {"col": "phaseScore_closeout", "desc": "wrap up of all work and handoff to the customer"}}
        phases_html = ""
        for name, info in phase_definitions.items():
            bar = horizontal_risk_bar_html(summary_df[info["col"]].mean(), width_percentage=95, height='1.65rem', font_size='1.2rem', top_offset='-1.8rem')
            phases_html += f"""
            <div style="text-align:center; margin-bottom:1rem;">
                <div style="font-size:1.5rem; margin-bottom:2rem; font-family:inherit;">
                    <strong>{html.escape(name)}</strong> - <em>{html.escape(info['desc'])}</em>
                </div>
                {bar}
            </div>"""
        st.html(f"""
        <div id="cr-box" style="
            border: 1px solid rgba(49,51,63,0.2);
            border-radius: 0.5rem;
            padding: 1.5rem 1.5rem 1.5rem 1.5rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-family: 'Source Sans Pro', sans-serif;
            box-sizing: border-box;
            min-height: 100%;
        ">
            <h2 style="display:block; width:100%; text-align:center; font-size:1.8rem; font-weight:700; color:#111; margin:0 0 0.375rem 0; padding-bottom:0.375rem; border-bottom:1px solid #e5e7eb; font-family:inherit;">CR-Score Components</h2>
            <h3 style="text-align:center; font-size:1.17rem; margin:0 0 1.5rem 0; font-weight:600; font-family:inherit;">4 Phases of Operations</h3>
            <div style="width:100%;">{phases_html}</div>
        </div>
        <script>
        (function() {{
            function fitToLeftColumn() {{
                try {{
                    var parentDoc = window.parent.document;
                    var columns = parentDoc.querySelectorAll('[data-testid="stColumn"]');
                    if (columns.length >= 2) {{
                        var leftColHeight = columns[0].offsetHeight;
                        if (leftColHeight > 0) {{
                            var box = document.getElementById('cr-box');
                            box.style.minHeight = leftColHeight + 'px';
                            document.body.style.minHeight = leftColHeight + 'px';
                        }}
                    }}
                }} catch(e) {{}}
            }}
            window.addEventListener('load', fitToLeftColumn);
            setTimeout(fitToLeftColumn, 200);
            setTimeout(fitToLeftColumn, 600);
        }})();
        </script>
        """)

    kpis_for_actions = all_kpis_df[all_kpis_df['impact_category'] == impact_category_filter] if not all_kpis_df.empty else pd.DataFrame()
    executive_top_performing = build_top_performing_kpis(kpis_for_actions)
    executive_top_priority = build_top_priority_kpis(kpis_for_actions)

    st.markdown("<hr style='margin-top: 1rem; margin-bottom: 0.75rem;'>", unsafe_allow_html=True)
    bottom_left, bottom_right = st.columns(2)
    with bottom_left:
        render_kpi_summary_section("Top Performing KPIs", executive_top_performing, get_kpi_strength_detail, "Details", accent_color="#16a34a")
    with bottom_right:
        render_kpi_summary_section("Top Priority KPIs to Improve", executive_top_priority, get_kpi_guidance, "Guidance", accent_color="#ef4444")


def display_phase_summary_page(phase_key, data, impact_category_filter, summary_for_impact_calc):
    if phase_key not in data:
        st.error(f"Data for the {phase_key} phase could not be loaded. Please ensure `{phase_key}_processes.csv` and `{phase_key}_kpis.csv` files are present.")
        return

    info = PHASE_INFO.get(phase_key)
    if not info: st.error("Invalid phase selected."); return
    
    st.markdown(f"<h1 style='text-align: center; color: #333333;'>{info['title']}</h1>", unsafe_allow_html=True)
    
    summary_df = data['executive_summary']
    processes_df_all_categories = data[phase_key]['processes']
    phase_kpis_all = data[phase_key]['kpis']
    kpis_df = phase_kpis_all[phase_kpis_all['impact_category'] == impact_category_filter]
    
    if summary_df.empty: st.info("No project data matches the selected filters."); return

    phase_score = summary_df[info['score_col']].mean()
    process_scores = processes_df_all_categories.groupby('process_name')['score'].mean()

    with st.container(border=True):
        st.markdown(f"<h2 style='display:block; width:100%; text-align: center; font-size: 1.8rem; font-weight: 700; color: #111; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.375rem;'>{phase_key.capitalize()} Phase Score</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-size:1.62em;'>{PHASE_DESCRIPTIONS.get(phase_key, '')}</p>", unsafe_allow_html=True)
        _, bar_col, _ = st.columns([0.05, 0.90, 0.05])
        with bar_col:
            st.markdown(f"<div style='margin-top: 2.0rem; padding-bottom: 1.5rem;'>{horizontal_risk_bar_html(phase_score, height='1.46rem', font_size='2.025rem', top_offset='-2.9rem', width_percentage=100)}</div>", unsafe_allow_html=True)

    top_performing_df = build_top_performing_kpis(phase_kpis_all)
    top_priority_df = build_top_priority_kpis(phase_kpis_all)

    col_top_performing, col_top_priority = st.columns(2)
    with col_top_performing:
        render_kpi_summary_section("Top Performing KPIs", top_performing_df, get_kpi_strength_detail, "Details", state_key=f"{phase_key}_top_performing", accent_color="#16a34a")

    with col_top_priority:
        render_kpi_summary_section("Top Priority KPIs to Improve", top_priority_df, get_kpi_guidance, "Guidance", state_key=f"{phase_key}_top_priority", accent_color="#ef4444")

    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown(f"<h2 style='text-align: center; font-size: 1.5rem;'>{phase_key.capitalize()} Process and KPI Details</h2>", unsafe_allow_html=True)
    for process_key in PHASE_PROCESS_MAPPING.get(phase_key, []):
        score = process_scores.get(process_key, 0)
        process_display_name = format_process_name(process_key)
        proc_key = f"proc_{phase_key}_{process_key}"
        process_desc = PROCESS_DESCRIPTIONS.get(process_key, "Tracks key performance indicators for this process and how they affect overall project outcomes.")

        st.markdown(f"""<style>
            div[data-testid="stHorizontalBlock"]:has(.proc-left-{proc_key}) > div[data-testid="stColumn"]:first-child {{
                flex: 0 0 425px !important;
                max-width: 425px !important;
                min-width: 425px !important;
            }}
            div[data-testid="stHorizontalBlock"]:has(.proc-left-{proc_key}) > div[data-testid="stColumn"]:last-child {{
                flex: 1 1 auto !important;
                min-width: 0 !important;
            }}
        </style>""", unsafe_allow_html=True)

        left_col, right_col = st.columns([0.35, 0.65])
        with left_col:
            st.markdown(f"<div class='proc-left-{proc_key}' style='max-width: 425px; padding-right: 16px; margin-top: 1.5rem;'><div style='margin-bottom: 2.2rem;'><span style='font-size: 1.5rem; white-space: nowrap;'><strong>{process_display_name}</strong></span></div>{horizontal_risk_bar_html(score, width_percentage=100, height='1.02rem', font_size='1.42rem', top_offset='-2.03rem')}<p style='font-size:1.0rem; color:#4b5563; margin-top:2.25rem;'>{process_desc}</p></div>", unsafe_allow_html=True)
        with right_col:
            display_kpi_table(kpis_df[kpis_df['process_name'] == process_key])

        st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def load_project_lookup() -> dict:
    """Return {str(procore_id): display_name} from S3 projects.csv."""
    try:
        import boto3, io as _io
        session = boto3.Session(profile_name='dev')
        s3 = session.client('s3')
        obj = s3.get_object(
            Bucket='kroo-crai-dev',
            Key='companies/Haugland Companies/procore/projects.csv'
        )
        df = pd.read_csv(_io.BytesIO(obj['Body'].read()), usecols=['procore_id', 'display_name'])
        df = df.dropna(subset=['procore_id'])
        return {str(int(row['procore_id'])): str(row['display_name']) for _, row in df.iterrows()}
    except Exception:
        return {}


@st.cache_data(ttl=3600)
def load_rfi_data():
    """Load raw RFI data from S3 (dev profile), falling back to local CSV."""
    try:
        import boto3, io as _io
        session = boto3.Session(profile_name='dev')
        s3 = session.client('s3')
        obj = s3.get_object(
            Bucket='kroo-crai-dev',
            Key='companies/Haugland Companies/procore/rfis.csv'
        )
        return pd.read_csv(_io.BytesIO(obj['Body'].read()))
    except Exception:
        local = os.path.join(
            os.path.dirname(__file__),
            '..', 'crai-data-pipeline', 'rfis_sample.csv'
        )
        fallback = r'C:\Users\jlwoo\Documents\CRAI\GitHub\local repository\crai-data-pipeline\rfis_sample.csv'
        for path in [local, fallback]:
            if os.path.exists(path):
                return pd.read_csv(path)
        return pd.DataFrame()


def compute_rfi_monthly_scores(df_raw, project_id_filter=None):
    """
    Compute monthly RFI KPI scores from raw RFI data.

    Methodology per KPI:
      % On Time          — grouped by created_at month; past-due unresolved RFIs = 0 (failed)
      Lead Time          — grouped by created_at month; all RFIs with a due_date
      Time to Resolution — grouped by time_resolved month; resolved RFIs only (actual close time is known)
      Usage Rate         — grouped by created_at month; all RFIs (count/week)
      Documentation Quality — grouped by created_at month; scored against 14-field checklist
    """
    if df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    df['created_at']    = pd.to_datetime(df['created_at'],    utc=True, errors='coerce')
    df['due_date']      = pd.to_datetime(df['due_date'],      utc=True, errors='coerce')
    df['time_resolved'] = pd.to_datetime(df['time_resolved'], utc=True, errors='coerce')
    df = df.dropna(subset=['created_at'])

    if project_id_filter:
        df = df[df['project_id'].astype(str) == str(project_id_filter)]
        if df.empty:
            return pd.DataFrame()

    now = pd.Timestamp.now(tz='UTC')
    df['is_resolved'] = df['time_resolved'].notna()
    df['has_due']     = df['due_date'].notna()
    df['past_due']    = df['due_date'].notna() & (df['due_date'] < now)

    # Days to close — clamped 0–60 per pipeline spec
    df['days_to_close'] = (df['time_resolved'] - df['created_at']).dt.days.clip(0, 60)

    # Lead time — clamped 0–60
    df['lead_time_days'] = (df['due_date'] - df['created_at']).dt.days.clip(0, 60)

    # % On Time logic:
    #   resolved before/on due → 1
    #   unresolved + past due   → 0  (penalised)
    #   unresolved + not yet due → NaN (excluded — outcome unknown)
    #   no due_date             → NaN (excluded)
    df['on_time'] = float('nan')
    df.loc[df['is_resolved'] & df['has_due'], 'on_time'] = (
        (df.loc[df['is_resolved'] & df['has_due'], 'time_resolved'] <=
         df.loc[df['is_resolved'] & df['has_due'], 'due_date']).astype(float)
    )
    df.loc[~df['is_resolved'] & df['past_due'], 'on_time'] = 0.0

    # Documentation quality: count non-empty fields from the pipeline's 14-field checklist
    doc_fields = [
        'assignee_name', 'ball_in_court_name', 'ball_in_court_role', 'cost_code_name',
        'cost_impact_status', 'drawing_number', 'due_date', 'location_name',
        'received_from_name', 'reference', 'responsible_contractor_name',
        'schedule_impact_status', 'specification_section_id', 'time_resolved'
    ]
    present = [f for f in doc_fields if f in df.columns]
    df['doc_quality'] = df[present].notna().astype(bool).sum(axis=1) / 14.0

    df['ym_created']  = df['created_at'].dt.to_period('M')
    df_res = df[df['is_resolved']].copy()
    df_res['ym_resolved'] = df_res['time_resolved'].dt.to_period('M')

    records = []

    # --- % On Time (created_at month, past-due failures included) ---
    for ym, g in df[df['has_due']].groupby('ym_created'):
        pct = g['on_time'].mean()
        if pd.isna(pct):
            continue
        score = round(max(0.0, min(1.0, pct / 0.8)) * 100, 1)
        records.append({'ym': str(ym), 'kpi_name': 'RFI % On Time', 'score': score,
                         'value': round(pct * 100, 1), 'unit': '%',
                         'n': len(g), 'note': f"{int(g['is_resolved'].sum())}/{len(g)} resolved"})

    # --- Lead Time (created_at month, all RFIs with due_date) ---
    for ym, g in df[df['has_due']].groupby('ym_created'):
        avg = g['lead_time_days'].mean()
        if pd.isna(avg):
            continue
        score = round(max(0.0, min(1.0, (avg - 7) / 7)) * 100, 1)
        records.append({'ym': str(ym), 'kpi_name': 'RFI Lead Time', 'score': score,
                         'value': round(avg, 1), 'unit': 'days',
                         'n': len(g), 'note': f"{len(g)} RFIs with due date"})

    # --- Time to Resolution (resolved_at month, resolved RFIs only) ---
    for ym, g in df_res.groupby('ym_resolved'):
        avg = g['days_to_close'].mean()
        if pd.isna(avg):
            continue
        score = round(max(0.0, min(1.0, (21 - avg) / 14)) * 100, 1)
        records.append({'ym': str(ym), 'kpi_name': 'RFI Time to Resolution', 'score': score,
                         'value': round(avg, 1), 'unit': 'days',
                         'n': len(g), 'note': f"{len(g)} resolved RFIs"})

    # --- Usage Rate (created_at month, all RFIs) ---
    for ym, g in df.groupby('ym_created'):
        weeks = ym.days_in_month / 7.0
        rfis_per_week = len(g) / weeks
        score = round(min(100.0, rfis_per_week * 100), 1)
        records.append({'ym': str(ym), 'kpi_name': 'RFI Usage Rate', 'score': score,
                         'value': round(rfis_per_week, 2), 'unit': 'RFIs/week',
                         'n': len(g), 'note': f"{len(g)} RFIs submitted"})

    # --- Documentation Quality (created_at month) ---
    for ym, g in df.groupby('ym_created'):
        avg = g['doc_quality'].mean()
        if pd.isna(avg):
            continue
        score = round(max(0.0, min(1.0, avg / 0.6)) * 100, 1)
        records.append({'ym': str(ym), 'kpi_name': 'RFI Documentation Quality', 'score': score,
                         'value': round(avg * 100, 1), 'unit': '%',
                         'n': len(g), 'note': f"{len(g)} RFIs scored"})

    return pd.DataFrame(records)


@st.cache_data(ttl=3600)
def load_submittal_data():
    """Load Submittal and Submittal Approver data from S3."""
    try:
        import boto3, io as _io
        session = boto3.Session(profile_name='dev')
        s3 = session.client('s3')
        sub_obj = s3.get_object(
            Bucket='kroo-crai-dev',
            Key='companies/Haugland Companies/procore/submittals.csv'
        )
        sub_df = pd.read_csv(_io.BytesIO(sub_obj['Body'].read()))
        app_obj = s3.get_object(
            Bucket='kroo-crai-dev',
            Key='companies/Haugland Companies/procore/submittal_approvers.csv'
        )
        app_df = pd.read_csv(_io.BytesIO(app_obj['Body'].read()))
        return sub_df, app_df
    except Exception:
        return pd.DataFrame(), pd.DataFrame()


def compute_submittal_monthly_scores(sub_raw, app_raw, project_id_filter=None):
    """
    Compute monthly Submittal KPI scores.

    KPIs:
      % On Time       — grouped by created_at month; issue_date <= submit_by
      Approval Rate   — grouped by returned_date month; (Approved + Approved as Noted) / total decisions
      Revision Rate   — grouped by created_at month; % with revision >= 1 (inverted: lower = better)
      Doc Quality     — grouped by created_at month; 3-field completeness checklist
    """
    if sub_raw.empty:
        return pd.DataFrame()

    df = sub_raw.copy()
    df['created_at'] = pd.to_datetime(df['created_at'], utc=True, errors='coerce')
    df['issue_date']  = pd.to_datetime(df['issue_date'],  utc=True, errors='coerce')
    df['submit_by']   = pd.to_datetime(df['submit_by'],   utc=True, errors='coerce')
    df = df.dropna(subset=['created_at'])

    if project_id_filter:
        df = df[df['project_id'].astype(str) == str(project_id_filter)]
        if df.empty:
            return pd.DataFrame()

    df['ym'] = df['created_at'].dt.to_period('M')
    records = []

    # --- % On Time (created_at month; issue_date <= submit_by) ---
    df_deadline = df[df['submit_by'].notna() & df['issue_date'].notna()].copy()
    df_deadline['on_time'] = (df_deadline['issue_date'] <= df_deadline['submit_by']).astype(float)
    for ym, g in df_deadline.groupby('ym'):
        pct = g['on_time'].mean()
        if pd.isna(pct):
            continue
        score = round(max(0.0, min(1.0, pct / 0.8)) * 100, 1)
        records.append({'ym': str(ym), 'kpi_name': 'Submittal % On Time', 'score': score,
                         'value': round(pct * 100, 1), 'unit': '%',
                         'n': len(g), 'note': f"{int(g['on_time'].sum())}/{len(g)} on time"})

    # --- Revision Rate (created_at month; inverted: 0% revision = 100, 25%+ = 0) ---
    if 'revision' in df.columns:
        df['_is_revision'] = (pd.to_numeric(df['revision'], errors='coerce').fillna(0) >= 1).astype(float)
        for ym, g in df.groupby('ym'):
            rev_rate = g['_is_revision'].mean()
            if pd.isna(rev_rate):
                continue
            score = round(max(0.0, min(1.0, 1.0 - (rev_rate / 0.25))) * 100, 1)
            records.append({'ym': str(ym), 'kpi_name': 'Submittal Revision Rate', 'score': score,
                             'value': round(rev_rate * 100, 1), 'unit': '% revised',
                             'n': len(g), 'note': f"{int(g['_is_revision'].sum())}/{len(g)} revised"})

    # --- Doc Quality (created_at month; 3-field checklist) ---
    doc_fields = ['specification_section_id', 'responsible_contractor_id', 'submittal_manager_id']
    present = [f for f in doc_fields if f in df.columns]
    if present:
        df['_doc_q'] = df[present].notna().astype(bool).sum(axis=1) / len(present)
        for ym, g in df.groupby('ym'):
            avg = g['_doc_q'].mean()
            if pd.isna(avg):
                continue
            score = round(max(0.0, min(1.0, avg / 0.8)) * 100, 1)
            records.append({'ym': str(ym), 'kpi_name': 'Submittal Doc Quality', 'score': score,
                             'value': round(avg * 100, 1), 'unit': '%',
                             'n': len(g), 'note': f"{len(g)} submittals scored"})

    # --- Approval Rate (returned_date month; from approvers table) ---
    if not app_raw.empty:
        app = app_raw.copy()
        app['returned_date'] = pd.to_datetime(app['returned_date'], utc=True, errors='coerce')
        if project_id_filter:
            sub_ids = set(df['_id'].astype(str))
            app = app[app['submittal_id'].astype(str).isin(sub_ids)]
        final = ['Approved', 'Approved as Noted', 'Revise and Resubmit', 'Rejected']
        app_final = app[app['response_name'].isin(final)].dropna(subset=['returned_date']).copy()
        app_final['ym'] = app_final['returned_date'].dt.to_period('M')
        app_final['_approved'] = app_final['response_name'].isin(['Approved', 'Approved as Noted']).astype(float)
        for ym, g in app_final.groupby('ym'):
            if len(g) < 5:
                continue
            pct = g['_approved'].mean()
            if pd.isna(pct):
                continue
            score = round(max(0.0, min(1.0, pct / 0.8)) * 100, 1)
            records.append({'ym': str(ym), 'kpi_name': 'Submittal Approval Rate', 'score': score,
                             'value': round(pct * 100, 1), 'unit': '%',
                             'n': len(g), 'note': f"{int(g['_approved'].sum())}/{len(g)} approved"})

    return pd.DataFrame(records)


@st.cache_data(ttl=3600)
def load_observation_data():
    """Load raw Observations data from S3."""
    try:
        import boto3, io as _io
        session = boto3.Session(profile_name='dev')
        s3 = session.client('s3')
        obj = s3.get_object(
            Bucket='kroo-crai-dev',
            Key='companies/Haugland Companies/procore/observations.csv'
        )
        return pd.read_csv(_io.BytesIO(obj['Body'].read()))
    except Exception:
        return pd.DataFrame()


def compute_observation_monthly_scores(df_raw, project_id_filter=None):
    """
    Compute monthly Observation KPI scores.

    KPIs:
      % Closed On Time — grouped by created_at month; past-due open = failed
      Time to Close    — grouped by created_at month; closed observations only
    """
    if df_raw.empty:
        return pd.DataFrame()

    df = df_raw.copy()
    df['created_at'] = pd.to_datetime(df['created_at'], utc=True, errors='coerce')
    df['due_date']   = pd.to_datetime(df['due_date'],   utc=True, errors='coerce')
    df['closed_at']  = pd.to_datetime(df['closed_at'],  utc=True, errors='coerce')
    df = df.dropna(subset=['created_at'])

    if project_id_filter:
        df = df[df['project_id'].astype(str) == str(project_id_filter)]
        if df.empty:
            return pd.DataFrame()

    now = pd.Timestamp.now(tz='UTC')
    df['is_closed'] = df['closed_at'].notna()
    df['has_due']   = df['due_date'].notna()
    df['past_due']  = df['due_date'].notna() & (df['due_date'] < now)
    df['days_to_close'] = (df['closed_at'] - df['created_at']).dt.days.clip(0, 365)

    # % On Time: closed on/before due → 1; unresolved + past due → 0; unknown → NaN
    df['on_time'] = float('nan')
    mask_closed = df['is_closed'] & df['has_due']
    df.loc[mask_closed, 'on_time'] = (
        (df.loc[mask_closed, 'closed_at'] <= df.loc[mask_closed, 'due_date']).astype(float)
    )
    df.loc[~df['is_closed'] & df['past_due'], 'on_time'] = 0.0

    df['ym'] = df['created_at'].dt.to_period('M')
    records = []

    # --- % Closed On Time (created_at month) ---
    for ym, g in df[df['has_due']].groupby('ym'):
        pct = g['on_time'].mean()
        if pd.isna(pct):
            continue
        score = round(max(0.0, min(1.0, pct / 0.8)) * 100, 1)
        records.append({'ym': str(ym), 'kpi_name': 'Obs % Closed On Time', 'score': score,
                         'value': round(pct * 100, 1), 'unit': '%',
                         'n': len(g), 'note': f"{int(g['is_closed'].sum())}/{len(g)} closed"})

    # --- Time to Close (closed_at month; grouped by when observation was resolved) ---
    df_closed = df[df['is_closed']].copy()
    df_closed['ym_closed'] = df_closed['closed_at'].dt.to_period('M')
    for ym, g in df_closed.groupby('ym_closed'):
        if len(g) < 3:
            continue
        avg = g['days_to_close'].mean()
        if pd.isna(avg):
            continue
        score = round(max(0.0, min(1.0, (30.0 - avg) / 30.0)) * 100, 1)
        records.append({'ym': str(ym), 'kpi_name': 'Obs Time to Close', 'score': score,
                         'value': round(avg, 1), 'unit': 'days',
                         'n': len(g), 'note': f"{len(g)} closed · avg {avg:.1f} days"})

    return pd.DataFrame(records)


def display_trends_page(filtered_data, filters):
    """Display monthly trend charts — RFI, Submittal, and Observation."""
    st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>KPI Trends</h1>", unsafe_allow_html=True)
    st.caption("Trends use live Procore data from S3. The sidebar project filter applies to CRAI Score pages only; use the dropdown below to filter Trends by project.")

    _cutoff = (pd.Timestamp.now() - pd.DateOffset(months=12)).to_period('M')

    # ── Project selector (populated from real S3 project IDs) ─
    project_lookup = load_project_lookup()  # {str_id: display_name}
    project_options = ['All Projects'] + sorted(project_lookup.values())
    _id_by_name = {v: k for k, v in project_lookup.items()}

    selected_project_name = st.selectbox(
        "Select Project",
        options=project_options,
        key="trend_project_selector",
    )
    project_id_filter = None if selected_project_name == 'All Projects' else _id_by_name.get(selected_project_name)

    # ── Metric selector ──────────────────────────────────────
    METRIC_OPTIONS = ["RFIs", "Submittals", "Observations"]
    selected_metric = st.selectbox(
        "Select Metric",
        options=METRIC_OPTIONS,
        key="trend_metric_selector",
    )

    # ── Helper: render one full-width chart per KPI ──────────
    def _render_kpi_charts(scores_df, kpi_list):
        """kpi_list: list of (kpi_name, color, method_note, benchmark, direction) tuples.
        benchmark: numeric industry-avg value, or None to omit the line.
        direction: '↑ higher is better', '↓ lower is better', or a custom note."""
        scores_df = scores_df[scores_df['ym'].apply(lambda y: pd.Period(y, 'M') >= _cutoff)]
        if scores_df.empty:
            st.info("No data in the past 12 months.")
            return
        scores_df = scores_df.sort_values('ym')
        x_order = sorted(scores_df['ym'].unique())

        # Format x labels as "Apr 2025" style
        def _fmt_ym(ym_str):
            try:
                return pd.Period(ym_str, 'M').to_timestamp().strftime('%b %Y')
            except Exception:
                return ym_str
        x_labels = [_fmt_ym(m) for m in x_order]

        for kpi, color, method, benchmark, direction in kpi_list:
            kpi_df = scores_df[scores_df['kpi_name'] == kpi].sort_values('ym')
            if kpi_df.empty:
                continue
            unit = kpi_df['unit'].iloc[0] if 'unit' in kpi_df.columns else ''
            x_vals = [_fmt_ym(m) for m in kpi_df['ym']]
            y_vals = kpi_df['value'].tolist()
            # Build customdata: [note, low_n_warning]
            low_n_threshold = 5
            notes = kpi_df['note'].fillna('').tolist()
            ns = kpi_df['n'].tolist()
            low_n_flags = [
                f"<span style='color:#f97316'>⚠ Low sample (n={n}): interpret with caution</span>" if n < low_n_threshold else ''
                for n in ns
            ]
            import numpy as _cd_np
            customdata = _cd_np.array([[note, flag] for note, flag in zip(notes, low_n_flags)], dtype=object)

            # Derive a translucent fill color from the line color
            import re as _re
            _hex = color.lstrip('#')
            _r, _g, _b = (int(_hex[i:i+2], 16) for i in (0, 2, 4))
            fill_color = f'rgba({_r},{_g},{_b},0.10)'
            marker_color = f'rgba({_r},{_g},{_b},1)'

            # Map trend KPI names to tooltip descriptions
            _trend_kpi_desc = {
                'RFI % On Time':             'Percentage of Requests for Information resolved within the required response window. Delays in RFI closure directly stall field productivity and sequence downstream work.',
                'RFI Lead Time':             'Average number of days between RFI creation and its assigned due date. Longer values indicate more generous response windows were set; shorter windows increase the risk of missed deadlines.',
                'RFI Time to Resolution':    'Average number of days from RFI submission to final resolution. Tracks end-to-end cycle time including design response and field acceptance.',
                'RFI Usage Rate':            'Number of RFIs generated per unit of project time. Elevated rates may signal design gaps, scope ambiguity, or inadequate preconstruction coordination.',
                'RFI Documentation Quality': 'Completeness of RFI records scored against a 14-field checklist. Poor documentation limits traceability, dispute resolution, and downstream coordination.',
                'Submittal % On Time':       'Percentage of submittals reviewed and approved within the required timeframe. Late approvals constrain procurement schedules and delay material deliveries.',
                'Submittal Approval Rate':   'Percentage of submittal decisions resulting in Approved or Approved as Noted. Low rates indicate design misalignment, specification gaps, or insufficient pre-coordination.',
                'Submittal Revision Rate':   'Percentage of submittals requiring at least one revision cycle. High revision rates signal inadequate preparation, unclear specifications, or repeated rejections.',
                'Submittal Doc Quality':     'Completeness of submittal records scored against a 3-field checklist. Incomplete submissions slow reviewer turnaround and increase the risk of re-submission cycles.',
                'Obs % Closed On Time':      'Percentage of quality observations resolved and closed within the required timeframe. Unresolved items accumulate and increase the probability of rework and defects.',
                'Obs Time to Close':         'Average days from observation creation to formal close, grouped by the month the observation was resolved. Long resolution times signal resource constraints, accountability gaps, or insufficient follow-through on field issues.',
            }
            desc = _trend_kpi_desc.get(kpi, '')

            st.markdown(
                f"<h3 style='font-size:1.05rem; font-weight:700; color:#111827; "
                f"margin-top:1.75rem; margin-bottom:0.1rem; letter-spacing:-0.01em;'>{kpi}"
                f"<span style='font-size:0.8rem; font-weight:500; color:#6b7280; "
                f"background:#f3f4f6; border-radius:4px; padding:2px 7px; margin-left:10px; "
                f"vertical-align:middle;'>{direction}</span></h3>",
                unsafe_allow_html=True,
            )
            if desc:
                st.markdown(
                    f"<p style='font-size:17px; color:#6b7280; margin-top:0; margin-bottom:0.4rem; line-height:1.45;'>{desc}</p>",
                    unsafe_allow_html=True,
                )
            fig = go.Figure()

            # Industry benchmark dashed line (no built-in annotation — we place it outside)
            if benchmark is not None:
                fig.add_hline(
                    y=benchmark,
                    line=dict(color='#111827', width=1.5, dash='dash'),
                )
                fig.add_annotation(
                    x=1.01,
                    y=benchmark,
                    xref='paper',
                    yref='y',
                    text=f"<b>Industry Avg:</b><br>{benchmark:.1f} {unit}",
                    showarrow=False,
                    xanchor='left',
                    yanchor='middle',
                    font=dict(size=17, color='#111827'),
                    align='left',
                )

            # Shaded area under the line
            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                mode='lines+markers',
                name=kpi,
                showlegend=False,
                fill='tozeroy',
                fillcolor=fill_color,
                line=dict(color=marker_color, width=2.5),
                cliponaxis=False,
                marker=dict(
                    size=8,
                    color='white',
                    line=dict(color=marker_color, width=2.5),
                ),
                customdata=customdata,
                hovertemplate=(
                    f"<b>%{{x}}</b><br>"
                    f"<b>{kpi}:</b> %{{y:.1f}} {unit}<br>"
                    "%{customdata[0]}<br>"
                    "%{customdata[1]}"
                    "<extra></extra>"
                ),
            ))

            import numpy as _np
            y_min = min(y_vals)
            y_max = max(y_vals)
            effective_min = min(y_min, benchmark) if benchmark is not None else y_min
            effective_max = max(y_max, benchmark) if benchmark is not None else y_max
            if unit.startswith('%'):
                # Smart floor: drop empty lower quarters so data fills the chart
                data_floor = min(effective_min, benchmark) if benchmark is not None else effective_min
                if data_floor >= 50:
                    y_range = [50.0, 103.0]
                    y_tick_vals = [50.0, 75.0, 100.0]
                    y_tick_text = ['50', '75', '100']
                elif data_floor >= 25:
                    y_range = [25.0, 103.0]
                    y_tick_vals = [25.0, 50.0, 75.0, 100.0]
                    y_tick_text = ['25', '50', '75', '100']
                else:
                    y_range = [0.0, 103.0]
                    y_tick_vals = [0.0, 25.0, 50.0, 75.0, 100.0]
                    y_tick_text = ['0', '25', '50', '75', '100']
            else:
                y_pad = (effective_max - effective_min) * 0.12 if effective_max != effective_min else abs(effective_max) * 0.12 or 1
                y_range = [max(0, effective_min - y_pad), effective_max + y_pad]
                y_tick_vals = [round(v, 1) for v in _np.linspace(effective_min, effective_max, 5)]
                y_tick_text = [f"{v:.1f}" for v in y_tick_vals]

            fig.update_layout(
                xaxis=dict(
                    showgrid=False,
                    tickangle=-40,
                    tickfont=dict(size=17, color='#6b7280'),
                    categoryorder='array',
                    categoryarray=x_labels,
                    tickvals=x_labels,
                    ticktext=x_labels,
                    showline=True,
                    linecolor='#e5e7eb',
                    linewidth=1,
                    range=[-0.2, len(x_labels) - 0.8],
                    ticks='outside',
                    ticklen=8,
                    tickwidth=2,
                    tickcolor='#9ca3af',
                    showspikes=True,
                    spikemode='toaxis',
                    spikesnap='data',
                    spikecolor='#9ca3af',
                    spikethickness=1,
                    spikedash='dot',
                ),
                yaxis=dict(
                    title=dict(
                        text={
                            '%':          'Completion Rate (%)',
                            '% revised':  'Revision Rate (%)',
                            'days':       'Avg Days',
                            'RFIs/week':  'RFIs per Week',
                        }.get(unit, unit),
                        font=dict(size=17, color='#6b7280'),
                    ),
                    title_font=dict(size=17, color='#6b7280'),
                    gridcolor='#e2e4e7',
                    tickfont=dict(size=17, color='#6b7280'),
                    tickvals=y_tick_vals,
                    ticktext=y_tick_text,
                    range=y_range,
                    zeroline=False,
                    showline=False,
                ),
                plot_bgcolor='white',
                paper_bgcolor='white',
                hovermode='closest',
                hoverdistance=100,
                margin=dict(t=40, b=50, l=60, r=120),
                height=520,
                hoverlabel=dict(
                    bgcolor='white',
                    bordercolor='#e5e7eb',
                    font=dict(size=15, color='#111827'),
                    align='auto',
                    namelength=0,
                ),
            )
            st.plotly_chart(fig, use_container_width=True)

        if project_id_filter:
            st.caption(f"Filtered to project: {project_id_filter}")

    # ── RFIs ─────────────────────────────────────────────────
    if selected_metric == "RFIs":
        with st.spinner("Loading RFI data..."):
            rfi_raw = load_rfi_data()
        if rfi_raw.empty:
            st.warning("RFI data could not be loaded.")
        else:
            rfi_scores = compute_rfi_monthly_scores(rfi_raw, project_id_filter=project_id_filter)
            if rfi_scores.empty:
                st.info("No RFI data available for the selected filters.")
            else:
                _render_kpi_charts(rfi_scores, [
                    ('RFI % On Time',             '#7c3aed', 'submission month; past-due open = failed',  80.0,  '↑ higher is better'),
                    ('RFI Lead Time',             '#06b6d4', 'submission month; all RFIs with due date',  14.0,  '↑ higher is better'),
                    ('RFI Time to Resolution',    '#f97316', 'resolution month; resolved RFIs only',      10.0,  '↓ lower is better'),
                    ('RFI Usage Rate',            '#10b981', 'submission month; RFIs per week',           None,  '↑ more usage = stronger adoption; interpret with project complexity'),
                    ('RFI Documentation Quality', '#6366f1', 'submission month; 14-field checklist',      60.0,  '↑ higher is better'),
                ])

    # ── Submittals ────────────────────────────────────────────
    elif selected_metric == "Submittals":
        with st.spinner("Loading Submittal data..."):
            sub_raw, app_raw = load_submittal_data()
        if sub_raw.empty:
            st.warning("Submittal data could not be loaded.")
        else:
            sub_scores = compute_submittal_monthly_scores(sub_raw, app_raw, project_id_filter=project_id_filter)
            if sub_scores.empty:
                st.info("No Submittal data available for the selected filters.")
            else:
                _render_kpi_charts(sub_scores, [
                    ('Submittal % On Time',     '#7c3aed', 'submission month; issue_date ≤ submit_by deadline',                       85.0,  '↑ higher is better'),
                    ('Submittal Approval Rate', '#10b981', 'response month; (Approved + Approved as Noted) / total decisions',        75.0,  '↑ higher is better'),
                    ('Submittal Revision Rate', '#ef4444', 'submission month; % of submittals on revision ≥ 1',                       20.0,  '↓ lower is better'),
                    ('Submittal Doc Quality',   '#6366f1', 'submission month; 3-field completeness checklist',                        80.0,  '↑ higher is better'),
                ])

    # ── Observations ──────────────────────────────────────────
    elif selected_metric == "Observations":
        with st.spinner("Loading Observation data..."):
            obs_raw = load_observation_data()
        if obs_raw.empty:
            st.warning("Observation data could not be loaded.")
        else:
            obs_scores = compute_observation_monthly_scores(obs_raw, project_id_filter=project_id_filter)
            if obs_scores.empty:
                st.info("No Observation data available for the selected filters.")
            else:
                _render_kpi_charts(obs_scores, [
                    ('Obs % Closed On Time', '#7c3aed', 'creation month; past-due open = failed',      80.0,  '↑ higher is better'),
                    ('Obs Time to Close',    '#f97316', 'close month; closed observations only',        7.0,  '↓ lower is better'),
                ])


def display_scoreboard(summary_for_impact_calc, data):
    """Display portfolio scoreboard with segment analysis"""

    if summary_for_impact_calc.empty:
        st.info("No portfolio data available.")
        return

    search_key = 'scoreboard_search'
    if search_key not in st.session_state:
        st.session_state[search_key] = ''

    filter_col, title_col, spacer_col = st.columns([0.25, 0.5, 0.25])
    with filter_col:
        st.markdown("<h3 style='text-align:left; margin-top:1.5rem; margin-bottom:0.25rem; font-size:1.56rem;'>Segment Portfolio By:</h3><style>h3 a { display: none !important; }</style>", unsafe_allow_html=True)
        segment_by = st.selectbox(
            "Segment Portfolio By:",
            ["Project", "Region", "Project Manager"],
            help="Select how to group the portfolio for analysis",
            label_visibility="collapsed"
        )
        st.markdown("<h3 style='text-align:left; margin-top:-0.8rem; margin-bottom:0.1rem; font-size:1.56rem;'>Search:</h3>", unsafe_allow_html=True)
        st.text_input(
            "Search",
            key=search_key,
            placeholder="\U0001F50D Search by name...",
            label_visibility="collapsed",
            on_change=lambda: st.session_state.update({'scoreboard_page': 0})
        )
    st.markdown("""<style>
        div.st-key-sc_search_input { margin-top: -1.2rem !important; }
        div.st-key-sc_search_input input { font-size: 0.95rem !important; padding: 0.35rem 0.6rem !important; }
    </style>""", unsafe_allow_html=True)
    with title_col:
        st.markdown("<h1 style='text-align:center; margin-bottom:0;'>Portfolio Scoreboard</h1><style>h1 a, h2 a { display: none !important; }</style>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center; margin-top:0; margin-bottom:0.5rem; font-size:1.5rem;'>Segment Performance Analysis</h2>", unsafe_allow_html=True)

    # Map selection to column name
    segment_column_map = {
        "Project": "projectId",
        "Region": "region",
        "Project Manager": "projectManager"
    }
    segment_col = segment_column_map[segment_by]
    
    # Build project metadata from construction KPIs for value/start/end columns.
    project_meta_df = pd.DataFrame(columns=['projectId', 'ProjValue', 'startDate', 'endDate'])
    if 'construction' in data and 'kpis' in data['construction']:
        construction_kpis = data['construction']['kpis'].copy()
        required_cols = {'projectId', 'ProjValue', 'startDate', 'endDate'}
        if required_cols.issubset(set(construction_kpis.columns)):
            project_meta_df = construction_kpis[['projectId', 'ProjValue', 'startDate', 'endDate']].drop_duplicates()
            project_meta_df = project_meta_df.groupby('projectId', as_index=False).first()

            # Normalize value and date fields for consistent display.
            project_meta_df['ProjValue_numeric'] = pd.to_numeric(
                project_meta_df['ProjValue'].astype(str).str.replace(r'[$,]', '', regex=True),
                errors='coerce'
            )
            project_meta_df['startDate_parsed'] = pd.to_datetime(project_meta_df['startDate'], errors='coerce')
            project_meta_df['endDate_parsed'] = pd.to_datetime(project_meta_df['endDate'], errors='coerce')

    # Calculate scoreboard data
    scoreboard_data = []
    
    for segment_value in sorted(summary_for_impact_calc[segment_col].unique()):
        segment_df = summary_for_impact_calc[summary_for_impact_calc[segment_col] == segment_value]
        
        # Calculate average score
        avg_score = segment_df['score'].mean()

        # Derive project metadata for this segment.
        project_ids_in_segment = segment_df['projectId'].dropna().unique()
        segment_meta = project_meta_df[project_meta_df['projectId'].isin(project_ids_in_segment)] if not project_meta_df.empty else pd.DataFrame()

        est_proj_value = None
        est_proj_start_date = None
        est_proj_end_date = None

        if not segment_meta.empty:
            est_proj_value = segment_meta['ProjValue_numeric'].sum(min_count=1)
            est_proj_start_date = segment_meta['startDate_parsed'].min()
            est_proj_end_date = segment_meta['endDate_parsed'].max()
        
        scoreboard_data.append({
            'Segment': segment_value,
            'CR-Score': avg_score,
            'Estimated Project Value': est_proj_value,
            'Est Proj Start Date': est_proj_start_date,
            'Est Proj End Date': est_proj_end_date
        })
    
    # Create DataFrame and sort by CR-Score (highest first)
    scoreboard_df = pd.DataFrame(scoreboard_data)
    
    if scoreboard_df.empty:
        st.info("No data available for selected segment.")
        return
    
    sort_col_key = 'scoreboard_sort_column'
    sort_dir_key = 'scoreboard_sort_direction'
    page_key = 'scoreboard_page'
    if sort_col_key not in st.session_state:
        st.session_state[sort_col_key] = 'CR-Score'
    if sort_dir_key not in st.session_state:
        st.session_state[sort_dir_key] = 'desc'
    if page_key not in st.session_state:
        st.session_state[page_key] = 0

    def toggle_sort(column_name):
        current_col = st.session_state[sort_col_key]
        current_dir = st.session_state[sort_dir_key]
        if current_col == column_name:
            st.session_state[sort_dir_key] = 'asc' if current_dir == 'desc' else 'desc'
        else:
            st.session_state[sort_col_key] = column_name
            st.session_state[sort_dir_key] = 'desc'
        st.session_state[page_key] = 0

    sort_column = st.session_state[sort_col_key]
    sort_ascending = st.session_state[sort_dir_key] == 'asc'
    scoreboard_df = scoreboard_df.sort_values(by=sort_column, ascending=sort_ascending, na_position='last').reset_index(drop=True)

    # Apply name search filter
    search_term = st.session_state.get(search_key, '').strip()
    if search_term:
        scoreboard_df = scoreboard_df[scoreboard_df['Segment'].str.contains(search_term, case=False, na=False)].reset_index(drop=True)

    rows_per_page = 50
    total_rows = len(scoreboard_df)
    total_pages = max(1, math.ceil(total_rows / rows_per_page))
    # Clamp page in case data changed
    if st.session_state[page_key] >= total_pages:
        st.session_state[page_key] = total_pages - 1
    current_page = st.session_state[page_key]
    page_start = current_page * rows_per_page
    page_end = min(page_start + rows_per_page, total_rows)
    paged_df = scoreboard_df.iloc[page_start:page_end]

    def format_currency(value):
        if pd.isna(value):
            return 'N/A'
        return f"${value:,.0f}"

    def format_date(value):
        if pd.isna(value):
            return 'N/A'
        return value.strftime('%m/%d/%Y')

    def sort_label(column_name, label):
        if st.session_state[sort_col_key] != column_name:
            return label
        return f"{label} {'↑' if st.session_state[sort_dir_key] == 'asc' else '↓'}"

    # Sort buttons targeted directly by st-key-* CSS classes — no marker needed.
    # This means col 0 has exactly ONE element (just its button), so all columns are aligned.
    st.markdown(f"""<style>
        div[data-testid="stHorizontalBlock"]:has(.st-key-sc_sort_segment) {{
            gap: 0 !important; margin-bottom: 0 !important;
        }}
        div.st-key-sc_sort_segment button,
        div.st-key-sc_sort_cr button,
        div.st-key-sc_sort_value button,
        div.st-key-sc_sort_start button,
        div.st-key-sc_sort_end button {{
            background: #f3f4f6 !important; color: #374151 !important;
            border: none !important; border-right: 1px solid #e5e7eb !important;
            border-radius: 0 !important;
            box-shadow: none !important; outline: none !important;
            font-size: 0.8rem !important; font-weight: 700 !important;
            text-transform: uppercase !important; letter-spacing: 0.05em !important;
            padding: 0.5rem 0.6rem !important; transition: none !important;
        }}
        div.st-key-sc_sort_segment button:hover,
        div.st-key-sc_sort_cr button:hover,
        div.st-key-sc_sort_value button:hover,
        div.st-key-sc_sort_start button:hover,
        div.st-key-sc_sort_end button:hover {{
            background: #e5e7eb !important; color: #111 !important;
        }}
        div.st-key-sc_sort_segment button:focus:not(:active),
        div.st-key-sc_sort_cr button:focus:not(:active),
        div.st-key-sc_sort_value button:focus:not(:active),
        div.st-key-sc_sort_start button:focus:not(:active),
        div.st-key-sc_sort_end button:focus:not(:active) {{
            box-shadow: none !important;
        }}
        div.st-key-sc_sort_segment button {{ border-radius: 0.375rem 0 0 0.375rem !important; }}
        div.st-key-sc_sort_end button     {{ border-radius: 0 0.375rem 0.375rem 0 !important; border-right: none !important; }}
        .sc-tbl {{ width:100%; border-collapse:separate; border-spacing:0 0.35rem; font-size:0.95rem; }}
        .sc-tbl td {{ padding:0.6rem 0.6rem; background:#f9fafb; vertical-align:middle; border:none; }}
        .sc-tbl td:first-child {{ border-radius:0.375rem 0 0 0.375rem; }}
        .sc-tbl td:last-child  {{ border-radius:0 0.375rem 0.375rem 0; }}
        .sc-tbl td.seg-name    {{ font-weight:700; color:#111; width:20%; font-size:1.19rem; }}
        .sc-tbl td.cr-score   {{ width:22%; padding-top:0.6rem; }}
        .sc-tbl td.proj-value {{ text-align:center; width:20%; font-size:1.19rem; }}
        .sc-tbl td.proj-date  {{ text-align:center; width:19%; font-size:1.19rem; }}
        .sc-tbl .sc-bar-wrap span {{ padding: 0.1rem 0.30rem !important; line-height: 1 !important; }}
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-sc_sort_segment) {{ margin-top: -1.5rem !important; }}
    </style>""", unsafe_allow_html=True)
    with st.container(border=True):
        pass

    # Pagination controls
    if True:
        st.markdown("""<style>
            div[data-testid="stHorizontalBlock"]:has(.st-key-sc_pg_first) {
                margin-top: -0.5rem !important;
                gap: 0.5rem !important;
                align-items: center !important;
                flex-wrap: nowrap !important;
                min-width: max-content !important;
            }
            div[data-testid="stHorizontalBlock"]:has(.st-key-sc_pg_first) > div[data-testid="stColumn"] {
                flex: 0 0 auto !important;
                width: auto !important;
                min-width: 0 !important;
                overflow: visible !important;
            }
            div.st-key-sc_pg_first button, div.st-key-sc_pg_prev button,
            div.st-key-sc_pg_next button, div.st-key-sc_pg_last button {
                background: #f3f4f6 !important; color: #000 !important;
                border: 1px solid #e5e7eb !important; border-radius: 0.375rem !important;
                font-size: 2.55rem !important; font-weight: 700 !important;
                padding: 0 0.4rem !important; box-shadow: none !important;
                height: 2.0rem !important; min-height: 0 !important; width: auto !important;
                line-height: 1 !important; overflow: visible !important;
                display: flex !important; align-items: center !important;
                justify-content: center !important;
            }
            div.st-key-sc_pg_first button p, div.st-key-sc_pg_prev button p,
            div.st-key-sc_pg_next button p, div.st-key-sc_pg_last button p {
                font-size: 2.55rem !important; font-weight: 700 !important;
                color: #000 !important; line-height: 1 !important; margin: 0 !important;
                padding: 0 !important; display: flex !important;
                align-items: center !important; justify-content: center !important;
            }
            div.st-key-sc_pg_first button:hover, div.st-key-sc_pg_prev button:hover,
            div.st-key-sc_pg_next button:hover, div.st-key-sc_pg_last button:hover {
                background: #e5e7eb !important; color: #000 !important;
            }
            div.st-key-sc_pg_first button:disabled, div.st-key-sc_pg_prev button:disabled,
            div.st-key-sc_pg_next button:disabled, div.st-key-sc_pg_last button:disabled {
                opacity: 1 !important; cursor: default !important;
            }
            div.st-key-sc_pg_first button:disabled p, div.st-key-sc_pg_prev button:disabled p,
            div.st-key-sc_pg_next button:disabled p, div.st-key-sc_pg_last button:disabled p {
                color: #bbb !important;
            }
            div[data-testid="stHorizontalBlock"]:has(.st-key-sc_pg_first) {
                margin-top: -0.5rem !important;
                margin-bottom: 0 !important;
                margin-left: auto !important;
                margin-right: auto !important;
                gap: 0.5rem !important;
                align-items: center !important;
                flex-wrap: nowrap !important;
                width: max-content !important;
            }
            div[data-testid="stHorizontalBlock"]:has(.st-key-sc_pg_first) > div[data-testid="stColumn"] {
                flex: 0 0 auto !important;
                width: auto !important;
                min-width: 0 !important;
                overflow: visible !important;
            }
        </style>""", unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns([1, 1, 2, 1, 1])
        with c1:
            st.button("«", key='sc_pg_first', on_click=lambda: st.session_state.update({page_key: 0}), disabled=(current_page == 0), use_container_width=True)
        with c2:
            st.button("‹", key='sc_pg_prev', on_click=lambda: st.session_state.update({page_key: max(0, current_page - 1)}), disabled=(current_page == 0), use_container_width=True)
        with c3:
            st.markdown(f"<p style='text-align:center; margin:0; margin-top:-0.4rem; padding:0 1.5rem; font-weight:700; font-size:1.3rem; width:100%; white-space:nowrap; display:flex; align-items:center; justify-content:center; height:2.0rem;'>Page {current_page + 1} of {total_pages}</p>", unsafe_allow_html=True)
        with c4:
            st.button("›", key='sc_pg_next', on_click=lambda: st.session_state.update({page_key: min(total_pages - 1, current_page + 1)}), disabled=(current_page == total_pages - 1), use_container_width=True)
        with c5:
            st.button("»", key='sc_pg_last', on_click=lambda: st.session_state.update({page_key: total_pages - 1}), disabled=(current_page == total_pages - 1), use_container_width=True)

        st.markdown("""<style>
            div[data-testid="stHorizontalBlock"]:has(.st-key-sc_goto_input) {
                margin-top: 0 !important;
                margin-left: auto !important;
                margin-right: auto !important;
                width: max-content !important;
                align-items: center !important;
                gap: 0.4rem !important;
            }
            div[data-testid="stHorizontalBlock"]:has(.st-key-sc_goto_input) + div,
            div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stHorizontalBlock"]:has(.st-key-sc_goto_input)) {
                margin-top: 0 !important;
                padding-top: 0 !important;
            }
            div[data-testid="stVerticalBlock"] > div:has(+ div > div[data-testid="stHorizontalBlock"]:has(.st-key-sc_goto_input)) {
                margin-bottom: 0 !important;
                padding-bottom: 0 !important;
            }
            div.st-key-sc_goto_input, div.st-key-sc_goto_input > div, div.st-key-sc_goto_input > div > div {
                min-height: 0 !important; height: auto !important;
                margin-bottom: 0 !important; padding-bottom: 0 !important;
            }
            div.st-key-sc_goto_input input {
                width: 3.0rem !important; text-align: center !important;
                height: 2.0rem !important; min-height: 0 !important;
                padding-top: 0 !important; padding-bottom: 0 !important;
                padding-left: 0.4rem !important; padding-right: 0.4rem !important;
                font-size: 1.3rem !important; font-weight: 700 !important;
                line-height: normal !important; box-sizing: border-box !important;
            }
            div[data-testid="stHorizontalBlock"]:has(.st-key-sc_goto_input) > div[data-testid="stColumn"]:first-child {
                flex: 0 0 max-content !important; width: max-content !important;
                display: flex !important; align-items: center !important;
            }
            div[data-testid="stHorizontalBlock"]:has(.st-key-sc_goto_input) > div[data-testid="stColumn"]:last-child {
                flex: 0 0 auto !important; width: auto !important;
                display: flex !important; align-items: center !important;
            }
            div.st-key-sc_goto_btn button {
                background: #f3f4f6 !important; color: #000 !important;
                border: 1px solid #e5e7eb !important; border-radius: 0.375rem !important;
                font-size: 0.85rem !important; font-weight: 600 !important;
                padding: 0.3rem 0.7rem !important; box-shadow: none !important;
            }
        </style>""", unsafe_allow_html=True)

        def go_to_page():
            val = st.session_state.get('sc_goto_input', '#')
            try:
                page_num = int(val)
                st.session_state[page_key] = max(0, min(total_pages - 1, page_num - 1))
            except (ValueError, TypeError):
                pass

        gl, gi = st.columns([1, 1])
        with gl:
            st.markdown("<p style='font-size:1.3rem;font-weight:700;margin:0;display:flex;align-items:center;height:2.0rem;white-space:nowrap;'>Go to Page</p>", unsafe_allow_html=True)
        with gi:
            st.text_input("Go to page", value="#", key='sc_goto_input',
                          label_visibility='collapsed', on_change=go_to_page)

# --- Main Application ---
def main():
    original_data = load_data()
    if not original_data: st.stop()

    st.markdown("""<style>
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] .stSelectbox label,
        section[data-testid="stSidebar"] .stSlider label,
        section[data-testid="stSidebar"] .stRadio label:first-of-type,
        section[data-testid="stSidebar"] p { font-weight: 700 !important; }
    </style>""", unsafe_allow_html=True)

    # Build project metadata for additional global filters.
    project_meta = pd.DataFrame(columns=['projectId', 'ProjValue_numeric', 'startDate_parsed'])
    if 'construction' in original_data and 'kpis' in original_data['construction']:
        construction_kpis = original_data['construction']['kpis'].copy()
        required_cols = {'projectId', 'ProjValue', 'startDate'}
        if required_cols.issubset(set(construction_kpis.columns)):
            project_meta = construction_kpis[['projectId', 'ProjValue', 'startDate']].drop_duplicates()
            project_meta = project_meta.groupby('projectId', as_index=False).first()
            project_meta['ProjValue_numeric'] = pd.to_numeric(
                project_meta['ProjValue'].astype(str).str.replace(r'[$,]', '', regex=True),
                errors='coerce'
            )
            project_meta['startDate_parsed'] = pd.to_datetime(project_meta['startDate'], errors='coerce')

    value_breakpoints = [
        0,
        100000,
        500000,
        1000000,
        5000000,
        10000000,
        25000000,
        50000000,
        100000000,
        1000000000
    ]
    value_options = [f"${v:,.0f}" for v in value_breakpoints] + ["> $1,000,000,000"]

    def value_label_to_number(label):
        if label == "> $1,000,000,000":
            return float('inf')
        return float(label.replace('$', '').replace(',', ''))

    date_min = date_max = None
    if not project_meta.empty and project_meta['startDate_parsed'].notna().any():
        date_min = project_meta['startDate_parsed'].min().date()
        date_max = project_meta['startDate_parsed'].max().date()
    
    import base64 as _b64
    with open("static/cr_ai_logo.png", "rb") as _f:
        _logo_b64 = _b64.b64encode(_f.read()).decode()
    st.sidebar.markdown(f"""<style>
        section[data-testid='stSidebar'] > div:first-child {{ padding-top: 0 !important; }}
        section[data-testid='stSidebar'] .stSidebarContent {{ padding-top: 0 !important; }}
        section[data-testid='stSidebar'] [data-testid='stSidebarContent'] {{ padding-top: 0 !important; }}
        [data-testid='stSidebarHeader'] {{ height: 2rem !important; min-height: 0 !important; padding: 0 !important; }}
    </style><div style='text-align:center;padding-top:0.5rem;margin-bottom:0;'><img src='data:image/png;base64,{_logo_b64}' width='100'></div>""", unsafe_allow_html=True)
    st.sidebar.markdown("<style>section[data-testid='stSidebar'] h1:first-of-type { margin-top: 0 !important; padding-top: 0 !important; }</style>", unsafe_allow_html=True)
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

    value_range_labels = st.sidebar.select_slider(
        "Estimated Project Value",
        options=value_options,
        value=(value_options[0], value_options[-1])
    )
    value_range = (value_label_to_number(value_range_labels[0]), value_label_to_number(value_range_labels[1]))

    if date_min is not None and date_max is not None:
        if date_min == date_max:
            date_range = (date_min, date_max)
            st.sidebar.markdown(f"Est Proj Start Date: {date_min.strftime('%m/%d/%Y')}")
        else:
            date_range = st.sidebar.date_input(
                "Est Proj Start Date",
                value=(date_min, date_max),
                min_value=date_min,
                max_value=date_max,
                format="MM/DD/YYYY"
            )
            if not isinstance(date_range, tuple) or len(date_range) != 2:
                date_range = (date_min, date_max)
    else:
        date_range = None
        st.sidebar.markdown("Est Proj Start Date: N/A")
    
    summary_for_impact_calc = original_data['executive_summary'].copy()
    if filters['project'] != 'All Projects': summary_for_impact_calc = summary_for_impact_calc[summary_for_impact_calc['projectId'] == filters['project']]
    if filters['region'] != 'All Regions': summary_for_impact_calc = summary_for_impact_calc[summary_for_impact_calc['region'] == filters['region']]
    if filters['pm'] != 'All PMs': summary_for_impact_calc = summary_for_impact_calc[summary_for_impact_calc['projectManager'] == filters['pm']]

    if value_range is not None:
        min_value, max_value = value_range
        if max_value == float('inf'):
            value_mask = project_meta['ProjValue_numeric'] >= float(min_value)
        else:
            value_mask = project_meta['ProjValue_numeric'].between(float(min_value), float(max_value), inclusive='both')
        value_project_ids = set(project_meta.loc[value_mask, 'projectId'])
        summary_for_impact_calc = summary_for_impact_calc[summary_for_impact_calc['projectId'].isin(value_project_ids)]

    if date_range is not None:
        start_date, end_date = date_range
        start_ts = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)
        date_project_ids = set(
            project_meta.loc[
                project_meta['startDate_parsed'].between(start_ts, end_ts, inclusive='both'),
                'projectId'
            ]
        )
        summary_for_impact_calc = summary_for_impact_calc[summary_for_impact_calc['projectId'].isin(date_project_ids)]

    # Filter action items based on sidebar selections
    action_items_filtered = original_data.get('action_items', pd.DataFrame()).copy()
    if not action_items_filtered.empty:
        if filters['project'] != 'All Projects': 
            action_items_filtered = action_items_filtered[action_items_filtered['projectId'] == filters['project']]
        if filters['region'] != 'All Regions': 
            action_items_filtered = action_items_filtered[action_items_filtered['region'] == filters['region']]
        if filters['pm'] != 'All PMs': 
            action_items_filtered = action_items_filtered[action_items_filtered['projectManager'] == filters['pm']]
        action_items_filtered = action_items_filtered[action_items_filtered['impact_category'] == filters['impact_category']]

    summary_df = summary_for_impact_calc.copy()
    summary_df = summary_df[summary_df['impact_category'] == filters['impact_category']]
    
    filtered_data = copy.deepcopy(original_data)
    filtered_data['executive_summary'] = summary_df
    filtered_data['action_items'] = action_items_filtered
    
    final_filtered_project_ids = summary_df['projectId'].unique()
    for phase in PHASE_INFO.keys():
        if phase in filtered_data:
            filtered_data[phase]['processes'] = filtered_data[phase]['processes'][filtered_data[phase]['processes']['projectId'].isin(final_filtered_project_ids)]
            filtered_data[phase]['kpis'] = filtered_data[phase]['kpis'][filtered_data[phase]['kpis']['projectId'].isin(final_filtered_project_ids)]

    st.sidebar.caption(f"Last updated: {datetime.date.today().strftime('%m/%d/%Y')}")
    st.sidebar.markdown("---")
    st.sidebar.title("Navigation")
    
    nav_options = ["Executive Summary", "Portfolio Scoreboard", "Bidding", "Preconstruction", "Construction", "Closeout", "KPI Trends"]
    page_selection = st.sidebar.radio("Page Navigation", nav_options, label_visibility="collapsed")

    if page_selection == "Executive Summary":
        display_executive_summary(filtered_data, summary_for_impact_calc, filters['impact_category'])
    elif page_selection == "Portfolio Scoreboard":
        display_scoreboard(summary_for_impact_calc, original_data)
    elif page_selection == "KPI Trends":
        display_trends_page(filtered_data, filters)
    else:
        display_phase_summary_page(page_selection.lower(), filtered_data, filters['impact_category'], summary_for_impact_calc)

    st.markdown(f"""
    <div style="text-align: center; color: #6b7280; font-size: 0.875rem; margin-top: 1rem; padding-bottom: 1rem;">
         <p style="margin-bottom:0.25rem;">&copy; {datetime.date.today().year} Construction Risk AI. All rights reserved.</p>
         <p style-top:0;">Data provided for informational purposes only. Consult with experts for detailed analysis.</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()