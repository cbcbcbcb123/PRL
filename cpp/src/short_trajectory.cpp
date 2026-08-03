#include "prl/cell_engine/short_trajectory.hpp"

#include "prl_cell_engine/cell_surface_force.hpp"
#include "prl_cell_engine/cell_surface_snapshot.hpp"

#include "cell.hpp"
#include "node.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <map>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace prl::cell_engine {
namespace {

using Vector3 = std::array<double, 3>;

Vector3 subtract(const Vector3& left, const Vector3& right) noexcept {
    return {left[0] - right[0], left[1] - right[1], left[2] - right[2]};
}

Vector3 cross(const Vector3& left, const Vector3& right) noexcept {
    return {
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    };
}

double dot(const Vector3& left, const Vector3& right) noexcept {
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2];
}

double norm(const Vector3& value) noexcept {
    return std::sqrt(dot(value, value));
}

Vector3 add(const Vector3& left, const Vector3& right) noexcept {
    return {left[0] + right[0], left[1] + right[1], left[2] + right[2]};
}

Vector3 scale(const Vector3& value, const double factor) noexcept {
    return {factor * value[0], factor * value[1], factor * value[2]};
}

struct IndependentSurfaceGeometry {
    double area{};
    double volume{};
    Vector3 centroid{};
    double minimum_face_area{std::numeric_limits<double>::infinity()};
    double minimum_triangle_quality{1.0};
    double minimum_oriented_face_alignment{1.0};
    std::vector<Vector3> oriented_face_vectors{};
};

IndependentSurfaceGeometry independent_surface_geometry(
    const core::SurfaceMeshSnapshot& mesh,
    const std::vector<Vector3>* const reference_face_vectors
) {
    if(reference_face_vectors != nullptr
       && reference_face_vectors->size() != mesh.faces.size()) {
        throw std::runtime_error("short trajectory changed fixed topology");
    }
    IndependentSurfaceGeometry result;
    result.oriented_face_vectors.reserve(mesh.faces.size());
    double signed_six_volume = 0.0;
    for(std::size_t face_index = 0; face_index < mesh.faces.size(); ++face_index) {
        const auto& face_data = mesh.faces[face_index];
        const auto& a = mesh.vertices.at(face_data.vertex_indices[0]).position;
        const auto& b = mesh.vertices.at(face_data.vertex_indices[1]).position;
        const auto& c = mesh.vertices.at(face_data.vertex_indices[2]).position;
        const auto ab = subtract(b, a);
        const auto ac = subtract(c, a);
        const auto bc = subtract(c, b);
        const auto oriented = cross(ab, ac);
        const double twice_area = norm(oriented);
        const double face_area = 0.5 * twice_area;
        const double edge_square_sum = dot(ab, ab) + dot(ac, ac) + dot(bc, bc);
        const double quality = 2.0 * std::sqrt(3.0) * twice_area
            / edge_square_sum;
        if(!std::isfinite(face_area)
           || face_area <= 0.0
           || !std::isfinite(quality)
           || quality <= 0.0) {
            throw std::runtime_error(
                "short trajectory contains a degenerate surface face"
            );
        }
        result.area += face_area;
        result.minimum_face_area = std::min(result.minimum_face_area, face_area);
        result.minimum_triangle_quality = std::min(
            result.minimum_triangle_quality,
            quality
        );
        for(std::size_t component = 0; component < 3; ++component) {
            result.centroid[component] += face_area
                * (a[component] + b[component] + c[component]) / 3.0;
        }
        signed_six_volume += dot(a, cross(b, c));
        result.oriented_face_vectors.push_back(oriented);
        if(reference_face_vectors != nullptr) {
            const auto& reference = reference_face_vectors->at(face_index);
            const double alignment = dot(reference, oriented)
                / (norm(reference) * twice_area);
            if(!std::isfinite(alignment)) {
                throw std::runtime_error(
                    "short trajectory face orientation became non-finite"
                );
            }
            result.minimum_oriented_face_alignment = std::min(
                result.minimum_oriented_face_alignment,
                alignment
            );
        }
    }
    if(!std::isfinite(result.area) || result.area <= 0.0) {
        throw std::runtime_error("short trajectory surface area is invalid");
    }
    for(double& component : result.centroid) component /= result.area;
    result.volume = std::abs(signed_six_volume) / 6.0;
    if(!std::isfinite(result.volume)
       || result.volume <= 0.0
       || !std::all_of(
            result.centroid.begin(),
            result.centroid.end(),
            [](const double value) { return std::isfinite(value); }
       )) {
        throw std::runtime_error("short trajectory geometry is non-finite");
    }
    return result;
}

std::uint64_t hash_bytes(
    std::uint64_t current,
    const void* const bytes,
    const std::size_t count
) noexcept {
    constexpr std::uint64_t prime = 1099511628211ULL;
    const auto* data = static_cast<const unsigned char*>(bytes);
    for(std::size_t index = 0; index < count; ++index) {
        current ^= data[index];
        current *= prime;
    }
    return current;
}

template<typename Value>
std::uint64_t hash_value(std::uint64_t current, const Value& value) noexcept {
    return hash_bytes(current, &value, sizeof(Value));
}

std::uint64_t cell_state_hash(const ::cell& target) noexcept {
    std::uint64_t result = 1469598103934665603ULL;
    const auto cell_id = target.get_id();
    const auto revision = target.get_mesh_revision();
    result = hash_value(result, cell_id);
    result = hash_value(result, revision);
    for(const node& current_node : target.get_node_lst()) {
        if(!current_node.is_used()) continue;
        const auto persistent_id = current_node.get_persistent_id();
        result = hash_value(result, persistent_id);
        const std::array<double, 6> state{
            current_node.pos().dx(),
            current_node.pos().dy(),
            current_node.pos().dz(),
            current_node.force().dx(),
            current_node.force().dy(),
            current_node.force().dz(),
        };
        result = hash_bytes(result, state.data(), sizeof(state));
    }
    const std::array<double, 5> caches{
        target.get_area(),
        target.get_volume(),
        target.get_centroid().dx(),
        target.get_centroid().dy(),
        target.get_centroid().dz(),
    };
    return hash_bytes(result, caches.data(), sizeof(caches));
}

std::uint64_t cell_position_hash(const ::cell& target) noexcept {
    std::uint64_t result = 1469598103934665603ULL;
    for(const node& current_node : target.get_node_lst()) {
        if(!current_node.is_used()) continue;
        const auto persistent_id = current_node.get_persistent_id();
        result = hash_value(result, persistent_id);
        const std::array<double, 3> position{
            current_node.pos().dx(),
            current_node.pos().dy(),
            current_node.pos().dz(),
        };
        result = hash_bytes(result, position.data(), sizeof(position));
    }
    return result;
}

std::uint64_t configuration_hash(
    const ActiveShortTrajectoryConfig& configuration
) noexcept {
    std::uint64_t result = 1469598103934665603ULL;
    result = hash_value(result, configuration.time_step);
    result = hash_value(result, configuration.step_count);
    result = hash_value(result, configuration.qoi_contraction_unit_id);
    const auto damping_measure = static_cast<std::uint8_t>(
        configuration.damping.measure
    );
    result = hash_value(result, damping_measure);
    return hash_value(result, configuration.damping.coefficient);
}

ShortTrajectoryStatus classify_failure(const std::string& reason) noexcept {
    if(reason.find("non-finite") != std::string::npos) {
        return ShortTrajectoryStatus::failed_non_finite_state;
    }
    if(reason.find("degenerate") != std::string::npos
       || reason.find("orientation") != std::string::npos) {
        return ShortTrajectoryStatus::failed_degenerate_or_flipped_surface;
    }
    return ShortTrajectoryStatus::failed_step_exception;
}

SurfaceDampingLaw surface_damping(const CellSurfaceDampingLaw damping) {
    switch(damping.measure) {
        case CellSurfaceDampingMeasure::uniform_per_vertex:
            return {SurfaceDampingMeasure::uniform_per_vertex, damping.coefficient};
        case CellSurfaceDampingMeasure::barycentric_dual_area:
            return {
                SurfaceDampingMeasure::barycentric_dual_area,
                damping.coefficient,
            };
    }
    throw std::invalid_argument("short-trajectory damping measure is unsupported");
}

const core::ActiveContractionUnitState& qoi_unit_state(
    const core::ActiveContractionEvaluation& active,
    const core::ActiveContractionUnitId qoi_unit_id
) {
    const auto unit = std::find_if(
        active.unit_states.begin(),
        active.unit_states.end(),
        [qoi_unit_id](const core::ActiveContractionUnitState& state) {
            return state.contraction_unit_id == qoi_unit_id;
        }
    );
    if(unit == active.unit_states.end()) {
        throw std::invalid_argument(
            "short trajectory QoI contraction unit is not registered"
        );
    }
    return *unit;
}

double cache_residual(
    const ::cell& target,
    const IndependentSurfaceGeometry& geometry,
    const double initial_area,
    const double initial_volume,
    const double characteristic_length
) {
    const Vector3 cache_centroid{
        target.get_centroid().dx(),
        target.get_centroid().dy(),
        target.get_centroid().dz(),
    };
    return std::max({
        std::abs(target.get_area() - geometry.area) / initial_area,
        std::abs(target.get_volume() - geometry.volume) / initial_volume,
        norm(subtract(cache_centroid, geometry.centroid)) / characteristic_length,
    });
}

std::uint64_t undirected_edge_key(std::size_t first, std::size_t second) {
    if(first > second) std::swap(first, second);
    if(first > std::numeric_limits<std::uint32_t>::max()
       || second > std::numeric_limits<std::uint32_t>::max()) {
        throw std::overflow_error("surface edge index exceeds audit key range");
    }
    return (static_cast<std::uint64_t>(first) << 32U)
        | static_cast<std::uint64_t>(second);
}

std::array<double, 3> surface_edge_scales(
    const core::SurfaceMeshSnapshot& mesh
) {
    std::unordered_set<std::uint64_t> edges;
    edges.reserve(3 * mesh.faces.size() / 2);
    double squared_length_sum = 0.0;
    double minimum_length = std::numeric_limits<double>::infinity();
    double maximum_length = 0.0;
    for(const auto& current_face : mesh.faces) {
        for(std::size_t local_edge = 0; local_edge < 3; ++local_edge) {
            const auto first = current_face.vertex_indices[local_edge];
            const auto second = current_face.vertex_indices[(local_edge + 1) % 3];
            if(!edges.emplace(undirected_edge_key(first, second)).second) continue;
            const double length = norm(subtract(
                mesh.vertices.at(first).position,
                mesh.vertices.at(second).position
            ));
            if(!std::isfinite(length) || length <= 0.0) {
                throw std::runtime_error("surface edge scale is invalid");
            }
            squared_length_sum += length * length;
            minimum_length = std::min(minimum_length, length);
            maximum_length = std::max(maximum_length, length);
        }
    }
    if(edges.empty() || !std::isfinite(squared_length_sum)) {
        throw std::runtime_error("surface edge scale requires a finite mesh");
    }
    return {
        std::sqrt(squared_length_sum / static_cast<double>(edges.size())),
        maximum_length,
        minimum_length,
    };
}

std::vector<double> barycentric_control_areas(
    const core::SurfaceMeshSnapshot& mesh
) {
    std::vector<double> result(mesh.vertices.size(), 0.0);
    for(const auto& current_face : mesh.faces) {
        const auto& a = mesh.vertices.at(current_face.vertex_indices[0]).position;
        const auto& b = mesh.vertices.at(current_face.vertex_indices[1]).position;
        const auto& c = mesh.vertices.at(current_face.vertex_indices[2]).position;
        const double face_area = 0.5 * norm(cross(subtract(b, a), subtract(c, a)));
        if(!std::isfinite(face_area) || face_area <= 0.0) {
            throw std::runtime_error("barycentric control area contains invalid face");
        }
        for(const auto vertex_index : current_face.vertex_indices) {
            result.at(vertex_index) += face_area / 3.0;
        }
    }
    if(!std::all_of(
            result.begin(),
            result.end(),
            [](const double area) { return std::isfinite(area) && area > 0.0; }
        )) {
        throw std::runtime_error("barycentric control area is invalid");
    }
    return result;
}

double triangle_quality(
    const core::SurfaceMeshSnapshot& mesh,
    const std::size_t face_index
) {
    const auto& current_face = mesh.faces.at(face_index);
    const auto& a = mesh.vertices.at(current_face.vertex_indices[0]).position;
    const auto& b = mesh.vertices.at(current_face.vertex_indices[1]).position;
    const auto& c = mesh.vertices.at(current_face.vertex_indices[2]).position;
    const auto ab = subtract(b, a);
    const auto ac = subtract(c, a);
    const auto bc = subtract(c, b);
    const double edge_square_sum = dot(ab, ab) + dot(ac, ac) + dot(bc, bc);
    const double quality = 2.0 * std::sqrt(3.0) * norm(cross(ab, ac))
        / edge_square_sum;
    if(!std::isfinite(quality) || quality <= 0.0) {
        throw std::runtime_error("local trajectory face quality is invalid");
    }
    return quality;
}

struct FamilyCLocalTopologyReference {
    std::vector<bool> is_valence_five{};
    std::vector<bool> is_closed_one_ring{};
    std::vector<double> initial_incident_edge_mean{};
    std::vector<std::array<std::size_t, 2>> closed_one_ring_edges{};
    std::vector<double> closed_one_ring_initial_edge_lengths{};
    std::vector<std::size_t> closed_one_ring_incident_faces{};
    double initial_local_minimum_triangle_quality{1.0};
};

FamilyCLocalTopologyReference family_c_local_topology_reference(
    const core::SurfaceMeshSnapshot& mesh
) {
    if(mesh.vertices.empty() || mesh.faces.empty()) {
        throw std::invalid_argument("Family C local topology requires a mesh");
    }
    std::unordered_map<std::uint64_t, std::array<std::size_t, 2>> edges;
    edges.reserve(3 * mesh.faces.size() / 2);
    std::vector<std::size_t> valences(mesh.vertices.size(), 0);
    std::vector<double> incident_length_sums(mesh.vertices.size(), 0.0);
    for(const auto& current_face : mesh.faces) {
        for(std::size_t local_edge = 0; local_edge < 3; ++local_edge) {
            const auto first = current_face.vertex_indices[local_edge];
            const auto second = current_face.vertex_indices[(local_edge + 1) % 3];
            const auto key = undirected_edge_key(first, second);
            if(!edges.emplace(key, std::array<std::size_t, 2>{first, second}).second) {
                continue;
            }
            const double length = norm(subtract(
                mesh.vertices.at(first).position,
                mesh.vertices.at(second).position
            ));
            if(!std::isfinite(length) || length <= 0.0) {
                throw std::runtime_error("Family C initial edge is invalid");
            }
            ++valences.at(first);
            ++valences.at(second);
            incident_length_sums.at(first) += length;
            incident_length_sums.at(second) += length;
        }
    }

    FamilyCLocalTopologyReference result;
    result.is_valence_five.resize(mesh.vertices.size(), false);
    result.is_closed_one_ring.resize(mesh.vertices.size(), false);
    result.initial_incident_edge_mean.resize(mesh.vertices.size(), 0.0);
    for(std::size_t index = 0; index < mesh.vertices.size(); ++index) {
        if(valences[index] == 0) {
            throw std::runtime_error("Family C vertex has no incident edge");
        }
        result.is_valence_five[index] = valences[index] == 5;
        result.is_closed_one_ring[index] = result.is_valence_five[index];
        result.initial_incident_edge_mean[index] = incident_length_sums[index]
            / static_cast<double>(valences[index]);
    }
    if(std::none_of(
            result.is_valence_five.begin(),
            result.is_valence_five.end(),
            [](const bool selected) { return selected; }
        )) {
        throw std::invalid_argument("Family C mesh has no valence-five vertices");
    }
    for(const auto& [key, endpoints] : edges) {
        static_cast<void>(key);
        if(result.is_valence_five.at(endpoints[0])
           || result.is_valence_five.at(endpoints[1])) {
            result.is_closed_one_ring[endpoints[0]] = true;
            result.is_closed_one_ring[endpoints[1]] = true;
        }
    }
    for(const auto& [key, endpoints] : edges) {
        static_cast<void>(key);
        if(!result.is_closed_one_ring.at(endpoints[0])
           || !result.is_closed_one_ring.at(endpoints[1])) {
            continue;
        }
        result.closed_one_ring_edges.push_back(endpoints);
        result.closed_one_ring_initial_edge_lengths.push_back(norm(subtract(
            mesh.vertices.at(endpoints[0]).position,
            mesh.vertices.at(endpoints[1]).position
        )));
    }
    for(std::size_t face_index = 0; face_index < mesh.faces.size(); ++face_index) {
        const auto& current_face = mesh.faces[face_index];
        const bool incident = std::any_of(
            current_face.vertex_indices.begin(),
            current_face.vertex_indices.end(),
            [&](const std::size_t vertex_index) {
                return result.is_closed_one_ring.at(vertex_index);
            }
        );
        if(!incident) continue;
        result.closed_one_ring_incident_faces.push_back(face_index);
        result.initial_local_minimum_triangle_quality = std::min(
            result.initial_local_minimum_triangle_quality,
            triangle_quality(mesh, face_index)
        );
    }
    if(result.closed_one_ring_edges.empty()
       || result.closed_one_ring_incident_faces.empty()
       || !std::isfinite(result.initial_local_minimum_triangle_quality)
       || result.initial_local_minimum_triangle_quality <= 0.0) {
        throw std::runtime_error("Family C local topology is incomplete");
    }
    return result;
}

