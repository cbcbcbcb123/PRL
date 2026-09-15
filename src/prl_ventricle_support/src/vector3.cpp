#include "prl/ventricle_support/vector3.hpp"

#include <cmath>
#include <stdexcept>

namespace prl::ventricle_support {

Vector3 add(const Vector3& left, const Vector3& right) noexcept {
    return {left[0] + right[0], left[1] + right[1], left[2] + right[2]};
}

Vector3 subtract(const Vector3& left, const Vector3& right) noexcept {
    return {left[0] - right[0], left[1] - right[1], left[2] - right[2]};
}

Vector3 scale(const Vector3& value, const double factor) noexcept {
    return {factor * value[0], factor * value[1], factor * value[2]};
}

double dot(const Vector3& left, const Vector3& right) noexcept {
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2];
}

Vector3 cross(const Vector3& left, const Vector3& right) noexcept {
    return {
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    };
}

double norm(const Vector3& value) noexcept {
    return std::sqrt(dot(value, value));
}

bool is_finite(const Vector3& value) noexcept {
    return std::isfinite(value[0])
        && std::isfinite(value[1])
        && std::isfinite(value[2]);
}

Vector3 normalized(const Vector3& value) {
    const double magnitude = norm(value);
    if(!(magnitude > 0.0) || !std::isfinite(magnitude)) {
        throw std::invalid_argument("cannot normalize a zero or non-finite vector");
    }
    return scale(value, 1.0 / magnitude);
}

}  // namespace prl::ventricle_support
