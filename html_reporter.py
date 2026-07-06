"""
html_reporter.py
----------------
Generates a self-contained, professional HTML report from the analysis output.

The report contains:
- Header with company name and analysis summary
- Per-quarter analysis cards
- Cross-quarter deviation tracker
- Management tone timeline
- Risks summary
"""

import json
from pathlib import Path
from datetime import datetime


# ── Tone color helpers ─────────────────────────────────────────────────────

def tone_color(tone: str) -> str:
    return {
        "positive": "#16a34a",
        "neutral": "#ca8a04",
        "negative": "#dc2626",
        "mixed": "#7c3aed",
    }.get(tone.lower() if tone else "", "#6b7280")


def tone_bg(tone: str) -> str:
    return {
        "positive": "#dcfce7",
        "neutral": "#fef9c3",
        "negative": "#fee2e2",
        "mixed": "#ede9fe",
    }.get(tone.lower() if tone else "", "#f3f4f6")


def outcome_badge(outcome: str) -> str:
    styles = {
        "delivered": ("✅ Delivered", "#dcfce7", "#15803d"),
        "partially_delivered": ("⚠️ Partial", "#fef9c3", "#92400e"),
        "not_delivered": ("❌ Not Delivered", "#fee2e2", "#991b1b"),
        "too_early_to_tell": ("⏳ Too Early", "#dbeafe", "#1d4ed8"),
    }
    label, bg, fg = styles.get(outcome, ("❓ Unknown", "#f3f4f6", "#374151"))
    return f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:4px;font-size:0.75rem;font-weight:600">{label}</span>'


def severity_badge(severity: str) -> str:
    styles = {
        "high": ("#fee2e2", "#991b1b"),
        "medium": ("#fef9c3", "#92400e"),
        "low": ("#dcfce7", "#15803d"),
    }
    bg, fg = styles.get(severity.lower() if severity else "medium", ("#f3f4f6", "#374151"))
    return f'<span style="background:{bg};color:{fg};padding:1px 6px;border-radius:3px;font-size:0.7rem;font-weight:600;text-transform:uppercase">{severity or "?"}</span>'


def trend_icon(trend: str) -> str:
    return {
        "improving": "📈",
        "deteriorating": "📉",
        "stable": "➡️",
        "mixed": "↕️",
    }.get(trend.lower() if trend else "", "❓")


# ── Quarter card builder ───────────────────────────────────────────────────

