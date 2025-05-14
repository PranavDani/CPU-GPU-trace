#ifndef DW_PID_H
#define DW_PID_H

#include <sys/types.h>
#include <linux/perf_event.h>
#include <elfutils/libdwfl.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <linux/perf_event.h>
#include <linux/hw_breakpoint.h>
#include <sys/syscall.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <errno.h>
#include <elfutils/libdwfl.h>
#include <elfutils/libdw.h>
#include <libelf.h>
#include <signal.h> // Needed for kill()
#include <assert.h>
#include <czmq.h> // Include czmq's zclock functions
#include <nvml.h>

#ifdef __cplusplus
extern "C" {
#endif

    Dwfl* init_dwfl(pid_t pid);
    char* get_callchains(struct perf_event_mmap_page* buffer, Dwfl* dwfl);
    long long get_energy();
    long get_process_time(pid_t pid);
    long get_total_cpu_time();
    double get_gpu_power(unsigned int gpu_count);

#ifdef __cplusplus
}
#endif

#endif // DW_PID_H
