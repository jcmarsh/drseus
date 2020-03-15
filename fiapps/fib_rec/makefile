CFLAGS = -Wall -O0 -g3
RM := rm -rf

fib_rec: helloworld.c makefile
	powerpc-linux-gnu-gcc $(CFLAGS) helloworld.c -o fib_rec

clean:
	-$(RM) fib_rec
