import streamlit as st
import pandas as pd
import json

st.set_page_config(layout="wide")
st.title("Interactive Dataset Graph Explorer")

# ---------------------------------------
# Helper: rerun with updated focus dataset
# ---------------------------------------
def rerun(focus):
    st.session_state["focused"] = focus
    st.rerun()

# ---------------------------------------
# Main App
# ---------------------------------------
uploaded_file = st.file_uploader("Upload your relationship CSV", type=["csv"])

if uploaded_file:

    df = pd.read_csv(uploaded_file)

    required = {"subject", "object", "score"}
    if not required.issubset(df.columns):
        st.error("CSV must include: subject, object, score")
        st.stop()

    # Optional URLs
    has_usub = "subject_url" in df.columns
    has_uobj = "object_url" in df.columns

    # All dataset names
    datasets = sorted(set(df["subject"]).union(df["object"]))

    # Initialize focus
    if "focused" not in st.session_state:
        st.session_state["focused"] = datasets[0]

    st.sidebar.header("Controls")

    # Threshold slider
    threshold = st.sidebar.slider(
        "Minimum relationship score",
        0.0, 1.0, 0.5, 0.01
    )

    # Dropdown fallback
    manual_focus = st.sidebar.selectbox(
        "Focus dataset:",
        datasets,
        index=datasets.index(st.session_state["focused"])
    )

    if manual_focus != st.session_state["focused"]:
        rerun(manual_focus)

    focused = st.session_state["focused"]

    st.write(f"### Focused Dataset: **{focused}**")

    # Filter edges for this dataset
    sub = df[
        ((df["subject"] == focused) | (df["object"] == focused)) &
        (df["score"] >= threshold)
    ]

    # Determine URL for center node
    center_url = None

    if has_usub:
        m = df[df["subject"] == focused]
        if not m.empty:
            center_url = m["subject_url"].iloc[0]

    if has_uobj and center_url is None:
        m = df[df["object"] == focused]
        if not m.empty:
            center_url = m["object_url"].iloc[0]

    # Cytoscape element list
    elements = []

    # Add center node
    elements.append({
        "data": {"id": focused, "label": focused, "url": center_url},
        "classes": "center"
    })

    # Add neighbors + edges
    for _, row in sub.iterrows():
        if row["subject"] == focused:
            n = row["object"]
            url = row["object_url"] if has_uobj else None
        else:
            n = row["subject"]
            url = row["subject_url"] if has_usub else None

        elements.append({
            "data": {"id": n, "label": n, "url": url},
            "classes": "neighbor"
        })

        elements.append({
            "data": {
                "source": focused,
                "target": n,
                "label": f"{row['score']:.2f}"
            }
        })

    # ---------------------------------------
    # Cytoscape JS Embedded Viewer
    # ---------------------------------------
    html = f"""
    <html>
    <head>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.21.0/cytoscape.min.js"></script>
    </head>
    <body>

    <div id="cy" style="height:800px; width:100%; background-color:#111;"></div>

    <script>
        var elements = {json.dumps(elements)};

        var cy = cytoscape({{
            container: document.getElementById('cy'),
            elements: elements,
            layout: {{ name: 'cose' }},
            style: [
    {{
        selector: 'node',
        style: {{
            'label': 'data(label)',
            'text-wrap': 'wrap',
            'text-max-width': '120px',
            'background-color': '#66ccff',
            'color': '#ffffff',
            'text-valign': 'center',
            'text-halign': 'center',
            'shape': 'round-rectangle',
            'width': 150,
            'height': 80,
            'padding': '10px',
            'font-size': '12px',
            'font-weight': 'bold'
        }}
    }},
    {{
        selector: '.center',
        style: {{
            'background-color': '#ff9900',
            'color': '#ffffff',
            'shape': 'round-rectangle',
            'width': 200,
            'height': 100,
            'padding': '15px',
            'text-wrap': 'wrap',
            'text-max-width': '180px',
            'border-width': 4,
            'border-color': 'white',
            'font-size': '14px',
            'font-weight': 'bold'
        }}
    }},
    {{
        selector: 'edge',
        style: {{
            'width': 2,
            'line-color': '#777',
            'curve-style': 'bezier',
            'target-arrow-color': '#777',
            'font-size': '8px',
            'label': ''
        }}
    }}
]

        }});

        // Hover → tooltip with URL
        cy.on('mouseover', 'node', function(evt) {{
            let url = evt.target.data('url');
            if(url) {{
                cy.tooltip = document.createElement('div');
                cy.tooltip.innerHTML = "<a href='" + url + "' target='_blank'>" + url + "</a>";
                cy.tooltip.style.position = "fixed";
                cy.tooltip.style.color = "#fff";
                cy.tooltip.style.background = "#333";
                cy.tooltip.style.padding = "5px 10px";
                cy.tooltip.style.borderRadius = "4px";
                cy.tooltip.style.zIndex = 9999;
                document.body.appendChild(cy.tooltip);

                document.body.onmousemove = function(e){{
                    cy.tooltip.style.left = (e.clientX+15) + "px";
                    cy.tooltip.style.top = (e.clientY+15) + "px";
                }};
            }}
        }});

        cy.on('mouseout', 'node', function(evt){{
            if(cy.tooltip) {{
                cy.tooltip.remove();
                cy.tooltip = null;
            }}
        }});

        // Click → tell Streamlit which node was clicked
        cy.on('tap', 'node', function(evt){{
            const nodeId = evt.target.id();
            window.parent.postMessage({{'focus_node': nodeId}}, "*");
        }});
    </script>

    </body>
    </html>
    """

    # Render in Streamlit
    st.components.v1.html(html, height=800)

    # Catch click events from JS
    msg = st.experimental_get_query_params().get("focus_node")
    if msg:
        print("Focus node clicked:", msg)
        rerun(msg[0])

    # Show link for center
    if center_url:
        st.markdown(
            f"[Open dataset page for **{focused}**]({center_url})",
            unsafe_allow_html=True
        )
