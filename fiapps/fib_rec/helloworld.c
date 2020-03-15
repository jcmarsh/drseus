
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int fib_i(int n) {
	int ii;
	int prev_0 = 1;
	int prev_1 = 1;
	int old_val = 0;

	for (ii = 2; ii < n; ii++) {
		old_val = prev_0;
		prev_0 += prev_1;
		prev_1 = old_val;
	}
	return prev_0;
}

int fib_r(int n) {
	if (n == 1) {
		return 1;
	} else if (n == 2) {
		return 1;
	} else {
		return fib_r(n-1) + fib_r(n-2);
	}
}

#define FIB_COUNT 12 // 40 takes about 15 seconds

int main()
{
	int fib_out_i = 0;
	int fib_out_r = 0;

	printf("Starting program\n\r");

	// Run once to warm caches before test section
        /*
	fib_out_i = fib_i(FIB_COUNT);
	fib_out_r = fib_r(FIB_COUNT);
	xil_printf("Result: %d, %d\n\r", fib_out_i, fib_out_r);
        */

        /* Set a breakpoint on this label to let DrSEUS restart exectuion when ready. */
        asm("drseus_start_tag:");
        fib_out_i = fib_i(FIB_COUNT);
        fib_out_r = fib_r(FIB_COUNT);
        asm("drseus_end_tag:");

	printf("Result: %d, %d\n\r", fib_out_i, fib_out_r);

        /* Not currently interested in the program detecitng errors. 
        if (fib_out_i != fib_out_r) {
          xil_printf("Fibs do not match: %d, %d %d\n\r", FIB_COUNT, fib_out_i, fib_out_r);
        } else {
          xil_printf("Result: %d, %d\n\r", fib_out_i, fib_out_r);
        }
        if (fib_out_i < 0 || fib_out_r < 0) {
          xil_printf("Fib overflow: %d, %d %d\n\r", FIB_COUNT, fib_out_i, fib_out_r);
        }
        */

        printf("safeword ");

        return 0;
}
