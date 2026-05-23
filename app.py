import streamlit as st
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from supabase import create_client

# ======================================================
# Page setup
# ======================================================
st.set_page_config(page_title="Andon Dashboard", layout="wide")

# ======================================================
# Supabase (server-side)
# ======================================================
@st.cache_resource
def get_sb():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)

sb = get_sb()

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def to_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        # assume local -> convert to UTC
        return dt.replace(tzinfo=timezone.utc).isoformat()
    return dt.astimezone(timezone.utc).isoformat()

def parse_dt(v: Optional[str]) -> Optional[datetime]:
    if not v:
        return None
    # Supabase returns ISO strings
    try:
        # handle "Z"
        if isinstance(v, str) and v.endswith("Z"):
            v = v[:-1] + "+00:00"
        return datetime.fromisoformat(v)
    except Exception:
        return None

# ======================================================
# Styles (clean + neutral)
# ======================================================
st.markdown(
    """
<style>
:root{
  --bg:#f6f7fb;
  --card:#ffffff;
  --border:#e6e8ef;
  --text:#111827;
  --muted:#6b7280;
  --blue:#2563eb;
  --green:#16a34a;
  --yellow:#f59e0b;
  --red:#dc2626;
  --shadow: 0 1px 0 rgba(16,24,40,.04), 0 8px 20px rgba(16,24,40,.06);
}
html, body, [data-testid="stAppViewContainer"]{ background: var(--bg); }
.block-container{
  padding-top: 6rem !important;
  padding-left: 1.2rem;
  padding-right: 1.2rem;
}
[data-testid="stAppViewContainer"]{ scroll-padding-top: 6rem; }

.header-left{ display:flex; align-items:center; gap: 12px; min-width: 260px; }
.h-title{ font-weight: 850; letter-spacing: -0.02em; font-size: 1.55rem; color: var(--text); margin: 0; }
.h-sub{ color: var(--muted); font-size: .92rem; margin-top: -2px; }

.badge{
  display:flex; align-items:center; gap:10px; padding: 10px 12px;
  border-radius: 10px; border: 1px solid var(--border); background: #fff; font-weight: 750;
}
.badge.badge-red{ background: rgba(220,38,38,.08); border-color: rgba(220,38,38,.25); color: var(--red); }
.badge.badge-yellow{ background: rgba(245,158,11,.10); border-color: rgba(245,158,11,.25); color: #92400e; }
.badge.badge-green{ background: rgba(22,163,74,.10); border-color: rgba(22,163,74,.22); color: var(--green); }

.dot{ width: 10px; height: 10px; border-radius: 999px; display:inline-block; }
.dot.green{ background: var(--green); }
.dot.yellow{ background: var(--yellow); }
.dot.red{ background: var(--red); }
.dot.gray{ background: #9ca3af; }

.grid{ display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
@media (max-width: 1100px){ .grid{ grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 700px){ .grid{ grid-template-columns: repeat(1, minmax(0, 1fr)); } }

.card{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; box-shadow: var(--shadow); padding: 14px; }
.card.selected{
  outline: 2px solid rgba(37,99,235,.55);
  border-color: rgba(37,99,235,.25);
  background: linear-gradient(180deg, rgba(37,99,235,.06), rgba(255,255,255,1) 55%);
}
.card h3{ margin: 0 0 6px 0; font-size: 1.03rem; letter-spacing: -0.01em; color: var(--text); }
.small{ color: var(--muted); font-size: .92rem; }
.pills{ display:flex; gap:8px; align-items:center; margin: 10px 0 10px 0; }
.pill{
  display:inline-flex; align-items:center; gap:8px; padding: 6px 10px; border-radius: 999px;
  border: 1px solid var(--border); background: #fff; font-weight: 750; font-size: .88rem;
}
.pill.red{ border-color: rgba(220,38,38,.25); background: rgba(220,38,38,.06); color: var(--red); }
.pill.yellow{ border-color: rgba(245,158,11,.25); background: rgba(245,158,11,.08); color: #92400e; }
.pill.green{ border-color: rgba(22,163,74,.22); background: rgba(22,163,74,.08); color: var(--green); }

.panel-title{ font-weight: 850; font-size: 1.06rem; margin-bottom: 6px; }
div.stButton > button{ border-radius: 10px !important; font-weight: 800 !important; padding: .62rem 1rem !important; }

.op-phys-wrap{
  display:flex;
  flex-direction:column;
  gap:14px;
  align-items:flex-start;
  margin: 6px 0 10px 0;
}
div.stButton > button.op-phys{
  width: 86px !important;
  height: 86px !important;
  padding: 0 !important;
  border-radius: 999px !important;
  border: 1px solid rgba(17,24,39,.14) !important;
  box-shadow: 0 10px 18px rgba(16,24,40,.08) !important;
  font-weight: 900 !important;
}
div.stButton > button.op-red{ background: #ef4444 !important; color: rgba(0,0,0,0) !important; }
div.stButton > button.op-yellow{ background: #f59e0b !important; color: rgba(0,0,0,0) !important; }
div.stButton > button.op-green{ background: #22c55e !important; color: rgba(0,0,0,0) !important; }
div.stButton > button.op-white{ background: #ffffff !important; color: #111827 !important; }
div.stButton > button.op-phys:active{
  transform: translateY(1px);
  box-shadow: 0 6px 14px rgba(16,24,40,.10) !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ======================================================
# Constants / Roles
# ======================================================
ROLE_OPTIONS = ["OP_A_S1", "OP_B_S2", "OP_C_S4", "MAINTENANCE", "ADMIN", "LM_A", "LM_B", "LM_C"]
LINE_OPTIONS = ["Line A", "Line B", "Line C"]

SEVERITY_GREEN = "GREEN"
SEVERITY_YELLOW = "YELLOW"
SEVERITY_RED = "RED"
SEVERITY_INFO = "INFO"

EVENT_OPEN = "OPEN"
EVENT_ACK = "ACKED"
EVENT_CLOSED = "CLOSED"

SOURCE_PHYSICAL = "PHYSICAL_BUTTON_SIM"
SOURCE_INFO = "INFO"

OP_ROLES = ("OP_A_S1", "OP_B_S2", "OP_C_S4")
MAINT_ADMIN_ROLES = ("MAINTENANCE", "ADMIN")

# ======================================================
# Names (Portugal NT — from your provided list)
# ======================================================
ROLE_NAMES = {
    "OP_A_S1": ["Cristiano Ronaldo", "Bruno Fernandes", "Bernardo Silva"],
    "OP_B_S2": ["Rúben Dias", "Diogo Dalot", "Nuno Mendes"],
    "OP_C_S4": ["Rafael Leão", "João Félix", "Vitinha"],
    "MAINTENANCE": ["Diogo Costa", "José Sá", "Rui Silva", "Nélson Semedo", "João Cancelo"],
    "ADMIN": ["Rúben Neves", "Matheus Nunes"],
    "LM_A": ["Gonçalo Inácio", "Renato Veiga"],
    "LM_B": ["Tomás Araújo", "Samuel Costa", "João Neves"],
    "LM_C": ["Trincão", "Francisco Conceição", "Pedro Neto", "Gonçalo Guedes", "Gonçalo Ramos"],
}

# ======================================================
# Domain model
# ======================================================
@dataclass
class Event:
    id: str
    line: str
    station: int
    severity: str
    status: str

    source: str
    source_station: int
    opened_by_user: str
    opened_by_name: str
    part_serial: str

    created_at: datetime
    ack_by: Optional[str] = None
    ack_by_name: Optional[str] = None
    ack_at: Optional[datetime] = None
    closed_by: Optional[str] = None
    closed_by_name: Optional[str] = None
    closed_at: Optional[datetime] = None

    failure_text: Optional[str] = None
    note: Optional[str] = None
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    assigned_at: Optional[datetime] = None


@dataclass
class PartFailureRecord:
    event_id: str
    part_serial: str
    failure_text: str
    operator_name: str
    opened_by_user: str
    line: str
    station: int
    severity: str
    created_at: datetime
    closed_at: datetime
    closed_by: str
    closed_by_name: str


def now() -> datetime:
    # keep your UI "local-ish"; DB stores ISO UTC
    return datetime.now()

def age_str(dt: datetime) -> str:
    delta = now() - dt.replace(tzinfo=None)
    mins = int(delta.total_seconds() // 60)
    if mins < 1:
        return "just now"
    if mins == 1:
        return "1 min"
    return f"{mins} min"

def severity_label(sev: str) -> str:
    return {"GREEN": "Running", "YELLOW": "Warning", "RED": "Stopped", "INFO": "Info"}.get(sev, sev)

def severity_css(sev: str) -> str:
    return {"GREEN": "green", "YELLOW": "yellow", "RED": "red", "INFO": "gray"}.get(sev, "gray")

def default_username_for(role: str, chosen_name: str) -> str:
    slug = "".join(ch for ch in chosen_name.lower() if ch.isalnum() or ch in (" ", "_", "-")).strip().replace(" ", "_")
    return f"demo_{role.lower()}_{slug}" if chosen_name else f"demo_{role.lower()}"

# ======================================================
# Supabase mapping helpers
# ======================================================
SB_TABLE = "andon_events_v2"

def event_to_row(e: Event) -> Dict[str, Any]:
    return {
        "id": e.id,
        "created_at": to_iso(e.created_at),
        "line": e.line,
        "station": int(e.station),
        "severity": e.severity,
        "status": e.status,
        "source": e.source,
        "source_station": int(e.source_station),
        "opened_by_user": e.opened_by_user,
        "opened_by_name": e.opened_by_name,
        "part_serial": e.part_serial or "",
        "ack_by": e.ack_by,
        "ack_by_name": e.ack_by_name,
        "ack_at": to_iso(e.ack_at),
        "closed_by": e.closed_by,
        "closed_by_name": e.closed_by_name,
        "closed_at": to_iso(e.closed_at),
        "failure_text": e.failure_text,
        "note": e.note,
        "assigned_to": e.assigned_to,
        "assigned_to_name": e.assigned_to_name,
        "assigned_at": to_iso(e.assigned_at),
    }

def row_to_event(r: Dict[str, Any]) -> Event:
    created_at = parse_dt(r.get("created_at")) or utcnow()
    # show as naive local-ish datetime in UI
    created_at_naive = created_at.replace(tzinfo=None)

    return Event(
        id=r["id"],
        line=r["line"],
        station=int(r["station"]),
        severity=r["severity"],
        status=r["status"],
        source=r["source"],
        source_station=int(r.get("source_station") or r["station"]),
        opened_by_user=r["opened_by_user"],
        opened_by_name=r["opened_by_name"],
        part_serial=r.get("part_serial") or "",
        created_at=created_at_naive,
        ack_by=r.get("ack_by"),
        ack_by_name=r.get("ack_by_name"),
        ack_at=(parse_dt(r.get("ack_at")) or None),
        closed_by=r.get("closed_by"),
        closed_by_name=r.get("closed_by_name"),
        closed_at=(parse_dt(r.get("closed_at")) or None),
        failure_text=r.get("failure_text"),
        note=r.get("note"),
        assigned_to=r.get("assigned_to"),
        assigned_to_name=r.get("assigned_to_name"),
        assigned_at=(parse_dt(r.get("assigned_at")) or None),
    )

def sb_list_events(lines: List[str]) -> List[Event]:
    if not lines:
        return []
    res = (
        sb.table(SB_TABLE)
        .select("*")
        .in_("line", lines)
        .order("created_at", desc=True)
        .limit(500)
        .execute()
    )
    data = res.data or []
    return [row_to_event(r) for r in data]

def sb_upsert_event(e: Event) -> None:
    sb.table(SB_TABLE).upsert(event_to_row(e)).execute()

def sb_update_event(event_id: str, patch: Dict[str, Any]) -> None:
    # Convert datetime fields to ISO if provided
    for k in ["created_at", "ack_at", "closed_at", "assigned_at"]:
        if k in patch:
            patch[k] = to_iso(patch[k])
    sb.table(SB_TABLE).update(patch).eq("id", event_id).execute()

# ======================================================
# Session initialization
# ======================================================
def seed_if_needed():
    # UI state
    if "selected_line" not in st.session_state:
        st.session_state.selected_line = None
    if "selected_station" not in st.session_state:
        st.session_state.selected_station = None
    if "role" not in st.session_state:
        st.session_state.role = "OP_A_S1"
    if "role_person_name" not in st.session_state:
        st.session_state.role_person_name = {}
    if st.session_state.role not in st.session_state.role_person_name:
        st.session_state.role_person_name[st.session_state.role] = ROLE_NAMES[st.session_state.role][0]
    if "username" not in st.session_state:
        nm = st.session_state.role_person_name.get(st.session_state.role, "")
        st.session_state.username = default_username_for(st.session_state.role, nm)
    if "line_overrides" not in st.session_state:
        st.session_state.line_overrides = {line: None for line in LINE_OPTIONS}
    if "part_failures" not in st.session_state:
        st.session_state.part_failures: List[PartFailureRecord] = []
    if "event_seq" not in st.session_state:
        st.session_state.event_seq = 2000
    if "maint_panel_open" not in st.session_state:
        st.session_state.maint_panel_open = False
    if "maint_selected_line" not in st.session_state:
        st.session_state.maint_selected_line = None
    if "op_docs" not in st.session_state:
        st.session_state.op_docs = []

    # Events: load from Supabase once per run (and on refresh we rerun anyway)
    role = st.session_state.role
    visible = visible_lines_for_user(role)
    st.session_state.events = sb_list_events(visible)

def user_context_for_role(role: str) -> dict:
    if role == "LM_A":
        return {"fixed_line": "Line A", "fixed_station": None}
    if role == "LM_B":
        return {"fixed_line": "Line B", "fixed_station": None}
    if role == "LM_C":
        return {"fixed_line": "Line C", "fixed_station": None}
    if role == "OP_A_S1":
        return {"fixed_line": "Line A", "fixed_station": 1}
    if role == "OP_B_S2":
        return {"fixed_line": "Line B", "fixed_station": 2}
    if role == "OP_C_S4":
        return {"fixed_line": "Line C", "fixed_station": 4}
    return {"fixed_line": None, "fixed_station": None}

def visible_lines_for_user(role: str) -> List[str]:
    ctx = user_context_for_role(role)
    if role in MAINT_ADMIN_ROLES:
        return LINE_OPTIONS
    if ctx["fixed_line"]:
        return [ctx["fixed_line"]]
    return []

seed_if_needed()

# ======================================================
# Access rules
# ======================================================
def can_view_line(role: str, line: str) -> bool:
    return line in visible_lines_for_user(role)

def can_ack(role: str, sev: str) -> bool:
    if sev == SEVERITY_INFO:
        return False
    if role in OP_ROLES:
        return False
    return role in ("MAINTENANCE", "ADMIN", "LM_A", "LM_B", "LM_C")

def can_close_event(role: str, sev: str) -> bool:
    if sev == SEVERITY_INFO:
        return False
    if role in OP_ROLES:
        return False
    if role in MAINT_ADMIN_ROLES:
        return sev in (SEVERITY_YELLOW, SEVERITY_RED)
    if role in ("LM_A", "LM_B", "LM_C"):
        return sev == SEVERITY_YELLOW
    return False

def can_assign(role: str) -> bool:
    return role == "ADMIN"

def can_override(role: str) -> bool:
    return role == "ADMIN"

# ======================================================
# Event helpers
# ======================================================
def get_open_event(line: str, station: int) -> Optional[Event]:
    candidates = [
        e for e in st.session_state.events
        if e.line == line
        and e.station == station
        and e.status != EVENT_CLOSED
        and e.severity in (SEVERITY_GREEN, SEVERITY_YELLOW, SEVERITY_RED)
        and e.status in (EVENT_OPEN, EVENT_ACK)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda e: e.created_at, reverse=True)
    return candidates[0]

def any_open_red_station(line: str) -> Optional[int]:
    reds = [
        e for e in st.session_state.events
        if e.line == line and e.status != EVENT_CLOSED and e.severity == SEVERITY_RED
    ]
    if not reds:
        return None
    reds.sort(key=lambda e: e.created_at)
    return reds[0].station

def derived_line_severity(line: str) -> str:
    if any_open_red_station(line) is not None:
        return SEVERITY_RED
    if any(
        e.line == line and e.status != EVENT_CLOSED and e.severity == SEVERITY_YELLOW
        for e in st.session_state.events
    ):
        return SEVERITY_YELLOW
    return SEVERITY_GREEN

def effective_line_severity(line: str) -> str:
    ov = st.session_state.line_overrides.get(line)
    if ov in (SEVERITY_GREEN, SEVERITY_YELLOW, SEVERITY_RED):
        return ov
    return derived_line_severity(line)

def status_badge(line: str) -> str:
    sev = effective_line_severity(line)
    red_station = any_open_red_station(line)
    ov = st.session_state.line_overrides.get(line)
    src = "override" if ov in (SEVERITY_GREEN, SEVERITY_YELLOW, SEVERITY_RED) else "derived"
    if sev == SEVERITY_RED:
        if red_station is not None and src == "derived":
            return f"STOPPED ({src}) — Red at Station {red_station}"
        return f"STOPPED ({src})"
    if sev == SEVERITY_YELLOW:
        return f"WARNING ({src})"
    return f"RUNNING ({src})"

def next_event_id() -> str:
    st.session_state.event_seq += 1
    return f"E-{st.session_state.event_seq}"

def current_user_name() -> str:
    return st.session_state.role_person_name.get(st.session_state.role, "")

def create_physical_button_sim_event(line: str, station: int, severity: str,
                                     opened_by_user: str, opened_by_name: str, scan_code: str) -> None:
    e = Event(
        id=next_event_id(),
        line=line,
        station=station,
        severity=severity,
        status=EVENT_OPEN,
        source=SOURCE_PHYSICAL,
        source_station=station,
        opened_by_user=opened_by_user,
        opened_by_name=opened_by_name,
        part_serial=scan_code,
        created_at=now(),
    )
    sb_upsert_event(e)

def create_info_event(line: str, station: int, opened_by_user: str, opened_by_name: str, note: str) -> None:
    e = Event(
        id=next_event_id(),
        line=line,
        station=station,
        severity=SEVERITY_INFO,
        status=EVENT_CLOSED,
        source=SOURCE_INFO,
        source_station=station,
        opened_by_user=opened_by_user,
        opened_by_name=opened_by_name,
        part_serial="",
        created_at=now(),
        note=note,
        closed_by=opened_by_user,
        closed_by_name=opened_by_name,
        closed_at=now(),
    )
    sb_upsert_event(e)

# ======================================================
# Maint/Admin overview helpers
# ======================================================
def open_counts_for_line(line: str) -> dict:
    reds = 0
    yellows = 0
    oldest_red_dt = None
    oldest_yellow_dt = None
    oldest_red_station = None
    oldest_yellow_station = None

    for s in range(1, 7):
        ev = get_open_event(line, s)
        if ev is None:
            continue
        if ev.severity == SEVERITY_RED:
            reds += 1
            if oldest_red_dt is None or ev.created_at < oldest_red_dt:
                oldest_red_dt = ev.created_at
                oldest_red_station = s
        if ev.severity == SEVERITY_YELLOW:
            yellows += 1
            if oldest_yellow_dt is None or ev.created_at < oldest_yellow_dt:
                oldest_yellow_dt = ev.created_at
                oldest_yellow_station = s

    return {
        "reds": reds,
        "yellows": yellows,
        "oldest_red_dt": oldest_red_dt,
        "oldest_red_station": oldest_red_station,
        "oldest_yellow_dt": oldest_yellow_dt,
        "oldest_yellow_station": oldest_yellow_station,
    }

def line_card_html(line: str, selected: bool) -> str:
    sev = effective_line_severity(line)
    counts = open_counts_for_line(line)

    pills = f'<span class="pill {severity_css(sev)}"><span class="dot {severity_css(sev)}"></span>{severity_label(sev)}</span>'

    if counts["reds"] == 0 and counts["yellows"] == 0:
        subtitle = "No active events"
    else:
        subtitle = f"Red: {counts['reds']} • Yellow: {counts['yellows']}"
        if counts["oldest_red_dt"] is not None:
            subtitle += f" • Oldest red: S{counts['oldest_red_station']} ({age_str(counts['oldest_red_dt'])})"
        elif counts["oldest_yellow_dt"] is not None:
            subtitle += f" • Oldest yellow: S{counts['oldest_yellow_station']} ({age_str(counts['oldest_yellow_dt'])})"

    return f"""
<div class="card {'selected' if selected else ''}">
  <h3>{line}</h3>
  <div class="small">{subtitle}</div>
  <div class="pills">{pills}</div>
</div>
"""

def technical_rows_for_line(line: str) -> List[dict]:
    rows = []
    for s in range(1, 7):
        ev = get_open_event(line, s)
        if ev is None:
            rows.append(
                {"Line": line, "Station": s, "Severity": "GREEN", "State": "—", "Age": "—",
                 "Scan code": "—", "Operator": "—", "Event ID": "", "Ack": "", "Assigned": ""}
            )
        else:
            rows.append(
                {"Line": line, "Station": s, "Severity": ev.severity, "State": ev.status,
                 "Age": age_str(ev.created_at), "Scan code": ev.part_serial or "",
                 "Operator": ev.opened_by_name or "", "Event ID": ev.id,
                 "Ack": (ev.ack_by_name or ev.ack_by or ""),
                 "Assigned": (ev.assigned_to_name or ev.assigned_to or "")}
            )

    rank = {SEVERITY_RED: 0, SEVERITY_YELLOW: 1, SEVERITY_GREEN: 2}
    def sort_key(r):
        sev = r["Severity"]
        sev_rank = rank.get(sev, 9)
        ev = get_open_event(line, r["Station"])
        created = ev.created_at if ev else now()
        return (sev_rank, created)

    rows.sort(key=sort_key)
    return rows

# ======================================================
# Top controls
# ======================================================
left, mid, right = st.columns([2.6, 2.2, 2.2], vertical_alignment="center")

with left:
    st.markdown(
        """
<div class="header-left">
  <div>
    <div class="h-title">RTPV</div>
    <div class="h-sub">Real Time Production Visibility</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

with mid:
    c1, c2, c3 = st.columns([1.2, 1.0, 1.0])
    with c1:
        prev_role = st.session_state.role
        st.session_state.role = st.selectbox(
            "Role",
            ROLE_OPTIONS,
            index=ROLE_OPTIONS.index(st.session_state.role),
            label_visibility="collapsed",
            key="role_sel",
        )
        if st.session_state.role not in st.session_state.role_person_name:
            st.session_state.role_person_name[st.session_state.role] = ROLE_NAMES[st.session_state.role][0]
        if st.session_state.role != prev_role:
            nm = st.session_state.role_person_name.get(st.session_state.role, "")
            st.session_state.username = default_username_for(st.session_state.role, nm)
            # reload events for new visibility
            st.session_state.events = sb_list_events(visible_lines_for_user(st.session_state.role))

    with c2:
        role = st.session_state.role
        names = ROLE_NAMES.get(role, ["Demo"])
        chosen = st.selectbox(
            "Name",
            names,
            index=names.index(st.session_state.role_person_name.get(role, names[0]))
            if st.session_state.role_person_name.get(role) in names else 0,
            label_visibility="collapsed",
            key="role_name_sel",
        )
        st.session_state.role_person_name[role] = chosen
        st.session_state.username = default_username_for(role, chosen)

    with c3:
        if st.button("Refresh", use_container_width=True):
            # reload events from DB
            st.session_state.events = sb_list_events(visible_lines_for_user(st.session_state.role))
            st.rerun()

with right:
    role = st.session_state.role
    ctx = user_context_for_role(role)

    badge_line = None
    if role in OP_ROLES or role in ("LM_A", "LM_B", "LM_C"):
        badge_line = ctx["fixed_line"]
        st.session_state.selected_line = badge_line
    elif role in MAINT_ADMIN_ROLES and st.session_state.maint_panel_open and st.session_state.maint_selected_line:
        badge_line = st.session_state.maint_selected_line

    if badge_line is None:
        st.markdown(
            """
<div class="badge">
  <span class="dot gray"></span>
  <span>Select a line</span>
</div>
""",
            unsafe_allow_html=True,
        )
    else:
        sev = effective_line_severity(badge_line)
        badge_class = "badge-green" if sev == SEVERITY_GREEN else ("badge-yellow" if sev == SEVERITY_YELLOW else "badge-red")
        st.markdown(
            f"""
<div class="badge {badge_class}">
  <span class="dot {severity_css(sev)}"></span>
  <span>{status_badge(badge_line)}</span>
</div>
""",
            unsafe_allow_html=True,
        )

st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

# ======================================================
# OPERATOR VIEW (ONLY)
# ======================================================
role = st.session_state.role
ctx = user_context_for_role(role)
user = st.session_state.username
user_name = current_user_name()

if role in OP_ROLES:
    st.session_state.selected_line = ctx["fixed_line"]
    st.session_state.selected_station = ctx["fixed_station"]

    st.subheader(f"Operator Panel — {ctx['fixed_line']} / Station {ctx['fixed_station']}")

    tab_actions, tab_docs = st.tabs(["Actions", "Docs (PDF)"])

    with tab_actions:
        st.caption("Create events via physical buttons. Yellow/Red require Operator name + Scan Code (from operator).")

        st.markdown("<div class='op-phys-wrap'>", unsafe_allow_html=True)

        b_red = st.button("Red", use_container_width=False, key=f"op_btn_red_{role}")
        b_yellow = st.button("Yellow", use_container_width=False, key=f"op_btn_yellow_{role}")
        b_green = st.button("Green", use_container_width=False, key=f"op_btn_green_{role}")
        b_call = st.button("Call", use_container_width=False, key=f"op_btn_calllm_{role}")

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            """
<script>
(function(){
  const root = window.parent.document;
  const all = Array.from(root.querySelectorAll('button'));
  const last4 = all.slice(-4);
  if(last4.length !== 4) return;
  last4[0].classList.add('op-phys','op-red');
  last4[1].classList.add('op-phys','op-yellow');
  last4[2].classList.add('op-phys','op-green');
  last4[3].classList.add('op-phys','op-white');
})();
</script>
""",
            unsafe_allow_html=True,
        )

        op_name = st.text_input("Operator name", placeholder="e.g., Cristiano Ronaldo", key=f"open_operator_name_{role}")
        scan_code = st.text_input("Scan Code (Yellow/Red)", placeholder="e.g., SCAN-00012345", key=f"open_scan_code_{role}")

        if b_red:
            if not op_name.strip():
                st.error("For **Red**, operator name is required.")
            elif not scan_code.strip():
                st.error("For **Red**, Scan Code is required.")
            else:
                create_physical_button_sim_event(
                    line=ctx["fixed_line"],
                    station=ctx["fixed_station"],
                    severity=SEVERITY_RED,
                    opened_by_user=user,
                    opened_by_name=op_name.strip(),
                    scan_code=scan_code.strip(),
                )
                st.success("Red event created.")
                st.rerun()

        if b_yellow:
            if not op_name.strip():
                st.error("For **Yellow**, operator name is required.")
            elif not scan_code.strip():
                st.error("For **Yellow**, Scan Code is required.")
            else:
                create_physical_button_sim_event(
                    line=ctx["fixed_line"],
                    station=ctx["fixed_station"],
                    severity=SEVERITY_YELLOW,
                    opened_by_user=user,
                    opened_by_name=op_name.strip(),
                    scan_code=scan_code.strip(),
                )
                st.success("Yellow event created.")
                st.rerun()

        if b_green:
            if not op_name.strip():
                st.error("For **Green**, operator name is required.")
            else:
                # Close open YELLOW/RED at station
                # We update DB rows instead of mutating session list
                # (then rerun reloads)
                visible = visible_lines_for_user(st.session_state.role)
                events_now = sb_list_events(visible)
                for e in events_now:
                    if (
                        e.line == ctx["fixed_line"]
                        and e.station == ctx["fixed_station"]
                        and e.status != EVENT_CLOSED
                        and e.severity in (SEVERITY_YELLOW, SEVERITY_RED)
                    ):
                        sb_update_event(e.id, {
                            "status": EVENT_CLOSED,
                            "closed_by": user,
                            "closed_by_name": user_name,
                            "closed_at": now(),
                        })

                create_info_event(
                    line=ctx["fixed_line"],
                    station=ctx["fixed_station"],
                    opened_by_user=user,
                    opened_by_name=op_name.strip(),
                    note=f"SET GREEN — Operator {op_name.strip()} set station to green (and closed open Yellow/Red at station).",
                )
                st.success("Station set to green (audit logged).")
                st.rerun()

        if b_call:
            if not op_name.strip():
                st.error("For **Call**, operator name is required.")
            else:
                create_info_event(
                    line=ctx["fixed_line"],
                    station=ctx["fixed_station"],
                    opened_by_user=user,
                    opened_by_name=op_name.strip(),
                    note=f"CALL LM — Operator {op_name.strip()} requested line manager.",
                )
                st.success("Call logged.")
                st.rerun()

        st.markdown("---")
        st.caption("Operator view hides technical panels and event feed by design.")

    # Keep your docs tab as-is (session-only)
    with tab_docs:
        st.subheader("Operator Documentation (PDF)")
        st.caption("Demo placeholders + real PDFs (if uploaded).")
        ghost_docs = [
            {"title": "Assembly Instructions", "meta": "PDF • (demo)"},
            {"title": "EIIT Slides", "meta": "PDF • (demo)"},
            {"title": "How to Use ChatGPT", "meta": "PDF • (demo)"},
        ]
        st.markdown("#### Quick Docs")
        for i, d in enumerate(ghost_docs):
            c1, c2, c3 = st.columns([3.2, 2.0, 1.2], vertical_alignment="center")
            with c1:
                st.write(f"**{d['title']}**")
            with c2:
                st.caption(d["meta"])
            with c3:
                if st.button("Open", key=f"ghost_open_{i}", use_container_width=True):
                    st.info("Demo only: this document is a placeholder (no file attached).")

        st.markdown("---")
        st.markdown("#### Library (Uploaded PDFs)")
        can_upload_docs = st.session_state.role in ("ADMIN", "MAINTENANCE")
        up_col, view_col = st.columns([1.0, 1.2], gap="large")

        with up_col:
            st.markdown("**Upload**")
            if can_upload_docs:
                uploads = st.file_uploader(
                    "Upload PDF(s)", type=["pdf"], accept_multiple_files=True,
                    key="op_docs_uploader", help="PDF only."
                )
                if uploads:
                    added = 0
                    for f in uploads:
                        data = f.getvalue()
                        title = f.name
                        exists = any(
                            (x.get("title") == title and len(x.get("data", b"")) == len(data))
                            for x in st.session_state.op_docs
                        )
                        if not exists:
                            st.session_state.op_docs.append({"title": title, "data": data})
                            added += 1
                    if added:
                        st.success(f"Added {added} document(s).")
                        st.rerun()
            else:
                st.info("Uploads are restricted. Ask Admin/Maintenance to add PDFs.")

            if st.session_state.op_docs and can_upload_docs:
                if st.button("Clear library", type="secondary", use_container_width=True, key="clear_docs"):
                    st.session_state.op_docs = []
                    st.success("Library cleared.")
                    st.rerun()

        with view_col:
            st.markdown("**Viewer**")
            if not st.session_state.op_docs:
                st.warning("No uploaded PDFs yet.")
            else:
                titles = [d["title"] for d in st.session_state.op_docs]
                picked = st.selectbox("Select document", titles, index=0, key="picked_doc")
                doc = next(d for d in st.session_state.op_docs if d["title"] == picked)
                st.download_button(
                    "Download PDF",
                    data=doc["data"],
                    file_name=doc["title"],
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"dl_{doc['title']}",
                )
                import base64
                b64 = base64.b64encode(doc["data"]).decode("utf-8")
                st.markdown(
                    f"""
<iframe
  src="data:application/pdf;base64,{b64}"
  width="100%"
  height="720"
  style="border:1px solid rgba(0,0,0,0.08); border-radius:10px; background:white;"
></iframe>
""",
                    unsafe_allow_html=True,
                )

    st.stop()

