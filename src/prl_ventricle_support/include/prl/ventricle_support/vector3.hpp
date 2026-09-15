#pragma once

#include <array>
#include <cstddef>

namespace prl::ventricle_support {

using Vector3 = std::array<double, 3>;

Vector3 add(const Vector3& left, const Vector3& right) noexcept;
Vector3 subtract(const Vector3& left, const Vector3& right) noexcept;
Vector3 scale(const Vector3& value, double factor) noexcept;
double dot(const Vector3& left, const Vector3& right) noexcept;
Vector3 cross(const Vector3& left, const Vector3& right) noexcept;
double norm(const Vector3& value) noexcept;
bool is_finite(const Vector3& value) noexcept;
Vector3 normalized(const Vector3& value);

}  // namespace prl::ventricle_support
