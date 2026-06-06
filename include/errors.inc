; errors.inc
;
; Purpose:
;   Public process exit-code contract. These values are intentionally stable
;   because scripts, CI jobs, and future enterprise integrations may branch
;   on them.
;
; Documentation mirror:
;   docs/cli-contract.md must be updated if any value changes.

%ifndef X64LENS_ERRORS_INC
%define X64LENS_ERRORS_INC

%define EXIT_OK              0
%define EXIT_GENERAL         1
%define EXIT_USAGE           2
%define EXIT_FILE            3
%define EXIT_NOT_ELF64_X64   4
%define EXIT_MALFORMED_ELF   5
%define EXIT_UNSUPPORTED     6
%define EXIT_BOUNDS          7

%endif
