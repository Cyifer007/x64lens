/*
 * Candidate-role vector probe for the Sprint 13 P086 private equivalence gate.
 *
 * This test-only C consumer owns an independently stated byte-layout contract
 * and never imports the production role lookup tables.  It can drive the
 * assembly materializer over arbitrary candidate vectors and six guard cases.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SUMMARY_SIZE 144u
#define SUMMARY_COUNT 0u
#define SUMMARY_CAPACITY 32u
#define RECORD_SIZE 112u
#define RECORD_PATTERN_ID 76u
#define RECORD_PATTERN_REG_COUNT 104u
#define RECORD_PATTERN_REG_ORDER 108u
#define ROLE_RECORD_SIZE 8u
#define MAX_RECORDS 4096u
#define EXIT_BOUNDS 7u

extern uint64_t x64lens_candidate_role_from_exact(void *summary, void *records, void *roles);

static uint32_t read_u32(const unsigned char *p) {
    uint32_t value;
    memcpy(&value, p, sizeof(value));
    return value;
}
static void write_u32(unsigned char *p, uint32_t value) { memcpy(p, &value, sizeof(value)); }
static void write_u64(unsigned char *p, uint64_t value) { memcpy(p, &value, sizeof(value)); }

static int vector_mode(const char *input_name, const char *output_name) {
    FILE *input = fopen(input_name, "rb");
    if (!input) { perror("fopen input"); return 2; }
    unsigned char header[12];
    if (fread(header, 1, sizeof(header), input) != sizeof(header) || memcmp(header, "X64R", 4) != 0) {
        fclose(input); fprintf(stderr, "candidate-role-vector-probe: invalid input header\n"); return 2;
    }
    uint32_t count = read_u32(header + 4), capacity = read_u32(header + 8);
    if (count > MAX_RECORDS || capacity > MAX_RECORDS) { fclose(input); return 2; }
    unsigned char *summary = calloc(1, SUMMARY_SIZE);
    unsigned char *records = calloc(capacity ? capacity : 1u, RECORD_SIZE);
    unsigned char *roles = calloc(capacity ? capacity : 1u, ROLE_RECORD_SIZE);
    if (!summary || !records || !roles) { fclose(input); free(summary); free(records); free(roles); return 2; }
    write_u64(summary + SUMMARY_COUNT, count); write_u64(summary + SUMMARY_CAPACITY, capacity);
    for (uint32_t i = 0; i < count; ++i) {
        unsigned char item[12];
        if (fread(item, 1, sizeof(item), input) != sizeof(item)) { fclose(input); free(summary); free(records); free(roles); return 2; }
        unsigned char *record = records + (size_t)i * RECORD_SIZE;
        write_u32(record + RECORD_PATTERN_ID, read_u32(item));
        write_u32(record + RECORD_PATTERN_REG_COUNT, read_u32(item + 4));
        write_u32(record + RECORD_PATTERN_REG_ORDER, read_u32(item + 8));
    }
    if (fgetc(input) != EOF) { fclose(input); free(summary); free(records); free(roles); return 2; }
    fclose(input);
    uint32_t status = (uint32_t)x64lens_candidate_role_from_exact(summary, records, roles);
    FILE *output = fopen(output_name, "wb");
    if (!output) { perror("fopen output"); free(summary); free(records); free(roles); return 2; }
    unsigned char out_header[12]; memcpy(out_header, "X64O", 4); write_u32(out_header + 4, status); write_u32(out_header + 8, count);
    if (fwrite(out_header, 1, sizeof(out_header), output) != sizeof(out_header) ||
        (count && fwrite(roles, ROLE_RECORD_SIZE, count, output) != count)) {
        fclose(output); free(summary); free(records); free(roles); return 2;
    }
    if (fclose(output) != 0) { free(summary); free(records); free(roles); return 2; }
    free(summary); free(records); free(roles); return 0;
}

static int guard_mode(const char *name) {
    unsigned char summary[SUMMARY_SIZE] = {0};
    unsigned char records[RECORD_SIZE] = {0};
    unsigned char roles[ROLE_RECORD_SIZE] = {0};
    void *s = summary, *r = records, *o = roles;
    uint64_t count = 1, capacity = 1;
    if (strcmp(name, "null-summary") == 0) s = NULL;
    else if (strcmp(name, "null-records") == 0) r = NULL;
    else if (strcmp(name, "null-roles") == 0) o = NULL;
    else if (strcmp(name, "count-over-capacity") == 0) { count = 2; capacity = 1; }
    else if (strcmp(name, "count-over-max") == 0) { count = MAX_RECORDS + 1u; capacity = MAX_RECORDS + 1u; }
    else if (strcmp(name, "empty") == 0) { count = 0; capacity = 0; }
    else { fprintf(stderr, "candidate-role-vector-probe: unknown guard\n"); return 2; }
    write_u64(summary + SUMMARY_COUNT, count); write_u64(summary + SUMMARY_CAPACITY, capacity);
    uint32_t status = (uint32_t)x64lens_candidate_role_from_exact(s, r, o);
    printf("%u\n", status);
    return 0;
}

int main(int argc, char **argv) {
    if (argc == 4 && strcmp(argv[1], "--vector") == 0) return vector_mode(argv[2], argv[3]);
    if (argc == 3 && strcmp(argv[1], "--guard") == 0) return guard_mode(argv[2]);
    fprintf(stderr, "usage: %s --vector INPUT OUTPUT | --guard CASE\n", argv[0]);
    return 2;
}
