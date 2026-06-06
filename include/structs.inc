; structs.inc
; Internal record layout contract. These offsets are planned for Sprint 3.
;
; Purpose:
;   Defines internal analysis record layouts and bitmaps used after the tool
;   moves from direct printing to structured facts. These offsets are designed
;   so text, JSON, benchmarking, and future SARIF output can all consume the
;   same analysis records.

%ifndef X64LENS_STRUCTS_INC
%define X64LENS_STRUCTS_INC

; gadget_record offsets
%define GADGET_FILE_OFFSET       0
%define GADGET_VIRTUAL_ADDRESS   8
%define GADGET_BYTE_START        16
%define GADGET_BYTE_LEN          24
%define GADGET_TERMINATOR_TYPE   32
%define GADGET_SEMANTIC_CLASS    36
%define GADGET_REGS_CONTROLLED   40
%define GADGET_REGS_CLOBBERED    48
%define GADGET_STACK_DELTA       56
%define GADGET_SIDE_EFFECT_FLAGS 64
%define GADGET_SCORE             72
%define GADGET_RECORD_SIZE       80

; register bitmap bits
%define REG_RAX_BIT              0
%define REG_RBX_BIT              1
%define REG_RCX_BIT              2
%define REG_RDX_BIT              3
%define REG_RSI_BIT              4
%define REG_RDI_BIT              5
%define REG_RBP_BIT              6
%define REG_RSP_BIT              7
%define REG_R8_BIT               8
%define REG_R9_BIT               9
%define REG_R10_BIT              10
%define REG_R11_BIT              11
%define REG_R12_BIT              12
%define REG_R13_BIT              13
%define REG_R14_BIT              14
%define REG_R15_BIT              15

; semantic classes
%define SEM_UNKNOWN_CANDIDATE    0
%define SEM_ARG_CONTROL          1
%define SEM_SYSCALL_NUM_CONTROL  2
%define SEM_SYSCALL_TRIGGER      3
%define SEM_STACK_PIVOT          4
%define SEM_MEMORY_WRITE         5
%define SEM_MEMORY_READ          6
%define SEM_REG_TRANSFER         7
%define SEM_ALIGNMENT            8
%define SEM_CLOBBER_HEAVY        9

%endif
