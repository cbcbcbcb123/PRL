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

struct FamilyCSmoothSphereTrajectoryConfig {
    double time_step{};
    std::size_t step_count{};
    double surface_tension{};
    CellSurfaceDampingLaw damping{};
    double reference_radius{};
};

struct FamilyCSmoothSphereTrajectorySample {
    SurfaceTensionShortTrajectorySample global{};
    double exact_radius{};
    double control_area_mean_radius{};
    double control_area_mean_radius_ratio{};
    double maximum_valence_five_excursion_error{};
    double rms_valence_five_radial_error{};
    double maximum_closed_one_ring_excursion_error{};
    double rms_closed_one_ring_radial_error{};
    double maximum_valence_five_error_over_initial_h{};
    double maximum_closed_one_ring_error_over_initial_h{};
    double maximum_closed_one_ring_edge_scaling_error{};
    double local_minimum_triangle_quality{};
    double local_minimum_triangle_quality_ratio{};
    double valence_five_normal_error_energy_fraction{};
    double valence_five_normal_error_relative_rms{};
    double valence_five_normal_error_pointwise_maximum{};
    double closed_one_ring_normal_error_energy_fraction{};
    double closed_one_ring_normal_error_relative_rms{};
    double closed_one_ring_normal_error_pointwise_maximum{};
    bool force_buffers_cleared{};
};

struct FamilyCSmoothSphereTrajectoryAudit {
    ShortTrajectoryStatus status{ShortTrajectoryStatus::failed_step_exception};
    FamilyCSmoothSphereTrajectoryConfig configuration{};
    double initial_rms_edge_length{};
    double initial_registered_surface_energy{};
    double initial_local_minimum_triangle_quality{};
    std::size_t valence_five_vertex_count{};
    std::size_t closed_one_ring_vertex_count{};
    std::size_t closed_one_ring_edge_count{};
    std::size_t closed_one_ring_incident_face_count{};
    double cumulative_positive_energy_balance_residual{};
    double normalized_positive_energy_balance_residual{};
    double minimum_oriented_face_alignment{1.0};
    double minimum_triangle_quality{1.0};
    double minimum_face_area_ratio{1.0};
    double maximum_normalized_cache_residual{};
    double maximum_normalized_centroid_drift{};
    std::vector<FamilyCSmoothSphereTrajectorySample> samples{};
    std::optional<ShortTrajectoryFailure> failure{};
};

struct FamilyCSmoothSphereGateThresholds {
    double maximum_finest_excursion_normalized_error{};
    double minimum_observed_order{};
    double roundoff_plateau_threshold{};
    double maximum_time_pollution_fraction{};
    double minimum_triangle_quality{};
    double minimum_face_area_ratio{};
    double maximum_normalized_cache_residual{};
    double maximum_normalized_centroid_drift{};
    double maximum_normalized_positive_energy_residual{};
    double maximum_local_excursion_normalized_error{};
    double maximum_local_edge_scaling_error{};
    double maximum_local_radial_error_over_initial_h{};
    double minimum_local_triangle_quality_ratio{};
};

struct FamilyCSmoothSphereQoiGateAudit {
    double exact_final_value{};
    double exact_excursion{};
    std::array<double, 4> responses{};
    std::array<double, 4> analytic_excursions{};
    std::array<double, 4> excursion_normalized_analytic_errors{};
    std::array<double, 3> analytic_observed_orders{};
    std::array<double, 3> adjacent_difference_excursions{};
    std::array<double, 3> excursion_normalized_adjacent_differences{};
    std::array<double, 2> generalized_self_convergence_orders{};
    bool analytic_roundoff_plateau{};
    bool analytic_errors_monotonic{};
    bool analytic_orders_passed{};
    bool finest_error_passed{};
    bool self_convergence_roundoff_plateau{};
    bool self_convergence_monotonic{};
    bool self_convergence_orders_passed{};
    bool passed{};
};

struct FamilyCSmoothSphereTimePollutionQoiAudit {
    double coarse_time_step_response{};
    double half_time_step_response{};
    double exact_final_value{};
    double exact_excursion{};
    double absolute_time_difference{};
    double excursion_normalized_time_difference{};
    double absolute_space_proxy{};
    double excursion_normalized_space_proxy{};
    bool roundoff_plateau{};
    bool passed{};
};

