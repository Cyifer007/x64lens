/*
 * dynamic-metadata-fact-probe.c
 *
 * Development-only probe for private bounded DT_TEXTREL/DF_TEXTREL evidence.
 * It maps one supplied ELF read-only, invokes the normal assembly ELF/PHDR
 * path, validates both private layout descriptors, and emits only side-car
 * facts. It is not linked into the runtime and defines no public policy.
 */
#define _GNU_SOURCE
#include "dynamic-metadata-layout.h"
#include "role-property-layout.h"

#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

extern uint64_t x64lens_elf64_validate(const void *base, uint64_t size);
extern uint64_t x64lens_phdr_analyze(const void *base, uint64_t size,
                                     void *summary, void *regions,
                                     uint64_t max_regions, void *private_context);

static uint64_t dq(const unsigned char *base, size_t size, uint64_t offset) {
    uint64_t value = 0;
    if (offset > size || sizeof(value) > size - (size_t)offset) {
        fputs("dynamic-metadata-fact-probe: descriptor offset exceeds record\n", stderr);
        exit(7);
    }
    memcpy(&value, base + (size_t)offset, sizeof(value));
    return value;
}

static uint64_t dynamic_layout(enum x64lens_dynamic_metadata_layout_field field) {
    return x64lens_dynamic_metadata_layout_value(
        x64lens_dynamic_metadata_layout_descriptor, field);
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <elf>\n", argv[0]);
        return 2;
    }
    if (!x64lens_role_property_layout_validate(
            x64lens_role_property_layout_descriptor,
            (size_t)x64lens_role_property_layout_descriptor_size) ||
        !x64lens_dynamic_metadata_layout_validate(
            x64lens_dynamic_metadata_layout_descriptor,
            (size_t)x64lens_dynamic_metadata_layout_descriptor_size)) {
        fputs("dynamic-metadata-fact-probe: private layout descriptor mismatch\n", stderr);
        return 7;
    }

    const size_t summary_size = (size_t)x64lens_role_property_layout_value(
        x64lens_role_property_layout_descriptor,
        X64LENS_LAYOUT_PHDR_SUMMARY_RECORD_SIZE);
    const size_t region_size = (size_t)x64lens_role_property_layout_value(
        x64lens_role_property_layout_descriptor,
        X64LENS_LAYOUT_EXEC_REGION_RECORD_SIZE);
    const uint64_t region_max = x64lens_role_property_layout_value(
        x64lens_role_property_layout_descriptor,
        X64LENS_LAYOUT_EXEC_REGION_MAX);
    const size_t private_size = (size_t)dynamic_layout(
        X64LENS_DYNAMIC_LAYOUT_PRIVATE_CONTEXT_SIZE);
    const size_t dynamic_offset = (size_t)dynamic_layout(
        X64LENS_DYNAMIC_LAYOUT_PRIVATE_OFFSET);
    const size_t dynamic_size = (size_t)dynamic_layout(
        X64LENS_DYNAMIC_LAYOUT_CONTEXT_SIZE);
    if (summary_size == 0 || region_size == 0 || region_max == 0 ||
        region_size > SIZE_MAX / region_max || dynamic_offset > private_size ||
        dynamic_size > private_size - dynamic_offset) {
        fputs("dynamic-metadata-fact-probe: private layout sizes are invalid\n", stderr);
        return 7;
    }

    int fd = open(argv[1], O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) { perror("open"); return 3; }
    struct stat st;
    if (fstat(fd, &st) != 0 || st.st_size <= 0) {
        perror("fstat"); close(fd); return 3;
    }
    void *mapping = mmap(NULL, (size_t)st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    close(fd);
    if (mapping == MAP_FAILED) { perror("mmap"); return 3; }

    unsigned char *summary = calloc(1, summary_size);
    unsigned char *regions = calloc(1, region_size * (size_t)region_max);
    unsigned char *private_context = calloc(1, private_size);
    if (summary == NULL || regions == NULL || private_context == NULL) {
        fputs("dynamic-metadata-fact-probe: allocation failed\n", stderr);
        free(summary); free(regions); free(private_context);
        munmap(mapping, (size_t)st.st_size);
        return 1;
    }

    uint64_t status = x64lens_elf64_validate(mapping, (uint64_t)st.st_size);
    if (status == 0) {
        status = x64lens_phdr_analyze(mapping, (uint64_t)st.st_size,
                                      summary, regions, region_max,
                                      private_context);
    }
    const unsigned char *ctx = private_context + dynamic_offset;
    printf("{\"status\":%" PRIu64
           ",\"carrier_count\":%" PRIu64
           ",\"textrel_tag_count\":%" PRIu64
           ",\"flags_count\":%" PRIu64
           ",\"flags_first_value\":%" PRIu64
           ",\"flags_and\":%" PRIu64
           ",\"flags_or\":%" PRIu64
           ",\"full_value_conflicts\":%" PRIu64
           ",\"textrel_conflicts\":%" PRIu64
           ",\"table_complete\":%" PRIu64
           ",\"textrel_state\":%" PRIu64 "}\n",
           status,
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_CARRIER_COUNT)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_TEXTREL_TAG_COUNT)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_FLAGS_COUNT)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_FLAGS_FIRST_VALUE)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_FLAGS_AND)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_FLAGS_OR)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_FULL_VALUE_CONFLICTS)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_TEXTREL_CONFLICTS)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_TABLE_COMPLETE)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_TEXTREL_STATE)));

    free(summary); free(regions); free(private_context);
    munmap(mapping, (size_t)st.st_size);
    return 0;
}
