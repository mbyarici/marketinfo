# -*- coding: utf-8 -*-
"""
Created on Sat Jan 18 06:25:53 2025

@author: Lenovo
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
    page_title="Gip İşlem Akışı",
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

#%%
auth_url = "https://giris.epias.com.tr/cas/v1/tickets"  # TGT almak için kullanacağınız URL
auth_payload = "username=mustafayarici@embaenergy.com&password=Seffaf.3406"
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

#%%payload


print("push") 

slctd_dt = st.date_input('Gün',value=date.today())
filtre=slctd_dt
slctd_dt = datetime.datetime(slctd_dt.year, slctd_dt.month, slctd_dt.day).replace(hour=0, minute=0, second=0)
local_timezone = pytz.timezone('Europe/Istanbul')
slctd_dt = slctd_dt.astimezone(local_timezone)

predate=slctd_dt- datetime.timedelta(days=1)

slctd_dt=slctd_dt.replace(hour=0)
slctd_dt = slctd_dt.strftime("%Y-%m-%dT%H:%M:%S%z")
slctd_dt = slctd_dt[:19] + slctd_dt[-5:-2] + ":" + slctd_dt[-2:]

predate=predate.replace(hour=0)
predate = predate.strftime("%Y-%m-%dT%H:%M:%S%z")
predate = predate[:19] + predate[-5:-2] + ":" + predate[-2:]

date1=predate
date2=slctd_dt

payload = {"startDate": date1, "endDate": date2 }
headers = {"TGT": tgt, "Content-Type": "application/json", "Accept": "application/json" }

print(date1)

miktar=200

#%%ptf
url_gipakis="https://seffaflik.epias.com.tr/electricity-service/v1/markets/idm/data/transaction-history"
gipakis_resp=req.post(url_gipakis, json=payload, headers=headers)
gipakis_df=pd.DataFrame(gipakis_resp.json()["items"])

#%%laptop farklı sürüm

gipakis_df["date"] = gipakis_df["date"].str.split(".", n=1).str[0]#?

# Convert to datetime

gipakis_df["date"] = pd.to_datetime(gipakis_df["date"], format='%Y-%m-%dT%H:%M:%S%z')

gipakis_df["date"]=gipakis_df["date"].dt.tz_localize(None)

#%%
def convert_date(df):
    try:
        
        df[['year', 'month', 'day', 'hour']] = df['contractName'].str.extract(r'PH(\d{2})(\d{2})(\d{2})(\d{2})', expand=True)
        df['Kontrat'] = df['year'] + df['month'] + df['day'] + df['hour']
        df['Kontrat'] = pd.to_datetime(df['Kontrat'], format='%y%m%d%H')
        df.drop(columns=['year', 'month', 'day', 'hour'], inplace=True)

        return df

    except Exception as e:
        print(f"Tarih Hata: {e}")
        return df
gipakis_df = convert_date(gipakis_df) 
#%%
def calculate_weighted_average(df, min_or_max):

    if min_or_max == 'min':
        df = df.sort_values(by='price')  # Sort by price in ascending order
    elif min_or_max == 'max':
        df = df.sort_values(by='price', ascending=False)  # Sort by price in descending order

    cumulative_quantity = 0
    selected_rows = []
    for index, row in df.iterrows():
        cumulative_quantity += row['quantity']
        selected_rows.append(row) 
        if cumulative_quantity >= miktar:
            break

    if cumulative_quantity >= miktar:
        selected_df = pd.DataFrame(selected_rows)
        weighted_sum = (selected_df['price'] * selected_df['quantity']).sum()
        return weighted_sum / cumulative_quantity
    else:
        return np.nan

def calculate_averages(df):

    unique_contracts = df['contractName'].unique()
    results = []

    for contract in unique_contracts:
        contract_df = df[df['contractName'] == contract]
        minavg = calculate_weighted_average(contract_df, 'min')
        maxavg = calculate_weighted_average(contract_df, 'max')
        kontrat = contract_df['Kontrat'].iloc[0] 
        results.append({'contractName': contract, 'minavg': minavg, 'maxavg': maxavg, 'Kontrat': kontrat})

    return pd.DataFrame(results)
#%%
df_with_averages = calculate_averages(gipakis_df)

#%%

gipakis_df = gipakis_df.merge(df_with_averages[["contractName","minavg","maxavg"]], on='contractName', how='left') 
gipakis_df = gipakis_df.sort_values(by='Kontrat', ascending=True)
#%%
url_ptf="https://seffaflik.epias.com.tr/electricity-service/v1/markets/dam/data/mcp"
payload = {
        "startDate": date1,
        "endDate": date2
    }

ptf_resp=req.post(url_ptf,json=payload, headers=headers, timeout=10)
df_ptf=pd.DataFrame(ptf_resp.json()["items"])

#df_ptf["date"] = df_ptf["date"].str.split(".", n=1).str[0]
df_ptf["date"] = pd.to_datetime(df_ptf["date"], format='%Y-%m-%dT%H:%M:%S%z')

df_ptf["date"]=df_ptf["date"].dt.tz_localize(None)

df_ptf.rename(columns={'date': 'Kontrat','price':'PTF'}, inplace=True)

gipakis_df=gipakis_df.merge(df_ptf[['Kontrat','PTF']], how='left',on=['Kontrat'])

#%%

url_yal="https://seffaflik.epias.com.tr/electricity-service/v1/markets/bpm/data/order-summary-up"
url_yat="https://seffaflik.epias.com.tr/electricity-service/v1/markets/bpm/data/order-summary-down"
url_yon="https://seffaflik.epias.com.tr/electricity-service/v1/markets/bpm/data/system-direction"

payload = {
        "startDate": date1,
        "region": "TR1",
        "endDate": date2
    }
yal_resp=req.post(url_yal,json=payload, headers=headers, timeout=10)
df_Yal=pd.DataFrame(yal_resp.json()["items"])
df_Yal["date"] = pd.to_datetime(df_Yal["date"], format='%Y-%m-%dT%H:%M:%S%z')
df_Yal["date"]=df_Yal["date"].dt.tz_localize(None)
df_Yal.rename(columns={'date': 'merge'}, inplace=True)
df_Yal["merge"]=df_Yal["merge"]+pd.to_timedelta(1, unit='H')

yon_resp=req.post(url_yon,json=payload, headers=headers, timeout=10)
df_Yon=pd.DataFrame(yon_resp.json()["items"])
df_Yon["date"] = pd.to_datetime(df_Yon["date"], format='%Y-%m-%dT%H:%M:%S%z')
df_Yon["date"]=df_Yon["date"].dt.tz_localize(None)
df_Yon.rename(columns={'date': 'merge'}, inplace=True)
#%%
df_Yal.drop(columns=['hour', 'upRegulationZeroCoded', 'upRegulationOneCoded', 'upRegulationTwoCoded','upRegulationDelivered'], inplace=True)

#%%
gipakis_df['merge']= gipakis_df['date'].dt.floor('H') #saate yuvarlama
gipakis_df=gipakis_df.merge(df_Yal[['merge','net']], how='left',on=['merge'])
grafik=gipakis_df[gipakis_df['Kontrat'].dt.date == filtre]
grafik=grafik[["date","price","quantity","Kontrat","minavg","maxavg","PTF","net"]]

#%%

# Kontrat saatlerini benzersiz olarak al
unique_hours = grafik['Kontrat'].dt.hour.unique()
unique_hours.sort() #Saatleri sıralar

# Grafik düzenini belirle (örneğin, 4 sütun)
num_cols = 2
num_rows = (len(unique_hours) + num_cols - 1) // num_cols # Satır sayısını otomatik hesaplar

for row in range(num_rows):
    cols = st.columns(num_cols)
    for col_idx in range(num_cols):
        idx = row * num_cols + col_idx
        if idx < len(unique_hours):
            hour = unique_hours[idx]
            hour_data = grafik[grafik['Kontrat'].dt.hour == hour].sort_values('date')

            with cols[col_idx]:
                fig = go.Figure()

                # Fiyat için çizgi grafiği (birinci y ekseni)
                fig.add_trace(go.Scatter(x=hour_data['date'], y=hour_data['price'], mode='lines+markers', name='Fiyat (TL/MWh)', yaxis='y1'))               
                # minavg için düz çizgi
                fig.add_trace(go.Scatter(x=hour_data['date'], y=hour_data['minavg'], mode='lines', name='Min. Ortalama', yaxis='y1', line=dict(color='green', dash='dash')))
                # maxavg için düz çizgi
                fig.add_trace(go.Scatter(x=hour_data['date'], y=hour_data['maxavg'], mode='lines', name='Max. Ortalama', yaxis='y1', line=dict(color='red', dash='dash')))
                # PTF için düz çizgi
                fig.add_trace(go.Scatter(x=hour_data['date'], y=hour_data['PTF'], mode='lines', name='PTF', yaxis='y1', line=dict(color='black')))
                # Yön
                fig.add_trace(go.Scatter(x=hour_data['date'], y=hour_data['net'], mode='lines', name='Yön(MWh)', yaxis='y2', line=dict(color='yellow')))
                # Miktar için sütun grafiği (ikinci y ekseni)
                fig.add_trace(go.Bar(x=hour_data['date'], y=hour_data['quantity'], name='Miktar (LOT)', yaxis='y2'))
                # Çift y ekseni ayarları
                fig.update_layout(
                    title=f"Saat {hour} Verileri",
                    #xaxis_title="Tarih ve Saat",
                    yaxis_title="Fiyat (TL/MWh)",
                    yaxis2=dict(
                        title="Miktar (MWh)",
                        overlaying="y",
                        side="right"
                    ),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.4, xanchor="center", x=0.5) # Legendi grafiğin altına taşır.
                )
                fig.update_layout(height=400) #yükseklik ayarı
                st.plotly_chart(fig,use_container_width=True)

