import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os,json,requests
bic_etl_home = os.getenv('bic_etl_home')
# ---- Sample DataFrame (replace this with your real dfActivity) ----
@st.cache_data(show_spinner=False)
def getActivityLog():
    flog=open(f"{bic_etl_home}/general/datasync/config.json")
    info = json.load(flog)
    username=info['username']
    password=info['password']
    api=info['appToken']
#    "$where": "created_at > '2023-01-01T00:00:00' and acting_user_name = 'Colorado Information Marketplace' order by 'created_at' desc"
    
    # URL of the login form
    query = {
    "$where": "created_at > '2023-01-01T00:00:00' and (acting_user_name = 'Colorado Information Marketplace' or acting_user_name = 'Business Intelligence Center of CO')"
    }
    login_url = 'https://data.colorado.gov/api/activity_log.json?$limit=6000000'
    response=requests.get(login_url,auth=(username, password),params=query)
    if response.status_code == 200:
      
#        activity_log=json.loads(response.text)
        dfActivity=pd.DataFrame.from_records(response.json())   
        titles=dfActivity['dataset_name'].unique()
        titles=[title for title in titles if isinstance(title,str)]
        titles.sort()
    else:
        print("Failed to download Activity Log")
        print(f"Error: {response.status_code}")
        print(f"Message: {response.text}")

    return dfActivity,titles


print("GETTING DATA")
dfActivity,titles = getActivityLog()

# ---- Filter ----
needs = ['affected_item', 'created_at', 'activity_type',
        'acting_user_name', 'service', 'dataset_uid',
        'dataset_name', 'asset_type', 'details']


# ---- Streamlit UI ----
st.set_page_config(page_title="DataFrame Viewer", layout="wide")

st.title("📊 DataFrame Viewer")

# Dropdown menu (replaces Tkinter OptionMenu)

title = st.selectbox("Choose an action:", titles)
print("TITLE SELECTED:", title)
# Event-like logic (replaces trace_add / event sniffer)
dfOut = dfActivity.loc[dfActivity['affected_item'] == title, needs]
dfOut['created_at'] = pd.to_datetime(dfOut['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
dfOut.sort_values(by='created_at', ascending=False, inplace=True)
dfOut = dfOut.sort_values(by='created_at', ascending=False)
html = dfOut.to_html(index=False, escape=False)




css = """
<style>
table {
  border-collapse: collapse;
  width: 100%;
  table-layout: fixed;
  font-family: Arial, sans-serif;
}
th, td {
  border: 1px solid #ccc;
  padding: 8px;
  word-wrap: break-word;
  white-space: normal;
  vertical-align: top;
}
td:nth-child(9) {
  max-height: 120px;           /* limit vertical height */
  overflow-y: auto;            /* vertical scrollbar */
  display: block;              /* allow scrolling */
}

th {
  background-color: #f0f0f0;
}</style>""" 


st.markdown(css + html, unsafe_allow_html=True)
#components.html(full_html, height=600, scrolling=True)
# st.write("### Full Table")
# st.dataframe(dfOut, width='stretch', height=600)

st.info("Select an option to view data.")
