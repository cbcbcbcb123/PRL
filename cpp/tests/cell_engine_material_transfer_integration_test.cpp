#include "prl/core/active_myocardial_mechanics.hpp"
#include "prl/core/myocardial_material_transfer.hpp"
#include "prl_cell_engine/cell_surface_snapshot.hpp"

#include "cell.hpp"
#include "edge.hpp"
#include "local_mesh_refiner.hpp"

#include <cassert>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr double tolerance = 1.0e-12;

void require(const bool condition, const char* const message) {
    if(!condition) throw std::runtime_error(message);
}

cell_ptr closed_swap_cell(const double lifted_vertex_height = 0.0) {
    mesh cell_mesh;
    cell_mesh.node_pos_lst = {
         0.0,  0.0,  0.0,
         0.0, -3.0,  0.0,
        -1.0, -1.5,  0.0,
         1.0, -1.5,  lifted_vertex_height,
         0.0,  0.0, -1.0,
         0.0, -3.0, -1.0,
        -1.0, -1.5, -1.0,
         1.0, -1.5, -1.0,
    };
    cell_mesh.face_point_ids = {
        {0, 1, 2},
        {0, 1, 3},
        {0, 4, 2},
        {2, 6, 4},
        {2, 6, 5},
        {5, 1, 2},
        {0, 3, 7},
        {7, 4, 0},
        {3, 1, 5},
        {5, 7, 3},
        {4, 5, 6},
        {4, 5, 7},
    };
    auto result = std::make_shared<cell>(cell_mesh, 17);
    result->generate_edge_set();
    return result;
}

prl::core::VertexId persistent_node_id(const cell& current_cell, const unsigned local_id) {
    return current_cell.get_node_lst().at(local_id).get_persistent_id();
}

std::vector<prl::core::SurfaceMaterialPoint> myocardial_points(const cell& current_cell) {
    using namespace prl::core;
    const auto a = persistent_node_id(current_cell, 0);
    const auto b = persistent_node_id(current_cell, 1);
    const auto c = persistent_node_id(current_cell, 2);
    const auto d = persistent_node_id(current_cell, 3);
    return {
        {
            MyocardialMaterialState{101, SurfaceRegion::apical, {1.0, 0.0, 0.0}, {0.2, 0.3}},
            {a, b, c},
            {0.2, 0.3, 0.5},
            0.17,
        },
        {
            MyocardialMaterialState{205, SurfaceRegion::basal, {0.0, 1.0, 0.0}, {0.4, 0.7}},
            {a, b, d},
            {0.4, 0.25, 0.35},
            0.23,
        },
    };
}

bool exactly_equal(
    const prl::core::SurfaceMeshSnapshot& left,
    const prl::core::SurfaceMeshSnapshot& right
) {
    if(left.cell_id != right.cell_id
       || left.revision != right.revision
       || left.vertices.size() != right.vertices.size()
       || left.faces.size() != right.faces.size()) {
        return false;
    }
    for(std::size_t index = 0; index < left.vertices.size(); ++index) {
        if(left.vertices[index].persistent_id != right.vertices[index].persistent_id
           || left.vertices[index].position != right.vertices[index].position) {
            return false;
        }
    }
    for(std::size_t index = 0; index < left.faces.size(); ++index) {
        if(left.faces[index].vertex_indices != right.faces[index].vertex_indices) {
            return false;
        }
    }
    return true;
}

bool exactly_equal(
    const prl::core::MyocardialCellMaterialState& left,
    const prl::core::MyocardialCellMaterialState& right
) {
    if(left.cell_id != right.cell_id
       || left.revision != right.revision
       || left.points.size() != right.points.size()) {
        return false;
    }
    for(std::size_t index = 0; index < left.points.size(); ++index) {
        const auto& left_point = left.points[index];
        const auto& right_point = right.points[index];
        if(left_point.material.material_point_id
               != right_point.material.material_point_id
           || left_point.material.region != right_point.material.region
           || left_point.material.fiber_direction
               != right_point.material.fiber_direction
           || left_point.material.active_state != right_point.material.active_state
           || left_point.host_vertex_ids != right_point.host_vertex_ids
           || left_point.barycentric != right_point.barycentric
           || left_point.reference_weight != right_point.reference_weight) {
            return false;
        }
    }
    return true;
}

