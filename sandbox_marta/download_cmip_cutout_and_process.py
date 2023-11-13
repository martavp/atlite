#!/usr/bin/env python
# coding: utf-8

import sys #to use files in git_repos folder
sys.path.insert(0,'/media/sf_Dropbox/AU/GIT_REPOS/atlite')

from atlite.datasets.era5 import retrieve_data, _rename_and_clean_coords, retrieval_times, _area
import xarray as xr
import atlite
import logging
import cdsapi
import geopandas as gpd
import matplotlib.pyplot as plt
from cartopy.io import shapereader
import cartopy.crs as ccrs
import numpy as np
import pandas as pd
logging.basicConfig(level=logging.INFO)

#%%
"""
1. Donwload cmip6 cutouts from ESGF. 
Script based on Oveweh PR

TODO 1: solve error message 
ctx = conn.new_context(facets='project,experiment_id')
Only the facets that you specify will be present in the facets_counts dictionary

TODO 2: Try downloading different climate models 

TODO 3: Decide which variant_label to use
"""
# 'source_id': model names in Table Hamann et al 2022
# experiment_id : ssp585 es RCP8.5
# it seems that I don't need to specify the data_node
# do I need to specify the variant_label?


def retrieve_cutout_cmip6(filename, year, esgf_params):
    
    cutout_cmip = atlite.Cutout(path=filename,
                                module=['cmip'],
                                x=slice(-13,45),
                                y=slice(32,83),
                                time=str(year)+'-01',
                                esgf_params=esgf_params,
                                dt='3H',dx=1, dy=1)
    # dt='3H'

    # ds = xr.Dataset(
    #         {
    #         "x": np.round(np.arange(-180, 180, 1), 9),
    #         "y": np.round(np.arange(-90, 90, 1), 9),
    #         "time": pd.date_range(start='2015', end='2100', freq=dt),})

    cutout_cmip.prepare()

    # cutout_cmip.data
    return cutout_cmip

esgf_params = {
   'data_node': 'esgf-cnr.hpc.cineca.it',
   'source_id': 'EC-Earth3',
   'variant_label':'r4i1p1f1',
   'experiment_id': 'ssp585',
   'project' : 'CMIP6',
   'frequency':['3hr','6hr']
}

cutout_cmip=retrieve_cutout_cmip6(filename='cutouts_cmip6/EC-Earth3/cmip_europe_2035.nc',
                      esgf_params=esgf_params, year=2035)

#%%
"""
2. Download geometry of Europan countries and join. 
This can later be used as shapes when converting the weather variables in the 
cutout to solar, wind and hydro power. 

"""
def natural_earth_shapes_EU(join_dict, drop_non_Europe=['MA','DZ','TN','GI']):
    # Download shape file (high resolution)
    shpfilename = shapereader.natural_earth(resolution='10m',
                                          category='cultural',
                                          name='admin_1_states_provinces')
    
    df =gpd.read_file(shpfilename)
    df = df.cx[-13:32,35:80]
    df = df[['iso_a2','geometry']]
    df = df.dissolve('iso_a2')
    df.index = list(df.index)
    drop_regions = drop_non_Europe
    # Absorbe microstates
    for main_r,sub_rs in join_dict.items():
        temp_main = df.loc[main_r,'geometry']
        for sub_r in sub_rs:
            drop_regions.append(sub_r)
            temp_r = df.loc[sub_r,'geometry']
        
            temp_main = temp_main.union(temp_r)
        temp_main = gpd.GeoSeries([temp_main])
        df.loc[[main_r],'geometry'] = temp_main.values
    
    df = df.drop(index=drop_regions)
    return df

# Create Europe shapefile
join_dict = {'FR':['GG','AD','MC'],
             'IT':['VA','SM'], 
             'GB':['JE','IM'],
             'FI':['AX'],
             'DK':['FO'],
             'CH':['LI'], 
             'BE':['LU'],
             'RS':['XK']}
europe = natural_earth_shapes_EU(join_dict)

#%%%
"""
2b. Alternative to 2 in wich only the geometry of a country is loaded.
"""
#Define country and shapes
shpfilename = shapereader.natural_earth(resolution="10m", 
                                      category="cultural", 
                                      name="admin_0_countries")

reader = shapereader.Reader(shpfilename)

#country='Denmark'
Denmark = gpd.GeoSeries({r.attributes["NAME_EN"]: r.geometry for r in reader.records()},
    crs={"init": "epsg:4326"},).reindex(["Denmark"])


#%%
"""
3. Convert cutout to wind and solar CF, and plot maps with CF per gridcell.
"""
# Solar power CF per gridcell map
pv_cf = cutout_cmip.pv(panel="CSi", 
                       orientation={"slope": 30.0, "azimuth": 180.0},
                       capacity_factor=True)
pv_cf.plot(alpha=0.7, cmap='autumn')
plt.title('CF solar')
plt.savefig('figures/capacity_factor_solar.jpg', 
            dpi=300, bbox_inches='tight')

#%%
# Wind Capacity factor CMIP : the surface roughness is not available 
# from the CMIP database so ERA5 roughness is used instead.
# (ideally this step is removed and wind velocity is interpolated from the 
# wind speed at two closest heights)
c = cdsapi.Client()