struct FamilyCLocalNormalErrorAudit {
    double valence_five_energy_fraction{};
    double valence_five_relative_rms{};
    double valence_five_pointwise_maximum{};
    double closed_one_ring_energy_fraction{};
    double closed_one_ring_relative_rms{};
    double closed_one_ring_pointwise_maximum{};
    bool force_buffers_cleared{};
};

FamilyCLocalNormalErrorAudit audit_family_c_local_normal_error(
    ::cell& target,
    const core::SurfaceMeshSnapshot& mesh,
    const std::vector<double>& control_areas,
    const FamilyCLocalTopologyReference& local_reference,
    const double damping_per_area,
    const double exact_normal_velocity
) {
    for(const node& current_node : target.get_node_lst()) {
        if(!current_node.is_used()) continue;
        const Vector3 force{
            current_node.force().dx(),
            current_node.force().dy(),
            current_node.force().dz(),
        };
        if(norm(force) != 0.0) {
            throw std::logic_error(
                "Family C local force audit requires empty force buffers"
            );
        }
    }
    std::vector<Vector3> forces;
    forces.reserve(mesh.vertices.size());
    try {
        target.apply_internal_forces(0.0);
        for(const node& current_node : target.get_node_lst()) {
            if(!current_node.is_used()) continue;
            forces.push_back({
                current_node.force().dx(),
                current_node.force().dy(),
                current_node.force().dz(),
            });
        }
    } catch(...) {
        static_cast<void>(reset_surface_forces(
            target,
            target.get_mesh_revision()
        ));
        throw;
    }
    static_cast<void>(reset_surface_forces(target, target.get_mesh_revision()));
    if(forces.size() != mesh.vertices.size()
       || control_areas.size() != mesh.vertices.size()) {
        throw std::runtime_error("Family C local force vertex order changed");
    }

    double total_energy = 0.0;
    double valence_five_energy = 0.0;
    double valence_five_area = 0.0;
    double closed_one_ring_energy = 0.0;
    double closed_one_ring_area = 0.0;
    FamilyCLocalNormalErrorAudit result;
    const double exact_speed = std::abs(exact_normal_velocity);
    for(std::size_t index = 0; index < mesh.vertices.size(); ++index) {
        const auto& position = mesh.vertices[index].position;
        const double radius = norm(position);
        if(!std::isfinite(radius) || radius <= 0.0) {
            throw std::runtime_error("Family C local force radius is invalid");
        }
        const auto normal = scale(position, 1.0 / radius);
        const auto velocity = scale(
            forces[index],
            1.0 / (damping_per_area * control_areas[index])
        );
        const double error = dot(velocity, normal) - exact_normal_velocity;
        const double energy = control_areas[index] * error * error;
        const double relative_error = std::abs(error) / exact_speed;
        total_energy += energy;
        if(local_reference.is_valence_five[index]) {
            valence_five_energy += energy;
            valence_five_area += control_areas[index];
            result.valence_five_pointwise_maximum = std::max(
                result.valence_five_pointwise_maximum,
                relative_error
            );
        }
        if(local_reference.is_closed_one_ring[index]) {
            closed_one_ring_energy += energy;
            closed_one_ring_area += control_areas[index];
            result.closed_one_ring_pointwise_maximum = std::max(
                result.closed_one_ring_pointwise_maximum,
                relative_error
            );
        }
    }
    if(!std::isfinite(total_energy) || total_energy <= 0.0
       || !std::isfinite(valence_five_area) || valence_five_area <= 0.0
       || !std::isfinite(closed_one_ring_area)
       || closed_one_ring_area <= 0.0) {
        throw std::runtime_error("Family C local normal-error ledger is invalid");
    }
    result.valence_five_energy_fraction = valence_five_energy / total_energy;
    result.valence_five_relative_rms = std::sqrt(
        valence_five_energy / valence_five_area
    ) / exact_speed;
    result.closed_one_ring_energy_fraction = closed_one_ring_energy / total_energy;
    result.closed_one_ring_relative_rms = std::sqrt(
        closed_one_ring_energy / closed_one_ring_area
    ) / exact_speed;
    result.force_buffers_cleared = true;
    for(const node& current_node : target.get_node_lst()) {
        if(!current_node.is_used()) continue;
        const Vector3 force{
            current_node.force().dx(),
            current_node.force().dy(),
            current_node.force().dz(),
        };
        result.force_buffers_cleared
            = result.force_buffers_cleared && norm(force) == 0.0;
    }
    return result;
}

double surface_area_with_displacement(
    const core::SurfaceMeshSnapshot& mesh,
    const std::vector<Vector3>& direction,
    const double scale_factor
) {
    if(direction.size() != mesh.vertices.size()) {
        throw std::invalid_argument("surface-energy direction size mismatch");
    }
    auto displaced = mesh;
    for(std::size_t index = 0; index < displaced.vertices.size(); ++index) {
        displaced.vertices[index].position = add(
            displaced.vertices[index].position,
            scale(direction[index], scale_factor)
        );
    }
    return independent_surface_geometry(displaced, nullptr).area;
}

std::vector<TrajectoryVertexPosition> vertex_positions(
    const core::SurfaceMeshSnapshot& mesh
) {
    std::vector<TrajectoryVertexPosition> result;
    result.reserve(mesh.vertices.size());
    for(const auto& vertex : mesh.vertices) {
        result.push_back({vertex.persistent_id, vertex.position});
    }
    return result;
}

double normalized_state_difference(
    const ActiveShortTrajectoryAudit& left,
    const ActiveShortTrajectoryAudit& right
) {
    if(left.final_positions.size() != right.final_positions.size()
       || left.final_positions.empty()) {
        throw std::invalid_argument(
            "time refinement requires equal nonempty fixed-topology states"
        );
    }
    std::unordered_map<core::VertexId, Vector3> right_by_id;
    right_by_id.reserve(right.final_positions.size());
    for(const auto& vertex : right.final_positions) {
        if(!right_by_id.emplace(vertex.vertex_id, vertex.position).second) {
            throw std::invalid_argument("time-refinement vertex IDs must be unique");
        }
    }
    double squared_error = 0.0;
    for(const auto& vertex : left.final_positions) {
        const auto match = right_by_id.find(vertex.vertex_id);
        if(match == right_by_id.end()) {
            throw std::invalid_argument(
                "time-refinement fixed-topology vertex IDs differ"
            );
        }
        const auto difference = subtract(vertex.position, match->second);
        squared_error += dot(difference, difference);
    }
    const double scale = 0.5 * (
        left.characteristic_length + right.characteristic_length
    );
    return std::sqrt(squared_error / left.final_positions.size()) / scale;
}

SelfConvergenceAudit self_convergence(
    const double coarse_medium_error,
    const double medium_fine_error,
    const ActiveTimeRefinementThresholds& thresholds
) {
    if(!std::isfinite(coarse_medium_error)
       || !std::isfinite(medium_fine_error)
       || coarse_medium_error < 0.0
       || medium_fine_error < 0.0) {
        throw std::invalid_argument("self-convergence errors must be finite and nonnegative");
    }
    SelfConvergenceAudit result;
    result.coarse_medium_normalized_error = coarse_medium_error;
    result.medium_fine_normalized_error = medium_fine_error;
    result.roundoff_plateau = coarse_medium_error
            <= thresholds.roundoff_plateau_threshold
        && medium_fine_error <= thresholds.roundoff_plateau_threshold;
    if(result.roundoff_plateau) {
        result.observed_order = 0.0;
        result.monotonic = true;
        result.order_passed = true;
    } else {
        result.observed_order = medium_fine_error == 0.0
            ? std::numeric_limits<double>::infinity()
            : std::log2(coarse_medium_error / medium_fine_error);
        result.monotonic = medium_fine_error < coarse_medium_error;
        result.order_passed = result.observed_order
            >= thresholds.minimum_observed_order;
    }
    result.fine_error_passed = medium_fine_error
        <= thresholds.maximum_medium_fine_normalized_error;
    result.passed = result.monotonic
        && result.fine_error_passed
        && result.order_passed;
    return result;
}

double normalized_scalar_difference(
    const double left,
    const double right,
    const double scale
) {
    if(!std::isfinite(left)
       || !std::isfinite(right)
       || !std::isfinite(scale)
       || scale <= 0.0) {
        throw std::invalid_argument("time-refinement scalar comparison is invalid");
    }
    return std::abs(left - right) / scale;
}

} // namespace

const char* short_trajectory_status_name(const ShortTrajectoryStatus status) noexcept {
    switch(status) {
        case ShortTrajectoryStatus::passed: return "passed";
        case ShortTrajectoryStatus::failed_invalid_configuration:
            return "failed_invalid_configuration";
        case ShortTrajectoryStatus::failed_non_finite_state:
            return "failed_non_finite_state";
        case ShortTrajectoryStatus::failed_degenerate_or_flipped_surface:
            return "failed_degenerate_or_flipped_surface";
        case ShortTrajectoryStatus::failed_penetration_limit:
            return "failed_penetration_limit";
        case ShortTrajectoryStatus::failed_energy_gate: return "failed_energy_gate";
        case ShortTrajectoryStatus::failed_refinement_gate:
            return "failed_refinement_gate";
        case ShortTrajectoryStatus::failed_step_exception:
            return "failed_step_exception";
    }
    return "failed_step_exception";
}

ActiveShortTrajectoryAudit run_active_fixed_topology_short_trajectory(
    ::cell& target,
    const core::MyocardialCellMaterialState& material,
    const std::vector<core::ActiveContractionUnit>& units,
    const ActiveShortTrajectoryConfig& configuration
) {
    ActiveShortTrajectoryAudit result;
    result.configuration = configuration;
    const auto config_hash = configuration_hash(configuration);
    auto fail = [&](const ShortTrajectoryStatus status,
                    const std::size_t step,
                    const double time,
                    const std::string& reason,
                    const std::uint64_t state_before) {
        const auto state_after = cell_state_hash(target);
        result.status = status;
        result.failure = ShortTrajectoryFailure{
            status,
            step,
            time,
            reason,
            config_hash,
            state_before,
            state_after,
            state_before == state_after,
        };
        result.final_positions = vertex_positions(capture_surface_snapshot(target));
        return result;
    };

    const auto entry_hash = cell_state_hash(target);
    if(!std::isfinite(configuration.time_step)
       || configuration.time_step <= 0.0
       || configuration.step_count == 0
       || configuration.qoi_contraction_unit_id == 0
       || configuration.damping.measure
            != CellSurfaceDampingMeasure::barycentric_dual_area
       || !std::isfinite(configuration.damping.coefficient)
       || configuration.damping.coefficient <= 0.0) {
        return fail(
            ShortTrajectoryStatus::failed_invalid_configuration,
            0,
            0.0,
            "active short-trajectory configuration is invalid",
            entry_hash
        );
    }

    try {
        static_cast<void>(refresh_surface_geometry(
            target,
            target.get_mesh_revision()
        ));
        const auto initial_mesh = capture_surface_snapshot(target);
        const auto initial_geometry = independent_surface_geometry(initial_mesh, nullptr);
        result.characteristic_length = std::cbrt(initial_geometry.volume);
        const auto initial_active = core::evaluate_active_contraction(
            initial_mesh,
            material,
            units
        );
        const auto& initial_qoi = qoi_unit_state(
            initial_active,
            configuration.qoi_contraction_unit_id
        );
        result.initial_axis_length = initial_qoi.length;
        result.initial_registered_active_energy = initial_active.audit.total_energy;
        if(!std::isfinite(result.characteristic_length)
           || result.characteristic_length <= 0.0
           || !std::isfinite(result.initial_axis_length)
           || result.initial_axis_length <= 0.0
           || !std::isfinite(result.initial_registered_active_energy)
           || result.initial_registered_active_energy <= 0.0) {
            throw std::invalid_argument(
                "active short trajectory requires positive initial scales"
            );
        }
        const auto reference_faces = initial_geometry.oriented_face_vectors;
        const auto initial_centroid = initial_geometry.centroid;

        auto append_sample = [&](const std::size_t step,
                                 const double time,
                                 const ActiveCellOverdampedStepAudit* const motion) {
            const auto mesh = capture_surface_snapshot(target);
            const auto geometry = independent_surface_geometry(mesh, &reference_faces);
            const auto active = core::evaluate_active_contraction(mesh, material, units);
            const auto& qoi = qoi_unit_state(
                active,
                configuration.qoi_contraction_unit_id
            );
            const double control_work = motion == nullptr
                ? 0.0
                : motion->active_control_energy;
            const double dissipation = motion == nullptr
                ? 0.0
                : motion->viscous_dissipation;
            const double previous_energy = result.samples.empty()
                ? active.audit.total_energy
                : result.samples.back().registered_active_energy;
            const double energy_residual = active.audit.total_energy
                - previous_energy + dissipation - control_work;
            const double normalized_cache = cache_residual(
                target,
                geometry,
                initial_geometry.area,
                initial_geometry.volume,
                result.characteristic_length
            );
            const ActiveShortTrajectorySample sample{
                step,
                time,
                qoi.length,
                (qoi.length - result.initial_axis_length)
                    / result.initial_axis_length,
                geometry.area,
                geometry.area / initial_geometry.area,
                geometry.volume,
                geometry.volume / initial_geometry.volume,
                geometry.centroid,
                norm(subtract(geometry.centroid, initial_centroid))
                    / result.characteristic_length,
                active.audit.total_energy,
                control_work,
                dissipation,
                energy_residual,
                geometry.minimum_oriented_face_alignment,
                geometry.minimum_triangle_quality,
                geometry.minimum_face_area / initial_geometry.minimum_face_area,
                normalized_cache,
                cell_state_hash(target),
            };
            result.samples.push_back(sample);
            result.cumulative_positive_energy_balance_residual += std::max(
                0.0,
                energy_residual
            );
            result.minimum_oriented_face_alignment = std::min(
                result.minimum_oriented_face_alignment,
                sample.minimum_oriented_face_alignment
            );
            result.minimum_triangle_quality = std::min(
                result.minimum_triangle_quality,
                sample.minimum_triangle_quality
            );
            result.minimum_face_area_ratio = std::min(
                result.minimum_face_area_ratio,
                sample.minimum_face_area_ratio
            );
            result.maximum_normalized_cache_residual = std::max(
                result.maximum_normalized_cache_residual,
                sample.maximum_normalized_cache_residual
            );
        };

        append_sample(0, 0.0, nullptr);
        for(std::size_t step = 1; step <= configuration.step_count; ++step) {
            const auto state_before = cell_state_hash(target);
            try {
                const auto motion = advance_active_cell_overdamped_one_step(
                    target,
                    material,
                    units,
                    configuration.time_step,
                    configuration.damping
                );
                append_sample(
                    step,
                    static_cast<double>(step) * configuration.time_step,
                    &motion
                );
            } catch(const std::exception& error) {
                return fail(
                    classify_failure(error.what()),
                    step,
                    static_cast<double>(step - 1) * configuration.time_step,
                    error.what(),
                    state_before
                );
            }
        }
        result.status = ShortTrajectoryStatus::passed;
        result.final_positions = vertex_positions(capture_surface_snapshot(target));
        return result;
    } catch(const std::exception& error) {
        return fail(
            classify_failure(error.what()),
            result.samples.size(),
            result.samples.empty() ? 0.0 : result.samples.back().time,
            error.what(),
            entry_hash
        );
    }
}

