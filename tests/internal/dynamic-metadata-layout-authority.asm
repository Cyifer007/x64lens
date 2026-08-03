; dynamic-metadata-layout-authority.asm
;
; Purpose:
;   Export the private dynamic-metadata side-car ABI directly from NASM's
;   include/structs.inc authority. The descriptor is development-only and is
;   never linked into the freestanding x64lens runtime.
;
; Roadmap role:
;   Patch 075 freezes the private DT_TEXTREL/DF_TEXTREL layout before the C fact
;   probe interprets assembly-owned records. Future dynamic families must extend
;   this descriptor deliberately rather than guessing offsets.

bits 64
default rel

%include "structs.inc"

%define DYNAMIC_METADATA_LAYOUT_MAGIC       0x58363444594e4d44
%define DYNAMIC_METADATA_LAYOUT_VERSION     1
%define DYNAMIC_METADATA_LAYOUT_FIELD_COUNT 19

section .rodata align=8
global x64lens_dynamic_metadata_layout_descriptor
global x64lens_dynamic_metadata_layout_descriptor_size

x64lens_dynamic_metadata_layout_descriptor:
    dq DYNAMIC_METADATA_LAYOUT_MAGIC
    dq DYNAMIC_METADATA_LAYOUT_VERSION
    dq DYNAMIC_METADATA_LAYOUT_FIELD_COUNT

    dq DYNAMIC_METADATA_CTX_CARRIER_COUNT
    dq DYNAMIC_METADATA_CTX_TEXTREL_TAG_COUNT
    dq DYNAMIC_METADATA_CTX_FLAGS_COUNT
    dq DYNAMIC_METADATA_CTX_FLAGS_FIRST_VALUE
    dq DYNAMIC_METADATA_CTX_FLAGS_AND
    dq DYNAMIC_METADATA_CTX_FLAGS_OR
    dq DYNAMIC_METADATA_CTX_FULL_VALUE_CONFLICTS
    dq DYNAMIC_METADATA_CTX_TEXTREL_CONFLICTS
    dq DYNAMIC_METADATA_CTX_TABLE_COMPLETE
    dq DYNAMIC_METADATA_CTX_TEXTREL_STATE

    dq DYNAMIC_METADATA_CARRIER_TAG
    dq DYNAMIC_METADATA_CARRIER_INDEX
    dq DYNAMIC_METADATA_CARRIER_FILE_OFFSET
    dq DYNAMIC_METADATA_CARRIER_VALUE
    dq DYNAMIC_METADATA_CARRIER_RECORD_SIZE
    dq DYNAMIC_METADATA_CARRIER_MAX
    dq DYNAMIC_METADATA_CONTEXT_SIZE
    dq PRIVATE_METADATA_DYNAMIC_OFFSET
    dq PRIVATE_METADATA_CONTEXT_SIZE
.end:

x64lens_dynamic_metadata_layout_descriptor_size:
    dq x64lens_dynamic_metadata_layout_descriptor.end - x64lens_dynamic_metadata_layout_descriptor

section .note.GNU-stack noalloc noexec nowrite progbits
