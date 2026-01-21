from streamlit_cytoscapejs import st_cytoscapejs

clicked = st_cytoscapejs(
    elements=elements,
    layout={"name": "cose"},
    stylesheet=[
        {
            "selector": "node",
            "style": {
                "label": "data(label)",
                "background-color": "#66ccff",
                "color": "white",
                "text-wrap": "wrap",
                "text-max-width": "120px",
                "width": 150,
                "height": 80,
                "font-size": "12px",
                "text-valign": "center",
                "text-halign": "center",
                "shape": "round-rectangle",
            },
        },
        {
            "selector": ".center",
            "style": {
                "background-color": "#ff9900",
                "color": "white",
                "width": 200,
                "height": 100,
                "font-size": "16px",
                "font-weight": "bold",
            },
        },
    ],
    height="800px"
)