ActiveTimeRefinementGateAudit evaluate_active_time_refinement(
    const ActiveShortTrajectoryAudit& coarse,
    const ActiveShortTrajectoryAudit& medium,
    const ActiveShortTrajectoryAudit& fine,
    const ActiveTimeRefinementThresholds& thresholds
) {
    const std::array<double, 5> threshold_values{
        thresholds.maximum_medium_fine_normalized_error,
        thresholds.minimum_observed_order,
        thresholds.roundoff_plateau_threshold,
        thresholds.maximum_coarse_normalized_positive_energy_residual,
        thresholds.minimum_energy_residual_reduction,
    };
    if(!std::all_of(
            threshold_values.begin(),
            threshold_values.end(),
            [](const double value) { return std::isfinite(value) && value >= 0.0; }
        )
       || thresholds.minimum_energy_residual_reduction < 1.0) {
        throw std::invalid_argument("time-refinement thresholds are invalid");
    }
    if(coarse.status != ShortTrajectoryStatus::passed
       || medium.status != ShortTrajectoryStatus::passed
       || fine.status != ShortTrajectoryStatus::passed
       || coarse.samples.empty()
       || medium.samples.empty()
       || fine.samples.empty()) {
        throw std::invalid_argument("time refinement requires three passed trajectories");
    }
    const double coarse_final_time = coarse.configuration.time_step
        * static_cast<double>(coarse.configuration.step_count);
    const double medium_final_time = medium.configuration.time_step
        * static_cast<double>(medium.configuration.step_count);
    const double fine_final_time = fine.configuration.time_step
        * static_cast<double>(fine.configuration.step_count);
    const double time_tolerance = 16.0 * std::numeric_limits<double>::epsilon()
        * std::max({1.0, coarse_final_time, medium_final_time, fine_final_time});
    if(std::abs(coarse.configuration.time_step
                - 2.0 * medium.configuration.time_step) > time_tolerance
       || std::abs(medium.configuration.time_step
                   - 2.0 * fine.configuration.time_step) > time_tolerance
       || std::abs(coarse_final_time - medium_final_time) > time_tolerance
       || std::abs(medium_final_time - fine_final_time) > time_tolerance) {
        throw std::invalid_argument(
            "time-refinement levels must use dt/dt2/dt4 at one final time"
        );
    }

    const auto& coarse_final = coarse.samples.back();
    const auto& medium_final = medium.samples.back();
    const auto& fine_final = fine.samples.back();
    ActiveTimeRefinementGateAudit result;
    result.state = self_convergence(
        normalized_state_difference(coarse, medium),
        normalized_state_difference(medium, fine),
        thresholds
    );
    result.axis_length = self_convergence(
        normalized_scalar_difference(
            coarse_final.axis_length,
            medium_final.axis_length,
            fine.initial_axis_length
        ),
        normalized_scalar_difference(
            medium_final.axis_length,
            fine_final.axis_length,
            fine.initial_axis_length
        ),
        thresholds
    );
    result.contraction = self_convergence(
        normalized_scalar_difference(
            coarse_final.contraction,
            medium_final.contraction,
            1.0
        ),
        normalized_scalar_difference(
            medium_final.contraction,
            fine_final.contraction,
            1.0
        ),
        thresholds
    );
    result.area_ratio = self_convergence(
        normalized_scalar_difference(
            coarse_final.area_ratio,
            medium_final.area_ratio,
            1.0
        ),
        normalized_scalar_difference(
            medium_final.area_ratio,
            fine_final.area_ratio,
            1.0
        ),
        thresholds
    );
    result.volume_ratio = self_convergence(
        normalized_scalar_difference(
            coarse_final.volume_ratio,
            medium_final.volume_ratio,
            1.0
        ),
        normalized_scalar_difference(
            medium_final.volume_ratio,
            fine_final.volume_ratio,
            1.0
        ),
        thresholds
    );
    result.registered_active_energy = self_convergence(
        normalized_scalar_difference(
            coarse_final.registered_active_energy,
            medium_final.registered_active_energy,
            fine.initial_registered_active_energy
        ),
        normalized_scalar_difference(
            medium_final.registered_active_energy,
            fine_final.registered_active_energy,
            fine.initial_registered_active_energy
        ),
        thresholds
    );
    result.coarse_normalized_positive_energy_residual
        = coarse.cumulative_positive_energy_balance_residual
        / coarse.initial_registered_active_energy;
    result.medium_normalized_positive_energy_residual
        = medium.cumulative_positive_energy_balance_residual
        / medium.initial_registered_active_energy;
    result.fine_normalized_positive_energy_residual
        = fine.cumulative_positive_energy_balance_residual
        / fine.initial_registered_active_energy;
    result.energy_residual_passed
        = result.coarse_normalized_positive_energy_residual
            <= thresholds.maximum_coarse_normalized_positive_energy_residual
        && thresholds.minimum_energy_residual_reduction
            * result.medium_normalized_positive_energy_residual
            <= result.coarse_normalized_positive_energy_residual
                + thresholds.roundoff_plateau_threshold
        && thresholds.minimum_energy_residual_reduction
            * result.fine_normalized_positive_energy_residual
            <= result.medium_normalized_positive_energy_residual
                + thresholds.roundoff_plateau_threshold;
    result.passed = result.state.passed
        && result.axis_length.passed
        && result.contraction.passed
        && result.area_ratio.passed
        && result.volume_ratio.passed
        && result.registered_active_energy.passed
        && result.energy_residual_passed;
    return result;
}

SurfaceTensionShortTrajectoryAudit
run_surface_tension_fixed_topology_short_trajectory(
    ::cell& target,
    const SurfaceTensionShortTrajectoryConfig& configuration
) {
    SurfaceTensionShortTrajectoryAudit result;
    result.configuration = configuration;
    ActiveShortTrajectoryConfig hash_configuration;
    hash_configuration.time_step = configuration.time_step;
    hash_configuration.step_count = configuration.step_count;
    hash_configuration.qoi_contraction_unit_id = 1;
    hash_configuration.damping = configuration.damping;
    const auto config_hash = hash_value(
        configuration_hash(hash_configuration),
        configuration.surface_tension
    );
    auto fail = [&](const ShortTrajectoryStatus status,
                    const std::size_t step,
                    const double time,
                    const std::string& reason,
                    const std::uint64_t state_before) {
        const auto state_after = cell_state_hash(target);
        result.status = status;
        result.failure = ShortTrajectoryFailure{
            status,
            step,
            time,
            reason,
            config_hash,
            state_before,
            state_after,
            state_before == state_after,
        };
        return result;
    };
    const auto entry_hash = cell_state_hash(target);
    if(!std::isfinite(configuration.time_step)
       || configuration.time_step <= 0.0
       || configuration.step_count == 0
       || !std::isfinite(configuration.surface_tension)
       || configuration.surface_tension <= 0.0
       || configuration.damping.measure
            != CellSurfaceDampingMeasure::barycentric_dual_area
       || !std::isfinite(configuration.damping.coefficient)
       || configuration.damping.coefficient <= 0.0) {
        return fail(
            ShortTrajectoryStatus::failed_invalid_configuration,
            0,
            0.0,
            "surface-tension short-trajectory configuration is invalid",
            entry_hash
        );
    }

    try {
        static_cast<void>(refresh_surface_geometry(
            target,
            target.get_mesh_revision()
        ));
        const auto initial_mesh = capture_surface_snapshot(target);
        const auto initial_geometry = independent_surface_geometry(initial_mesh, nullptr);
        const auto reference_faces = initial_geometry.oriented_face_vectors;
        const auto initial_centroid = initial_geometry.centroid;
        result.characteristic_length = std::cbrt(initial_geometry.volume);
        result.initial_registered_surface_energy = configuration.surface_tension
            * initial_geometry.area;
        if(!std::isfinite(result.characteristic_length)
           || result.characteristic_length <= 0.0
           || !std::isfinite(result.initial_registered_surface_energy)
           || result.initial_registered_surface_energy <= 0.0) {
            throw std::invalid_argument(
                "surface-tension trajectory requires positive initial scales"
            );
        }

        auto append_sample = [&](const std::size_t step,
                                 const double time,
                                 const SurfaceOverdampedStepAudit* const motion) {
            const auto mesh = capture_surface_snapshot(target);
            const auto geometry = independent_surface_geometry(mesh, &reference_faces);
            const double energy = configuration.surface_tension * geometry.area;
            const double previous_energy = result.samples.empty()
                ? energy
                : result.samples.back().registered_surface_energy;
            const double dissipation = motion == nullptr
                ? 0.0
                : motion->viscous_dissipation;
            const double residual = energy - previous_energy + dissipation;
            const double normalized_cache = cache_residual(
                target,
                geometry,
                initial_geometry.area,
                initial_geometry.volume,
                result.characteristic_length
            );
            const SurfaceTensionShortTrajectorySample sample{
                step,
                time,
                geometry.area,
                geometry.area / initial_geometry.area,
                geometry.volume,
                geometry.volume / initial_geometry.volume,
                geometry.centroid,
                norm(subtract(geometry.centroid, initial_centroid))
                    / result.characteristic_length,
                energy,
                energy / result.initial_registered_surface_energy,
                dissipation,
                residual,
                geometry.minimum_oriented_face_alignment,
                geometry.minimum_triangle_quality,
                geometry.minimum_face_area / initial_geometry.minimum_face_area,
                normalized_cache,
            };
            result.samples.push_back(sample);
            result.cumulative_positive_energy_balance_residual += std::max(0.0, residual);
            result.minimum_oriented_face_alignment = std::min(
                result.minimum_oriented_face_alignment,
                sample.minimum_oriented_face_alignment
            );
            result.minimum_triangle_quality = std::min(
                result.minimum_triangle_quality,
                sample.minimum_triangle_quality
            );
            result.minimum_face_area_ratio = std::min(
                result.minimum_face_area_ratio,
                sample.minimum_face_area_ratio
            );
            result.maximum_normalized_cache_residual = std::max(
                result.maximum_normalized_cache_residual,
                sample.maximum_normalized_cache_residual
            );
        };

        append_sample(0, 0.0, nullptr);
        const auto damping = surface_damping(configuration.damping);
        for(std::size_t step = 1; step <= configuration.step_count; ++step) {
            const auto state_before = cell_state_hash(target);
            try {
                target.apply_internal_forces(configuration.time_step);
                const auto motion = advance_surface_overdamped(
                    target,
                    target.get_mesh_revision(),
                    configuration.time_step,
                    damping
                );
                append_sample(
                    step,
                    static_cast<double>(step) * configuration.time_step,
                    &motion
                );
            } catch(const std::exception& error) {
                static_cast<void>(reset_surface_forces(
                    target,
                    target.get_mesh_revision()
                ));
                return fail(
                    classify_failure(error.what()),
                    step,
                    static_cast<double>(step - 1) * configuration.time_step,
                    error.what(),
                    state_before
                );
            }
        }
        result.normalized_positive_energy_balance_residual
            = result.cumulative_positive_energy_balance_residual
            / result.initial_registered_surface_energy;
        result.status = ShortTrajectoryStatus::passed;
        return result;
    } catch(const std::exception& error) {
        return fail(
            classify_failure(error.what()),
            result.samples.size(),
            result.samples.empty() ? 0.0 : result.samples.back().time,
            error.what(),
            entry_hash
        );
    }
}