# ======================================================
# Main layout (non-OP)
# ======================================================
grid_col, detail_col = st.columns([3.3, 1.7], gap="large")

# ======================================================
# LEFT
# ======================================================
with grid_col:
    if role in MAINT_ADMIN_ROLES:
        st.markdown("### Overview — Lines")
        st.caption("Colors reflect effective status (includes Admin overrides). Open a line to see the technical table.")

        lines_html = ['<div class="grid">']
        for line in LINE_OPTIONS:
            selected = (st.session_state.maint_panel_open and st.session_state.maint_selected_line == line)
            lines_html.append(line_card_html(line, selected))
        lines_html.append("</div>")
        st.markdown("\n".join(lines_html), unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        pick_cols = st.columns(len(LINE_OPTIONS))
        for i, line in enumerate(LINE_OPTIONS):
            with pick_cols[i]:
                if st.button("Open", use_container_width=True, key=f"open_line_{line}"):
                    st.session_state.maint_selected_line = line
                    st.session_state.maint_panel_open = True
                    st.session_state.selected_line = line
                    st.session_state.selected_station = 1
                    st.rerun()

        if st.session_state.maint_panel_open and st.session_state.maint_selected_line:
            active_line = st.session_state.maint_selected_line
            if not can_view_line(role, active_line):
                st.error("You don't have permission to view this line.")
                st.stop()

            st.markdown("---")
            topA, topB = st.columns([2, 1])
            with topA:
                st.subheader(f"Technical Panel — {active_line}")
                st.caption("Sorted by severity (RED → YELLOW → GREEN).")
            with topB:
                if st.button("Close panel", use_container_width=True, key="close_maint_panel"):
                    st.session_state.maint_panel_open = False
                    st.session_state.selected_line = None
                    st.session_state.selected_station = None
                    st.rerun()

            st.dataframe(
                technical_rows_for_line(active_line),
                use_container_width=True,
                hide_index=True,
            )

            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            st.caption("Pick a station to view details:")
            pick_cols2 = st.columns(6)
            for i in range(6):
                s = i + 1
                with pick_cols2[i]:
                    if st.button(f"S{s}", use_container_width=True, key=f"maint_pick_{active_line}_{s}"):
                        st.session_state.selected_line = active_line
                        st.session_state.selected_station = s
                        st.rerun()

    else:
        active_line = ctx["fixed_line"]
        st.session_state.selected_line = active_line
        if st.session_state.selected_station is None:
            st.session_state.selected_station = 1

        if not can_view_line(role, active_line):
            st.error("You don't have permission to view this line.")
            st.stop()

        st.markdown(f"### Stations — {active_line}")

        stations_html = ['<div class="grid">']
        for s in range(1, 7):
            ev = get_open_event(active_line, s)
            selected = (st.session_state.selected_station == s)

            if ev is None:
                subtitle = "Running"
                pills = '<span class="pill green"><span class="dot green"></span>Running</span>'
                age = "&nbsp;"
            else:
                subtitle = f"{severity_label(ev.severity)} • {'Acked' if ev.status == EVENT_ACK else 'Open'}"
                pills = f'<span class="pill {severity_css(ev.severity)}"><span class="dot {severity_css(ev.severity)}"></span>{severity_label(ev.severity)}</span>'
                age = f"Active for {age_str(ev.created_at)}"

            stations_html.append(
                f"""
<div class="card {'selected' if selected else ''}">
  <h3>Station {s}</h3>
  <div class="small">{subtitle}</div>
  <div class="pills">{pills}</div>
  <div class="small">{age}</div>
</div>
"""
            )
        stations_html.append("</div>")
        st.markdown("\n".join(stations_html), unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        st.caption("Select station:")
        pick_cols = st.columns(6)
        for i in range(6):
            s = i + 1
            with pick_cols[i]:
                if st.button(f"{s}", use_container_width=True, key=f"pick_{active_line}_{s}"):
                    st.session_state.selected_station = s
                    st.rerun()

# ======================================================
# RIGHT: Details
# ======================================================
with detail_col:
    st.markdown("### Details")

    if role in MAINT_ADMIN_ROLES:
        if not (st.session_state.maint_panel_open and st.session_state.selected_line and st.session_state.selected_station):
            st.info("Open a line and pick a station to view details.")
            st.stop()

    active_line = st.session_state.selected_line
    station = st.session_state.selected_station

    if active_line is None or station is None:
        st.info("Select a line/station to view details.")
        st.stop()

    if not can_view_line(role, active_line):
        st.error("You don't have permission to view this line.")
        st.stop()

    ev = get_open_event(active_line, station)

    st.markdown(
        f"""
<div class="card">
  <div class="panel-title">Station {station} — {active_line}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    info_box = st.container(border=True)
    with info_box:
        if ev is None:
            st.write("**State:** Running (no open events)")
            st.write("**Source:** —")
            st.write("**Scan Code:** —")
            st.write("**Operator:** —")
            st.write("**Age:** —")
        else:
            st.write(f"**State:** {severity_label(ev.severity)}")
            st.write(f"**Source:** {ev.source} (Station {ev.source_station})")
            st.write(f"**Opened by (user):** **{ev.opened_by_user}**")
            st.write(f"**Operator name:** **{ev.opened_by_name}**")
            st.write(f"**Scan Code:** **{ev.part_serial}**")
            st.write(f"**Age:** {age_str(ev.created_at)}")
            st.write(f"**Event state:** {ev.status}")

            if ev.assigned_to:
                nm = f" ({ev.assigned_to_name})" if ev.assigned_to_name else ""
                st.caption(f"Assigned: **{ev.assigned_to}**{nm}")

            if ev.ack_by:
                nm = f" ({ev.ack_by_name})" if ev.ack_by_name else ""
                st.caption(f"Acked by: **{ev.ack_by}**{nm}")

            st.markdown("---")

            can_close_this = can_close_event(role, ev.severity) and ev.status != EVENT_CLOSED

            failure_text = st.text_area(
                "Failure description (required to close)",
                placeholder="e.g., sensor not detecting / screw broken / missing material...",
                height=90,
                disabled=not can_close_this,
                key=f"failure_{ev.id}",
            )

            show_assign = (ev.severity in (SEVERITY_YELLOW, SEVERITY_RED)) and (ev.status != EVENT_CLOSED)

            assigned_choice = None
            if show_assign and can_assign(role):
                tech_options = ROLE_NAMES["MAINTENANCE"]
                assigned_choice = st.selectbox(
                    "Assign technician",
                    tech_options,
                    index=0 if (ev.assigned_to_name not in tech_options) else tech_options.index(ev.assigned_to_name),
                    key=f"assign_choice_{ev.id}",
                )

            c1, c2, c3 = st.columns([1.2, 1.1, 1.1])

            with c1:
                ack_disabled = (not can_ack(role, ev.severity)) or ev.status in (EVENT_ACK, EVENT_CLOSED)
                if st.button("Ack", use_container_width=True, disabled=ack_disabled, key=f"ack_{ev.id}"):
                    sb_update_event(ev.id, {
                        "status": EVENT_ACK,
                        "ack_by": st.session_state.username,
                        "ack_by_name": current_user_name(),
                        "ack_at": now(),
                    })
                    st.success("Acknowledged.")
                    st.rerun()

            with c2:
                close_disabled = not can_close_this
                if st.button("Close", use_container_width=True, disabled=close_disabled, type="primary", key=f"close_{ev.id}"):
                    if not failure_text.strip():
                        st.error("Failure description is required to close.")
                    else:
                        sb_update_event(ev.id, {
                            "status": EVENT_CLOSED,
                            "closed_by": st.session_state.username,
                            "closed_by_name": current_user_name(),
                            "closed_at": now(),
                            "failure_text": failure_text.strip(),
                        })

                        # Keep your parts/failures panel session-only for now
                        st.session_state.part_failures.append(
                            PartFailureRecord(
                                event_id=ev.id,
                                part_serial=ev.part_serial,
                                failure_text=failure_text.strip(),
                                operator_name=ev.opened_by_name,
                                opened_by_user=ev.opened_by_user,
                                line=ev.line,
                                station=ev.station,
                                severity=ev.severity,
                                created_at=ev.created_at,
                                closed_at=now(),
                                closed_by=st.session_state.username,
                                closed_by_name=current_user_name() or "",
                            )
                        )

                        st.success("Closed and logged.")
                        st.rerun()

            with c3:
                if show_assign and can_assign(role):
                    assign_disabled = (assigned_choice is None) or (ev.status == EVENT_CLOSED)
                    if st.button("Assign", use_container_width=True, disabled=assign_disabled, key=f"assign_{ev.id}"):
                        stamp = now().strftime("%H:%M:%S")
                        note_append = f"\n[{stamp}] Assigned to {assigned_choice} by {current_user_name()} ({st.session_state.username})"
                        sb_update_event(ev.id, {
                            "assigned_to": default_username_for("MAINTENANCE", assigned_choice),
                            "assigned_to_name": assigned_choice,
                            "assigned_at": now(),
                            "note": (ev.note or "") + note_append,
                        })
                        st.success(f"Assigned to: {assigned_choice}.")
                        st.rerun()
                else:
                    st.button("Assign", use_container_width=True, disabled=True, key=f"assign_disabled_{ev.id}")

        if can_override(role):
            st.markdown("---")
            st.subheader("Admin — Line Override")

            current_ov = st.session_state.line_overrides.get(active_line)

            override = st.selectbox(
                "Override state",
                ["(none)", "RUNNING (green)", "WARNING (yellow)", "STOPPED (red)"],
                index=0 if current_ov is None else (1 if current_ov == SEVERITY_GREEN else 2 if current_ov == SEVERITY_YELLOW else 3),
                key=f"override_{active_line}",
            )

            cA, cB = st.columns([1, 1])
            with cA:
                if st.button("Apply", use_container_width=True, key=f"apply_override_{active_line}"):
                    mapping = {"(none)": None, "RUNNING (green)": SEVERITY_GREEN, "WARNING (yellow)": SEVERITY_YELLOW, "STOPPED (red)": SEVERITY_RED}
                    st.session_state.line_overrides[active_line] = mapping[override]
                    st.success("Override updated.")
                    st.rerun()
            with cB:
                if st.button("Clear", use_container_width=True, key=f"clear_override_{active_line}"):
                    st.session_state.line_overrides[active_line] = None
                    st.success("Override cleared.")
                    st.rerun()

st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

# ======================================================
# Bottom: Event Feed (non-OP only)
# ======================================================
with st.expander("Event Feed", expanded=False):
    st.caption("No auto-refresh. Use **Refresh** at the top or F5.")
    role = st.session_state.role
    visible_lines = visible_lines_for_user(role)

    # reload a fresh feed from DB for accuracy
    events_sorted: List[Event] = sorted(sb_list_events(visible_lines), key=lambda e: e.created_at, reverse=True)

    rows = []
    for e in events_sorted:
        rows.append(
            {
                "ID": e.id,
                "Line": e.line,
                "Station": e.station,
                "Severity": e.severity,
                "State": e.status,
                "Source": e.source,
                "Src station": e.source_station,
                "Opened by (user)": e.opened_by_user,
                "Opened by (name)": e.opened_by_name,
                "Scan code": e.part_serial,
                "Created": e.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "Age": age_str(e.created_at),
                "Ack by (user)": e.ack_by or "",
                "Ack by (name)": e.ack_by_name or "",
                "Assigned": e.assigned_to_name or "",
                "Closed by (user)": e.closed_by or "",
                "Closed by (name)": e.closed_by_name or "",
                "Failure": e.failure_text or "",
                "Note": e.note or "",
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

if st.session_state.role == "ADMIN":
    with st.expander("Admin — Parts & Failures", expanded=False):
        pf_rows = []
        for r in sorted(st.session_state.part_failures, key=lambda x: x.closed_at, reverse=True):
            pf_rows.append(
                {
                    "Scan code": r.part_serial,
                    "Failure": r.failure_text,
                    "Operator": r.operator_name,
                    "Opened by (user)": r.opened_by_user,
                    "Line": r.line,
                    "Station": r.station,
                    "Severity": r.severity,
                    "Event ID": r.event_id,
                    "Created": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "Closed": r.closed_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "Closed by (user)": r.closed_by,
                    "Closed by (name)": r.closed_by_name,
                }
            )
        st.dataframe(pf_rows, use_container_width=True, hide_index=True)

st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
st.info("Yellow/Red require Operator name + Scan Code at creation. Operators cannot Ack/Close. Close requires failure description. Green logs SET GREEN and closes open Yellow/Red at the station.")