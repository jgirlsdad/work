# mylab/util.py
def maybe_import_mpl():
    try:
        import matplotlib.pyplot as plt
        return plt
    except Exception:
        return None