struct FamilyCSmoothSphereGateAudit {
    std::array<double, 4> rms_edge_lengths{};
    std::array<FamilyCSmoothSphereQoiGateAudit, 4> qois{};
    std::array<FamilyCSmoothSphereTimePollutionQoiAudit, 4> time_pollution{};
    double minimum_oriented_face_alignment{1.0};
    double minimum_triangle_quality{1.0};
    double minimum_face_area_ratio{1.0};
    double maximum_normalized_cache_residual{};
    double maximum_normalized_centroid_drift{};
    double maximum_normalized_positive_energy_residual{};
    double maximum_valence_five_excursion_error{};
    double maximum_closed_one_ring_excursion_error{};
    double maximum_valence_five_error_over_initial_h{};
    double maximum_closed_one_ring_error_over_initial_h{};
    double maximum_closed_one_ring_edge_scaling_error{};
    double minimum_local_triangle_quality_ratio{1.0};
    bool trajectories_passed{};
    bool mesh_scales_decreased{};
    bool analytic_qois_passed{};
    bool self_convergence_passed{};
    bool time_pollution_passed{};
    bool global_geometry_passed{};
    bool energy_coverage_passed{};
    bool local_risk_bounds_passed{};
    bool force_buffers_cleared{};
    bool passed{};
};

struct MeanRadiusTimeFloorThresholds {
    double minimum_time_order{};
    double maximum_time_order{};
    double common_raw_roundoff_plateau{};
    double maximum_richardson_error{};
    double maximum_cross_mesh_richardson_difference{};
    double minimum_triangle_quality{};
    double minimum_face_area_ratio{};
    double maximum_normalized_cache_residual{};
    double maximum_normalized_centroid_drift{};
    double maximum_normalized_positive_energy_residual{};
    double maximum_local_excursion_normalized_error{};
    double maximum_local_edge_scaling_error{};
    double maximum_local_radial_error_over_initial_h{};
    double minimum_local_triangle_quality_ratio{};
};

struct MeanRadiusTimeFloorLevelAudit {
    double initial_rms_edge_length{};
    std::array<double, 4> time_steps{};
    std::array<std::size_t, 4> step_counts{};
    std::array<double, 4> mean_radius_responses{};
    std::array<double, 4> final_area_ratios{};
    std::array<double, 4> final_volume_ratios{};
    std::array<double, 4> final_registered_energy_ratios{};
    std::array<double, 3> adjacent_time_differences{};
    std::array<double, 2> observed_time_orders{};
    double exact_mean_radius_response{};
    double richardson_response{};
    double richardson_error{};
    double minimum_oriented_face_alignment{1.0};
    double minimum_triangle_quality{1.0};
    double minimum_face_area_ratio{1.0};
    double maximum_normalized_cache_residual{};
    double maximum_normalized_centroid_drift{};
    double maximum_normalized_positive_energy_residual{};
    double maximum_valence_five_excursion_error{};
    double maximum_closed_one_ring_excursion_error{};
    double maximum_valence_five_error_over_initial_h{};
    double maximum_closed_one_ring_error_over_initial_h{};
    double maximum_closed_one_ring_edge_scaling_error{};
    double minimum_local_triangle_quality_ratio{1.0};
    bool common_roundoff_plateau{};
    bool differences_strictly_decreased{};
    bool time_orders_passed{};
    bool richardson_passed{};
    bool readonly_controls_passed{};
    bool force_buffers_cleared{};
    bool passed{};
};