int real_swap_transfers_registered_myocardial_state() {
    using namespace prl::core;
    auto current_cell = closed_swap_cell();
    auto sink = std::make_shared<MyocardialMaterialTransferSink>(tolerance);
    sink->register_cell(
        prl::cell_engine::capture_surface_snapshot(*current_cell),
        myocardial_points(*current_cell)
    );
    local_mesh_refiner refiner(0.1, 10.0, true, sink);

    const auto edge_iterator = current_cell->get_edge_set().find(edge(0, 1));
    assert(edge_iterator != current_cell->get_edge_set().end());
    refiner.swap_edge(const_cast<edge&>(*edge_iterator), current_cell);

    const auto state = sink->cell_state(17);
    const auto audit = sink->last_audit(17);
    assert(current_cell->get_mesh_revision() == 1);
    assert(state.revision == current_cell->get_mesh_revision());
    assert(state.points.size() == 2);
    assert(state.points[0].material.material_point_id == 101);
    assert(state.points[0].material.region == SurfaceRegion::apical);
    assert(state.points[0].material.active_state == std::vector<double>({0.2, 0.3}));
    assert(std::abs(state.points[0].reference_weight - 0.17) <= tolerance);
    assert(state.points[1].material.material_point_id == 205);
    assert(state.points[1].material.region == SurfaceRegion::basal);
    assert(state.points[1].material.active_state == std::vector<double>({0.4, 0.7}));
    assert(std::abs(state.points[1].reference_weight - 0.23) <= tolerance);
    assert(audit.operation == RemeshOperation::edge_swap);
    assert(audit.point_count == 2);
    assert(audit.maximum_rebind_error <= tolerance);
    assert(audit.active_state_residual == 0.0);
    assert(audit.reference_weight_residual == 0.0);
    return 0;
}

int transfer_failure_propagates_from_the_real_refiner() {
    using namespace prl::core;
    auto current_cell = closed_swap_cell(0.2);
    auto sink = std::make_shared<MyocardialMaterialTransferSink>(tolerance);
    sink->register_cell(
        prl::cell_engine::capture_surface_snapshot(*current_cell),
        myocardial_points(*current_cell)
    );
    const auto before_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto before_material = sink->cell_state(17);
    local_mesh_refiner refiner(0.1, 10.0, true, sink);
    const auto edge_iterator = current_cell->get_edge_set().find(edge(0, 1));
    assert(edge_iterator != current_cell->get_edge_set().end());

    bool failure_propagated = false;
    try {
        refiner.swap_edge(const_cast<edge&>(*edge_iterator), current_cell);
    } catch(const std::runtime_error& error) {
        const std::string message = error.what();
        failure_propagated = message.find("id=101") != std::string::npos
            && message.find("distance=") != std::string::npos;
    }
    require(failure_propagated, "material-transfer failure did not propagate");
    const auto after_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto after_material = sink->cell_state(17);
    require(current_cell->get_mesh_revision() == 0,
            "rejected remesh advanced the cell revision");
    require(exactly_equal(after_mesh, before_mesh),
            "rejected remesh changed cell geometry, topology, or persistent IDs");
    require(exactly_equal(after_material, before_material),
            "rejected remesh changed myocardial material state");

    bool audit_absent = false;
    try {
        static_cast<void>(sink->last_audit(17));
    } catch(const std::logic_error&) {
        audit_absent = true;
    }
    assert(audit_absent);
    return 0;
}

