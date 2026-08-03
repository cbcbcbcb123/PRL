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

std::array<double, 2> surface_edge_scales(
    const core::SurfaceMeshSnapshot& mesh
) {
    std::unordered_set<std::uint64_t> edges;
    edges.reserve(3 * mesh.faces.size() / 2);
    double squared_length_sum = 0.0;
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
            maximum_length = std::max(maximum_length, length);
        }
    }
    if(edges.empty() || !std::isfinite(squared_length_sum)) {
        throw std::runtime_error("surface edge scale requires a finite mesh");
    }
    return {
        std::sqrt(squared_length_sum / static_cast<double>(edges.size())),
        maximum_length,
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
    std::vector<Vector3> direction;
    direction.reserve(mesh.vertices.size());
    double maximum_direction_norm = 0.0;
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
    return {
        mesh.vertices.size(),
        mesh.faces.size(),
        edge_scales[0],
        edge_scales[1],
        registered_energy,
        legacy_cache,
        finite_difference,
        force_directional,
        residual,
        normal_velocity_error,
        tangential_velocity_error,
        net_force_residual,
        force_buffers_cleared,
    };
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

} // namespace prl::cell_engine
