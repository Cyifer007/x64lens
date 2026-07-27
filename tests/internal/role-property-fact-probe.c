/*
 * role-property-fact-probe.c
 *
 * Development-only fact probe for the Sprint 12 private binary-role and GNU-
 * property lattices. The probe maps one supplied ELF read-only, invokes the
 * same bounded assembly validators used by x64lens, and emits a compact JSON
 * record. It is not linked into the freestanding runtime and does not define
 * public report policy.
 */
#define _GNU_SOURCE
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

enum {
    PHDR_SUMMARY_PHNUM = 0,
    PHDR_SUMMARY_INTERP_COUNT = 144,
    PHDR_SUMMARY_FLAGS1_COUNT = 152,
    PHDR_SUMMARY_SONAME_COUNT = 168,
    PHDR_SUMMARY_ROLE_EVIDENCE = 184,
    PHDR_SUMMARY_ROLE_STATE = 192,
    PHDR_SUMMARY_GNU_PROPERTY_VIEW_COUNT = 216,
    PHDR_SUMMARY_GNU_PROPERTY_CONTRIBUTOR_COUNT = 224,
    PHDR_SUMMARY_GNU_PROPERTY_NOTE_COUNT = 232,
    PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_COUNT = 240,
    PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_AND = 248,
    PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_OR = 256,
    PHDR_SUMMARY_RECORD_SIZE = 264,

    GNU_PROPERTY_CTX_UNKNOWN_COUNT = 24,
    GNU_PROPERTY_CTX_CONFLICT_COUNT = 40,
    GNU_PROPERTY_CTX_OVERLAP_COUNT = 48,
    GNU_PROPERTY_CTX_IBT_STATE = 72,
    GNU_PROPERTY_CTX_SHSTK_STATE = 80,
    GNU_PROPERTY_CONTEXT_SIZE = 3160,

    EXEC_REGION_RECORD_SIZE = 64,
    EXEC_REGION_MAX = 64,
};

static uint64_t qword(const unsigned char *base, size_t offset) {
    uint64_t value = 0;
    memcpy(&value, base + offset, sizeof(value));
    return value;
}

static void emit(uint64_t status, const unsigned char *summary,
                 const unsigned char *context) {
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
        qword(summary, PHDR_SUMMARY_PHNUM),
        qword(summary, PHDR_SUMMARY_ROLE_STATE),
        qword(summary, PHDR_SUMMARY_ROLE_EVIDENCE),
        qword(summary, PHDR_SUMMARY_INTERP_COUNT),
        qword(summary, PHDR_SUMMARY_FLAGS1_COUNT),
        qword(summary, PHDR_SUMMARY_SONAME_COUNT),
        qword(summary, PHDR_SUMMARY_GNU_PROPERTY_VIEW_COUNT),
        qword(summary, PHDR_SUMMARY_GNU_PROPERTY_CONTRIBUTOR_COUNT),
        qword(summary, PHDR_SUMMARY_GNU_PROPERTY_NOTE_COUNT),
        qword(summary, PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_COUNT),
        qword(summary, PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_AND),
        qword(summary, PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_OR),
        qword(context, GNU_PROPERTY_CTX_UNKNOWN_COUNT),
        qword(context, GNU_PROPERTY_CTX_CONFLICT_COUNT),
        qword(context, GNU_PROPERTY_CTX_OVERLAP_COUNT),
        qword(context, GNU_PROPERTY_CTX_IBT_STATE),
        qword(context, GNU_PROPERTY_CTX_SHSTK_STATE));
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s <elf>\n", argv[0]);
        return 2;
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

    unsigned char summary[PHDR_SUMMARY_RECORD_SIZE];
    unsigned char context[GNU_PROPERTY_CONTEXT_SIZE];
    unsigned char regions[EXEC_REGION_RECORD_SIZE * EXEC_REGION_MAX];
    memset(summary, 0, sizeof(summary));
    memset(context, 0, sizeof(context));
    memset(regions, 0, sizeof(regions));

    uint64_t status = x64lens_elf64_validate(mapping, (uint64_t)st.st_size);
    if (status == 0) {
        status = x64lens_phdr_analyze(
            mapping, (uint64_t)st.st_size, summary, regions,
            EXEC_REGION_MAX, context);
    }
    if (status == 0) {
        status = x64lens_binary_role_classify(summary);
    }
    emit(status, summary, context);
    munmap(mapping, (size_t)st.st_size);
    return 0;
}
