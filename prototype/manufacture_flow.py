import random
import time
import json
import os
import concurrent.futures
import multiprocessing

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as f:
        return json.load(f)

CONFIG = load_config()

class Item:
    def __init__(self, name, p, is_new=False):
        self.name = name
        self.is_new = is_new
        self.is_registered = not is_new
        self.smt_sequence = self._generate_smt_sequence(p)
        self.test_sequence = self._generate_test_sequence(p)

    def _generate_smt_sequence(self, p):
        categories = ['PCBA', 'Solder', 'P&P', 'Reflow', 'Oven']
        seq = random.sample(categories, random.randint(3, 5))
        instances = {
            'PCBA': [f"PCBA-{i+1}" for i in range(p['NUM_PCBA_MACHINES'])],
            'Solder': [f"Solder-{i+1}" for i in range(p['NUM_SOLDER_PASTE_MACHINES'])],
            'P&P': [f"P&P-{i+1}" for i in range(p['NUM_PNP_MACHINES'])],
            'Reflow': [f"Reflow-{i+1}" for i in range(p['NUM_REFLOW_MACHINES'])],
            'Oven': [f"Oven-{i+1}" for i in range(p['NUM_OVEN_MACHINES'])]
        }
        return [random.choice(instances[cat]) for cat in seq]

    def _generate_test_sequence(self, p):
        optional_cats = ['ICT', 'Board', 'Flying', 'X-ray']
        seq = random.sample(optional_cats, random.randint(1, 3))
        if 'FCT' not in seq:
            seq.insert(random.randint(0, len(seq)), 'FCT')
        seq.append('Visual')
        instances = {
            'ICT': [f"ICT-{i+1}" for i in range(p['NUM_ICT_MACHINES'])],
            'Board': [f"Board-{i+1}" for i in range(p['NUM_BOARD_TEST_MACHINES'])],
            'FCT': [f"FCT-{i+1}" for i in range(p['NUM_FCT_MACHINES'])],
            'Visual': [f"Visual-{i+1}" for i in range(p['NUM_VISUAL_TEST_MACHINES'])],
            'Flying': [f"Flying-{i+1}" for i in range(p['NUM_FLYING_PROBE_MACHINES'])],
            'X-ray': [f"X-ray-{i+1}" for i in range(p['NUM_XRAY_MACHINES'])]
        }
        return [random.choice(instances[cat]) for cat in seq]

class PO:
    def __init__(self, po_id, item, qty):
        self.po_id = po_id
        self.item = item
        self.qty = qty

def generate_item_data(params, base_seed):
    random.seed(base_seed)
    p = params
    num_reg = p['INITIAL_REGISTERED_ITEMS']
    num_new = p['ORDERS_PER_DAY'] // 10
    reg_smt_lens = [random.randint(3, 5) for _ in range(num_reg)]
    reg_test_lens = [random.randint(2, 5) for _ in range(num_reg)]
    new_smt_lens = [random.randint(3, 5) for _ in range(num_new)]
    new_test_lens = [random.randint(2, 5) for _ in range(num_new)]
    accepted_flags = [random.random() > p['DFM_REJECTION_RATE'] for _ in range(num_new)]
    accepted_count = sum(accepted_flags)
    return reg_smt_lens, reg_test_lens, new_smt_lens, new_test_lens, accepted_flags, accepted_count

