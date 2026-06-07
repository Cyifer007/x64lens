; constants.inc
;
; Purpose:
;   Central compile-time constants for x64lens. Keeping syscall numbers,
;   file constants, version strings, process exit codes, and small Linux ABI
;   assumptions in one include prevents drift across modules and makes the
;   CLI/output contract easier to audit.
;
; Maintenance rule:
;   If a public exit code, version string, syscall constant, or Linux ABI
;   offset changes, update docs/cli-contract.md, docs/versioning.md, and the
;   active sprint notes.

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

; Linux syscall mmap returns a negative errno encoded in RAX on failure.
; Success addresses for normal user mappings are non-negative canonical user
; addresses, so Sprint 1 uses the sign flag as the error check.
%define MAP_FAILED_NEGATIVE  -1

; Standard file descriptors.
%define STDIN                0
%define STDOUT               1
%define STDERR               2

; Linux x86_64 struct stat assumptions used by fstat(2).
; st_size is at offset 48 in the kernel-provided stat layout on x86_64.
; We reserve more than the structure needs to avoid relying on the exact tail
; length during Sprint 1.
%define STATBUF_SIZE         160
%define STAT_ST_SIZE         48

; Sprint 3 scanner defaults. The first scanner is intentionally bounded so
; raw candidate extraction cannot walk arbitrarily far backward from a
; terminator byte. Larger values can be tested later once the arena allocator
; and benchmark harness are in place.
%define GADGET_DEFAULT_MAX_DEPTH 8
%define GADGET_MAX_DEPTH_LIMIT   32

%endif