int real_split_and_merge_advance_the_same_material_registry() {
    using namespace prl::core;
    auto current_cell = closed_swap_cell();
    auto sink = std::make_shared<MyocardialMaterialTransferSink>(1.0);
    sink->register_cell(
        prl::cell_engine::capture_surface_snapshot(*current_cell),
        myocardial_points(*current_cell)
    );
    local_mesh_refiner refiner(0.1, 10.0, true, sink);
    edge_set edges_to_check;

    const auto original_edge = current_cell->get_edge_set().find(edge(0, 1));
    assert(original_edge != current_cell->get_edge_set().end());
    refiner.split_edge(const_cast<edge&>(*original_edge), current_cell, edges_to_check);
    assert(current_cell->get_mesh_revision() == 1);
    assert(sink->cell_state(17).revision == 1);
    assert(sink->last_audit(17).operation == RemeshOperation::edge_split);

    const auto split_node_id = static_cast<unsigned>(current_cell->get_node_lst().size() - 1);
    const auto split_edge = current_cell->get_edge_set().find(edge(0, split_node_id));
    assert(split_edge != current_cell->get_edge_set().end());
    refiner.merge_edge(const_cast<edge&>(*split_edge), current_cell, edges_to_check);

    const auto state = sink->cell_state(17);
    const auto audit = sink->last_audit(17);
    assert(current_cell->get_mesh_revision() == 2);
    assert(state.revision == current_cell->get_mesh_revision());
    assert(state.points.size() == 2);
    assert(state.points[0].material.active_state == std::vector<double>({0.2, 0.3}));
    assert(state.points[1].material.active_state == std::vector<double>({0.4, 0.7}));
    assert(audit.operation == RemeshOperation::edge_merge);
    assert(audit.point_count == 2);
    assert(audit.active_state_residual == 0.0);
    assert(audit.reference_weight_residual == 0.0);
    assert(audit.maximum_rebind_error <= 1.0);
    return 0;
}

int active_mechanics_is_invariant_through_the_real_refiner() {
    using namespace prl::core;
    auto current_cell = closed_swap_cell();
    auto sink = std::make_shared<MyocardialMaterialTransferSink>(tolerance);
    sink->register_cell(
        prl::cell_engine::capture_surface_snapshot(*current_cell),
        myocardial_points(*current_cell)
    );

    const auto activation = c1_activation_protocol(1.5, 0.0, 0.1);
    sink->update_active_state(
        17,
        101,
        0,
        {activation.activation, activation.activation_rate}
    );
    const auto before_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto before_material = sink->cell_state(17);
    const auto unit = build_active_contraction_unit(
        before_mesh,
        before_material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );
    const auto before = evaluate_active_contraction(before_mesh, before_material, {unit});

    local_mesh_refiner refiner(0.1, 10.0, true, sink);
    const auto edge_iterator = current_cell->get_edge_set().find(edge(0, 1));
    require(edge_iterator != current_cell->get_edge_set().end(), "swap edge is missing");
    refiner.swap_edge(const_cast<edge&>(*edge_iterator), current_cell);

    const auto after_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto after_material = sink->cell_state(17);
    const auto after = evaluate_active_contraction(after_mesh, after_material, {unit});
    require(after_mesh.revision == 1, "real refiner did not advance the mesh revision");
    require(after_material.revision == after_mesh.revision,
            "active material and mesh revisions diverged after remeshing");
    require(std::abs(after.audit.total_energy - before.audit.total_energy) <= tolerance,
            "active energy changed across real remeshing");
    require(
        std::abs(after.audit.total_input_power - before.audit.total_input_power) <= tolerance,
        "active input power changed across real remeshing"
    );
    require(
        std::abs(after.unit_states.at(0).length - before.unit_states.at(0).length) <= tolerance,
        "active anchor length changed across real remeshing"
    );
    require(
        std::abs(
            after.unit_states.at(0).preferred_length
            - before.unit_states.at(0).preferred_length
        ) <= tolerance,
        "active preferred length changed across real remeshing"
    );
    require(after.audit.net_force_residual <= tolerance,
            "active resultant is nonzero after real remeshing");
    require(after.audit.net_moment_residual <= tolerance,
            "active net moment is nonzero after real remeshing");
    require(after.audit.minimum_axis_fiber_alignment >= 0.9,
            "active axis lost fiber alignment after real remeshing");
    return 0;
}

