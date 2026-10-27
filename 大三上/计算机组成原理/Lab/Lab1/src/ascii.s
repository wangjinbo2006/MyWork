li s0, 0x21
li s1, 0x7f
mv s2, ra
loop:
mv a0, s0
jal ra, WRITE_SERIAL
addi s0, s0, 1
bne s0, s1, loop
mv ra, s2
jr ra
WRITE_SERIAL:
li t0, 0x10000000
.TESTW:
lb t1, 5(t0)
andi t1, t1, 0x20
beq t1, zero, .TESTW
sb a0, 0(t0)
jr ra
