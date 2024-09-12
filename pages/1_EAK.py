# -*- coding: utf-8 -*-
"""
Created on Thu Sep 12 10:46:44 2024

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
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.set_page_config(page_title="EAK", page_icon=":chart_with_upwards_trend:", layout="wide")

st.markdown(hide_st_style, unsafe_allow_html=True)








#%%cash
@st.cache_data  # Allow caching DataFrame
def loading(date1,date2):

    print("döngü")
    eak=pd.DataFrame()
    for i in eaklist['organizationId']:
        st.write(date1," - ",date2)
        temporg=eaklist[eaklist['organizationId']==i]
        
        payload = {
                "startDate": date1,
                "endDate": date2,
                "region": "TR1",
                "organizationId": i
            }
        headers = {
                "TGT": tgt,  # Aldığımız TGT burada kullanılıyor
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        print("try")
    
        try:        
            print("try1")
            resp_aic = req.post(url_aic, json=payload, headers=headers, timeout=15)
            print(str(i)+" başarılı")
            sleep(1)
        except:
            try:
                print("try2")
                resp_aic = req.post(url_aic, json=payload, headers=headers, timeout=15)
                print(str(i)+" başarılı"+ "deneme2")
                sleep(1)
            except:
                try:
                    print("try3")
                    resp_aic = req.post(url_aic, json=payload, headers=headers, timeout=15)
                    print(str(i)+" başarılı"+ "deneme3")
                    sleep(1)
                except:
                    try:
                        print("try4")
                        resp_aic = req.post(url_aic, json=payload, headers=headers, timeout=15)
                        print(str(i)+" başarılı"+ "deneme4")
                        sleep(1)
                    except:
                        try:
                            print("try5")
                            resp_aic = req.post(url_aic, json=payload, headers=headers, timeout=15)
                            print(str(i)+" başarılı"+ "deneme5")
                            sleep(1)
                        except:
                            print(str(i)+" hatalı eak")
                            sleep(1)
                            pass
    
        if not pd.DataFrame(resp_aic.json()["items"]).empty:
            temp_eak=pd.DataFrame(resp_aic.json()["items"])
            temp_eak['organizationId']=i
            temp_eak=temp_eak.merge(temporg, how='left',on=['organizationId'])
            eak=pd.concat([eak, temp_eak])
        print(str(i)+" eak")
        st.write(eak.head(3))
        sleep(1)  
    return eak#,diff_pv      



#%%tgt
auth_url = "https://giris.epias.com.tr/cas/v1/tickets"  # TGT almak için kullanacağınız URL
auth_payload = "username=mustafayarici@embaenergy.com&password=Seffaf.3406"
auth_headers = {"Content-Type": "application/x-www-form-urlencoded","Accept": "text/plain"}

#%%
try:
    auth_response = req.post(auth_url, data=auth_payload, headers=auth_headers)
    auth_response.raise_for_status()  # Eğer istek başarısız olursa hata fırlatır
    tgt = auth_response.text  # TGT'yi yanıt metninden al
    print("TGT : başarılı")
except Exception as e:
    print("TGT alma hatası:", e)
    tgt = None  # TGT alınamazsa devam edemeyiz


#%% eak sorgu listesi ve link
url_aic="https://seffaflik.epias.com.tr/electricity-service/v1/generation/data/aic"
eaklist=pd.DataFrame(pd.read_excel("eaklist.xlsx", "secim",index_col=None, na_values=['NA']))


#%%tarih seç date1

date1 = st.date_input('Gün 1',value=date.today())
date1 = datetime.datetime(date1.year, date1.month, date1.day).replace(hour=0, minute=0, second=0)
local_timezone = pytz.timezone('Europe/Istanbul')
date1 = date1.astimezone(local_timezone)
date1=date1.replace(hour=0)
date1 = date1.strftime("%Y-%m-%dT%H:%M:%S%z")
date1 = date1[:19] + date1[-5:-2] + ":" + date1[-2:]

#%%date2

date2 = st.date_input('Gün 2',value=date.today())
date2 = datetime.datetime(date2.year, date2.month, date2.day, 0, 0, 0)
local_timezone = pytz.timezone('Europe/Istanbul')
date2 = date2.astimezone(local_timezone)
date2=date2.replace(hour=0)
date2 = date2.strftime("%Y-%m-%dT%H:%M:%S%z")
date2 = date2[:19] + date2[-5:-2] + ":" + date2[-2:]

"""
#%%
print("döngü")
eak=pd.DataFrame()
for i in eaklist['organizationId']:
    temporg=eaklist[eaklist['organizationId']==i]
    st.write(date1," - ",date2)
    payload = {
            "startDate": date1,
            "endDate": date2,
            "region": "TR1",
            "organizationId": i
        }
    headers = {
            "TGT": tgt,  # Aldığımız TGT burada kullanılıyor
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    print("try")

    try:        
        print("try1")
        resp_aic = req.post(url_aic, json=payload, headers=headers, timeout=15)
        print(str(i)+" başarılı")
        sleep(1)
    except:
        try:
            print("try2")
            resp_aic = req.post(url_aic, json=payload, headers=headers, timeout=15)
            print(str(i)+" başarılı"+ "deneme2")
            sleep(1)
        except:
            try:
                print("try3")
                resp_aic = req.post(url_aic, json=payload, headers=headers, timeout=15)
                print(str(i)+" başarılı"+ "deneme3")
                sleep(1)
            except:
                try:
                    print("try4")
                    resp_aic = req.post(url_aic, json=payload, headers=headers, timeout=15)
                    print(str(i)+" başarılı"+ "deneme4")
                    sleep(1)
                except:
                    try:
                        print("try5")
                        resp_aic = req.post(url_aic, json=payload, headers=headers, timeout=15)
                        print(str(i)+" başarılı"+ "deneme5")
                        sleep(1)
                    except:
                        print(str(i)+" hatalı kgüp")
                        sleep(1)
                        pass
             
   
    #print(pd.DataFrame(resp_dpp.json()["items"]))

    if not pd.DataFrame(resp_aic.json()["items"]).empty:
        temp_eak=pd.DataFrame(resp_aic.json()["items"])
        temp_eak['organizationId']=i
        temp_eak=temp_eak.merge(temporg, how='left',on=['organizationId'])
        eak=pd.concat([eak, temp_eak])
    print(str(i)+" eak")
    st.info(eak.head(3))
    sleep(1)

"""


eak = loading(date1,date2)


st.dataframe(eak.head(5),height=600,use_container_width=True)

#%%

eak["date"]=pd.to_datetime(eak["date"].str[0:-3], format='%Y-%m-%dT%H:%M:%S.%f')
eak["date"]=eak["date"].dt.tz_localize(None)
eak['shortdate']=eak['date'].dt.date

#%%
st.download_button(
   "Veri İndir",
   eak.to_csv(sep=";", decimal=",",index=False).encode('utf-8-sig'),
   "EAK Verileri.csv",
   "text/csv",
   key='download-EAK'
)  