int real_swap_records_the_active_remesh_energy_defect() {
    using namespace prl::core;
    auto current_cell = closed_swap_cell();
    auto sink = std::make_shared<MyocardialMaterialTransferSink>(tolerance);
    sink->register_cell(
        prl::cell_engine::capture_surface_snapshot(*current_cell),
        myocardial_points(*current_cell)
    );
    const auto activation = c1_activation_protocol(1.5, 0.0, 0.1);
    sink->update_active_state(
        17,
        101,
        0,
        {activation.activation, activation.activation_rate}
    );
    const auto before_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto before_material = sink->cell_state(17);
    const auto unit = build_active_contraction_unit(
        before_mesh,
        before_material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );
    const auto before = evaluate_active_contraction(
        before_mesh,
        before_material,
        {unit}
    );
    sink->begin_active_remesh_energy_ledger(before_mesh, {unit});

    local_mesh_refiner refiner(0.1, 10.0, true, sink);
    const auto edge_iterator = current_cell->get_edge_set().find(edge(0, 1));
    require(edge_iterator != current_cell->get_edge_set().end(), "swap edge is missing");
    refiner.swap_edge(const_cast<edge&>(*edge_iterator), current_cell);

    const auto after_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto after_material = sink->cell_state(17);
    const auto after = evaluate_active_contraction(after_mesh, after_material, {unit});
    const auto transfer = sink->last_audit(17);
    const auto defect = sink->last_remesh_energy_defect(17);
    const auto ledger = sink->remesh_energy_ledger(17);
    std::cerr << std::setprecision(17)
              << "swap_delta_psi=" << defect.delta_psi_remesh
              << " step_fiber_alignment=" << defect.minimum_step_fiber_alignment
              << " initial_fiber_alignment=" << defect.minimum_initial_fiber_alignment
              << " ledger_initial_fiber_alignment="
              << ledger.minimum_initial_fiber_alignment
              << '\n';
    require(defect.operation == RemeshOperation::edge_swap,
            "remesh-energy ledger recorded the wrong operation");
    require(defect.before_revision == 0 && defect.after_revision == 1,
            "remesh-energy ledger revisions are wrong");
    require(std::abs(defect.stored_energy_before - before.audit.total_energy) <= tolerance
                && std::abs(defect.stored_energy_after - after.audit.total_energy) <= tolerance,
            "remesh-energy ledger does not match independent active energy");
    require(std::abs(defect.delta_psi_remesh
                     - (defect.stored_energy_after - defect.stored_energy_before))
                <= tolerance,
            "DeltaPsi_remesh is not the stored-energy jump");
    require(defect.declared_remesh_work == 0.0,
            "topology-only remeshing invented mechanical work");
    require(std::abs(defect.algorithmic_energy_defect) <= tolerance,
            "planar real swap created active algorithmic energy");
    require(ledger.event_count == 1
                && std::abs(ledger.cumulative_delta_psi_remesh) <= tolerance
                && ledger.cumulative_declared_remesh_work == 0.0,
            "single-event remesh-energy ledger did not accumulate correctly");
    require(std::abs(defect.minimum_step_fiber_alignment
                     - transfer.minimum_fiber_alignment) <= tolerance,
            "remesh-energy ledger lost the transfer fiber-rotation audit");
    require(defect.minimum_initial_fiber_alignment >= 0.0
                && defect.minimum_initial_fiber_alignment <= 1.0
                && std::abs(ledger.minimum_initial_fiber_alignment
                            - defect.minimum_initial_fiber_alignment) <= tolerance,
            "remesh-energy ledger did not accumulate baseline fiber alignment");
    return 0;
}

