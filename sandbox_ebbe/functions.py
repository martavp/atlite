import cdsapi
import geopandas as gpd
from cartopy.io import shapereader
import os 

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

def retrieve_roughness(coords,year,file):
    
    if os.path.isfile(file):
        string = "roughness has already been retrieved"
        print(string)
        return

    # Wind Capacity factor CMIP : the surface roughness is not available 
    # from the CMIP database so ERA5 roughness is used instead.
    # (ideally this step is removed and wind velocity is interpolated from the 
    # wind speed at two closest heights)
    c = cdsapi.Client()
    c.retrieve(
        'reanalysis-era5-single-levels-monthly-means',
        {
            'product_type': 'monthly_averaged_reanalysis',
            'format': 'netcdf',
            'variable': 'forecast_surface_roughness',
            'year': year,
            'month': [
                    '01', '02', '03',
                    '04', '05', '07',
                    '08', '09', '10',
                    '11',
                    ],
            'area': [
                    coords["latmax"], coords["lonmin"], coords["latmin"], coords["lonmax"],
                    ],
            'time': '00:00',
        },
        'data/roughness.nc')

    print("roughness was retrieved")
    return

