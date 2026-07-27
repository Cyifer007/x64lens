; role-property-layout-authority.asm
;
; Purpose:
;   Export the private binary-role/GNU-property probe ABI directly from the
;   NASM record authority. C development probes consume this descriptor instead
;   of duplicating offsets and sizes. The object is test-only and is never
;   linked into the freestanding x64lens runtime.
;
; Safety boundary:
;   Every qword below is an assembly-time constant from include/structs.inc.
;   The paired C reconciliation harness independently checks the exact order,
;   values, descriptor size, magic, and version before any private fact probe
;   may interpret an assembly-owned record.

bits 64
default rel

%include "structs.inc"

%define ROLE_PROPERTY_LAYOUT_MAGIC       0x5836344c41594f55
%define ROLE_PROPERTY_LAYOUT_VERSION     1
%define ROLE_PROPERTY_LAYOUT_FIELD_COUNT 21

section .rodata align=8

global x64lens_role_property_layout_descriptor
global x64lens_role_property_layout_descriptor_size

x64lens_role_property_layout_descriptor:
    dq ROLE_PROPERTY_LAYOUT_MAGIC
    dq ROLE_PROPERTY_LAYOUT_VERSION
    dq ROLE_PROPERTY_LAYOUT_FIELD_COUNT

    dq PHDR_SUMMARY_PHNUM
    dq PHDR_SUMMARY_INTERP_COUNT
    dq PHDR_SUMMARY_FLAGS1_COUNT
    dq PHDR_SUMMARY_SONAME_COUNT
    dq PHDR_SUMMARY_ROLE_EVIDENCE
    dq PHDR_SUMMARY_ROLE_STATE
    dq PHDR_SUMMARY_GNU_PROPERTY_VIEW_COUNT
    dq PHDR_SUMMARY_GNU_PROPERTY_CONTRIBUTOR_COUNT
    dq PHDR_SUMMARY_GNU_PROPERTY_NOTE_COUNT
    dq PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_COUNT
    dq PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_AND
    dq PHDR_SUMMARY_GNU_PROPERTY_FEATURE1_OR
    dq PHDR_SUMMARY_RECORD_SIZE

    dq GNU_PROPERTY_CTX_UNKNOWN_COUNT
    dq GNU_PROPERTY_CTX_CONFLICT_COUNT
    dq GNU_PROPERTY_CTX_OVERLAP_COUNT
    dq GNU_PROPERTY_CTX_IBT_STATE
    dq GNU_PROPERTY_CTX_SHSTK_STATE
    dq GNU_PROPERTY_CONTEXT_SIZE

    dq EXEC_REGION_RECORD_SIZE
    dq EXEC_REGION_MAX
.end:

x64lens_role_property_layout_descriptor_size:
    dq x64lens_role_property_layout_descriptor.end - x64lens_role_property_layout_descriptor
