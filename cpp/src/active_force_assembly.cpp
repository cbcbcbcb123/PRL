#include "prl/cell_engine/active_force_assembly.hpp"

#include "prl_cell_engine/cell_surface_force.hpp"
#include "prl_cell_engine/cell_surface_snapshot.hpp"

#include <vector>

namespace prl::cell_engine {

ActiveCellForceAssemblyAudit assemble_active_cell_forces(
    ::cell& target,
    const core::MyocardialCellMaterialState& material,
    const std::vector<core::ActiveContractionUnit>& units
) {
    const auto mesh = capture_surface_snapshot(target);
    const auto active = core::evaluate_active_contraction(mesh, material, units);
    std::vector<SurfaceVertexForce> force_increments;
    force_increments.reserve(active.vertex_forces.size());
    for(const auto& vertex_force : active.vertex_forces) {
        force_increments.push_back({vertex_force.vertex_id, vertex_force.force});
    }
    const auto injection = apply_surface_vertex_forces(
        target,
        mesh.revision,
        force_increments
    );
    return {
        active.cell_id,
        active.revision,
        active.audit.unit_count,
        injection.injected_vertex_count,
        active.audit.total_energy,
        active.audit.total_input_power,
        injection.injected_force_l2_norm,
        injection.net_force_residual,
        injection.net_moment_residual,
        active.audit.minimum_axis_fiber_alignment,
        active.audit.maximum_activation,
    };
}

} // namespace prl::cell_engine
