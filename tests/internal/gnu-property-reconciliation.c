/*
 * gnu-property-reconciliation.c
 *
 * Purpose:
 *   Independent C-side oracle for the private bounded GNU property-note
 *   parser. The runtime remains freestanding NASM; this executable is a
 *   development-only harness linked against gnu_property.asm and bounds.asm.
 *
 * Scope:
 *   Exercises canonical carrier views, original PHDR contributors, bounded
 *   note/property parsing, IBT/SHSTK states, duplicates, conflicts, unknowns,
 *   truncation, padding, overlap, and implementation caps. It does not inspect
 *   public reports or alter runtime schema fields.
 */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern uint64_t x64lens_gnu_property_context_init(void *context, void *summary);
extern uint64_t x64lens_gnu_property_register_carrier(
    const void *base, uint64_t file_size, void *context,
    uint64_t phdr_index, const void *phdr);
extern uint64_t x64lens_gnu_property_parse(
    const void *base, uint64_t file_size, void *context, void *summary);

enum {
    EXIT_OK = 0,
    EXIT_MALFORMED_ELF = 5,
    EXIT_UNSUPPORTED = 6,
    EXIT_BOUNDS = 7,
    PT_NOTE = 4,
    PT_GNU_PROPERTY = 0x6474e553u,
    GNU_PROPERTY_X86_FEATURE_1_AND = 0xc0000002u,
    GNU_PROPERTY_X86_FEATURE_1_IBT = 1u,
    GNU_PROPERTY_X86_FEATURE_1_SHSTK = 2u,
    GNU_PROPERTY_STATE_UNKNOWN = 0,
    GNU_PROPERTY_STATE_ABSENT = 1,
    GNU_PROPERTY_STATE_PRESENT = 2,
    GNU_PROPERTY_STATE_CONTRADICTORY = 3,
    PHDR_SUMMARY_RECORD_SIZE = 264,
    GNU_PROPERTY_CONTEXT_SIZE = 3160,
    GNU_PROPERTY_CARRIER_MAX = 32,
    GNU_PROPERTY_CONTRIBUTOR_MAX = 64,
    GNU_PROPERTY_NOTE_SCAN_MAX = 256,
};

enum {
    P_TYPE = 0,
    P_OFFSET = 8,
    P_FILESZ = 32,
    P_MEMSZ = 40,
    P_ALIGN = 48,
};

enum {
    SUM_VIEW_COUNT = 216,
    SUM_CONTRIBUTOR_COUNT = 224,
    SUM_NOTE_COUNT = 232,
    SUM_FEATURE_COUNT = 240,
    SUM_FEATURE_AND = 248,
    SUM_FEATURE_OR = 256,
};

enum {
    CTX_CARRIER_COUNT = 0,
    CTX_CONTRIBUTOR_COUNT = 8,
    CTX_NOTE_COUNT = 16,
    CTX_UNKNOWN_COUNT = 24,
    CTX_FEATURE_COUNT = 32,
    CTX_CONFLICT_COUNT = 40,
    CTX_OVERLAP_COUNT = 48,
    CTX_FEATURE_AND = 56,
    CTX_FEATURE_OR = 64,
    CTX_IBT_STATE = 72,
    CTX_SHSTK_STATE = 80,
    CTX_CARRIERS = 88,
    CARRIER_OFFSET = 0,
    CARRIER_SIZE = 8,
    CARRIER_KIND = 16,
    CARRIER_ALIGN = 24,
    CARRIER_RECORD_SIZE = 32,
    CARRIER_ALIGN_4 = 1,
    CARRIER_ALIGN_8 = 2,
    CTX_CONTRIBUTORS = CTX_CARRIERS + GNU_PROPERTY_CARRIER_MAX * CARRIER_RECORD_SIZE,
    CONTRIB_PHDR_INDEX = 0,
    CONTRIB_PHDR_TYPE = 8,
    CONTRIB_CARRIER_SLOT = 16,
    CONTRIB_RECORD_SIZE = 24,
};

_Static_assert(PHDR_SUMMARY_RECORD_SIZE == 264, "summary contract");
_Static_assert(PHDR_SUMMARY_RECORD_SIZE - 200 <= 64, "summary growth ceiling");
_Static_assert(GNU_PROPERTY_CONTEXT_SIZE <= 4096, "context must remain bounded to 4 KiB");

