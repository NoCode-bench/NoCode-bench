import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from threading import Lock
from concurrent.futures import as_completed
from docker.errors import DockerException

import docker
from tqdm import tqdm
from unidiff import PatchSet

import utils.docker_utils as du
from construction.filter_execution.constants import *
from construction.filter_execution.testlog_extractor import *
from utils.logger import get_logger
from utils.utils import load_jsonl, dump_jsonl

GIT_APPLY_CMDS = [
    "git apply --verbose",
    "git apply --verbose --reject",
    "patch --batch --fuzz=5 -p1 -i",
]


def run_instance(
        instance_id,
        image_name,
        commit_id,
        test_patch,
        feature_patch,
        version,
        repo,
        p2p,
        f2p,
        work_dir,
        client,
        log_dir,
        proxy,
):
    '''
    Run a single instance with the given prediction.
    '''
    container = None
    patch_dir = os.path.join(log_dir, "patches")
    logfile_dir = os.path.join(log_dir, "exec_logs")

    os.makedirs(patch_dir, exist_ok=True)
    os.makedirs(logfile_dir, exist_ok=True)

    patch_path = os.path.join(patch_dir, f'patch_{instance_id}.diff')
    logger = get_logger(
        log_name=instance_id,
        log_file=os.path.join(logfile_dir, f'{instance_id}.log')
    )

    test_results = {
        'instance_id': instance_id,
        'f2p': [],
        'p2p': [],
        'feature_patch_applied': False
    }
    try:
        # build container
        container_name = f'{image_name}__{instance_id}'
        container = du.build_container(image_name=f'{image_name}:dev', container_name=container_name, client=client, logger=logger, proxy=proxy)
        container.start()
        # reset branch
        container.exec_run('git clean -fdx', workdir=work_dir)
        container.exec_run('git reset --hard HEAD', workdir=work_dir)
        # checkout base_commit 
        git_checkout_cmd = f"git checkout {commit_id}"
        container.exec_run(git_checkout_cmd, workdir=work_dir)
        # apply test patch
        patch_file = Path(patch_path)
        patch_file.write_text(test_patch)
        du.copy_to_container(container, patch_file, PurePosixPath(DOCKER_PATCH))
        cmd_res = container.exec_run(f"git apply {DOCKER_PATCH}", workdir=work_dir)
        if cmd_res.exit_code != 0:
            logger.info(f"Failed to apply test patch to container")
            return test_results
        else:
            logger.info(f"Successfully applied test patch to container")
        # get the config of the instance
        config = MAP_REPO_TO_CONFIG[repo][version]
        # run pre_install
        if 'pre_install' in config:
            for pre_install_cmd in config['pre_install']:
                cmd_res = container.exec_run(cmd=pre_install_cmd, workdir=work_dir)

        # apply feature patch
        patch_file.write_text(feature_patch)
        du.copy_to_container(container, patch_file, PurePosixPath(DOCKER_PATCH))
        applied_patch = False
        for git_apply_cmd in GIT_APPLY_CMDS:
            cmd_res = container.exec_run(f"{git_apply_cmd} {DOCKER_PATCH}", workdir=work_dir)
            if cmd_res.exit_code == 0:
                logger.info(f"Successfully applied feature patch to container")
                applied_patch = True
                break
            else:
                logger.info(f"Failed to apply feature patch to container: {git_apply_cmd}")

        test_results['feature_patch_applied'] = applied_patch

        if not applied_patch:
            logger.info(f"Failed to apply feature patch to container")
            return test_results

        # conda activate and install
        cmd_res = container.exec_run(f"conda run -n {config['conda_env']} {config['install']}", workdir=work_dir)

        # run f2p and p2p
        def run_tests_in_parallel(container, test_files, config, work_dir, timeout, logger, test_type):
            results = [None] * len(test_files)

            def run_test(index, test_file):
                logger.info(f'begin to run {test_type}: {test_file}')
                test_cmd = f"conda run -n {config['conda_env'].strip()} {config['test_cmd'].strip()} {test_file}"
                cmd_res = du.exec_run_with_timeout(container=container, cmd=test_cmd, workdir=work_dir, timeout=timeout)
                results[index] = cmd_res[0]
                logger.info(f"test log: {cmd_res}")

            min_worker = min(25, len(test_files)) if len(test_files) > 0 else 1
            with ThreadPoolExecutor(max_workers=min_worker) as executor:
                futures = [executor.submit(run_test, i, test_file) for i, test_file in enumerate(test_files)]
                for future in as_completed(futures):
                    future.result()

            return results

        # 并行执行f2p测试
        logger.info(f'begin to run f2p tests')
        f2p_results = run_tests_in_parallel(container, f2p, config, work_dir, 600, logger, 'f2p')

        # 并行执行p2p测试
        logger.info(f'begin to run p2p tests')
        p2p_results = run_tests_in_parallel(container, p2p, config, work_dir, 600, logger, 'p2p')

        # 更新测试结果
        test_results.update({
            'f2p': f2p_results,
            'p2p': p2p_results
        })

    except Exception as e:
        logger.error(f'error: {e}')
        raise
    finally:
        du.cleanup_container(client, container, logger)

    return test_results