int real_split_and_merge_record_separate_energy_defects() {
    using namespace prl::core;
    auto current_cell = closed_swap_cell();
    auto sink = std::make_shared<MyocardialMaterialTransferSink>(1.0);
    sink->register_cell(
        prl::cell_engine::capture_surface_snapshot(*current_cell),
        myocardial_points(*current_cell)
    );
    const auto activation = c1_activation_protocol(1.5, 0.0, 0.1);
    sink->update_active_state(
        17,
        101,
        0,
        {activation.activation, activation.activation_rate}
    );
    const auto initial_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto initial_material = sink->cell_state(17);
    const auto unit = build_active_contraction_unit(
        initial_mesh,
        initial_material,
        501,
        101,
        205,
        101,
        10.0,
        0.0
    );
    const auto initial_energy = evaluate_active_contraction(
        initial_mesh,
        initial_material,
        {unit}
    ).audit.total_energy;
    require(initial_energy > 1.0e-2,
            "split/merge hardening case has trivial initial active energy");
    sink->begin_active_remesh_energy_ledger(initial_mesh, {unit});
    local_mesh_refiner refiner(0.1, 10.0, true, sink);
    edge_set edges_to_check;

    const auto original_edge = current_cell->get_edge_set().find(edge(0, 1));
    require(original_edge != current_cell->get_edge_set().end(), "split edge is missing");
    refiner.split_edge(
        const_cast<edge&>(*original_edge),
        current_cell,
        edges_to_check
    );
    const auto split_defect = sink->last_remesh_energy_defect(17);
    require(split_defect.operation == RemeshOperation::edge_split
                && split_defect.before_revision == 0
                && split_defect.after_revision == 1,
            "real split did not produce its own remesh-energy defect");
    require(split_defect.declared_remesh_work == 0.0
                && std::isfinite(split_defect.algorithmic_energy_defect),
            "real split remesh-energy defect is invalid");

    const auto split_node_id = static_cast<unsigned>(current_cell->get_node_lst().size() - 1);
    const auto split_edge = current_cell->get_edge_set().find(edge(0, split_node_id));
    require(split_edge != current_cell->get_edge_set().end(), "merge edge is missing");
    refiner.merge_edge(
        const_cast<edge&>(*split_edge),
        current_cell,
        edges_to_check
    );
    const auto merge_defect = sink->last_remesh_energy_defect(17);
    const auto ledger = sink->remesh_energy_ledger(17);
    const auto final_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto final_energy = evaluate_active_contraction(
        final_mesh,
        sink->cell_state(17),
        {unit}
    ).audit.total_energy;

    std::cerr << std::setprecision(17)
              << "split_delta_psi=" << split_defect.delta_psi_remesh
              << " merge_delta_psi=" << merge_defect.delta_psi_remesh
              << " cumulative_delta_psi=" << ledger.cumulative_delta_psi_remesh
              << " final_energy_drift=" << final_energy - initial_energy
              << '\n';
    require(merge_defect.operation == RemeshOperation::edge_merge
                && merge_defect.before_revision == 1
                && merge_defect.after_revision == 2,
            "real merge did not produce its own remesh-energy defect");
    require(ledger.event_count == 2
                && ledger.split_event_count == 1
                && ledger.swap_event_count == 0
                && ledger.merge_event_count == 1,
            "split/merge operation counts are not independently auditable");
    require(ledger.cumulative_declared_remesh_work == 0.0,
            "split/merge sequence invented mechanical work");
    require(std::abs(
                ledger.cumulative_delta_psi_remesh
                - (final_energy - initial_energy)
            ) <= tolerance,
            "split/merge cumulative defect does not match the energy drift");
    require(ledger.energy_telescoping_residual <= tolerance,
            "split/merge energy ledger does not telescope");
    RemeshCycleGateThresholds thresholds{
        1.0e-12,
        1.0e-12,
        1.0e-12,
        1.0e-12,
        1.0e-12,
        1.0 - 1.0e-12,
    };
    thresholds.minimum_event_count = 2;
    thresholds.maximum_rebind_error = 1.0e-12;
    const auto gate = evaluate_remesh_cycle_gate(ledger, thresholds);
    require(gate.energy_drift_passed
                && gate.absolute_defect_passed
                && gate.fiber_drift_passed
                && gate.rebind_passed
                && gate.passed,
            "real split/merge failed the nontrivial quantitative cycle gate");
    return 0;
}

