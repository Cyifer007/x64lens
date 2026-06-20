/*
 * Controlled exact-capacity fixture.
 *
 * This executable contains exactly 4096 `ret` bytes, matching the current
 * gadget-record arena capacity. It verifies that the final valid slot remains
 * usable before the 4097th candidate triggers fail-closed behavior.
 */

.global _start
.section .text
_start:
.rept 4096
    ret
.endr
