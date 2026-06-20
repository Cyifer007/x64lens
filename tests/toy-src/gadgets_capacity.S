/*
 * Controlled candidate-capacity fixture.
 *
 * This executable contains one more `ret` byte than the current bounded
 * gadget-record arena can store. It verifies that the scanner returns the
 * documented unsupported-feature status instead of silently truncating a
 * report or writing past candidate storage.
 */

.global _start
.section .text
_start:
.rept 4097
    ret
.endr
