; constants.inc
;
; Purpose:
;   Central compile-time constants for x64lens. Keeping syscall numbers,
;   file constants, version strings, and process exit codes in one include
;   prevents drift across modules and makes the CLI/output contract easier
;   to audit.
;
; Maintenance rule:
;   If a public exit code, version string, or syscall constant changes,
;   update docs/cli-contract.md, docs/versioning.md, and the active project state notes.

%ifndef X64LENS_CONSTANTS_INC
%define X64LENS_CONSTANTS_INC

%define X64LENS_VERSION      "0.1.0-dev"
%define X64LENS_SCHEMA       "0.1.0"
%define X64LENS_NAME         "x64lens"

; Linux x86_64 syscall numbers used by the no-libc implementation path.
%define SYS_READ             0
%define SYS_WRITE            1
%define SYS_OPEN             2
%define SYS_CLOSE            3
%define SYS_FSTAT            5
%define SYS_MMAP             9
%define SYS_MUNMAP           11
%define SYS_EXIT             60
%define SYS_OPENAT           257

; File constants.
%define AT_FDCWD             -100
%define O_RDONLY             0

; mmap constants for read-only private target mapping.
%define PROT_READ            0x1
%define MAP_PRIVATE          0x02

; Standard file descriptors.
%define STDIN                0
%define STDOUT               1
%define STDERR               2

%endif
