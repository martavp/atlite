#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import numpy as np

years=np.arange(2015,2023) 
data=pd.DataFrame(index=years)
data.to_csv('../../../com/meenergy/cutouts_cmip6/summary.csv')
  