FamilyCSmoothSphereTrajectoryAudit run_family_c_smooth_sphere_trajectory(
    ::cell& target,
    const FamilyCSmoothSphereTrajectoryConfig& configuration
) {
    FamilyCSmoothSphereTrajectoryAudit result;
    result.configuration = configuration;
    ActiveShortTrajectoryConfig hash_configuration;
    hash_configuration.time_step = configuration.time_step;
    hash_configuration.step_count = configuration.step_count;
    hash_configuration.qoi_contraction_unit_id = 1;
    hash_configuration.damping = configuration.damping;
    auto config_hash = hash_value(
        configuration_hash(hash_configuration),
        configuration.surface_tension
    );
    config_hash = hash_value(config_hash, configuration.reference_radius);
    auto fail = [&](const ShortTrajectoryStatus status,
                    const std::size_t step,
                    const double time,
                    const std::string& reason,
                    const std::uint64_t state_before) {
        const auto state_after = cell_state_hash(target);
        result.status = status;
        result.failure = ShortTrajectoryFailure{
            status,
            step,
            time,
            reason,
            config_hash,
            state_before,
            state_after,
            state_before == state_after,
        };
        return result;
    };
    const auto entry_hash = cell_state_hash(target);
    if(!std::isfinite(configuration.time_step)
       || configuration.time_step <= 0.0
       || configuration.step_count == 0
       || !std::isfinite(configuration.surface_tension)
       || configuration.surface_tension <= 0.0
       || configuration.damping.measure
            != CellSurfaceDampingMeasure::barycentric_dual_area
       || !std::isfinite(configuration.damping.coefficient)
       || configuration.damping.coefficient <= 0.0
       || !std::isfinite(configuration.reference_radius)
       || configuration.reference_radius <= 0.0) {
        return fail(
            ShortTrajectoryStatus::failed_invalid_configuration,
            0,
            0.0,
            "Family C smooth trajectory configuration is invalid",
            entry_hash
        );
    }

    try {
        static_cast<void>(refresh_surface_geometry(
            target,
            target.get_mesh_revision()
        ));
        const auto initial_mesh = capture_surface_snapshot(target);
        const auto initial_geometry = independent_surface_geometry(
            initial_mesh,
            nullptr
        );
        const auto reference_faces = initial_geometry.oriented_face_vectors;
        const auto initial_centroid = initial_geometry.centroid;
        const auto local_reference = family_c_local_topology_reference(initial_mesh);
        result.initial_rms_edge_length = surface_edge_scales(initial_mesh)[0]
            / configuration.reference_radius;
        result.initial_registered_surface_energy = configuration.surface_tension
            * initial_geometry.area;
        result.initial_local_minimum_triangle_quality
            = local_reference.initial_local_minimum_triangle_quality;
        result.valence_five_vertex_count = static_cast<std::size_t>(std::count(
            local_reference.is_valence_five.begin(),
            local_reference.is_valence_five.end(),
            true
        ));
        result.closed_one_ring_vertex_count = static_cast<std::size_t>(std::count(
            local_reference.is_closed_one_ring.begin(),
            local_reference.is_closed_one_ring.end(),
            true
        ));
        result.closed_one_ring_edge_count
            = local_reference.closed_one_ring_edges.size();
        result.closed_one_ring_incident_face_count
            = local_reference.closed_one_ring_incident_faces.size();
        if(!std::isfinite(result.initial_rms_edge_length)
           || result.initial_rms_edge_length <= 0.0
           || !std::isfinite(result.initial_registered_surface_energy)
           || result.initial_registered_surface_energy <= 0.0) {
            throw std::invalid_argument(
                "Family C smooth trajectory requires positive initial scales"
            );
        }
        result.samples.reserve(configuration.step_count + 1);

        auto append_sample = [&](const std::size_t step,
                                 const double time,
                                 const SurfaceOverdampedStepAudit* const motion) {
            const auto mesh = capture_surface_snapshot(target);
            if(mesh.vertices.size() != initial_mesh.vertices.size()
               || mesh.faces.size() != initial_mesh.faces.size()) {
                throw std::runtime_error(
                    "Family C smooth trajectory changed fixed topology"
                );
            }
            const auto geometry = independent_surface_geometry(
                mesh,
                &reference_faces
            );
            const auto control_areas = barycentric_control_areas(mesh);
            const double exact_radius_squared
                = configuration.reference_radius * configuration.reference_radius
                - 4.0 * configuration.surface_tension * time
                    / configuration.damping.coefficient;
            if(!std::isfinite(exact_radius_squared)
               || exact_radius_squared <= 0.0) {
                throw std::runtime_error(
                    "Family C analytic radius became non-positive"
                );
            }
            const double exact_radius = std::sqrt(exact_radius_squared);
            const double exact_normal_velocity
                = -2.0 * configuration.surface_tension
                    / (configuration.damping.coefficient * exact_radius);
            double control_area_sum = 0.0;
            double weighted_radius_sum = 0.0;
            for(std::size_t index = 0; index < mesh.vertices.size(); ++index) {
                control_area_sum += control_areas[index];
                weighted_radius_sum += control_areas[index]
                    * norm(mesh.vertices[index].position);
            }
            const double control_area_mean_radius
                = weighted_radius_sum / control_area_sum;
            const double energy = configuration.surface_tension * geometry.area;
            const double previous_energy = result.samples.empty()
                ? energy
                : result.samples.back().global.registered_surface_energy;
            const double dissipation = motion == nullptr
                ? 0.0
                : motion->viscous_dissipation;
            const double ledger_residual = energy - previous_energy + dissipation;
            const double normalized_cache = cache_residual(
                target,
                geometry,
                initial_geometry.area,
                initial_geometry.volume,
                configuration.reference_radius
            );

            double valence_five_radial_square_sum = 0.0;
            double closed_one_ring_radial_square_sum = 0.0;
            double maximum_valence_five_radial_error = 0.0;
            double maximum_closed_one_ring_radial_error = 0.0;
            double maximum_valence_five_error_over_h = 0.0;
            double maximum_closed_one_ring_error_over_h = 0.0;
            for(std::size_t index = 0; index < mesh.vertices.size(); ++index) {
                const double radial_error = std::abs(
                    norm(mesh.vertices[index].position) - exact_radius
                );
                if(local_reference.is_valence_five[index]) {
                    valence_five_radial_square_sum += radial_error * radial_error;
                    maximum_valence_five_radial_error = std::max(
                        maximum_valence_five_radial_error,
                        radial_error
                    );
                    maximum_valence_five_error_over_h = std::max(
                        maximum_valence_five_error_over_h,
                        radial_error
                            / local_reference.initial_incident_edge_mean[index]
                    );
                }
                if(local_reference.is_closed_one_ring[index]) {
                    closed_one_ring_radial_square_sum += radial_error * radial_error;
                    maximum_closed_one_ring_radial_error = std::max(
                        maximum_closed_one_ring_radial_error,
                        radial_error
                    );
                    maximum_closed_one_ring_error_over_h = std::max(
                        maximum_closed_one_ring_error_over_h,
                        radial_error
                            / local_reference.initial_incident_edge_mean[index]
                    );
                }
            }
            const double radial_excursion = std::max(
                std::abs(exact_radius - configuration.reference_radius),
                1.0e-12
            );
            const double maximum_valence_five_excursion_error = step == 0
                ? 0.0
                : maximum_valence_five_radial_error / radial_excursion;
            const double maximum_closed_one_ring_excursion_error = step == 0
                ? 0.0
                : maximum_closed_one_ring_radial_error / radial_excursion;
            if(step == 0) {
                maximum_valence_five_error_over_h = 0.0;
                maximum_closed_one_ring_error_over_h = 0.0;
            }
            double maximum_edge_scaling_error = 0.0;
            const double exact_radius_ratio
                = exact_radius / configuration.reference_radius;
            for(std::size_t edge_index = 0;
                edge_index < local_reference.closed_one_ring_edges.size();
                ++edge_index) {
                const auto& endpoints
                    = local_reference.closed_one_ring_edges[edge_index];
                const double current_length = norm(subtract(
                    mesh.vertices.at(endpoints[0]).position,
                    mesh.vertices.at(endpoints[1]).position
                ));
                const double relative_scaling = current_length
                    / local_reference.closed_one_ring_initial_edge_lengths[edge_index]
                    / exact_radius_ratio;
                maximum_edge_scaling_error = std::max(
                    maximum_edge_scaling_error,
                    std::abs(relative_scaling - 1.0)
                );
            }
            double local_minimum_quality = 1.0;
            for(const auto face_index
                : local_reference.closed_one_ring_incident_faces) {
                local_minimum_quality = std::min(
                    local_minimum_quality,
                    triangle_quality(mesh, face_index)
                );
            }
            const auto local_force = audit_family_c_local_normal_error(
                target,
                mesh,
                control_areas,
                local_reference,
                configuration.damping.coefficient,
                exact_normal_velocity
            );

            FamilyCSmoothSphereTrajectorySample sample;
            sample.global = SurfaceTensionShortTrajectorySample{
                step,
                time,
                geometry.area,
                geometry.area / initial_geometry.area,
                geometry.volume,
                geometry.volume / initial_geometry.volume,
                geometry.centroid,
                norm(subtract(geometry.centroid, initial_centroid))
                    / configuration.reference_radius,
                energy,
                energy / result.initial_registered_surface_energy,
                dissipation,
                ledger_residual,
                geometry.minimum_oriented_face_alignment,
                geometry.minimum_triangle_quality,
                geometry.minimum_face_area / initial_geometry.minimum_face_area,
                normalized_cache,
            };
            sample.exact_radius = exact_radius;
            sample.control_area_mean_radius = control_area_mean_radius;
            sample.control_area_mean_radius_ratio = control_area_mean_radius
                / configuration.reference_radius;
            sample.maximum_valence_five_excursion_error
                = maximum_valence_five_excursion_error;
            sample.rms_valence_five_radial_error = std::sqrt(
                valence_five_radial_square_sum
                / static_cast<double>(result.valence_five_vertex_count)
            );
            sample.maximum_closed_one_ring_excursion_error
                = maximum_closed_one_ring_excursion_error;
            sample.rms_closed_one_ring_radial_error = std::sqrt(
                closed_one_ring_radial_square_sum
                / static_cast<double>(result.closed_one_ring_vertex_count)
            );
            sample.maximum_valence_five_error_over_initial_h
                = maximum_valence_five_error_over_h;
            sample.maximum_closed_one_ring_error_over_initial_h
                = maximum_closed_one_ring_error_over_h;
            sample.maximum_closed_one_ring_edge_scaling_error
                = maximum_edge_scaling_error;
            sample.local_minimum_triangle_quality = local_minimum_quality;
            sample.local_minimum_triangle_quality_ratio = local_minimum_quality
                / result.initial_local_minimum_triangle_quality;
            sample.valence_five_normal_error_energy_fraction
                = local_force.valence_five_energy_fraction;
            sample.valence_five_normal_error_relative_rms
                = local_force.valence_five_relative_rms;
            sample.valence_five_normal_error_pointwise_maximum
                = local_force.valence_five_pointwise_maximum;
            sample.closed_one_ring_normal_error_energy_fraction
                = local_force.closed_one_ring_energy_fraction;
            sample.closed_one_ring_normal_error_relative_rms
                = local_force.closed_one_ring_relative_rms;
            sample.closed_one_ring_normal_error_pointwise_maximum
                = local_force.closed_one_ring_pointwise_maximum;
            sample.force_buffers_cleared = local_force.force_buffers_cleared;
            result.samples.push_back(sample);
            result.cumulative_positive_energy_balance_residual += std::max(
                0.0,
                ledger_residual
            );
            result.minimum_oriented_face_alignment = std::min(
                result.minimum_oriented_face_alignment,
                sample.global.minimum_oriented_face_alignment
            );
            result.minimum_triangle_quality = std::min(
                result.minimum_triangle_quality,
                sample.global.minimum_triangle_quality
            );
            result.minimum_face_area_ratio = std::min(
                result.minimum_face_area_ratio,
                sample.global.minimum_face_area_ratio
            );
            result.maximum_normalized_cache_residual = std::max(
                result.maximum_normalized_cache_residual,
                sample.global.maximum_normalized_cache_residual
            );
            result.maximum_normalized_centroid_drift = std::max(
                result.maximum_normalized_centroid_drift,
                sample.global.normalized_surface_centroid_drift
            );
        };

        append_sample(0, 0.0, nullptr);
        const auto damping = surface_damping(configuration.damping);
        for(std::size_t step = 1; step <= configuration.step_count; ++step) {
            const auto state_before = cell_state_hash(target);
            try {
                target.apply_internal_forces(configuration.time_step);
                const auto motion = advance_surface_overdamped(
                    target,
                    target.get_mesh_revision(),
                    configuration.time_step,
                    damping
                );
                append_sample(
                    step,
                    static_cast<double>(step) * configuration.time_step,
                    &motion
                );
            } catch(const std::exception& error) {
                static_cast<void>(reset_surface_forces(
                    target,
                    target.get_mesh_revision()
                ));
                return fail(
                    classify_failure(error.what()),
                    step,
                    static_cast<double>(step - 1) * configuration.time_step,
                    error.what(),
                    state_before
                );
            }
        }
        result.normalized_positive_energy_balance_residual
            = result.cumulative_positive_energy_balance_residual
                / result.initial_registered_surface_energy;
        result.status = ShortTrajectoryStatus::passed;
        return result;
    } catch(const std::exception& error) {
        return fail(
            classify_failure(error.what()),
            result.samples.size(),
            result.samples.empty() ? 0.0 : result.samples.back().global.time,
            error.what(),
            entry_hash
        );
    }
}

FamilyCSmoothSphereGateAudit evaluate_family_c_smooth_sphere_gate(
    const std::array<FamilyCSmoothSphereTrajectoryAudit, 4>& levels,
    const FamilyCSmoothSphereTrajectoryAudit& finest_half_time_step,
    const FamilyCSmoothSphereGateThresholds& thresholds
) {
    const std::array<double, 13> threshold_values{
        thresholds.maximum_finest_excursion_normalized_error,
        thresholds.minimum_observed_order,
        thresholds.roundoff_plateau_threshold,
        thresholds.maximum_time_pollution_fraction,
        thresholds.minimum_triangle_quality,
        thresholds.minimum_face_area_ratio,
        thresholds.maximum_normalized_cache_residual,
        thresholds.maximum_normalized_centroid_drift,
        thresholds.maximum_normalized_positive_energy_residual,
        thresholds.maximum_local_excursion_normalized_error,
        thresholds.maximum_local_edge_scaling_error,
        thresholds.maximum_local_radial_error_over_initial_h,
        thresholds.minimum_local_triangle_quality_ratio,
    };
    if(!std::all_of(
            threshold_values.begin(),
            threshold_values.end(),
            [](const double value) { return std::isfinite(value) && value >= 0.0; }
        )
       || thresholds.minimum_triangle_quality > 1.0
       || thresholds.minimum_face_area_ratio > 1.0
       || thresholds.minimum_local_triangle_quality_ratio > 1.0) {
        throw std::invalid_argument("Family C smooth trajectory thresholds are invalid");
    }

    FamilyCSmoothSphereGateAudit result;
    result.force_buffers_cleared = true;
    result.trajectories_passed = std::all_of(
        levels.begin(),
        levels.end(),
        [](const auto& audit) {
            return audit.status == ShortTrajectoryStatus::passed
                && !audit.samples.empty();
        }
    ) && finest_half_time_step.status == ShortTrajectoryStatus::passed
        && !finest_half_time_step.samples.empty();
    if(!result.trajectories_passed) return result;

    const auto& reference = levels.front().configuration;
    auto nearly_equal = [](const double left, const double right) {
        return std::abs(left - right)
            <= 1.0e-12 * std::max({1.0, std::abs(left), std::abs(right)});
    };
    const double final_time = reference.time_step
        * static_cast<double>(reference.step_count);
    for(std::size_t index = 0; index < levels.size(); ++index) {
        const auto& audit = levels[index];
        const auto& configuration = audit.configuration;
        if(configuration.damping.measure
                != CellSurfaceDampingMeasure::barycentric_dual_area
           || configuration.step_count != reference.step_count
           || audit.samples.size() != configuration.step_count + 1
           || !nearly_equal(configuration.time_step, reference.time_step)
           || !nearly_equal(configuration.surface_tension, reference.surface_tension)
           || !nearly_equal(
                configuration.damping.coefficient,
                reference.damping.coefficient
              )
           || !nearly_equal(
                configuration.reference_radius,
                reference.reference_radius
              )
           || !nearly_equal(audit.samples.back().global.time, final_time)) {
            throw std::invalid_argument(
                "Family C spatial gate requires one frozen physical trajectory configuration"
            );
        }
        result.rms_edge_lengths[index] = audit.initial_rms_edge_length;
    }
    const auto& half_configuration = finest_half_time_step.configuration;
    if(half_configuration.damping.measure
            != CellSurfaceDampingMeasure::barycentric_dual_area
       || finest_half_time_step.samples.size()
            != half_configuration.step_count + 1
       || half_configuration.step_count != 2 * reference.step_count
       || !nearly_equal(2.0 * half_configuration.time_step, reference.time_step)
       || !nearly_equal(
            half_configuration.time_step
                * static_cast<double>(half_configuration.step_count),
            final_time
          )
       || !nearly_equal(
            half_configuration.surface_tension,
            reference.surface_tension
          )
       || !nearly_equal(
            half_configuration.damping.coefficient,
            reference.damping.coefficient
          )
       || !nearly_equal(
            half_configuration.reference_radius,
            reference.reference_radius
          )
       || !nearly_equal(
            finest_half_time_step.initial_rms_edge_length,
            levels.back().initial_rms_edge_length
          )) {
        throw std::invalid_argument(
            "Family C time-pollution gate requires the frozen finest dt/2 run"
        );
    }
    result.mesh_scales_decreased = true;
    for(std::size_t index = 0; index + 1 < levels.size(); ++index) {
        result.mesh_scales_decreased = result.mesh_scales_decreased
            && result.rms_edge_lengths[index + 1]
                < result.rms_edge_lengths[index];
    }

    const double exact_radius_squared
        = reference.reference_radius * reference.reference_radius
        - 4.0 * reference.surface_tension * final_time
            / reference.damping.coefficient;
    if(!std::isfinite(exact_radius_squared) || exact_radius_squared <= 0.0) {
        throw std::invalid_argument("Family C exact final radius is invalid");
    }
    const double exact_radius_ratio = std::sqrt(exact_radius_squared)
        / reference.reference_radius;
    const std::array<double, 4> exact_values{
        exact_radius_ratio,
        exact_radius_ratio * exact_radius_ratio,
        exact_radius_ratio * exact_radius_ratio * exact_radius_ratio,
        exact_radius_ratio * exact_radius_ratio,
    };
    auto qoi_value = [](const FamilyCSmoothSphereTrajectorySample& sample,
                        const std::size_t metric) {
        switch(metric) {
            case 0: return sample.control_area_mean_radius_ratio;
            case 1: return sample.global.area_ratio;
            case 2: return sample.global.volume_ratio;
            case 3: return sample.global.energy_ratio;
            default: throw std::logic_error("Family C QoI index is invalid");
        }
    };
    auto observed_order = [&](const double coarse_error,
                              const double fine_error,
                              const double coarse_h,
                              const double fine_h) {
        if(!std::isfinite(coarse_error) || !std::isfinite(fine_error)
           || coarse_error <= 0.0 || fine_error <= 0.0
           || !std::isfinite(coarse_h) || !std::isfinite(fine_h)
           || coarse_h <= fine_h || fine_h <= 0.0) {
            return std::numeric_limits<double>::quiet_NaN();
        }
        return std::log(coarse_error / fine_error)
            / std::log(coarse_h / fine_h);
    };
    auto generalized_order = [](const double coarse_difference,
                                const double fine_difference,
                                const double coarse_h,
                                const double middle_h,
                                const double fine_h) {
        if(!std::isfinite(coarse_difference)
           || !std::isfinite(fine_difference)
           || coarse_difference <= 0.0 || fine_difference <= 0.0
           || !std::isfinite(coarse_h) || !std::isfinite(middle_h)
           || !std::isfinite(fine_h)
           || coarse_h <= middle_h || middle_h <= fine_h || fine_h <= 0.0) {
            return std::numeric_limits<double>::quiet_NaN();
        }
        const double target = coarse_difference / fine_difference;
        auto ratio = [&](const double order) {
            if(std::abs(order) < 1.0e-10) {
                return std::log(coarse_h / middle_h)
                    / std::log(middle_h / fine_h);
            }
            return (std::pow(coarse_h, order) - std::pow(middle_h, order))
                / (std::pow(middle_h, order) - std::pow(fine_h, order));
        };
        auto residual = [&](const double order) {
            const double current_ratio = ratio(order);
            if(!std::isfinite(current_ratio) || current_ratio <= 0.0) {
                return std::numeric_limits<double>::quiet_NaN();
            }
            return std::log(current_ratio / target);
        };
        constexpr double minimum_search_order = 0.0;
        constexpr double maximum_search_order = 16.0;
        constexpr std::size_t search_intervals = 4096;
        double left = minimum_search_order;
        double left_residual = residual(left);
        for(std::size_t index = 1; index <= search_intervals; ++index) {
            const double right = minimum_search_order
                + (maximum_search_order - minimum_search_order)
                    * static_cast<double>(index)
                    / static_cast<double>(search_intervals);
            const double right_residual = residual(right);
            if(std::isfinite(left_residual) && std::isfinite(right_residual)
               && (left_residual == 0.0 || right_residual == 0.0
                   || std::signbit(left_residual) != std::signbit(right_residual))) {
                double bracket_left = left;
                double bracket_right = right;
                for(std::size_t iteration = 0; iteration < 100; ++iteration) {
                    const double middle = 0.5 * (bracket_left + bracket_right);
                    const double middle_residual = residual(middle);
                    if(!std::isfinite(middle_residual)) break;
                    const double bracket_left_residual = residual(bracket_left);
                    if(middle_residual == 0.0
                       || std::abs(bracket_right - bracket_left) <= 1.0e-12) {
                        return middle;
                    }
                    if(std::signbit(bracket_left_residual)
                       != std::signbit(middle_residual)) {
                        bracket_right = middle;
                    } else {
                        bracket_left = middle;
                    }
                }
                return 0.5 * (bracket_left + bracket_right);
            }
            left = right;
            left_residual = right_residual;
        }
        return std::numeric_limits<double>::quiet_NaN();
    };

    result.analytic_qois_passed = true;
    result.self_convergence_passed = true;
    result.time_pollution_passed = true;
    for(std::size_t metric = 0; metric < result.qois.size(); ++metric) {
        auto& qoi = result.qois[metric];
        qoi.exact_final_value = exact_values[metric];
        for(std::size_t level = 0; level < levels.size(); ++level) {
            const double initial_value = qoi_value(
                levels[level].samples.front(),
                metric
            );
            qoi.analytic_excursions[level] = std::max(
                std::abs(qoi.exact_final_value - initial_value),
                1.0e-12
            );
            qoi.responses[level] = qoi_value(levels[level].samples.back(), metric);
            qoi.excursion_normalized_analytic_errors[level] = std::abs(
                qoi.responses[level] - qoi.exact_final_value
            ) / qoi.analytic_excursions[level];
        }
        qoi.exact_excursion = qoi.analytic_excursions.back();
        qoi.analytic_roundoff_plateau = std::all_of(
            qoi.excursion_normalized_analytic_errors.begin(),
            qoi.excursion_normalized_analytic_errors.end(),
            [&](const double error) {
                return error <= thresholds.roundoff_plateau_threshold;
            }
        );
        qoi.analytic_errors_monotonic = true;
        qoi.analytic_orders_passed = true;
        for(std::size_t pair = 0; pair < 3; ++pair) {
            const double coarse_error
                = qoi.excursion_normalized_analytic_errors[pair];
            const double fine_error
                = qoi.excursion_normalized_analytic_errors[pair + 1];
            qoi.analytic_errors_monotonic
                = qoi.analytic_errors_monotonic && fine_error <= coarse_error;
            qoi.analytic_observed_orders[pair] = observed_order(
                coarse_error,
                fine_error,
                result.rms_edge_lengths[pair],
                result.rms_edge_lengths[pair + 1]
            );
            qoi.analytic_orders_passed = qoi.analytic_orders_passed
                && (qoi.analytic_roundoff_plateau
                    || (std::isfinite(qoi.analytic_observed_orders[pair])
                        && qoi.analytic_observed_orders[pair]
                            >= thresholds.minimum_observed_order));
        }
        qoi.finest_error_passed
            = qoi.excursion_normalized_analytic_errors.back()
            <= thresholds.maximum_finest_excursion_normalized_error;
        for(std::size_t pair = 0; pair < 3; ++pair) {
            qoi.adjacent_difference_excursions[pair] = std::max(
                std::abs(
                    qoi.exact_final_value
                    - qoi_value(levels[pair].samples.front(), metric)
                ),
                1.0e-12
            );
            qoi.excursion_normalized_adjacent_differences[pair] = std::abs(
                qoi.responses[pair] - qoi.responses[pair + 1]
            ) / qoi.adjacent_difference_excursions[pair];
        }
        qoi.self_convergence_roundoff_plateau = std::all_of(
            qoi.excursion_normalized_adjacent_differences.begin(),
            qoi.excursion_normalized_adjacent_differences.end(),
            [&](const double difference) {
                return difference <= thresholds.roundoff_plateau_threshold;
            }
        );
        qoi.self_convergence_monotonic = true;
        qoi.self_convergence_orders_passed = true;
        for(std::size_t triplet = 0; triplet < 2; ++triplet) {
            const double coarse_difference
                = qoi.excursion_normalized_adjacent_differences[triplet];
            const double fine_difference
                = qoi.excursion_normalized_adjacent_differences[triplet + 1];
            qoi.self_convergence_monotonic
                = qoi.self_convergence_monotonic
                && fine_difference <= coarse_difference;
            qoi.generalized_self_convergence_orders[triplet]
                = generalized_order(
                    coarse_difference,
                    fine_difference,
                    result.rms_edge_lengths[triplet],
                    result.rms_edge_lengths[triplet + 1],
                    result.rms_edge_lengths[triplet + 2]
                );
            qoi.self_convergence_orders_passed
                = qoi.self_convergence_orders_passed
                && (qoi.self_convergence_roundoff_plateau
                    || (std::isfinite(
                            qoi.generalized_self_convergence_orders[triplet]
                        )
                        && qoi.generalized_self_convergence_orders[triplet]
                            >= thresholds.minimum_observed_order));
        }
        qoi.passed = qoi.analytic_errors_monotonic
            && qoi.analytic_orders_passed
            && qoi.finest_error_passed
            && qoi.self_convergence_monotonic
            && qoi.self_convergence_orders_passed;
        result.analytic_qois_passed = result.analytic_qois_passed
            && qoi.analytic_errors_monotonic
            && qoi.analytic_orders_passed
            && qoi.finest_error_passed;
        result.self_convergence_passed = result.self_convergence_passed
            && qoi.self_convergence_monotonic
            && qoi.self_convergence_orders_passed;

        auto& time = result.time_pollution[metric];
        time.coarse_time_step_response = qoi.responses.back();
        time.half_time_step_response = qoi_value(
            finest_half_time_step.samples.back(),
            metric
        );
        time.exact_final_value = qoi.exact_final_value;
        time.exact_excursion = std::max(
            std::abs(
                time.exact_final_value
                - qoi_value(finest_half_time_step.samples.front(), metric)
            ),
            1.0e-12
        );
        time.absolute_time_difference = std::abs(
            time.coarse_time_step_response - time.half_time_step_response
        );
        time.excursion_normalized_time_difference
            = time.absolute_time_difference / time.exact_excursion;
        time.absolute_space_proxy = std::abs(
            time.half_time_step_response - time.exact_final_value
        );
        time.excursion_normalized_space_proxy
            = time.absolute_space_proxy / time.exact_excursion;
        time.roundoff_plateau
            = time.absolute_time_difference
                <= thresholds.roundoff_plateau_threshold
            && time.absolute_space_proxy
                <= thresholds.roundoff_plateau_threshold;
        time.passed = time.roundoff_plateau
            || time.absolute_time_difference
                <= thresholds.maximum_time_pollution_fraction
                    * time.absolute_space_proxy;
        result.time_pollution_passed = result.time_pollution_passed
            && time.passed;
    }

    auto audit_run = [&](const FamilyCSmoothSphereTrajectoryAudit& audit) {
        result.minimum_oriented_face_alignment = std::min(
            result.minimum_oriented_face_alignment,
            audit.minimum_oriented_face_alignment
        );
        result.minimum_triangle_quality = std::min(
            result.minimum_triangle_quality,
            audit.minimum_triangle_quality
        );
        result.minimum_face_area_ratio = std::min(
            result.minimum_face_area_ratio,
            audit.minimum_face_area_ratio
        );
        result.maximum_normalized_cache_residual = std::max(
            result.maximum_normalized_cache_residual,
            audit.maximum_normalized_cache_residual
        );
        result.maximum_normalized_centroid_drift = std::max(
            result.maximum_normalized_centroid_drift,
            audit.maximum_normalized_centroid_drift
        );
        result.maximum_normalized_positive_energy_residual = std::max(
            result.maximum_normalized_positive_energy_residual,
            audit.normalized_positive_energy_balance_residual
        );
        for(const auto& sample : audit.samples) {
            result.maximum_valence_five_excursion_error = std::max(
                result.maximum_valence_five_excursion_error,
                sample.maximum_valence_five_excursion_error
            );
            result.maximum_closed_one_ring_excursion_error = std::max(
                result.maximum_closed_one_ring_excursion_error,
                sample.maximum_closed_one_ring_excursion_error
            );
            result.maximum_valence_five_error_over_initial_h = std::max(
                result.maximum_valence_five_error_over_initial_h,
                sample.maximum_valence_five_error_over_initial_h
            );
            result.maximum_closed_one_ring_error_over_initial_h = std::max(
                result.maximum_closed_one_ring_error_over_initial_h,
                sample.maximum_closed_one_ring_error_over_initial_h
            );
            result.maximum_closed_one_ring_edge_scaling_error = std::max(
                result.maximum_closed_one_ring_edge_scaling_error,
                sample.maximum_closed_one_ring_edge_scaling_error
            );
            result.minimum_local_triangle_quality_ratio = std::min(
                result.minimum_local_triangle_quality_ratio,
                sample.local_minimum_triangle_quality_ratio
            );
            result.force_buffers_cleared = result.force_buffers_cleared
                && sample.force_buffers_cleared;
        }
    };
    for(const auto& audit : levels) audit_run(audit);
    audit_run(finest_half_time_step);

    result.global_geometry_passed
        = result.minimum_oriented_face_alignment > 0.0
        && result.minimum_triangle_quality >= thresholds.minimum_triangle_quality
        && result.minimum_face_area_ratio >= thresholds.minimum_face_area_ratio
        && result.maximum_normalized_cache_residual
            <= thresholds.maximum_normalized_cache_residual
        && result.maximum_normalized_centroid_drift
            <= thresholds.maximum_normalized_centroid_drift;
    result.energy_coverage_passed
        = result.maximum_normalized_positive_energy_residual
        <= thresholds.maximum_normalized_positive_energy_residual;
    result.local_risk_bounds_passed
        = result.maximum_valence_five_excursion_error
            <= thresholds.maximum_local_excursion_normalized_error
        && result.maximum_closed_one_ring_excursion_error
            <= thresholds.maximum_local_excursion_normalized_error
        && result.maximum_valence_five_error_over_initial_h
            <= thresholds.maximum_local_radial_error_over_initial_h
        && result.maximum_closed_one_ring_error_over_initial_h
            <= thresholds.maximum_local_radial_error_over_initial_h
        && result.maximum_closed_one_ring_edge_scaling_error
            <= thresholds.maximum_local_edge_scaling_error
        && result.minimum_local_triangle_quality_ratio
            >= thresholds.minimum_local_triangle_quality_ratio;
    result.passed = result.trajectories_passed
        && result.mesh_scales_decreased
        && result.analytic_qois_passed
        && result.self_convergence_passed
        && result.time_pollution_passed
        && result.global_geometry_passed
        && result.energy_coverage_passed
        && result.local_risk_bounds_passed
        && result.force_buffers_cleared;
    return result;
}

