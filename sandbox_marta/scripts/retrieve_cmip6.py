#!/usr/bin/env python
# coding: utf-8

import sys #to use files in git_repos folder
sys.path.insert(0,'../../atlite')
#sys.path.insert(0,'/media/sf_Dropbox/AU/GIT_REPOS/atlite')
from atlite.datasets.era5 import retrieve_data, _rename_and_clean_coords, retrieval_times, _area
import xarray as xr
import atlite
import logging
import geopandas as gpd
import numpy as np
import pandas as pd
logging.basicConfig(level=logging.INFO)

import os
# Removing facets warning: 
os.environ['ESGF_PYCLIENT_NO_FACETS_STAR_WARNING']='1'

import datetime

def retrieve_cutout_cmip6(filename, year, esgf_params):   
    cutout_cmip = atlite.Cutout(path=filename,
                                module='cmip',
                                x=slice(-13,45),
                                y=slice(32,83),
                                time=str(year),
                                esgf_params=esgf_params,
                                dt='3H',dx=1, dy=1)
    
    cutout_cmip.prepare()
    
    return cutout_cmip

if __name__ == "__main__":
    if "snakemake" not in globals():
        from _helpers import mock_snakemake

        snakemake = mock_snakemake(
            "retrieve_cutout_cmip6",
            configfiles ="config/config.yaml",
            source_id = 'EC-Earth3',
            variant_label ='r4i1p1f1',
            experiment_id = 'ssp585',
            year="2034")

    logging.basicConfig(level=snakemake.config["logging"]["level"])

    source_id = snakemake.wildcards.source_id

    variant_label = snakemake.wildcards.variant_label

    experiment_id = snakemake.wildcards.experiment_id

    year = int(snakemake.wildcards.year[-4:])


esgf_params = {
    'data_node': 'esgf-cnr.hpc.cineca.it',
    'source_id': source_id,
    'variant_label': variant_label,
    'experiment_id': experiment_id,
    'project' : 'CMIP6',
    'frequency': ['3hr','6hr'] }


retrieve_cutout_cmip6(
                      #filename='../cutouts_cmip6/{}/Europe_{}_{}_{}_{}.nc'.format(source_id, source_id, variant_label, experiment_id, year),
                      filename='../../../com/meenergy/cutouts_cmip6/{}/Europe_{}_{}_{}_{}.nc'.format(source_id, source_id, variant_label, experiment_id, year),
                      year=year, esgf_params=esgf_params)

    