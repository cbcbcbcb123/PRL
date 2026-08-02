#pragma once

#include "prl/core/myocardial_material_transfer.hpp"

#include <array>
#include <cstddef>
#include <cstdint>
#include <vector>

namespace prl::core {

using ActiveContractionUnitId = std::uint64_t;

struct ActivationSample {
    double activation{};
    double activation_rate{};
};

/** Frozen C1 rest-ramp-hold-release activation protocol. */
[[nodiscard]] ActivationSample c1_activation_protocol(
    double time,
    double delay = 0.0,
    double alpha_peak = 0.1
);

/**
 * One preferred-length contraction unit between persistent material points.
 *
 * Activation and the material fiber director are read from
 * activation_material_point_id. The reference length is fixed when the unit is
 * built and is independent of later remeshing.
 */
struct ActiveContractionUnit {
    ActiveContractionUnitId contraction_unit_id{};
    MaterialPointId minus_material_point_id{};
    MaterialPointId plus_material_point_id{};
    MaterialPointId activation_material_point_id{};
    double reference_length{};
    double stiffness{};
    double minimum_axis_fiber_alignment{};
};

struct ActiveContractionUnitState {
    ActiveContractionUnitId contraction_unit_id{};
    double length{};
    std::array<double, 3> axis{};
    double preferred_length{};
    double preferred_length_rate{};
    double activation{};
    double activation_rate{};
    double energy{};
    double input_power{};
    double axis_fiber_alignment{};
};

struct ActiveVertexForce {
    VertexId vertex_id{};
    std::array<double, 3> force{};
};

struct ActiveContractionAudit {
    std::size_t unit_count{};
    double total_energy{};
    double total_input_power{};
    double net_force_residual{};
    double net_moment_residual{};
    double minimum_axis_fiber_alignment{};
    double maximum_activation{};
};

struct ActiveContractionEvaluation {
    CellId cell_id{};
    MeshRevision revision{};
    std::vector<ActiveContractionUnitState> unit_states{};
    std::vector<ActiveVertexForce> vertex_forces{};
    ActiveContractionAudit audit{};
};

[[nodiscard]] ActiveContractionUnit build_active_contraction_unit(
    const SurfaceMeshSnapshot& reference_mesh,
    const MyocardialCellMaterialState& reference_material,
    ActiveContractionUnitId contraction_unit_id,
    MaterialPointId minus_material_point_id,
    MaterialPointId plus_material_point_id,
    MaterialPointId activation_material_point_id,
    double stiffness,
    double minimum_axis_fiber_alignment = 0.9
);

[[nodiscard]] ActiveContractionEvaluation evaluate_active_contraction(
    const SurfaceMeshSnapshot& mesh,
    const MyocardialCellMaterialState& material,
    const std::vector<ActiveContractionUnit>& units
);

} // namespace prl::core
