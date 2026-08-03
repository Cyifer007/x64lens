/*
 * dynamic-metadata-layout.h
 *
 * Independent C contract for the private Sprint 12 dynamic-metadata side-car.
 * The paired NASM descriptor provides the implementation values; this header
 * names and independently checks every represented offset and size before a C
 * development probe interprets assembly-owned bytes.
 */
#ifndef X64LENS_DYNAMIC_METADATA_LAYOUT_H
#define X64LENS_DYNAMIC_METADATA_LAYOUT_H

#include <stddef.h>
#include <stdint.h>

#define X64LENS_DYNAMIC_METADATA_LAYOUT_MAGIC UINT64_C(0x58363444594e4d44)
#define X64LENS_DYNAMIC_METADATA_LAYOUT_VERSION UINT64_C(1)
#define X64LENS_DYNAMIC_METADATA_LAYOUT_FIELD_COUNT UINT64_C(19)
#define X64LENS_DYNAMIC_METADATA_LAYOUT_HEADER_QWORDS 3U
#define X64LENS_DYNAMIC_METADATA_LAYOUT_QWORDS \
    (X64LENS_DYNAMIC_METADATA_LAYOUT_HEADER_QWORDS + \
     (size_t)X64LENS_DYNAMIC_METADATA_LAYOUT_FIELD_COUNT)
#define X64LENS_DYNAMIC_METADATA_LAYOUT_BYTES \
    (X64LENS_DYNAMIC_METADATA_LAYOUT_QWORDS * sizeof(uint64_t))

#define X64LENS_DYNAMIC_METADATA_STATE_UNKNOWN UINT64_C(0)
#define X64LENS_DYNAMIC_METADATA_STATE_ABSENT UINT64_C(1)
#define X64LENS_DYNAMIC_METADATA_STATE_PRESENT UINT64_C(2)
#define X64LENS_DYNAMIC_METADATA_STATE_CONTRADICTORY UINT64_C(3)

enum x64lens_dynamic_metadata_layout_field {
    X64LENS_DYNAMIC_LAYOUT_CTX_CARRIER_COUNT = 0,
    X64LENS_DYNAMIC_LAYOUT_CTX_TEXTREL_TAG_COUNT,
    X64LENS_DYNAMIC_LAYOUT_CTX_FLAGS_COUNT,
    X64LENS_DYNAMIC_LAYOUT_CTX_FLAGS_FIRST_VALUE,
    X64LENS_DYNAMIC_LAYOUT_CTX_FLAGS_AND,
    X64LENS_DYNAMIC_LAYOUT_CTX_FLAGS_OR,
    X64LENS_DYNAMIC_LAYOUT_CTX_FULL_VALUE_CONFLICTS,
    X64LENS_DYNAMIC_LAYOUT_CTX_TEXTREL_CONFLICTS,
    X64LENS_DYNAMIC_LAYOUT_CTX_TABLE_COMPLETE,
    X64LENS_DYNAMIC_LAYOUT_CTX_TEXTREL_STATE,
    X64LENS_DYNAMIC_LAYOUT_CARRIER_TAG,
    X64LENS_DYNAMIC_LAYOUT_CARRIER_INDEX,
    X64LENS_DYNAMIC_LAYOUT_CARRIER_FILE_OFFSET,
    X64LENS_DYNAMIC_LAYOUT_CARRIER_VALUE,
    X64LENS_DYNAMIC_LAYOUT_CARRIER_RECORD_SIZE,
    X64LENS_DYNAMIC_LAYOUT_CARRIER_MAX,
    X64LENS_DYNAMIC_LAYOUT_CONTEXT_SIZE,
    X64LENS_DYNAMIC_LAYOUT_PRIVATE_OFFSET,
    X64LENS_DYNAMIC_LAYOUT_PRIVATE_CONTEXT_SIZE,
};

extern const uint64_t x64lens_dynamic_metadata_layout_descriptor[];
extern const uint64_t x64lens_dynamic_metadata_layout_descriptor_size;

static inline uint64_t
x64lens_dynamic_metadata_layout_value(
    const uint64_t *descriptor,
    enum x64lens_dynamic_metadata_layout_field field) {
    return descriptor[X64LENS_DYNAMIC_METADATA_LAYOUT_HEADER_QWORDS + (size_t)field];
}

static inline int
x64lens_dynamic_metadata_layout_validate(const uint64_t *descriptor,
                                         size_t descriptor_bytes) {
    static const uint64_t expected[X64LENS_DYNAMIC_METADATA_LAYOUT_FIELD_COUNT] = {
        0, 8, 16, 24, 32, 40, 48, 56, 64, 72,
        0, 8, 16, 24, 32, 64, 2128, 3160, 5288,
    };
    if (descriptor == NULL ||
        descriptor_bytes != X64LENS_DYNAMIC_METADATA_LAYOUT_BYTES) {
        return 0;
    }
    if (descriptor[0] != X64LENS_DYNAMIC_METADATA_LAYOUT_MAGIC ||
        descriptor[1] != X64LENS_DYNAMIC_METADATA_LAYOUT_VERSION ||
        descriptor[2] != X64LENS_DYNAMIC_METADATA_LAYOUT_FIELD_COUNT) {
        return 0;
    }
    for (size_t i = 0; i < (size_t)X64LENS_DYNAMIC_METADATA_LAYOUT_FIELD_COUNT; ++i) {
        if (descriptor[X64LENS_DYNAMIC_METADATA_LAYOUT_HEADER_QWORDS + i] != expected[i]) {
            return 0;
        }
    }
    return 1;
}

#endif
