/* Reconcile the NASM-emitted dynamic side-car descriptor with the independent C contract. */
#include "dynamic-metadata-layout.h"

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    if (!x64lens_dynamic_metadata_layout_validate(
            x64lens_dynamic_metadata_layout_descriptor,
            (size_t)x64lens_dynamic_metadata_layout_descriptor_size)) {
        fputs("sprint12-dynamic-metadata-layout-smoke: error: descriptor mismatch\n", stderr);
        return 1;
    }
    uint64_t mutated[X64LENS_DYNAMIC_METADATA_LAYOUT_QWORDS];
    memcpy(mutated, x64lens_dynamic_metadata_layout_descriptor, sizeof(mutated));
    mutated[1] += 1;
    if (x64lens_dynamic_metadata_layout_validate(mutated, sizeof(mutated))) {
        fputs("sprint12-dynamic-metadata-layout-smoke: error: version mutation accepted\n", stderr);
        return 1;
    }
    memcpy(mutated, x64lens_dynamic_metadata_layout_descriptor, sizeof(mutated));
    mutated[X64LENS_DYNAMIC_METADATA_LAYOUT_HEADER_QWORDS +
            X64LENS_DYNAMIC_LAYOUT_CTX_TEXTREL_STATE] += 8;
    if (x64lens_dynamic_metadata_layout_validate(mutated, sizeof(mutated))) {
        fputs("sprint12-dynamic-metadata-layout-smoke: error: offset mutation accepted\n", stderr);
        return 1;
    }
    memcpy(mutated, x64lens_dynamic_metadata_layout_descriptor, sizeof(mutated));
    mutated[X64LENS_DYNAMIC_METADATA_LAYOUT_HEADER_QWORDS +
            X64LENS_DYNAMIC_LAYOUT_CTX_RPATH_STATE] += 8;
    if (x64lens_dynamic_metadata_layout_validate(mutated, sizeof(mutated))) {
        fputs("sprint12-dynamic-metadata-layout-smoke: error: search-path offset mutation accepted\n", stderr);
        return 1;
    }
    printf("sprint12-dynamic-metadata-layout-smoke: ok qwords=%zu fields=%" PRIu64
           " descriptor_bytes=%" PRIu64 " context_bytes=%" PRIu64
           " private_context_bytes=%" PRIu64 " mutations=3\n",
           X64LENS_DYNAMIC_METADATA_LAYOUT_QWORDS,
           x64lens_dynamic_metadata_layout_descriptor[2],
           x64lens_dynamic_metadata_layout_descriptor_size,
           x64lens_dynamic_metadata_layout_value(
               x64lens_dynamic_metadata_layout_descriptor,
               X64LENS_DYNAMIC_LAYOUT_CONTEXT_SIZE),
           x64lens_dynamic_metadata_layout_value(
               x64lens_dynamic_metadata_layout_descriptor,
               X64LENS_DYNAMIC_LAYOUT_PRIVATE_CONTEXT_SIZE));
    return 0;
}