def render_quarter_card(q: dict, idx: int) -> str:
    quarter = q.get("quarter", f"Quarter {idx+1}")
    tone = q.get("management_tone", {})
    tone_val = tone.get("overall", "neutral")
    score = tone.get("score", 5)
    triggers = q.get("earnings_triggers", [])
    changes = q.get("business_changes", [])
    risks = q.get("risks_and_issues", [])
    commitments = q.get("commitments_made", [])
    metrics = q.get("key_metrics_mentioned", {})
    summary = q.get("summary", "")
    error = q.get("_error", "")

    # Metrics bar
    metrics_html = ""
    metric_items = [
        ("Revenue Growth", metrics.get("revenue_growth")),
        ("Margin", metrics.get("margin")),
        ("Order Book", metrics.get("order_book")),
        ("Guidance", metrics.get("guidance")),
    ]
    metric_parts = []
    for label, val in metric_items:
        if val:
            metric_parts.append(
                f'<div class="metric-chip"><span class="metric-label">{label}</span>'
                f'<span class="metric-val">{val}</span></div>'
            )
    if metric_parts:
        metrics_html = f'<div class="metrics-row">{"".join(metric_parts)}</div>'

    # Triggers
    triggers_html = ""
    if triggers:
        items = ""
        for t in triggers:
            conf_color = {"high": "#15803d", "medium": "#ca8a04", "low": "#6b7280"}.get(
                (t.get("confidence") or "medium").lower(), "#6b7280"
            )
            items += (
                f'<li class="trigger-item">'
                f'<span class="trigger-bullet" style="color:{conf_color}">▶</span>'
                f'<div><strong>{t.get("trigger","")}</strong>'
                f'<span class="trigger-detail"> — {t.get("detail","")}</span></div>'
                f'</li>'
            )
        triggers_html = f'<ul class="item-list">{items}</ul>'
    else:
        triggers_html = '<p class="empty-note">No specific triggers identified.</p>'

    # Changes
    changes_html = ""
    if changes:
        items = ""
        for c in changes:
            sig = c.get("significance", "minor")
            icon = "🔴" if sig == "major" else "🔵"
            items += (
                f'<li class="change-item">'
                f'<span class="change-type">{icon} {c.get("change_type","other").upper()}</span>'
                f'<span>{c.get("description","")}</span>'
                f'</li>'
            )
        changes_html = f'<ul class="item-list">{items}</ul>'
    else:
        changes_html = '<p class="empty-note">No significant business changes reported.</p>'

    # Risks
    risks_html = ""
    if risks:
        items = ""
        for r in risks:
            items += (
                f'<li class="risk-item">'
                f'{severity_badge(r.get("severity","medium"))}'
                f'<div><strong>{r.get("risk","")}</strong>'
                f'<span class="risk-detail"> — {r.get("detail","")}</span>'
                f'<span class="risk-cat"> [{r.get("category","")}]</span></div>'
                f'</li>'
            )
        risks_html = f'<ul class="item-list">{items}</ul>'
    else:
        risks_html = '<p class="empty-note">No significant risks highlighted.</p>'

    # Commitments
    commitments_html = ""
    if commitments:
        items = ""
        for c in commitments:
            metric_str = f' <em>({c.get("metric","")})</em>' if c.get("metric") else ""
            tf_str = f' <span class="timeframe">— {c.get("timeframe","")}</span>' if c.get("timeframe") else ""
            items += f'<li>📌 {c.get("commitment","")}{metric_str}{tf_str}</li>'
        commitments_html = f'<ul class="commit-list">{items}</ul>'
    else:
        commitments_html = '<p class="empty-note">No specific commitments recorded.</p>'

    error_banner = ""
    if error:
        error_banner = f'<div class="error-banner">⚠️ {error}</div>'

    tone_score_bar = f"""
    <div class="tone-score-bar">
      <span class="tone-label">Tone Score</span>
      <div class="score-track">
        <div class="score-fill" style="width:{score*10}%;background:{tone_color(tone_val)}"></div>
      </div>
      <span class="score-num">{score}/10</span>
    </div>
    """

    return f"""
<div class="quarter-card" id="q{idx+1}">
  <div class="card-header" style="background:{tone_bg(tone_val)};border-left:4px solid {tone_color(tone_val)}">
    <div class="card-header-left">
      <span class="quarter-badge">Q{idx+1}</span>
      <h2 class="quarter-title">{quarter}</h2>
    </div>
    <div class="card-header-right">
      <span class="tone-pill" style="background:{tone_color(tone_val)};color:white">
        {tone_val.upper()}
      </span>
    </div>
  </div>

  {error_banner}
  {metrics_html}

  <div class="card-body">
    {f'<p class="summary-text">{summary}</p>' if summary else ''}
    {tone_score_bar}

    <div class="section-grid">
      <div class="section-block">
        <h3 class="section-title">🚀 Earnings Triggers</h3>
        {triggers_html}
      </div>

      <div class="section-block">
        <h3 class="section-title">🔄 Business Changes</h3>
        {changes_html}
      </div>

      <div class="section-block">
        <h3 class="section-title">⚠️ Risks & Issues</h3>
        {risks_html}
      </div>

      <div class="section-block">
        <h3 class="section-title">📋 Commitments Made</h3>
        {commitments_html}
      </div>
    </div>

    <div class="tone-detail">
      <strong>Tone Reasoning:</strong> {tone.get("reasoning", "")}
      {f'<div class="key-phrases">Key phrases: ' + ' · '.join(f'<em>"{p}"</em>' for p in tone.get("key_phrases", [])) + '</div>' if tone.get("key_phrases") else ''}
    </div>
  </div>
</div>
"""


# ── Deviation section ──────────────────────────────────────────────────────

