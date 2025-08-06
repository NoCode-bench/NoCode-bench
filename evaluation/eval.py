import argparse
import docker
import json
import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from datasets import load_dataset
from docker.errors import DockerException
from pathlib import Path, PurePosixPath
from threading import Lock
from tqdm import tqdm
from unidiff import PatchSet
import shlex

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
        image_level
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
        if image_level == 'repo':
            container_name = f'{image_name}__{instance_id}'
            try:
                existing_container = client.containers.get(container_name)
                logger.info(f"Found container with the same name {container_name} running, forcibly stopping and removing it")
                existing_container.stop(timeout=0)  # Force immediate stop
                existing_container.remove(force=True)
                logger.info(f"Successfully removed container with the same name {container_name}")
            except docker.errors.NotFound:
                # Container doesn't exist, continue normal flow
                pass
            except Exception as e:
                logger.error(f"Error cleaning up container with the same name: {str(e)}")
            
            # build container
            container = du.build_container(image_name=f'{image_name}:dev', container_name=container_name, client=client,
                                           logger=logger, proxy=proxy)
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

            # conda activate and install
            cmd_res = container.exec_run(f"conda run -n {config['conda_env']} {config['install']}",
                                         workdir=work_dir)

        else:
            # Check if container with the same name exists and clean it up
            container_name = f'{image_name}__{instance_id}'
            try:
                existing_container = client.containers.get(container_name)
                logger.info(f"Found container with the same name {container_name} running, forcibly stopping and removing it")
                existing_container.stop(timeout=0)  # Force immediate stop
                existing_container.remove(force=True)
                logger.info(f"Successfully removed container with the same name {container_name}")
            except docker.errors.NotFound:
                # Container doesn't exist, continue normal flow
                pass
            except Exception as e:
                logger.error(f"Error cleaning up container with the same name: {str(e)}")
                
            # build container
            container = du.build_container(image_name=f'ncbench_{instance_id}:latest', container_name=container_name, client=client,
                                           logger=logger, proxy=proxy)
            container.start()

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


        # run f2p and p2p
        def run_tests_in_parallel(container, test_files, config, work_dir, timeout, logger, test_type):
            results = [None] * len(test_files)

            def format_django_test_name(test_str):
                match = re.match(r"(.*?)\s+\((.*?)\)", test_str)
                if match:
                    method_name, class_path = match.groups()
                    return f"{class_path}.{method_name}"
                return test_str

            def run_test(index, test_file):
                logger.info(f'begin to run {test_type}: {test_file}')
                if "django" in config['conda_env']:
                    test_file = format_django_test_name(test_file)
                    test_file_escaped = f'"{test_file}"'
                else:
                    test_file_escaped = shlex.quote(test_file)
                test_cmd = f"conda run -n {config['conda_env'].strip()} {config['test_cmd'].strip()} {test_file_escaped}"

                if "sphinx" in config['conda_env']:
                    clean_cmd = "sudo rm -rf /root/sphinx/.tox/py*"
                    clean_res = du.exec_run_with_timeout(container=container, cmd=clean_cmd, workdir=work_dir,
                                                         timeout=timeout)
                    logger.info(f"Sphinx cleanup completed for test {index}: {clean_res}")

                cmd_res = du.exec_run_with_timeout(
                    container=container,
                    cmd=test_cmd,
                    workdir=work_dir,
                    timeout=timeout
                )
                results[index] = cmd_res[0]
                logger.info(f"test log: {cmd_res}")

            is_sphinx = "sphinx" in config['conda_env']

            if is_sphinx:
                logger.info("Sphinx environment detected, running tests sequentially to avoid tox conflicts")
                for i, test_file in enumerate(test_files):
                    run_test(i, test_file)
            else:
                min_worker = min(25, len(test_files)) if len(test_files) > 0 else 1
                logger.info(f"Running tests in parallel with {min_worker} workers")
                with ThreadPoolExecutor(max_workers=min_worker) as executor:
                    futures = [executor.submit(run_test, i, test_file) for i, test_file in enumerate(test_files)]
                    for future in as_completed(futures):
                        future.result()

            return results

        # Run f2p tests in parallel
        logger.info(f'begin to run f2p tests')
        f2p_results = run_tests_in_parallel(container, f2p, config, work_dir, 600, logger, 'f2p')

        # Run p2p tests in parallel
        logger.info(f'begin to run p2p tests')
        p2p_results = run_tests_in_parallel(container, p2p, config, work_dir, 600, logger, 'p2p')

        # Update test results
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
        return None
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
    # two loggers: one total, one per test
    os.makedirs(args.log_dir, exist_ok=True)
    detail_path = os.path.join(args.log_dir, 'evaluation_details.jsonl')
    prev_instance = []
    if os.path.exists(detail_path):
        prev_instance = load_jsonl(detail_path)
    existing = {i['instance_id']: i for i in prev_instance}
    logger = get_logger(log_name='eval', log_file=os.path.join(args.log_dir, '0eval.log'))
    logger.info(args)
    if 'jsonl' in args.bench_tasks:
        tasks = load_jsonl(args.bench_tasks)
    else:
        tasks = load_dataset(args.bench_tasks, split='test')
    tasks_record = {i['instance_id']: i for i in tasks}
    logger.info(f'Loaded {len(tasks)} tasks')
    predictions = load_jsonl(args.predictions_path)
    client = docker.from_env()
    if args.gold:
        predictions = tasks

    # Filter out unresolved tasks
    if args.unresolved_only and os.path.exists(detail_path):
        unresolved_ids = set()
        for instance in prev_instance:
            if not instance.get('resolved', False):
                unresolved_ids.add(instance['instance_id'])

        # Only keep unresolved tasks
        predictions = [pred for pred in predictions if pred['instance_id'] in unresolved_ids]
        logger.info(f'Filtered to {len(predictions)} unresolved tasks')

    def process_instance(pred, tasks_record, write_lock=None):
        instance_id = pred['instance_id']

        if instance_id in existing and not args.unresolved_only:
            logger.info(f"Skipping existing instance_id: {instance_id}")
            return
        task = tasks_record[instance_id]
        repo_name = task['repo'].split('/')[-1]

        feature_patch = task['feature_patch'] if args.gold else pred['model_patch']

        try:
            report = run_instance(
                instance_id=pred['instance_id'],
                image_name=f'fb_{repo_name}',
                commit_id=task['base_commit'],
                test_patch=task['test_patch'],
                feature_patch=feature_patch,
                version=task['version'],
                repo=task['repo'],
                p2p=task['PASS2PASS'],
                f2p=task['FAIL2PASS'],
                work_dir=f'/root/{repo_name}',
                client=client,
                log_dir=args.log_dir,
                proxy=args.proxy,
                image_level=args.image_level
            )
        except (DockerException, Exception) as e:
            logger.error(f"Instance {instance_id} skipped due to docker error: {e}")
            return
        with write_lock:
            with open(reports_fpath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(report) + '\n')

    # run evaluation and store results in reports_fapth
    reports_fpath = os.path.join(args.log_dir, '0reports.jsonl')
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
    if 'jsonl' in args.bench_tasks:
        all_tasks = load_jsonl(args.bench_tasks)
    else:
        all_tasks = load_dataset(args.bench_tasks, split='test')
    reports_fpath = os.path.join(args.log_dir, '0reports.jsonl')
    if os.path.exists(reports_fpath):
        reports = load_jsonl(reports_fpath)
    else:
        reports = []

    predictions = load_jsonl(args.predictions_path)

    reports_record = {r['instance_id']: r for r in reports if r}
    if args.gold:
        predictions_record = {t['instance_id']: t for t in all_tasks}
    else:
        predictions_record = {p['instance_id']: p for p in predictions if p}

    # ==== Phase 1: Process and save results ====
    output_fpath = os.path.join(args.log_dir, 'evaluation_details.jsonl')

    # Load existing results (if any)
    existing_results = {}
    if args.unresolved_only and os.path.exists(output_fpath):
        existing_details = load_jsonl(output_fpath)
        existing_results = {item["instance_id"]: item for item in existing_details}

    # Process all tasks, build final results list
    final_results_to_write = []
    newly_processed_instances = set()  # Track instances processed in this run

    for task in all_tasks:
        instance_id = task['instance_id']

        # If in unresolved_only mode and instance exists, skip processing but keep existing results
        if args.unresolved_only and instance_id in existing_results:
            final_results_to_write.append(existing_results[instance_id])
            continue

        # Process new instances or reprocess all instances
        if instance_id in reports_record:
            report = reports_record[instance_id]

            patch_applied = report.get('feature_patch_applied', False)
            
            if args.gold and 'feature_patch_applied' not in report:
                patch_applied = True

            result = eval_instance(task, report)

            if not result:
                continue

            p2p_success = not result['p2p']['failure']
            f2p_success = not result['f2p']['failure']
            resolved = p2p_success and f2p_success

            model_patch = ''
            if args.gold:
                model_patch = task.get('feature_patch', '')
            else:
                if instance_id in predictions_record:
                    model_patch = predictions_record[instance_id].get('model_patch', '')

            instance_eval_details = {
                "instance_id": instance_id,
                "resolved": resolved,
                "applied": patch_applied,
                "model_patch": model_patch,
                "P2P": result.get('p2p', {}),
                "F2P": result.get('f2p', {})
            }

            newly_processed_instances.add(instance_id)
            final_results_to_write.append(instance_eval_details)

        else:
            # Instances without reports
            resolved = False

            instance_eval_details = {
                "instance_id": instance_id,
                "resolved": resolved,
                "notes": "Instance not attempted or report was empty.",
                "P2P": {"success": [], "fail": task.get('PASS2PASS', [])},
                "F2P": {"success": [], "fail": task.get('FAIL2PASS', [])}
            }

            newly_processed_instances.add(instance_id)
            final_results_to_write.append(instance_eval_details)

    # Save results to file
    dump_jsonl(final_results_to_write, output_fpath)
    print(f"Detailed evaluation results saved to: {output_fpath}")

    # ==== Phase 2: Read data from saved file and calculate metrics ====
    saved_results = load_jsonl(output_fpath)

    # Scope explanation for metrics calculation
    total_instances = len(all_tasks)
    if args.unresolved_only:
        newly_processed_count = len(newly_processed_instances)
        scope_description = f"Unresolved Only Mode (Processed {newly_processed_count} instances this run, Total {total_instances} instances)"
    else:
        scope_description = f"All Instances Mode (Total {total_instances} instances)"

    # Calculate metrics based on saved results
    submitted_instances = len([r for r in saved_results if r['instance_id'] in reports_record])

    # FPT rate: Count of completely resolved instances
    fpt_rate = sum(1 for r in saved_results if r.get("resolved", False))

    # RT rate: Count of instances without P2P failures
    rt_rate = 0
    for r in saved_results:
        p2p_data = r.get("P2P", {})
        has_p2p_failure = (
                p2p_data.get("failure") or
                p2p_data.get("fail") or
                len(p2p_data.get("failure", [])) > 0 or
                len(p2p_data.get("fail", [])) > 0
        )
        if not has_p2p_failure:
            rt_rate += 1

    # Apply rate: Count of instances where patch was successfully applied
    fp_apply_rate = sum(1 for r in saved_results if r.get("applied", False))

    # FV-Micro calculation
    fv_micro_ok = 0
    fv_micro_all = 0
    for r in saved_results:
        f2p_data = r.get("F2P", {})
        success_count = len(f2p_data.get("success", []))
        failure_count = len(f2p_data.get("failure", [])) + len(f2p_data.get("fail", []))

        fv_micro_ok += success_count
        fv_micro_all += success_count + failure_count

    fv_micro_score = fv_micro_ok / fv_micro_all if fv_micro_all > 0 else 0

    # FV-Macro calculation
    fv_macro_scores = []
    for r in saved_results:
        f2p_data = r.get("F2P", {})
        success_count = len(f2p_data.get("success", []))
        failure_count = len(f2p_data.get("failure", [])) + len(f2p_data.get("fail", []))
        total_f2p = success_count + failure_count

        if total_f2p > 0:
            instance_score = success_count / total_f2p
        else:
            instance_score = 1.0  # Perfect score if no tests
        fv_macro_scores.append(instance_score)

    fv_macro_score = sum(fv_macro_scores) / len(fv_macro_scores) if fv_macro_scores else 0

    # ==== Phase 3: Generate and output report ====
    summary_lines = [
        "-" * 30,
        f"{args.predictions_path}",
        f"Evaluation Results - {scope_description}",
        "-" * 30,
        f"Total Instances: {total_instances}",
        f"Submitted Instances: {submitted_instances}",
        f"Applied%: {fp_apply_rate / total_instances:.2%} ({fp_apply_rate} / {total_instances})" if total_instances > 0 else "Applied%: 0.00% (0 / 0)",
        f"Success%: {fpt_rate / total_instances:.2%} ({fpt_rate} / {total_instances})" if total_instances > 0 else "Resolved%: 0.00% (0 / 0)",
        f"Regression Test (RT%): {rt_rate / total_instances:.2%} ({rt_rate} / {total_instances})" if total_instances > 0 else "RT%: 0.00% (0 / 0)",
        f"FV-Micro: {fv_micro_score:.4f} ({fv_micro_ok} / {fv_micro_all})",
        f"FV-Macro: {fv_macro_score:.4f}",
    ]

    if args.unresolved_only and newly_processed_instances:
        summary_lines.extend([
            "-" * 30,
            f"This Run Details:",
            f"Newly Processed Instances: {len(newly_processed_instances)}",
        ])

    summary_report_str = "\n".join(summary_lines)
    print(summary_report_str)

    summary_output_fpath = args.output_file if args.output_file else f'{args.predictions_path.split(".")[0]}_summary_report.txt'
    with open(summary_output_fpath, 'w', encoding='utf-8') as f:
        f.write(summary_report_str)


