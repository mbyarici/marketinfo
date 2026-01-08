# -*- coding: utf-8 -*-
"""
Created on Wed May 10 14:21:53 2023

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

#%%sayfa düzeni
st.set_page_config(
    page_title="Kesinti",
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

    print("döngü")

    all_data = pd.DataFrame()
    while date1 <= date2:
        
        print(date1)
        formatted_date = date1.strftime("%Y-%m-%dT%H:%M:%S%z")
        formatted_date = formatted_date[:19] + formatted_date[-5:-2] + ":" + formatted_date[-2:]
        print(formatted_date)
        payload = {"startDate": formatted_date, "endDate": formatted_date }
        print(payload)
        blok_resp = req.post(block_url, json=payload, headers=headers)
        df_blok=pd.DataFrame(blok_resp.json()["items"])
        df_blok["date"]=pd.to_datetime(df_blok["date"].str[0:-3], format='%Y-%m-%dT%H:%M:%S.%f')
        df_blok["date"]=df_blok["date"].dt.tz_localize(None)
    
        market_resp = req.post(marketvolume_url, json=payload, headers=headers)
        df_market=pd.DataFrame(market_resp.json()["items"])    
        df_market["date"]=pd.to_datetime(df_market["date"].str[0:-3], format='%Y-%m-%dT%H:%M:%S.%f')
        df_market["date"]=df_market["date"].dt.tz_localize(None)
        #df_market.drop(columns = ['period','periodType'],inplace=True)
    
        try:
            suplydemand = pd.DataFrame()
            
            for hour in range(24):
    
                print(hour)
                current_datetime = date1.replace(hour=hour)
                current_datetime = current_datetime.strftime("%Y-%m-%dT%H:%M:%S%z")
                current_datetime = current_datetime[:19] + current_datetime[-5:-2] + ":" + current_datetime[-2:]
                payload = {"date": current_datetime}
                sleep(1)
                print(payload)
                resp1 = req.post(suplydemand_url,json=payload, headers=headers, timeout=15)
                st.write(current_datetime)
                hourdata=pd.DataFrame(resp1.json()["items"])
                suplydemand = pd.concat([suplydemand, hourdata], ignore_index=True)
    
            suplydemand["date"]=pd.to_datetime(suplydemand["date"].str[0:-3], format='%Y-%m-%dT%H:%M:%S.%f')
            suplydemand["date"]=suplydemand["date"].dt.tz_localize(None)
            suplydemand['hour']=suplydemand["date"].apply(lambda x:x.hour)
            suplydemand["kesisim"]=suplydemand["demand"]+suplydemand["supply"]
            sleep(1) 
    
        except:
            print("Arz-Talep okunamadı")
    
        demand_pv=pd.pivot_table(suplydemand, values='demand', index=['price'], columns=['hour'], aggfunc=np.mean)
        demand_pv=demand_pv.interpolate(method='index')#fark interpolasyonları bul #deneme2=x.interpolate(method='values')#aynısı
    
        suply_pv=pd.pivot_table(suplydemand, values='supply', index=['price'], columns=['hour'], aggfunc=np.mean)
        suply_pv=suply_pv.interpolate(method='index')#fark interpolasyonları bul #deneme2=x.interpolate(method='values')#aynısı
        
        kesinti=pd.DataFrame()
        kesinti["Date"] = df_blok["date"].dt.date
        kesinti["Hour"] = df_blok["date"].dt.hour
        kesinti['Saatlik FBA']=demand_pv.iloc[-1]-df_blok["amountOfPurchasingTowardsMatchedBlock"]
        
        kesinti["Saatlik Eşleşen Alış"]=df_market["matchedBids"]-df_blok["amountOfPurchasingTowardsMatchedBlock"]
    
        kesinti["Kesinti"]=kesinti["Saatlik Eşleşen Alış"]-kesinti['Saatlik FBA']
    
        kesinti["Kesinti"] = kesinti["Kesinti"].apply(lambda x: x if x < 0 else 0)
    
        kesinti["KesintiOranı"]=kesinti["Kesinti"]/kesinti['Saatlik FBA']
    
        all_data = pd.concat([all_data, kesinti])
    
        # Move to the next day
        date1 += timedelta(days=1)
        print(date1)

    sleep(1)  
    return all_data    

#%%tarih seç date1
yesterday = datetime.date.today() - datetime.timedelta(days=1)
date1 = st.date_input('Gün 1',value=yesterday)
date1 = datetime.datetime(date1.year, date1.month, date1.day).replace(hour=0, minute=0, second=0)
local_timezone = pytz.timezone('Europe/Istanbul')
date1 = date1.astimezone(local_timezone)
date1=date1.replace(hour=0)

#%%date2

date2 = st.date_input('Gün 2',value=yesterday)
date2 = datetime.datetime(date2.year, date2.month, date2.day, 0, 0, 0)
local_timezone = pytz.timezone('Europe/Istanbul')
date2 = date2.astimezone(local_timezone)
date2=date2.replace(hour=0)

# Define the URL endpoints
suplydemand_url = "https://seffaflik.epias.com.tr/electricity-service/v1/markets/dam/data/supply-demand"
block_url = "https://seffaflik.epias.com.tr/electricity-service/v1/markets/dam/data/amount-of-block-buying"
marketvolume_url = "https://seffaflik.epias.com.tr/electricity-service/v1/markets/dam/data/clearing-quantity"

#%%
auth_url = "https://giris.epias.com.tr/cas/v1/tickets"  # TGT almak için kullanacağınız URL
auth_payload = "username=mustafayarici@embaenergy.com&password=Seffaf.0634"
auth_headers = {"Content-Type": "application/x-www-form-urlencoded","Accept": "text/plain"}

#%%

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

all_data = loading(date1,date2)

# Reset the index of the combined dataframe
all_data.reset_index(drop=True, inplace=True)

# Print the final dataframe containing all the data
all_data.iloc[:,2:4]=all_data.iloc[:,2:4].round(2)

#%%
st.download_button(
   "Veri İndir",
   all_data.to_csv(sep=";", decimal=",",index=False).encode('utf-8-sig'),
   "Kesinti Verileri.csv",
   "text/csv",
   key='download-Kesinti'
)
