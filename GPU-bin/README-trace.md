/usr/local/cuda/extras/CUPTI/samples/cupti_trace_injection

The file libcupti_trace_injection.so is a shared object that is part of the NVIDIA CUDA Profiling Tools Interface (CUPTI). It enables tracing and profiling of CUDA applications by providing functions that inject tracing code into CUDA kernels. This makes it possible to collect performance data and analyze the behavior of CUDA workloads.

To use the injector, set the environment variable as follows:
```
export CUDA_INJECTION64_PATH=libcupti_trace_injection.so 
```

Running this setup will produce a GPU trace that includes DRIVER, RUNTIME, and CUPTI Trace data.