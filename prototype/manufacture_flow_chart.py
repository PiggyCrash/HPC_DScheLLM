import json
import os
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from matplotlib import rcParams

def load_results():
    result_path = os.path.join(os.path.dirname(__file__), 'manufacture_flow_result.json')
    with open(result_path, 'r') as f:
        return json.load(f)

def build_combined_data(data):
    all_scenarios = []
    seq_totals = []
    par_corrected = []
    seq_smt_dur = []
    par_smt_dur = []
    seq_test_dur = []
    par_test_dur = []
    seq_total_po = []
    par_total_po = []
    total_smt_machines = []
    total_testing_machines = []

    for config_key in ['config_old', 'config']:
        cfg = data[config_key]
        for sc in cfg['scenarios']:
            all_scenarios.append(sc)
            seq_totals.append(cfg['sequential'][sc]['total'])
            par_corrected.append(cfg['parallel'][sc]['total_minus_overhead'])
            seq_smt_dur.append(cfg['sequential'][sc]['smt_duration'])
            par_smt_dur.append(cfg['parallel'][sc]['smt_duration'])
            seq_test_dur.append(cfg['sequential'][sc]['testing_duration'])
            par_test_dur.append(cfg['parallel'][sc]['testing_duration'])
            seq_total_po.append(cfg['sequential'][sc]['total_po'])
            par_total_po.append(cfg['parallel'][sc]['total_po'])
            total_smt_machines.append(cfg['sequential'][sc]['total_smt_machines'])
            total_testing_machines.append(cfg['sequential'][sc]['total_testing_machines'])

    return {
        'scenarios': all_scenarios,
        'seq_totals': seq_totals,
        'par_corrected': par_corrected,
        'seq_smt_dur': seq_smt_dur,
        'par_smt_dur': par_smt_dur,
        'seq_test_dur': seq_test_dur,
        'par_test_dur': par_test_dur,
        'seq_total_po': seq_total_po,
        'par_total_po': par_total_po,
        'total_smt_machines': total_smt_machines,
        'total_testing_machines': total_testing_machines
    }

def setup_style():
    rcParams['font.family'] = 'serif'
    rcParams['font.size'] = 10
    rcParams['axes.linewidth'] = 0.8
    rcParams['xtick.major.width'] = 0.6
    rcParams['ytick.major.width'] = 0.6
    rcParams['xtick.direction'] = 'in'
    rcParams['ytick.direction'] = 'in'
    rcParams['xtick.major.size'] = 4
    rcParams['ytick.major.size'] = 4

def render_charts(cd):
    setup_style()

    scenarios = cd['scenarios']
    n = len(scenarios)
    x = np.arange(n)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 9))
    fig.patch.set_facecolor('white')

    bar_width = 0.30

    ax1.set_facecolor('white')
    ax1.bar(x - bar_width / 2, cd['seq_totals'], bar_width,
            label='Sequential', color='#D94F4F', edgecolor='#333', linewidth=0.5)
    ax1.bar(x + bar_width / 2, cd['par_corrected'], bar_width,
            label='Parallel (minus Overhead)', color='#4A90C4', edgecolor='#333', linewidth=0.5)

    ax1.plot(x, cd['seq_smt_dur'], marker='o', linewidth=1.4, markersize=4,
             color='#D48B2C', linestyle='-', label='SMT Duration (Seq)', zorder=5)
    ax1.plot(x, cd['seq_test_dur'], marker='s', linewidth=1.4, markersize=4,
             color='#3A9A5B', linestyle='-', label='Testing Duration (Seq)', zorder=5)
    ax1.plot(x, cd['par_smt_dur'], marker='^', linewidth=1.4, markersize=4,
             color='#E8A838', linestyle='--', label='SMT Duration (Par)', zorder=5)
    ax1.plot(x, cd['par_test_dur'], marker='D', linewidth=1.4, markersize=4,
             color='#5CC47A', linestyle='--', label='Testing Duration (Par)', zorder=5)

    ax1.set_xlabel('Company Number', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Duration (seconds)', fontsize=11, fontweight='bold')
    ax1.set_title('(a) Sequential vs Parallel Duration with SMT & Testing Phase',
                  fontsize=12, fontweight='bold', pad=10)
    ax1.set_xticks(x)
    ax1.set_xticklabels(scenarios, fontsize=9)
    ax1.legend(fontsize=7, loc='upper left', frameon=True, fancybox=False,
               edgecolor='#999', ncol=2)
    for spine in ax1.spines.values():
        spine.set_color('#333')

    ax2.set_facecolor('white')
    bar_width2 = 0.40

    smt_m = np.array(cd['total_smt_machines'])
    test_m = np.array(cd['total_testing_machines'])
    total_po = np.array(cd['seq_total_po'])

    ax2.bar(x, total_po, bar_width2,
            label='Total PO', color='#4A90C4', edgecolor='#333', linewidth=0.5)

    ax2_twin = ax2.twinx()
    ax2_twin.plot(x, smt_m, marker='o', linewidth=1.8, markersize=5,
                  color='#D94F4F', linestyle='-', label='SMT Machines', zorder=5)
    ax2_twin.plot(x, test_m, marker='s', linewidth=1.8, markersize=5,
                  color='#27AE60', linestyle='-', label='Testing Machines', zorder=5)
    ax2_twin.set_ylabel('Machine Count', fontsize=11, fontweight='bold')
    ax2_twin.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, _: f'{val:,.0f}'))
    ax2_twin.spines['top'].set_visible(False)
    for spine in ax2_twin.spines.values():
        spine.set_color('#333')

    ax2.set_xlabel('Company Number', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Total PO', fontsize=11, fontweight='bold')
    ax2.set_title('(b) Total PO + Machine Allocation',
                  fontsize=12, fontweight='bold', pad=10)
    ax2.set_xticks(x)
    ax2.set_xticklabels(scenarios, fontsize=9)
    ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda val, _: f'{val:,.0f}'))
    for spine in ax2.spines.values():
        spine.set_color('#333')

    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, fontsize=7, loc='upper left',
               frameon=True, fancybox=False, edgecolor='#999')

    plt.tight_layout(pad=2.0)

    chart_path = os.path.join(os.path.dirname(__file__), 'manufacture_flow_chart.png')
    plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"Chart saved to {chart_path}")
    plt.show()

if __name__ == "__main__":
    data = load_results()
    cd = build_combined_data(data)
    render_charts(cd)
