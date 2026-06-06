; syscall.inc
;
; Purpose:
;   Compatibility include for syscall constants. This currently re-exports
;   constants.inc. It exists so syscall-specific definitions can move here
;   later without changing every source file.

%ifndef X64LENS_SYSCALL_INC
%define X64LENS_SYSCALL_INC

%include "constants.inc"

%endif
