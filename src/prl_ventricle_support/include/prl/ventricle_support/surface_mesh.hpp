#pragma once

#include "prl/ventricle_support/vector3.hpp"

#include <array>
#include <cstdint>
#include <iosfwd>
#include <vector>

namespace prl::ventricle_support {

using Triangle = std::array<std::uint32_t, 3>;

struct SurfaceMesh {
    std::vector<Vector3> vertices;
    std::vector<Triangle> faces;
};

void validate_surface_mesh(const SurfaceMesh& mesh);
SurfaceMesh read_plain_surface_mesh(std::istream& input);
void write_plain_surface_mesh(std::ostream& output, const SurfaceMesh& mesh);

}  // namespace prl::ventricle_support