def process_chunk(args):
    p, chunk_start, chunk_end, chunk_seed, base_seed = args

    reg_smt_lens, reg_test_lens, new_smt_lens, new_test_lens, accepted_flags, _ = generate_item_data(p, base_seed)
    num_reg = len(reg_smt_lens)
    num_new = len(new_smt_lens)

    random.seed(chunk_seed)

    reg_item_po_count = 0
    new_item_po_count = 0
    partial_final_po = 0
    partial_qty = 0
    partial_smt_steps = 0
    partial_smt_raw = 0
    partial_test_steps = 0
    partial_test_raw = 0
    partial_unique_items = set()

    for i in range(chunk_start, chunk_end):
        is_new = random.random() < 0.1
        qty = random.randint(p['MIN_QTY_PER_PO'], p['MAX_QTY_PER_PO'])

        if is_new:
            new_item_po_count += 1
            idx = random.randint(0, num_new - 1)
            if not accepted_flags[idx]:
                continue
            smt_len = new_smt_lens[idx]
            test_len = new_test_lens[idx]
            item_id = f"new_{idx}"
        else:
            reg_item_po_count += 1
            idx = random.randint(0, num_reg - 1)
            smt_len = reg_smt_lens[idx]
            test_len = reg_test_lens[idx]
            item_id = f"reg_{idx}"

        partial_final_po += 1
        partial_qty += qty
        partial_smt_steps += smt_len
        partial_smt_raw += qty * smt_len
        partial_test_steps += test_len
        partial_test_raw += qty * test_len
        partial_unique_items.add(item_id)

    return {
        'reg_po': reg_item_po_count,
        'new_po': new_item_po_count,
        'final_po': partial_final_po,
        'qty': partial_qty,
        'smt_steps': partial_smt_steps,
        'smt_raw': partial_smt_raw,
        'test_steps': partial_test_steps,
        'test_raw': partial_test_raw,
        'unique_items': partial_unique_items
    }

def build_chunks(params, num_chunks):
    p = params
    base_seed = str(p.get('DESC', '0'))
    n = p['ORDERS_PER_DAY']
    chunk_size = n // num_chunks
    chunks = []
    for w in range(num_chunks):
        cs = w * chunk_size
        ce = cs + chunk_size if w < num_chunks - 1 else n
        chunk_seed = f"{base_seed}_chunk_{w}"
        chunks.append((p, cs, ce, chunk_seed, base_seed))
    return chunks

def reduce_results(partial_results, params):
    p = params
    base_seed = str(p.get('DESC', '0'))
    num_unique_new = p['ORDERS_PER_DAY'] // 10
    _, _, _, _, accepted_flags, accepted_count = generate_item_data(p, base_seed)

    total_reg_po = sum(pr['reg_po'] for pr in partial_results)
    total_new_po = sum(pr['new_po'] for pr in partial_results)
    total_final_po = sum(pr['final_po'] for pr in partial_results)
    total_qty = sum(pr['qty'] for pr in partial_results)
    total_smt_steps = sum(pr['smt_steps'] for pr in partial_results)
    total_smt_raw = sum(pr['smt_raw'] for pr in partial_results)
    total_test_steps = sum(pr['test_steps'] for pr in partial_results)
    total_test_raw = sum(pr['test_raw'] for pr in partial_results)
    all_unique = set()
    for pr in partial_results:
        all_unique.update(pr['unique_items'])

    avg_smt = total_smt_steps / total_final_po if total_final_po > 0 else 0
    avg_test = total_test_steps / total_final_po if total_final_po > 0 else 0

    return {
        'total_reg_po': total_reg_po,
        'total_new_po': total_new_po,
        'total_final_po': total_final_po,
        'total_qty': total_qty,
        'total_smt_steps': total_smt_steps,
        'total_smt_raw': total_smt_raw,
        'total_test_steps': total_test_steps,
        'total_test_raw': total_test_raw,
        'all_unique': all_unique,
        'avg_smt': avg_smt,
        'avg_test': avg_test,
        'num_unique_new': num_unique_new,
        'accepted_count': accepted_count
    }

def format_result(params, reduced, timings):
    p = params
    r = reduced
    t = timings
    result = {
        "1. OE - Total PO": (p['ORDERS_PER_DAY'], t.get('t1', 0.0)),
        "1. OE - Item Breakdown": (f"{r['total_reg_po']} Reg / {r['total_new_po']} New", None),
        "1. OE - New Item Types": (r['num_unique_new'], None),
        "2. DFM - Proceeding PO": (r['total_final_po'], t.get('t2', 0.0)),
        "2. DFM - Accepted New": (r['accepted_count'], None),
        "3. SMT - Total PO": (r['total_final_po'], t.get('t3', 0.0)),
        "3. SMT - Total Qty": (r['total_qty'], None),
        "3. SMT - Total Step": (r['total_smt_steps'], None),
        "3. SMT - Row Calculation": (f"{r['total_qty']} x {r['avg_smt']:.2f}", None),
        "3. SMT - Raw Data": (r['total_smt_raw'], None),
        "4. Assembly Data (Sum Qty)": (r['total_qty'], t.get('t4', 0.0)),
        "5. Testing - Total PO": (r['total_final_po'], t.get('t5', 0.0)),
        "5. Testing - Total Qty": (r['total_qty'], None),
        "5. Testing - Total Step": (r['total_test_steps'], None),
        "5. Testing - Row Calculation": (f"{r['total_qty']} x {r['avg_test']:.2f}", None),
        "5. Testing - Raw Data": (r['total_test_raw'], None),
        "6. Quality Check (Sum Qty)": (r['total_qty'], t.get('t6', 0.0)),
        "Total New Rows": (
            r['total_final_po'] + len(r['all_unique']) + r['total_smt_raw'] + r['total_qty'] + r['total_test_raw'] + r['total_qty'],
            t['total']
        )
    }
    return result

