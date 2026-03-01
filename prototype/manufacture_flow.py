import random
import time
import json
import os

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

def run_simulation(params):
    p = params
    start_total = time.perf_counter()

    reg_items = [Item(f"Prod-Reg-{i+1:04d}", p) for i in range(p['INITIAL_REGISTERED_ITEMS'])]
    num_unique_new = p['ORDERS_PER_DAY'] // 10
    new_items_unique = [Item(f"Prod-New-{i+1:04d}", p, is_new=True) for i in range(num_unique_new)]
    
    all_pos = []
    t1_s = time.perf_counter()
    reg_item_po_count = 0
    new_item_po_count = 0
    for i in range(p['ORDERS_PER_DAY']):
        is_new = random.random() < 0.1
        if is_new:
            item = random.choice(new_items_unique)
            new_item_po_count += 1
        else:
            item = random.choice(reg_items)
            reg_item_po_count += 1
        qty = random.randint(p['MIN_QTY_PER_PO'], p['MAX_QTY_PER_PO'])
        all_pos.append(PO(f"PO-{i+1:04d}", item, qty))
    t1_d = time.perf_counter() - t1_s

    t2_s = time.perf_counter()
    accepted_new_items = [it for it in new_items_unique if random.random() > p['DFM_REJECTION_RATE']]
    final_pos = [po for po in all_pos if not po.item.is_new or po.item in accepted_new_items]
    t2_d = time.perf_counter() - t2_s

    t3_s = time.perf_counter()
    total_po = len(final_pos)
    total_qty = sum(po.qty for po in final_pos)
    total_steps = sum(len(po.item.smt_sequence) for po in final_pos)
    smt_raw_data = sum(po.qty * len(po.item.smt_sequence) for po in final_pos)
    avg_steps = total_steps / total_po if total_po > 0 else 0
    t3_d = time.perf_counter() - t3_s

    t4_s = time.perf_counter()
    assembly_data = total_qty
    t4_d = time.perf_counter() - t4_s

    t5_s = time.perf_counter()
    total_po_test = len(final_pos)
    total_qty_test = sum(po.qty for po in final_pos)
    total_steps_test = sum(len(po.item.test_sequence) for po in final_pos)
    testing_raw_data = sum(po.qty * len(po.item.test_sequence) for po in final_pos)
    avg_steps_test = total_steps_test / total_po_test if total_po_test > 0 else 0
    t5_d = time.perf_counter() - t5_s

    t6_s = time.perf_counter()
    quality_check = total_qty_test
    t6_d = time.perf_counter() - t6_s

    total_duration = time.perf_counter() - start_total
    
    results = {
        "1. OE - Total PO": (p['ORDERS_PER_DAY'], t1_d),
        "1. OE - Item Breakdown": (f"{reg_item_po_count} Reg / {new_item_po_count} New", None),
        "1. OE - New Item Types": (num_unique_new, None),
        "2. DFM - Proceeding PO": (len(final_pos), t2_d),
        "2. DFM - Accepted New": (len(accepted_new_items), None),
        "3. SMT - Total PO": (total_po, t3_d),
        "3. SMT - Total Qty": (total_qty, None),
        "3. SMT - Total Step": (total_steps, None),
        "3. SMT - Row Calculation": (f"{total_qty} x {avg_steps:.2f}", None),
        "3. SMT - Raw Data": (smt_raw_data, None),
        "4. Assembly Data (Sum Qty)": (assembly_data, t4_d),
        "5. Testing - Total PO": (total_po_test, t5_d),
        "5. Testing - Total Qty": (total_qty_test, None),
        "5. Testing - Total Step": (total_steps_test, None),
        "5. Testing - Row Calculation": (f"{total_qty_test} x {avg_steps_test:.2f}", None),
        "5. Testing - Raw Data": (testing_raw_data, None),
        "6. Quality Check (Sum Qty)": (quality_check, t6_d),
        "Total New Rows": (len(final_pos) + len(set(po.item for po in final_pos)) + smt_raw_data + total_qty + testing_raw_data + total_qty_test, total_duration)
    }
    return results

def benchmark():
    default = CONFIG['default_params']
    scenarios = CONFIG['benchmark_scenarios']
    
    print(f"Current manufacture condition:")
    print(f"Orders/Day: {default['ORDERS_PER_DAY']}")
    print(f"Registered Items: {default['INITIAL_REGISTERED_ITEMS']}")
    print(f"Qty Range: {default['MIN_QTY_PER_PO']}-{default['MAX_QTY_PER_PO']}")
    print(f"SMT Machines: PCBA({default['NUM_PCBA_MACHINES']}), Solder({default['NUM_SOLDER_PASTE_MACHINES']}), P&P({default['NUM_PNP_MACHINES']}), Reflow({default['NUM_REFLOW_MACHINES']}), Oven({default['NUM_OVEN_MACHINES']})")
    print(f"Testing Machines: ICT({default['NUM_ICT_MACHINES']}), Board({default['NUM_BOARD_TEST_MACHINES']}), FCT({default['NUM_FCT_MACHINES']}), Visual({default['NUM_VISUAL_TEST_MACHINES']}), Flying({default['NUM_FLYING_PROBE_MACHINES']}), X-ray({default['NUM_XRAY_MACHINES']})")
    print(f"Test Attempts: {default['MIN_TEST_ATTEMPTS']}-{default['MAX_TEST_ATTEMPTS']}\n")

    all_results = []
    headers = []
    for sc in scenarios:
        run_params = default.copy()
        run_params.update(sc)
        all_results.append(run_simulation(run_params))
        headers.append(sc.get('DESC', 'Trial'))

    step_names = [
        "1. OE - Total PO", "1. OE - Item Breakdown", "1. OE - New Item Types", "---",
        "2. DFM - Proceeding PO", "2. DFM - Accepted New", "---",
        "3. SMT - Total PO", "3. SMT - Total Qty", "3. SMT - Total Step", "3. SMT - Row Calculation", "3. SMT - Raw Data", "---",
        "4. Assembly Data (Sum Qty)", "---",
        "5. Testing - Total PO", "5. Testing - Total Qty", "5. Testing - Total Step", "5. Testing - Row Calculation", "5. Testing - Raw Data", "---",
        "6. Quality Check (Sum Qty)", "===",
        "Total New Rows"
    ]

    s_w, c_w = 28, 22
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
            d_s = f"[{dur:.6f}]" if dur is not None else ""
            combined = f"{v_s} {d_s}".strip()
            row += f" | {combined:<{c_w}}"
        print(row)

if __name__ == "__main__":
    benchmark()
