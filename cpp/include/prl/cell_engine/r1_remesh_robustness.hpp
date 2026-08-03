#pragma once

#include "prl/cell_engine/owned_active_overdamped_step.hpp"
#include "prl/core/myocardial_material_transfer.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

class cell;

namespace prl::cell_engine {

enum class R1RemeshRobustnessStatus : std::uint8_t {
    passed,
    failed_invalid_configuration,
    failed_fixed_trajectory,
    failed_remesh_trajectory,
    failed_qoi_difference,
    failed_j1_gate,
    failed_geometry_cache_force_finite_gate,
};

[[nodiscard]] const char* r1_remesh_robustness_status_name(
    R1RemeshRobustnessStatus status
) noexcept;

struct R1RemeshRobustnessConfig {
    double time_step{};
    std::size_t step_count{};
    std::size_t split_step{};
    std::size_t merge_step{};
    core::ActiveContractionUnitId qoi_contraction_unit_id{};
    CellSurfaceDampingLaw damping{};

    double maximum_qoi_difference{2.0e-3};
    double maximum_remesh_defect{1.0e-12};
    double minimum_initial_active_energy{1.0e-2};
    double minimum_fiber_alignment{1.0 - 1.0e-12};
    double maximum_rebind_error{1.0e-12};
    double minimum_triangle_quality{0.05};
    double minimum_face_area_ratio{1.0e-4};
    double maximum_normalized_cache_residual{1.0e-12};
    double maximum_normalized_centroid_drift{1.0e-2};
    double minimum_volume_ratio{0.5};
    double maximum_volume_ratio{1.5};
    double maximum_force_buffer_norm{1.0e-12};
    double maximum_normalized_positive_energy_residual{5.0e-3};
};

struct R1TrajectorySample {
    std::size_t step{};
    double time{};
    core::MeshRevision revision{};
    std::size_t vertex_count{};
    std::size_t face_count{};
    double axis_length{};
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
    double minimum_oriented_face_alignment{1.0};
    double minimum_triangle_quality{1.0};
    double minimum_face_area_ratio{1.0};
    double maximum_normalized_cache_residual{};
    double force_buffer_l2_norm{};
    bool finite{};
    std::uint64_t state_hash{};
};

struct R1RemeshEventAudit {
    std::size_t event_id{};
    std::size_t scheduled_step{};
    core::RemeshOperation operation{};
    core::MeshRevision before_revision{};
    core::MeshRevision after_revision{};
    core::RemeshTransferAudit material_transfer{};
    core::RemeshEnergyDefectAudit energy_defect{};
};

struct R1QoiComparisonSample {
    std::size_t step{};
    double normalized_axis_difference{};
    double area_ratio_difference{};
    double volume_ratio_difference{};
    double normalized_active_energy_difference{};
};

struct R1RemeshRobustnessAudit {
    R1RemeshRobustnessStatus status{
        R1RemeshRobustnessStatus::failed_invalid_configuration
    };
    R1RemeshRobustnessConfig configuration{};
    std::uint64_t configuration_hash{};
    std::uint64_t fixed_initial_state_hash{};
    std::uint64_t remesh_initial_state_hash{};
    double characteristic_length{};
    double initial_axis_length{};
    double initial_active_energy{};
    std::vector<R1TrajectorySample> fixed_samples{};
    std::vector<R1TrajectorySample> remesh_samples{};
    std::vector<R1RemeshEventAudit> events{};
    std::vector<R1QoiComparisonSample> qoi_comparisons{};
    core::RemeshEnergyLedgerAudit remesh_ledger{};
    double maximum_axis_difference{};
    double maximum_area_ratio_difference{};
    double maximum_volume_ratio_difference{};
    double maximum_active_energy_difference{};
    double fixed_normalized_positive_energy_residual{};
    double remesh_normalized_positive_energy_residual{};
    bool qoi_gate_passed{};
    bool j1_gate_passed{};
    bool safety_gate_passed{};
    bool passed{};
    std::size_t first_failure_step{};
    std::string failure_reason{};
};

/**
 * Run the frozen R1 fixed-topology/remesh-on pair through production seams.
 *
 * The remesh branch uses synchronous real split/merge operations observed by
 * MyocardialMaterialTransferSink. No synthetic RemeshEvent or private mesh
 * mutation seam is accepted by this API.
 */
[[nodiscard]] R1RemeshRobustnessAudit run_active_r1_remesh_robustness(
    ::cell& fixed_target,
    const core::MyocardialCellMaterialState& fixed_material,
    ::cell& remesh_target,
    const core::MyocardialCellMaterialState& remesh_material,
    const std::vector<core::ActiveContractionUnit>& units,
    const R1RemeshRobustnessConfig& configuration
);

} // namespace prl::cell_engine
