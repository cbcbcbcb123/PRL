#include "prl/cell_engine/r1_remesh_robustness.hpp"

#include "prl_cell_engine/cell_surface_force.hpp"
#include "prl_cell_engine/cell_surface_snapshot.hpp"

#include "cell.hpp"
#include "edge.hpp"
#include "local_mesh_refiner.hpp"
#include "node.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <memory>
#include <stdexcept>
#include <unordered_set>
#include <utility>
#include <vector>

namespace prl::cell_engine {
namespace {

using Vector3 = std::array<double, 3>;

constexpr double frozen_time_step = 6.25e-4;
constexpr std::size_t frozen_step_count = 8;
constexpr std::size_t frozen_split_step = 2;
constexpr std::size_t frozen_merge_step = 3;
constexpr double frozen_damping_density = 10.0;

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

bool finite_vector(const Vector3& value) noexcept {
    return std::all_of(value.begin(), value.end(), [](const double component) {
        return std::isfinite(component);
    });
}

struct InitialFaceReference {
    std::array<core::VertexId, 3> vertex_ids{};
    Vector3 oriented_vector{};
};

struct IndependentSurfaceGeometry {
    double area{};
    double volume{};
    Vector3 centroid{};
    double minimum_face_area{std::numeric_limits<double>::infinity()};
    double minimum_triangle_quality{1.0};
    double minimum_oriented_face_alignment{1.0};
};

std::vector<InitialFaceReference> initial_face_references(
    const core::SurfaceMeshSnapshot& mesh
) {
    std::vector<InitialFaceReference> result;
    result.reserve(mesh.faces.size());
    for(const auto& current_face : mesh.faces) {
        const auto& a = mesh.vertices.at(current_face.vertex_indices[0]);
        const auto& b = mesh.vertices.at(current_face.vertex_indices[1]);
        const auto& c = mesh.vertices.at(current_face.vertex_indices[2]);
        const auto oriented = cross(
            subtract(b.position, a.position),
            subtract(c.position, a.position)
        );
        if(!std::isfinite(norm(oriented)) || norm(oriented) <= 0.0) {
            throw std::runtime_error("R1 initial surface contains a degenerate face");
        }
        result.push_back({
            {a.persistent_id, b.persistent_id, c.persistent_id},
            oriented,
        });
    }
    return result;
}

bool contains_vertex(
    const std::array<core::VertexId, 3>& ids,
    const core::VertexId id
) noexcept {
    return std::find(ids.begin(), ids.end(), id) != ids.end();
}

IndependentSurfaceGeometry independent_surface_geometry(
    const core::SurfaceMeshSnapshot& mesh,
    const std::vector<InitialFaceReference>& references,
    const std::unordered_set<core::VertexId>& initial_vertex_ids
) {
    if(mesh.vertices.empty() || mesh.faces.empty()) {
        throw std::runtime_error("R1 surface mesh is empty");
    }
    IndependentSurfaceGeometry result;
    double signed_six_volume = 0.0;
    for(const auto& current_face : mesh.faces) {
        const auto& a = mesh.vertices.at(current_face.vertex_indices[0]);
        const auto& b = mesh.vertices.at(current_face.vertex_indices[1]);
        const auto& c = mesh.vertices.at(current_face.vertex_indices[2]);
        if(!finite_vector(a.position)
           || !finite_vector(b.position)
           || !finite_vector(c.position)) {
            throw std::runtime_error("R1 surface contains a non-finite vertex");
        }
        const auto ab = subtract(b.position, a.position);
        const auto ac = subtract(c.position, a.position);
        const auto bc = subtract(c.position, b.position);
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
            throw std::runtime_error("R1 surface contains a degenerate face");
        }
        result.area += face_area;
        result.minimum_face_area = std::min(result.minimum_face_area, face_area);
        result.minimum_triangle_quality = std::min(
            result.minimum_triangle_quality,
            quality
        );
        for(std::size_t component = 0; component < 3; ++component) {
            result.centroid[component] += face_area
                * (a.position[component] + b.position[component]
                   + c.position[component]) / 3.0;
        }
        signed_six_volume += dot(a.position, cross(b.position, c.position));

        std::vector<core::VertexId> retained_ids;
        for(const auto* vertex : {&a, &b, &c}) {
            if(initial_vertex_ids.count(vertex->persistent_id) != 0) {
                retained_ids.push_back(vertex->persistent_id);
            }
        }
        double chosen_alignment = -std::numeric_limits<double>::infinity();
        double chosen_absolute_alignment = -1.0;
        for(const auto& reference : references) {
            const bool contains_retained = std::all_of(
                retained_ids.begin(),
                retained_ids.end(),
                [&](const core::VertexId id) {
                    return contains_vertex(reference.vertex_ids, id);
                }
            );
            if(!contains_retained) continue;
            const double alignment = dot(reference.oriented_vector, oriented)
                / (norm(reference.oriented_vector) * twice_area);
            if(std::abs(alignment) > chosen_absolute_alignment) {
                chosen_alignment = alignment;
                chosen_absolute_alignment = std::abs(alignment);
            }
        }
        if(!std::isfinite(chosen_alignment)) {
            throw std::runtime_error(
                "R1 current face has no initial orientation ancestor"
            );
        }
        result.minimum_oriented_face_alignment = std::min(
            result.minimum_oriented_face_alignment,
            chosen_alignment
        );
    }
    if(!std::isfinite(result.area) || result.area <= 0.0) {
        throw std::runtime_error("R1 surface area is invalid");
    }
    for(double& component : result.centroid) component /= result.area;
    result.volume = std::abs(signed_six_volume) / 6.0;
    if(!std::isfinite(result.volume)
       || result.volume <= 0.0
       || !finite_vector(result.centroid)) {
        throw std::runtime_error("R1 independent geometry is non-finite");
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

std::uint64_t material_state_hash(
    std::uint64_t result,
    const core::MyocardialCellMaterialState& material
) noexcept {
    result = hash_value(result, material.cell_id);
    result = hash_value(result, material.revision);
    for(const auto& point : material.points) {
        result = hash_value(result, point.material.material_point_id);
        result = hash_value(result, point.material.region);
        result = hash_bytes(
            result,
            point.material.fiber_direction.data(),
            sizeof(point.material.fiber_direction)
        );
        for(const double state : point.material.active_state) {
            result = hash_value(result, state);
        }
        result = hash_bytes(
            result,
            point.host_vertex_ids.data(),
            sizeof(point.host_vertex_ids)
        );
        result = hash_bytes(
            result,
            point.barycentric.data(),
            sizeof(point.barycentric)
        );
        result = hash_value(result, point.reference_weight);
    }
    return result;
}

std::uint64_t cell_state_hash(
    const ::cell& target,
    const core::MyocardialCellMaterialState& material
) noexcept {
    std::uint64_t result = 1469598103934665603ULL;
    result = hash_value(result, target.get_id());
    result = hash_value(result, target.get_mesh_revision());
    for(const node& current_node : target.get_node_lst()) {
        if(!current_node.is_used()) continue;
        result = hash_value(result, current_node.get_persistent_id());
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
    result = hash_bytes(result, caches.data(), sizeof(caches));
    return material_state_hash(result, material);
}

std::uint64_t configuration_hash(
    const R1RemeshRobustnessConfig& configuration
) noexcept {
    std::uint64_t result = 1469598103934665603ULL;
    result = hash_value(result, configuration.time_step);
    result = hash_value(result, configuration.step_count);
    result = hash_value(result, configuration.split_step);
    result = hash_value(result, configuration.merge_step);
    result = hash_value(result, configuration.qoi_contraction_unit_id);
    result = hash_value(result, configuration.damping.measure);
    result = hash_value(result, configuration.damping.coefficient);
    result = hash_value(result, configuration.collapse_mode);
    result = hash_value(result, configuration.survivor_persistent_id);
    const std::array<double, 12> thresholds{
        configuration.maximum_qoi_difference,
        configuration.maximum_remesh_defect,
        configuration.minimum_initial_active_energy,
        configuration.minimum_fiber_alignment,
        configuration.maximum_rebind_error,
        configuration.minimum_triangle_quality,
        configuration.minimum_face_area_ratio,
        configuration.maximum_normalized_cache_residual,
        configuration.maximum_normalized_centroid_drift,
        configuration.minimum_volume_ratio,
        configuration.maximum_volume_ratio,
        configuration.maximum_force_buffer_norm,
    };
    result = hash_bytes(result, thresholds.data(), sizeof(thresholds));
    return hash_value(
        result,
        configuration.maximum_normalized_positive_energy_residual
    );
}

double force_buffer_l2_norm(const ::cell& target) noexcept {
    double square_sum = 0.0;
    for(const node& current_node : target.get_node_lst()) {
        if(!current_node.is_used()) continue;
        square_sum += current_node.force().squared_norm();
    }
    return std::sqrt(square_sum);
}

double cache_residual(
    const ::cell& target,
    const IndependentSurfaceGeometry& geometry,
    const double initial_area,
    const double initial_volume,
    const double characteristic_length
) {
    const Vector3 cached_centroid{
        target.get_centroid().dx(),
        target.get_centroid().dy(),
        target.get_centroid().dz(),
    };
    return std::max({
        std::abs(target.get_area() - geometry.area) / initial_area,
        std::abs(target.get_volume() - geometry.volume) / initial_volume,
        norm(subtract(cached_centroid, geometry.centroid)) / characteristic_length,
    });
}

const core::ActiveContractionUnitState& qoi_state(
    const core::ActiveContractionEvaluation& active,
    const core::ActiveContractionUnitId qoi_id
) {
    const auto found = std::find_if(
        active.unit_states.begin(),
        active.unit_states.end(),
        [qoi_id](const core::ActiveContractionUnitState& state) {
            return state.contraction_unit_id == qoi_id;
        }
    );
    if(found == active.unit_states.end()) {
        throw std::invalid_argument("R1 QoI contraction unit is missing");
    }
    return *found;
}

bool same_initial_mesh(
    const core::SurfaceMeshSnapshot& left,
    const core::SurfaceMeshSnapshot& right
) noexcept {
    if(left.cell_id != right.cell_id
       || left.revision != right.revision
       || left.vertices.size() != right.vertices.size()
       || left.faces.size() != right.faces.size()) {
        return false;
    }
    for(std::size_t index = 0; index < left.vertices.size(); ++index) {
        if(left.vertices[index].persistent_id != right.vertices[index].persistent_id
           || left.vertices[index].position != right.vertices[index].position) {
            return false;
        }
    }
    for(std::size_t index = 0; index < left.faces.size(); ++index) {
        if(left.faces[index].vertex_indices != right.faces[index].vertex_indices) {
            return false;
        }
    }
    return true;
}

bool valid_frozen_configuration(
    const R1RemeshRobustnessConfig& configuration
) noexcept {
    const std::array<double, 15> finite_values{
        configuration.time_step,
        configuration.damping.coefficient,
        configuration.maximum_qoi_difference,
        configuration.maximum_remesh_defect,
        configuration.minimum_initial_active_energy,
        configuration.minimum_fiber_alignment,
        configuration.maximum_rebind_error,
        configuration.minimum_triangle_quality,
        configuration.minimum_face_area_ratio,
        configuration.maximum_normalized_cache_residual,
        configuration.maximum_normalized_centroid_drift,
        configuration.minimum_volume_ratio,
        configuration.maximum_volume_ratio,
        configuration.maximum_force_buffer_norm,
        configuration.maximum_normalized_positive_energy_residual,
    };
    return std::all_of(finite_values.begin(), finite_values.end(), [](const double value) {
               return std::isfinite(value);
           })
        && configuration.time_step == frozen_time_step
        && configuration.step_count == frozen_step_count
        && configuration.split_step == frozen_split_step
        && configuration.merge_step == frozen_merge_step
        && configuration.qoi_contraction_unit_id != 0
        && configuration.damping.measure
            == CellSurfaceDampingMeasure::barycentric_dual_area
        && configuration.damping.coefficient == frozen_damping_density
        && (configuration.collapse_mode == R1CollapseMode::midpoint
            || (configuration.collapse_mode
                    == R1CollapseMode::endpoint_survivor
                && configuration.survivor_persistent_id == 0))
        && configuration.maximum_qoi_difference == 2.0e-3
        && configuration.maximum_remesh_defect == 1.0e-12
        && configuration.minimum_initial_active_energy == 1.0e-2
        && configuration.minimum_fiber_alignment == 1.0 - 1.0e-12
        && configuration.maximum_rebind_error == 1.0e-12
        && configuration.minimum_triangle_quality == 0.05
        && configuration.minimum_face_area_ratio == 1.0e-4
        && configuration.maximum_normalized_cache_residual == 1.0e-12
        && configuration.maximum_normalized_centroid_drift == 1.0e-2
        && configuration.minimum_volume_ratio == 0.5
        && configuration.maximum_volume_ratio == 1.5
        && configuration.maximum_force_buffer_norm == 1.0e-12
        && configuration.maximum_normalized_positive_energy_residual == 5.0e-3;
}

bool finite_sample(const R1TrajectorySample& sample) noexcept {
    const std::array<double, 16> values{
        sample.time,
        sample.axis_length,
        sample.surface_area,
        sample.area_ratio,
        sample.volume,
        sample.volume_ratio,
        sample.normalized_surface_centroid_drift,
        sample.registered_active_energy,
        sample.active_control_work,
        sample.viscous_dissipation,
        sample.energy_balance_residual,
        sample.minimum_oriented_face_alignment,
        sample.minimum_triangle_quality,
        sample.minimum_face_area_ratio,
        sample.maximum_normalized_cache_residual,
        sample.force_buffer_l2_norm,
    };
    return finite_vector(sample.surface_centroid)
        && std::all_of(values.begin(), values.end(), [](const double value) {
            return std::isfinite(value);
        });
}

bool sample_passes_safety(
    const R1TrajectorySample& sample,
    const R1RemeshRobustnessConfig& configuration
) noexcept {
    return sample.finite
        && sample.minimum_oriented_face_alignment > 0.0
        && sample.minimum_triangle_quality >= configuration.minimum_triangle_quality
        && sample.minimum_face_area_ratio >= configuration.minimum_face_area_ratio
        && sample.maximum_normalized_cache_residual
            <= configuration.maximum_normalized_cache_residual
        && sample.normalized_surface_centroid_drift
            <= configuration.maximum_normalized_centroid_drift
        && sample.volume_ratio >= configuration.minimum_volume_ratio
        && sample.volume_ratio <= configuration.maximum_volume_ratio
        && sample.force_buffer_l2_norm <= configuration.maximum_force_buffer_norm;
}

} // namespace

const char* r1_remesh_robustness_status_name(
    const R1RemeshRobustnessStatus status
) noexcept {
    switch(status) {
        case R1RemeshRobustnessStatus::passed: return "passed";
        case R1RemeshRobustnessStatus::failed_invalid_configuration:
            return "failed_r1_setup";
        case R1RemeshRobustnessStatus::failed_fixed_trajectory:
            return "failed_r1_fixed_trajectory";
        case R1RemeshRobustnessStatus::failed_remesh_trajectory:
            return "failed_r1_remesh_trajectory";
        case R1RemeshRobustnessStatus::failed_qoi_difference:
            return "failed_r1_qoi_difference";
        case R1RemeshRobustnessStatus::failed_j1_gate:
            return "failed_r1_j1_gate";
        case R1RemeshRobustnessStatus::failed_geometry_cache_force_finite_gate:
            return "failed_r1_geometry_cache_force_finite_gate";
    }
    return "failed_invalid_configuration";
}

R1RemeshRobustnessAudit run_active_r1_remesh_robustness(
    ::cell& fixed_target,
    const core::MyocardialCellMaterialState& fixed_material,
    ::cell& remesh_target,
    const core::MyocardialCellMaterialState& remesh_material,
    const std::vector<core::ActiveContractionUnit>& units,
    const R1RemeshRobustnessConfig& configuration
) {
    R1RemeshRobustnessAudit result;
    result.configuration = configuration;
    result.configuration_hash = configuration_hash(configuration);
    if(!valid_frozen_configuration(configuration)
       || units.empty()
       || &fixed_target == &remesh_target) {
        result.failure_reason = "R1 frozen configuration or target pair is invalid";
        return result;
    }

    auto fail = [&](const R1RemeshRobustnessStatus status,
                    const std::size_t step,
                    const std::string& reason) {
        result.status = status;
        result.first_failure_step = step;
        result.failure_reason = reason;
        result.passed = false;
        return result;
    };

    try {
        static_cast<void>(refresh_surface_geometry(
            fixed_target,
            fixed_target.get_mesh_revision()
        ));
        static_cast<void>(refresh_surface_geometry(
            remesh_target,
            remesh_target.get_mesh_revision()
        ));
        const auto fixed_initial_mesh = capture_surface_snapshot(fixed_target);
        const auto remesh_initial_mesh = capture_surface_snapshot(remesh_target);
        if(!same_initial_mesh(fixed_initial_mesh, remesh_initial_mesh)
           || fixed_initial_mesh.revision != 0
           || fixed_material.cell_id != fixed_initial_mesh.cell_id
           || fixed_material.revision != fixed_initial_mesh.revision
           || remesh_material.cell_id != remesh_initial_mesh.cell_id
           || remesh_material.revision != remesh_initial_mesh.revision) {
            return fail(
                R1RemeshRobustnessStatus::failed_invalid_configuration,
                0,
                "R1 fixed/remesh initial mesh or material states differ"
            );
        }
        const auto fixed_references = initial_face_references(fixed_initial_mesh);
        const auto remesh_references = initial_face_references(remesh_initial_mesh);
        std::unordered_set<core::VertexId> fixed_initial_vertex_ids;
        std::unordered_set<core::VertexId> remesh_initial_vertex_ids;
        for(const auto& vertex : fixed_initial_mesh.vertices) {
            fixed_initial_vertex_ids.emplace(vertex.persistent_id);
        }
        for(const auto& vertex : remesh_initial_mesh.vertices) {
            remesh_initial_vertex_ids.emplace(vertex.persistent_id);
        }
        const auto fixed_initial_geometry = independent_surface_geometry(
            fixed_initial_mesh,
            fixed_references,
            fixed_initial_vertex_ids
        );
        const auto remesh_initial_geometry = independent_surface_geometry(
            remesh_initial_mesh,
            remesh_references,
            remesh_initial_vertex_ids
        );
        result.characteristic_length = std::cbrt(fixed_initial_geometry.volume);
        const auto initial_active = core::evaluate_active_contraction(
            fixed_initial_mesh,
            fixed_material,
            units
        );
        result.initial_axis_length = qoi_state(
            initial_active,
            configuration.qoi_contraction_unit_id
        ).length;
        result.initial_active_energy = initial_active.audit.total_energy;
        result.fixed_initial_state_hash = cell_state_hash(
            fixed_target,
            fixed_material
        );
        result.remesh_initial_state_hash = cell_state_hash(
            remesh_target,
            remesh_material
        );
        if(!std::isfinite(result.characteristic_length)
           || result.characteristic_length <= 0.0
           || !std::isfinite(result.initial_axis_length)
           || result.initial_axis_length <= 0.0
           || !std::isfinite(result.initial_active_energy)
           || result.initial_active_energy <= configuration.minimum_initial_active_energy
           || result.fixed_initial_state_hash != result.remesh_initial_state_hash) {
            return fail(
                R1RemeshRobustnessStatus::failed_invalid_configuration,
                0,
                "R1 initial scales, active energy, or state hashes are invalid"
            );
        }

        auto make_sample = [&](::cell& target,
                               const core::MyocardialCellMaterialState& material,
                               const std::size_t step,
                               const IndependentSurfaceGeometry& initial_geometry,
                               const std::vector<InitialFaceReference>& references,
                               const std::unordered_set<core::VertexId>& initial_vertex_ids,
                               const Vector3& initial_centroid,
                               const OwnedActiveCellOverdampedStepAudit* const motion) {
            const auto mesh = capture_surface_snapshot(target);
            const auto geometry = independent_surface_geometry(
                mesh,
                references,
                initial_vertex_ids
            );
            const auto active = core::evaluate_active_contraction(mesh, material, units);
            const auto& qoi = qoi_state(
                active,
                configuration.qoi_contraction_unit_id
            );
            const double control_work = motion == nullptr
                ? 0.0
                : motion->motion.active_control_energy;
            const double dissipation = motion == nullptr
                ? 0.0
                : motion->motion.viscous_dissipation;
            const double energy_residual = motion == nullptr
                ? 0.0
                : active.audit.total_energy
                    - motion->motion.active_energy_before
                    + dissipation - control_work;
            R1TrajectorySample sample{
                step,
                static_cast<double>(step) * configuration.time_step,
                mesh.revision,
                mesh.vertices.size(),
                mesh.faces.size(),
                qoi.length,
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
                cache_residual(
                    target,
                    geometry,
                    initial_geometry.area,
                    initial_geometry.volume,
                    result.characteristic_length
                ),
                force_buffer_l2_norm(target),
                false,
                cell_state_hash(target, material),
            };
            sample.finite = finite_sample(sample);
            return sample;
        };

        result.fixed_samples.push_back(make_sample(
            fixed_target,
            fixed_material,
            0,
            fixed_initial_geometry,
            fixed_references,
            fixed_initial_vertex_ids,
            fixed_initial_geometry.centroid,
            nullptr
        ));
        if(!sample_passes_safety(result.fixed_samples.back(), configuration)) {
            return fail(
                R1RemeshRobustnessStatus::failed_geometry_cache_force_finite_gate,
                0,
                "R1 fixed initial safety gate failed"
            );
        }
        double fixed_positive_energy_residual = 0.0;
        for(std::size_t step = 1; step <= configuration.step_count; ++step) {
            const auto motion = advance_owned_active_cell_overdamped_one_step(
                fixed_target,
                fixed_material,
                units,
                configuration.time_step,
                configuration.damping
            );
            result.fixed_samples.push_back(make_sample(
                fixed_target,
                fixed_material,
                step,
                fixed_initial_geometry,
                fixed_references,
                fixed_initial_vertex_ids,
                fixed_initial_geometry.centroid,
                &motion
            ));
            const auto& sample = result.fixed_samples.back();
            fixed_positive_energy_residual += std::max(
                0.0,
                sample.energy_balance_residual
            );
            if(!sample_passes_safety(sample, configuration)) {
                return fail(
                    R1RemeshRobustnessStatus::failed_geometry_cache_force_finite_gate,
                    step,
                    "R1 fixed step safety gate failed"
                );
            }
        }
        result.fixed_normalized_positive_energy_residual
            = fixed_positive_energy_residual / result.initial_active_energy;
        if(result.fixed_normalized_positive_energy_residual
           > configuration.maximum_normalized_positive_energy_residual) {
            return fail(
                R1RemeshRobustnessStatus::failed_fixed_trajectory,
                configuration.step_count,
                "R1 fixed active-energy ledger gate failed"
            );
        }

        auto sink = std::make_shared<core::MyocardialMaterialTransferSink>(
            configuration.maximum_rebind_error
        );
        sink->register_cell(remesh_initial_mesh, remesh_material.points);
        local_mesh_refiner refiner(0.1, 10.0, true, sink);
        auto remesh_cell = remesh_target.shared_from_this();
        edge_set edges_to_check;
        auto current_material = sink->cell_state(remesh_initial_mesh.cell_id);
        result.remesh_samples.push_back(make_sample(
            remesh_target,
            current_material,
            0,
            remesh_initial_geometry,
            remesh_references,
            remesh_initial_vertex_ids,
            remesh_initial_geometry.centroid,
            nullptr
        ));
        if(!sample_passes_safety(result.remesh_samples.back(), configuration)) {
            return fail(
                R1RemeshRobustnessStatus::failed_geometry_cache_force_finite_gate,
                0,
                "R1 remesh initial safety gate failed"
            );
        }

        double remesh_positive_energy_residual = 0.0;
        unsigned split_node_local_id = std::numeric_limits<unsigned>::max();
        for(std::size_t step = 1; step <= configuration.step_count; ++step) {
            if(step == configuration.merge_step) {
                const auto merge_edge_iterator = remesh_target.get_edge_set().find(
                    edge(0, split_node_local_id)
                );
                if(merge_edge_iterator == remesh_target.get_edge_set().end()) {
                    return fail(
                        R1RemeshRobustnessStatus::failed_remesh_trajectory,
                        step,
                        "R1 corresponding real merge edge is missing"
                    );
                }
                const auto collapse_operation = configuration.collapse_mode
                        == R1CollapseMode::endpoint_survivor
                    ? core::RemeshOperation::edge_collapse_survivor
                    : core::RemeshOperation::edge_merge;
                if(configuration.collapse_mode
                   == R1CollapseMode::endpoint_survivor) {
                    refiner.collapse_edge_to_survivor(
                        const_cast<edge&>(*merge_edge_iterator),
                        configuration.survivor_persistent_id,
                        remesh_cell,
                        edges_to_check
                    );
                } else {
                    refiner.merge_edge(
                        const_cast<edge&>(*merge_edge_iterator),
                        remesh_cell,
                        edges_to_check
                    );
                }
                current_material = sink->cell_state(remesh_initial_mesh.cell_id);
                const auto transfer = sink->last_audit(remesh_initial_mesh.cell_id);
                const auto defect = sink->last_remesh_energy_defect(
                    remesh_initial_mesh.cell_id
                );
                result.events.push_back({
                    result.events.size() + 1,
                    step,
                    collapse_operation,
                    defect.before_revision,
                    defect.after_revision,
                    transfer,
                    defect,
                });
                result.remesh_ledger = sink->remesh_energy_ledger(
                    remesh_initial_mesh.cell_id
                );
            }

            const auto motion = advance_owned_active_cell_overdamped_one_step(
                remesh_target,
                current_material,
                units,
                configuration.time_step,
                configuration.damping
            );

            if(step == configuration.split_step) {
                const auto before_split_mesh = capture_surface_snapshot(remesh_target);
                sink->begin_active_remesh_energy_ledger(before_split_mesh, units);
                const auto split_edge_iterator = remesh_target.get_edge_set().find(
                    edge(0, 1)
                );
                if(split_edge_iterator == remesh_target.get_edge_set().end()) {
                    return fail(
                        R1RemeshRobustnessStatus::failed_remesh_trajectory,
                        step,
                        "R1 registered real split edge is missing"
                    );
                }
                refiner.split_edge(
                    const_cast<edge&>(*split_edge_iterator),
                    remesh_cell,
                    edges_to_check
                );
                split_node_local_id = static_cast<unsigned>(
                    remesh_target.get_node_lst().size() - 1
                );
                current_material = sink->cell_state(remesh_initial_mesh.cell_id);
                const auto transfer = sink->last_audit(remesh_initial_mesh.cell_id);
                const auto defect = sink->last_remesh_energy_defect(
                    remesh_initial_mesh.cell_id
                );
                result.events.push_back({
                    result.events.size() + 1,
                    step,
                    core::RemeshOperation::edge_split,
                    defect.before_revision,
                    defect.after_revision,
                    transfer,
                    defect,
                });
                result.remesh_ledger = sink->remesh_energy_ledger(
                    remesh_initial_mesh.cell_id
                );
            }

            result.remesh_samples.push_back(make_sample(
                remesh_target,
                current_material,
                step,
                remesh_initial_geometry,
                remesh_references,
                remesh_initial_vertex_ids,
                remesh_initial_geometry.centroid,
                &motion
            ));
            const auto& sample = result.remesh_samples.back();
            remesh_positive_energy_residual += std::max(
                0.0,
                sample.energy_balance_residual
            );
            result.remesh_normalized_positive_energy_residual
                = remesh_positive_energy_residual / result.initial_active_energy;
            if(!sample_passes_safety(sample, configuration)) {
                return fail(
                    R1RemeshRobustnessStatus::failed_geometry_cache_force_finite_gate,
                    step,
                    "R1 remesh step safety gate failed"
                );
            }
        }
        result.remesh_normalized_positive_energy_residual
            = remesh_positive_energy_residual / result.initial_active_energy;
        if(result.remesh_normalized_positive_energy_residual
           > configuration.maximum_normalized_positive_energy_residual) {
            return fail(
                R1RemeshRobustnessStatus::failed_remesh_trajectory,
                configuration.step_count,
                "R1 remesh active-energy ledger gate failed"
            );
        }

        if(result.fixed_samples.size() != result.remesh_samples.size()) {
            return fail(
                R1RemeshRobustnessStatus::failed_qoi_difference,
                configuration.step_count,
                "R1 fixed/remesh sample counts differ"
            );
        }
        for(std::size_t index = 0; index < result.fixed_samples.size(); ++index) {
            const auto& fixed = result.fixed_samples[index];
            const auto& remesh = result.remesh_samples[index];
            const R1QoiComparisonSample comparison{
                fixed.step,
                std::abs(remesh.axis_length - fixed.axis_length)
                    / result.initial_axis_length,
                std::abs(remesh.area_ratio - fixed.area_ratio),
                std::abs(remesh.volume_ratio - fixed.volume_ratio),
                std::abs(
                    remesh.registered_active_energy
                    - fixed.registered_active_energy
                ) / result.initial_active_energy,
            };
            result.qoi_comparisons.push_back(comparison);
            result.maximum_axis_difference = std::max(
                result.maximum_axis_difference,
                comparison.normalized_axis_difference
            );
            result.maximum_area_ratio_difference = std::max(
                result.maximum_area_ratio_difference,
                comparison.area_ratio_difference
            );
            result.maximum_volume_ratio_difference = std::max(
                result.maximum_volume_ratio_difference,
                comparison.volume_ratio_difference
            );
            result.maximum_active_energy_difference = std::max(
                result.maximum_active_energy_difference,
                comparison.normalized_active_energy_difference
            );
        }
        result.qoi_gate_passed = result.maximum_axis_difference
                <= configuration.maximum_qoi_difference
            && result.maximum_area_ratio_difference
                <= configuration.maximum_qoi_difference
            && result.maximum_volume_ratio_difference
                <= configuration.maximum_qoi_difference
            && result.maximum_active_energy_difference
                <= configuration.maximum_qoi_difference;
        if(!result.qoi_gate_passed) {
            return fail(
                R1RemeshRobustnessStatus::failed_qoi_difference,
                configuration.step_count,
                "R1 fixed/remesh normalized QoI difference exceeded 2e-3"
            );
        }

        result.remesh_ledger = sink->remesh_energy_ledger(
            remesh_initial_mesh.cell_id
        );
        const auto& ledger = result.remesh_ledger;
        result.j1_gate_passed = ledger.coverage
                == core::RemeshEnergyCoverage::active_contraction_only
            && ledger.initial_stored_energy
                > configuration.minimum_initial_active_energy
            && std::abs(ledger.final_stored_energy - ledger.initial_stored_energy)
                <= configuration.maximum_remesh_defect
            && ledger.cumulative_absolute_algorithmic_energy_defect
                <= configuration.maximum_remesh_defect
            && ledger.minimum_step_fiber_alignment
                >= configuration.minimum_fiber_alignment
            && ledger.minimum_initial_fiber_alignment
                >= configuration.minimum_fiber_alignment
            && ledger.maximum_rebind_error <= configuration.maximum_rebind_error
            && ledger.event_count == 2
            && ledger.split_event_count == 1
            && ledger.swap_event_count == 0
            && ledger.merge_event_count == 1
            && std::abs(ledger.cumulative_declared_remesh_work)
                <= configuration.maximum_remesh_defect
            && ledger.energy_telescoping_residual
                <= configuration.maximum_remesh_defect
            && ledger.cumulative_absolute_inter_event_stored_energy_change
                <= configuration.maximum_remesh_defect
            && ledger.maximum_absolute_inter_event_stored_energy_change
                <= configuration.maximum_remesh_defect;
        if(!result.j1_gate_passed) {
            return fail(
                R1RemeshRobustnessStatus::failed_j1_gate,
                configuration.merge_step,
                "R1 real split/merge J1 ledger gate failed"
            );
        }

        result.safety_gate_passed = std::all_of(
            result.fixed_samples.begin(),
            result.fixed_samples.end(),
            [&](const R1TrajectorySample& sample) {
                return sample_passes_safety(sample, configuration);
            }
        ) && std::all_of(
            result.remesh_samples.begin(),
            result.remesh_samples.end(),
            [&](const R1TrajectorySample& sample) {
                return sample_passes_safety(sample, configuration);
            }
        );
        if(!result.safety_gate_passed) {
            return fail(
                R1RemeshRobustnessStatus::failed_geometry_cache_force_finite_gate,
                configuration.step_count,
                "R1 aggregate safety gate failed"
            );
        }
        result.status = R1RemeshRobustnessStatus::passed;
        result.passed = true;
        return result;
    } catch(const std::exception& error) {
        const auto status = result.fixed_samples.size()
                < configuration.step_count + 1
            ? R1RemeshRobustnessStatus::failed_fixed_trajectory
            : R1RemeshRobustnessStatus::failed_remesh_trajectory;
        const auto step = status == R1RemeshRobustnessStatus::failed_fixed_trajectory
            ? result.fixed_samples.size()
            : result.remesh_samples.size();
        return fail(status, step, error.what());
    }
}

} // namespace prl::cell_engine
