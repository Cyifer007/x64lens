/*
 * role-property-layout.h
 *
 * Development-only ABI authority shared by the C private-fact probe and its
 * reconciliation harness. The authoritative field values are emitted from
 * NASM's include/structs.inc by role-property-layout-authority.asm; this header
 * names descriptor slots and independently records the expected Patch 067 ABI.
 * It is not linked into the freestanding x64lens runtime.
 */
#ifndef X64LENS_ROLE_PROPERTY_LAYOUT_H
#define X64LENS_ROLE_PROPERTY_LAYOUT_H

#include <stddef.h>
#include <stdint.h>

#define X64LENS_ROLE_PROPERTY_LAYOUT_MAGIC UINT64_C(0x5836344c41594f55)
#define X64LENS_ROLE_PROPERTY_LAYOUT_VERSION UINT64_C(1)
#define X64LENS_ROLE_PROPERTY_LAYOUT_FIELD_COUNT UINT64_C(21)
#define X64LENS_ROLE_PROPERTY_LAYOUT_HEADER_QWORDS 3U
#define X64LENS_ROLE_PROPERTY_LAYOUT_QWORDS \
    (X64LENS_ROLE_PROPERTY_LAYOUT_HEADER_QWORDS + \
     (size_t)X64LENS_ROLE_PROPERTY_LAYOUT_FIELD_COUNT)
#define X64LENS_ROLE_PROPERTY_LAYOUT_BYTES \
    (X64LENS_ROLE_PROPERTY_LAYOUT_QWORDS * sizeof(uint64_t))

enum x64lens_role_property_layout_field {
    X64LENS_LAYOUT_PHDR_SUMMARY_PHNUM = 0,
    X64LENS_LAYOUT_PHDR_SUMMARY_INTERP_COUNT,
    X64LENS_LAYOUT_PHDR_SUMMARY_FLAGS1_COUNT,
    X64LENS_LAYOUT_PHDR_SUMMARY_SONAME_COUNT,
    X64LENS_LAYOUT_PHDR_SUMMARY_ROLE_EVIDENCE,
    X64LENS_LAYOUT_PHDR_SUMMARY_ROLE_STATE,
    X64LENS_LAYOUT_PHDR_SUMMARY_PROPERTY_VIEW_COUNT,
    X64LENS_LAYOUT_PHDR_SUMMARY_PROPERTY_CONTRIBUTOR_COUNT,
    X64LENS_LAYOUT_PHDR_SUMMARY_PROPERTY_NOTE_COUNT,
    X64LENS_LAYOUT_PHDR_SUMMARY_PROPERTY_FEATURE1_COUNT,
    X64LENS_LAYOUT_PHDR_SUMMARY_PROPERTY_FEATURE1_AND,
    X64LENS_LAYOUT_PHDR_SUMMARY_PROPERTY_FEATURE1_OR,
    X64LENS_LAYOUT_PHDR_SUMMARY_RECORD_SIZE,
    X64LENS_LAYOUT_PROPERTY_CTX_UNKNOWN_COUNT,
    X64LENS_LAYOUT_PROPERTY_CTX_CONFLICT_COUNT,
    X64LENS_LAYOUT_PROPERTY_CTX_OVERLAP_COUNT,
    X64LENS_LAYOUT_PROPERTY_CTX_IBT_STATE,
    X64LENS_LAYOUT_PROPERTY_CTX_SHSTK_STATE,
    X64LENS_LAYOUT_PROPERTY_CONTEXT_SIZE,
    X64LENS_LAYOUT_EXEC_REGION_RECORD_SIZE,
    X64LENS_LAYOUT_EXEC_REGION_MAX,
};

extern const uint64_t x64lens_role_property_layout_descriptor[];
extern const uint64_t x64lens_role_property_layout_descriptor_size;

static inline uint64_t
x64lens_role_property_layout_value(const uint64_t *descriptor,
                                   enum x64lens_role_property_layout_field field) {
    return descriptor[X64LENS_ROLE_PROPERTY_LAYOUT_HEADER_QWORDS + (size_t)field];
}

static inline int
x64lens_role_property_layout_validate(const uint64_t *descriptor,
                                      size_t descriptor_bytes) {
    static const uint64_t expected[X64LENS_ROLE_PROPERTY_LAYOUT_FIELD_COUNT] = {
        0, 144, 152, 168, 184, 192,
        216, 224, 232, 240, 248, 256, 264,
        24, 40, 48, 72, 80, 3160, 64, 64,
    };

    if (descriptor == NULL || descriptor_bytes != X64LENS_ROLE_PROPERTY_LAYOUT_BYTES) {
        return 0;
    }
    if (descriptor[0] != X64LENS_ROLE_PROPERTY_LAYOUT_MAGIC ||
        descriptor[1] != X64LENS_ROLE_PROPERTY_LAYOUT_VERSION ||
        descriptor[2] != X64LENS_ROLE_PROPERTY_LAYOUT_FIELD_COUNT) {
        return 0;
    }
    for (size_t i = 0; i < (size_t)X64LENS_ROLE_PROPERTY_LAYOUT_FIELD_COUNT; ++i) {
        if (descriptor[X64LENS_ROLE_PROPERTY_LAYOUT_HEADER_QWORDS + i] != expected[i]) {
            return 0;
        }
    }
    return 1;
}

#endif
