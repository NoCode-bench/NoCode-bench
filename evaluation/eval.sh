python ./evaluation/eval.py \
    --predictions_path ./all_preds.jsonl \  # <path_to_your_predictions>
    --log_dir ./evaluation/logs \
    --feature_bench_tasks results/augmentation/fb-verified_v0.1_masked_augmented.jsonl \
    --max_workers 110 \
    --output_file eval_result.txt