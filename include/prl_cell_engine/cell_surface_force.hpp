#pragma once

#include "prl_cell_engine/remesh_contract.hpp"

#include <array>
#include <cstddef>
#include <vector>

class cell;

namespace prl::cell_engine {

/** One additive force addressed by stable surface-vertex identity. */
struct SurfaceVertexForce {
    core::VertexId vertex_id{};
    std::array<double, 3> force{};
};

/** Audit of the force increment committed to one cell force buffer. */
struct SurfaceForceInjectionAudit {
    core::CellId cell_id{};
    core::MeshRevision revision{};
    std::size_t injected_vertex_count{};
    double injected_force_l2_norm{};
    double net_force_residual{};
    double net_moment_residual{};
};

/** Validated and committed derived geometry for one surface cell. */
struct SurfaceGeometryAudit {
    core::CellId cell_id{};
    core::MeshRevision revision{};
    std::size_t refreshed_face_count{};
    double surface_area{};
    double volume{};
    std::array<double, 3> centroid{};
    double minimum_face_area{};
};

/** Spatial measure represented by one damping coefficient. */
enum class SurfaceDampingMeasure {
    /** Legacy X1-G/H law: the same damping is assigned to every used vertex. */
    uniform_per_vertex,
    /** Surface drag density lumped with one third of each incident face area. */
    barycentric_dual_area,
};

/** Explicit damping law for an overdamped surface update. */
struct SurfaceDampingLaw {
    SurfaceDampingMeasure measure{SurfaceDampingMeasure::uniform_per_vertex};
    double coefficient{};
};

/** Audit of one atomic overdamped position update. */
struct SurfaceOverdampedStepAudit {
    core::CellId cell_id{};
    core::MeshRevision revision{};
    std::size_t stepped_vertex_count{};
    double time_step{};
    double damping_coefficient{};
    SurfaceDampingMeasure damping_measure{SurfaceDampingMeasure::uniform_per_vertex};
    double control_area_sum{};
    double minimum_nodal_damping{};
    double maximum_nodal_damping{};
    double preassembled_force_l2_norm{};
    double additional_force_l2_norm{};
    double total_force_l2_norm{};
    double displacement_l2_norm{};
    double total_force_work{};
    double viscous_dissipation{};
    double work_dissipation_residual{};
    double net_displacement_residual{};
    std::size_t refreshed_face_count{};
    double surface_area_after{};
    double volume_after{};
    std::array<double, 3> centroid_after{};
    double minimum_face_area_after{};
};

/**
 * Atomically accumulate finite force increments into used cell vertices.
 *
 * The caller must own the target cell for the duration of this operation.
 * All IDs, the expected topology revision, and all resulting force values are
 * validated before the first force-buffer write.
 */
[[nodiscard]] SurfaceForceInjectionAudit apply_surface_vertex_forces(
    ::cell& target,
    core::MeshRevision expected_revision,
    const std::vector<SurfaceVertexForce>& forces
);

/**
 * Advance one non-static cell by dx = dt * force / damping and reset forces.
 *
 * Existing node forces are treated as preassembled contributions. Additional
 * forces are addressed by persistent vertex ID. Positions and force buffers
 * are committed only after the complete step, including the derived face and
 * cell geometry, has been validated. Geometry caches are refreshed on commit.
 */
[[nodiscard]] SurfaceOverdampedStepAudit advance_surface_overdamped(
    ::cell& target,
    core::MeshRevision expected_revision,
    double time_step,
    SurfaceDampingLaw damping,
    const std::vector<SurfaceVertexForce>& additional_forces = {}
);

/**
 * Backward-compatible X1-G/H overload using uniform per-vertex damping.
 *
 * This overload deliberately preserves its historical meaning. New spatially
 * convergent PRL paths should pass an explicit SurfaceDampingLaw instead.
 */
[[nodiscard]] SurfaceOverdampedStepAudit advance_surface_overdamped(
    ::cell& target,
    core::MeshRevision expected_revision,
    double time_step,
    double damping_coefficient,
    const std::vector<SurfaceVertexForce>& additional_forces = {}
);

/** Validate current positions and refresh face/cell geometry caches. */
[[nodiscard]] SurfaceGeometryAudit refresh_surface_geometry(
    ::cell& target,
    core::MeshRevision expected_revision
);

/** Clear every used-node force buffer after a rejected owned assembly. */
[[nodiscard]] std::size_t reset_surface_forces(
    ::cell& target,
    core::MeshRevision expected_revision
);

} // namespace prl::cell_engine
