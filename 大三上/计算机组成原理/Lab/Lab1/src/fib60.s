li t0, 0x80400000
li t1, 1
li t2, 0
li t3, 1
li t4, 0
li t5, 58
loop:
add t6, t1, t3
sltu a0, t6, t1
add a1, t2, t4
add a1, a1, a0
mv t1, t3
mv t2, t4
mv t3, t6
mv t4, a1
addi t5, t5, -1
bne t5, zero, loop
sw t3, 0(t0)
sw t4, 4(t0)
jr ra
