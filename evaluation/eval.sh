export PYTHONPATH=$PYTHONPATH:$(pwd)
python3 ./evaluation/eval.py \
   --predictions_path ./allhands_preds_claude.jsonl \
   --log_dir ./evaluation/logs_gold_verified_new \
   --bench_tasks data_verified.jsonl.new_v2 \
   --max_workers 50 \
   --image_level instance \
   --proxy 127.0.0.1:7897 \
   --output_file eval_result_gold_verified.txt \
   --gold \
   --unresolved_only