MeanRadiusTimeFloorGateAudit evaluate_mean_radius_time_floor(
    const std::array<
        std::array<FamilyCSmoothSphereTrajectoryAudit, 4>,
        2
    >& runs,
    const MeanRadiusTimeFloorThresholds& thresholds
) {
    const std::array<double, 14> threshold_values{
        thresholds.minimum_time_order,
        thresholds.maximum_time_order,
        thresholds.common_raw_roundoff_plateau,
        thresholds.maximum_richardson_error,
        thresholds.maximum_cross_mesh_richardson_difference,
        thresholds.minimum_triangle_quality,
        thresholds.minimum_face_area_ratio,
        thresholds.maximum_normalized_cache_residual,
        thresholds.maximum_normalized_centroid_drift,
        thresholds.maximum_normalized_positive_energy_residual,
        thresholds.maximum_local_excursion_normalized_error,
        thresholds.maximum_local_edge_scaling_error,
        thresholds.maximum_local_radial_error_over_initial_h,
        thresholds.minimum_local_triangle_quality_ratio,
    };
    if(!std::all_of(
            threshold_values.begin(),
            threshold_values.end(),
            [](const double value) { return std::isfinite(value) && value >= 0.0; }
        )
       || thresholds.minimum_time_order > thresholds.maximum_time_order
       || thresholds.minimum_triangle_quality > 1.0
       || thresholds.minimum_face_area_ratio > 1.0
       || thresholds.minimum_local_triangle_quality_ratio > 1.0) {
        throw std::invalid_argument("mean-radius time-floor thresholds are invalid");
    }
    constexpr std::array<double, 4> expected_time_steps{
        4.0e-4, 2.0e-4, 1.0e-4, 5.0e-5
    };
    constexpr std::array<std::size_t, 4> expected_step_counts{
        50, 100, 200, 400
    };
    constexpr double expected_final_time = 2.0e-2;
    constexpr double expected_surface_tension = 2.0e-2;
    constexpr double expected_damping_per_area = 10.0;
    constexpr double expected_reference_radius = 1.0;
    auto nearly_equal = [](const double left, const double right) {
        return std::abs(left - right)
            <= 1.0e-12 * std::max({1.0, std::abs(left), std::abs(right)});
    };

    MeanRadiusTimeFloorGateAudit result;
    result.trajectories_passed = true;
    for(std::size_t level = 0; level < runs.size(); ++level) {
        for(std::size_t time_index = 0;
            time_index < runs[level].size();
            ++time_index) {
            const auto& audit = runs[level][time_index];
            const auto& configuration = audit.configuration;
            result.trajectories_passed = result.trajectories_passed
                && audit.status == ShortTrajectoryStatus::passed
                && !audit.failure.has_value()
                && audit.samples.size() == expected_step_counts[time_index] + 1
                && configuration.step_count == expected_step_counts[time_index]
                && nearly_equal(
                    configuration.time_step,
                    expected_time_steps[time_index]
                )
                && nearly_equal(
                    configuration.time_step
                        * static_cast<double>(configuration.step_count),
                    expected_final_time
                )
                && nearly_equal(
                    configuration.surface_tension,
                    expected_surface_tension
                )
                && configuration.damping.measure
                    == CellSurfaceDampingMeasure::barycentric_dual_area
                && nearly_equal(
                    configuration.damping.coefficient,
                    expected_damping_per_area
                )
                && nearly_equal(
                    configuration.reference_radius,
                    expected_reference_radius
                )
                && !audit.samples.empty()
                && nearly_equal(
                    audit.samples.back().global.time,
                    expected_final_time
                );
        }
    }
    if(!result.trajectories_passed) return result;
    for(std::size_t level = 0; level < runs.size(); ++level) {
        for(std::size_t time_index = 1;
            time_index < runs[level].size();
            ++time_index) {
            if(!nearly_equal(
                    runs[level][time_index].initial_rms_edge_length,
                    runs[level][0].initial_rms_edge_length
                )) {
                throw std::invalid_argument(
                    "mean-radius time-floor runs changed the initial mesh"
                );
            }
        }
    }
    if(!(runs[0][0].initial_rms_edge_length
         > runs[1][0].initial_rms_edge_length)) {
        throw std::invalid_argument(
            "mean-radius time-floor levels must be coarse then fine"
        );
    }
    const double exact_radius_squared
        = expected_reference_radius * expected_reference_radius
        - 4.0 * expected_surface_tension * expected_final_time
            / expected_damping_per_area;
    result.exact_mean_radius_response = std::sqrt(exact_radius_squared)
        / expected_reference_radius;
    result.time_levels_passed = true;
    result.readonly_controls_passed = true;

    for(std::size_t level = 0; level < runs.size(); ++level) {
        auto& current = result.levels[level];
        current.initial_rms_edge_length
            = runs[level][0].initial_rms_edge_length;
        current.time_steps = expected_time_steps;
        current.step_counts = expected_step_counts;
        current.exact_mean_radius_response = result.exact_mean_radius_response;
        current.force_buffers_cleared = true;
        for(std::size_t time_index = 0;
            time_index < runs[level].size();
            ++time_index) {
            const auto& audit = runs[level][time_index];
            const auto& final_sample = audit.samples.back();
            current.mean_radius_responses[time_index]
                = final_sample.control_area_mean_radius_ratio;
            current.final_area_ratios[time_index]
                = final_sample.global.area_ratio;
            current.final_volume_ratios[time_index]
                = final_sample.global.volume_ratio;
            current.final_registered_energy_ratios[time_index]
                = final_sample.global.energy_ratio;
            current.minimum_oriented_face_alignment = std::min(
                current.minimum_oriented_face_alignment,
                audit.minimum_oriented_face_alignment
            );
            current.minimum_triangle_quality = std::min(
                current.minimum_triangle_quality,
                audit.minimum_triangle_quality
            );
            current.minimum_face_area_ratio = std::min(
                current.minimum_face_area_ratio,
                audit.minimum_face_area_ratio
            );
            current.maximum_normalized_cache_residual = std::max(
                current.maximum_normalized_cache_residual,
                audit.maximum_normalized_cache_residual
            );
            current.maximum_normalized_centroid_drift = std::max(
                current.maximum_normalized_centroid_drift,
                audit.maximum_normalized_centroid_drift
            );
            current.maximum_normalized_positive_energy_residual = std::max(
                current.maximum_normalized_positive_energy_residual,
                audit.normalized_positive_energy_balance_residual
            );
            for(const auto& sample : audit.samples) {
                current.maximum_valence_five_excursion_error = std::max(
                    current.maximum_valence_five_excursion_error,
                    sample.maximum_valence_five_excursion_error
                );
                current.maximum_closed_one_ring_excursion_error = std::max(
                    current.maximum_closed_one_ring_excursion_error,
                    sample.maximum_closed_one_ring_excursion_error
                );
                current.maximum_valence_five_error_over_initial_h = std::max(
                    current.maximum_valence_five_error_over_initial_h,
                    sample.maximum_valence_five_error_over_initial_h
                );
                current.maximum_closed_one_ring_error_over_initial_h = std::max(
                    current.maximum_closed_one_ring_error_over_initial_h,
                    sample.maximum_closed_one_ring_error_over_initial_h
                );
                current.maximum_closed_one_ring_edge_scaling_error = std::max(
                    current.maximum_closed_one_ring_edge_scaling_error,
                    sample.maximum_closed_one_ring_edge_scaling_error
                );
                current.minimum_local_triangle_quality_ratio = std::min(
                    current.minimum_local_triangle_quality_ratio,
                    sample.local_minimum_triangle_quality_ratio
                );
                current.force_buffers_cleared = current.force_buffers_cleared
                    && sample.force_buffers_cleared;
            }
        }
        for(std::size_t pair = 0; pair < 3; ++pair) {
            current.adjacent_time_differences[pair] = std::abs(
                current.mean_radius_responses[pair]
                - current.mean_radius_responses[pair + 1]
            );
        }
        current.common_roundoff_plateau = std::all_of(
            current.adjacent_time_differences.begin(),
            current.adjacent_time_differences.end(),
            [&](const double difference) {
                return difference <= thresholds.common_raw_roundoff_plateau;
            }
        );
        current.differences_strictly_decreased
            = current.adjacent_time_differences[0]
                > current.adjacent_time_differences[1]
            && current.adjacent_time_differences[1]
                > current.adjacent_time_differences[2];
        current.time_orders_passed = !current.common_roundoff_plateau;
        for(std::size_t order_index = 0; order_index < 2; ++order_index) {
            const double coarse_difference
                = current.adjacent_time_differences[order_index];
            const double fine_difference
                = current.adjacent_time_differences[order_index + 1];
            current.observed_time_orders[order_index]
                = coarse_difference > 0.0 && fine_difference > 0.0
                ? std::log2(coarse_difference / fine_difference)
                : std::numeric_limits<double>::quiet_NaN();
            current.time_orders_passed = current.time_orders_passed
                && std::isfinite(current.observed_time_orders[order_index])
                && current.observed_time_orders[order_index]
                    >= thresholds.minimum_time_order
                && current.observed_time_orders[order_index]
                    <= thresholds.maximum_time_order;
        }
        current.richardson_response
            = 2.0 * current.mean_radius_responses[3]
            - current.mean_radius_responses[2];
        current.richardson_error = std::abs(
            current.richardson_response - current.exact_mean_radius_response
        );
        current.richardson_passed = current.richardson_error
            <= thresholds.maximum_richardson_error;
        current.readonly_controls_passed
            = current.minimum_oriented_face_alignment > 0.0
            && current.minimum_triangle_quality
                >= thresholds.minimum_triangle_quality
            && current.minimum_face_area_ratio
                >= thresholds.minimum_face_area_ratio
            && current.maximum_normalized_cache_residual
                <= thresholds.maximum_normalized_cache_residual
            && current.maximum_normalized_centroid_drift
                <= thresholds.maximum_normalized_centroid_drift
            && current.maximum_normalized_positive_energy_residual
                <= thresholds.maximum_normalized_positive_energy_residual
            && current.maximum_valence_five_excursion_error
                <= thresholds.maximum_local_excursion_normalized_error
            && current.maximum_closed_one_ring_excursion_error
                <= thresholds.maximum_local_excursion_normalized_error
            && current.maximum_valence_five_error_over_initial_h
                <= thresholds.maximum_local_radial_error_over_initial_h
            && current.maximum_closed_one_ring_error_over_initial_h
                <= thresholds.maximum_local_radial_error_over_initial_h
            && current.maximum_closed_one_ring_edge_scaling_error
                <= thresholds.maximum_local_edge_scaling_error
            && current.minimum_local_triangle_quality_ratio
                >= thresholds.minimum_local_triangle_quality_ratio
            && current.force_buffers_cleared;
        current.passed = !current.common_roundoff_plateau
            && current.differences_strictly_decreased
            && current.time_orders_passed
            && current.richardson_passed
            && current.readonly_controls_passed;
        result.time_levels_passed = result.time_levels_passed
            && !current.common_roundoff_plateau
            && current.differences_strictly_decreased
            && current.time_orders_passed
            && current.richardson_passed;
        result.readonly_controls_passed = result.readonly_controls_passed
            && current.readonly_controls_passed;
    }
    result.cross_mesh_richardson_difference = std::abs(
        result.levels[0].richardson_response
        - result.levels[1].richardson_response
    );
    result.richardson_cross_mesh_passed
        = result.cross_mesh_richardson_difference
        <= thresholds.maximum_cross_mesh_richardson_difference;
    result.passed = result.trajectories_passed
        && result.time_levels_passed
        && result.richardson_cross_mesh_passed
        && result.readonly_controls_passed;
    return result;
}