struct MeanRadiusTimeFloorGateAudit {
    double exact_mean_radius_response{};
    std::array<MeanRadiusTimeFloorLevelAudit, 2> levels{};
    double cross_mesh_richardson_difference{};
    bool trajectories_passed{};
    bool time_levels_passed{};
    bool richardson_cross_mesh_passed{};
    bool readonly_controls_passed{};
    bool passed{};
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
    double control_area{};
    double normal_velocity_error{};
    double normal_signed_relative_error{};
    double normal_absolute_relative_error{};
    double tangential_relative_speed{};
    bool in_valence_five_closed_one_ring{};
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
    double exact_normal_velocity{};
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

struct SphericalMeanRadiusStructuralIdentityAudit {
    std::size_t vertex_count{};
    std::size_t face_count{};
    double rms_edge_length{};
    double surface_area{};
    double dual_area_sum{};
    double dual_area_to_surface_area_ratio{};
    double homogeneity_force_contraction{};
    double exact_homogeneity_force_contraction{};
    double normalized_homogeneity_residual{};
    double mean_radial_velocity{};
    double exact_mean_radial_velocity{};
    double normalized_mean_radial_velocity_residual{};
    double normalized_net_force_residual{};
    double maximum_relative_radius_deviation{};
    double maximum_position_displacement{};
    double maximum_force_buffer_norm_after{};
    std::uint64_t position_hash_before{};
    std::uint64_t position_hash_after{};
    std::uint64_t state_hash_before{};
    std::uint64_t state_hash_after{};
    bool force_buffers_cleared{};
};

struct SphericalNormalErrorRegionDiagnostic {
    std::size_t vertex_count{};
    double control_area{};
    double error_energy{};
    double total_error_energy_fraction{};
    double area_weighted_relative_rms{};
    double maximum_pointwise_relative_error{};
};

struct SphericalNormalErrorEnergyLevelAudit {
    double rms_edge_length{};
    double total_control_area{};
    double total_error_energy{};
    double partition_closure_residual{};
    SphericalNormalErrorRegionDiagnostic valence_five{};
    SphericalNormalErrorRegionDiagnostic valence_six{};
    SphericalNormalErrorRegionDiagnostic valence_five_closed_one_ring{};
    bool finite_nonnegative{};
    bool partition_closed{};
};

struct SphericalNormalErrorEnergyRefinementAudit {
    std::array<SphericalNormalErrorEnergyLevelAudit, 4> levels{};
    std::array<double, 3> total_error_energy_observed_orders{};
    std::array<double, 3> valence_five_error_energy_observed_orders{};
    std::array<double, 3> valence_six_error_energy_observed_orders{};
    std::array<double, 3> valence_five_closed_one_ring_observed_orders{};
    bool mesh_scales_decreased{};
    bool finite_nonnegative{};
    bool partition_closed{};
};

struct SphericalSymmetryBreakingLevelAudit {
    std::size_t vertex_count{};
    std::size_t symmetry_class_count{};
    std::size_t maximum_symmetry_class_size{};
    std::size_t minimum_required_class_count{};
    bool class_size_passed{};
    bool class_count_passed{};
    bool passed{};
};

struct SphericalSymmetryBreakingRefinementAudit {
    std::array<SphericalSymmetryBreakingLevelAudit, 4> levels{};
    bool passed{};
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

[[nodiscard]] FamilyCSmoothSphereTrajectoryAudit
run_family_c_smooth_sphere_trajectory(
    ::cell& target,
    const FamilyCSmoothSphereTrajectoryConfig& configuration
);

[[nodiscard]] FamilyCSmoothSphereGateAudit
evaluate_family_c_smooth_sphere_gate(
    const std::array<FamilyCSmoothSphereTrajectoryAudit, 4>& levels,
    const FamilyCSmoothSphereTrajectoryAudit& finest_half_time_step,
    const FamilyCSmoothSphereGateThresholds& thresholds
);

[[nodiscard]] MeanRadiusTimeFloorGateAudit evaluate_mean_radius_time_floor(
    const std::array<
        std::array<FamilyCSmoothSphereTrajectoryAudit, 4>,
        2
    >& runs,
    const MeanRadiusTimeFloorThresholds& thresholds
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

/** Audit the initial equal-radius Euler/mean-radius identities without motion. */
[[nodiscard]] SphericalMeanRadiusStructuralIdentityAudit
audit_spherical_mean_radius_structural_identity(
    ::cell& target,
    double surface_tension,
    double damping_per_area,
    double reference_radius
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

[[nodiscard]] SphericalNormalErrorEnergyRefinementAudit
evaluate_spherical_normal_error_energy_refinement(
    const std::array<SphericalSurfaceTensionInstantaneousAudit, 4>& levels
);

[[nodiscard]] SphericalSymmetryBreakingRefinementAudit
evaluate_quality_controlled_symmetry_breaking(
    const std::array<SphericalSurfaceTensionInstantaneousAudit, 4>& levels
);

} // namespace prl::cell_engine