def extract_test_info(content, instance_id):
    if 'django' in instance_id:
        return extract_django_tests(content)
    elif 'sympy' in instance_id:
        return extract_sympy_tests(content)
    elif any(i in instance_id for i in ['pytest', 'sphinx', 'requests']):
        return extract_pytest_info(content, old=True)
    else:
        return extract_pytest_info(content)


def eval_instance(task, report):
    all_tests = report['f2p'] + report['p2p']
    all_results = []
    for r in all_tests:
        all_results.extend(extract_test_info(r, report['instance_id']))
    try:
        tests_record = {i[1]: i[0] for i in all_results}
    except:
        return
    f2p_success = []
    f2p_failure = []
    for test_case in task['FAIL2PASS']:
        if test_case in tests_record:
            if tests_record[test_case] == 'PASSED':
                f2p_success.append(test_case)
            else:
                f2p_failure.append(test_case)
        else:
            f2p_failure.append(test_case)

    p2p_success = []
    p2p_failure = []
    for test_case in task['PASS2PASS']:
        if test_case in tests_record:
            if tests_record[test_case] == 'PASSED':
                p2p_success.append(test_case)
            else:
                p2p_failure.append(test_case)
        else:
            p2p_failure.append(test_case)

    results = {
        'f2p': {
            "success": f2p_success,
            "failure": f2p_failure,
        },
        'p2p': {
            "success": p2p_success,
            "failure": p2p_failure,
        },
    }
    return results


def run_instances(args):
    # two loggers: one tatol, one per test
    os.makedirs(args.log_dir, exist_ok=True)
    reports_fpath = os.path.join(args.log_dir, '0reports.jsonl')
    detail_path = os.path.join(args.log_dir, 'evaluation_details.jsonl')
    prev_reports = []
    prev_instance = []
    if os.path.exists(detail_path):
        prev_instance = load_jsonl(detail_path)
    if os.path.exists(reports_fpath):
        prev_reports = load_jsonl(reports_fpath)
    existing = {i['instance_id']: i for i in prev_instance}
    logger = get_logger(log_name='eval', log_file=os.path.join(args.log_dir, '0eval.log'))
    logger.info(args)
    tasks = load_jsonl(args.feature_bench_tasks)
    tasks_record = {i['instance_id']: i for i in tasks}
    logger.info(f'Loaded {len(tasks)} tasks')
    predictions = load_jsonl(args.predictions_path)
    client = docker.from_env()

    def process_instance(pred, tasks_record, write_lock=None):
        instance_id = pred['instance_id']

        if instance_id in existing:
            logger.info(f"Skipping existing instance_id: {instance_id}")
            return
        task = tasks_record[instance_id]
        repo_name = task['repo'].split('/')[-1]
        try:
            report = run_instance(
                instance_id=pred['instance_id'],
                image_name=f'fb_{repo_name}',
                commit_id=task['base_commit'],
                test_patch=task['test_patch'],
                feature_patch=pred['model_patch'],
                version=task['version'],
                repo=task['repo'],
                p2p=task['PASS2PASS'],
                f2p=task['FAIL2PASS'],
                work_dir=f'/root/{repo_name}',
                client=client,
                log_dir=args.log_dir,
                proxy=args.proxy,
            )
        except (DockerException, Exception) as e:
            logger.error(f"Instance {instance_id} skipped due to docker error: {e}")
            return
        with write_lock:
            with open(reports_fpath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(report) + '\n')

    # run evaluation and store results in reports_fapth
    write_lock = Lock()
    if args.max_workers == 1:
        for pred in tqdm(predictions):
            process_instance(pred, tasks_record, write_lock)
    else:
        with ThreadPoolExecutor(args.max_workers) as executor:
            futures = [executor.submit(process_instance, pred, tasks_record, write_lock) for pred in predictions]
            for future in tqdm(
                    as_completed(futures),
                    total=len(predictions),
                    colour="MAGENTA",
            ):
                future.result()

    logger.info(f"Finished process for {len(predictions)} predictions")


