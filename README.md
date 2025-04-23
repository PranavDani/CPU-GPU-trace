# CPU-GPU Trace

## Overview
This project provides tools for tracing CPU and GPU performance using cgroups. The main script, `start_cgroup.sh`, creates a cgroup for a target executable, runs the executable, traces its performance using `dw-pid`, and processes the results to generate flame graphs.

## Prerequisites
- A Linux system with cgroup support.
- NVIDIA drivers and development libraries (e.g., `nvidia-driver-550` and `libnvidia-ml-dev`).
- Build tools (e.g., `make`) to compile `dw-pid` located in the `CPU_Trace` directory.
- Perl and any dependencies for `flamegraph.pl`.

## Usage
Run the script with the path to the executable and any arguments:
```
./start_cgroup.sh <executable_path> [<executable_args>...]
```
The script will:
- Create a result directory (`./Result/<executable_name>`).
- Create a cgroup under the `perf_event` controller.
- Run the executable and add its PID to the cgroup.
- Trace the executable’s performance with `dw-pid` and generate CSV output.
- Process the trace data to produce energy and CPU flame graphs.

## Files
- **start_cgroup.sh**: Main shell script to handle cgroup management, tracing, and report generation.
- **CPU_Trace/**: Contains tracing tools including `dw-pid`.
- **Result/**: Output directory where trace files and generated reports are saved.
- **collapse_report.py** and **flamegraph.pl**: Utilities used to generate and visualize reports.

## Cleanup
The script automatically removes the created cgroup upon exit. In case of errors during the execution or PID addition, cleanup routines remove partial configurations.

For further details, consult individual script comments and utility documentation.
