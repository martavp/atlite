#!/usr/bin/env python
# coding: utf-8

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib
import seaborn as sb

data_capacity_pv = pd.read_excel('data/Statistical Review of World Energy Data.xlsx',
                         sheet_name='Solar Capacity',
                         index_col=0, header=3) 
data_generation_pv = pd.read_excel('data/Statistical Review of World Energy Data.xlsx',
                         sheet_name='Solar Generation - TWh',
                         index_col=0, header=2) 

data_capacity_wind = pd.read_excel('data/Statistical Review of World Energy Data.xlsx',
                         sheet_name='Wind Capacity',
                         index_col=0, header=3) 
data_generation_wind = pd.read_excel('data/Statistical Review of World Energy Data.xlsx',
                         sheet_name='Wind Generation - TWh',
                         index_col=0, header=2) 


countries_pv=[
        'Austria',
       'Belgium',
      'Bulgaria',
'Czech Republic',
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
'Total Europe',]

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
'Total Europe',]

years=np.arange(2015,2023) #data available from 1009 but only data from 2015 is considered 
CF_pv=pd.DataFrame(index=years, columns=countries_pv)
CF_wind=pd.DataFrame(index=years, columns=countries_wind)

for country in countries_pv:
    capacity_pv=0.001*data_capacity_pv.loc[country,years] #MW -> GW
    generation_pv=1000*data_generation_pv.loc[country,years] #TWh -> GWh
    CF_pv[country]=(1/8760)*generation_pv/capacity_pv

for country in countries_wind:    
    capacity_wind=0.001*data_capacity_wind.loc[country,years] #MW -> GW
    generation_wind=1000*data_generation_wind.loc[country,years] #TWh -> GWh
    CF_wind[country]=(1/8760)*generation_wind/capacity_wind
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
cb = matplotlib.colorbar.ColorbarBase(ax2, cmap=cmap)
ax2.set_yticks([0,1], [years[0],years[-1]])
plt.savefig('figures/cf_wind_historical.jpg', 
             dpi=300, bbox_inches='tight')




