#!/usr/bin/env python
# coding: utf-8

# In[26]:


import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridUpdateMode
from st_aggrid.grid_options_builder import GridOptionsBuilder
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', None)


# In[2]:


df1 = pd.read_csv("Asset_Inventory.csv")


# In[11]:


dfCIM = df1.loc[df1["Owner"] == "Colorado Information Marketplace"]


# In[15]:


dfCIMMap = dfCIM.loc[dfCIM["Type"] == "map"]


# In[24]:


dfCIMMapCen = dfCIMMap.loc[dfCIMMap["Name"].str.lower().str.contains("census")]


# In[32]:


df = dfCIMMapCen
gd = GridOptionsBuilder.from_dataframe(df)
gd.configure_selection(selection_mode='multiple', use_checkbox=True)
gridoptions = gd.build()

grid_table = AgGrid(df, height=250, gridOptions=gridoptions,
                    update_mode=GridUpdateMode.SELECTION_CHANGED)

st.write('## Selected')
selected_row = grid_table["selected_rows"]
st.dataframe(selected_row)


# In[ ]:




