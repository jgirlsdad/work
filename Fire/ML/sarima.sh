#!/usr/bin/env bash

python sarima.py \
  --climate_dir "data/Climate-Indices" \
  --db_path "/home/joe/Fire/Data/DB/era5DataMeans.db" \
  --point 500 --var VPD \
  --H 1,3,6,8,12 \
  --orders 1,1,1 --sorders 1,1,1 --m 12 \
  --exog none \
  --out_csv sarima_results_exog.csv