def render_deviation_section(dev: dict) -> str:
    deviations = dev.get("deviations", [])
    narrative_shifts = dev.get("narrative_shifts", [])
    recurring_themes = dev.get("recurring_themes", [])
    credibility_score = dev.get("management_credibility_score")
    credibility_reasoning = dev.get("credibility_reasoning", "")
    overall_trend = dev.get("overall_trend", "")
    analyst_view = dev.get("analyst_view", "")

    # Deviation table
    dev_rows = ""
    for d in deviations:
        dev_rows += f"""
        <tr>
          <td class="td-quarter">{d.get("commitment_quarter","")}</td>
          <td>{d.get("commitment","")}</td>
          <td class="td-quarter">{d.get("check_quarter","")}</td>
          <td>{outcome_badge(d.get("outcome",""))}</td>
          <td>{d.get("detail","")}</td>
          <td>{severity_badge(d.get("severity",""))}</td>
        </tr>"""

    dev_table = f"""
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Promised In</th>
            <th>Commitment</th>
            <th>Checked In</th>
            <th>Outcome</th>
            <th>Details</th>
            <th>Severity</th>
          </tr>
        </thead>
        <tbody>
          {dev_rows if dev_rows else '<tr><td colspan="6" class="empty-td">No deviations identified across quarters.</td></tr>'}
        </tbody>
      </table>
    </div>"""

    # Narrative shifts
    shifts_html = ""
    if narrative_shifts:
        items = ""
        for s in narrative_shifts:
            quarters = ", ".join(s.get("quarters_involved", []))
            items += f"""
            <div class="shift-item">
              <span class="shift-topic">{s.get("topic","")}</span>
              <span class="shift-qtrs">({quarters})</span>
              <p>{s.get("shift_description","")}</p>
            </div>"""
        shifts_html = f'<div class="shifts-wrap">{items}</div>'
    else:
        shifts_html = '<p class="empty-note">No significant narrative shifts detected.</p>'

    # Recurring themes
    themes_html = ""
    if recurring_themes:
        items = ""
        for t in recurring_themes:
            quarters = ", ".join(t.get("quarters", []))
            items += f"""
            <div class="theme-item">
              {trend_icon(t.get("trend",""))}
              <div>
                <strong>{t.get("theme","")}</strong>
                <span class="theme-trend"> — {t.get("trend","").upper()}</span>
                <span class="theme-qtrs"> ({quarters})</span>
              </div>
            </div>"""
        themes_html = f'<div class="themes-wrap">{items}</div>'
    else:
        themes_html = '<p class="empty-note">No recurring themes identified.</p>'

    # Credibility score gauge
    cred_html = ""
    if credibility_score is not None:
        cred_color = "#16a34a" if credibility_score >= 7 else "#ca8a04" if credibility_score >= 4 else "#dc2626"
        cred_html = f"""
        <div class="cred-gauge">
          <div class="cred-circle" style="border-color:{cred_color}">
            <span class="cred-num" style="color:{cred_color}">{credibility_score}</span>
            <span class="cred-denom">/10</span>
          </div>
          <div class="cred-label">Management<br>Credibility</div>
        </div>"""

    return f"""
<div class="deviation-section">
  <h2 class="section-main-title">🔍 Cross-Quarter Intelligence</h2>

  <div class="cred-banner">
    {cred_html}
    <div class="cred-text">
      <h3>Overall Trend: {trend_icon(overall_trend)} {overall_trend.upper()}</h3>
      <p>{credibility_reasoning}</p>
    </div>
  </div>

  <div class="analyst-view">
    <h3>📊 Analyst Synthesis</h3>
    <p>{analyst_view}</p>
  </div>

  <h3 class="sub-section-title">📉 Commitment Deviation Tracker</h3>
  {dev_table}

  <div class="two-col">
    <div>
      <h3 class="sub-section-title">🔄 Narrative Shifts</h3>
      {shifts_html}
    </div>
    <div>
      <h3 class="sub-section-title">🔁 Recurring Themes</h3>
      {themes_html}
    </div>
  </div>
</div>
"""


# ── Tone timeline ──────────────────────────────────────────────────────────

