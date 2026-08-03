#include "prl/cell_engine/r1_remesh_robustness.hpp"
#include "prl/core/active_myocardial_mechanics.hpp"
#include "prl_cell_engine/cell_surface_snapshot.hpp"

#include "cell.hpp"
#include "custom_structures.hpp"
#include "node.hpp"

#include <cmath>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <vector>

namespace {

void require(const bool condition, const char* const message) {
    if(!condition) throw std::runtime_error(message);
}

const char* operation_name(const prl::core::RemeshOperation operation) {
    switch(operation) {
        case prl::core::RemeshOperation::edge_split: return "edge_split";
        case prl::core::RemeshOperation::edge_swap: return "edge_swap";
        case prl::core::RemeshOperation::edge_merge: return "edge_merge";
    }
    return "unknown";
}

void emit_samples(
    const char* const run,
    const std::vector<prl::cell_engine::R1TrajectorySample>& samples
) {
    for(const auto& sample : samples) {
        std::cout << "r1_sample,run," << run
                  << ",step," << sample.step
                  << ",time," << sample.time
                  << ",revision," << sample.revision
                  << ",vertex_count," << sample.vertex_count
                  << ",face_count," << sample.face_count
                  << ",axis_length," << sample.axis_length
                  << ",surface_area," << sample.surface_area
                  << ",area_ratio," << sample.area_ratio
                  << ",volume," << sample.volume
                  << ",volume_ratio," << sample.volume_ratio
                  << ",centroid_x," << sample.surface_centroid[0]
                  << ",centroid_y," << sample.surface_centroid[1]
                  << ",centroid_z," << sample.surface_centroid[2]
                  << ",normalized_centroid_drift,"
                  << sample.normalized_surface_centroid_drift
                  << ",registered_active_energy,"
                  << sample.registered_active_energy
                  << ",active_control_work," << sample.active_control_work
                  << ",viscous_dissipation," << sample.viscous_dissipation
                  << ",energy_balance_residual," << sample.energy_balance_residual
                  << ",minimum_oriented_face_alignment,"
                  << sample.minimum_oriented_face_alignment
                  << ",minimum_triangle_quality,"
                  << sample.minimum_triangle_quality
                  << ",minimum_face_area_ratio," << sample.minimum_face_area_ratio
                  << ",maximum_normalized_cache_residual,"
                  << sample.maximum_normalized_cache_residual
                  << ",force_buffer_l2_norm," << sample.force_buffer_l2_norm
                  << ",finite," << sample.finite
                  << ",state_hash," << sample.state_hash
                  << '\n';
    }
}

void emit_machine_records(
    const prl::cell_engine::R1RemeshRobustnessAudit& audit
) {
    const auto& config = audit.configuration;
    std::cout << std::setprecision(17)
              << "r1_config,time_step," << config.time_step
              << ",step_count," << config.step_count
              << ",split_step," << config.split_step
              << ",merge_step," << config.merge_step
              << ",qoi_unit," << config.qoi_contraction_unit_id
              << ",damping_measure,barycentric_dual_area"
              << ",damping_coefficient," << config.damping.coefficient
              << ",maximum_qoi_difference," << config.maximum_qoi_difference
              << ",maximum_remesh_defect," << config.maximum_remesh_defect
              << ",configuration_hash," << audit.configuration_hash
              << ",fixed_initial_state_hash," << audit.fixed_initial_state_hash
              << ",remesh_initial_state_hash," << audit.remesh_initial_state_hash
              << ",characteristic_length," << audit.characteristic_length
              << ",initial_axis_length," << audit.initial_axis_length
              << ",initial_active_energy," << audit.initial_active_energy
              << '\n';
    emit_samples("fixed", audit.fixed_samples);
    emit_samples("remesh", audit.remesh_samples);
    for(const auto& event : audit.events) {
        const auto& defect = event.energy_defect;
        std::cout << "r1_event,event_id," << event.event_id
                  << ",scheduled_step," << event.scheduled_step
                  << ",operation," << operation_name(event.operation)
                  << ",before_revision," << event.before_revision
                  << ",after_revision," << event.after_revision
                  << ",stored_energy_before," << defect.stored_energy_before
                  << ",stored_energy_after," << defect.stored_energy_after
                  << ",inter_event_stored_energy_change,"
                  << defect.inter_event_stored_energy_change
                  << ",delta_psi_remesh," << defect.delta_psi_remesh
                  << ",declared_remesh_work," << defect.declared_remesh_work
                  << ",algorithmic_energy_defect,"
                  << defect.algorithmic_energy_defect
                  << ",minimum_step_fiber_alignment,"
                  << defect.minimum_step_fiber_alignment
                  << ",minimum_initial_fiber_alignment,"
                  << defect.minimum_initial_fiber_alignment
                  << ",maximum_rebind_error," << defect.maximum_rebind_error
                  << '\n';
        const auto& transfer = event.material_transfer;
        std::cout << "r1_transfer,event_id," << event.event_id
                  << ",operation," << operation_name(transfer.operation)
                  << ",point_count," << transfer.point_count
                  << ",region_retention_fraction,"
                  << transfer.region_retention_fraction
                  << ",active_state_residual," << transfer.active_state_residual
                  << ",maximum_fiber_norm_error,"
                  << transfer.maximum_fiber_norm_error
                  << ",maximum_fiber_tangency_error,"
                  << transfer.maximum_fiber_tangency_error
                  << ",minimum_fiber_alignment,"
                  << transfer.minimum_fiber_alignment
                  << ",maximum_rebind_error," << transfer.maximum_rebind_error
                  << ",id_retention_fraction," << transfer.id_retention_fraction
                  << ",reference_weight_residual,"
                  << transfer.reference_weight_residual
                  << '\n';
    }
    for(const auto& comparison : audit.qoi_comparisons) {
        std::cout << "r1_qoi,step," << comparison.step
                  << ",normalized_axis_difference,"
                  << comparison.normalized_axis_difference
                  << ",area_ratio_difference," << comparison.area_ratio_difference
                  << ",volume_ratio_difference,"
                  << comparison.volume_ratio_difference
                  << ",normalized_active_energy_difference,"
                  << comparison.normalized_active_energy_difference
                  << '\n';
    }
    const auto& ledger = audit.remesh_ledger;
    std::cout << "r1_ledger,event_count," << ledger.event_count
              << ",split_event_count," << ledger.split_event_count
              << ",swap_event_count," << ledger.swap_event_count
              << ",merge_event_count," << ledger.merge_event_count
              << ",initial_revision," << ledger.initial_revision
              << ",current_revision," << ledger.current_revision
              << ",initial_stored_energy," << ledger.initial_stored_energy
              << ",final_stored_energy," << ledger.final_stored_energy
              << ",signed_inter_event,"
              << ledger.cumulative_inter_event_stored_energy_change
              << ",sum_abs_inter_event,"
              << ledger.cumulative_absolute_inter_event_stored_energy_change
              << ",max_abs_inter_event,"
              << ledger.maximum_absolute_inter_event_stored_energy_change
              << ",cumulative_delta_psi_remesh,"
              << ledger.cumulative_delta_psi_remesh
              << ",sum_abs_delta_psi_remesh,"
              << ledger.cumulative_absolute_delta_psi_remesh
              << ",declared_remesh_work,"
              << ledger.cumulative_declared_remesh_work
              << ",signed_algorithmic_energy_defect,"
              << ledger.cumulative_algorithmic_energy_defect
              << ",sum_abs_algorithmic_energy_defect,"
              << ledger.cumulative_absolute_algorithmic_energy_defect
              << ",maximum_absolute_delta_psi_remesh,"
              << ledger.maximum_absolute_delta_psi_remesh
              << ",energy_telescoping_residual,"
              << ledger.energy_telescoping_residual
              << ",minimum_step_fiber_alignment,"
              << ledger.minimum_step_fiber_alignment
              << ",minimum_initial_fiber_alignment,"
              << ledger.minimum_initial_fiber_alignment
              << ",maximum_rebind_error," << ledger.maximum_rebind_error
              << '\n';
    std::cout << "r1_gate,status,"
              << prl::cell_engine::r1_remesh_robustness_status_name(audit.status)
              << ",first_failure_step," << audit.first_failure_step
              << ",fixed_normalized_positive_energy_residual,"
              << audit.fixed_normalized_positive_energy_residual
              << ",remesh_normalized_positive_energy_residual,"
              << audit.remesh_normalized_positive_energy_residual
              << ",maximum_axis_difference," << audit.maximum_axis_difference
              << ",maximum_area_ratio_difference,"
              << audit.maximum_area_ratio_difference
              << ",maximum_volume_ratio_difference,"
              << audit.maximum_volume_ratio_difference
              << ",maximum_active_energy_difference,"
              << audit.maximum_active_energy_difference
              << ",qoi_gate_passed," << audit.qoi_gate_passed
              << ",j1_gate_passed," << audit.j1_gate_passed
              << ",safety_gate_passed," << audit.safety_gate_passed
              << ",passed," << audit.passed
              << ",failure_reason," << audit.failure_reason
              << '\n';
}

std::shared_ptr<cell_type_parameters> zero_passive_cell_type() {
    face_type_parameters face_type;
    face_type.name_ = "r1_zero_passive_surface";
    face_type.face_type_global_id_ = 0;
    face_type.surface_tension_ = 0.0;
    face_type.adherence_strength_ = 0.0;
    face_type.repulsion_strength_ = 0.0;
    face_type.bending_modulus_ = 0.0;

    auto result = std::make_shared<cell_type_parameters>();
    result->name_ = "r1_owned_active_cell";
    result->global_type_id_ = 2;
    result->mass_density_ = 1.0;
    result->bulk_modulus_ = 0.0;
    result->max_pressure_ = 1.0e6;
    result->initial_pressure_ = 0.0;
    result->area_elasticity_modulus_ = 0.0;
    result->avg_division_vol_ = 1.0e6;
    result->std_division_vol_ = 0.0;
    result->avg_growth_rate_ = 0.0;
    result->std_growth_rate_ = 0.0;
    result->min_vol_ = 1.0e-12;
    result->angle_regularization_factor_ = 0.0;
    result->target_isoperimetric_ratio_ = 150.0;
    result->surface_coupling_max_curvature_ = 1.0e6;
    result->add_face_type(face_type);
    return result;
}

cell_ptr r1_cell() {
    mesh cell_mesh;
    cell_mesh.node_pos_lst = {
         0.0,  0.0,  0.0,
         0.0, -3.0,  0.0,
        -1.0, -1.5,  0.0,
         1.0, -1.5,  0.0,
         0.0,  0.0, -1.0,
         0.0, -3.0, -1.0,
        -1.0, -1.5, -1.0,
         1.0, -1.5, -1.0,
    };
    cell_mesh.face_point_ids = {
        {0, 1, 2}, {0, 1, 3}, {0, 4, 2}, {2, 6, 4},
        {2, 6, 5}, {5, 1, 2}, {0, 3, 7}, {7, 4, 0},
        {3, 1, 5}, {5, 7, 3}, {4, 5, 6}, {4, 5, 7},
    };
    auto result = std::make_shared<cell>(cell_mesh, 17, zero_passive_cell_type());
    result->initialize_cell_properties();
    return result;
}

prl::core::VertexId persistent_node_id(
    const cell& current_cell,
    const unsigned local_id
) {
    return current_cell.get_node_lst().at(local_id).get_persistent_id();
}

prl::core::MyocardialCellMaterialState r1_material(const cell& current_cell) {
    using namespace prl::core;
    const auto a = persistent_node_id(current_cell, 0);
    const auto b = persistent_node_id(current_cell, 1);
    const auto c = persistent_node_id(current_cell, 2);
    const auto d = persistent_node_id(current_cell, 3);
    return {
        17,
        0,
        {
            {
                MyocardialMaterialState{
                    101,
                    SurfaceRegion::apical,
                    {1.0, 0.0, 0.0},
                    {0.05, 0.0},
                },
                {a, b, c},
                {0.2, 0.3, 0.5},
                0.17,
            },
            {
                MyocardialMaterialState{
                    205,
                    SurfaceRegion::basal,
                    {1.0, 0.0, 0.0},
                    {},
                },
                {a, b, d},
                {0.4, 0.25, 0.35},
                0.23,
            },
        },
    };
}

} // namespace

