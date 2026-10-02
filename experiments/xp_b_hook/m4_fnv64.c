/* m4_fnv64.c — genuine FNV-1a-64 collision construction for XP-B M4.
 *
 * Attack exploited: FNV-1a's last step is h' = (h ^ b) * P (P odd, invertible
 * mod 2^64). Two messages pA||cA and pB||cB collide iff
 *      (hA ^ cA) * P == (hB ^ cB) * P   <=>  hA ^ cA == hB ^ cB
 * with cA,cB single bytes; choose cA = 0, cB = hA ^ hB, which requires
 * hA ^ hB < 256, i.e. the two prefix states agree in their top 56 bits.
 * Birthday search for such a prefix pair costs ~2^28 (not the generic 2^32),
 * because the 8-bit suffix freedom is applied *after* the match.
 *
 * Usage: m4_fnv64 <log2_N> <salt> [threads]
 * Prints: N, evaluations, collisions_found, and for each 32 bytes of hex
 * (prefix + suffix) proof, plus a self-verification of the collision.
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>

#define P 0x100000001B3ULL
#define OFF 0xCBF29CE484222325ULL

static inline uint64_t fnv1a64(const uint8_t *b, size_t n) {
    uint64_t h = OFF;
    for (size_t i = 0; i < n; i++) { h = (h ^ b[i]) * P; }
    return h;
}

/* FNV over the 8-byte big-endian encoding of x (the rho/generator function). */
static inline uint64_t F(uint64_t x) {
    uint8_t b[8];
    for (int i = 0; i < 8; i++) b[i] = (uint8_t)(x >> (56 - 8 * i));
    return fnv1a64(b, 8);
}

static uint32_t rng_state = 0x2718u;
static inline uint32_t nextrand(void) {
    rng_state = rng_state * 1664525u + 1013904223u;  /* LCG */
    return rng_state;
}

static int cmp_u64(const void *a, const void *b) {
    uint64_t x = *(const uint64_t *)a, y = *(const uint64_t *)b;
    return (x > y) - (x < y);
}

int main(int argc, char **argv) {
    int log2N = (argc > 1) ? atoi(argv[1]) : 28;
    uint32_t salt = (argc > 2) ? (uint32_t)strtoul(argv[2], NULL, 10) : 1;
    if (log2N < 1 || log2N > 31) { fprintf(stderr, "bad log2N\n"); return 2; }
    uint64_t N = 1ULL << log2N;

    rng_state = 0x2718u ^ (salt * 2654435761u);

    uint64_t *keys = malloc(N * sizeof(uint64_t));
    if (!keys) { fprintf(stderr, "oom keys\n"); return 2; }

    clock_t t0 = clock();
    /* key[i] = F(prefix_i) >> 8  (the 56-bit agreement we search for) */
    for (uint64_t i = 0; i < N; i++) {
        uint64_t p = ((uint64_t)nextrand() << 32) ^ nextrand();
        p ^= (uint64_t)salt * 0x9E3779B97F4A7C15ULL;
        keys[i] = F(p) >> 8;
    }
    clock_t t1 = clock();
    qsort(keys, N, sizeof(uint64_t), cmp_u64);
    clock_t t2 = clock();

    /* adjacent duplicates = a pair of prefixes agreeing on the top 56 bits */
    uint64_t found = 0;
    for (uint64_t i = 1; i < N; i++)
        if (keys[i] == keys[i - 1]) found++;

    printf("{\"log2N\":%d,\"salt\":%u,\"N\":%llu,\"evaluations\":%llu,"
           "\"key_collisions\":%llu,\"gen_s\":%.3f,\"sort_s\":%.3f}\n",
           log2N, salt, (unsigned long long)N, (unsigned long long)N,
           (unsigned long long)found,
           (double)(t1 - t0) / CLOCKS_PER_SEC, (double)(t2 - t1) / CLOCKS_PER_SEC);

    if (found == 0) return 0;

    /* recover ONE pair by rescanning: find two prefixes with the same key */
    uint64_t dup_key = 0;
    for (uint64_t i = 1; i < N; i++)
        if (keys[i] == keys[i - 1]) { dup_key = keys[i]; break; }

    uint64_t p1 = 0, p2 = 0; int got = 0;

    /* second pass over the identical prefix stream to recover the pair */
    rng_state = 0x2718u ^ (salt * 2654435761u);
    for (uint64_t i = 0; i < N && got < 2; i++) {
        uint64_t pp = ((uint64_t)nextrand() << 32) ^ nextrand();
        pp ^= (uint64_t)salt * 0x9E3779B97F4A7C15ULL;
        if ((F(pp) >> 8) == dup_key) {
            if (got == 0) { p1 = pp; got = 1; }
            else if (pp != p1) { p2 = pp; got = 2; }
        }
    }
    if (got < 2) { printf("{\"pair_recovered\":false}\n"); return 0; }

    uint64_t hA = F(p1), hB = F(p2);
    uint8_t cB = (uint8_t)((hA ^ hB) & 0xFF);
    if ((hA ^ hB) > 0xFF) { printf("{\"pair_recovered\":false,\"why\":\"lowbyte\"}\n"); return 0; }

    uint8_t mA[9], mB[9];
    for (int i = 0; i < 8; i++) { mA[i] = (uint8_t)(p1 >> (56 - 8 * i)); mB[i] = (uint8_t)(p2 >> (56 - 8 * i)); }
    mA[8] = 0x00; mB[8] = cB;

    uint64_t fA = fnv1a64(mA, 9), fB = fnv1a64(mB, 9);
    printf("{\"pair_recovered\":true,\"verified\":%s,"
           "\"hashA\":\"%016llx\",\"hashB\":\"%016llx\","
           "\"msgA\":\"", (fA == fB) ? "true" : "false",
           (unsigned long long)fA, (unsigned long long)fB);
    for (int i = 0; i < 9; i++) printf("%02x", mA[i]);
    printf("\",\"msgB\":\"");
    for (int i = 0; i < 9; i++) printf("%02x", mB[i]);
    printf("\"}\n");
    return 0;
}
