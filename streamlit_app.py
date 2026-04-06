import streamlit as st
import pandas as pd
import datetime
import os
import html
import copy
import re
import math

# --- Page Configuration (MUST BE THE FIRST STREAMLIT COMMAND) ---
st.set_page_config(page_title="CR-Score Dashboard (Construction View)", layout="wide")

# Style primary buttons as professional blue with bold labels.
st.markdown(
    """
    <style>
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
    <div style="display:flex; justify-content:center; align-items:center; width:100%; margin:1rem 0 0.5rem 0;">
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

def render_kpi_summary_section(title, rows_df, detail_func, detail_header, state_key=None):
    with st.container(border=True):
        if state_key:
            title_col, button_col = st.columns([0.72, 0.28])
            with title_col:
                st.markdown(f"<h2 style='text-align: left; font-size: 1.5rem; margin-bottom: 0.5rem;'>{title}</h2>", unsafe_allow_html=True)
            with button_col:
                button_label = "Hide Details" if st.session_state.get(state_key, False) else "Show Details"
                st.button(button_label, key=f"btn_{state_key}", on_click=lambda s_key=state_key: st.session_state.update({s_key: not st.session_state.get(s_key, False)}), use_container_width=False, type="primary")
            if not st.session_state.get(state_key, False):
                return
        else:
            st.markdown(f"<h2 style='text-align: center; font-size: 1.5rem;'>{title}</h2>", unsafe_allow_html=True)

        if rows_df.empty:
            st.info("No KPI data for current selection.")
            return

        header_cols = st.columns([0.12, 0.30, 0.58])
        header_cols[0].markdown("<span style='font-size: 1.5rem;'><strong>Rank</strong></span>", unsafe_allow_html=True)
        header_cols[1].markdown("<span style='font-size: 1.5rem;'><strong>KPI Name</strong></span>", unsafe_allow_html=True)
        header_cols[2].markdown(f"<span style='font-size: 1.5rem;'><strong>{detail_header}</strong></span>", unsafe_allow_html=True)
        for i, row in rows_df.iterrows():
            kpi_name_display = format_kpi_name(row['kpi_name'])
            detail_text = detail_func(row['kpi_name'])
            row_cols = st.columns([0.12, 0.30, 0.58])
            row_cols[0].markdown(f"<span style='font-size: 1.5rem;'><strong>{i+1}</strong></span>", unsafe_allow_html=True)
            row_cols[1].markdown(f"<span style='font-size: 1.5rem;'>{html.escape(kpi_name_display)}</span>", unsafe_allow_html=True)
            row_cols[2].markdown(f"<span style='font-size: 1.2rem;'>{html.escape(detail_text)}</span>", unsafe_allow_html=True)

def build_kpi_tooltip(kpi_name):
    name = str(kpi_name or "").strip()
    lowered = name.lower()

    definition_overrides = {
        '% of bids targeted': 'Percentage of identified opportunities that are intentionally pursued through the bid pipeline.',
        'as-built drawing accuracy': 'Degree to which final as-built drawings match installed field conditions.',
        'budgets create date': 'Elapsed time to create the baseline project budget after project kickoff.',
        'client training completion': 'Percentage of required owner/end-user training sessions completed before handover.',
        'daily logs rate': 'Frequency and consistency of daily field log completion.',
        'daily logs delay': 'Lag between field activity date and daily log submission date.',
        'meetings documentation': 'Completeness and timeliness of meeting records, decisions, and assigned actions.',
        'meetings rate': 'Frequency of planned coordination/production meetings held on schedule.',
        'photos usage': 'Rate of required photo documentation captured and attached to records.',
        'drawings usage': 'Extent to which current drawing sets are actively used by project teams in execution.',
        'specifications usage': 'Extent to which teams reference and apply technical specifications during execution.',
        'gantt chart completion rate': 'Rate of required schedule updates and task status completion in the master plan.',
        'o&m manuals submitted timely': 'Percentage of O&M manuals submitted by required turnover deadlines.'
    }

    def infer_definition(metric_name, metric_lower):
        if metric_lower in definition_overrides:
            return definition_overrides[metric_lower]
        if 'lead time' in metric_lower:
            return 'Time between the create date and the due date for the item.'
        if 'closed on time' in metric_lower:
            return 'Percent of items closed before the due date (on time).'
        if 'detail quality' in metric_lower:
            return 'Quality and completeness of item documentation details entered by users.'
        if 'rate' in metric_lower:
            return 'Count of items divided by the number of project days.'
        if 'lead time' in metric_lower:
            return f"Average elapsed time to complete {metric_name}."
        if 'time to close' in metric_lower:
            return f"Average time required to close {metric_name.replace('Time to Close', '').strip()} items."
        if 'rate' in metric_lower:
            return f"Percentage/frequency metric showing how consistently {metric_name} is achieved."
        if 'variance' in metric_lower:
            return f"Difference between planned and actual outcomes for {metric_name}."
        if 'ratio' in metric_lower:
            return f"Relative relationship between two linked quantities in {metric_name}."
        if 'cycle' in metric_lower:
            return f"Average cycle duration for {metric_name}."
        if 'completion' in metric_lower or 'closed on time' in metric_lower:
            return f"Share of required items completed on time for {metric_name}."
        if 'compliance' in metric_lower:
            return f"Extent to which required standards are satisfied for {metric_name}."
        if 'score' in metric_lower:
            return f"Composite performance score for {metric_name}."
        return f"Operational performance metric for {metric_name}."

    if lowered in KPI_GUIDANCE_MAP:
        definition = infer_definition(name, lowered)
        return f"Definition: {definition} Why it matters: {KPI_GUIDANCE_MAP[lowered]}"

    fallback_definition = infer_definition(name, lowered)
    fallback_why = "Helps teams detect performance drift early and prioritize actions before schedule, cost, quality, or safety risk worsens."
    return f"Definition: {fallback_definition} Why it matters: {fallback_why}"

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

    def impact_badge_html(label):
        style_map = {
            'High': 'background:#dcfce7; color:#166534;',
            'Average': 'background:#ecfccb; color:#3f6212;',
            'Low': 'background:#fef9c3; color:#854d0e;'
        }
        style = style_map.get(label, style_map['Average'])
        return f"<span style='display:inline-block; min-width:5.5rem; text-align:center; padding:0.2rem 0.6rem; border-radius:9999px; font-size:1.25rem; font-weight:700; {style}'>{label}</span>"

    with st.container(border=True):
        header_cols = st.columns([0.4, 0.2, 0.15, 0.1, 0.15])
        header_cols[0].markdown("<span style='font-size: 1.5rem;'><strong>KPI Name</strong></span>", unsafe_allow_html=True)
        header_cols[1].markdown("<div style='text-align:center; font-size: 1.5rem;'><strong>Best Practice</strong></div>", unsafe_allow_html=True)
        header_cols[2].markdown("<div style='text-align:center; font-size: 1.5rem;'><strong>Actual (Avg)</strong></div>" if is_averaged else "<div style='text-align:center; font-size: 1.5rem;'><strong>Actual</strong></div>", unsafe_allow_html=True)
        header_cols[3].markdown("<div style='text-align:center; font-size: 1.5rem;'><strong>Score</strong></div>", unsafe_allow_html=True)
        header_cols[4].markdown("<span style='font-size: 1.5rem;'><strong>Priority</strong></span>", unsafe_allow_html=True)
        
        for _, row in display_df.iterrows():
            row_cols = st.columns([0.4, 0.2, 0.15, 0.1, 0.15])
            actual_val = row['actual_numeric']
            unit = row.get('unit', '')
            actual_display = f"{actual_val:.0%}" if unit == '%' else f"{actual_val:.1f}"
            kpi_name = str(row.get('kpi_name', 'N/A'))
            kpi_name_display = format_kpi_name(kpi_name)
            tooltip_text = build_kpi_tooltip(kpi_name)
            row_cols[0].markdown(
                f"<span style='font-size: 1.5rem; cursor: help;' title=\"{html.escape(tooltip_text, quote=True)}\">{html.escape(kpi_name_display)} <span style='font-size: 1.05rem; color:#6b7280;'>[?]</span></span>",
                unsafe_allow_html=True
            )
            row_cols[1].markdown(f"<div style='text-align:center; font-size: 1.5rem;'>{html.escape(str(row.get('bp_range_display', 'N/A')))}</div>", unsafe_allow_html=True)
            row_cols[2].markdown(f"<div style='text-align:center; font-size: 1.5rem;'>{actual_display}</div>", unsafe_allow_html=True)
            row_cols[3].markdown(f"<div style='text-align:center; font-size: 1.5rem;'>{row.get('score', 0):.0f}</div>", unsafe_allow_html=True)
            row_cols[4].markdown(impact_badge_html(row.get('impact_label', 'Average')), unsafe_allow_html=True)

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
    st.markdown(
        """<div style="display:flex;justify-content:center;margin-bottom:1rem;">
        <svg width="150" height="150" xmlns="http://www.w3.org/2000/svg">
          <circle cx="75" cy="75" r="70" fill="red" />
          <text x="75" y="80" text-anchor="middle" fill="white" font-size="14" font-weight="bold">TEST CIRCLE</text>
        </svg></div>""",
        unsafe_allow_html=True
    )
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

    top_row_left, top_row_right = st.columns(2)
    with top_row_left:
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; margin-bottom: 0.25rem; font-size: 1.5rem;'>CR-Score</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; max-width: 100%; margin: 0.25rem auto 0.5rem auto; font-size:1.62em;'>Represents the adoption of Best Practices for all KPIs across all 4 Phases of Operations.</p>", unsafe_allow_html=True)
            st.markdown(circular_score_meter_html(cr_score, size=330), unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("<h3 style='text-align: center; margin-bottom: 0.5rem; font-size: 1.4rem;'>Estimated Impact of Operational Performance</h3>", unsafe_allow_html=True)
            est_col1, est_col2 = st.columns([0.5, 0.5])
            with est_col1:
                st.markdown("<p style='text-align: right; margin-bottom: 0.2rem; font-size: 1.4rem;'>Improvement in Project Costs:</p>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: right; margin-bottom: 0.2rem; font-size: 1.4rem;'>Improvement in Project Timeline:</p>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: right; margin-bottom: 0.2rem; font-size: 1.4rem;'>Reduction in Incidents:</p>", unsafe_allow_html=True)
            with est_col2:
                st.markdown(f"<p style='font-weight: 700; color: #2563eb; margin-bottom: 0.2rem; font-size: 1.4rem;'>{cost_estimate:.1f}% out of 18.0% possible</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-weight: 700; color: #2563eb; margin-bottom: 0.2rem; font-size: 1.4rem;'>{schedule_estimate:.1f}% out of 30.0% possible</p>", unsafe_allow_html=True)
                st.markdown(f"<p style='font-weight: 700; color: #2563eb; margin-bottom: 0.2rem; font-size: 1.4rem;'>{safety_estimate:.1f}% out of 60.0% possible</p>", unsafe_allow_html=True)

    with top_row_right:
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; margin-bottom: 0.1rem; font-size: 1.5rem;'>CR-Score Components</h2>", unsafe_allow_html=True)
            st.markdown("<h3 style='text-align: center; margin-top: 0; margin-bottom: 0.5rem;'>4 Phases of Operations</h3>", unsafe_allow_html=True)
            phase_definitions = {"Bidding": {"col": "phaseScore_bidding", "desc": "selecting what jobs to bid on and building estimates"},"Precon": {"col": "phaseScore_precon", "desc": "For bids that are won, all the project preparation"},"Construction": {"col": "phaseScore_construction", "desc": "executing the plan and completing the project"},"Closeout": {"col": "phaseScore_closeout", "desc": "wrap up of all work and handoff to the customer"}}
            for name, info in phase_definitions.items():
                st.markdown(f"<div style='font-size: 1.5rem; margin-bottom: 1.5rem;'><strong>{html.escape(name)}</strong> - <em>{html.escape(info['desc'])}</em></div>", unsafe_allow_html=True)
                st.markdown(horizontal_risk_bar_html(summary_df[info["col"]].mean(), width_percentage=90, height='1.65rem', font_size='1.2rem', top_offset='-1.8rem'), unsafe_allow_html=True)

    kpis_for_actions = all_kpis_df[all_kpis_df['impact_category'] == impact_category_filter] if not all_kpis_df.empty else pd.DataFrame()
    executive_top_performing = build_top_performing_kpis(kpis_for_actions)
    executive_top_priority = build_top_priority_kpis(kpis_for_actions)

    st.markdown("<hr style='margin-top: 1rem; margin-bottom: 0.75rem;'>", unsafe_allow_html=True)
    bottom_left, bottom_right = st.columns(2)
    with bottom_left:
        render_kpi_summary_section("Top Performing KPIs", executive_top_performing, get_kpi_strength_detail, "Details")
    with bottom_right:
        render_kpi_summary_section("Top Priority KPIs to Improve", executive_top_priority, get_kpi_guidance, "Guidance")


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
        st.markdown(f"<h2 style='text-align: center; font-size: 1.5rem;'>{phase_key.capitalize()} Phase Score</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-size:1.62em;'>{PHASE_DESCRIPTIONS.get(phase_key, '')}</p>", unsafe_allow_html=True)
        st.markdown(f"<div style='margin-top: 2.0rem;'>{horizontal_risk_bar_html(phase_score, height='1.95rem', font_size='2.7rem', top_offset='-3.15rem', width_percentage=90)}</div>", unsafe_allow_html=True)

    top_performing_df = build_top_performing_kpis(phase_kpis_all)
    top_priority_df = build_top_priority_kpis(phase_kpis_all)

    col_top_performing, col_top_priority = st.columns(2)
    with col_top_performing:
        render_kpi_summary_section("Top Performing KPIs", top_performing_df, get_kpi_strength_detail, "Details", state_key=f"{phase_key}_top_performing")

    with col_top_priority:
        render_kpi_summary_section("Top Priority KPIs to Improve", top_priority_df, get_kpi_guidance, "Guidance", state_key=f"{phase_key}_top_priority")

    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown(f"<h2 style='text-align: center; font-size: 1.5rem;'>{phase_key.capitalize()} Processes</h2>", unsafe_allow_html=True)
    for process_key in PHASE_PROCESS_MAPPING.get(phase_key, []):
        score = process_scores.get(process_key, 0)
        process_display_name = format_process_name(process_key)
        state_key = f"show_kpis_{phase_key}_{process_key}"
        button_label = "Hide KPIs" if st.session_state.get(state_key, False) else "Show KPIs"

        process_header_col, _ = st.columns([0.34, 0.66])
        with process_header_col:
            name_col, btn_col = st.columns([0.62, 0.38])
            with name_col:
                st.markdown(f"<span style='font-size: 1.5rem;'><strong>{process_display_name}</strong></span>", unsafe_allow_html=True)
            with btn_col:
                st.button(button_label, key=f"btn_{state_key}", on_click=lambda s_key=state_key: st.session_state.update({s_key: not st.session_state.get(s_key, False)}), use_container_width=False, type="primary")

        st.markdown(horizontal_risk_bar_html(score, width_percentage=100, height='1.65rem', font_size='1.2rem', top_offset='-1.8rem'), unsafe_allow_html=True)
        if st.session_state.get(state_key, False):
            display_kpi_table(kpis_df[kpis_df['process_name'] == process_key])

def display_scoreboard(summary_for_impact_calc, data):
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
    if sort_col_key not in st.session_state:
        st.session_state[sort_col_key] = 'CR-Score'
    if sort_dir_key not in st.session_state:
        st.session_state[sort_dir_key] = 'desc'

    def toggle_sort(column_name):
        current_col = st.session_state[sort_col_key]
        current_dir = st.session_state[sort_dir_key]
        if current_col == column_name:
            st.session_state[sort_dir_key] = 'asc' if current_dir == 'desc' else 'desc'
        else:
            st.session_state[sort_col_key] = column_name
            st.session_state[sort_dir_key] = 'desc'

    sort_column = st.session_state[sort_col_key]
    sort_ascending = st.session_state[sort_dir_key] == 'asc'
    scoreboard_df = scoreboard_df.sort_values(by=sort_column, ascending=sort_ascending, na_position='last').reset_index(drop=True)

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

    st.markdown(f"<h3 style='text-align: center; margin-bottom: 1rem; font-size: 1.56rem;'>Portfolio Segmented by {segment_by}</h3>", unsafe_allow_html=True)

    with st.container(border=True):
        header_cols = st.columns([0.20, 0.22, 0.20, 0.19, 0.19])
        header_cols[0].markdown(f"<span style='font-size: 1.5rem;'><strong>{segment_by}</strong></span>", unsafe_allow_html=True)
        with header_cols[1]:
            st.button(sort_label('CR-Score', 'CR-Score'), key='sort_cr_score', on_click=lambda: toggle_sort('CR-Score'), use_container_width=True, type='primary')
        with header_cols[2]:
            st.button(sort_label('Estimated Project Value', 'Estimated Project Value'), key='sort_est_value', on_click=lambda: toggle_sort('Estimated Project Value'), use_container_width=True, type='primary')
        with header_cols[3]:
            st.button(sort_label('Est Proj Start Date', 'Est Proj Start Date'), key='sort_est_start', on_click=lambda: toggle_sort('Est Proj Start Date'), use_container_width=True, type='primary')
        with header_cols[4]:
            st.button(sort_label('Est Proj End Date', 'Est Proj End Date'), key='sort_est_end', on_click=lambda: toggle_sort('Est Proj End Date'), use_container_width=True, type='primary')

        for _, row in scoreboard_df.iterrows():
            row_cols = st.columns([0.20, 0.22, 0.20, 0.19, 0.19])
            row_cols[0].markdown(f"<span style='font-size: 1.5rem;'><strong>{html.escape(str(row['Segment']))}</strong></span>", unsafe_allow_html=True)
            row_cols[1].markdown(horizontal_risk_bar_html(row['CR-Score'], height='1.45rem', font_size='1.1rem', top_offset='-1.5rem', width_percentage=92), unsafe_allow_html=True)
            row_cols[2].markdown(f"<div style='text-align:right; font-size: 1.5rem;'>{format_currency(row['Estimated Project Value'])}</div>", unsafe_allow_html=True)
            row_cols[3].markdown(f"<div style='text-align:center; font-size: 1.5rem;'>{format_date(row['Est Proj Start Date'])}</div>", unsafe_allow_html=True)
            row_cols[4].markdown(f"<div style='text-align:center; font-size: 1.5rem;'>{format_date(row['Est Proj End Date'])}</div>", unsafe_allow_html=True)

# --- Main Application ---
def main():
    original_data = load_data()
    if not original_data: st.stop()

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
    
    nav_options = ["Executive Summary", "Scoreboard", "Bidding", "Preconstruction", "Construction", "Closeout"]
    page_selection = st.sidebar.radio("Page Navigation", nav_options, label_visibility="collapsed")

    if page_selection == "Executive Summary":
        display_executive_summary(filtered_data, summary_for_impact_calc, filters['impact_category'])
    elif page_selection == "Scoreboard":
        display_scoreboard(summary_for_impact_calc, original_data)
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