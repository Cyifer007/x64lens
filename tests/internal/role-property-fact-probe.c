/*
 * role-property-fact-probe.c
 *
 * Development-only fact probe for the Sprint 12 private binary-role and GNU-
 * property lattices. The probe maps one supplied ELF read-only, invokes the
 * same bounded assembly validators used by x64lens, and emits a compact JSON
 * record. It consumes an assembly-emitted ABI descriptor before interpreting
 * any assembly-owned record. It is not linked into the freestanding runtime
 * and does not define public report policy.
 */
#define _GNU_SOURCE
#include "role-property-layout.h"
#include "dynamic-metadata-layout.h"

#include <errno.h>
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
extern uint64_t x64lens_phdr_analyze(
    const void *base, uint64_t size, void *summary, void *regions,
    uint64_t max_regions, void *property_context);
extern uint64_t x64lens_binary_role_classify(void *summary);

static uint64_t qword(const unsigned char *base, size_t size, uint64_t offset) {
    uint64_t value = 0;
    if (offset > size || sizeof(value) > size - (size_t)offset) {
        fputs("role-property-fact-probe: descriptor offset exceeds record\n", stderr);
        exit(7);
    }
    memcpy(&value, base + (size_t)offset, sizeof(value));
    return value;
}

static uint64_t layout(enum x64lens_role_property_layout_field field) {
    return x64lens_role_property_layout_value(
        x64lens_role_property_layout_descriptor, field);
}

static void emit(uint64_t status, const unsigned char *summary,
                 size_t summary_size, const unsigned char *context,
                 size_t context_size) {
    printf(
        "{\"status\":%" PRIu64
        ",\"phnum\":%" PRIu64
        ",\"role_state\":%" PRIu64
        ",\"role_evidence\":%" PRIu64
        ",\"interp_count\":%" PRIu64
        ",\"flags1_count\":%" PRIu64
        ",\"soname_count\":%" PRIu64
        ",\"property_view_count\":%" PRIu64
        ",\"property_contributor_count\":%" PRIu64
        ",\"property_note_count\":%" PRIu64
        ",\"property_feature_count\":%" PRIu64
        ",\"property_feature_and\":%" PRIu64
        ",\"property_feature_or\":%" PRIu64
        ",\"property_unknown_count\":%" PRIu64
        ",\"property_conflict_count\":%" PRIu64
        ",\"property_overlap_count\":%" PRIu64
        ",\"ibt_state\":%" PRIu64
        ",\"shstk_state\":%" PRIu64 "}\n",
        status,
        qword(summary, summary_size, layout(X64LENS_LAYOUT_PHDR_SUMMARY_PHNUM)),
        qword(summary, summary_size, layout(X64LENS_LAYOUT_PHDR_SUMMARY_ROLE_STATE)),
        qword(summary, summary_size, layout(X64LENS_LAYOUT_PHDR_SUMMARY_ROLE_EVIDENCE)),
        qword(summary, summary_size, layout(X64LENS_LAYOUT_PHDR_SUMMARY_INTERP_COUNT)),
        qword(summary, summary_size, layout(X64LENS_LAYOUT_PHDR_SUMMARY_FLAGS1_COUNT)),
        qword(summary, summary_size, layout(X64LENS_LAYOUT_PHDR_SUMMARY_SONAME_COUNT)),
        qword(summary, summary_size, layout(X64LENS_LAYOUT_PHDR_SUMMARY_PROPERTY_VIEW_COUNT)),
        qword(summary, summary_size, layout(X64LENS_LAYOUT_PHDR_SUMMARY_PROPERTY_CONTRIBUTOR_COUNT)),
        qword(summary, summary_size, layout(X64LENS_LAYOUT_PHDR_SUMMARY_PROPERTY_NOTE_COUNT)),
        qword(summary, summary_size, layout(X64LENS_LAYOUT_PHDR_SUMMARY_PROPERTY_FEATURE1_COUNT)),
        qword(summary, summary_size, layout(X64LENS_LAYOUT_PHDR_SUMMARY_PROPERTY_FEATURE1_AND)),
        qword(summary, summary_size, layout(X64LENS_LAYOUT_PHDR_SUMMARY_PROPERTY_FEATURE1_OR)),
        qword(context, context_size, layout(X64LENS_LAYOUT_PROPERTY_CTX_UNKNOWN_COUNT)),
        qword(context, context_size, layout(X64LENS_LAYOUT_PROPERTY_CTX_CONFLICT_COUNT)),
        qword(context, context_size, layout(X64LENS_LAYOUT_PROPERTY_CTX_OVERLAP_COUNT)),
        qword(context, context_size, layout(X64LENS_LAYOUT_PROPERTY_CTX_IBT_STATE)),
        qword(context, context_size, layout(X64LENS_LAYOUT_PROPERTY_CTX_SHSTK_STATE)));
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
        fputs("role-property-fact-probe: private layout descriptor mismatch\n", stderr);
        return 7;
    }

    const uint64_t summary_size_u64 = layout(X64LENS_LAYOUT_PHDR_SUMMARY_RECORD_SIZE);
    const uint64_t context_size_u64 = x64lens_dynamic_metadata_layout_value(
        x64lens_dynamic_metadata_layout_descriptor,
        X64LENS_DYNAMIC_LAYOUT_PRIVATE_CONTEXT_SIZE);
    const uint64_t region_size_u64 = layout(X64LENS_LAYOUT_EXEC_REGION_RECORD_SIZE);
    const uint64_t region_max_u64 = layout(X64LENS_LAYOUT_EXEC_REGION_MAX);
    if (summary_size_u64 == 0 || context_size_u64 == 0 || region_size_u64 == 0 ||
        region_max_u64 == 0 || region_size_u64 > SIZE_MAX / region_max_u64 ||
        summary_size_u64 > SIZE_MAX || context_size_u64 > SIZE_MAX) {
        fputs("role-property-fact-probe: private layout sizes are invalid\n", stderr);
        return 7;
    }

    int fd = open(argv[1], O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) {
        perror("open");
        return 3;
    }
    struct stat st;
    if (fstat(fd, &st) != 0 || st.st_size <= 0) {
        perror("fstat");
        close(fd);
        return 3;
    }
    void *mapping = mmap(NULL, (size_t)st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    close(fd);
    if (mapping == MAP_FAILED) {
        perror("mmap");
        return 3;
    }

    const size_t summary_size = (size_t)summary_size_u64;
    const size_t context_size = (size_t)context_size_u64;
    const size_t regions_size = (size_t)(region_size_u64 * region_max_u64);
    unsigned char *summary = calloc(1, summary_size);
    unsigned char *context = calloc(1, context_size);
    unsigned char *regions = calloc(1, regions_size);
    if (summary == NULL || context == NULL || regions == NULL) {
        fputs("role-property-fact-probe: allocation failed\n", stderr);
        free(summary);
        free(context);
        free(regions);
        munmap(mapping, (size_t)st.st_size);
        return 1;
    }

    uint64_t status = x64lens_elf64_validate(mapping, (uint64_t)st.st_size);
    if (status == 0) {
        status = x64lens_phdr_analyze(
            mapping, (uint64_t)st.st_size, summary, regions,
            region_max_u64, context);
    }
    if (status == 0) {
        status = x64lens_binary_role_classify(summary);
    }
    emit(status, summary, summary_size, context, context_size);

    free(summary);
    free(context);
    free(regions);
    munmap(mapping, (size_t)st.st_size);
    return 0;
}