typedef struct {
    uint8_t image[131072];
    uint8_t summary[PHDR_SUMMARY_RECORD_SIZE];
    uint8_t context[GNU_PROPERTY_CONTEXT_SIZE];
    uint8_t phdrs[128 * 56];
} fixture_t;

static uint64_t qword(const uint8_t *p, size_t off) {
    uint64_t value;
    memcpy(&value, p + off, sizeof(value));
    return value;
}

static void put32(uint8_t *p, size_t off, uint32_t value) {
    memcpy(p + off, &value, sizeof(value));
}

static void put64(uint8_t *p, size_t off, uint64_t value) {
    memcpy(p + off, &value, sizeof(value));
}

static void fail(const char *case_name, const char *detail) {
    fprintf(stderr, "gnu-property-reconciliation: %s: %s\n", case_name, detail);
    exit(1);
}

static void expect_u64(const char *name, const char *field, uint64_t got, uint64_t expected) {
    if (got != expected) {
        fprintf(stderr, "%s: %s got=%llu expected=%llu\n", name, field,
                (unsigned long long)got, (unsigned long long)expected);
        exit(1);
    }
}

static void reset(fixture_t *f) {
    memset(f, 0, sizeof(*f));
    if (x64lens_gnu_property_context_init(f->context, f->summary) != EXIT_OK) {
        fail("reset", "context init failed");
    }
}

static uint8_t *phdr(fixture_t *f, size_t index, uint32_t type,
                     uint64_t off, uint64_t size) {
    uint8_t *p = f->phdrs + index * 56;
    memset(p, 0, 56);
    put32(p, P_TYPE, type);
    put64(p, P_OFFSET, off);
    put64(p, P_FILESZ, size);
    put64(p, P_MEMSZ, size);
    put64(p, P_ALIGN, 8);
    return p;
}

static size_t append_property(uint8_t *dst, size_t pos, uint32_t type,
                              const uint8_t *data, uint32_t size,
                              int nonzero_padding) {
    put32(dst, pos, type);
    put32(dst, pos + 4, size);
    memcpy(dst + pos + 8, data, size);
    size_t end = pos + 8 + size;
    size_t next = (end + 7u) & ~7u;
    for (size_t i = end; i < next; ++i) dst[i] = nonzero_padding ? 0xa5u : 0u;
    return next;
}

static size_t make_property_note(uint8_t *dst, const uint32_t *values,
                                 size_t value_count, uint32_t extra_type,
                                 int wrong_owner, int wrong_note_type,
                                 int bad_feature_size, int nonzero_padding) {
    memset(dst, 0, 512);
    put32(dst, 0, 4);
    put32(dst, 8, wrong_note_type ? 6u : 5u);
    memcpy(dst + 12, wrong_owner ? "BAD\0" : "GNU\0", 4);
    size_t pos = 16;
    for (size_t i = 0; i < value_count; ++i) {
        uint8_t data[8] = {0};
        memcpy(data, &values[i], 4);
        pos = append_property(dst, pos, GNU_PROPERTY_X86_FEATURE_1_AND,
                              data, bad_feature_size ? 8u : 4u,
                              nonzero_padding);
    }
    if (extra_type != 0) {
        const uint32_t marker = 0x11223344u;
        pos = append_property(dst, pos, extra_type,
                              (const uint8_t *)&marker, 4, 0);
    }
    put32(dst, 4, (uint32_t)(pos - 16));
    return (pos + 7u) & ~7u;
}

static size_t make_unknown_note(uint8_t *dst, uint64_t align,
                                int nonzero_padding) {
    const uint8_t owner[5] = {'O', 'T', 'H', 'R', '\0'};
    memset(dst, 0, 64);
    put32(dst, 0, sizeof(owner));
    put32(dst, 4, 0);
    put32(dst, 8, 0x11223344u);
    memcpy(dst + 12, owner, sizeof(owner));
    size_t next = (12u + sizeof(owner) + (size_t)align - 1u) & ~((size_t)align - 1u);
    if (nonzero_padding && next > 17u) dst[17] = 0xa5u;
    return next;
}

