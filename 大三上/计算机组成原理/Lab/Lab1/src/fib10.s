li t0, 0x80400000
li t1, 1
li t2, 1
li t3, 10
loop:
sw t1, 0(t0)
add t4, t1, t2
addi t0, t0, 4
mv t1, t2
mv t2, t4
addi t3, t3, -1
bne t3, zero, loop
jr ra
