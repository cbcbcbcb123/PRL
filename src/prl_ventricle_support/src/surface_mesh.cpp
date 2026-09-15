#include "prl/ventricle_support/surface_mesh.hpp"

#include <iomanip>
#include <istream>
#include <limits>
#include <ostream>
#include <stdexcept>
#include <string>

namespace prl::ventricle_support {
namespace {

constexpr std::uint64_t kMaximumItemCount = 100'000'000;

std::size_t checked_count(const std::uint64_t value, const char* label) {
    if(value == 0 || value > kMaximumItemCount) {
        throw std::runtime_error(std::string("invalid ") + label + " count");
    }
    if(value > static_cast<std::uint64_t>(std::numeric_limits<std::size_t>::max())) {
        throw std::runtime_error(std::string(label) + " count exceeds platform size");
    }
    return static_cast<std::size_t>(value);
}

}  // namespace

void validate_surface_mesh(const SurfaceMesh& mesh) {
    if(mesh.vertices.empty() || mesh.faces.empty()) {
        throw std::invalid_argument("surface mesh requires vertices and faces");
    }
    for(const Vector3& vertex : mesh.vertices) {
        if(!is_finite(vertex)) {
            throw std::invalid_argument("surface mesh contains a non-finite vertex");
        }
    }
    for(const Triangle& face : mesh.faces) {
        if(face[0] >= mesh.vertices.size()
           || face[1] >= mesh.vertices.size()
           || face[2] >= mesh.vertices.size()) {
            throw std::invalid_argument("surface mesh face references a missing vertex");
        }
        if(face[0] == face[1] || face[1] == face[2] || face[2] == face[0]) {
            throw std::invalid_argument("surface mesh contains a repeated face vertex");
        }
    }
}

SurfaceMesh read_plain_surface_mesh(std::istream& input) {
    std::uint64_t vertex_count_raw{};
    std::uint64_t face_count_raw{};
    if(!(input >> vertex_count_raw >> face_count_raw)) {
        throw std::runtime_error("surface mesh header is missing or invalid");
    }
    const std::size_t vertex_count = checked_count(vertex_count_raw, "vertex");
    const std::size_t face_count = checked_count(face_count_raw, "face");

    SurfaceMesh mesh;
    mesh.vertices.resize(vertex_count);
    mesh.faces.resize(face_count);
    for(Vector3& vertex : mesh.vertices) {
        if(!(input >> vertex[0] >> vertex[1] >> vertex[2])) {
            throw std::runtime_error("surface mesh vertex data is incomplete");
        }
    }
    for(Triangle& face : mesh.faces) {
        std::uint64_t first{};
        std::uint64_t second{};
        std::uint64_t third{};
        if(!(input >> first >> second >> third)) {
            throw std::runtime_error("surface mesh face data is incomplete");
        }
        if(first > std::numeric_limits<std::uint32_t>::max()
           || second > std::numeric_limits<std::uint32_t>::max()
           || third > std::numeric_limits<std::uint32_t>::max()) {
            throw std::runtime_error("surface mesh face index exceeds uint32 range");
        }
        face = {
            static_cast<std::uint32_t>(first),
            static_cast<std::uint32_t>(second),
            static_cast<std::uint32_t>(third),
        };
    }
    validate_surface_mesh(mesh);
    return mesh;
}

void write_plain_surface_mesh(std::ostream& output, const SurfaceMesh& mesh) {
    validate_surface_mesh(mesh);
    output << mesh.vertices.size() << ' ' << mesh.faces.size() << '\n';
    output << std::setprecision(17);
    for(const Vector3& vertex : mesh.vertices) {
        output << vertex[0] << ' ' << vertex[1] << ' ' << vertex[2] << '\n';
    }
    for(const Triangle& face : mesh.faces) {
        output << face[0] << ' ' << face[1] << ' ' << face[2] << '\n';
    }
    if(!output) {
        throw std::runtime_error("surface mesh write failed");
    }
}

}  // namespace prl::ventricle_support