SurfaceTensionSpatialRefinementGateAudit
evaluate_surface_tension_spatial_refinement(
    const SurfaceTensionShortTrajectoryAudit& coarse,
    const SurfaceTensionShortTrajectoryAudit& base,
    const SurfaceTensionShortTrajectoryAudit& fine,
    const SurfaceTensionSpatialRefinementThresholds& thresholds
) {
    const std::array<double, 6> values{
        thresholds.maximum_base_fine_normalized_error,
        thresholds.minimum_observed_order,
        thresholds.roundoff_plateau_threshold,
        thresholds.maximum_normalized_positive_energy_residual,
        thresholds.minimum_triangle_quality,
        thresholds.maximum_normalized_cache_residual,
    };
    if(!std::all_of(
            values.begin(),
            values.end(),
            [](const double value) { return std::isfinite(value) && value >= 0.0; }
        )
       || thresholds.minimum_triangle_quality > 1.0) {
        throw std::invalid_argument("spatial-refinement thresholds are invalid");
    }
    if(coarse.status != ShortTrajectoryStatus::passed
       || base.status != ShortTrajectoryStatus::passed
       || fine.status != ShortTrajectoryStatus::passed
       || coarse.samples.empty()
       || base.samples.empty()
       || fine.samples.empty()) {
        throw std::invalid_argument("spatial refinement requires three passed trajectories");
    }
    const ActiveTimeRefinementThresholds metric_thresholds{
        thresholds.maximum_base_fine_normalized_error,
        thresholds.minimum_observed_order,
        thresholds.roundoff_plateau_threshold,
        0.0,
        1.0,
    };
    const auto& coarse_final = coarse.samples.back();
    const auto& base_final = base.samples.back();
    const auto& fine_final = fine.samples.back();
    auto metric = [&](const double coarse_value,
                      const double base_value,
                      const double fine_value) {
        return self_convergence(
            std::abs(coarse_value - base_value),
            std::abs(base_value - fine_value),
            metric_thresholds
        );
    };

    SurfaceTensionSpatialRefinementGateAudit result;
    result.area_ratio = metric(
        coarse_final.area_ratio,
        base_final.area_ratio,
        fine_final.area_ratio
    );
    result.volume_ratio = metric(
        coarse_final.volume_ratio,
        base_final.volume_ratio,
        fine_final.volume_ratio
    );
    result.registered_energy_ratio = metric(
        coarse_final.energy_ratio,
        base_final.energy_ratio,
        fine_final.energy_ratio
    );
    result.normalized_surface_centroid_drift = metric(
        coarse_final.normalized_surface_centroid_drift,
        base_final.normalized_surface_centroid_drift,
        fine_final.normalized_surface_centroid_drift
    );
    result.minimum_oriented_face_alignment = std::min({
        coarse.minimum_oriented_face_alignment,
        base.minimum_oriented_face_alignment,
        fine.minimum_oriented_face_alignment,
    });
    result.minimum_triangle_quality = std::min({
        coarse.minimum_triangle_quality,
        base.minimum_triangle_quality,
        fine.minimum_triangle_quality,
    });
    result.minimum_face_area_ratio = std::min({
        coarse.minimum_face_area_ratio,
        base.minimum_face_area_ratio,
        fine.minimum_face_area_ratio,
    });
    result.maximum_normalized_cache_residual = std::max({
        coarse.maximum_normalized_cache_residual,
        base.maximum_normalized_cache_residual,
        fine.maximum_normalized_cache_residual,
    });
    result.energy_coverage_passed
        = coarse.normalized_positive_energy_balance_residual
            <= thresholds.maximum_normalized_positive_energy_residual
        && base.normalized_positive_energy_balance_residual
            <= thresholds.maximum_normalized_positive_energy_residual
        && fine.normalized_positive_energy_balance_residual
            <= thresholds.maximum_normalized_positive_energy_residual;
    result.surface_quality_passed
        = result.minimum_oriented_face_alignment > 0.0
        && result.minimum_triangle_quality >= thresholds.minimum_triangle_quality
        && result.minimum_face_area_ratio >= 1.0e-4;
    result.cache_consistency_passed
        = result.maximum_normalized_cache_residual
        <= thresholds.maximum_normalized_cache_residual;
    result.passed = result.area_ratio.passed
        && result.volume_ratio.passed
        && result.registered_energy_ratio.passed
        && result.normalized_surface_centroid_drift.passed
        && result.energy_coverage_passed
        && result.surface_quality_passed
        && result.cache_consistency_passed;
    return result;
}

SphericalMeanRadiusStructuralIdentityAudit
audit_spherical_mean_radius_structural_identity(
    ::cell& target,
    const double surface_tension,
    const double damping_per_area,
    const double reference_radius
) {
    if(!std::isfinite(surface_tension) || surface_tension <= 0.0
       || !std::isfinite(damping_per_area) || damping_per_area <= 0.0
       || !std::isfinite(reference_radius) || reference_radius <= 0.0) {
        throw std::invalid_argument(
            "spherical mean-radius structural audit configuration is invalid"
        );
    }
    const auto revision = target.get_mesh_revision();
    static_cast<void>(refresh_surface_geometry(target, revision));
    const auto mesh_before = capture_surface_snapshot(target);
    if(mesh_before.vertices.empty() || mesh_before.faces.empty()) {
        throw std::invalid_argument(
            "spherical mean-radius structural audit requires a mesh"
        );
    }
    const auto geometry = independent_surface_geometry(mesh_before, nullptr);
    const auto control_areas = barycentric_control_areas(mesh_before);
    const auto edge_scales = surface_edge_scales(mesh_before);
    const double dual_area_sum = std::accumulate(
        control_areas.begin(),
        control_areas.end(),
        0.0
    );
    double maximum_relative_radius_deviation = 0.0;
    for(const auto& vertex : mesh_before.vertices) {
        maximum_relative_radius_deviation = std::max(
            maximum_relative_radius_deviation,
            std::abs(norm(vertex.position) - reference_radius) / reference_radius
        );
    }
    for(const node& current_node : target.get_node_lst()) {
        if(!current_node.is_used()) continue;
        const Vector3 force{
            current_node.force().dx(),
            current_node.force().dy(),
            current_node.force().dz(),
        };
        if(norm(force) != 0.0) {
            throw std::logic_error(
                "spherical mean-radius structural audit requires empty force buffers"
            );
        }
    }
    const auto state_hash_before = cell_state_hash(target);
    const auto position_hash_before = cell_position_hash(target);
    std::vector<Vector3> forces;
    forces.reserve(mesh_before.vertices.size());
    try {
        target.apply_internal_forces(0.0);
        for(const node& current_node : target.get_node_lst()) {
            if(!current_node.is_used()) continue;
            forces.push_back({
                current_node.force().dx(),
                current_node.force().dy(),
                current_node.force().dz(),
            });
        }
    } catch(...) {
        static_cast<void>(reset_surface_forces(target, revision));
        throw;
    }
    static_cast<void>(reset_surface_forces(target, revision));
    static_cast<void>(refresh_surface_geometry(target, revision));
    if(forces.size() != mesh_before.vertices.size()) {
        throw std::runtime_error(
            "spherical mean-radius structural force order changed"
        );
    }

    double homogeneity_contraction = 0.0;
    double weighted_radial_velocity = 0.0;
    Vector3 net_force{};
    for(std::size_t index = 0; index < forces.size(); ++index) {
        const auto& position = mesh_before.vertices[index].position;
        const auto& force = forces[index];
        homogeneity_contraction += dot(position, force);
        const auto prescribed_sphere_normal = scale(
            position,
            1.0 / reference_radius
        );
        const auto velocity = scale(
            force,
            1.0 / (damping_per_area * control_areas[index])
        );
        weighted_radial_velocity += control_areas[index]
            * dot(velocity, prescribed_sphere_normal);
        net_force = add(net_force, force);
    }
    const double exact_homogeneity_contraction
        = -2.0 * surface_tension * geometry.area;
    const double homogeneity_scale = 2.0 * surface_tension * geometry.area;
    const double mean_radial_velocity
        = weighted_radial_velocity / dual_area_sum;
    const double exact_mean_radial_velocity
        = -2.0 * surface_tension / (damping_per_area * reference_radius);
    const double net_force_scale
        = surface_tension * geometry.area / reference_radius;
    const auto mesh_after = capture_surface_snapshot(target);
    if(mesh_after.vertices.size() != mesh_before.vertices.size()) {
        throw std::runtime_error(
            "spherical mean-radius structural audit changed vertex count"
        );
    }
    double maximum_position_displacement = 0.0;
    for(std::size_t index = 0; index < mesh_before.vertices.size(); ++index) {
        maximum_position_displacement = std::max(
            maximum_position_displacement,
            norm(subtract(
                mesh_after.vertices[index].position,
                mesh_before.vertices[index].position
            ))
        );
    }
    double maximum_force_buffer_norm_after = 0.0;
    for(const node& current_node : target.get_node_lst()) {
        if(!current_node.is_used()) continue;
        maximum_force_buffer_norm_after = std::max(
            maximum_force_buffer_norm_after,
            norm({
                current_node.force().dx(),
                current_node.force().dy(),
                current_node.force().dz(),
            })
        );
    }

    SphericalMeanRadiusStructuralIdentityAudit result;
    result.vertex_count = mesh_before.vertices.size();
    result.face_count = mesh_before.faces.size();
    result.rms_edge_length = edge_scales[0] / reference_radius;
    result.surface_area = geometry.area;
    result.dual_area_sum = dual_area_sum;
    result.dual_area_to_surface_area_ratio = dual_area_sum / geometry.area;
    result.homogeneity_force_contraction = homogeneity_contraction;
    result.exact_homogeneity_force_contraction
        = exact_homogeneity_contraction;
    result.normalized_homogeneity_residual = std::abs(
        homogeneity_contraction - exact_homogeneity_contraction
    ) / homogeneity_scale;
    result.mean_radial_velocity = mean_radial_velocity;
    result.exact_mean_radial_velocity = exact_mean_radial_velocity;
    result.normalized_mean_radial_velocity_residual = std::abs(
        mean_radial_velocity - exact_mean_radial_velocity
    ) / std::abs(exact_mean_radial_velocity);
    result.normalized_net_force_residual = norm(net_force) / net_force_scale;
    result.maximum_relative_radius_deviation
        = maximum_relative_radius_deviation;
    result.maximum_position_displacement = maximum_position_displacement;
    result.maximum_force_buffer_norm_after = maximum_force_buffer_norm_after;
    result.position_hash_before = position_hash_before;
    result.position_hash_after = cell_position_hash(target);
    result.state_hash_before = state_hash_before;
    result.state_hash_after = cell_state_hash(target);
    result.force_buffers_cleared = maximum_force_buffer_norm_after == 0.0;
    return result;
}

