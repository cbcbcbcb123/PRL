#pragma once

#include "prl/core/remesh_contract.hpp"

#include <array>
#include <cstdint>
#include <limits>
#include <memory>
#include <vector>

namespace prl::core {

struct ActiveContractionUnit;

/**
 * One persistent myocardial material point and its current geometric host.
 *
 * Biology is owned by material_point_id. The host is expressed using stable
 * vertex IDs, never a temporary face index; barycentric coordinates follow the
 * same vertex order as host_vertex_ids.
 */
struct SurfaceMaterialPoint {
    MyocardialMaterialState material{};
    std::array<VertexId, 3> host_vertex_ids{};
    std::array<double, 3> barycentric{};
    double reference_weight{};
};

struct MyocardialCellMaterialState {
    CellId cell_id{};
    MeshRevision revision{};
    std::vector<SurfaceMaterialPoint> points{};
};

/** Energy owners currently included in the remesh-defect ledger. */
enum class RemeshEnergyCoverage : std::uint8_t {
    active_contraction_only,
};

/** One topology-event energy jump, which is not relabeled as physical work. */
struct RemeshEnergyDefectAudit {
    CellId cell_id{};
    RemeshOperation operation{};
    MeshRevision before_revision{};
    MeshRevision after_revision{};
    RemeshEnergyCoverage coverage{RemeshEnergyCoverage::active_contraction_only};
    std::size_t active_unit_count{};
    double stored_energy_before{};
    double stored_energy_after{};
    double inter_event_stored_energy_change{};
    double delta_psi_remesh{};
    double declared_remesh_work{};
    double algorithmic_energy_defect{};
    double minimum_step_fiber_alignment{};
    double minimum_initial_fiber_alignment{};
    double maximum_rebind_error{};
};

/** Cumulative ledger for a pure or interleaved sequence of remesh events. */
struct RemeshEnergyLedgerAudit {
    CellId cell_id{};
    MeshRevision initial_revision{};
    MeshRevision current_revision{};
    RemeshEnergyCoverage coverage{RemeshEnergyCoverage::active_contraction_only};
    std::size_t active_unit_count{};
    std::size_t event_count{};
    std::size_t split_event_count{};
    std::size_t swap_event_count{};
    std::size_t merge_event_count{};
    double initial_stored_energy{};
    double final_stored_energy{};
    double cumulative_inter_event_stored_energy_change{};
    double cumulative_absolute_inter_event_stored_energy_change{};
    double maximum_absolute_inter_event_stored_energy_change{};
    double cumulative_delta_psi_remesh{};
    double cumulative_absolute_delta_psi_remesh{};
    double cumulative_declared_remesh_work{};
    double cumulative_algorithmic_energy_defect{};
    double cumulative_absolute_algorithmic_energy_defect{};
    double maximum_absolute_delta_psi_remesh{};
    double energy_telescoping_residual{};
    double minimum_step_fiber_alignment{1.0};
    double minimum_initial_fiber_alignment{1.0};
    double maximum_rebind_error{};
};

/** Thresholds for accepting a remesh-only topology cycle. */
struct RemeshCycleGateThresholds {
    double maximum_absolute_final_energy_drift{};
    double maximum_cumulative_absolute_energy_defect{};
    double maximum_absolute_inter_event_energy_change{};
    double maximum_absolute_declared_remesh_work{};
    double maximum_energy_telescoping_residual{};
    double minimum_initial_fiber_alignment{};
    std::size_t minimum_event_count{1};
    double maximum_rebind_error{std::numeric_limits<double>::max()};
    double maximum_cumulative_absolute_inter_event_energy_change{
        std::numeric_limits<double>::max()
    };
    double maximum_per_event_absolute_inter_event_energy_change{
        std::numeric_limits<double>::max()
    };
};

/** Independently visible decisions composing the remesh-cycle gate. */
struct RemeshCycleGateAudit {
    bool event_count_passed{};
    bool energy_drift_passed{};
    bool absolute_defect_passed{};
    bool inter_event_change_passed{};
    bool absolute_inter_event_change_passed{};
    bool maximum_inter_event_change_passed{};
    bool remesh_work_passed{};
    bool telescoping_passed{};
    bool fiber_drift_passed{};
    bool rebind_passed{};
    bool passed{};
    double final_energy_drift{};
    double fiber_drift{};
};

[[nodiscard]] RemeshCycleGateAudit evaluate_remesh_cycle_gate(
    const RemeshEnergyLedgerAudit& ledger,
    const RemeshCycleGateThresholds& thresholds
);

/**
 * Thread-safe production consumer for synchronous cell-engine remesh events.
 *
 * Each cell is transferred atomically under its own lock. Events for different
 * cells may proceed concurrently. A failed transfer leaves the registered
 * state and revision unchanged.
 */
class MyocardialMaterialTransferSink final : public RemeshEventSink {
public:
    explicit MyocardialMaterialTransferSink(double maximum_rebind_distance = 1.0e-12);
    ~MyocardialMaterialTransferSink() override;

    MyocardialMaterialTransferSink(const MyocardialMaterialTransferSink&) = delete;
    MyocardialMaterialTransferSink& operator=(const MyocardialMaterialTransferSink&) = delete;
    MyocardialMaterialTransferSink(MyocardialMaterialTransferSink&&) = delete;
    MyocardialMaterialTransferSink& operator=(MyocardialMaterialTransferSink&&) = delete;

    void register_cell(
        const SurfaceMeshSnapshot& mesh,
        std::vector<SurfaceMaterialPoint> points
    );

    void on_remesh(
        const RemeshEvent& event,
        const SurfaceMeshSnapshot& before,
        const SurfaceMeshSnapshot& after
    ) override;

    void update_active_state(
        CellId cell_id,
        MaterialPointId material_point_id,
        MeshRevision expected_revision,
        std::vector<double> active_state
    );

    /** Begin an active-stored-energy ledger at a revision-matched mesh state. */
    void begin_active_remesh_energy_ledger(
        const SurfaceMeshSnapshot& mesh,
        std::vector<ActiveContractionUnit> units
    );

    [[nodiscard]] MyocardialCellMaterialState cell_state(CellId cell_id) const;
    [[nodiscard]] RemeshTransferAudit last_audit(CellId cell_id) const;
    [[nodiscard]] RemeshEnergyDefectAudit last_remesh_energy_defect(
        CellId cell_id
    ) const;
    [[nodiscard]] RemeshEnergyLedgerAudit remesh_energy_ledger(CellId cell_id) const;

private:
    class Impl;
    std::unique_ptr<Impl> implementation_;
};

} // namespace prl::core