def render_tone_timeline(quarterly: list) -> str:
    if not quarterly:
        return ""
    items = ""
    for i, q in enumerate(quarterly):
        tone = q.get("management_tone", {})
        tone_val = tone.get("overall", "neutral")
        score = tone.get("score", 5)
        quarter = q.get("quarter", f"Q{i+1}")
        items += f"""
        <div class="timeline-item">
          <div class="tl-bar-wrap">
            <div class="tl-bar" style="height:{score*8}px;background:{tone_color(tone_val)}"
                 title="{quarter}: {tone_val} ({score}/10)"></div>
          </div>
          <div class="tl-label">{quarter.replace("FY","<br>FY")}</div>
          <div class="tl-score" style="color:{tone_color(tone_val)}">{score}/10</div>
        </div>"""

    return f"""
<div class="timeline-section">
  <h3 class="sub-section-title">📊 Management Tone Timeline</h3>
  <div class="timeline-bars">{items}</div>
  <div class="timeline-legend">
    <span style="color:#16a34a">● Positive</span>
    <span style="color:#ca8a04">● Neutral</span>
    <span style="color:#dc2626">● Negative</span>
    <span style="color:#7c3aed">● Mixed</span>
  </div>
</div>
"""


# ── Full HTML page ─────────────────────────────────────────────────────────

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
       background: #f0f4f8; color: #1e293b; line-height: 1.6; }
.page-wrap { max-width: 1200px; margin: 0 auto; padding: 24px 16px 60px; }

/* Header */
.page-header { background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 100%);
               color: white; padding: 32px; border-radius: 12px; margin-bottom: 32px; }
.page-header h1 { font-size: 2rem; font-weight: 700; }
.page-header .subtitle { opacity: 0.8; margin-top: 6px; font-size: 0.95rem; }
.header-meta { display: flex; gap: 24px; margin-top: 16px; flex-wrap: wrap; }
.meta-chip { background: rgba(255,255,255,0.15); padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; }