int repeated_real_swap_cycles_do_not_accumulate_remesh_defects() {
    using namespace prl::core;
    auto current_cell = closed_swap_cell();
    auto sink = std::make_shared<MyocardialMaterialTransferSink>(tolerance);
    sink->register_cell(
        prl::cell_engine::capture_surface_snapshot(*current_cell),
        myocardial_points(*current_cell)
    );
    const auto activation = c1_activation_protocol(1.5, 0.0, 0.1);
    sink->update_active_state(
        17,
        101,
        0,
        {activation.activation, activation.activation_rate}
    );
    const auto initial_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto initial_material = sink->cell_state(17);
    const auto unit = build_active_contraction_unit(
        initial_mesh,
        initial_material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );
    sink->begin_active_remesh_energy_ledger(initial_mesh, {unit});
    local_mesh_refiner refiner(0.1, 10.0, true, sink);

    constexpr std::size_t cycle_count = 8;
    for(std::size_t cycle = 0; cycle < cycle_count; ++cycle) {
        const auto forward_edge = current_cell->get_edge_set().find(edge(0, 1));
        require(forward_edge != current_cell->get_edge_set().end(),
                "forward cycle swap edge is missing");
        refiner.swap_edge(const_cast<edge&>(*forward_edge), current_cell);

        const auto reverse_edge = current_cell->get_edge_set().find(edge(2, 3));
        require(reverse_edge != current_cell->get_edge_set().end(),
                "reverse cycle swap edge is missing");
        refiner.swap_edge(const_cast<edge&>(*reverse_edge), current_cell);
    }

    const auto ledger = sink->remesh_energy_ledger(17);
    const RemeshCycleGateThresholds thresholds{
        1.0e-12,
        1.0e-12,
        1.0e-12,
        1.0e-12,
        1.0e-12,
        1.0 - 1.0e-12,
    };
    const auto gate = evaluate_remesh_cycle_gate(ledger, thresholds);
    std::cerr << std::setprecision(17)
              << "cycle_events=" << ledger.event_count
              << " final_energy_drift=" << gate.final_energy_drift
              << " cumulative_absolute_delta_psi="
              << ledger.cumulative_absolute_delta_psi_remesh
              << " cumulative_remesh_work="
              << ledger.cumulative_declared_remesh_work
              << " minimum_initial_fiber_alignment="
              << ledger.minimum_initial_fiber_alignment
              << '\n';
    require(ledger.event_count == 2 * cycle_count
                && ledger.swap_event_count == 2 * cycle_count
                && ledger.split_event_count == 0
                && ledger.merge_event_count == 0,
            "real swap-cycle event accounting is incomplete");
    require(gate.event_count_passed
                && gate.energy_drift_passed
                && gate.absolute_defect_passed
                && gate.inter_event_change_passed
                && gate.remesh_work_passed
                && gate.telescoping_passed
                && gate.fiber_drift_passed
                && gate.passed,
            "real swap cycles accumulated a remesh defect");
    return 0;
}

