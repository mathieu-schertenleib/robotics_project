#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ch.h"
#include "hal.h"
#include "memory_protection.h"
#include <usbcfg.h>
#include <main.h>
#include <chprintf.h>
#include <motors.h>
#include <communications.h>
#include <arm_math.h>
#include <msgbus/messagebus.h>
#include <move.h>
#include <audio/audio_thread.h>
#include <odometrie.h>
#include <listen.h>
#include <sensors/VL53L0X/VL53L0X.h>

messagebus_t bus;
MUTEX_DECL(bus_lock);
CONDVAR_DECL(bus_condvar);

#define BTH (BaseSequentialStream* ) &SD3

static void serial_start(void) {
	static SerialConfig ser_cfg = { 115200, 0, 0, 0, };

	sdStart(&SD3, &ser_cfg); // UART3.
}

static void timer12_start(void) {
	//General Purpose Timer configuration
	//timer 12 is a 16 bit timer so we can measure time
	//to about 65ms with a 1Mhz counter
	static const GPTConfig gpt12cfg = { 1000000, /* 1MHz timer clock in order to measure uS.*/
	NULL, /* Timer callback.*/
	0, 0 };

	gptStart(&GPTD12, &gpt12cfg);
	//let the timer count to max value
	gptStartContinuous(&GPTD12, 0xFFFF);
}

int main(void) {

	halInit();
	chSysInit();
	mpu_init();

	messagebus_init(&bus, &bus_lock, &bus_condvar);

	//starts the serial communication
	serial_start();
	//starts the USB communication
	usb_start();
	//starts timer 12
	timer12_start();
	//inits the motors
	motors_init();
	//init move thread
	lauch_move_thd();
	VL53L0X_start();
	lauch_odometrie_thd();

	/* Infinite loop. */
	while (1) {
		
		listen(BTH,BTH);
		chprintf(BTH,"in Main\r\n");
		chThdSleepMilliseconds(1000);
	}
}

#define STACK_CHK_GUARD 0xe2dee396
uintptr_t __stack_chk_guard = STACK_CHK_GUARD;

void __stack_chk_fail(void) {
	chSysHalt("Stack smashing detected");
}
