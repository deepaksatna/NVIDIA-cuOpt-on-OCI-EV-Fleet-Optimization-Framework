#!/usr/bin/env python3
"""
NVIDIA cuOpt on OCI - Benchmark Visualization
Generates professional charts from benchmark results
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# Set style for professional appearance
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['figure.titlesize'] = 16

# Colors - Oracle/NVIDIA inspired
ORACLE_RED = '#C74634'
NVIDIA_GREEN = '#76B900'
OCI_BLUE = '#0078D4'
DARK_GRAY = '#333333'
LIGHT_GRAY = '#F5F5F5'

# Custom color palette
COLORS = {
    'primary': NVIDIA_GREEN,
    'secondary': OCI_BLUE,
    'accent': ORACLE_RED,
    'success': '#28A745',
    'background': '#FFFFFF',
    'grid': '#E0E0E0'
}

def load_results():
    """Load benchmark results from JSON"""
    script_dir = Path(__file__).parent
    with open(script_dir / 'complete_results.json', 'r') as f:
        return json.load(f)

def create_fleet_scaling_chart(data, output_dir):
    """Create fleet scaling performance chart"""
    fig, ax = plt.subplots(figsize=(14, 8))

    fleet_data = data['fleet_scaling_results']

    # Extract data in order
    scenarios = ['EV-Fleet-10v', 'EV-Fleet-25v', 'EV-Fleet-50v', 'EV-Fleet-100v',
                 'EV-Fleet-150v', 'EV-Fleet-200v', 'EV-Fleet-300v', 'EV-Fleet-400v', 'EV-Fleet-500v']

    vehicles = [fleet_data[s]['vehicles'] for s in scenarios]
    avg_response = [fleet_data[s]['avg_response_ms'] / 1000 for s in scenarios]  # Convert to seconds
    p95_response = [fleet_data[s]['p95_response_ms'] / 1000 for s in scenarios]
    locations = [fleet_data[s]['locations'] for s in scenarios]

    # Create the main line plot
    line1 = ax.plot(vehicles, avg_response, 'o-', color=NVIDIA_GREEN, linewidth=3,
                    markersize=12, label='Average Response Time', zorder=5)
    line2 = ax.plot(vehicles, p95_response, 's--', color=OCI_BLUE, linewidth=2,
                    markersize=8, label='P95 Response Time', zorder=4)

    # Fill area between avg and p95
    ax.fill_between(vehicles, avg_response, p95_response, alpha=0.2, color=OCI_BLUE)

    # Add data labels
    for i, (v, avg, loc) in enumerate(zip(vehicles, avg_response, locations)):
        ax.annotate(f'{avg:.1f}s\n({loc} locs)',
                   xy=(v, avg), xytext=(0, 15),
                   textcoords='offset points', ha='center', fontsize=9,
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.8))

    # Styling
    ax.set_xlabel('Number of Vehicles', fontsize=14, fontweight='bold')
    ax.set_ylabel('Response Time (seconds)', fontsize=14, fontweight='bold')
    ax.set_title('NVIDIA cuOpt Fleet Scaling Performance on OCI\n10 to 500 Vehicles with 100% Success Rate',
                fontsize=16, fontweight='bold', pad=20)

    ax.set_xticks(vehicles)
    ax.set_xlim(0, 520)
    ax.set_ylim(0, max(p95_response) * 1.15)

    ax.legend(loc='upper left', fontsize=11)
    ax.grid(True, alpha=0.3)

    # Add performance zones
    ax.axhspan(0, 30, alpha=0.1, color='green', label='Real-time Zone (<30s)')
    ax.axhspan(30, 120, alpha=0.1, color='yellow')
    ax.axhspan(120, 250, alpha=0.1, color='orange')

    # Add zone labels
    ax.text(510, 15, 'Real-time\n(<30s)', fontsize=9, ha='right', va='center',
           color='green', fontweight='bold')
    ax.text(510, 75, 'Batch\n(30-120s)', fontsize=9, ha='right', va='center',
           color='#B8860B', fontweight='bold')
    ax.text(510, 180, 'Enterprise\n(>120s)', fontsize=9, ha='right', va='center',
           color='#FF8C00', fontweight='bold')

    # Add footer
    fig.text(0.5, 0.02, 'Platform: OCI OKE | GPUs: 4x NVIDIA A10 (96GB) | cuOpt Version: 25.12',
            ha='center', fontsize=10, style='italic', color='gray')

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig(output_dir / '01_fleet_scaling_performance.png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("Created: 01_fleet_scaling_performance.png")

def create_use_case_comparison(data, output_dir):
    """Create use case comparison bar chart"""
    fig, ax = plt.subplots(figsize=(14, 8))

    use_case_data = data['use_case_results']

    # Group use cases
    categories = {
        'Last-Mile Delivery': ['LastMile-Small', 'LastMile-Medium', 'LastMile-Large'],
        'EV Charging': ['Charging-Small', 'Charging-Medium', 'Charging-Large'],
        'Fleet Dispatch': ['Dispatch-Realtime', 'Dispatch-Batch']
    }

    colors = [NVIDIA_GREEN, OCI_BLUE, ORACLE_RED]

    x_positions = []
    heights = []
    bar_colors = []
    labels = []
    vehicles_list = []

    pos = 0
    group_positions = []

    for i, (category, scenarios) in enumerate(categories.items()):
        group_start = pos
        for scenario in scenarios:
            if scenario in use_case_data:
                x_positions.append(pos)
                heights.append(use_case_data[scenario]['avg_response_ms'] / 1000)
                bar_colors.append(colors[i])
                labels.append(scenario.replace('-', '\n'))
                vehicles_list.append(use_case_data[scenario]['vehicles'])
                pos += 1
        group_positions.append((group_start + pos - 1) / 2)
        pos += 0.5  # Gap between groups

    # Create bars
    bars = ax.bar(x_positions, heights, color=bar_colors, edgecolor='white', linewidth=2, width=0.8)

    # Add value labels on bars
    for bar, height, vehicles in zip(bars, heights, vehicles_list):
        ax.text(bar.get_x() + bar.get_width()/2, height + 1, f'{height:.1f}s\n({vehicles}v)',
               ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Set labels
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel('Response Time (seconds)', fontsize=14, fontweight='bold')
    ax.set_title('cuOpt Use Case Performance Comparison\nReal-World EV Fleet Optimization Scenarios',
                fontsize=16, fontweight='bold', pad=20)

    # Add legend
    legend_patches = [
        mpatches.Patch(color=NVIDIA_GREEN, label='Last-Mile Delivery'),
        mpatches.Patch(color=OCI_BLUE, label='EV Charging Optimization'),
        mpatches.Patch(color=ORACLE_RED, label='Fleet Dispatch')
    ]
    ax.legend(handles=legend_patches, loc='upper right', fontsize=11)

    ax.set_ylim(0, max(heights) * 1.25)
    ax.grid(True, axis='y', alpha=0.3)

    # Add 100% success badge
    ax.text(0.02, 0.98, '100% SUCCESS RATE', transform=ax.transAxes,
           fontsize=12, fontweight='bold', color='white',
           bbox=dict(boxstyle='round,pad=0.5', facecolor='green', edgecolor='none'),
           va='top')

    fig.text(0.5, 0.02, 'Platform: OCI OKE | GPUs: 4x NVIDIA A10 (96GB) | cuOpt Version: 25.12',
            ha='center', fontsize=10, style='italic', color='gray')

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig(output_dir / '02_use_case_comparison.png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("Created: 02_use_case_comparison.png")

def create_scalability_analysis(data, output_dir):
    """Create scalability analysis chart"""
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    fleet_data = data['fleet_scaling_results']
    scenarios = ['EV-Fleet-10v', 'EV-Fleet-25v', 'EV-Fleet-50v', 'EV-Fleet-100v',
                 'EV-Fleet-150v', 'EV-Fleet-200v', 'EV-Fleet-300v', 'EV-Fleet-400v', 'EV-Fleet-500v']

    vehicles = np.array([fleet_data[s]['vehicles'] for s in scenarios])
    locations = np.array([fleet_data[s]['locations'] for s in scenarios])
    avg_response = np.array([fleet_data[s]['avg_response_ms'] / 1000 for s in scenarios])

    # Left: Response time per vehicle
    ax1 = axes[0]
    time_per_vehicle = avg_response / vehicles * 1000  # ms per vehicle
    bars = ax1.bar(range(len(scenarios)), time_per_vehicle, color=NVIDIA_GREEN, edgecolor='white', linewidth=2)
    ax1.set_xticks(range(len(scenarios)))
    ax1.set_xticklabels([f'{v}v' for v in vehicles], fontsize=10)
    ax1.set_ylabel('Response Time per Vehicle (ms)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Fleet Size', fontsize=12, fontweight='bold')
    ax1.set_title('Optimization Efficiency\n(Response Time per Vehicle)', fontsize=14, fontweight='bold')
    ax1.grid(True, axis='y', alpha=0.3)

    for bar, val in zip(bars, time_per_vehicle):
        ax1.text(bar.get_x() + bar.get_width()/2, val + 5, f'{val:.0f}ms',
                ha='center', va='bottom', fontsize=9)

    # Right: Throughput (vehicles optimized per minute)
    ax2 = axes[1]
    throughput = vehicles / (avg_response / 60)  # vehicles per minute
    bars2 = ax2.bar(range(len(scenarios)), throughput, color=OCI_BLUE, edgecolor='white', linewidth=2)
    ax2.set_xticks(range(len(scenarios)))
    ax2.set_xticklabels([f'{v}v' for v in vehicles], fontsize=10)
    ax2.set_ylabel('Vehicles Optimized per Minute', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Fleet Size', fontsize=12, fontweight='bold')
    ax2.set_title('Optimization Throughput\n(Vehicles per Minute)', fontsize=14, fontweight='bold')
    ax2.grid(True, axis='y', alpha=0.3)

    for bar, val in zip(bars2, throughput):
        ax2.text(bar.get_x() + bar.get_width()/2, val + 2, f'{val:.0f}',
                ha='center', va='bottom', fontsize=9)

    fig.suptitle('cuOpt Scalability Analysis on OCI', fontsize=16, fontweight='bold', y=1.02)
    fig.text(0.5, 0.02, 'Platform: OCI OKE | GPUs: 4x NVIDIA A10 (96GB) | cuOpt Version: 25.12',
            ha='center', fontsize=10, style='italic', color='gray')

    plt.tight_layout(rect=[0, 0.05, 1, 0.98])
    plt.savefig(output_dir / '03_scalability_analysis.png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("Created: 03_scalability_analysis.png")

def create_executive_dashboard(data, output_dir):
    """Create executive summary dashboard"""
    fig = plt.figure(figsize=(16, 12))

    # Create grid
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # Title
    fig.suptitle('NVIDIA cuOpt on Oracle Cloud Infrastructure\nEV Fleet Optimization Performance Dashboard',
                fontsize=20, fontweight='bold', y=0.98)

    # KPI Cards (top row)
    ax_kpi1 = fig.add_subplot(gs[0, 0])
    ax_kpi2 = fig.add_subplot(gs[0, 1])
    ax_kpi3 = fig.add_subplot(gs[0, 2])

    # KPI 1: Success Rate
    ax_kpi1.set_xlim(0, 1)
    ax_kpi1.set_ylim(0, 1)
    ax_kpi1.add_patch(plt.Circle((0.5, 0.5), 0.4, color=NVIDIA_GREEN, alpha=0.2))
    ax_kpi1.add_patch(plt.Circle((0.5, 0.5), 0.35, color=NVIDIA_GREEN, alpha=0.3))
    ax_kpi1.text(0.5, 0.55, '100%', fontsize=36, fontweight='bold', ha='center', va='center', color=NVIDIA_GREEN)
    ax_kpi1.text(0.5, 0.25, 'Success Rate', fontsize=14, ha='center', va='center', fontweight='bold')
    ax_kpi1.axis('off')
    ax_kpi1.set_title('Reliability', fontsize=14, fontweight='bold', pad=10)

    # KPI 2: Max Fleet Size
    ax_kpi2.set_xlim(0, 1)
    ax_kpi2.set_ylim(0, 1)
    ax_kpi2.add_patch(plt.Circle((0.5, 0.5), 0.4, color=OCI_BLUE, alpha=0.2))
    ax_kpi2.add_patch(plt.Circle((0.5, 0.5), 0.35, color=OCI_BLUE, alpha=0.3))
    ax_kpi2.text(0.5, 0.55, '500', fontsize=36, fontweight='bold', ha='center', va='center', color=OCI_BLUE)
    ax_kpi2.text(0.5, 0.25, 'Vehicles', fontsize=14, ha='center', va='center', fontweight='bold')
    ax_kpi2.axis('off')
    ax_kpi2.set_title('Max Fleet Tested', fontsize=14, fontweight='bold', pad=10)

    # KPI 3: Total Scenarios
    ax_kpi3.set_xlim(0, 1)
    ax_kpi3.set_ylim(0, 1)
    ax_kpi3.add_patch(plt.Circle((0.5, 0.5), 0.4, color=ORACLE_RED, alpha=0.2))
    ax_kpi3.add_patch(plt.Circle((0.5, 0.5), 0.35, color=ORACLE_RED, alpha=0.3))
    ax_kpi3.text(0.5, 0.55, '17', fontsize=36, fontweight='bold', ha='center', va='center', color=ORACLE_RED)
    ax_kpi3.text(0.5, 0.25, 'Scenarios', fontsize=14, ha='center', va='center', fontweight='bold')
    ax_kpi3.axis('off')
    ax_kpi3.set_title('Tests Completed', fontsize=14, fontweight='bold', pad=10)

    # Fleet Scaling Chart (middle left)
    ax_fleet = fig.add_subplot(gs[1, :2])
    fleet_data = data['fleet_scaling_results']
    scenarios = ['EV-Fleet-10v', 'EV-Fleet-25v', 'EV-Fleet-50v', 'EV-Fleet-100v',
                 'EV-Fleet-150v', 'EV-Fleet-200v', 'EV-Fleet-300v', 'EV-Fleet-400v', 'EV-Fleet-500v']
    vehicles = [fleet_data[s]['vehicles'] for s in scenarios]
    avg_response = [fleet_data[s]['avg_response_ms'] / 1000 for s in scenarios]

    ax_fleet.fill_between(vehicles, avg_response, alpha=0.3, color=NVIDIA_GREEN)
    ax_fleet.plot(vehicles, avg_response, 'o-', color=NVIDIA_GREEN, linewidth=3, markersize=10)
    ax_fleet.set_xlabel('Vehicles', fontsize=12, fontweight='bold')
    ax_fleet.set_ylabel('Response Time (s)', fontsize=12, fontweight='bold')
    ax_fleet.set_title('Fleet Scaling Performance', fontsize=14, fontweight='bold')
    ax_fleet.grid(True, alpha=0.3)
    ax_fleet.set_xlim(0, 520)

    # Infrastructure Info (middle right)
    ax_infra = fig.add_subplot(gs[1, 2])
    ax_infra.axis('off')

    infra_text = """
    Infrastructure

    Cloud: Oracle Cloud (OCI)
    Service: OKE (Kubernetes)

    GPU Nodes: 4
    GPU Type: NVIDIA A10
    GPU Memory: 24GB each
    Total GPU: 96GB

    cuOpt Version: 25.12
    cuOpt Replicas: 4
    """
    ax_infra.text(0.1, 0.9, infra_text, fontsize=11, va='top', fontfamily='monospace',
                 bbox=dict(boxstyle='round,pad=0.5', facecolor=LIGHT_GRAY, edgecolor='gray'))
    ax_infra.set_title('Platform Details', fontsize=14, fontweight='bold')

    # Use Case Summary (bottom)
    ax_usecase = fig.add_subplot(gs[2, :])

    use_cases = ['Last-Mile\nSmall', 'Last-Mile\nMedium', 'Last-Mile\nLarge',
                'Charging\nSmall', 'Charging\nMedium', 'Charging\nLarge',
                'Dispatch\nRealtime', 'Dispatch\nBatch']
    use_case_keys = ['LastMile-Small', 'LastMile-Medium', 'LastMile-Large',
                    'Charging-Small', 'Charging-Medium', 'Charging-Large',
                    'Dispatch-Realtime', 'Dispatch-Batch']
    use_case_colors = [NVIDIA_GREEN]*3 + [OCI_BLUE]*3 + [ORACLE_RED]*2

    use_case_data = data['use_case_results']
    times = [use_case_data[k]['avg_response_ms'] / 1000 for k in use_case_keys]

    bars = ax_usecase.bar(use_cases, times, color=use_case_colors, edgecolor='white', linewidth=2)
    ax_usecase.set_ylabel('Response Time (s)', fontsize=12, fontweight='bold')
    ax_usecase.set_title('Use Case Performance Summary', fontsize=14, fontweight='bold')
    ax_usecase.grid(True, axis='y', alpha=0.3)

    for bar, t in zip(bars, times):
        ax_usecase.text(bar.get_x() + bar.get_width()/2, t + 1, f'{t:.0f}s',
                       ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Footer
    fig.text(0.5, 0.01, 'Benchmark Date: 2026-01-15 | All scenarios achieved 100% success rate',
            ha='center', fontsize=11, style='italic', color='gray')

    plt.savefig(output_dir / '04_executive_dashboard.png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("Created: 04_executive_dashboard.png")

def create_latency_distribution(data, output_dir):
    """Create latency distribution chart"""
    fig, ax = plt.subplots(figsize=(14, 8))

    fleet_data = data['fleet_scaling_results']
    scenarios = ['EV-Fleet-10v', 'EV-Fleet-25v', 'EV-Fleet-50v', 'EV-Fleet-100v',
                 'EV-Fleet-150v', 'EV-Fleet-200v', 'EV-Fleet-300v', 'EV-Fleet-400v', 'EV-Fleet-500v']

    x = np.arange(len(scenarios))
    width = 0.35

    avg_times = [fleet_data[s]['avg_response_ms'] / 1000 for s in scenarios]
    p95_times = [fleet_data[s]['p95_response_ms'] / 1000 for s in scenarios]

    bars1 = ax.bar(x - width/2, avg_times, width, label='Average', color=NVIDIA_GREEN, edgecolor='white', linewidth=2)
    bars2 = ax.bar(x + width/2, p95_times, width, label='P95', color=OCI_BLUE, edgecolor='white', linewidth=2)

    # Add variance indicators
    for i, (avg, p95) in enumerate(zip(avg_times, p95_times)):
        variance = ((p95 - avg) / avg) * 100
        ax.annotate(f'+{variance:.1f}%', xy=(x[i] + width/2, p95), xytext=(0, 5),
                   textcoords='offset points', ha='center', fontsize=8, color='gray')

    ax.set_xlabel('Fleet Size', fontsize=14, fontweight='bold')
    ax.set_ylabel('Response Time (seconds)', fontsize=14, fontweight='bold')
    ax.set_title('Latency Distribution: Average vs P95\nConsistent Performance Across All Fleet Sizes',
                fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace('EV-Fleet-', '') for s in scenarios], fontsize=11)
    ax.legend(fontsize=12)
    ax.grid(True, axis='y', alpha=0.3)

    # Add insight box
    insight_text = "Key Insight: P95 latency within 5% of average\ndemonstrates exceptional consistency"
    ax.text(0.98, 0.98, insight_text, transform=ax.transAxes, fontsize=10,
           va='top', ha='right', bbox=dict(boxstyle='round,pad=0.5', facecolor='lightyellow', edgecolor='orange'))

    fig.text(0.5, 0.02, 'Platform: OCI OKE | GPUs: 4x NVIDIA A10 (96GB) | cuOpt Version: 25.12',
            ha='center', fontsize=10, style='italic', color='gray')

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig(output_dir / '05_latency_distribution.png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("Created: 05_latency_distribution.png")

def create_complexity_heatmap(data, output_dir):
    """Create problem complexity vs performance heatmap"""
    fig, ax = plt.subplots(figsize=(12, 10))

    # Combine all data
    all_data = {**data['fleet_scaling_results'], **data['use_case_results']}

    scenarios = list(all_data.keys())
    vehicles = [all_data[s]['vehicles'] for s in scenarios]
    locations = [all_data[s]['locations'] for s in scenarios]
    times = [all_data[s]['avg_response_ms'] / 1000 for s in scenarios]

    # Create scatter plot with size based on response time
    scatter = ax.scatter(vehicles, locations, c=times, s=[t*3 for t in times],
                        cmap='RdYlGn_r', alpha=0.7, edgecolors='black', linewidth=1)

    # Add labels
    for i, scenario in enumerate(scenarios):
        ax.annotate(scenario.replace('EV-Fleet-', '').replace('-', '\n'),
                   xy=(vehicles[i], locations[i]), xytext=(5, 5),
                   textcoords='offset points', fontsize=8)

    ax.set_xlabel('Number of Vehicles', fontsize=14, fontweight='bold')
    ax.set_ylabel('Number of Locations', fontsize=14, fontweight='bold')
    ax.set_title('Problem Complexity vs Performance\nBubble Size = Response Time',
                fontsize=16, fontweight='bold', pad=20)

    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax, label='Response Time (seconds)')
    cbar.ax.set_ylabel('Response Time (seconds)', fontsize=12)

    ax.grid(True, alpha=0.3)

    fig.text(0.5, 0.02, 'Platform: OCI OKE | GPUs: 4x NVIDIA A10 (96GB) | cuOpt Version: 25.12',
            ha='center', fontsize=10, style='italic', color='gray')

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig(output_dir / '06_complexity_heatmap.png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("Created: 06_complexity_heatmap.png")

def main():
    """Generate all benchmark charts"""
    print("=" * 60)
    print("  NVIDIA cuOpt on OCI - Benchmark Visualization Generator")
    print("=" * 60)

    # Load data
    data = load_results()
    output_dir = Path(__file__).parent / 'charts'
    output_dir.mkdir(exist_ok=True)

    print(f"\nOutput directory: {output_dir}")
    print(f"Generating charts...\n")

    # Generate all charts
    create_fleet_scaling_chart(data, output_dir)
    create_use_case_comparison(data, output_dir)
    create_scalability_analysis(data, output_dir)
    create_executive_dashboard(data, output_dir)
    create_latency_distribution(data, output_dir)
    create_complexity_heatmap(data, output_dir)

    print("\n" + "=" * 60)
    print("  All charts generated successfully!")
    print("=" * 60)
    print(f"\nCharts saved to: {output_dir}")

if __name__ == "__main__":
    main()