int interleaved_energy_changes_are_not_hidden_by_signed_cancellation() {
    using namespace prl::core;
    auto current_cell = closed_swap_cell();
    auto sink = std::make_shared<MyocardialMaterialTransferSink>(tolerance);
    sink->register_cell(
        prl::cell_engine::capture_surface_snapshot(*current_cell),
        myocardial_points(*current_cell)
    );
    const auto low_activation = c1_activation_protocol(1.5, 0.0, 0.1);
    sink->update_active_state(
        17,
        101,
        0,
        {low_activation.activation, 0.0}
    );
    const auto initial_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto initial_material = sink->cell_state(17);
    const auto unit = build_active_contraction_unit(
        initial_mesh,
        initial_material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );
    sink->begin_active_remesh_energy_ledger(initial_mesh, {unit});
    local_mesh_refiner refiner(0.1, 10.0, true, sink);

    const auto forward_edge_1 = current_cell->get_edge_set().find(edge(0, 1));
    require(forward_edge_1 != current_cell->get_edge_set().end(),
            "first interleaved swap edge is missing");
    refiner.swap_edge(const_cast<edge&>(*forward_edge_1), current_cell);

    sink->update_active_state(17, 101, 1, {0.1, 0.0});
    const auto reverse_edge = current_cell->get_edge_set().find(edge(2, 3));
    require(reverse_edge != current_cell->get_edge_set().end(),
            "interleaved reverse swap edge is missing");
    refiner.swap_edge(const_cast<edge&>(*reverse_edge), current_cell);

    sink->update_active_state(
        17,
        101,
        2,
        {low_activation.activation, 0.0}
    );
    const auto forward_edge_2 = current_cell->get_edge_set().find(edge(0, 1));
    require(forward_edge_2 != current_cell->get_edge_set().end(),
            "second interleaved swap edge is missing");
    refiner.swap_edge(const_cast<edge&>(*forward_edge_2), current_cell);

    const auto ledger = sink->remesh_energy_ledger(17);
    require(std::abs(ledger.cumulative_inter_event_stored_energy_change)
                <= 1.0e-12,
            "interleaved signed energy changes did not cancel in the fixture");
    require(ledger.cumulative_absolute_inter_event_stored_energy_change > 1.0e-2
                && ledger.maximum_absolute_inter_event_stored_energy_change > 1.0e-2,
            "interleaved absolute energy-change ledger hid cancellation");

    RemeshCycleGateThresholds thresholds{
        1.0e-12,
        1.0e-12,
        1.0e-12,
        1.0e-12,
        1.0e-12,
        1.0 - 1.0e-12,
    };
    thresholds.minimum_event_count = 3;
    thresholds.maximum_rebind_error = 1.0e-12;
    thresholds.maximum_cumulative_absolute_inter_event_energy_change = 1.0e-12;
    thresholds.maximum_per_event_absolute_inter_event_energy_change = 1.0e-12;
    const auto gate = evaluate_remesh_cycle_gate(ledger, thresholds);
    require(gate.inter_event_change_passed
                && !gate.absolute_inter_event_change_passed
                && !gate.maximum_inter_event_change_passed
                && !gate.passed,
            "signed cancellation incorrectly passed the no-interleaving gate");
    return 0;
}

} // namespace

int main(const int argc, const char* const argv[]) {
    assert(argc == 2);
    const std::string behavior = argv[1];
    if(behavior == "real_swap") return real_swap_transfers_registered_myocardial_state();
    if(behavior == "failure_propagation") return transfer_failure_propagates_from_the_real_refiner();
    if(behavior == "real_split_merge") return real_split_and_merge_advance_the_same_material_registry();
    if(behavior == "active_remesh_invariance") {
        return active_mechanics_is_invariant_through_the_real_refiner();
    }
    if(behavior == "real_swap_energy_ledger") {
        return real_swap_records_the_active_remesh_energy_defect();
    }
    if(behavior == "real_split_merge_energy_ledger") {
        return real_split_and_merge_record_separate_energy_defects();
    }
    if(behavior == "real_swap_cycle_gate") {
        return repeated_real_swap_cycles_do_not_accumulate_remesh_defects();
    }
    if(behavior == "interleaved_energy_no_cancellation") {
        return interleaved_energy_changes_are_not_hidden_by_signed_cancellation();
    }
    return 1;
}
