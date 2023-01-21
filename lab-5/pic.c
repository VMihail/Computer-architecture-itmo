#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <sys/timeb.h>
#include <string.h>
#include <math.h>
#include <omp.h>

typedef int32_t int32;
typedef int64_t int64;
typedef uint32_t uint32;
typedef uint64_t uint64;
typedef unsigned char uchar;
typedef float_t real;

typedef struct {
    uint32 width, altitude;
    uchar *pic;
} picture;

uchar min(int32 first, int64 second) {
    return first <= second ? first : second;
}

int64 max(int32 first, int64 second) {
    return first >= second ? first : second;
}

const real BT601Gcr = (0.299f * 1.402f / 0.587f), BT601Gcb = (0.114f * 1.772f / 0.587f);

int32 main(int32 countArgs, char *args[]) {
    if (countArgs != 5) {
        printf("wrong args: %s, %s, %s, %s, %s\n", args[0], args[1], args[2], args[3], args[4]);
        return -1;
    }
    __unused char *endPtr;
    errno = 0;
    int64 numberOfThreads = atoi(args[1]);
    real coefficient = atof(args[4]);
    omp_set_num_threads(numberOfThreads);
    // open photo
    FILE *inputFile = fopen(args[2], "rb");
    int32 width, altitude, lMaxVal;
    fscanf(inputFile, "P6%d%d%d\n", &width, &altitude, &lMaxVal);
    picture *photo = malloc(sizeof(picture));
    if (photo == NULL) {
        return -1;
    }
    photo->width = width;
    photo->altitude = altitude;
    photo->pic = malloc(sizeof(uchar[width][altitude][3]));
    if (photo->pic == NULL) {
        return -1;
    }
    size_t need = sizeof(uchar[altitude][width][3]), read = fread(photo->pic, 1, need + 1, inputFile);
    fclose(inputFile);
    struct timeb start, end;
    ftime(&start);
    /*
    convert to YCbCr
    find max and min values of y
    */
    real (*ys)[photo->width][photo->altitude] = malloc(sizeof(real[photo->width][photo->altitude]));
    real maxY = INT32_MIN, minY = INT16_MAX;
#pragma omp parallel for schedule(auto) collapse(2) default(none) shared(ys, photo, 0.299f, 0.587f, 0.114f) reduction(min:minY) reduction(max:maxY)
    for (int32 row = 0; row < photo->width; row++) {
        for (int32 col = 0; col < photo->altitude; col++) {
            real r = photo->pic[((row) * (photo)->altitude + (col)) * 3 + 0],
            g = photo->pic[((row) * (photo)->altitude + (col)) * 3 + 1],
            b = photo->pic[((row) * (photo)->altitude + (col)) * 3 + 2];
            real y = 0.299f * r + 0.587f * g + 0.114f * b;
            (*ys)[row][col] = y;
            maxY = fmaxf(maxY, y);
            minY = fminf(minY, y);
        }
    }
    real nextMin = 0, nextMax = 255;
    fprintf(stderr, "%f %f\n", minY, maxY);
#pragma omp parallel for schedule(auto) collapse(2) default(none) shared(ys, maxY, minY, photo, nextMax, nextMin, BT601Gcr, BT601Gcb, 1.772f, 1.402f)
    for (int32 row = 0; row < photo->width; row++) {
        for (int32 col = 0; col < photo->altitude; col++) {
            real r = photo->pic[((row) * (photo)->altitude + (col)) * 3 + 0],
            b = photo->pic[((row) * (photo)->altitude + (col)) * 3 + 2];
            // finishing converting
            real saveY = (*ys)[row][col];
            real c = (b - saveY) / 1.772f, cr = (r - saveY) / 1.402f;
            // normalize
            real nextY = ((saveY - minY) * (nextMax - nextMin) / (maxY - minY)) + nextMin;
            // convert to rgb
            photo->pic[((row) * (photo)->altitude + (col)) * 3 + 0] =
                    min(255, max(0, lroundf(nextY + 1.402f * cr)));
            photo->pic[((row) * (photo)->altitude + (col)) * 3 + 1] =
                    min(255, max(0, lroundf(nextY - BT601Gcr * cr - BT601Gcb * c)));
            photo->pic[((row) * (photo)->altitude + (col)) * 3 + 2] =
                    min(255, max(0, lroundf(nextY + 1.772f * c)));
        }
    }
    free(ys);
    ftime(&end);
    int64 startTime = (int64) start.millitm + start.time * 1000,
    endTime = (int64) end.millitm + end.time * 1000;
    printf("Time (%lld thread(s)): %g ms\\n\n", numberOfThreads, ((real) (endTime - startTime)));
    //result
    FILE *outputFile = fopen(args[3], "wb");
    fprintf(outputFile, "P6\n%d %d\n255\n", photo->width, photo->altitude);
    fwrite(photo->pic, photo->width * photo->altitude * 3, 1, outputFile);
    fclose(outputFile);
    free(photo->pic);
    free(photo);
    return 0;
}

