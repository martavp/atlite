#!/usr/bin/env python
# coding: utf-8
#%%
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib

# IRENA Renewable Statistics https://www.irena.org/Publications/2024/Jul/Renewable-energy-statistics-2024

data_capacity_IRENA = pd.read_csv('data/RECAP_20231018-202343.csv',
                         index_col=(0,1), header=1, skiprows=0, 
                         sep=',', encoding='latin') 
data_capacity_IRENA.columns=pd.to_numeric(data_capacity_IRENA.columns)

data_generation_IRENA = pd.read_csv('data/RE-ELECGEN_20231018-202430.csv',
                         index_col=(0,1), header=1, skiprows=0, 
                         sep=',', encoding='latin') 
data_generation_IRENA.columns=pd.to_numeric(data_generation_IRENA.columns)

#%%
#Updated IRENA datafile
data_IRENA = pd.read_excel('data/IRENA_Stats_extract_2024 H2.xlsx',
                          sheet_name='All data',
                          header=1) 
#%%
# Former BP statistics, https://www.energyinst.org/statistical-review
filename = 'data/EI-Stats-Review-All-Data.xlsx' 

data_capacity_pv = pd.read_excel(filename,
                         sheet_name='Solar Installed Capacity',
                         index_col=0, header=3) 
data_generation_pv = pd.read_excel(filename,
                         sheet_name='Solar Generation - TWh',
                         index_col=0, header=2) 

data_capacity_wind = pd.read_excel(filename,
                         sheet_name='Wind Installed Capacity',
                         index_col=0, header=3) 
data_generation_wind = pd.read_excel(filename,
                         sheet_name='Wind Generation - TWh',
                         index_col=0, header=2) 


countries_pv=[
        'Austria',
       'Belgium',
      'Bulgaria',
#'Czech Republic',
       'Denmark',
        'France',
       'Germany',
        'Greece',
       'Hungary',
         'Italy',
   'Netherlands',
        'Poland',
      'Portugal',
       'Romania',
      'Slovakia',
         'Spain',
        'Sweden',
   'Switzerland',
'United Kingdom',
#'Total Europe',
]

countries_wind=[
'Austria',
    'Belgium',
   'Bulgaria',
    'Denmark',
    'Finland',
     'France',
    'Germany',
     'Greece',
    'Ireland',
      'Italy',
'Netherlands',
     'Norway',
     'Poland',
   'Portugal',
    'Romania',
      'Spain',
     'Sweden',
'United Kingdom',
#'Total Europe',
]

years=np.arange(2015,2022) #data available from 2009 but only data from 2015 is considered 
CF_pv=pd.DataFrame(index=years, columns=countries_pv)
CF_wind=pd.DataFrame(index=years, columns=countries_wind)
CF_pv_IRENA=pd.DataFrame(index=years, columns=countries_pv)
CF_wind_IRENA=pd.DataFrame(index=years, columns=countries_wind)

for country in countries_pv:
    capacity_pv=0.001*data_capacity_pv.loc[country,years] #MW -> GW
    generation_pv=1000*data_generation_pv.loc[country,years] #TWh -> GWh
    CF_pv[country]=(1/8760)*generation_pv/capacity_pv
    CF_pv_IRENA[country]=(1/8760)*1000*data_generation_IRENA.loc[(country,'Solar photovoltaic'),years]/data_capacity_IRENA.loc[(country,'Solar photovoltaic'),years]
    
for country in countries_wind:    
    capacity_wind=0.001*data_capacity_wind.loc[country,years] #MW -> GW
    generation_wind=1000*data_generation_wind.loc[country,years] #TWh -> GWh
    CF_wind[country]=(1/8760)*generation_wind/capacity_wind
    CF_wind_IRENA[country]=(1/8760)*1000*data_generation_IRENA.loc[(country,'Wind'),years]/data_capacity_IRENA.loc[(country,'Wind'),years]
    
#%%
plt.figure(figsize=(8, 4))
gs1 = gridspec.GridSpec(1, 20)
gs1.update(wspace=0.4, hspace=0.2)
ax1 = plt.subplot(gs1[0,0:19])
ax2 = plt.subplot(gs1[0,19])

ax1.boxplot(CF_pv[countries_pv], showfliers=False, medianprops=dict(color='black'))
ax1.set_ylabel('Capacity factor PV')
ax1.set_xticks(np.arange(1,len(countries_pv)+1),countries_pv, rotation=45)
cmap = matplotlib.colormaps.get_cmap('autumn')

for i,year in enumerate(years):
    ax1.plot(np.arange(1,len(countries_pv)+1), CF_pv.loc[year,countries_pv], linewidth=0,
             marker='o', markersize=5, color=cmap(i/len(years)))
    ax1.plot(np.arange(1,len(countries_pv)+1)+0.3, CF_pv_IRENA.loc[year,countries_pv], linewidth=0,
               marker='o', markersize=5, markerfacecolor='white', markeredgecolor=cmap(i/len(years)))
cb = matplotlib.colorbar.ColorbarBase(ax2, cmap=cmap)
ax2.set_yticks([0,1], [years[0],years[-1]])
plt.savefig('figures/cf_pv_historical.jpg', 
             dpi=300, bbox_inches='tight')

#%%
plt.figure(figsize=(8, 4))
gs1 = gridspec.GridSpec(1, 20)
gs1.update(wspace=0.4, hspace=0.2)
ax1 = plt.subplot(gs1[0,0:19])
ax2 = plt.subplot(gs1[0,19])

ax1.boxplot(CF_wind[countries_wind], showfliers=False, medianprops=dict(color='black'))
ax1.set_ylabel('Capacity factor wind')
ax1.set_xticks(np.arange(1,len(countries_wind)+1),countries_wind, rotation=45)
cmap = matplotlib.colormaps.get_cmap('viridis')

for i,year in enumerate(years):
    ax1.plot(np.arange(1,len(countries_wind)+1), CF_wind.loc[year,countries_wind], linewidth=0,
              marker='o', markersize=5, color=cmap(i/len(years)))
    ax1.plot(np.arange(1,len(countries_wind)+1)+0.3, CF_wind_IRENA.loc[year,countries_wind], linewidth=0,
              marker='o', markersize=5, markerfacecolor='white', markeredgecolor=cmap(i/len(years)))
cb = matplotlib.colorbar.ColorbarBase(ax2, cmap=cmap)
ax2.set_yticks([0,1], [years[0],years[-1]])
plt.savefig('figures/cf_wind_historical.jpg', 
              dpi=300, bbox_inches='tight')

