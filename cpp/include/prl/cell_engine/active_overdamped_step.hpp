#pragma once

#include "prl/core/active_myocardial_mechanics.hpp"

#include <array>
#include <cstddef>
#include <vector>

class cell;

namespace prl::cell_engine {

/** Spatial measure represented by the PRL cell-surface damping coefficient. */
enum class CellSurfaceDampingMeasure {
    /** Historical X1-G/H behavior retained only for replay compatibility. */
    uniform_per_vertex,
    /** Surface drag density lumped by barycentric vertex control area. */
    barycentric_dual_area,
};

/** PRL-owned damping configuration mapped to the cell-engine primitive. */
struct CellSurfaceDampingLaw {
    CellSurfaceDampingMeasure measure{CellSurfaceDampingMeasure::uniform_per_vertex};
    double coefficient{};
};

/** Ledger for one owned active overdamped surface step. */
struct ActiveCellOverdampedStepAudit {
    core::CellId cell_id{};
    core::MeshRevision revision{};
    std::size_t unit_count{};
    std::size_t stepped_vertex_count{};
    double time_step{};
    double damping_coefficient{};
    CellSurfaceDampingMeasure damping_measure{
        CellSurfaceDampingMeasure::uniform_per_vertex
    };
    double control_area_sum{};
    double minimum_nodal_damping{};
    double maximum_nodal_damping{};
    double active_energy_before{};
    double active_input_power{};
    double active_control_energy{};
    double preassembled_force_l2_norm{};
    double active_force_l2_norm{};
    double total_force_l2_norm{};
    double displacement_l2_norm{};
    double total_force_work{};
    double viscous_dissipation{};
    double work_dissipation_residual{};
    double net_displacement_residual{};
    double minimum_axis_fiber_alignment{};
    double maximum_activation{};
    std::size_t refreshed_face_count{};
    double surface_area_after{};
    double volume_after{};
    std::array<double, 3> centroid_after{};
    double minimum_face_area_after{};
};

/**
 * Evaluate active forces and execute one atomic overdamped position update.
 *
 * Existing cell force buffers are treated as already assembled passive or
 * contact contributions. The operation does not update activation or topology.
 */
[[nodiscard]] ActiveCellOverdampedStepAudit advance_active_cell_overdamped_one_step(
    ::cell& target,
    const core::MyocardialCellMaterialState& material,
    const std::vector<core::ActiveContractionUnit>& units,
    double time_step,
    CellSurfaceDampingLaw damping
);

/** Replay-compatible X1-G/H overload using uniform per-vertex damping. */
[[nodiscard]] ActiveCellOverdampedStepAudit advance_active_cell_overdamped_one_step(
    ::cell& target,
    const core::MyocardialCellMaterialState& material,
    const std::vector<core::ActiveContractionUnit>& units,
    double time_step,
    double damping_coefficient
);

} // namespace prl::cell_engine
