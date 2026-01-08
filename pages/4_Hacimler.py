# -*- coding: utf-8 -*-
"""
Created on Thu Jan 30 14:34:45 2025

@author: mustafayarici
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import numpy as np
import datetime
import xlsxwriter
from datetime import date
from datetime import timedelta
from io import BytesIO,StringIO
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score
from sklearn.linear_model import LinearRegression
import requests as req
import pytz
from time import sleep

st.set_page_config(
    page_title="Gip Eşleşme",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed" # Kenar çubuğunu da kapalı başlatmak isterseniz
)

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

#%%cash
@st.cache_data
def loading(date1,date2):
    tumorg=pd.DataFrame()
    print("döngü")
    for i in giplist['id']:
                
        payload = {
                "startDate": date1,
                "endDate": date2,

                "organizationId": i
            }

        print("try")

        try:        
            print("try1")
            resp_volume = req.post(pkeslesme_url, json=payload, headers=headers, timeout=15)
            print(str(i)+" başarılı")

        except:
            try:
                print("try2")
                resp_volume = req.post(pkeslesme_url, json=payload, headers=headers, timeout=15)
                print(str(i)+" başarılı"+ "deneme2")

            except:
                print(str(i)+" hata GiP")
                pass

        if not pd.DataFrame(resp_volume.json()["items"]).empty:
            temp_volume=pd.DataFrame(resp_volume.json()["items"])
            temp_volume["organizationId"]=i
                                  
            tumorg=pd.concat([tumorg, temp_volume])
            print(str(i)+" gip")
  
    return tumorg    

#%%

slctd_dt = st.date_input('Gün',value=date.today()- datetime.timedelta(days=1))
filtre=slctd_dt
slctd_dt = datetime.datetime(slctd_dt.year, slctd_dt.month, slctd_dt.day).replace(hour=0, minute=0, second=0)
local_timezone = pytz.timezone('Europe/Istanbul')
slctd_dt = slctd_dt.astimezone(local_timezone)

slctd_dt=slctd_dt.replace(hour=0)
slctd_dt = slctd_dt.strftime("%Y-%m-%dT%H:%M:%S%z")
slctd_dt = slctd_dt[:19] + slctd_dt[-5:-2] + ":" + slctd_dt[-2:]

date1=slctd_dt
date2=slctd_dt

datename=date1[:10]

#%%
auth_url = "https://giris.epias.com.tr/cas/v1/tickets"  # TGT almak için kullanacağınız URL
auth_payload = "username=mustafayarici@embaenergy.com&password=Seffaf.0634"
auth_headers = {"Content-Type": "application/x-www-form-urlencoded","Accept": "text/plain"}
# TGT isteğini yap
try:
    auth_response = req.post(auth_url, data=auth_payload, headers=auth_headers)
    auth_response.raise_for_status()  
    tgt = auth_response.text  # TGT'yi yanıt metninden al
    print("TGT : başarılı")
except Exception as e:
    print("TGT alma hatası:", e)
    tgt = None  # TGT alınamazsa devam edemeyiz
headers = {"TGT": tgt, "Content-Type": "application/json", "Accept": "application/json" }

#%%
pktur_url="https://seffaflik.epias.com.tr/electricity-service/v1/markets/general-data/data/market-participants"
headers = {"TGT": tgt, "Content-Type": "application/json", "Accept": "application/json" }
payload = {}
resp_pktur = req.post(pktur_url, json=payload, headers=headers, timeout=15)
pk_tur_list=pd.DataFrame(resp_pktur.json()["items"])

#%%
giplist=pk_tur_list[pk_tur_list['intraDayEntry']==True][["orgName","orgCode","eicCode","id"]]

#%%

pkeslesme_url="https://seffaflik.epias.com.tr/electricity-service/v1/markets/idm/data/matching-quantity"

tumorg=loading(date1,date2)

tumorg.reset_index(drop=True, inplace=True)

#%%

def convert_date(df):
    try:
        
        df[['year', 'month', 'day', 'hour']] = df['kontratAdi'].str.extract(r'PH(\d{2})(\d{2})(\d{2})(\d{2})', expand=True)
        df['Tarih'] = df['year'] + df['month'] + df['day'] + df['hour']
        df['Tarih'] = pd.to_datetime(df['Tarih'], format='%y%m%d%H')
        df.drop(columns=['year', 'month', 'day', 'hour'], inplace=True)

        return df

    except Exception as e:
        print(f"Tarih Hata: {e}")
        return df
gipeslesme = convert_date(tumorg) 


#%%
giplist.rename(columns ={'id':'organizationId'},inplace=True)
#gipeslesme['Tarih'] = pd.to_datetime(gipeslesme['Tarih'])
gipeslesme=gipeslesme.merge(giplist[['organizationId','orgName']], how='left',on=['organizationId'])


gipeslesme.rename(columns ={'orgName':'Katılımcı','clearingQuantityAsk':'Alış Miktarı','clearingQuantityBid':'Satış Miktarı',},inplace=True)
#%%

selected_hour = st.selectbox('Saat Seçiniz',  range(24), index=0)

#%%

filtered_data = gipeslesme[ (gipeslesme['Tarih'].dt.hour == selected_hour) ]

#tabledata=filtered_data.copy()
#filtered_data=filtered_data.loc[:, (filtered_data != 0).any(axis=0)]

alısdata=filtered_data[["Katılımcı","Alış Miktarı"]]
#alısdata.rename(columns ={'clearingQuantityAsk':'Alış Miktarı','orgName':'Katılımcı'},inplace=True)

#%%
satisdata=filtered_data[["Katılımcı","Satış Miktarı"]]



col1, col2 = st.columns(2)

with col1:
    st.dataframe(alısdata,use_container_width=True)

with col2:
    st.dataframe(satisdata,use_container_width=True)

st.download_button(
   "Veri İndir",
   gipeslesme.to_csv(sep=";", decimal=",",index=False).encode('utf-8-sig'),
   "Eslesme.csv",
   "text/csv",
   key='download-Eslesme'
)
