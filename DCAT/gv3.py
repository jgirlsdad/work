import streamlit as st
import pandas as pd
from streamlit_cytoscapejs import st_cytoscapejs
import math
import time

st.set_page_config(layout="wide")
st.title("Interactive Dataset Graph Explorer")


# ---------------------------------------
# Helper: update focus + rerun
# ---------------------------------------
def rerun(focus: str):
    st.session_state["focused"] = focus
    st.rerun()


def normalize_clicked(clicked):
    """Normalize the value returned by st_cytoscapejs to a node id string or None."""
    if not clicked:
        return None

    if isinstance(clicked, dict):
        # Most common format: {"selected_node_id": "The Dataset Title"}
        if "selected_node_id" in clicked:
            return clicked["selected_node_id"]
        # Fallback: take first value
        try:
            return list(clicked.values())[0]
        except Exception:
            return None

    # If it's already a string
    if isinstance(clicked, str):
        return clicked

    return None


# ---------------------------------------
# Upload CSV
# ---------------------------------------
uploaded_file = st.file_uploader("Upload your relationship CSV", type=["csv"])

if not uploaded_file:
    st.stop()

df = pd.read_csv(uploaded_file)
#df['subject_url'] = f"https://data.colorado.gov/d/{df['subject_w4x4']}"
required = {"subject", "object", "score"}
if not required.issubset(df.columns):
    st.error("CSV must include columns: subject, object, score")
    st.stop()

# Optional URL columns
has_usub = "subject_url" in df.columns
has_uobj = "object_url" in df.columns

datasets = sorted(set(df["subject"]).union(df["object"]))

if "focused" not in st.session_state:
    st.session_state["focused"] = datasets[0]

# Track click history for double-click detection
if "last_clicked_node" not in st.session_state:
    st.session_state["last_clicked_node"] = None
if "last_clicked_time" not in st.session_state:
    st.session_state["last_clicked_time"] = 0.0
if "selected_node" not in st.session_state:
    st.session_state["selected_node"] = st.session_state["focused"]

focused = st.session_state["focused"]

# ---------------------------------------
# Sidebar controls
# ---------------------------------------
st.sidebar.header("Controls")

threshold = st.sidebar.slider(
    "Minimum relationship score", 0.0, 1.0, 0.5, 0.01
)

manual_focus = st.sidebar.selectbox(
    "Focus dataset:",
    datasets,
    index=datasets.index(focused)
)

if manual_focus != focused:
    rerun(manual_focus)

focused = st.session_state["focused"]
st.write(f"### Focused Dataset: **{focused}**")

# ---------------------------------------
# Filter edges for focused node
# ---------------------------------------
sub = df[
    ((df["subject"] == focused) | (df["object"] == focused))
    & (df["score"] >= threshold)
]

# Determine center URL (if available)
center_url = None
if has_usub:
    rows = df[df["subject"] == focused]
    if not rows.empty:
        center_url = rows["subject_url"].iloc[0]
if has_uobj and center_url is None:
    rows = df[df["object"] == focused]
    if not rows.empty:
        center_url = rows["object_url"].iloc[0]

# ---------------------------------------
# Build Cytoscape elements WITH POSITIONS
# and collect node → url, node → score (from center)
# ---------------------------------------
elements = []
node_urls = {}
node_scores = {}

# Center node at origin
elements.append({
    "data": {
        "id": focused,
        "label": focused,
        "title": center_url or "",
    },
    "position": {"x": 0, "y": 0},
    "classes": "center",
})
node_urls[focused] = center_url

# Neighbor nodes + edges on circle
neighbors = []
for _, row in sub.iterrows():
    if row["subject"] == focused:
        neighbor = row["object"]
        url = row["object_url"] if has_uobj else None
    else:
        neighbor = row["subject"]
        url = row["subject_url"] if has_usub else None

    neighbors.append((neighbor, url, row["score"]))

N = len(neighbors)
R = 300 + 10 * N  # radius grows if many neighbors

for i, (n, url, score) in enumerate(neighbors):
    angle = 2 * math.pi * i / max(N, 1)
    x = R * math.cos(angle)
    y = R * math.sin(angle)

    # Neighbor node
    elements.append({
        "data": {
            "id": n,
            "label": n,
            "title": url or "",
        },
        "position": {"x": x, "y": y},
        "classes": "neighbor",
    })
    node_urls[n] = url
    node_scores[n] = float(score)

    # Edge
    elements.append({
        "data": {
            "source": focused,
            "target": n,
            "label": f"{score:.2f}",
        }
    })

# ---------------------------------------
# Layout: graph + info panel
# ---------------------------------------
col_graph, col_info = st.columns([3, 2])

with col_graph:
    clicked_raw = st_cytoscapejs(
        elements=elements,
        stylesheet=[
            {
                "selector": "node",
                "style": {
                    "label": "data(label)",
                    "text-wrap": "wrap",
                    "text-max-width": "130px",
                    "background-color": "#66ccff",
                    "color": "white",
                    "text-valign": "center",
                    "text-halign": "center",
                    "shape": "round-rectangle",
                    "width": 160,
                    "height": 80,
                    "padding": "10px",
                    "font-size": "12px",
                    "font-weight": "bold",
                }
            },
            {
                "selector": ".center",
                "style": {
                    "background-color": "#ff9900",
                    "color": "white",
                    "border-width": 4,
                    "border-color": "white",
                    "shape": "round-rectangle",
                    "width": 200,
                    "height": 100,
                    "font-size": "14px",
                    "font-weight": "bold",
                }
            },
            {
                "selector": "edge",
                "style": {
                    "width": 2,
                    "line-color": "#888",
                    "curve-style": "bezier",
                    "target-arrow-color": "#bbb",
                }
            }
        ],
        height="800px",
        key="cyto_graph",
    )

# ---------------------------------------
# Handle single-click vs "double-click"
# ---------------------------------------
clicked_node = normalize_clicked(clicked_raw)

if clicked_node:
    now = time.time()
    last_node = st.session_state.get("last_clicked_node")
    last_time = st.session_state.get("last_clicked_time", 0.0)

    # "Double-click" = two clicks on same node within 0.8 seconds
    if last_node == clicked_node and (now - last_time) < 0.8:
        # Treat as double-click → change focus
        if clicked_node != focused:
            st.session_state["selected_node"] = clicked_node
            st.session_state["last_clicked_node"] = clicked_node
            st.session_state["last_clicked_time"] = now
            rerun(clicked_node)
    else:
        # Single-click → update selection only
        st.session_state["selected_node"] = clicked_node
        st.session_state["last_clicked_node"] = clicked_node
        st.session_state["last_clicked_time"] = now

# ---------------------------------------
# Info panel
# ---------------------------------------
with col_info:
    selected = st.session_state.get("selected_node", focused)
    st.subheader("Selected dataset")

    st.write(f"**Title:** {selected}")

    url = node_urls.get(selected)
    if url:
        st.markdown(f"**URL:** [{url}]({url})", unsafe_allow_html=True)
    else:
        st.write("**URL:** (none available)")

    if selected == focused:
        st.write("_This is the current center (focused) dataset._")
    else:
        score = node_scores.get(selected)
        if score is not None:
            st.write(f"**Similarity score (to center):** {score:.3f}")
        st.write("_Double-click this node in the graph to make it the new center._")

    # Also show the current center link for convenience
    if center_url:
        st.markdown(
            f"\n\n**Current center dataset page:** "
            f"[{focused}]({center_url})",
            unsafe_allow_html=True,
        )
