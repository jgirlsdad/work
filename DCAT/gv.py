import streamlit as st
import pandas as pd
from pyvis.network import Network
import tempfile
import os

st.title("Dataset Similarity Graph Viewer with Clickable Nodes")

uploaded_file = st.file_uploader("Upload your relationship CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    # Ensure required columns
    required_cols = {"subject", "object", "score"}
    if not required_cols.issubset(df.columns):
        st.error(f"CSV must contain: {required_cols}")
        st.stop()

    # Optional URL columns
    has_subject_url = "subject_url" in df.columns
    has_object_url = "object_url" in df.columns

    # Sidebar controls
    st.sidebar.header("Controls")
    datasets = sorted(set(df["subject"]).union(df["object"]))
    selected = st.sidebar.selectbox("Select dataset to focus:", datasets)

    threshold = st.sidebar.slider(
        "Minimum score threshold",
        0.0, 1.0, 0.5, 0.01
    )

    # Extract subgraph
    sub_df = df[
        ((df["subject"] == selected) | (df["object"] == selected)) &
        (df["score"] >= threshold)
    ]

    if sub_df.empty:
        st.warning("No relationships above this threshold.")
        st.stop()

    # Build graph
    net = Network(
        height="750px",
        width="100%",
        bgcolor="#1e1e1e",
        font_color="white"
    )

    net.barnes_hut()

    # --------------------
    # Add center node
    # --------------------
    center_url = None
    if has_subject_url:
        # If the selected dataset appears as "subject"
        center_url_match = df[df["subject"] == selected]
        if not center_url_match.empty:
            center_url = center_url_match["subject_url"].iloc[0]

    if has_object_url and center_url is None:
        center_url_match = df[df["object"] == selected]
        if not center_url_match.empty:
            center_url = center_url_match["object_url"].iloc[0]

    # Node with clickable link (via HTML in PyVis title)
    label_html = f"<a href='{center_url}' target='_blank'>{selected}</a>" if center_url else selected

    net.add_node(
        selected,
        label=selected,
        title=label_html,
        shape="dot",
        color="orange",
        size=30
    )

    # --------------------
    # Add neighbors
    # --------------------
    for _, row in sub_df.iterrows():
        if row["subject"] == selected:
            neighbor = row["object"]
            url = row["object_url"] if has_object_url else None
        else:
            neighbor = row["subject"]
            url = row["subject_url"] if has_subject_url else None

        score = row["score"]

        # HTML click link
        n_title = f"<a href='{url}' target='_blank'>{neighbor}</a>" if url else neighbor

        net.add_node(
            neighbor,
            label=neighbor,
            title=n_title,
            color="lightblue",
            size=15
        )
        net.add_edge(
            selected,
            neighbor,
            value=score,
            title=f"Score: {score:.3f}"
        )

    # Save to temp file
    tmp_path = os.path.join(tempfile.gettempdir(), "graph.html")
    net.save_graph(tmp_path)

    # Render
    st.components.v1.html(open(tmp_path, "r", encoding="utf-8").read(), height=800)