def eval_instances(args):
    all_tasks = load_jsonl(args.feature_bench_tasks)

    reports_fpath = os.path.join(args.log_dir, '0reports.jsonl')
    if os.path.exists(reports_fpath):
        reports = load_jsonl(reports_fpath)
    else:
        reports = []

    predictions = load_jsonl(args.predictions_path)

    reports_record = {r['instance_id']: r for r in reports if r}
    predictions_record = {p['instance_id']: p for p in predictions if p}

    fpt_rate = 0  # Full pass test rate
    rt_rate = 0  # Regression test rate
    fp_apply_rate = 0  # Feature patch apply rate
    fv_macro_scores = []
    fv_micro_scores = [0, 0]
    final_results_to_write = []

    for task in all_tasks:
        instance_id = task['instance_id']

        if instance_id in reports_record:
            report = reports_record[instance_id]

            patch_applied = False
            if 'feature_patch_applied' in report:
                if report['feature_patch_applied']:
                    patch_applied = True
            else:

                if instance_id in predictions_record:
                    prediction = predictions_record[instance_id]

                    if prediction.get('model_patch'):
                        patch_applied = True

            if patch_applied:
                fp_apply_rate += 1

            result = eval_instance(task, report)

            if not result:
                continue

            p2p_success = not result['p2p']['failure']
            if p2p_success:
                rt_rate += 1

            f2p_success = not result['f2p']['failure']
            resolved = p2p_success and f2p_success
            if resolved:
                fpt_rate += 1

            instance_eval_details = {
                "instance_id": instance_id,
                "model_patch": predictions_record[instance_id].get('model_patch', ''),
                "resolved": resolved,
                "applied": patch_applied,
                "P2P": result.get('p2p', {}),
                "F2P": result.get('f2p', {})
            }

            total_f2p_tests = len(result['f2p']['success']) + len(result['f2p']['failure'])
            if total_f2p_tests > 0:
                instance_macro_score = len(result['f2p']['success']) / total_f2p_tests
            else:
                instance_macro_score = 1.0

            fv_macro_scores.append(instance_macro_score)
            fv_micro_scores[0] += len(result['f2p']['success'])
            fv_micro_scores[1] += total_f2p_tests
        else:
            resolved = False

            instance_eval_details = {
                "instance_id": instance_id,
                "resolved": resolved,
                "notes": "Instance not attempted or report was empty.",
                "P2P": {"success": [], "fail": task.get('PASS2PASS', [])},
                "F2P": {"success": [], "fail": task.get('FAIL2PASS', [])}
            }

            fv_macro_scores.append(0.0)
            fv_micro_scores[1] += len(task.get('FAIL2PASS', []))

        final_results_to_write.append(instance_eval_details)

    total_instances = len(all_tasks)
    fv_macro_score = sum(fv_macro_scores) / len(fv_macro_scores) if fv_macro_scores else 0
    fv_micro_score = fv_micro_scores[0] / fv_micro_scores[1] if fv_micro_scores[1] > 0 else 0

    summary_lines = [
        "-" * 30,
        f"{args.predictions_path}",
        "Evaluation Results",
        "-" * 30,
        f"Total Instances: {total_instances}",
        f"Submitted Instances: {len(reports_record)}",
        f"Applied%: {fp_apply_rate / total_instances:.2%} ({fp_apply_rate} / {total_instances})",
        f"Resolved% : {fpt_rate / total_instances:.2%} ({fpt_rate} / {total_instances})",
        f"Regression Test (RT%): {rt_rate / total_instances:.2%} ({rt_rate} / {total_instances})",
        f"FV-Micro: {fv_micro_score:.4f} ({fv_micro_scores[0]} / {fv_micro_scores[1]})",
        f"FV-Macro: {fv_macro_score:.4f}",
    ]
    summary_report_str = "\n".join(summary_lines)
    print(summary_report_str)

    output_fpath = os.path.join(args.log_dir, 'evaluation_details.jsonl')
    dump_jsonl(final_results_to_write, output_fpath)
    print(f"Detailed evaluation results saved to: {output_fpath}")

    summary_output_fpath = args.output_file if args.output_file else f'{args.predictions_path.split(".")[0]}_summary_report.txt'

    with open(summary_output_fpath, 'w', encoding='utf-8') as f:
        f.write(summary_report_str)
    print(f"Summary report saved to: {summary_output_fpath}")


