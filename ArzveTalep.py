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

#%%sayfa düzeni
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.set_page_config(page_title="Arz -Talep", page_icon=":chart_with_upwards_trend:", layout="wide")

st.markdown(hide_st_style, unsafe_allow_html=True)

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

# Format the date string with time zone offset
#date1 = selected_datetime_local.strftime("%Y-%m-%dT%H:%M:%S%z")
#date1 = date1[:19] + date1[-5:-2] + ":" + date1[-2:]

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
    }
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