int main(const int argc, char* const argv[]) {
    const bool formal_response = argc == 2
        && std::string(argv[1]) == "--formal-response";
    if(argc > 2 || (argc == 2 && !formal_response)) {
        std::cerr << "usage: r1_remesh_robustness_integration_test "
                     "[--formal-response]\n";
        return 2;
    }
    auto fixed_cell = r1_cell();
    auto remesh_cell = r1_cell();
    const auto fixed_material = r1_material(*fixed_cell);
    const auto remesh_material = r1_material(*remesh_cell);
    const auto unit = prl::core::build_active_contraction_unit(
        prl::cell_engine::capture_surface_snapshot(*fixed_cell),
        fixed_material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );

    prl::cell_engine::R1RemeshRobustnessConfig config;
    config.time_step = 6.25e-4;
    config.step_count = 8;
    config.split_step = 2;
    config.merge_step = 3;
    config.qoi_contraction_unit_id = 501;
    config.damping = {
        prl::cell_engine::CellSurfaceDampingMeasure::barycentric_dual_area,
        10.0,
    };
    config.maximum_qoi_difference = 2.0e-3;
    config.maximum_remesh_defect = 1.0e-12;

    const auto audit = prl::cell_engine::run_active_r1_remesh_robustness(
        *fixed_cell,
        fixed_material,
        *remesh_cell,
        remesh_material,
        {unit},
        config
    );

    emit_machine_records(audit);
    std::cout.flush();

    std::cout << "r1_diagnostic,status,"
              << prl::cell_engine::r1_remesh_robustness_status_name(audit.status)
              << ",first_failure_step," << audit.first_failure_step
              << ",reason," << audit.failure_reason
              << ",fixed_samples," << audit.fixed_samples.size()
              << ",remesh_samples," << audit.remesh_samples.size()
              << ",events," << audit.events.size()
              << '\n';
    if(!audit.remesh_samples.empty()) {
        const auto& last = audit.remesh_samples.back();
        std::cout << std::setprecision(17)
                  << "r1_last_remesh_sample,step," << last.step
                  << ",revision," << last.revision
                  << ",vertices," << last.vertex_count
                  << ",faces," << last.face_count
                  << ",finite," << last.finite
                  << ",orientation," << last.minimum_oriented_face_alignment
                  << ",quality," << last.minimum_triangle_quality
                  << ",face_ratio," << last.minimum_face_area_ratio
                  << ",cache," << last.maximum_normalized_cache_residual
                  << ",centroid," << last.normalized_surface_centroid_drift
                  << ",volume_ratio," << last.volume_ratio
                  << ",force_buffer," << last.force_buffer_l2_norm
                  << '\n';
    }

    require(
        audit.status
            == prl::cell_engine::R1RemeshRobustnessStatus::
                failed_geometry_cache_force_finite_gate,
        "v09 R1 regression did not preserve the frozen failure status"
    );
    require(audit.first_failure_step == 3,
            "v09 R1 regression did not preserve first failure step 3");
    require(audit.fixed_samples.size() == 9 && audit.remesh_samples.size() == 4,
            "v09 R1 regression did not stop at the first hard failure");
    require(audit.events.size() == 2
                && audit.events[0].operation == prl::core::RemeshOperation::edge_split
                && audit.events[1].operation == prl::core::RemeshOperation::edge_merge,
            "v09 R1 regression did not preserve the real split/merge evidence");
    const auto& failed_sample = audit.remesh_samples.back();
    require(std::abs(
                failed_sample.normalized_surface_centroid_drift
                - 0.083736797387197567
            ) <= 1.0e-15,
            "v09 R1 centroid-drift boundary value changed");
    require(failed_sample.normalized_surface_centroid_drift > 1.0e-2
                && failed_sample.finite
                && failed_sample.minimum_oriented_face_alignment > 0.0
                && failed_sample.minimum_triangle_quality >= 0.05
                && failed_sample.minimum_face_area_ratio >= 1.0e-4
                && failed_sample.maximum_normalized_cache_residual <= 1.0e-12
                && failed_sample.force_buffer_l2_norm <= 1.0e-12,
            "v09 R1 first-failure boundary or peer controls changed");
    require(audit.qoi_comparisons.empty()
                && !audit.qoi_gate_passed
                && !audit.j1_gate_passed
                && !audit.safety_gate_passed
                && !audit.passed,
            "v09 R1 ran or passed a downstream gate after first failure");
    require(audit.remesh_ledger.event_count == 2,
            "v09 R1 lost the observed supporting event ledger");
    if(formal_response) return 1;

    std::cout << "r1_regression,status,passed_frozen_failure_regression,"
                 "formal_response_exit_code,1\n";
    return 0;
}
