#pragma once

#include "prl/core/active_myocardial_mechanics.hpp"

#include <cstddef>
#include <vector>

class cell;

namespace prl::cell_engine {

/** Auditable active contribution committed during one cell force-assembly step. */
struct ActiveCellForceAssemblyAudit {
    core::CellId cell_id{};
    core::MeshRevision revision{};
    std::size_t unit_count{};
    std::size_t injected_vertex_count{};
    double total_active_energy{};
    double total_active_input_power{};
    double injected_force_l2_norm{};
    double net_force_residual{};
    double net_moment_residual{};
    double minimum_axis_fiber_alignment{};
    double maximum_activation{};
};

/**
 * Evaluate active contraction and accumulate its nodal forces into one real cell.
 *
 * This is a force-assembly operation only: it does not integrate positions,
 * update activation, remesh, or invoke passive/contact force models.
 */
[[nodiscard]] ActiveCellForceAssemblyAudit assemble_active_cell_forces(
    ::cell& target,
    const core::MyocardialCellMaterialState& material,
    const std::vector<core::ActiveContractionUnit>& units
);

} // namespace prl::cell_engine