def run_simulation(params, num_chunks):
    p = params
    start_task = time.perf_counter()
    chunks = build_chunks(p, num_chunks)

    t1_s = time.perf_counter()
    partial_results = [process_chunk(c) for c in chunks]
    t1_d = time.perf_counter() - t1_s

    total_task_duration = time.perf_counter() - start_task
    reduced = reduce_results(partial_results, p)

    timings = {'t1': t1_d, 't2': 0.0, 't3': 0.0, 't4': 0.0, 't5': 0.0, 't6': 0.0, 'total': total_task_duration}
    return format_result(p, reduced, timings)

def run_simulation_parallel(params, num_workers):
    p = params
    start_task = time.perf_counter()
    chunks = build_chunks(p, num_workers)

    t_par_s = time.perf_counter()
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        partial_results = list(executor.map(process_chunk, chunks))
    t_par_d = time.perf_counter() - t_par_s

    total_task_duration = time.perf_counter() - start_task
    overhead = total_task_duration - t_par_d
    reduced = reduce_results(partial_results, p)

    timings = {'t1': 0.0, 't2': t_par_d, 't3': 0.0, 't4': 0.0, 't5': 0.0, 't6': 0.0, 'total': total_task_duration}
    result = format_result(p, reduced, timings)
    result['_overhead'] = overhead
    result['_par_work'] = t_par_d
    return result

