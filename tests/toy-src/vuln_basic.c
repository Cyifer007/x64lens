/*
 * vuln_basic.c
 *
 * Purpose:
 *   Controlled local test binary for later mitigation and gadget-analysis
 *   experiments. This file is intentionally unsafe and must only be used in
 *   local lab conditions. It is not part of any remote exploitation workflow.
 */

#include <stdio.h>
#include <string.h>

void copy_user_input(const char *input) {
    char buf[32];
    /* Intentional unsafe copy for controlled compiler-flag experiments. */
    strcpy(buf, input);
    puts(buf);
}

int main(int argc, char **argv) {
    if (argc > 1) {
        copy_user_input(argv[1]);
    }
    return 0;
}
