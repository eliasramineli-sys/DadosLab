#include <cstdint>
#include <cstddef>
#include <random>
#include <mutex>
#include <array>

#ifdef _WIN32
#define API extern "C" __declspec(dllexport)
#else
#define API extern "C" __attribute__((visibility("default")))
#endif

namespace {
std::mutex guard;
std::mt19937_64 engine([] {
    std::random_device rd;
    std::seed_seq seed{rd(), rd(), rd(), rd(), rd(), rd(), rd(), rd()};
    return std::mt19937_64(seed);
}());
}

API int dice_version() noexcept { return 1; }

// Bounded C ABI. Exceptions never cross the boundary into ctypes.
API int dice_roll(std::uint32_t* output, std::size_t size) noexcept {
    if (!output || size == 0 || size > 100000) return -1;
    try {
        std::lock_guard lock(guard);
        std::uniform_int_distribution<std::uint32_t> face(1, 6);
        for (std::size_t i = 0; i < size; ++i) output[i] = face(engine);
        return 0;
    } catch (...) { return -2; }
}

API int dice_counts(const std::uint32_t* values, std::size_t size,
                    std::uint64_t* output) noexcept {
    if (!output || (size && !values) || size > 100000) return -1;
    std::array<std::uint64_t, 6> counts{};
    for (std::size_t i = 0; i < size; ++i) {
        if (values[i] < 1 || values[i] > 6) return -1;
        ++counts[values[i] - 1];
    }
    for (int i = 0; i < 6; ++i) output[i] = counts[i];
    return 0;
}
