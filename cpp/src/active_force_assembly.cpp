#include "prl/cell_engine/active_force_assembly.hpp"
#include "prl/cell_engine/active_overdamped_step.hpp"

#include "prl_cell_engine/cell_surface_force.hpp"
#include "prl_cell_engine/cell_surface_snapshot.hpp"

#include <cmath>
#include <stdexcept>
#include <vector>

namespace prl::cell_engine {
namespace {

std::vector<SurfaceVertexForce> surface_forces_from(
    const core::ActiveContractionEvaluation& active
) {
    std::vector<SurfaceVertexForce> result;
    result.reserve(active.vertex_forces.size());
    for(const auto& vertex_force : active.vertex_forces) {
        result.push_back({vertex_force.vertex_id, vertex_force.force});
    }
    return result;
}

} // namespace

ActiveCellForceAssemblyAudit assemble_active_cell_forces(
    ::cell& target,
    const core::MyocardialCellMaterialState& material,
    const std::vector<core::ActiveContractionUnit>& units
) {
    const auto mesh = capture_surface_snapshot(target);
    const auto active = core::evaluate_active_contraction(mesh, material, units);
    const auto force_increments = surface_forces_from(active);
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

ActiveCellOverdampedStepAudit advance_active_cell_overdamped_one_step(
    ::cell& target,
    const core::MyocardialCellMaterialState& material,
    const std::vector<core::ActiveContractionUnit>& units,
    const double time_step,
    const double damping_coefficient
) {
    if(!std::isfinite(time_step) || time_step <= 0.0) {
        throw std::invalid_argument("active overdamped time step must be finite and positive");
    }
    if(!std::isfinite(damping_coefficient) || damping_coefficient <= 0.0) {
        throw std::invalid_argument(
            "active overdamped damping coefficient must be finite and positive"
        );
    }
    const auto before_mesh = capture_surface_snapshot(target);
    const auto before_active = core::evaluate_active_contraction(
        before_mesh,
        material,
        units
    );
    const double active_control_energy = before_active.audit.total_input_power * time_step;
    if(!std::isfinite(before_active.audit.total_energy)
       || !std::isfinite(before_active.audit.total_input_power)
       || !std::isfinite(active_control_energy)
       || !std::isfinite(before_active.audit.net_force_residual)
       || !std::isfinite(before_active.audit.net_moment_residual)
       || !std::isfinite(before_active.audit.minimum_axis_fiber_alignment)
       || !std::isfinite(before_active.audit.maximum_activation)) {
        throw std::runtime_error("active overdamped pre-step audit must be finite");
    }
    const auto step = advance_surface_overdamped(
        target,
        before_mesh.revision,
        time_step,
        damping_coefficient,
        surface_forces_from(before_active)
    );
    return {
        before_active.cell_id,
        before_active.revision,
        before_active.audit.unit_count,
        step.stepped_vertex_count,
        step.time_step,
        step.damping_coefficient,
        before_active.audit.total_energy,
        before_active.audit.total_input_power,
        active_control_energy,
        step.preassembled_force_l2_norm,
        step.additional_force_l2_norm,
        step.total_force_l2_norm,
        step.displacement_l2_norm,
        step.total_force_work,
        step.viscous_dissipation,
        step.work_dissipation_residual,
        step.net_displacement_residual,
        before_active.audit.minimum_axis_fiber_alignment,
        before_active.audit.maximum_activation,
        step.refreshed_face_count,
        step.surface_area_after,
        step.volume_after,
        step.centroid_after,
        step.minimum_face_area_after,
    };
}

} // namespace prl::cell_engine