static uint64_t register_one(fixture_t *f, size_t phdr_index, uint32_t type,
                             uint64_t off, uint64_t size) {
    uint8_t *p = phdr(f, phdr_index, type, off, size);
    return x64lens_gnu_property_register_carrier(
        f->image, sizeof(f->image), f->context, phdr_index, p);
}

static uint64_t register_one_align(fixture_t *f, size_t phdr_index,
                                   uint32_t type, uint64_t off,
                                   uint64_t size, uint64_t align) {
    uint8_t *p = phdr(f, phdr_index, type, off, size);
    put64(p, P_ALIGN, align);
    return x64lens_gnu_property_register_carrier(
        f->image, sizeof(f->image), f->context, phdr_index, p);
}

static uint64_t parse(fixture_t *f) {
    return x64lens_gnu_property_parse(
        f->image, sizeof(f->image), f->context, f->summary);
}

static void expect_states(const char *name, fixture_t *f,
                          uint64_t ibt, uint64_t shstk) {
    expect_u64(name, "ibt", qword(f->context, CTX_IBT_STATE), ibt);
    expect_u64(name, "shstk", qword(f->context, CTX_SHSTK_STATE), shstk);
}

int main(void) {
    fixture_t *f = calloc(1, sizeof(*f));
    if (f == NULL) return 1;
    const uint64_t off = 4096;
    size_t note_size;
    uint32_t values[2];

    /* 1. No carriers: both facts remain unknown. */
    reset(f);
    if (parse(f) != EXIT_OK) fail("empty", "parse failed");
    expect_states("empty", f, GNU_PROPERTY_STATE_UNKNOWN, GNU_PROPERTY_STATE_UNKNOWN);

    /* 2. IBT-only property through PT_NOTE. */
    reset(f);
    values[0] = GNU_PROPERTY_X86_FEATURE_1_IBT;
    note_size = make_property_note(f->image + off, values, 1, 0, 0, 0, 0, 0);
    uint8_t *ibt_phdr = phdr(f, 0, PT_NOTE, off, note_size);
    put64(ibt_phdr, P_MEMSZ, 0); /* note evidence is bounded by p_filesz, not PT_LOAD rules */
    if (x64lens_gnu_property_register_carrier(
            f->image, sizeof(f->image), f->context, 0, ibt_phdr) != EXIT_OK ||
        parse(f) != EXIT_OK)
        fail("ibt", "registration or parse failed");
    expect_states("ibt", f, GNU_PROPERTY_STATE_PRESENT, GNU_PROPERTY_STATE_ABSENT);

    /* 3. IBT+SHSTK through PT_GNU_PROPERTY. */
    reset(f);
    values[0] = 3;
    note_size = make_property_note(f->image + off, values, 1, 0, 0, 0, 0, 0);
    if (register_one(f, 0, PT_GNU_PROPERTY, off, note_size) != EXIT_OK || parse(f) != EXIT_OK)
        fail("both", "registration or parse failed");
    expect_states("both", f, GNU_PROPERTY_STATE_PRESENT, GNU_PROPERTY_STATE_PRESENT);

    /* 4. Exact duplicate carriers canonicalize the bytes but retain contributors. */
    reset(f);
    values[0] = 3;
    note_size = make_property_note(f->image + off, values, 1, 0, 0, 0, 0, 0);
    if (register_one(f, 7, PT_NOTE, off, note_size) != EXIT_OK ||
        register_one(f, 11, PT_GNU_PROPERTY, off, note_size) != EXIT_OK ||
        parse(f) != EXIT_OK) fail("duplicate-carrier", "failed");
    expect_u64("duplicate-carrier", "views", qword(f->summary, SUM_VIEW_COUNT), 1);
    expect_u64("duplicate-carrier", "contributors", qword(f->summary, SUM_CONTRIBUTOR_COUNT), 2);
    expect_u64("duplicate-carrier", "notes", qword(f->summary, SUM_NOTE_COUNT), 1);
    expect_u64("duplicate-carrier", "carrier-offset", qword(f->context, CTX_CARRIERS + CARRIER_OFFSET), off);
    expect_u64("duplicate-carrier", "carrier-size", qword(f->context, CTX_CARRIERS + CARRIER_SIZE), note_size);
    expect_u64("duplicate-carrier", "carrier-kind", qword(f->context, CTX_CARRIERS + CARRIER_KIND), 3);
    expect_u64("duplicate-carrier", "carrier-align", qword(f->context, CTX_CARRIERS + CARRIER_ALIGN), CARRIER_ALIGN_8);
    expect_u64("duplicate-carrier", "contrib0-index", qword(f->context, CTX_CONTRIBUTORS + CONTRIB_PHDR_INDEX), 7);
    expect_u64("duplicate-carrier", "contrib0-type", qword(f->context, CTX_CONTRIBUTORS + CONTRIB_PHDR_TYPE), PT_NOTE);
    expect_u64("duplicate-carrier", "contrib0-slot", qword(f->context, CTX_CONTRIBUTORS + CONTRIB_CARRIER_SLOT), 0);
    expect_u64("duplicate-carrier", "contrib1-index", qword(f->context, CTX_CONTRIBUTORS + CONTRIB_RECORD_SIZE + CONTRIB_PHDR_INDEX), 11);
    expect_u64("duplicate-carrier", "contrib1-type", qword(f->context, CTX_CONTRIBUTORS + CONTRIB_RECORD_SIZE + CONTRIB_PHDR_TYPE), PT_GNU_PROPERTY);
    expect_u64("duplicate-carrier", "contrib1-slot", qword(f->context, CTX_CONTRIBUTORS + CONTRIB_RECORD_SIZE + CONTRIB_CARRIER_SLOT), 0);

    /* 5. Unknown property types are bounded private facts. */
    reset(f);
    note_size = make_property_note(f->image + off, values, 0, 0xdeadbeefu, 0, 0, 0, 0);
    if (register_one(f, 0, PT_NOTE, off, note_size) != EXIT_OK || parse(f) != EXIT_OK)
        fail("unknown-type", "failed");
    expect_u64("unknown-type", "unknown", qword(f->context, CTX_UNKNOWN_COUNT), 1);
    expect_states("unknown-type", f, GNU_PROPERTY_STATE_UNKNOWN, GNU_PROPERTY_STATE_UNKNOWN);

    /* 6. Unknown feature bits do not promote a named fact. */
    reset(f);
    values[0] = GNU_PROPERTY_X86_FEATURE_1_IBT | 0x80u;
    note_size = make_property_note(f->image + off, values, 1, 0, 0, 0, 0, 0);
    if (register_one(f, 0, PT_NOTE, off, note_size) != EXIT_OK || parse(f) != EXIT_OK)
        fail("unknown-bit", "failed");
    expect_u64("unknown-bit", "unknown", qword(f->context, CTX_UNKNOWN_COUNT), 1);
    expect_states("unknown-bit", f, GNU_PROPERTY_STATE_PRESENT, GNU_PROPERTY_STATE_ABSENT);

    /* 7. Identical duplicate feature records remain present, not conflicting. */
    reset(f);
    values[0] = values[1] = 3;
    note_size = make_property_note(f->image + off, values, 2, 0, 0, 0, 0, 0);
    if (register_one(f, 0, PT_NOTE, off, note_size) != EXIT_OK || parse(f) != EXIT_OK)
        fail("duplicate-feature", "failed");
    expect_u64("duplicate-feature", "feature_count", qword(f->summary, SUM_FEATURE_COUNT), 2);
    expect_u64("duplicate-feature", "conflicts", qword(f->context, CTX_CONFLICT_COUNT), 0);
    expect_states("duplicate-feature", f, GNU_PROPERTY_STATE_PRESENT, GNU_PROPERTY_STATE_PRESENT);

    /* 8. Conflicting AND records retain contradiction for each split bit. */
    reset(f);
    values[0] = 1; values[1] = 2;
    note_size = make_property_note(f->image + off, values, 2, 0, 0, 0, 0, 0);
    if (register_one(f, 0, PT_NOTE, off, note_size) != EXIT_OK || parse(f) != EXIT_OK)
        fail("conflicting-feature", "failed");
    expect_u64("conflicting-feature", "conflicts", qword(f->context, CTX_CONFLICT_COUNT), 1);
    expect_states("conflicting-feature", f,
                  GNU_PROPERTY_STATE_CONTRADICTORY,
                  GNU_PROPERTY_STATE_CONTRADICTORY);

    /* 9-10. Owner/type mismatches are unrelated notes, not malformed evidence. */
    reset(f);
    values[0] = 3;
    note_size = make_property_note(f->image + off, values, 1, 0, 1, 0, 0, 0);
    if (register_one(f, 0, PT_NOTE, off, note_size) != EXIT_OK || parse(f) != EXIT_OK)
        fail("wrong-owner", "failed");
    expect_u64("wrong-owner", "notes", qword(f->summary, SUM_NOTE_COUNT), 0);
    reset(f);
    note_size = make_property_note(f->image + off, values, 1, 0, 0, 1, 0, 0);
    if (register_one(f, 0, PT_NOTE, off, note_size) != EXIT_OK || parse(f) != EXIT_OK)
        fail("wrong-type", "failed");
    expect_u64("wrong-type", "notes", qword(f->summary, SUM_NOTE_COUNT), 0);

    /* 11. Truncated note header. */
    reset(f);
    memset(f->image + off, 0xa5, 8);
    if (register_one(f, 0, PT_NOTE, off, 8) != EXIT_OK || parse(f) != EXIT_MALFORMED_ELF)
        fail("truncated-header", "expected malformed");

    /* 12. Descriptor extent beyond the carrier. */
    reset(f);
    memset(f->image + off, 0, 32);
    put32(f->image + off, 0, 4); put32(f->image + off, 4, 64);
    put32(f->image + off, 8, 5); memcpy(f->image + off + 12, "GNU\0", 4);
    if (register_one(f, 0, PT_NOTE, off, 32) != EXIT_OK || parse(f) != EXIT_MALFORMED_ELF)
        fail("truncated-desc", "expected malformed");

    /* 13. Feature record with the wrong payload width. */
    reset(f);
    note_size = make_property_note(f->image + off, values, 1, 0, 0, 0, 1, 0);
    if (register_one(f, 0, PT_NOTE, off, note_size) != EXIT_OK || parse(f) != EXIT_MALFORMED_ELF)
        fail("feature-width", "expected malformed");

    /* 14. Nonzero property alignment padding. */
    reset(f);
    note_size = make_property_note(f->image + off, values, 1, 0, 0, 0, 0, 1);
    if (register_one(f, 0, PT_NOTE, off, note_size) != EXIT_OK || parse(f) != EXIT_MALFORMED_ELF)
        fail("property-padding", "expected malformed");

    /* 15. Descriptor scan cap is stable unsupported behavior. */
    reset(f);
    memset(f->image + off, 0, 70000);
    put32(f->image + off, 0, 4); put32(f->image + off, 4, 65537);
    put32(f->image + off, 8, 5); memcpy(f->image + off + 12, "GNU\0", 4);
    if (register_one(f, 0, PT_NOTE, off, 65560) != EXIT_OK || parse(f) != EXIT_UNSUPPORTED)
        fail("descriptor-cap", "expected unsupported");

    /* 16. Carrier and contributor capacities are independently bounded. */
    reset(f);
    for (size_t i = 0; i < GNU_PROPERTY_CARRIER_MAX; ++i) {
        if (register_one(f, i, PT_NOTE, off + i * 16, 0) != EXIT_OK)
            fail("carrier-cap", "unexpected early failure");
    }
    if (register_one(f, 40, PT_NOTE, off + 4096, 0) != EXIT_UNSUPPORTED)
        fail("carrier-cap", "expected carrier cap");
    reset(f);
    for (size_t i = 0; i < GNU_PROPERTY_CONTRIBUTOR_MAX; ++i) {
        if (register_one(f, i, PT_NOTE, off, 0) != EXIT_OK)
            fail("contributor-cap", "unexpected early failure");
    }
    if (register_one(f, 65, PT_NOTE, off, 0) != EXIT_UNSUPPORTED)
        fail("contributor-cap", "expected contributor cap");

    /* 17. Partial physical overlap remains distinct and visible. */
    reset(f);
    values[0] = 3;
    note_size = make_property_note(f->image + off, values, 1, 0, 0, 0, 0, 0);
    if (register_one(f, 0, PT_NOTE, off, note_size) != EXIT_OK ||
        register_one(f, 1, PT_NOTE, off + note_size - 4, 8) != EXIT_OK)
        fail("partial-overlap", "registration failed");
    expect_u64("partial-overlap", "overlap", qword(f->context, CTX_OVERLAP_COUNT), 1);
    expect_u64("partial-overlap", "views", qword(f->context, CTX_CARRIER_COUNT), 2);

    /* 18. Structural range failure takes precedence over the carrier byte cap. */
    reset(f);
    if (register_one(f, 0, PT_NOTE, sizeof(f->image) - 4,
                     1048577) != EXIT_MALFORMED_ELF)
        fail("carrier-range", "out-of-file oversized carrier was not malformed");

    /* 19. Unknown-note floods remain bounded even without recognized notes. */
    reset(f);
    memset(f->image + off, 0, (GNU_PROPERTY_NOTE_SCAN_MAX + 1u) * 16u);
    if (register_one(f, 0, PT_NOTE, off,
                     (GNU_PROPERTY_NOTE_SCAN_MAX + 1u) * 16u) != EXIT_OK ||
        parse(f) != EXIT_UNSUPPORTED)
        fail("note-cap", "expected bounded unsupported note count");

    /* 20. PT_GNU_PROPERTY requires native ELF64 eight-byte note alignment. */
    reset(f);
    values[0] = 3;
    note_size = make_property_note(f->image + off, values, 1, 0, 0, 0, 0, 0);
    if (register_one_align(f, 0, PT_GNU_PROPERTY, off, note_size, 4) != EXIT_MALFORMED_ELF)
        fail("property-carrier-align", "misaligned PT_GNU_PROPERTY was not malformed");

    /* 21. Carrier alignment controls the transition across unrelated notes. */
    reset(f);
    size_t prefix_size = make_unknown_note(f->image + off, 8, 0);
    note_size = make_property_note(f->image + off + prefix_size, values, 1, 0, 0, 0, 0, 0);
    if (register_one(f, 0, PT_NOTE, off, prefix_size + note_size) != EXIT_OK ||
        parse(f) != EXIT_OK)
        fail("aligned-note-stream", "eight-byte note stream did not reach property note");
    expect_states("aligned-note-stream", f,
                  GNU_PROPERTY_STATE_PRESENT, GNU_PROPERTY_STATE_PRESENT);

    /* 22. Outer note alignment padding is authenticated, not skipped. */
    reset(f);
    prefix_size = make_unknown_note(f->image + off, 8, 1);
    if (register_one(f, 0, PT_NOTE, off, prefix_size) != EXIT_OK ||
        parse(f) != EXIT_MALFORMED_ELF)
        fail("outer-note-padding", "nonzero note padding was not malformed");

    /* 23. Unrepresented PT_NOTE alignment is a stable unsupported feature. */
    reset(f);
    if (register_one_align(f, 0, PT_NOTE, off, 0, 16) != EXIT_UNSUPPORTED)
        fail("note-align-cap", "unsupported PT_NOTE alignment was accepted");

    /* 24. GNU property records are ordered monotonically by type. */
    reset(f);
    values[0] = 3;
    note_size = make_property_note(f->image + off, values, 1, 1, 0, 0, 0, 0);
    if (register_one(f, 0, PT_NOTE, off, note_size) != EXIT_OK ||
        parse(f) != EXIT_MALFORMED_ELF)
        fail("property-order", "descending property type was not malformed");

    /* 25. A recognized GNU property descriptor contains at least one header. */
    reset(f);
    note_size = make_property_note(f->image + off, values, 0, 0, 0, 0, 0, 0);
    if (register_one(f, 0, PT_NOTE, off, note_size) != EXIT_OK ||
        parse(f) != EXIT_MALFORMED_ELF)
        fail("empty-property-desc", "empty recognized descriptor was not malformed");

    printf("sprint12-gnu-property-internal: ok cases=25 states=4 carriers=32 contributors=64 summary_bytes=264 context_bytes=%d alignments=2 ordering=1\n",
           GNU_PROPERTY_CONTEXT_SIZE);
    free(f);
    return 0;
}
