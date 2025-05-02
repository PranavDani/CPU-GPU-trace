#include <cupti.h>

// Callback function for CUDA API events
void CUPTIAPI callbackHandler(void* userdata, CUpti_CallbackDomain domain,
    CUpti_CallbackId cbid, const void* cbdata) {
    if (domain == CUPTI_CB_DOMAIN_RUNTIME_API) {
        const CUpti_CallbackData* data = (CUpti_CallbackData*)cbdata;
        if (data->callbackSite == CUPTI_API_ENTER &&
            cbid == CUPTI_RUNTIME_TRACE_CBID_cudaLaunchKernel_v7000) {
            // Extract kernel launch details
            const cudaLaunchKernel_params* params =
                (cudaLaunchKernel_params*)data->functionParams;
            printf("Kernel launched: %s\n", params->symbolName);
            printf("Grid: (%d,%d,%d), Block: (%d,%d,%d)\n",
                params->gridDim.x, params->gridDim.y, params->gridDim.z,
                params->blockDim.x, params->blockDim.y, params->blockDim.z);
        }
    }
}

int main() {
    CUpti_SubscriberHandle subscriber;
    cuptiSubscribe(&subscriber, callbackHandler, NULL);
    cuptiEnableDomain(1, subscriber, CUPTI_CB_DOMAIN_RUNTIME_API);

    // Attach to external process here (see Step 3)
    return 0;
}
