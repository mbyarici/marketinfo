# -*- coding: utf-8 -*-
"""
Created on Thu Nov 23 08:13:03 2023

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
    page_title="Arz - Talep",
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

print("push") 
#%%arz talep cash
@st.cache_data  # Allow caching DataFrame
def loading(date1):

    suplydemand_url= "https://seffaflik.epias.com.tr/electricity-service/v1/markets/dam/data/supply-demand"
    try:
        suplydemand = pd.DataFrame()
        
        for hour in range(24):

            print(hour)
            current_datetime = date1.replace(hour=hour)
            current_datetime = current_datetime.strftime("%Y-%m-%dT%H:%M:%S%z")
            current_datetime = current_datetime[:19] + current_datetime[-5:-2] + ":" + current_datetime[-2:]
            
            
            payload = {"date": current_datetime}
            resp1 = req.post(suplydemand_url,json=payload, headers=headers, timeout=15)
            hourdata=pd.DataFrame(resp1.json()["items"])
            suplydemand = pd.concat([suplydemand, hourdata], ignore_index=True)

        suplydemand["date"]=pd.to_datetime(suplydemand["date"].str[0:-3], format='%Y-%m-%dT%H:%M:%S.%f')
        suplydemand["date"]=suplydemand["date"].dt.tz_localize(None)
        suplydemand['hour']=suplydemand["date"].apply(lambda x:x.hour)
        suplydemand["kesisim"]=suplydemand["demand"]+suplydemand["supply"]

    except:
        st.write("Arz-Talep okunamadı")
        
    #diff_pv=pd.pivot_table(suplydemand, values='kesisim', index=['price'], columns=['hour'], aggfunc=np.mean)
    #diff_pv=diff_pv.interpolate(method='index')#fark interpolasyonları bul #deneme2=x.interpolate(method='values')#aynısı    
    return suplydemand#,diff_pv        

#%%

print("push") 
 
date1 = st.date_input('Baz gün',value=date.today())
print(date1)

# Create a datetime object with the selected date and desired time (00:00:00)
selected_datetime = datetime.datetime(date1.year, date1.month, date1.day, 0, 0, 0)

# Get your local time zone (Istanbul)
local_timezone = pytz.timezone('Europe/Istanbul')

# Convert the datetime object to your local time zone (optional)
date1 = selected_datetime.astimezone(local_timezone)

print(date1)

#%%
auth_url = "https://giris.epias.com.tr/cas/v1/tickets"  # TGT almak için kullanacağınız URL
auth_payload = "username=mustafayarici@embaenergy.com&password=Seffaf.3406"
auth_headers = {"Content-Type": "application/x-www-form-urlencoded","Accept": "text/plain"}

# TGT isteğini yap
try:
    auth_response = req.post(auth_url, data=auth_payload, headers=auth_headers)
    auth_response.raise_for_status()  # Eğer istek başarısız olursa hata fırlatır
    tgt = auth_response.text  # TGT'yi yanıt metninden al
    print("TGT : başarılı")
except Exception as e:
    print("TGT alma hatası:", e)
    tgt = None  # TGT alınamazsa devam edemeyiz  


payload = {
        "date": date1,
    }#kullanılmayan
headers = {
        "TGT": tgt,  # Aldığımız TGT burada kullanılıyor
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

#%%

# Cache teki arz talebi değiştir. 
suplydemand = loading(date1)#,diff_pv        
        
# Number of columns in each row
num_cols = 3

# Get unique hours in the DataFrame
unique_hours = suplydemand["hour"].unique()

# Calculate the number of rows needed
num_rows = (len(unique_hours) - 1) // num_cols + 1  

suplydemand["kesisim"] = suplydemand["kesisim"].round(6)
result_df = pd.DataFrame(columns=["Saat", "Fiyat"])
asgari=0
azami=3000

default_columns = [f"saat{i}" for i in range(24)]
default = pd.DataFrame(0, index=range(1), columns=default_columns)
st.title("Değişim değerleri girebilirsiniz. Arzı artırmak için :(-): / Talebi artırmak için :(+)")

edited_df = st.data_editor(default)
edited_df=edited_df.fillna(0)

def intersection(hour_data):   
    hour_data=hour_data.reset_index(drop=True)
    hour_data["kesisim"]=hour_data["kesisim"]+edited_df.loc[0,'saat'+str(hour_data["hour"].iloc[0])]
    abs_hour_data=hour_data.copy()
    abs_hour_data["kesisim"]=abs_hour_data["kesisim"].abs()
    abs_index=abs_hour_data["kesisim"].idxmin()

    
    if hour_data["kesisim"].loc[abs_index]>0 and hour_data["kesisim"][0]>0:#arz fazlası sebebiyle fiyat 0 çıkıyosa başka adıma git

        while hour_data["kesisim"].loc[abs_index]==hour_data["kesisim"].shift(-1, axis = 0).loc[abs_index]:
            abs_index=abs_index+1


        xp =[hour_data["kesisim"].loc[abs_index],hour_data["kesisim"].shift(+1, axis = 0).loc[abs_index]]
        fp=[hour_data["price"].loc[abs_index],hour_data["price"].shift(+1, axis = 0).loc[abs_index]]
        tempptf=np.interp(0, xp, fp)

    elif hour_data["price"].loc[abs_index]== azami:#fiyat arz yetmezliği sebebiyle maks çıktıysa
        #print(azami)
        tempptf=azami
    
    elif hour_data["price"].loc[abs_index]== asgari:#arz fazlası fiyat 0 ise burası
        #print(asgari)
        tempptf=asgari
    
    else:
        #print("alt")
        xp =[hour_data["kesisim"].loc[abs_index],hour_data["kesisim"].shift(+1, axis = 0).loc[abs_index]]
        fp=[hour_data["price"].loc[abs_index],hour_data["price"].shift(+1, axis = 0).loc[abs_index]]
        fp.sort()
        xp.sort()
        tempptf=np.interp(0, xp, fp)
        tempptf=tempptf.round(2)
    return tempptf,hour_data



ptf_df = pd.DataFrame(columns=["Saat", "Fiyat"])
# Loop through the rows and columns
for row in range(num_rows):
    cols = st.columns(num_cols)
    for col_idx in range(num_cols):
        idx = row * num_cols + col_idx
        if idx < len(unique_hours):
            hour = unique_hours[idx]
            hour_data = suplydemand[suplydemand["hour"] == hour]
            
            intersection_price,hour_data=intersection(hour_data)
            
            
            new_row = pd.DataFrame({"Saat": [hour], "Fiyat": [intersection_price]})
            ptf_df = pd.concat([ptf_df, new_row], ignore_index=True)
            
            #ptf_df = ptf_df.append({"Saat": hour, "Fiyat": intersection_price}, ignore_index=True)
            with cols[col_idx]:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=hour_data["kesisim"], y=hour_data["price"], mode="lines", name=f"Saat {hour}"))
                # Add a horizontal line at y=0
                fig.add_shape(
                    go.layout.Shape(
                        type="line",
                        x0=0,
                        x1=0,
                        y0=hour_data["kesisim"].min(),
                        y1=hour_data["kesisim"].max(),
                        line=dict(color="red", width=2),
                    )
                )
                fig.update_layout(title=f"Saat {hour} PTF: {intersection_price}", xaxis_title="Miktar (MWh)", yaxis_title="Fiyat (TL/MWh)")
                #st.write(edited_df.loc[0,'saat'+str(hour_data["hour"].iloc[0])])
                st.plotly_chart(fig)
 
#col1
            
st.dataframe(ptf_df,height=880)                
st.download_button(
   "İndir",
   ptf_df.to_csv(sep=";", decimal=",",index=False).encode('utf-8-sig'),
   "PTF.csv",
   "text/csv",
   key='download-PTF'
)

#%%
#tablolar

#%%
# Format the date string with time zone offset
date1 = date1.strftime("%Y-%m-%dT%H:%M:%S%z")
date1 = date1[:19] + date1[-5:-2] + ":" + date1[-2:]
payload = {"startDate": date1, "endDate": date1 }

#%%blok buy
block_buy_url = "https://seffaflik.epias.com.tr/electricity-service/v1/markets/dam/data/amount-of-block-buying"
blok_resp_buy = req.post(block_buy_url, json=payload, headers=headers)
df_blok_buy=pd.DataFrame(blok_resp_buy.json()["items"])
df_blok_buy["date"]=pd.to_datetime(df_blok_buy["date"].str[0:-3], format='%Y-%m-%dT%H:%M:%S.%f')
df_blok_buy["date"]=df_blok_buy["date"].dt.tz_localize(None)

#%% block sale
block_sale_url= "https://seffaflik.epias.com.tr/electricity-service/v1/markets/dam/data/amount-of-block-selling"
blok_resp_sale = req.post(block_sale_url, json=payload, headers=headers)
df_blok_sale=pd.DataFrame(blok_resp_sale.json()["items"])
df_blok_sale["date"]=pd.to_datetime(df_blok_sale["date"].str[0:-3], format='%Y-%m-%dT%H:%M:%S.%f')
df_blok_sale["date"]=df_blok_sale["date"].dt.tz_localize(None)

#%%
#
#supply
#
#%%
suply_pv=pd.pivot_table(suplydemand, values='supply', index=['price'], columns=['hour'], aggfunc=np.mean)
suply_pv=suply_pv.interpolate(method='index')#fark interpolasyonları bul #deneme2=x.interpolate(method='values')#aynısı

#%%
suplysummery=pd.DataFrame()
suplysummery['FBS']=suply_pv.iloc[0]*-1
suplysummery['FBS']=suplysummery['FBS']-df_blok_sale['amountOfSalesTowardsMatchedBlock']
suplysummery['BlokEşleşme']=df_blok_sale['amountOfSalesTowardsMatchedBlock']

#%%
suply_diff=-suply_pv+suply_pv.shift(1, axis = 0)
suply_diff.iloc[0]=suply_pv.iloc[0]*-1
suply_diff=suply_diff.round(0).astype(int)
suply_diff["price_level"]=suply_diff.index# indexteki fiyat kolona yaz

#%%
suplysummery['0-300TL']=suply_diff[(suply_diff['price_level'] > 0) & (suply_diff['price_level'] <= 300)].sum()
suplysummery['300-600TL']=suply_diff[(suply_diff['price_level'] > 300) & (suply_diff['price_level'] <= 600)].sum()
suplysummery['600-1000']=suply_diff[(suply_diff['price_level'] > 600) & (suply_diff['price_level'] <= 1000)].sum()
suplysummery['1000-1500TL']=suply_diff[(suply_diff['price_level'] > 1000) & (suply_diff['price_level'] <= 1500)].sum()
suplysummery['1500-1750TL']=suply_diff[(suply_diff['price_level'] > 1500) & (suply_diff['price_level'] <= 1750)].sum()
suplysummery['1750-2000TL']=suply_diff[(suply_diff['price_level'] > 1750) & (suply_diff['price_level'] <= 2000)].sum()
suplysummery['2000-2250']=suply_diff[(suply_diff['price_level'] > 2000) & (suply_diff['price_level'] <= 2250)].sum()
suplysummery['2250-2500']=suply_diff[(suply_diff['price_level'] > 2250) & (suply_diff['price_level'] <= 2500)].sum()
suplysummery['2500-3000']=suply_diff[(suply_diff['price_level'] > 2500) & (suply_diff['price_level'] <= 3000)].sum()
suplysummery.iloc[:,0:2]=suplysummery.iloc[:,0:2].round(0)

#%%
st.dataframe(suplysummery,height=600,use_container_width=True)
st.download_button(
   "Arz İndir",
   suplysummery.to_csv(sep=";", decimal=",").encode('utf-8-sig'),
   "Arz Tablo.csv",
   "text/csv",
   key='download-ArzTablo'
)

#%%
#
#demand
#
demand_pv=pd.pivot_table(suplydemand, values='demand', index=['price'], columns=['hour'], aggfunc=np.mean)
demand_pv=demand_pv.interpolate(method='index')

#%%
demand_diff=demand_pv.shift(1, axis = 0)-demand_pv
demand_diff.iloc[0]=demand_pv.iloc[0]
demand_diff=demand_diff.round(0).astype(int)
demand_diff["price_level"]=demand_diff.index# indexteki fiyat kolona yaz

#%%
demandsummery=pd.DataFrame()
demandsummery['MaksAlış']=demand_diff.iloc[0]

demandsummery['0-600TL']=demand_diff[(demand_diff['price_level'] > 0) & (demand_diff['price_level'] <= 600)].sum()
demandsummery['600-1000TL']=demand_diff[(demand_diff['price_level'] > 600) & (demand_diff['price_level'] <= 1000)].sum()
demandsummery['1000-1250TL']=demand_diff[(demand_diff['price_level'] > 1000) & (demand_diff['price_level'] <= 1250)].sum()
demandsummery['1250-1500TL']=demand_diff[(demand_diff['price_level'] > 1250) & (demand_diff['price_level'] <= 1500)].sum()
demandsummery['1500-1750TL']=demand_diff[(demand_diff['price_level'] > 1500) & (demand_diff['price_level'] <= 1750)].sum()
demandsummery['1750-2000TL']=demand_diff[(demand_diff['price_level'] > 1750) & (demand_diff['price_level'] <= 2000)].sum()
demandsummery['2000-2250TL']=demand_diff[(demand_diff['price_level'] > 2000) & (demand_diff['price_level'] <= 2250)].sum()
demandsummery['2250-2500TL']=demand_diff[(demand_diff['price_level'] > 2250) & (demand_diff['price_level'] <= 2500)].sum()
demandsummery['2500-2750TL']=demand_diff[(demand_diff['price_level'] > 2500) & (demand_diff['price_level'] <= 2750)].sum()
demandsummery['2750TL Üzeri']=demand_diff[(demand_diff['price_level'] > 2750) ].sum()
demandsummery.drop('price_level',inplace=True)

st.dataframe(demandsummery,height=600,use_container_width=True)
st.download_button(
   "Talep İndir",
   demandsummery.to_csv(sep=";", decimal=",").encode('utf-8-sig'),
   "Talep Tablo.csv",
   "text/csv",
   key='download-TalepTablo'
)

#%%
diff_pv=pd.pivot_table(suplydemand, values='kesisim', index=['price'], columns=['hour'], aggfunc=np.mean)
diff_pv=diff_pv.interpolate(method='index')#fark interpolasyonları bul #deneme2=x.interpolate(method='values')#aynısı  
diff_pv=diff_pv.round(2)
#diff_pv.iloc[:,0:24]=diff_pv.iloc[:,0:24].round(2)
#%%

st.download_button(
   "Fark İndir",
   diff_pv.to_csv(sep=";", decimal=",").encode('utf-8-sig'),
   "Fark.csv",
   "text/csv",
   key='download-FarkTablo'
)