c.retrieve(
    'reanalysis-era5-single-levels-monthly-means',
    {
        'format': 'netcdf',
        'product_type': 'monthly_averaged_reanalysis',
        'variable': 'forecast_surface_roughness',
        'year': '2019',
        'month': [
            '01', '02', '03',
            '04', '05', '06',
            '07', '08', '09',
            '10', '11', '12',
        ],
        'area': [
            83, -13, 32,
            45,
        ],
        'time': '00:00',
    },
    'roughness.nc')

from atlite.datasets.era5 import _rename_and_clean_coords
# Create roughness data based on 1 year average from ERA5. 
# Then interpolate the ERA5 data into the resolution of CMIP.

roughness = xr.open_dataset('roughness.nc')

roughness = roughness.rename({'fsr':'roughness'})

roughness = roughness.mean(dim='time')

roughness = _rename_and_clean_coords(roughness)
roughness.roughness.attrs['prepared_feature'] = 'wind'

da = roughness.roughness.interp_like(cutout_cmip.data['influx'].isel(time=0))

cutout_cmip.data = cutout_cmip.data.assign(roughness=da)

# Wind power CF per gridcell map
wind_cf = cutout_cmip.wind('Vestas_V112_3MW', 
                           capacity_factor=True)

wind_cf.plot(alpha=0.7, cmap='winter')
plt.title('CF wind')
plt.savefig('figures/capacity_factor_wind.jpg', 
            dpi=300, bbox_inches='tight')
#%%
"""
4. Convert weather variables in cutout into wind, solar and hydropower and
aggregate them on a country basis
This is done with shapes=europe.

"""
# Wind power time series per country
cp_wind = cutout_cmip.wind('Vestas_V112_3MW', 
                           shapes=europe, 
                           capacity_factor=True, 
                           per_unit=True
                           )    
fig,ax = plt.subplots(figsize=(8,5))
cp_wind.sel(dim_0='DE').plot()
plt.savefig('figures/germany_wind_timeseries.jpg', 
            dpi=300, bbox_inches='tight')

fig,ax = plt.subplots(subplot_kw=dict(projection=ccrs.PlateCarree()),
                      figsize=(8,10))
europe['mean_cp_wind'] = cp_wind.mean(dim='time')
europe.plot(column='mean_cp_wind', ax=ax, legend=True)
ax.set_title('Single January Mean wind capacites EC-Earth3')
plt.savefig('figures/Europe_wind_map.jpg', 
            dpi=300, bbox_inches='tight')
#%%
# Solar power time series per country
pv_cp = cutout_cmip.pv('CSi',
                        shapes=europe,
                        orientation={"slope": 30.0, "azimuth": 180.0},
                        #orientation='latitude_optimal', 
                        capacity_factor=True, 
                        per_unit=True)

fig,ax = plt.subplots(figsize=(8,5))
pv_cp.sel(dim_0='DE').plot()
plt.savefig('figures/germany_solar_timeseries.jpg', 
            dpi=300, bbox_inches='tight')

fig,ax = plt.subplots(subplot_kw=dict(projection=ccrs.PlateCarree()),
            figsize=(8,10))
europe['mean_cf_pv'] = pv_cp.mean(dim='time')
europe.plot(column='mean_cf_pv', ax=ax, legend=True)
ax.set_title('1 January Mean PV Solar EC-Earth3')
plt.savefig('figures/Europe_solar_map.jpg', 
            dpi=300, bbox_inches='tight')

#%%
"""
4. Create time series assuming layout uniform/proportional capacity factor
This is done using the exponent cf_exponent

"""
# Solar power CF per gridcell map
pv_cf = cutout_cmip.pv('CSi', 
                       orientation={"slope": 30.0, "azimuth": 180.0},
                       capacity_factor=True)

cf_exponent=2
layout_pv=pv_cf**cf_exponent
agg_pv_cf = cutout_cmip.pv('CSi', 
                           orientation={"slope": 30.0, "azimuth": 180.0},
                           layout=layout_pv,
                           per_unit=True).to_pandas()

fig, ax = plt.subplots(1, figsize=(12, 8))
agg_pv_cf.plot.area(ax=ax, color='orange')

ax.text(0.5, 0.9, 
        'mean CF = ' + str(round(agg_pv_cf.values.mean(),2)), 
        fontsize=20,
        horizontalalignment='center',
        verticalalignment='center', 
        transform=ax.transAxes)
fig.tight_layout()
plt.savefig('figures/agg_cf_solar.jpg', 
            dpi=300, bbox_inches='tight')
#%%
"""
5. Plot the distribution of capacity vs the resource

"""
data=pv_cf.values.flatten()
plt.hist(data, color='dodgerblue', bins=10, alpha=0.8, rwidth=0.85)
plt.xlabel("CF solar")
plt.savefig('figures/distribution_solar_uniform.jpg', 
            dpi=300, bbox_inches='tight')
#%%
data=pv_cf.values.flatten()
weights=layout_pv.values.flatten() 
plt.hist(data, weights=weights, color='dodgerblue', bins=10, alpha=0.8, rwidth=0.85)
plt.xlabel("CF solar")
plt.savefig('figures/distribution_solar_exponent_{}.jpg'.format(cf_exponent), 
            dpi=300, bbox_inches='tight')
