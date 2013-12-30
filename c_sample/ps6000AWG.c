
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>


#ifdef _WIN32
#include "../ps6000Api.h"
#else
#include <libps6000/ps6000Api.h>
#endif

void check_error(int r){
    if(r != PICO_OK){
        printf("Picoscope Error code is 0x%X", r);
        exit(0);
    }
}

int main(){
    int      awgDeltaTMultiplier = 2;
    uint32_t deltaPhase = 1<<(32 - 14 -awgDeltaTMultiplier);
    float    awgDeltaT  = (float)(5E-9 * (1<<awgDeltaTMultiplier));

    int32_t awgSize = 100;
    float   awgTimeLength = awgDeltaT * awgSize;

#if 0
    int16_t awgMinValue = -32768;
    int16_t awgMaxValue =  32767;
#else
	int16_t awgMinValue = 0x0000;
	int16_t awgMaxValue = 0x0FFF;
#endif

    int16_t awgDelta = (awgMaxValue/(awgSize-1)) -
                       (awgMinValue/(awgSize-1));
    int16_t *awg = (int16_t *)malloc(sizeof(int16_t) * awgSize);
    if(awg == NULL){
        printf("Malloc failed .....");
        exit(1);
    }
    int32_t i;
    printf("Waveform is:\n");
    for(i=0; i<awgSize; i++){
        awg[i] = awgMinValue + i*awgDelta;
        printf("awg[%.3d] = %+.5d\n", i, awg[i]);
    }

    short ps_handle;
    int r;

    r = ps6000OpenUnit(&ps_handle, NULL);
    check_error(r);

    uint32_t timebase = 5;
    float    timebase_dt = 6.4E-9f;
    float    timeIntervalNanoseconds;
    uint32_t maxSamples;

    unsigned long wanted_samples = 0;
    wanted_samples = (unsigned long)(awgTimeLength / timebase_dt * 5);

    r = ps6000GetTimebase2(ps_handle, timebase,
            wanted_samples, &timeIntervalNanoseconds, 0, &maxSamples, 0);
    check_error(r);


    // set channel A to 2V
    r = ps6000SetChannel(ps_handle, PS6000_CHANNEL_A, 1, PS6000_DC_1M,
            PS6000_2V, 0, PS6000_BW_FULL);
    check_error(r);


    // this trigger is rather useless because we don't care about it
    r = ps6000SetSimpleTrigger(ps_handle, 1, PS6000_CHANNEL_A, 0, PS6000_RISING, 0, 1000);
    check_error(r);

    r = ps6000SetSigGenArbitrary(
        ps_handle, //handle,
        0,      //offsetVoltage,
        (int32_t)(4E6), //pkToPk,
        deltaPhase,     //startDeltaPhase,
        deltaPhase,     //stopDeltaPhase,
        0, //deltaPhaseIncrement,
        0, //dwelllCount,
        awg, // * arbitraryWaveform
        awgSize, //arbitraryWaveformSize,
        0, //sweepType,
        PS6000_ES_OFF, // operation,
        PS6000_SINGLE, // indexMode,
        1, // shots,
        0, // sweeps,
        PS6000_SIGGEN_RISING, // triggerType,
        PS6000_SIGGEN_NONE, // triggerSource,
        0 // extInThreshold
    );
	float timeIndisposedMS;
	r = ps6000RunBlock(ps_handle, 0, wanted_samples, timebase, 0, &timeIndisposedMS, 0, NULL, NULL);
    check_error(r);

    short ready = 0;
    do{
        r = ps6000IsReady(ps_handle, &ready);
        check_error(r);
    }while(ready == 0);

    int16_t *data_ptr;
    data_ptr = (int16_t *)malloc(sizeof(int16_t)*wanted_samples);

    r = ps6000SetDataBuffer(ps_handle, PS6000_CHANNEL_A, data_ptr,
            wanted_samples, PS6000_RATIO_MODE_NONE);
    check_error(r);

    uint32_t noSamples;
    short overflow;
    noSamples = wanted_samples;
    r = ps6000GetValues(ps_handle, 0, &noSamples, 1, PS6000_RATIO_MODE_NONE, 0, &overflow);
    check_error(r);

    r = ps6000Stop(ps_handle);
    check_error(r);

    r = ps6000CloseUnit(ps_handle);
    check_error(r);

    FILE *f;
    fopen_s(&f, "measured_waveform.txt", "w+");
	uint32_t s;
    for(s=0;s<noSamples; s++){
        fprintf(f, "%d\n", data_ptr[s]);
    }
    fclose(f);
    f = 0;

    free(data_ptr);
    data_ptr = NULL;
    return 0;
}
