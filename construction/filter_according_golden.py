#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
from pathlib import Path
from utils.utils import load_jsonl, dump_jsonl


def collect_failed_instances(eval_path: Path):
    failed_ids = dict()
    eval_details = load_jsonl(eval_path)
    for record in eval_details:
        if not record.get("resolved", True) and "request" not in record["instance_id"]:
            fail_f2p = record["F2P"]["failure"]
            fail_p2p = record["P2P"]["failure"]
            failed_ids[record["instance_id"]] = {"F2P": fail_f2p, "P2P": fail_p2p}

    return failed_ids


def strip_pass_fields(
        data_path: Path, failed_ids, output_path: Path
) -> None:
    data = load_jsonl(data_path)
    cleaned_data = []
    for instance in data:
        instance_id = instance["instance_id"]
        if instance_id in failed_ids:
            p2p = instance['PASS2PASS']
            f2p = instance['FAIL2PASS']

            # 从P2P中删除失败的测试名称
            if failed_ids[instance_id]["P2P"]:
                for fail_test in failed_ids[instance_id]["P2P"]:
                    if fail_test in p2p:
                        p2p.remove(fail_test)

            # 从F2P中删除失败的测试名称
            if failed_ids[instance_id]["F2P"]:
                for fail_test in failed_ids[instance_id]["F2P"]:
                    if fail_test in f2p:
                        f2p.remove(fail_test)

            # 更新实例中的字段
            instance['PASS2PASS'] = p2p
            instance['FAIL2PASS'] = f2p

        cleaned_data.append(instance)

    # 将清理后的数据写入输出文件
    dump_jsonl(cleaned_data, output_path)



def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove PASS2PASS & FAIL2PASS for failing instances."
    )
    parser.add_argument(
        "--eval",
        help="Path to evaluation_details.jsonl",
        default="../evaluation_details.jsonl",
    )
    parser.add_argument(
        "--data",
        help="Path to data_verified.jsonl (or类似文件)",
        default="../data_verified.jsonl.new_v2",
    )
    parser.add_argument(
        "--out",
        help="Output file path to write cleaned data",
        default="../data_verified_filter.jsonl",
    )
    args = parser.parse_args()

    eval_path = Path(args.eval)
    data_path = Path(args.data)
    output_path = Path(args.out)

    failed_ids = collect_failed_instances(eval_path)
    print(f"发现 {len(failed_ids)} 个存在失败的 instance_id")

    strip_pass_fields(data_path, failed_ids, output_path)
    print(f"处理完成，结果已写入 {output_path}")


if __name__ == "__main__":
    main()