SphericalSurfaceTensionInstantaneousAudit
audit_spherical_surface_tension_instantaneous(
    ::cell& target,
    const double surface_tension,
    const double damping_per_area,
    const double directional_step_per_rms_edge
) {
    if(!std::isfinite(surface_tension) || surface_tension <= 0.0
       || !std::isfinite(damping_per_area) || damping_per_area <= 0.0
       || !std::isfinite(directional_step_per_rms_edge)
       || directional_step_per_rms_edge <= 0.0) {
        throw std::invalid_argument("spherical instantaneous audit configuration is invalid");
    }
    const auto revision = target.get_mesh_revision();
    static_cast<void>(refresh_surface_geometry(target, revision));
    const auto mesh = capture_surface_snapshot(target);
    const auto geometry = independent_surface_geometry(mesh, nullptr);
    const auto edge_scales = surface_edge_scales(mesh);
    const auto control_areas = barycentric_control_areas(mesh);
    if(mesh.vertices.empty()) {
        throw std::invalid_argument("spherical instantaneous audit requires vertices");
    }
    const double reference_radius = norm(mesh.vertices.front().position);
    if(!std::isfinite(reference_radius) || reference_radius <= 0.0) {
        throw std::runtime_error("spherical instantaneous audit radius is invalid");
    }
    std::unordered_map<std::uint64_t, std::size_t> edge_incidence;
    edge_incidence.reserve(3 * mesh.faces.size() / 2);
    double minimum_outward_alignment = std::numeric_limits<double>::infinity();
    double signed_volume = 0.0;
    bool all_face_origin_contributions_positive = true;
    for(const auto& current_face : mesh.faces) {
        for(std::size_t local_edge = 0; local_edge < 3; ++local_edge) {
            const auto first = current_face.vertex_indices[local_edge];
            const auto second = current_face.vertex_indices[(local_edge + 1) % 3];
            ++edge_incidence[undirected_edge_key(first, second)];
        }
        const auto& a = mesh.vertices.at(current_face.vertex_indices[0]).position;
        const auto& b = mesh.vertices.at(current_face.vertex_indices[1]).position;
        const auto& c = mesh.vertices.at(current_face.vertex_indices[2]).position;
        const auto oriented = cross(subtract(b, a), subtract(c, a));
        const auto face_centroid = scale(add(add(a, b), c), 1.0 / 3.0);
        const double alignment = dot(oriented, face_centroid)
            / (norm(oriented) * norm(face_centroid));
        const double face_signed_volume = dot(a, cross(b, c)) / 6.0;
        if(!std::isfinite(alignment) || !std::isfinite(face_signed_volume)) {
            throw std::runtime_error("spherical mesh orientation proxy is non-finite");
        }
        minimum_outward_alignment = std::min(
            minimum_outward_alignment,
            alignment
        );
        all_face_origin_contributions_positive
            = all_face_origin_contributions_positive && face_signed_volume > 0.0;
        signed_volume += face_signed_volume;
    }
    std::vector<std::size_t> valences(mesh.vertices.size(), 0);
    std::vector<std::vector<double>> incident_edge_lengths(mesh.vertices.size());
    bool closed_two_manifold = true;
    for(const auto& [key, incidence] : edge_incidence) {
        closed_two_manifold = closed_two_manifold && incidence == 2;
        const auto first = static_cast<std::size_t>(key >> 32U);
        const auto second = static_cast<std::size_t>(key & 0xffffffffULL);
        ++valences.at(first);
        ++valences.at(second);
        const double edge_length = norm(subtract(
            mesh.vertices.at(first).position,
            mesh.vertices.at(second).position
        ));
        incident_edge_lengths.at(first).push_back(edge_length);
        incident_edge_lengths.at(second).push_back(edge_length);
    }
    std::vector<bool> in_valence_five_closed_one_ring(
        mesh.vertices.size(),
        false
    );
    for(std::size_t index = 0; index < valences.size(); ++index) {
        in_valence_five_closed_one_ring[index] = valences[index] == 5;
    }
    for(const auto& [key, incidence] : edge_incidence) {
        static_cast<void>(incidence);
        const auto first = static_cast<std::size_t>(key >> 32U);
        const auto second = static_cast<std::size_t>(key & 0xffffffffULL);
        if(valences.at(first) == 5 || valences.at(second) == 5) {
            in_valence_five_closed_one_ring[first] = true;
            in_valence_five_closed_one_ring[second] = true;
        }
    }
    const auto euler_characteristic
        = static_cast<std::int64_t>(mesh.vertices.size())
        - static_cast<std::int64_t>(edge_incidence.size())
        + static_cast<std::int64_t>(mesh.faces.size());
    const bool positive_signed_volume = std::isfinite(signed_volume)
        && signed_volume > 0.0;
    const bool no_self_intersection_proxy_passed = closed_two_manifold
        && euler_characteristic == 2
        && minimum_outward_alignment > 0.0
        && positive_signed_volume
        && all_face_origin_contributions_positive;
    constexpr double symmetry_quantization = 1.0e-10;
    std::vector<std::size_t> symmetry_class_ids(mesh.vertices.size(), 0);
    std::unordered_map<std::string, std::size_t> symmetry_class_by_signature;
    std::size_t next_symmetry_class_id = 1;
    for(std::size_t index = 0; index < mesh.vertices.size(); ++index) {
        auto normalized_lengths = incident_edge_lengths.at(index);
        for(double& length : normalized_lengths) length /= edge_scales[0];
        std::sort(normalized_lengths.begin(), normalized_lengths.end());
        std::ostringstream signature;
        signature << valences.at(index) << ':'
                  << std::llround(
                        control_areas.at(index)
                        / (geometry.area / static_cast<double>(mesh.vertices.size()))
                        / symmetry_quantization
                     );
        for(const double length : normalized_lengths) {
            signature << ':' << std::llround(length / symmetry_quantization);
        }
        const auto [class_entry, inserted] = symmetry_class_by_signature.emplace(
            signature.str(),
            next_symmetry_class_id
        );
        if(inserted) ++next_symmetry_class_id;
        symmetry_class_ids[index] = class_entry->second;
    }
    std::vector<Vector3> direction;
    direction.reserve(mesh.vertices.size());
    double maximum_direction_norm = 0.0;
    double maximum_radius_deviation = 0.0;
    for(const auto& current_vertex : mesh.vertices) {
        const auto& position = current_vertex.position;
        const double radius = norm(position);
        if(!std::isfinite(radius) || radius <= 0.0) {
            throw std::runtime_error("spherical instantaneous audit vertex is invalid");
        }
        if(std::abs(radius - reference_radius)
           > 1.0e-12 * std::max(1.0, reference_radius)) {
            throw std::invalid_argument(
                "spherical instantaneous audit requires one projected radius"
            );
        }
        maximum_radius_deviation = std::max(
            maximum_radius_deviation,
            std::abs(radius - reference_radius)
        );
        const auto normal = scale(position, 1.0 / radius);
        const double amplitude = 0.25
            + 0.10 * position[0]
            + 0.07 * position[1]
            - 0.05 * position[2];
        const Vector3 tangent{
            -normal[2] * normal[0],
            -normal[2] * normal[1],
            1.0 - normal[2] * normal[2],
        };
        direction.push_back(add(
            scale(normal, amplitude),
            scale(tangent, 0.05)
        ));
        maximum_direction_norm = std::max(
            maximum_direction_norm,
            norm(direction.back())
        );
    }
    if(!std::isfinite(maximum_direction_norm) || maximum_direction_norm <= 0.0) {
        throw std::runtime_error("spherical instantaneous audit direction is invalid");
    }
    for(auto& value : direction) value = scale(value, 1.0 / maximum_direction_norm);

    const double epsilon = directional_step_per_rms_edge * edge_scales[0];
    const double registered_energy = surface_tension * geometry.area;
    const double energy_plus = surface_tension
        * surface_area_with_displacement(mesh, direction, epsilon);
    const double energy_minus = surface_tension
        * surface_area_with_displacement(mesh, direction, -epsilon);
    const double finite_difference = (energy_plus - energy_minus) / (2.0 * epsilon);

    for(const node& current_node : target.get_node_lst()) {
        if(!current_node.is_used()) continue;
        const Vector3 force{
            current_node.force().dx(),
            current_node.force().dy(),
            current_node.force().dz(),
        };
        if(norm(force) != 0.0) {
            throw std::logic_error("spherical instantaneous audit requires empty force buffers");
        }
    }

    double force_directional = 0.0;
    double legacy_cache = 0.0;
    std::vector<Vector3> assembled_forces;
    assembled_forces.reserve(mesh.vertices.size());
    try {
        target.apply_internal_forces(0.0);
        legacy_cache = target.get_surface_tension_energy();
        std::size_t used_index = 0;
        for(const node& current_node : target.get_node_lst()) {
            if(!current_node.is_used()) continue;
            if(used_index >= direction.size()) {
                throw std::runtime_error("force and snapshot vertex order mismatch");
            }
            const Vector3 force{
                current_node.force().dx(),
                current_node.force().dy(),
                current_node.force().dz(),
            };
            assembled_forces.push_back(force);
            force_directional -= dot(force, direction[used_index]);
            ++used_index;
        }
        if(used_index != direction.size()) {
            throw std::runtime_error("force and snapshot vertex count mismatch");
        }
    } catch(...) {
        static_cast<void>(reset_surface_forces(target, revision));
        throw;
    }
    static_cast<void>(reset_surface_forces(target, revision));

    bool force_buffers_cleared = true;
    for(const node& current_node : target.get_node_lst()) {
        if(!current_node.is_used()) continue;
        const Vector3 force{
            current_node.force().dx(),
            current_node.force().dy(),
            current_node.force().dz(),
        };
        force_buffers_cleared = force_buffers_cleared && norm(force) == 0.0;
    }
    const double denominator = std::max({
        std::abs(finite_difference),
        std::abs(force_directional),
        registered_energy,
        1.0e-30,
    });
    const double residual = std::abs(finite_difference - force_directional)
        / denominator;
    const double exact_normal_velocity = -2.0 * surface_tension
        / (damping_per_area * reference_radius);
    double normal_error_square_integral = 0.0;
    double tangential_square_integral = 0.0;
    double control_area_sum = 0.0;
    Vector3 net_force{};
    std::vector<SphericalVertexInstantaneousDiagnostic> vertex_diagnostics;
    vertex_diagnostics.reserve(assembled_forces.size());
    for(std::size_t index = 0; index < assembled_forces.size(); ++index) {
        const auto& position = mesh.vertices.at(index).position;
        const auto normal = scale(position, 1.0 / norm(position));
        const double control_area = control_areas.at(index);
        const auto velocity = scale(
            assembled_forces[index],
            1.0 / (damping_per_area * control_area)
        );
        const double normal_velocity = dot(velocity, normal);
        const auto tangential_velocity = subtract(
            velocity,
            scale(normal, normal_velocity)
        );
        const double normal_error = normal_velocity - exact_normal_velocity;
        vertex_diagnostics.push_back({
            index,
            valences.at(index),
            symmetry_class_ids.at(index),
            control_area / (
                geometry.area / static_cast<double>(mesh.vertices.size())
            ),
            control_area,
            normal_error,
            normal_error / std::abs(exact_normal_velocity),
            std::abs(normal_error) / std::abs(exact_normal_velocity),
            norm(tangential_velocity) / std::abs(exact_normal_velocity),
            in_valence_five_closed_one_ring.at(index),
        });
        normal_error_square_integral += control_area
            * normal_error * normal_error;
        tangential_square_integral += control_area
            * dot(tangential_velocity, tangential_velocity);
        control_area_sum += control_area;
        net_force = add(net_force, assembled_forces[index]);
    }
    const double normal_velocity_error = std::sqrt(
        normal_error_square_integral / control_area_sum
    ) / std::abs(exact_normal_velocity);
    const double tangential_velocity_error = std::sqrt(
        tangential_square_integral / control_area_sum
    ) / std::abs(exact_normal_velocity);
    const double net_force_residual = norm(net_force)
        / (surface_tension * geometry.area / reference_radius);
    if(!std::isfinite(legacy_cache)
       || !std::isfinite(finite_difference)
       || !std::isfinite(force_directional)
       || !std::isfinite(residual)
       || !std::isfinite(normal_velocity_error)
       || !std::isfinite(tangential_velocity_error)
       || !std::isfinite(net_force_residual)) {
        throw std::runtime_error("spherical instantaneous audit became non-finite");
    }
    struct DistributionAccumulator {
        std::size_t valence{};
        std::size_t count{};
        double normal_sum{};
        double normal_square_sum{};
        double normal_maximum{};
        double tangent_sum{};
        double tangent_square_sum{};
        double tangent_maximum{};
    };
    auto accumulate_vertex = [](DistributionAccumulator& distribution,
                                const SphericalVertexInstantaneousDiagnostic& vertex) {
        distribution.valence = vertex.valence;
        ++distribution.count;
        distribution.normal_sum += vertex.normal_absolute_relative_error;
        distribution.normal_square_sum += vertex.normal_absolute_relative_error
            * vertex.normal_absolute_relative_error;
        distribution.normal_maximum = std::max(
            distribution.normal_maximum,
            vertex.normal_absolute_relative_error
        );
        distribution.tangent_sum += vertex.tangential_relative_speed;
        distribution.tangent_square_sum += vertex.tangential_relative_speed
            * vertex.tangential_relative_speed;
        distribution.tangent_maximum = std::max(
            distribution.tangent_maximum,
            vertex.tangential_relative_speed
        );
    };
    std::map<std::size_t, DistributionAccumulator> by_valence;
    std::map<std::size_t, DistributionAccumulator> by_symmetry_class;
    for(const auto& vertex : vertex_diagnostics) {
        accumulate_vertex(by_valence[vertex.valence], vertex);
        accumulate_vertex(by_symmetry_class[vertex.symmetry_class_id], vertex);
    }
    std::vector<SphericalValenceDistributionDiagnostic> valence_distributions;
    valence_distributions.reserve(by_valence.size());
    for(const auto& [valence, distribution] : by_valence) {
        const double count = static_cast<double>(distribution.count);
        valence_distributions.push_back({
            valence,
            distribution.count,
            distribution.normal_sum / count,
            distribution.normal_maximum,
            std::sqrt(distribution.normal_square_sum / count),
            distribution.tangent_sum / count,
            distribution.tangent_maximum,
            std::sqrt(distribution.tangent_square_sum / count),
        });
    }
    std::vector<SphericalSymmetryClassDistributionDiagnostic>
        symmetry_class_distributions;
    symmetry_class_distributions.reserve(by_symmetry_class.size());
    std::size_t maximum_symmetry_class_size = 0;
    for(const auto& [class_id, distribution] : by_symmetry_class) {
        const double count = static_cast<double>(distribution.count);
        maximum_symmetry_class_size = std::max(
            maximum_symmetry_class_size,
            distribution.count
        );
        symmetry_class_distributions.push_back({
            class_id,
            distribution.valence,
            distribution.count,
            distribution.normal_sum / count,
            distribution.normal_maximum,
            std::sqrt(distribution.normal_square_sum / count),
            distribution.tangent_sum / count,
            distribution.tangent_maximum,
            std::sqrt(distribution.tangent_square_sum / count),
        });
    }
    SphericalSurfaceTensionInstantaneousAudit result;
    result.vertex_count = mesh.vertices.size();
    result.face_count = mesh.faces.size();
    result.rms_edge_length = edge_scales[0];
    result.maximum_edge_length = edge_scales[1];
    result.minimum_edge_length = edge_scales[2];
    result.maximum_radius_deviation = maximum_radius_deviation;
    result.minimum_triangle_quality = geometry.minimum_triangle_quality;
    result.minimum_outward_alignment = minimum_outward_alignment;
    result.minimum_face_to_mean_area_ratio = geometry.minimum_face_area
        / (geometry.area / static_cast<double>(mesh.faces.size()));
    result.euler_characteristic = euler_characteristic;
    result.closed_two_manifold = closed_two_manifold;
    result.positive_signed_volume = positive_signed_volume;
    result.all_face_origin_contributions_positive
        = all_face_origin_contributions_positive;
    result.no_self_intersection_proxy_passed
        = no_self_intersection_proxy_passed;
    result.registered_surface_energy = registered_energy;
    result.legacy_cache_energy = legacy_cache;
    result.finite_difference_directional_derivative = finite_difference;
    result.force_directional_derivative = force_directional;
    result.normalized_directional_derivative_residual = residual;
    result.exact_normal_velocity = exact_normal_velocity;
    result.normal_velocity_relative_l2_error = normal_velocity_error;
    result.tangential_velocity_relative_l2_error = tangential_velocity_error;
    result.normalized_net_force_residual = net_force_residual;
    result.force_buffers_cleared = force_buffers_cleared;
    result.vertex_diagnostics = std::move(vertex_diagnostics);
    result.maximum_symmetry_class_size = maximum_symmetry_class_size;
    result.valence_distributions = std::move(valence_distributions);
    result.symmetry_class_distributions = std::move(
        symmetry_class_distributions
    );
    return result;
}

SphericalDirectionalDerivativeRefinementAudit
evaluate_spherical_directional_derivative_refinement(
    const std::array<SphericalSurfaceTensionInstantaneousAudit, 4>& levels,
    const SphericalDirectionalDerivativeThresholds& thresholds
) {
    const std::array<double, 4> threshold_values{
        thresholds.maximum_finest_normalized_residual,
        thresholds.minimum_observed_order,
        thresholds.consistency_plateau_threshold,
        thresholds.maximum_legacy_cache_ratio_error,
    };
    if(!std::all_of(
            threshold_values.begin(),
            threshold_values.end(),
            [](const double value) { return std::isfinite(value) && value >= 0.0; }
        )) {
        throw std::invalid_argument("spherical directional thresholds are invalid");
    }

    SphericalDirectionalDerivativeRefinementAudit result;
    result.minimum_observed_order = std::numeric_limits<double>::infinity();
    result.mesh_scales_decreased = true;
    result.residuals_monotonic = true;
    result.legacy_cache_exclusion_passed = true;
    result.force_buffers_cleared = true;
    for(std::size_t level = 0; level < levels.size(); ++level) {
        const auto& current = levels[level];
        const double residual = current.normalized_directional_derivative_residual;
        if(!std::isfinite(current.rms_edge_length)
           || current.rms_edge_length <= 0.0
           || !std::isfinite(residual)
           || residual < 0.0
           || !std::isfinite(current.registered_surface_energy)
           || current.registered_surface_energy <= 0.0
           || !std::isfinite(current.legacy_cache_energy)) {
            throw std::invalid_argument("spherical directional level is invalid");
        }
        result.normalized_residuals[level] = residual;
        result.legacy_cache_exclusion_passed
            = result.legacy_cache_exclusion_passed
            && std::abs(
                current.legacy_cache_energy / current.registered_surface_energy - 0.5
            ) <= thresholds.maximum_legacy_cache_ratio_error;
        result.force_buffers_cleared
            = result.force_buffers_cleared && current.force_buffers_cleared;
        if(level == 0) continue;
        result.mesh_scales_decreased = result.mesh_scales_decreased
            && current.rms_edge_length < levels[level - 1].rms_edge_length;
        result.residuals_monotonic = result.residuals_monotonic
            && residual <= levels[level - 1]
                .normalized_directional_derivative_residual;
    }
    result.consistency_plateau = std::all_of(
        result.normalized_residuals.begin(),
        result.normalized_residuals.end(),
        [&](const double residual) {
            return residual <= thresholds.consistency_plateau_threshold;
        }
    );
    bool orders_passed = true;
    if(!result.consistency_plateau) {
        for(std::size_t pair = 0; pair < result.observed_orders.size(); ++pair) {
            const double coarse_error = result.normalized_residuals[pair];
            const double fine_error = result.normalized_residuals[pair + 1];
            const double mesh_ratio = levels[pair].rms_edge_length
                / levels[pair + 1].rms_edge_length;
            if(coarse_error <= 0.0 || fine_error <= 0.0 || mesh_ratio <= 1.0) {
                orders_passed = false;
                result.observed_orders[pair] = 0.0;
                continue;
            }
            result.observed_orders[pair] = std::log(coarse_error / fine_error)
                / std::log(mesh_ratio);
            result.minimum_observed_order = std::min(
                result.minimum_observed_order,
                result.observed_orders[pair]
            );
            orders_passed = orders_passed
                && std::isfinite(result.observed_orders[pair])
                && result.observed_orders[pair] >= thresholds.minimum_observed_order;
        }
    } else {
        result.minimum_observed_order = 0.0;
    }
    result.finest_residual_passed = result.normalized_residuals.back()
        <= thresholds.maximum_finest_normalized_residual;
    result.passed = result.mesh_scales_decreased
        && (result.consistency_plateau || result.residuals_monotonic)
        && orders_passed
        && result.finest_residual_passed
        && result.legacy_cache_exclusion_passed
        && result.force_buffers_cleared;
    return result;
}