def write_content(fpath, content):
    with open(fpath, 'w') as f:
        f.write(content)


def eval_file_localization(args):
    """
    Evaluate file-level and patch-level localization, then append the
    results to the same *_summary_report.txt produced in eval_instances.
    """
    # ---------- build reference mapping ----------
    tasks = load_jsonl(args.feature_bench_tasks)
    tasks_record = {}
    for task in tasks:
        gt_patch_set = PatchSet(task['feature_patch'])
        ref_files = [f.path for f in gt_patch_set if f.path.endswith('.py')]
        tasks_record[task['instance_id']] = ref_files

    eval_levels = ['patch', 'file'] if args.fl_level == 'both' else [args.fl_level]

    # ---------- statistics holders ----------
    fl_patch_success = fl_patch_total = 0
    fl_file_success = fl_file_total = 0

    # ---------- patch-level localization ----------
    if 'patch' in eval_levels:
        predictions = load_jsonl(args.predictions_path)
        fl_patch_total = len(predictions)
        correct_ids, wrong_ids = set(), set()

        for prediction in predictions:
            iid = prediction['instance_id']
            if iid not in tasks_record:
                continue
            gt_files = set(tasks_record[iid])
            try:
                pred_files = {f.path for f in PatchSet(prediction['model_patch'])}
            except Exception as e:
                print(f"[Warning] Failed to parse patch for instance {iid}: {e}")
                continue
            if gt_files.issubset(pred_files):
                fl_patch_success += 1
                correct_ids.add(iid)
            else:
                wrong_ids.add(iid)

    # ---------- file-level localization ----------
    if 'file' in eval_levels and args.fl_predictions_path:
        fl_preds = load_jsonl(args.fl_predictions_path)
        fl_file_total = len(fl_preds)

        for prediction in fl_preds:
            iid = prediction['instance_id']
            if iid not in tasks_record:
                continue
            if set(tasks_record[iid]).issubset(set(prediction['found_files'])):
                fl_file_success += 1

    # ---------- append summary to report ----------
    summary_path = (
        args.output_file
        if args.output_file
        else f'{args.predictions_path.split(".")[0]}_summary_report.txt'
    )

    lines = []
    if 'patch' in eval_levels:
        rate = fl_patch_success / fl_patch_total if fl_patch_total else 0
        print(f"FL-Patch Success Rate: {fl_patch_success} / {fl_patch_total} ({rate:.2%})")
        lines.append(
            f"FL-Patch Success Rate: {fl_patch_success} / {fl_patch_total} ({rate:.2%})"
        )
    if 'file' in eval_levels:
        rate = fl_file_success / fl_file_total if fl_file_total else 0
        print(f"FL-File Success Rate: {fl_file_success} / {fl_file_total} ({rate:.2%})")
        lines.append(
            f"FL-File  Success Rate: {fl_file_success} / {fl_file_total} ({rate:.2%})"
        )
    lines.append('-' * 30)

    with open(summary_path, 'a', encoding='utf-8') as f:
        f.write('\n' + '\n'.join(lines))



def main(args):

    run_instances(args)
    eval_instances(args)
    eval_file_localization(args)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions_path", type=str, help="Path to predictions file (must be .jsonl)", required=True)
    parser.add_argument("--fl_predictions_path", type=str, help="Path to fl predictions file (must be .jsonl)")
    parser.add_argument("--log_dir", type=str, help="Path to log directory", required=True)
    parser.add_argument("--feature_bench_tasks", type=str, help="Path to benchmark task instances file", required=True)
    parser.add_argument("--fl_level", type=str, choices=['patch', 'file', 'both'], default='patch')
    parser.add_argument("--output_file", type=str, default=None, help="(Optional) Path to save detailed evaluation results (.jsonl).")
    parser.add_argument("--timeout", type=int, help="(Optional) Timeout in seconds (default: 600)", default=600)
    parser.add_argument("--max_workers", type=int, help="(Optional) Max workers (default: 10)", default=1)
    parser.add_argument("--proxy", type=int, help="(Optional) Http proxy (default: None)", default=None)

    args = parser.parse_args()
    main(args)
