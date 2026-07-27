/*
 * role-property-layout-reconciliation.c
 *
 * Reconcile the NASM-emitted private fact-probe descriptor with the independent
 * C ABI contract. The harness also proves that a version mutation and a field-
 * offset mutation are rejected. It is development validation only.
 */
#include "role-property-layout.h"

#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    if (!x64lens_role_property_layout_validate(
            x64lens_role_property_layout_descriptor,
            (size_t)x64lens_role_property_layout_descriptor_size)) {
        fputs("sprint12-role-property-layout-smoke: error: descriptor mismatch\n", stderr);
        return 1;
    }

    uint64_t mutated[X64LENS_ROLE_PROPERTY_LAYOUT_QWORDS];
    memcpy(mutated, x64lens_role_property_layout_descriptor, sizeof(mutated));
    mutated[1] += 1;
    if (x64lens_role_property_layout_validate(mutated, sizeof(mutated))) {
        fputs("sprint12-role-property-layout-smoke: error: version mutation accepted\n", stderr);
        return 1;
    }

    memcpy(mutated, x64lens_role_property_layout_descriptor, sizeof(mutated));
    mutated[X64LENS_ROLE_PROPERTY_LAYOUT_HEADER_QWORDS +
            X64LENS_LAYOUT_PHDR_SUMMARY_ROLE_STATE] += 8;
    if (x64lens_role_property_layout_validate(mutated, sizeof(mutated))) {
        fputs("sprint12-role-property-layout-smoke: error: offset mutation accepted\n", stderr);
        return 1;
    }

    printf("sprint12-role-property-layout-smoke: ok qwords=%zu fields=%" PRIu64
           " descriptor_bytes=%" PRIu64 " mutations=2\n",
           X64LENS_ROLE_PROPERTY_LAYOUT_QWORDS,
           x64lens_role_property_layout_descriptor[2],
           x64lens_role_property_layout_descriptor_size);
    return 0;
}
