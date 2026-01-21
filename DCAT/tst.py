import streamlit as st

st.set_page_config(layout="wide")

st.write("## Click Test — Cytoscape → Streamlit")

html = """
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.21.0/cytoscape.min.js"></script>
</head>
<body>
<div id="cy" style="width:100%; height:400px; background:#111;"></div>

<script>
var cy = cytoscape({
    container: document.getElementById('cy'),
    elements: [
        { data: { id: 'A', label: 'Node A' } },
        { data: { id: 'B', label: 'Node B' } },
        { data: { source: 'A', target: 'B' } }
    ],
    style: [
        {
            selector: 'node',
            style: {
                'label': 'data(label)',
                'background-color': '#66ccff',
                'color': 'white',
                'text-valign': 'center',
                'text-halign': 'center',
                'width': 60,
                'height': 60
            }
        }
    ],
    layout: { name: 'circle' }
});

// SEND MESSAGE TO STREAMLIT
//cy.on('tap', 'node', function(evt){
//     const nodeId = evt.target.id();
//     window.parent.postMessage({type: 'cy_click', node: nodeId}, "*");
//});

cy.on('tap', 'node', function(evt){
    const nodeId = evt.target.id();
    document.getElementById("clicked_node").value = nodeId;
    document.getElementById("clicked_node_form").submit();
});

</script>
<form id="clicked_node_form" method="GET">
    <input type="text" id="clicked_node" name="clicked_node" hidden>
</form>
</body>
</html>
"""

clicked = st.text_input("clicked", key="clicked_node")

# If updated → rerun viewer focused on that node
if clicked and clicked != st.session_state.get("focused", None):
    st.session_state["focused"] = clicked
    st.rerun()

# LISTEN FOR MESSAGE
clicked = st.components.v1.html(html, height=450)

# JS → Python event system
event = st.experimental_get_query_params().get("cy_click")
if event:
    st.write(f"### Node clicked: {event[0]}")
