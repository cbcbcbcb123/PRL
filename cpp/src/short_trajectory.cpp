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

} // namespace prl::cell_engine