SphericalInstantaneousVelocityRefinementAudit
evaluate_spherical_instantaneous_velocity_refinement(
    const std::array<SphericalSurfaceTensionInstantaneousAudit, 4>& levels,
    const SphericalInstantaneousVelocityThresholds& thresholds
) {
    const std::array<double, 5> threshold_values{
        thresholds.maximum_finest_normal_velocity_error,
        thresholds.maximum_finest_tangential_pollution,
        thresholds.minimum_observed_order,
        thresholds.roundoff_plateau_threshold,
        thresholds.maximum_normalized_net_force_residual,
    };
    if(!std::all_of(
            threshold_values.begin(),
            threshold_values.end(),
            [](const double value) { return std::isfinite(value) && value >= 0.0; }
        )) {
        throw std::invalid_argument("spherical velocity thresholds are invalid");
    }

    SphericalInstantaneousVelocityRefinementAudit result;
    bool mesh_scales_decreased = true;
    for(std::size_t level = 0; level < levels.size(); ++level) {
        const auto& current = levels[level];
        const std::array<double, 4> values{
            current.rms_edge_length,
            current.normal_velocity_relative_l2_error,
            current.tangential_velocity_relative_l2_error,
            current.normalized_net_force_residual,
        };
        if(!std::all_of(
                values.begin(),
                values.end(),
                [](const double value) { return std::isfinite(value) && value >= 0.0; }
            )
           || current.rms_edge_length <= 0.0) {
            throw std::invalid_argument("spherical velocity level is invalid");
        }
        result.normal_velocity_errors[level]
            = current.normal_velocity_relative_l2_error;
        result.tangential_pollution_errors[level]
            = current.tangential_velocity_relative_l2_error;
        result.normalized_net_force_residuals[level]
            = current.normalized_net_force_residual;
        if(level > 0) {
            mesh_scales_decreased = mesh_scales_decreased
                && current.rms_edge_length < levels[level - 1].rms_edge_length;
        }
    }

    struct MetricGate {
        std::array<double, 3> orders{};
        bool plateau{};
        bool monotonic{};
        bool passed{};
    };
    auto evaluate_metric = [&](const std::array<double, 4>& errors,
                               const double maximum_finest_error) {
        MetricGate metric;
        metric.plateau = std::all_of(
            errors.begin(),
            errors.end(),
            [&](const double error) {
                return error <= thresholds.roundoff_plateau_threshold;
            }
        );
        metric.monotonic = true;
        bool orders_passed = true;
        for(std::size_t pair = 0; pair < metric.orders.size(); ++pair) {
            metric.monotonic = metric.monotonic
                && errors[pair + 1] <= errors[pair];
            if(metric.plateau) continue;
            const double mesh_ratio = levels[pair].rms_edge_length
                / levels[pair + 1].rms_edge_length;
            if(errors[pair] <= 0.0 || errors[pair + 1] <= 0.0
               || mesh_ratio <= 1.0) {
                orders_passed = false;
                continue;
            }
            metric.orders[pair] = std::log(errors[pair] / errors[pair + 1])
                / std::log(mesh_ratio);
            orders_passed = orders_passed
                && std::isfinite(metric.orders[pair])
                && metric.orders[pair] >= thresholds.minimum_observed_order;
        }
        metric.passed = errors.back() <= maximum_finest_error
            && (metric.plateau || (metric.monotonic && orders_passed));
        return metric;
    };

    const auto normal = evaluate_metric(
        result.normal_velocity_errors,
        thresholds.maximum_finest_normal_velocity_error
    );
    const auto tangent = evaluate_metric(
        result.tangential_pollution_errors,
        thresholds.maximum_finest_tangential_pollution
    );
    result.normal_velocity_observed_orders = normal.orders;
    result.tangential_pollution_observed_orders = tangent.orders;
    result.normal_velocity_plateau = normal.plateau;
    result.tangential_pollution_plateau = tangent.plateau;
    result.normal_velocity_monotonic = normal.monotonic;
    result.tangential_pollution_monotonic = tangent.monotonic;
    result.normal_velocity_passed = normal.passed;
    result.tangential_pollution_passed = tangent.passed;
    result.net_force_passed = std::all_of(
        result.normalized_net_force_residuals.begin(),
        result.normalized_net_force_residuals.end(),
        [&](const double residual) {
            return residual <= thresholds.maximum_normalized_net_force_residual;
        }
    );
    result.passed = mesh_scales_decreased
        && result.normal_velocity_passed
        && result.tangential_pollution_passed
        && result.net_force_passed;
    return result;
}

SphericalMeshFamilyDiagnosticAudit evaluate_spherical_mesh_family_quality(
    const std::array<SphericalSurfaceTensionInstantaneousAudit, 4>& levels,
    const SphericalMeshFamilyDiagnosticThresholds& thresholds
) {
    const std::array<double, 4> threshold_values{
        thresholds.maximum_radius_deviation,
        thresholds.minimum_triangle_quality,
        thresholds.minimum_face_to_mean_area_ratio,
        thresholds.maximum_edge_length_ratio,
    };
    if(!std::all_of(
            threshold_values.begin(),
            threshold_values.end(),
            [](const double value) { return std::isfinite(value) && value >= 0.0; }
        )
       || thresholds.minimum_triangle_quality > 1.0
       || thresholds.minimum_face_to_mean_area_ratio > 1.0
       || thresholds.maximum_edge_length_ratio < 1.0) {
        throw std::invalid_argument("spherical mesh-family thresholds are invalid");
    }

    SphericalMeshFamilyDiagnosticAudit result;
    result.mesh_scales_decreased = true;
    result.radii_passed = true;
    result.topology_proxy_passed = true;
    result.outward_orientation_passed = true;
    result.shape_regularity_passed = true;
    for(std::size_t level = 0; level < levels.size(); ++level) {
        const auto& current = levels[level];
        const std::array<double, 7> values{
            current.rms_edge_length,
            current.minimum_edge_length,
            current.maximum_edge_length,
            current.maximum_radius_deviation,
            current.minimum_triangle_quality,
            current.minimum_outward_alignment,
            current.minimum_face_to_mean_area_ratio,
        };
        if(!std::all_of(
                values.begin(),
                values.end(),
                [](const double value) { return std::isfinite(value) && value >= 0.0; }
            )
           || current.rms_edge_length <= 0.0
           || current.minimum_edge_length <= 0.0) {
            throw std::invalid_argument("spherical mesh-family level is invalid");
        }
        result.rms_edge_lengths[level] = current.rms_edge_length;
        result.minimum_triangle_qualities[level] = current.minimum_triangle_quality;
        result.minimum_outward_alignments[level] = current.minimum_outward_alignment;
        result.minimum_face_to_mean_area_ratios[level]
            = current.minimum_face_to_mean_area_ratio;
        result.maximum_to_minimum_edge_ratios[level]
            = current.maximum_edge_length / current.minimum_edge_length;
        if(level > 0) {
            result.mesh_scales_decreased = result.mesh_scales_decreased
                && current.rms_edge_length < levels[level - 1].rms_edge_length;
        }
        result.radii_passed = result.radii_passed
            && current.maximum_radius_deviation
                <= thresholds.maximum_radius_deviation;
        result.topology_proxy_passed = result.topology_proxy_passed
            && current.closed_two_manifold
            && current.euler_characteristic == 2
            && current.positive_signed_volume
            && current.all_face_origin_contributions_positive
            && current.no_self_intersection_proxy_passed;
        result.outward_orientation_passed
            = result.outward_orientation_passed
            && current.minimum_outward_alignment > 0.0;
        result.shape_regularity_passed = result.shape_regularity_passed
            && current.minimum_triangle_quality
                >= thresholds.minimum_triangle_quality
            && current.minimum_face_to_mean_area_ratio
                >= thresholds.minimum_face_to_mean_area_ratio
            && result.maximum_to_minimum_edge_ratios[level]
                <= thresholds.maximum_edge_length_ratio;
    }
    result.passed = result.mesh_scales_decreased
        && result.radii_passed
        && result.topology_proxy_passed
        && result.outward_orientation_passed
        && result.shape_regularity_passed;
    return result;
}

SphericalNormalErrorEnergyRefinementAudit
evaluate_spherical_normal_error_energy_refinement(
    const std::array<SphericalSurfaceTensionInstantaneousAudit, 4>& levels
) {
    SphericalNormalErrorEnergyRefinementAudit result;
    result.mesh_scales_decreased = true;
    result.finite_nonnegative = true;
    result.partition_closed = true;

    auto accumulate = [](SphericalNormalErrorRegionDiagnostic& region,
                         const SphericalVertexInstantaneousDiagnostic& vertex,
                         const double exact_normal_speed) {
        const double error_energy = vertex.control_area
            * vertex.normal_velocity_error * vertex.normal_velocity_error;
        ++region.vertex_count;
        region.control_area += vertex.control_area;
        region.error_energy += error_energy;
        region.maximum_pointwise_relative_error = std::max(
            region.maximum_pointwise_relative_error,
            std::abs(vertex.normal_velocity_error) / exact_normal_speed
        );
    };

    for(std::size_t level = 0; level < levels.size(); ++level) {
        const auto& current = levels[level];
        auto& level_result = result.levels[level];
        const double exact_normal_speed = std::abs(current.exact_normal_velocity);
        if(!std::isfinite(current.rms_edge_length)
           || current.rms_edge_length <= 0.0
           || !std::isfinite(exact_normal_speed)
           || exact_normal_speed <= 0.0
           || current.vertex_diagnostics.size() != current.vertex_count) {
            throw std::invalid_argument("spherical normal-error level is invalid");
        }
        level_result.rms_edge_length = current.rms_edge_length;
        for(const auto& vertex : current.vertex_diagnostics) {
            const std::array<double, 3> values{
                vertex.control_area,
                vertex.normal_velocity_error,
                vertex.normal_absolute_relative_error,
            };
            if(!std::all_of(
                    values.begin(),
                    values.end(),
                    [](const double value) { return std::isfinite(value); }
                )
               || vertex.control_area <= 0.0
               || vertex.normal_absolute_relative_error < 0.0) {
                throw std::invalid_argument(
                    "spherical normal-error vertex is invalid"
                );
            }
            const double error_energy = vertex.control_area
                * vertex.normal_velocity_error * vertex.normal_velocity_error;
            level_result.total_control_area += vertex.control_area;
            level_result.total_error_energy += error_energy;
            if(vertex.valence == 5) {
                accumulate(
                    level_result.valence_five,
                    vertex,
                    exact_normal_speed
                );
            } else if(vertex.valence == 6) {
                accumulate(
                    level_result.valence_six,
                    vertex,
                    exact_normal_speed
                );
            }
            if(vertex.in_valence_five_closed_one_ring) {
                accumulate(
                    level_result.valence_five_closed_one_ring,
                    vertex,
                    exact_normal_speed
                );
            }
        }
        auto finalize = [&](SphericalNormalErrorRegionDiagnostic& region) {
            region.total_error_energy_fraction
                = level_result.total_error_energy > 0.0
                ? region.error_energy / level_result.total_error_energy
                : 0.0;
            region.area_weighted_relative_rms = region.control_area > 0.0
                ? std::sqrt(region.error_energy / region.control_area)
                    / exact_normal_speed
                : 0.0;
        };
        finalize(level_result.valence_five);
        finalize(level_result.valence_six);
        finalize(level_result.valence_five_closed_one_ring);
        level_result.partition_closure_residual = std::abs(
            level_result.total_error_energy
            - level_result.valence_five.error_energy
            - level_result.valence_six.error_energy
        );
        const std::array<double, 18> reported_values{
            level_result.total_control_area,
            level_result.total_error_energy,
            level_result.partition_closure_residual,
            level_result.valence_five.control_area,
            level_result.valence_five.error_energy,
            level_result.valence_five.total_error_energy_fraction,
            level_result.valence_five.area_weighted_relative_rms,
            level_result.valence_five.maximum_pointwise_relative_error,
            level_result.valence_six.control_area,
            level_result.valence_six.error_energy,
            level_result.valence_six.total_error_energy_fraction,
            level_result.valence_six.area_weighted_relative_rms,
            level_result.valence_six.maximum_pointwise_relative_error,
            level_result.valence_five_closed_one_ring.control_area,
            level_result.valence_five_closed_one_ring.error_energy,
            level_result.valence_five_closed_one_ring.total_error_energy_fraction,
            level_result.valence_five_closed_one_ring.area_weighted_relative_rms,
            level_result.valence_five_closed_one_ring
                .maximum_pointwise_relative_error,
        };
        level_result.finite_nonnegative = std::all_of(
            reported_values.begin(),
            reported_values.end(),
            [](const double value) {
                return std::isfinite(value) && value >= 0.0;
            }
        );
        level_result.partition_closed = level_result.partition_closure_residual
            <= 1.0e-12 * std::max(1.0, level_result.total_error_energy);
        result.finite_nonnegative = result.finite_nonnegative
            && level_result.finite_nonnegative;
        result.partition_closed = result.partition_closed
            && level_result.partition_closed;
        if(level > 0) {
            result.mesh_scales_decreased = result.mesh_scales_decreased
                && current.rms_edge_length < levels[level - 1].rms_edge_length;
        }
    }

    auto observed_orders = [&](auto energy_at) {
        std::array<double, 3> orders{};
        for(std::size_t pair = 0; pair < orders.size(); ++pair) {
            const double coarse = energy_at(result.levels[pair]);
            const double fine = energy_at(result.levels[pair + 1]);
            const double mesh_ratio = result.levels[pair].rms_edge_length
                / result.levels[pair + 1].rms_edge_length;
            if(coarse > 0.0 && fine > 0.0 && mesh_ratio > 1.0) {
                orders[pair] = std::log(coarse / fine) / std::log(mesh_ratio);
            }
        }
        return orders;
    };
    result.total_error_energy_observed_orders = observed_orders(
        [](const auto& level) { return level.total_error_energy; }
    );
    result.valence_five_error_energy_observed_orders = observed_orders(
        [](const auto& level) { return level.valence_five.error_energy; }
    );
    result.valence_six_error_energy_observed_orders = observed_orders(
        [](const auto& level) { return level.valence_six.error_energy; }
    );
    result.valence_five_closed_one_ring_observed_orders = observed_orders(
        [](const auto& level) {
            return level.valence_five_closed_one_ring.error_energy;
        }
    );
    return result;
}

SphericalSymmetryBreakingRefinementAudit
evaluate_quality_controlled_symmetry_breaking(
    const std::array<SphericalSurfaceTensionInstantaneousAudit, 4>& levels
) {
    SphericalSymmetryBreakingRefinementAudit result;
    result.passed = true;
    for(std::size_t level = 0; level < levels.size(); ++level) {
        const auto& current = levels[level];
        auto& level_result = result.levels[level];
        std::size_t represented_vertices = 0;
        std::size_t computed_maximum_class_size = 0;
        for(const auto& distribution : current.symmetry_class_distributions) {
            represented_vertices += distribution.vertex_count;
            computed_maximum_class_size = std::max(
                computed_maximum_class_size,
                distribution.vertex_count
            );
        }
        const bool class_partition_consistent
            = represented_vertices == current.vertex_count
            && computed_maximum_class_size
                == current.maximum_symmetry_class_size;
        level_result.vertex_count = current.vertex_count;
        level_result.symmetry_class_count
            = current.symmetry_class_distributions.size();
        level_result.maximum_symmetry_class_size
            = current.maximum_symmetry_class_size;
        level_result.minimum_required_class_count = current.vertex_count / 2;
        level_result.class_size_passed = class_partition_consistent
            && computed_maximum_class_size <= 2;
        level_result.class_count_passed
            = level_result.symmetry_class_count
                >= level_result.minimum_required_class_count;
        level_result.passed = current.vertex_count > 0
            && level_result.class_size_passed
            && level_result.class_count_passed;
        result.passed = result.passed && level_result.passed;
    }
    return result;
}

} // namespace prl::cell_engine