/* Nav */
.nav-tabs { display: flex; gap: 8px; margin-bottom: 24px; flex-wrap: wrap; }
.nav-tab { background: white; border: 1px solid #e2e8f0; padding: 8px 18px;
           border-radius: 20px; cursor: pointer; font-size: 0.85rem; font-weight: 500;
           color: #475569; text-decoration: none; transition: all 0.2s; }
.nav-tab:hover { background: #2563eb; color: white; border-color: #2563eb; }

/* Quarter cards */
.quarter-card { background: white; border-radius: 12px; margin-bottom: 28px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08); overflow: hidden; }
.card-header { display: flex; justify-content: space-between; align-items: center;
               padding: 16px 24px; }
.card-header-left { display: flex; align-items: center; gap: 12px; }
.quarter-badge { background: #1e3a5f; color: white; width: 36px; height: 36px;
                 border-radius: 50%; display: flex; align-items: center; justify-content: center;
                 font-weight: 700; font-size: 0.9rem; flex-shrink: 0; }
.quarter-title { font-size: 1.2rem; font-weight: 700; color: #1e293b; }
.tone-pill { padding: 4px 14px; border-radius: 20px; font-size: 0.8rem; font-weight: 700;
             letter-spacing: 0.05em; }
.card-body { padding: 20px 24px; }
.summary-text { color: #475569; font-size: 0.95rem; margin-bottom: 16px;
                padding: 12px; background: #f8fafc; border-radius: 8px; border-left: 3px solid #94a3b8; }

/* Metrics */
.metrics-row { display: flex; gap: 12px; padding: 12px 24px; background: #f8fafc;
               border-top: 1px solid #e2e8f0; flex-wrap: wrap; }
.metric-chip { background: white; border: 1px solid #e2e8f0; padding: 6px 12px;
               border-radius: 6px; font-size: 0.8rem; }
.metric-label { color: #64748b; font-weight: 500; margin-right: 6px; }
.metric-val { color: #1e293b; font-weight: 700; }

/* Tone score bar */
.tone-score-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.tone-label { font-size: 0.8rem; color: #64748b; width: 80px; flex-shrink: 0; }
.score-track { flex: 1; height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; }
.score-fill { height: 100%; border-radius: 4px; transition: width 0.5s; }
.score-num { font-size: 0.85rem; font-weight: 700; color: #475569; width: 40px; text-align: right; }

/* Section grid */
.section-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 16px; }
@media (max-width: 768px) { .section-grid { grid-template-columns: 1fr; } }
.section-block { background: #f8fafc; border-radius: 8px; padding: 16px; }
.section-title { font-size: 0.9rem; font-weight: 700; color: #1e293b; margin-bottom: 12px;
                 padding-bottom: 8px; border-bottom: 1px solid #e2e8f0; }

/* Lists */
.item-list { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.trigger-item { display: flex; gap: 8px; font-size: 0.875rem; }
.trigger-bullet { flex-shrink: 0; margin-top: 2px; }
.trigger-detail { color: #64748b; }
.change-item { display: flex; flex-direction: column; gap: 3px; font-size: 0.875rem;
               padding: 6px 0; border-bottom: 1px solid #e2e8f0; }
.change-item:last-child { border-bottom: none; }
.change-type { font-size: 0.7rem; font-weight: 700; color: #64748b; }
.risk-item { display: flex; gap: 8px; align-items: flex-start; font-size: 0.875rem;
             padding: 6px 0; border-bottom: 1px solid #e2e8f0; }
.risk-item:last-child { border-bottom: none; }
.risk-detail { color: #64748b; }
.risk-cat { color: #94a3b8; font-size: 0.75rem; }
.commit-list { list-style: none; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.commit-list li { font-size: 0.875rem; padding: 6px 0; border-bottom: 1px solid #e2e8f0; }
.commit-list li:last-child { border-bottom: none; }
.timeframe { color: #64748b; font-size: 0.8rem; }

/* Tone detail */
.tone-detail { background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 8px;
               padding: 12px 16px; font-size: 0.875rem; color: #0c4a6e; }
.key-phrases { margin-top: 6px; color: #0369a1; }
.empty-note { color: #94a3b8; font-size: 0.85rem; font-style: italic; }
.error-banner { background: #fee2e2; color: #991b1b; padding: 10px 24px; font-size: 0.85rem; }

/* Deviation section */
.deviation-section { background: white; border-radius: 12px; padding: 28px;
                     box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 28px; }
.section-main-title { font-size: 1.4rem; font-weight: 700; margin-bottom: 20px; color: #1e293b; }
.sub-section-title { font-size: 1rem; font-weight: 700; color: #1e293b; margin: 20px 0 12px; }

/* Credibility */
.cred-banner { display: flex; align-items: center; gap: 24px; background: #f8fafc;
               border-radius: 10px; padding: 20px; margin-bottom: 24px; }
.cred-gauge { display: flex; flex-direction: column; align-items: center; gap: 6px; flex-shrink: 0; }
.cred-circle { width: 72px; height: 72px; border: 4px solid; border-radius: 50%;
               display: flex; flex-direction: column; align-items: center; justify-content: center; }
.cred-num { font-size: 1.4rem; font-weight: 800; line-height: 1; }
.cred-denom { font-size: 0.7rem; color: #64748b; }
.cred-label { font-size: 0.75rem; color: #64748b; text-align: center; font-weight: 600; }
.cred-text h3 { font-size: 1rem; font-weight: 700; color: #1e293b; margin-bottom: 8px; }
.cred-text p { font-size: 0.9rem; color: #475569; }

/* Analyst view */
.analyst-view { background: linear-gradient(135deg, #1e3a5f10, #2563eb10);
                border: 1px solid #2563eb30; border-radius: 8px; padding: 16px;
                margin-bottom: 20px; }
.analyst-view h3 { font-size: 0.95rem; font-weight: 700; margin-bottom: 8px; color: #1e3a5f; }
.analyst-view p { font-size: 0.9rem; color: #334155; }

/* Table */
.table-wrap { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.data-table th { background: #1e3a5f; color: white; padding: 10px 12px; text-align: left; font-weight: 600; }
.data-table td { padding: 10px 12px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
.data-table tr:nth-child(even) { background: #f8fafc; }
.td-quarter { font-weight: 600; color: #1e3a5f; white-space: nowrap; }
.empty-td { text-align: center; color: #94a3b8; font-style: italic; padding: 20px; }

/* Two col */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 8px; }
@media (max-width: 768px) { .two-col { grid-template-columns: 1fr; } }

/* Shifts & themes */
.shifts-wrap, .themes-wrap { display: flex; flex-direction: column; gap: 12px; }
.shift-item { background: #f8fafc; border-radius: 8px; padding: 12px; font-size: 0.875rem; }
.shift-topic { font-weight: 700; color: #1e293b; }
.shift-qtrs { color: #64748b; font-size: 0.8rem; margin-left: 6px; }
.shift-item p { color: #475569; margin-top: 4px; }
.theme-item { display: flex; align-items: flex-start; gap: 10px; padding: 10px;
              background: #f8fafc; border-radius: 8px; font-size: 0.875rem; }
.theme-trend { color: #64748b; font-size: 0.8rem; }
.theme-qtrs { color: #94a3b8; font-size: 0.75rem; }

/* Timeline */
.timeline-section { background: white; border-radius: 12px; padding: 24px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 28px; }
.timeline-bars { display: flex; align-items: flex-end; gap: 16px; height: 100px;
                 padding: 0 12px; }
.timeline-item { display: flex; flex-direction: column; align-items: center; gap: 4px; flex: 1; min-width: 60px; }
.tl-bar-wrap { height: 80px; display: flex; align-items: flex-end; }
.tl-bar { width: 40px; border-radius: 4px 4px 0 0; min-height: 8px; transition: height 0.4s; }
.tl-label { font-size: 0.7rem; color: #64748b; text-align: center; font-weight: 500; }
.tl-score { font-size: 0.75rem; font-weight: 700; }
.timeline-legend { display: flex; gap: 16px; margin-top: 12px; font-size: 0.8rem;
                   padding-top: 8px; border-top: 1px solid #e2e8f0; flex-wrap: wrap; }

/* Footer */
.report-footer { text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 40px;
                 padding-top: 20px; border-top: 1px solid #e2e8f0; }
"""


def generate_html(analysis: dict, company_name: str, output_path: Path) -> Path:
    """
    Generate the full HTML report.
    analysis: output from llm_analyser.run_full_analysis()
    """
    quarterly = analysis.get("quarterly_analyses", [])
    deviation = analysis.get("deviation_analysis", {})
    n = analysis.get("quarters_analysed", len(quarterly))
    now = datetime.now().strftime("%d %B %Y, %I:%M %p")

    # Build nav tabs
    nav = ""
    for i, q in enumerate(quarterly):
        quarter = q.get("quarter", f"Q{i+1}")
        nav += f'<a class="nav-tab" href="#q{i+1}">{quarter}</a>'
    nav += '<a class="nav-tab" href="#cross-quarter">Cross-Quarter</a>'

    # Build quarter cards
    cards = "".join(render_quarter_card(q, i) for i, q in enumerate(quarterly))

    # Tone timeline
    timeline = render_tone_timeline(quarterly)

    # Deviation
    deviation_section = f'<div id="cross-quarter">{render_deviation_section(deviation)}</div>'

    # Overall tone summary
    tones = [q.get("management_tone", {}).get("overall", "neutral") for q in quarterly]
    tone_counts = {t: tones.count(t) for t in set(tones)}
    tone_summary = " | ".join(f"{k.title()}: {v}" for k, v in sorted(tone_counts.items()))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{company_name} — ConcAll Analysis Report</title>
  <style>{CSS}</style>
</head>
<body>
<div class="page-wrap">

  <div class="page-header">
    <h1>📞 {company_name}</h1>
    <div class="subtitle">Earnings Call Intelligence Report</div>
    <div class="header-meta">
      <span class="meta-chip">📅 Generated: {now}</span>
      <span class="meta-chip">📊 Quarters Analysed: {n}</span>
      <span class="meta-chip">🎙 Tone: {tone_summary}</span>
    </div>
  </div>

  <nav class="nav-tabs">{nav}</nav>

  {timeline}

  {cards}

  {deviation_section}

  <div class="report-footer">
    Generated by ConcAll Analyser · Powered by Claude AI · {now}<br>
    <em>This report is for informational purposes only and does not constitute investment advice.</em>
  </div>

</div>
</body>
</html>"""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return output_path