def print_table(title, headers, all_results):
    step_names = [
        "1. OE - Total PO", "1. OE - Item Breakdown", "1. OE - New Item Types", "---",
        "2. DFM - Proceeding PO", "2. DFM - Accepted New", "---",
        "3. SMT - Total PO", "3. SMT - Total Qty", "3. SMT - Total Step", "3. SMT - Row Calculation", "3. SMT - Raw Data", "---",
        "4. Assembly Data (Sum Qty)", "---",
        "5. Testing - Total PO", "5. Testing - Total Qty", "5. Testing - Total Step", "5. Testing - Row Calculation", "5. Testing - Raw Data", "---",
        "6. Quality Check (Sum Qty)", "===",
        "Total New Rows"
    ]

    s_w = 29
    n_cols = len(headers)
    c_w = min(19, max(14, (140 - s_w) // n_cols - 3))
    print(f"\n{title}")
    h1 = f"{'Step':<{s_w}}"
    h2 = f"{'='*s_w}"
    for h in headers:
        h1 += f" | {h:<{c_w}}"
        h2 += f" | {'='*c_w}"

    print(h1)
    print(h2)

    for step in step_names:
        if step == "---":
            sep = f"{'-'*s_w}"
            for _ in headers: sep += f" + {'-'*c_w}"
            print(sep)
            continue
        if step == "===":
            sep = f"{'='*s_w}"
            for _ in headers: sep += f" | {'='*c_w}"
            print(sep)
            continue

        row = f"{step:<{s_w}}"
        for res_dict in all_results:
            val, dur = res_dict.get(step, (None, None))
            v_s = str(val) if val is not None else ""
            d_s = f"[{dur:.2f}]" if dur is not None else ""
            combined = f"{v_s} {d_s}".strip()
            combined = combined[:c_w]
            row += f" | {combined:<{c_w}}"
        print(row)

def run_config(config, num_cores):
    default = config['default_params']
    scenarios = config['benchmark_scenarios']

    scenario_params = []
    headers = []
    for sc in scenarios:
        p = default.copy()
        p.update(sc)
        scenario_params.append(p)
        headers.append(sc.get('DESC', 'Trial'))

    seq_results = [run_simulation(p, num_cores) for p in scenario_params]
    par_results = [run_simulation_parallel(p, num_cores) for p in scenario_params]

    return headers, scenario_params, seq_results, par_results

def extract_chart_data(headers, scenario_params, seq_results, par_results):
    chart_data = {
        "scenarios": headers,
        "sequential": {},
        "parallel": {}
    }
    for i, h in enumerate(headers):
        p = scenario_params[i]
        seq_total = seq_results[i]["Total New Rows"][1]
        par_total = par_results[i]["Total New Rows"][1]
        par_overhead = par_results[i].get('_overhead', 0.0)
        par_minus_overhead = par_total - par_overhead

        total_smt_machines = (p['NUM_PCBA_MACHINES'] + p['NUM_SOLDER_PASTE_MACHINES'] +
                              p['NUM_PNP_MACHINES'] + p['NUM_REFLOW_MACHINES'] + p['NUM_OVEN_MACHINES'])
        total_testing_machines = (p['NUM_ICT_MACHINES'] + p['NUM_BOARD_TEST_MACHINES'] +
                                  p['NUM_FCT_MACHINES'] + p['NUM_VISUAL_TEST_MACHINES'] +
                                  p['NUM_FLYING_PROBE_MACHINES'] + p['NUM_XRAY_MACHINES'])

        seq_smt_raw = seq_results[i]["3. SMT - Raw Data"][0]
        seq_test_raw = seq_results[i]["5. Testing - Raw Data"][0]
        seq_data_total = seq_smt_raw + seq_test_raw
        seq_smt_dur = seq_total * (seq_smt_raw / seq_data_total) if seq_data_total > 0 else 0
        seq_test_dur = seq_total * (seq_test_raw / seq_data_total) if seq_data_total > 0 else 0

        par_smt_raw = par_results[i]["3. SMT - Raw Data"][0]
        par_test_raw = par_results[i]["5. Testing - Raw Data"][0]
        par_data_total = par_smt_raw + par_test_raw
        par_smt_dur = par_minus_overhead * (par_smt_raw / par_data_total) if par_data_total > 0 else 0
        par_test_dur = par_minus_overhead * (par_test_raw / par_data_total) if par_data_total > 0 else 0

        chart_data["sequential"][h] = {
            "total": seq_total,
            "smt_duration": seq_smt_dur,
            "testing_duration": seq_test_dur,
            "total_po": seq_results[i]["2. DFM - Proceeding PO"][0],
            "total_new_rows": seq_results[i]["Total New Rows"][0],
            "smt_raw": seq_smt_raw,
            "testing_raw": seq_test_raw,
            "total_smt_machines": total_smt_machines,
            "total_testing_machines": total_testing_machines
        }
        chart_data["parallel"][h] = {
            "total": par_total,
            "total_minus_overhead": par_minus_overhead,
            "overhead": par_overhead,
            "smt_duration": par_smt_dur,
            "testing_duration": par_test_dur,
            "total_po": par_results[i]["2. DFM - Proceeding PO"][0],
            "total_new_rows": par_results[i]["Total New Rows"][0],
            "smt_raw": par_smt_raw,
            "testing_raw": par_test_raw,
            "total_smt_machines": total_smt_machines,
            "total_testing_machines": total_testing_machines
        }
    return chart_data

def benchmark():
    default = CONFIG['default_params']
    scenarios = CONFIG['benchmark_scenarios']
    num_cores = multiprocessing.cpu_count()

    print(f"Current manufacture condition:")
    print(f"Orders/Day: {default['ORDERS_PER_DAY']}")
    print(f"Registered Items: {default['INITIAL_REGISTERED_ITEMS']}")
    print(f"Qty Range: {default['MIN_QTY_PER_PO']}-{default['MAX_QTY_PER_PO']}")
    print(f"SMT Machines: PCBA({default['NUM_PCBA_MACHINES']}), Solder({default['NUM_SOLDER_PASTE_MACHINES']}), P&P({default['NUM_PNP_MACHINES']}), Reflow({default['NUM_REFLOW_MACHINES']}), Oven({default['NUM_OVEN_MACHINES']})")
    print(f"Testing Machines: ICT({default['NUM_ICT_MACHINES']}), Board({default['NUM_BOARD_TEST_MACHINES']}), FCT({default['NUM_FCT_MACHINES']}), Visual({default['NUM_VISUAL_TEST_MACHINES']}), Flying({default['NUM_FLYING_PROBE_MACHINES']}), X-ray({default['NUM_XRAY_MACHINES']})")
    print(f"Test Attempts: {default['MIN_TEST_ATTEMPTS']}-{default['MAX_TEST_ATTEMPTS']}")
    print(f"CPU Cores Available: {num_cores}\n")

    scenario_params = []
    headers = []
    for sc in scenarios:
        p = default.copy()
        p.update(sc)
        scenario_params.append(p)
        headers.append(sc.get('DESC', 'Trial'))

    start_seq = time.perf_counter()
    seq_results = [run_simulation(p, num_cores) for p in scenario_params]
    total_seq_wall = time.perf_counter() - start_seq

    print_table("Sequential Execution", headers, seq_results)

    start_par = time.perf_counter()
    par_results = [run_simulation_parallel(p, num_cores) for p in scenario_params]
    total_par_wall = time.perf_counter() - start_par

    print_table(f"Data-Parallel Execution ({num_cores} cores)", headers, par_results)

    seq_durations = [res["Total New Rows"][1] for res in seq_results]
    par_durations = [res["Total New Rows"][1] for res in par_results]
    par_overheads = [res['_overhead'] for res in par_results]
    par_works = [res['_par_work'] for res in par_results]

    print(f"\nPer-Scenario Speedup:")
    print(f"{'Scenario':<12} | {'Sequential':<14} | {'Parallel':<14} | {'Overhead':<14} | {'Speedup':<10}")
    print(f"{'='*12} | {'='*14} | {'='*14} | {'='*14} | {'='*10}")
    for i, h in enumerate(headers):
        sd = seq_durations[i]
        pd = par_durations[i]
        oh = par_overheads[i]
        speedup = sd / pd if pd > 0 else 0
        print(f"{h:<12} | {sd:<14.6f} | {pd:<14.6f} | {oh:<14.6f} | {speedup:<10.2f}x")

    seq_math = " + ".join([f"{d:.6f}" for d in seq_durations])
    par_math = " + ".join([f"{d:.6f}" for d in par_durations])
    overhead_math = " + ".join([f"{o:.6f}" for o in par_overheads])
    total_overhead = sum(par_overheads)
    corrected_par = total_par_wall - total_overhead

    print(f"\nOverall Batch Performance Comparison:")
    print(f"Sequential Total Wall-Clock: {total_seq_wall:.6f}s ({seq_math})")
    print(f"Parallel Total Wall-Clock:   {total_par_wall:.6f}s ({par_math})")
    print(f"Total Overhead:              {total_overhead:.6f}s ({overhead_math})")
    print(f"Parallel (minus Overhead):   {corrected_par:.6f}s")
    print(f"Parallel Speedup Factor:     {total_seq_wall/total_par_wall:.2f}x")
    print(f"Corrected Speedup Factor:    {total_seq_wall/corrected_par:.2f}x")

    config_old_path = os.path.join(os.path.dirname(__file__), 'config_old.json')
    with open(config_old_path, 'r') as f:
        config_old = json.load(f)

    print(f"\n{'='*60}")
    print(f"Running config_old.json scenarios...")
    print(f"{'='*60}")

    old_headers, old_params, old_seq, old_par = run_config(config_old, num_cores)

    print_table("Sequential Execution (config_old)", old_headers, old_seq)
    print_table(f"Data-Parallel Execution (config_old, {num_cores} cores)", old_headers, old_par)

    export_data = {
        "config_old": extract_chart_data(old_headers, old_params, old_seq, old_par),
        "config": extract_chart_data(headers, scenario_params, seq_results, par_results)
    }

    result_path = os.path.join(os.path.dirname(__file__), 'manufacture_flow_result.json')
    with open(result_path, 'w') as f:
        json.dump(export_data, f, indent=4)
    print(f"\nResults exported to {result_path}")

if __name__ == "__main__":
    benchmark()
