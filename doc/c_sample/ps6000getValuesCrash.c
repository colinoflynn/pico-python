/* I originally added this file to show how the signal generator
* was malfunctioning. It seems to work, but I would rather keep this code.
*/


#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#ifdef _WIN32
#include "..\ps6000Api.h"
#else
#include <libps6000/ps6000Api.h>
#endif

void check_error(int r){
	if (r != PICO_OK){
		printf("Picoscope Error code is 0x%X", r);
		exit(0);
	}
}

int main(){
	short ps_handle;
	int r;
	printf("This is a demo about the weirdly behaving Picoscope 6403B\n"
		"getValues seems to crash the system after repeated calls\n"
		"This code runs a stress test until it crashes the application\n"
		"I tested this code with a 2.5V pkToPk 1kHz sine wave attached to Channel A\n");

	r = ps6000OpenUnit(&ps_handle, NULL);
	check_error(r);

	// taken from page 23
	// TODO: Set the time base so that we get 4096 samplkes
	unsigned long timebase = 5;
	float timebase_dt = (float)(6.4E-9);
	float timeInterval_ns;
	uint32_t maxSamples;


	unsigned long wanted_samples = 4096;
	float wanted_duration = wanted_samples * timebase_dt;

	r = ps6000GetTimebase2(ps_handle, timebase, wanted_samples, &timeInterval_ns, 0, &maxSamples, 0);
	check_error(r);

	printf("Set timebase to %d = %f ns\n", timebase, timeInterval_ns);
	printf("Will measure for %d samples = %f ns\n", wanted_samples, wanted_duration * 1E9);
	printf("Max samples = %d\n", maxSamples);

	if (wanted_samples > maxSamples){
		printf("Error, too many samples \n");
		exit(0);
	}

	// change me when you change the range of the channel
	double channel_pk_to_pk = 2.0;
	r = ps6000SetChannel(ps_handle, PS6000_CHANNEL_A, 1, PS6000_DC_1M,
		PS6000_2V, 0, PS6000_BW_FULL);
	check_error(r);

	r = ps6000SetSimpleTrigger(ps_handle, 1, PS6000_CHANNEL_A, 0, PS6000_RISING, 0, 1000);
	check_error(r);
	printf("Set the trigger\n");

	int nCaptures = 4096;

	int16_t *data_ptr;



	uint32_t noSamples;
	short overflow;
	int32_t timeIndisposedMs = 0;
	int i;
	for (i = 0; i<nCaptures; i++){
		data_ptr = (int16_t *)malloc(sizeof(int16_t)*wanted_samples);
		if (data_ptr == NULL){
			printf("Error, malloc for data failed .... what.....\n");
			exit(0);
		}
		printf("Capture %d/%d", i + 1, nCaptures);

		r = ps6000RunBlock(ps_handle, 0, wanted_samples, timebase, 0, &timeIndisposedMs, 0, NULL, NULL);
		check_error(r);
		printf("Finished calling RunBlock\n");

		printf("Time indisposed = %d ms\n", timeIndisposedMs);
		short ready = 0;
		do{
			r = ps6000IsReady(ps_handle, &ready);
			check_error(r);
		} while (ready == 0);

		printf("Data is ready\n");

		r = ps6000SetDataBuffer(ps_handle, PS6000_CHANNEL_A, data_ptr,
			wanted_samples, PS6000_RATIO_MODE_NONE);
		check_error(r);
		printf("Finished calling setDataBuffer\n");

		noSamples = wanted_samples;
		r = ps6000GetValues(ps_handle, 0, &noSamples, 1, PS6000_RATIO_MODE_NONE, 0, &overflow);
		check_error(r);
		printf("Obtained %d/%d samples\n", noSamples, wanted_samples);
		free(data_ptr);
		data_ptr = NULL;
	}

	r = ps6000Stop(ps_handle);
	check_error(r);

	r = ps6000CloseUnit(ps_handle);
	check_error(r);




	return 0;
}
