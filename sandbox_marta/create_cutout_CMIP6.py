#!/usr/bin/env python
# coding: utf-8

# In[ ]:
import sys #to use files in git_repos folder
sys.path.insert(0,'../../atlite')
import atlite

import logging
logging.basicConfig(level=logging.INFO)


# In[ ]:

esgf_params = {
   'data_node': 'esgf-cnr.hpc.cineca.it',
   'source_id': 'EC-Earth3',
   'variant_label':'r4i1p1f1',
   'experiment_id': 'ssp126',
   'project' : 'CMIP6',
   'frequency': ['3hr', '6hr']
}
# Define cutout time duration: 
start_date = "2015-01-02"
end_date = "2015-01-08"

yy_start = datetime.datetime.strptime(start_date,"%Y-%m-%d").year-2000
yy_end = datetime.datetime.strptime(end_date,"%Y-%m-%d").year-2000
source_id = esgf_params["source_id"].replace("-", "_")
cutout_name = f'Europe_{source_id}_{esgf_params["experiment_id"]}_{yy_start}_{yy_end}'


path = filename      


cutout = atlite.Cutout(
                            path=path,
                            module="cmip",
                            #bounds = bounds,
                            x=slice(-13,45),
                            y=slice(32,83),
                            time=slice(start_date, end_date),
                            esgf_params=esgf_params,
                            dt='3H',dx=1, dy=1)

cutout.prepare()

