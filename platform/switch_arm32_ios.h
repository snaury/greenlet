/*
 * this is the internal transfer function.
 *
 * HISTORY
 * 28-Jan-12  Alexey Borzenkov <snaury@gmail.com>
 *      Ported to iPhone OS (different aapcs from normal arm32)
 *
 */

#define STACK_REFPLUS 1

#ifdef SLP_EVAL
#define STACK_MAGIC 0

/* iPhone OS uses r7 as a frame pointer and r9 as a scratch register.
   However, fp still resolves to r11 so need to use r7 explicitly below.
   Also, some vfp registers should be saved across calls and switches. */
#define REGS_TO_SAVE_GENERAL "r4", "r5", "r6", "r8", "r10", "r11", "lr"
#ifdef __VFP_FP__
#define REGS_TO_SAVE REGS_TO_SAVE_GENERAL, \
                     "d8", "d9", "d10", "d11", "d12", "d13", "d14", "d15"
#else
#define REGS_TO_SAVE REGS_TO_SAVE_GENERAL
#endif

static int
slp_switch(void)
{
        void *fp;
        register int result;
        register int *stackref, stsizediff;
        __asm__ volatile ("" : : : REGS_TO_SAVE);
        __asm__ volatile ("str r7,%0" : "=m" (fp));
        __asm__ ("mov %0,sp" : "=l" (stackref));
        {
                SLP_SAVE_STATE(stackref, stsizediff);
                __asm__ volatile (
                    "add sp,sp,%0\n\t"
                    "add r7,r7,%0"
                    :
                    : "r" (stsizediff)
                    : REGS_TO_SAVE);
                SLP_RESTORE_STATE();
        }
        __asm__ volatile ("ldr r7,%0" : : "m" (fp));
        __asm__ volatile ("mov %0, #0" : "=r" (result));
        __asm__ volatile ("" : : : REGS_TO_SAVE);
        return result;
}

#endif