def eval_file_localization(args):
    """
    Evaluate file-level and patch-level localization, then append the
    results to the same *_summary_report.txt produced in eval_instances.
    """
    if 'jsonl' in args.bench_tasks:
        tasks = load_jsonl(args.bench_tasks)
    else:
        tasks = load_dataset(args.bench_tasks, split='test')
    tasks_record = {}
    for task in tasks:
        gt_patch_set = PatchSet(task['feature_patch'])
        ref_files = [f.path for f in gt_patch_set if f.path.endswith('.py')]
        tasks_record[task['instance_id']] = ref_files

    eval_levels = ['patch', 'file'] if args.fl_level == 'both' else [args.fl_level]

    fl_patch_success = fl_patch_total = 0
    fl_file_success = fl_file_total = 0

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

    if 'file' in eval_levels and args.fl_predictions_path:
        fl_preds = load_jsonl(args.fl_predictions_path)
        fl_file_total = len(fl_preds)

        for prediction in fl_preds:
            iid = prediction['instance_id']
            if iid not in tasks_record:
                continue
            if set(tasks_record[iid]).issubset(set(prediction['found_files'])):
                fl_file_success += 1

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
    parser.add_argument("--bench_tasks", type=str, help="Path to benchmark task instances file", required=True)
    parser.add_argument("--fl_level", type=str, choices=['patch', 'file', 'both'], default='patch')
    parser.add_argument("--image_level", type=str, choices=['instance', 'repo'], default='repo')
    parser.add_argument("--output_file", type=str, default=None,
                        help="(Optional) Path to save detailed evaluation results (.jsonl).")
    parser.add_argument("--timeout", type=int, help="(Optional) Timeout in seconds (default: 600)", default=600)
    parser.add_argument("--max_workers", type=int, help="(Optional) Max workers (default: 1)", default=1)
    parser.add_argument("--proxy", type=str, help="(Optional) Http proxy (default: None)", default=None)
    parser.add_argument("--gold", action="store_true", help="(Optional) Use golden patch (feature_patch) from dataset instead of model predictions")
    parser.add_argument("--unresolved_only", action="store_true", help="(Optional) Only run unresolved tasks from previous evaluation")

    args = parser.parse_args()
    main(args)

