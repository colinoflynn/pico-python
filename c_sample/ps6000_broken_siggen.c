/* I originally added this file to show how the signal generator
 * was malfunctioning. It seems to work, but I would rather keep this code.
 */


#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <libps6000/ps6000Api.h>

void check_error(int r){
    if(r != PICO_OK){
        printf("Picoscope Error code is 0x%X", r);
        exit(0);
    }
}

int main(){
    short ps_handle;
    int r;
    printf("This is a demo about the weirdly behaving Picoscope 6403B\n"
           "signal generator sticking to low values\n");

    r = ps6000OpenUnit(&ps_handle, NULL);
    check_error(r);

    // taken from page 23
    unsigned long timebase = 5;
    float timebase_dt = 6.4E-9;
    float timeInterval_ns;
    uint32_t maxSamples;


    float wanted_duration = 1E-6;

    unsigned long wanted_samples = 0;

    wanted_samples = wanted_duration / timebase_dt;

    r = ps6000GetTimebase2(ps_handle, timebase, wanted_samples, &timeInterval_ns, 0, &maxSamples, 0);
    check_error(r);

    printf("Set timebase to %d = %f ns\n", timebase, timeInterval_ns);
    printf("Will measure for %d samples = %f ns\n", wanted_samples, wanted_duration * 1E9);
    printf("Max samples = %d\n", maxSamples);

    if(wanted_samples > maxSamples){
        printf("Error, too many samples \n");
        exit(0);
    }

    // change me when you change the range of the channel
    double channel_pk_to_pk = 0.05;
    r = ps6000SetChannel(ps_handle, PS6000_CHANNEL_A, 1, PS6000_DC_1M,
            PS6000_50MV, 0, PS6000_BW_FULL);
    check_error(r);

    r = ps6000SetSimpleTrigger(ps_handle, 1, PS6000_CHANNEL_A, 0, PS6000_RISING, 0, 1000);
    check_error(r);

    float f_gen = 1/(10*timebase_dt);
    unsigned long pkToPk = 4.0E6;
    r = ps6000SetSigGenBuiltIn(ps_handle, 0, pkToPk, PS6000_SQUARE,
            f_gen, f_gen, 0, 0, PS6000_UP, PS6000_ES_OFF, 1, 0,
            PS6000_SIGGEN_RISING, PS6000_SIGGEN_NONE, 0);
    check_error(r);
    printf("Just set signal generator to generate a %d uV pkToPk signal @ %f MHz\n", pkToPk, f_gen/1E6);

    int32_t timeIndisposedMs = 0;
    r = ps6000RunBlock(ps_handle, 0, wanted_samples, timebase, 0, &timeIndisposedMs, 0, NULL, NULL);
    check_error(r);

    printf("Time indisposed = %d ms\n", timeIndisposedMs);

    short ready = 0;
    do{
        r = ps6000IsReady(ps_handle, &ready);
        check_error(r);
    }while(ready == 0);
    sleep(1);

    int16_t *data_ptr;

    data_ptr = (int16_t *)malloc(sizeof(int16_t)*wanted_samples);
    if(data_ptr == NULL){
        printf("Error, malloc for data failed .... what.....\n");
        exit(0);
    }
    uint32_t i;
    for(i=0; i<wanted_samples; i++)
        data_ptr[i] = i;

    r = ps6000SetDataBuffer(ps_handle, PS6000_CHANNEL_A, data_ptr,
            wanted_samples, PS6000_RATIO_MODE_NONE);
    check_error(r);

    uint32_t noSamples;
    short overflow;
    noSamples = wanted_samples;
    r = ps6000GetValues(ps_handle, 0, &noSamples, 1, PS6000_RATIO_MODE_NONE, 0, &overflow);
    check_error(r);

    sleep(1);

    r = ps6000Stop(ps_handle);
    check_error(r);

    r = ps6000CloseUnit(ps_handle);
    check_error(r);


    printf("Measured %d / %d samples \n", noSamples, wanted_samples);
    printf("Printing results\n");
    for(i = 0; i < wanted_samples; i++){
        printf("[%.3d] = %d | %7.7fV \n", i, data_ptr[i], (((double)(data_ptr[i])/PS6000_MAX_VALUE) *channel_pk_to_pk));
    }


    free(data_ptr);
    data_ptr = NULL;


    return 0;
}
