#!/usr/bin/env bash

python grid_lstm_gpu_runner_horizons.py \
  --T 20,24,28 --units 256  --layers 1 --batch 128 \
  --epochs 200 --patience 20 --H 1,2,3,4,5,6,7,8 --huber --dropout 0.1 \
  --max_runs 12 --save_models
