#pragma once

// Build-only compatibility shim for upstream commit 38af451.
// SimuCell3D requests C++17 but still calls the removed std::random_shuffle.

#include <algorithm>
#include <random>

namespace std {

template <class RandomIterator>
void random_shuffle(RandomIterator first, RandomIterator last) {
    static thread_local mt19937 generator(0x53433344U);
    shuffle(first, last, generator);
}

}  // namespace std
