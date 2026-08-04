/*
 * dynamic-metadata-fact-probe.c
 *
 * Development-only probe for private bounded dynamic metadata. It maps one
 * supplied ELF read-only, invokes the normal assembly ELF/PHDR path, validates
 * both private layout descriptors, and emits the complete fixed summary plus
 * exact hex-encoded RPATH/RUNPATH records. It is not linked into the runtime,
 * opens no target-derived path, and defines no public policy.
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

static void print_hex(const unsigned char *bytes, uint64_t length) {
    static const char alphabet[] = "0123456789abcdef";
    for (uint64_t i = 0; i < length; ++i) {
        unsigned char value = bytes[i];
        putchar(alphabet[value >> 4]);
        putchar(alphabet[value & 0x0f]);
    }
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
    const uint64_t search_record_count = dq(
        ctx, dynamic_size,
        dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_SEARCH_RECORD_COUNT));
    const uint64_t search_bytes_used = dq(
        ctx, dynamic_size,
        dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_SEARCH_BYTES_USED));
    const uint64_t search_record_max = dynamic_layout(
        X64LENS_DYNAMIC_LAYOUT_SEARCH_RECORD_MAX);
    const uint64_t search_bytes_max = dynamic_layout(
        X64LENS_DYNAMIC_LAYOUT_SEARCH_BYTES_MAX);
    const uint64_t records_offset = dynamic_layout(
        X64LENS_DYNAMIC_LAYOUT_CTX_SEARCH_RECORDS);
    const uint64_t record_size = dynamic_layout(
        X64LENS_DYNAMIC_LAYOUT_SEARCH_RECORD_SIZE);
    const uint64_t pool_offset = dynamic_layout(
        X64LENS_DYNAMIC_LAYOUT_CTX_SEARCH_BYTES);
    if (search_record_count > search_record_max ||
        search_bytes_used > search_bytes_max ||
        records_offset > dynamic_size ||
        record_size > dynamic_size ||
        search_record_count > (dynamic_size - records_offset) / record_size ||
        pool_offset > dynamic_size || search_bytes_max > dynamic_size - pool_offset) {
        fputs("dynamic-metadata-fact-probe: private search-path bounds are invalid\n", stderr);
        free(summary); free(regions); free(private_context);
        munmap(mapping, (size_t)st.st_size);
        return 7;
    }

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
           ",\"textrel_state\":%" PRIu64
           ",\"search_record_count\":%" PRIu64
           ",\"search_bytes_used\":%" PRIu64
           ",\"rpath_carrier_count\":%" PRIu64
           ",\"runpath_carrier_count\":%" PRIu64
           ",\"rpath_value_count\":%" PRIu64
           ",\"runpath_value_count\":%" PRIu64
           ",\"rpath_value_conflicts\":%" PRIu64
           ",\"runpath_value_conflicts\":%" PRIu64
           ",\"rpath_first_record\":%" PRIu64
           ",\"runpath_first_record\":%" PRIu64
           ",\"rpath_state\":%" PRIu64
           ",\"runpath_state\":%" PRIu64
           ",\"paths\":[",
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
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_TEXTREL_STATE)),
           search_record_count,
           search_bytes_used,
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_RPATH_CARRIER_COUNT)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_RUNPATH_CARRIER_COUNT)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_RPATH_VALUE_COUNT)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_RUNPATH_VALUE_COUNT)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_RPATH_VALUE_CONFLICTS)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_RUNPATH_VALUE_CONFLICTS)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_RPATH_FIRST_RECORD)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_RUNPATH_FIRST_RECORD)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_RPATH_STATE)),
           dq(ctx, dynamic_size, dynamic_layout(X64LENS_DYNAMIC_LAYOUT_CTX_RUNPATH_STATE)));

    for (uint64_t i = 0; i < search_record_count; ++i) {
        const uint64_t record = records_offset + i * record_size;
        const uint64_t byte_pool_record_offset = dq(
            ctx, dynamic_size,
            record + dynamic_layout(X64LENS_DYNAMIC_LAYOUT_SEARCH_RECORD_BYTE_POOL_OFFSET));
        const uint64_t byte_length = dq(
            ctx, dynamic_size,
            record + dynamic_layout(X64LENS_DYNAMIC_LAYOUT_SEARCH_RECORD_BYTE_LENGTH));
        if (byte_pool_record_offset > search_bytes_used ||
            byte_length > search_bytes_used - byte_pool_record_offset ||
            byte_pool_record_offset > search_bytes_max ||
            byte_length > search_bytes_max - byte_pool_record_offset) {
            fputs("dynamic-metadata-fact-probe: private path record exceeds pool\n", stderr);
            free(summary); free(regions); free(private_context);
            munmap(mapping, (size_t)st.st_size);
            return 7;
        }
        if (i != 0) putchar(',');
        printf("{\"tag\":%" PRIu64
               ",\"dynamic_index\":%" PRIu64
               ",\"dynamic_file_offset\":%" PRIu64
               ",\"string_table_offset\":%" PRIu64
               ",\"string_file_offset\":%" PRIu64
               ",\"byte_pool_offset\":%" PRIu64
               ",\"byte_length\":%" PRIu64
               ",\"bytes_hex\":\"",
               dq(ctx, dynamic_size, record + dynamic_layout(X64LENS_DYNAMIC_LAYOUT_SEARCH_RECORD_TAG)),
               dq(ctx, dynamic_size, record + dynamic_layout(X64LENS_DYNAMIC_LAYOUT_SEARCH_RECORD_INDEX)),
               dq(ctx, dynamic_size, record + dynamic_layout(X64LENS_DYNAMIC_LAYOUT_SEARCH_RECORD_DYNAMIC_FILE_OFFSET)),
               dq(ctx, dynamic_size, record + dynamic_layout(X64LENS_DYNAMIC_LAYOUT_SEARCH_RECORD_STRING_TABLE_OFFSET)),
               dq(ctx, dynamic_size, record + dynamic_layout(X64LENS_DYNAMIC_LAYOUT_SEARCH_RECORD_STRING_FILE_OFFSET)),
               byte_pool_record_offset, byte_length);
        print_hex(ctx + pool_offset + byte_pool_record_offset, byte_length);
        fputs("\"}", stdout);
    }
    fputs("]}\n", stdout);

    free(summary); free(regions); free(private_context);
    munmap(mapping, (size_t)st.st_size);
    return 0;
}
