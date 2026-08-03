#pragma once

#include "prl/cell_engine/active_overdamped_step.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <vector>

class cell;

namespace prl::cell_engine {

enum class ShortTrajectoryStatus : std::uint8_t {
    passed,
    failed_invalid_configuration,
    failed_non_finite_state,
    failed_degenerate_or_flipped_surface,
    failed_penetration_limit,
    failed_energy_gate,
    failed_refinement_gate,
    failed_step_exception,
};

[[nodiscard]] const char* short_trajectory_status_name(
    ShortTrajectoryStatus status
) noexcept;

struct ActiveShortTrajectoryConfig {
    double time_step{};
    std::size_t step_count{};
    core::ActiveContractionUnitId qoi_contraction_unit_id{};
    CellSurfaceDampingLaw damping{};
};

struct ShortTrajectoryFailure {
    ShortTrajectoryStatus status{ShortTrajectoryStatus::failed_step_exception};
    std::size_t first_failure_step{};
    double time_before_failure{};
    std::string reason{};
    std::uint64_t configuration_hash{};
    std::uint64_t state_hash_before{};
    std::uint64_t state_hash_after{};
    bool atomic_state_preserved{};
};

struct TrajectoryVertexPosition {
    core::VertexId vertex_id{};
    std::array<double, 3> position{};
};

struct ActiveShortTrajectorySample {
    std::size_t step{};
    double time{};
    double axis_length{};
    double contraction{};
    double surface_area{};
    double area_ratio{};
    double volume{};
    double volume_ratio{};
    std::array<double, 3> surface_centroid{};
    double normalized_surface_centroid_drift{};
    double registered_active_energy{};
    double active_control_work{};
    double viscous_dissipation{};
    double energy_balance_residual{};
    double minimum_oriented_face_alignment{};
    double minimum_triangle_quality{};
    double minimum_face_area_ratio{};
    double maximum_normalized_cache_residual{};
    std::uint64_t state_hash{};
};

struct ActiveShortTrajectoryAudit {
    ShortTrajectoryStatus status{ShortTrajectoryStatus::failed_step_exception};
    ActiveShortTrajectoryConfig configuration{};
    double characteristic_length{};
    double initial_axis_length{};
    double initial_registered_active_energy{};
    double cumulative_positive_energy_balance_residual{};
    double minimum_oriented_face_alignment{1.0};
    double minimum_triangle_quality{1.0};
    double minimum_face_area_ratio{1.0};
    double maximum_normalized_cache_residual{};
    std::vector<ActiveShortTrajectorySample> samples{};
    std::vector<TrajectoryVertexPosition> final_positions{};
    std::optional<ShortTrajectoryFailure> failure{};
};

struct ActiveTimeRefinementThresholds {
    double maximum_medium_fine_normalized_error{};
    double minimum_observed_order{};
    double roundoff_plateau_threshold{};
    double maximum_coarse_normalized_positive_energy_residual{};
    double minimum_energy_residual_reduction{};
};

struct SelfConvergenceAudit {
    double coarse_medium_normalized_error{};
    double medium_fine_normalized_error{};
    double observed_order{};
    bool roundoff_plateau{};
    bool monotonic{};
    bool fine_error_passed{};
    bool order_passed{};
    bool passed{};
};

struct ActiveTimeRefinementGateAudit {
    SelfConvergenceAudit state{};
    SelfConvergenceAudit axis_length{};
    SelfConvergenceAudit contraction{};
    SelfConvergenceAudit area_ratio{};
    SelfConvergenceAudit volume_ratio{};
    SelfConvergenceAudit registered_active_energy{};
    double coarse_normalized_positive_energy_residual{};
    double medium_normalized_positive_energy_residual{};
    double fine_normalized_positive_energy_residual{};
    bool energy_residual_passed{};
    bool passed{};
};

struct SurfaceTensionShortTrajectoryConfig {
    double time_step{};
    std::size_t step_count{};
    double surface_tension{};
    CellSurfaceDampingLaw damping{};
};

struct SurfaceTensionShortTrajectorySample {
    std::size_t step{};
    double time{};
    double surface_area{};
    double area_ratio{};
    double volume{};
    double volume_ratio{};
    std::array<double, 3> surface_centroid{};
    double normalized_surface_centroid_drift{};
    double registered_surface_energy{};
    double energy_ratio{};
    double viscous_dissipation{};
    double energy_balance_residual{};
    double minimum_oriented_face_alignment{};
    double minimum_triangle_quality{};
    double minimum_face_area_ratio{};
    double maximum_normalized_cache_residual{};
};

struct SurfaceTensionShortTrajectoryAudit {
    ShortTrajectoryStatus status{ShortTrajectoryStatus::failed_step_exception};
    SurfaceTensionShortTrajectoryConfig configuration{};
    double characteristic_length{};
    double initial_registered_surface_energy{};
    double cumulative_positive_energy_balance_residual{};
    double normalized_positive_energy_balance_residual{};
    double minimum_oriented_face_alignment{1.0};
    double minimum_triangle_quality{1.0};
    double minimum_face_area_ratio{1.0};
    double maximum_normalized_cache_residual{};
    std::vector<SurfaceTensionShortTrajectorySample> samples{};
    std::optional<ShortTrajectoryFailure> failure{};
};

struct SurfaceTensionSpatialRefinementThresholds {
    double maximum_base_fine_normalized_error{};
    double minimum_observed_order{};
    double roundoff_plateau_threshold{};
    double maximum_normalized_positive_energy_residual{};
    double minimum_triangle_quality{};
    double maximum_normalized_cache_residual{};
};

struct SurfaceTensionSpatialRefinementGateAudit {
    SelfConvergenceAudit area_ratio{};
    SelfConvergenceAudit volume_ratio{};
    SelfConvergenceAudit registered_energy_ratio{};
    SelfConvergenceAudit normalized_surface_centroid_drift{};
    double minimum_oriented_face_alignment{};
    double minimum_triangle_quality{};
    double minimum_face_area_ratio{};
    double maximum_normalized_cache_residual{};
    bool energy_coverage_passed{};
    bool surface_quality_passed{};
    bool cache_consistency_passed{};
    bool passed{};
};

struct SphericalVertexInstantaneousDiagnostic {
    std::size_t vertex_index{};
    std::size_t valence{};
    std::size_t symmetry_class_id{};
    double control_area_ratio{};
    double normal_signed_relative_error{};
    double normal_absolute_relative_error{};
    double tangential_relative_speed{};
};

struct SphericalValenceDistributionDiagnostic {
    std::size_t valence{};
    std::size_t vertex_count{};
    double normal_absolute_error_mean{};
    double normal_absolute_error_maximum{};
    double normal_absolute_error_rms{};
    double tangential_speed_mean{};
    double tangential_speed_maximum{};
    double tangential_speed_rms{};
};

struct SphericalSymmetryClassDistributionDiagnostic {
    std::size_t symmetry_class_id{};
    std::size_t valence{};
    std::size_t vertex_count{};
    double normal_absolute_error_mean{};
    double normal_absolute_error_maximum{};
    double normal_absolute_error_rms{};
    double tangential_speed_mean{};
    double tangential_speed_maximum{};
    double tangential_speed_rms{};
};

struct SphericalSurfaceTensionInstantaneousAudit {
    std::size_t vertex_count{};
    std::size_t face_count{};
    double rms_edge_length{};
    double maximum_edge_length{};
    double minimum_edge_length{};
    double maximum_radius_deviation{};
    double minimum_triangle_quality{};
    double minimum_outward_alignment{};
    double minimum_face_to_mean_area_ratio{};
    std::int64_t euler_characteristic{};
    bool closed_two_manifold{};
    bool positive_signed_volume{};
    bool all_face_origin_contributions_positive{};
    bool no_self_intersection_proxy_passed{};
    double registered_surface_energy{};
    double legacy_cache_energy{};
    double finite_difference_directional_derivative{};
    double force_directional_derivative{};
    double normalized_directional_derivative_residual{};
    double normal_velocity_relative_l2_error{};
    double tangential_velocity_relative_l2_error{};
    double normalized_net_force_residual{};
    bool force_buffers_cleared{};
    std::vector<SphericalVertexInstantaneousDiagnostic> vertex_diagnostics{};
    std::size_t maximum_symmetry_class_size{};
    std::vector<SphericalValenceDistributionDiagnostic> valence_distributions{};
    std::vector<SphericalSymmetryClassDistributionDiagnostic>
        symmetry_class_distributions{};
};

struct SphericalDirectionalDerivativeThresholds {
    double maximum_finest_normalized_residual{};
    double minimum_observed_order{};
    double consistency_plateau_threshold{};
    double maximum_legacy_cache_ratio_error{};
};

struct SphericalDirectionalDerivativeRefinementAudit {
    std::array<double, 4> normalized_residuals{};
    std::array<double, 3> observed_orders{};
    double minimum_observed_order{};
    bool consistency_plateau{};
    bool mesh_scales_decreased{};
    bool residuals_monotonic{};
    bool finest_residual_passed{};
    bool legacy_cache_exclusion_passed{};
    bool force_buffers_cleared{};
    bool passed{};
};

struct SphericalInstantaneousVelocityThresholds {
    double maximum_finest_normal_velocity_error{};
    double maximum_finest_tangential_pollution{};
    double minimum_observed_order{};
    double roundoff_plateau_threshold{};
    double maximum_normalized_net_force_residual{};
};

struct SphericalInstantaneousVelocityRefinementAudit {
    std::array<double, 4> normal_velocity_errors{};
    std::array<double, 4> tangential_pollution_errors{};
    std::array<double, 4> normalized_net_force_residuals{};
    std::array<double, 3> normal_velocity_observed_orders{};
    std::array<double, 3> tangential_pollution_observed_orders{};
    bool normal_velocity_plateau{};
    bool tangential_pollution_plateau{};
    bool normal_velocity_monotonic{};
    bool tangential_pollution_monotonic{};
    bool normal_velocity_passed{};
    bool tangential_pollution_passed{};
    bool net_force_passed{};
    bool passed{};
};

struct SphericalMeshFamilyDiagnosticThresholds {
    double maximum_radius_deviation{};
    double minimum_triangle_quality{};
    double minimum_face_to_mean_area_ratio{};
    double maximum_edge_length_ratio{};
};

struct SphericalMeshFamilyDiagnosticAudit {
    std::array<double, 4> rms_edge_lengths{};
    std::array<double, 4> minimum_triangle_qualities{};
    std::array<double, 4> minimum_outward_alignments{};
    std::array<double, 4> minimum_face_to_mean_area_ratios{};
    std::array<double, 4> maximum_to_minimum_edge_ratios{};
    bool mesh_scales_decreased{};
    bool radii_passed{};
    bool topology_proxy_passed{};
    bool outward_orientation_passed{};
    bool shape_regularity_passed{};
    bool passed{};
};

/** Run a fixed-topology, active-only trajectory with no retry or step adaptation. */
[[nodiscard]] ActiveShortTrajectoryAudit run_active_fixed_topology_short_trajectory(
    ::cell& target,
    const core::MyocardialCellMaterialState& material,
    const std::vector<core::ActiveContractionUnit>& units,
    const ActiveShortTrajectoryConfig& configuration
);

[[nodiscard]] ActiveTimeRefinementGateAudit evaluate_active_time_refinement(
    const ActiveShortTrajectoryAudit& coarse,
    const ActiveShortTrajectoryAudit& medium,
    const ActiveShortTrajectoryAudit& fine,
    const ActiveTimeRefinementThresholds& thresholds
);

[[nodiscard]] SurfaceTensionShortTrajectoryAudit
run_surface_tension_fixed_topology_short_trajectory(
    ::cell& target,
    const SurfaceTensionShortTrajectoryConfig& configuration
);

[[nodiscard]] SurfaceTensionSpatialRefinementGateAudit
evaluate_surface_tension_spatial_refinement(
    const SurfaceTensionShortTrajectoryAudit& coarse,
    const SurfaceTensionShortTrajectoryAudit& base,
    const SurfaceTensionShortTrajectoryAudit& fine,
    const SurfaceTensionSpatialRefinementThresholds& thresholds
);

/** Audit the real surface-tension force against the registered gamma*A owner. */
[[nodiscard]] SphericalSurfaceTensionInstantaneousAudit
audit_spherical_surface_tension_instantaneous(
    ::cell& target,
    double surface_tension,
    double damping_per_area,
    double directional_step_per_rms_edge
);

[[nodiscard]] SphericalDirectionalDerivativeRefinementAudit
evaluate_spherical_directional_derivative_refinement(
    const std::array<SphericalSurfaceTensionInstantaneousAudit, 4>& levels,
    const SphericalDirectionalDerivativeThresholds& thresholds
);

[[nodiscard]] SphericalInstantaneousVelocityRefinementAudit
evaluate_spherical_instantaneous_velocity_refinement(
    const std::array<SphericalSurfaceTensionInstantaneousAudit, 4>& levels,
    const SphericalInstantaneousVelocityThresholds& thresholds
);

[[nodiscard]] SphericalMeshFamilyDiagnosticAudit
evaluate_spherical_mesh_family_quality(
    const std::array<SphericalSurfaceTensionInstantaneousAudit, 4>& levels,
    const SphericalMeshFamilyDiagnosticThresholds& thresholds
);

} // namespace prl::cell_engine
