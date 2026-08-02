#include "prl/cell_engine/active_force_assembly.hpp"
#include "prl/cell_engine/active_overdamped_step.hpp"
#include "prl/core/active_myocardial_mechanics.hpp"
#include "prl/core/myocardial_material_transfer.hpp"
#include "prl_cell_engine/cell_surface_force.hpp"
#include "prl_cell_engine/cell_surface_snapshot.hpp"

#include "cell.hpp"
#include "edge.hpp"
#include "local_mesh_refiner.hpp"
#include "node.hpp"
#include "vec3.hpp"

#include <array>
#include <cmath>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr double tolerance = 1.0e-12;

void require(const bool condition, const char* const message) {
    if(!condition) throw std::runtime_error(message);
}

cell_ptr active_test_cell() {
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

std::vector<prl::core::SurfaceMaterialPoint> active_material_points(
    const cell& current_cell,
    const double activation_time = 1.5
) {
    using namespace prl::core;
    const auto activation = c1_activation_protocol(activation_time, 0.0, 0.1);
    const auto a = persistent_node_id(current_cell, 0);
    const auto b = persistent_node_id(current_cell, 1);
    const auto c = persistent_node_id(current_cell, 2);
    const auto d = persistent_node_id(current_cell, 3);
    return {
        {
            MyocardialMaterialState{
                101,
                SurfaceRegion::apical,
                {1.0, 0.0, 0.0},
                {activation.activation, activation.activation_rate},
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
    };
}

std::array<double, 3> active_force_for(
    const prl::core::ActiveContractionEvaluation& evaluation,
    const prl::core::VertexId vertex_id
) {
    for(const auto& vertex_force : evaluation.vertex_forces) {
        if(vertex_force.vertex_id == vertex_id) return vertex_force.force;
    }
    throw std::runtime_error("active evaluation omitted a persistent vertex");
}

double active_force_l2_norm(
    const prl::core::ActiveContractionEvaluation& evaluation
) {
    double squared_norm = 0.0;
    for(const auto& vertex_force : evaluation.vertex_forces) {
        for(const double component : vertex_force.force) {
            squared_norm += component * component;
        }
    }
    return std::sqrt(squared_norm);
}

bool nearly_equal(const double left, const double right) {
    return std::abs(left - right) <= tolerance;
}

int active_force_accumulates_into_the_real_cell_buffer() {
    using namespace prl::core;
    auto current_cell = active_test_cell();
    MyocardialMaterialTransferSink sink(tolerance);
    const auto mesh_snapshot = prl::cell_engine::capture_surface_snapshot(*current_cell);
    sink.register_cell(mesh_snapshot, active_material_points(*current_cell));
    const auto material = sink.cell_state(17);
    const auto unit = build_active_contraction_unit(
        mesh_snapshot,
        material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );
    const auto expected = evaluate_active_contraction(mesh_snapshot, material, {unit});

    const std::array<double, 3> passive_baseline{0.01, -0.02, 0.03};
    current_cell->add_force(vec3{
        passive_baseline[0],
        passive_baseline[1],
        passive_baseline[2],
    });
    const auto audit = prl::cell_engine::assemble_active_cell_forces(
        *current_cell,
        material,
        {unit}
    );

    require(current_cell->get_mesh_revision() == 0,
            "single-step force assembly changed the mesh revision");
    require(audit.cell_id == 17 && audit.revision == 0,
            "single-step force assembly audit identity mismatch");
    require(audit.unit_count == 1, "single-step force assembly unit count mismatch");
    require(audit.injected_vertex_count == current_cell->get_nb_of_nodes(),
            "single-step force assembly did not cover every used vertex");
    require(nearly_equal(audit.total_active_energy, expected.audit.total_energy),
            "single-step active-energy ledger mismatch");
    require(nearly_equal(audit.total_active_input_power, expected.audit.total_input_power),
            "single-step active-power ledger mismatch");
    require(audit.net_force_residual <= tolerance,
            "single-step active force has a nonzero resultant");
    require(audit.net_moment_residual <= tolerance,
            "single-step active force has a nonzero moment");

    for(const node& current_node : current_cell->get_node_lst()) {
        if(!current_node.is_used()) continue;
        const auto active_force = active_force_for(
            expected,
            current_node.get_persistent_id()
        );
        require(nearly_equal(current_node.force().dx(), passive_baseline[0] + active_force[0]),
                "active x-force did not accumulate into the real cell buffer");
        require(nearly_equal(current_node.force().dy(), passive_baseline[1] + active_force[1]),
                "active y-force did not accumulate into the real cell buffer");
        require(nearly_equal(current_node.force().dz(), passive_baseline[2] + active_force[2]),
                "active z-force did not accumulate into the real cell buffer");
    }
    return 0;
}

int rejected_force_injection_leaves_the_real_cell_buffer_unchanged() {
    using namespace prl::core;
    auto current_cell = active_test_cell();
    const std::array<double, 3> baseline{0.01, -0.02, 0.03};
    current_cell->add_force(vec3{baseline[0], baseline[1], baseline[2]});
    const auto valid_vertex = persistent_node_id(*current_cell, 0);

    const auto mesh_snapshot = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const MyocardialCellMaterialState material{
        17,
        0,
        active_material_points(*current_cell),
    };
    const auto unit = build_active_contraction_unit(
        mesh_snapshot,
        material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );
    auto stale_material = material;
    stale_material.revision = 1;
    bool stale_material_rejected = false;
    try {
        static_cast<void>(prl::cell_engine::assemble_active_cell_forces(
            *current_cell,
            stale_material,
            {unit}
        ));
    } catch(const std::invalid_argument&) {
        stale_material_rejected = true;
    }
    require(stale_material_rejected, "stale active material state was assembled");

    bool unknown_vertex_rejected = false;
    try {
        static_cast<void>(prl::cell_engine::apply_surface_vertex_forces(
            *current_cell,
            0,
            {
                {valid_vertex, {0.2, 0.0, 0.0}},
                {999999, {0.0, 0.1, 0.0}},
            }
        ));
    } catch(const std::out_of_range&) {
        unknown_vertex_rejected = true;
    }
    require(unknown_vertex_rejected, "unknown persistent force vertex was accepted");

    bool stale_revision_rejected = false;
    try {
        static_cast<void>(prl::cell_engine::apply_surface_vertex_forces(
            *current_cell,
            1,
            {{valid_vertex, {0.2, 0.0, 0.0}}}
        ));
    } catch(const std::logic_error&) {
        stale_revision_rejected = true;
    }
    require(stale_revision_rejected, "stale force-assembly revision was accepted");

    for(const node& current_node : current_cell->get_node_lst()) {
        if(!current_node.is_used()) continue;
        require(nearly_equal(current_node.force().dx(), baseline[0]),
                "rejected force injection changed the x buffer");
        require(nearly_equal(current_node.force().dy(), baseline[1]),
                "rejected force injection changed the y buffer");
        require(nearly_equal(current_node.force().dz(), baseline[2]),
                "rejected force injection changed the z buffer");
    }
    return 0;
}

int active_force_assembly_tracks_the_post_remesh_revision() {
    using namespace prl::core;
    auto current_cell = active_test_cell();
    auto sink = std::make_shared<MyocardialMaterialTransferSink>(tolerance);
    const auto before_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    sink->register_cell(before_mesh, active_material_points(*current_cell));
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

    local_mesh_refiner refiner(0.1, 10.0, true, sink);
    const auto edge_iterator = current_cell->get_edge_set().find(edge(0, 1));
    require(edge_iterator != current_cell->get_edge_set().end(), "swap edge is missing");
    refiner.swap_edge(const_cast<edge&>(*edge_iterator), current_cell);

    const auto after_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto after_material = sink->cell_state(17);
    const auto expected = evaluate_active_contraction(after_mesh, after_material, {unit});
    const std::array<double, 3> passive_baseline{-0.03, 0.02, 0.01};
    current_cell->add_force(vec3{
        passive_baseline[0],
        passive_baseline[1],
        passive_baseline[2],
    });
    const auto audit = prl::cell_engine::assemble_active_cell_forces(
        *current_cell,
        after_material,
        {unit}
    );

    require(after_mesh.revision == 1 && after_material.revision == 1,
            "real remesh did not synchronize the assembly revision");
    require(audit.revision == 1, "active assembly did not use the post-remesh revision");
    require(nearly_equal(audit.total_active_energy, expected.audit.total_energy),
            "post-remesh active-energy ledger mismatch");
    require(nearly_equal(audit.total_active_input_power, expected.audit.total_input_power),
            "post-remesh active-power ledger mismatch");
    require(audit.net_force_residual <= tolerance,
            "post-remesh injected force has a nonzero resultant");
    require(audit.net_moment_residual <= tolerance,
            "post-remesh injected force has a nonzero moment");
    for(const node& current_node : current_cell->get_node_lst()) {
        if(!current_node.is_used()) continue;
        const auto active_force = active_force_for(
            expected,
            current_node.get_persistent_id()
        );
        require(nearly_equal(current_node.force().dx(), passive_baseline[0] + active_force[0]),
                "post-remesh active x-force assembly mismatch");
        require(nearly_equal(current_node.force().dy(), passive_baseline[1] + active_force[1]),
                "post-remesh active y-force assembly mismatch");
        require(nearly_equal(current_node.force().dz(), passive_baseline[2] + active_force[2]),
                "post-remesh active z-force assembly mismatch");
    }
    return 0;
}

int one_overdamped_step_moves_the_real_cell_down_active_energy() {
    using namespace prl::core;
    auto current_cell = active_test_cell();
    const auto before_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const MyocardialCellMaterialState material{
        17,
        0,
        active_material_points(*current_cell, 2.5),
    };
    const auto unit = build_active_contraction_unit(
        before_mesh,
        material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );
    const auto before_active = evaluate_active_contraction(before_mesh, material, {unit});
    const double time_step = 1.0e-3;
    const double damping = 1.0;

    const auto audit = prl::cell_engine::advance_active_cell_overdamped_one_step(
        *current_cell,
        material,
        {unit},
        time_step,
        damping
    );
    const auto after_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto after_active = evaluate_active_contraction(after_mesh, material, {unit});

    require(current_cell->get_mesh_revision() == 0,
            "overdamped step changed the mesh revision");
    require(audit.cell_id == 17 && audit.revision == 0,
            "overdamped step audit identity mismatch");
    require(audit.stepped_vertex_count == current_cell->get_nb_of_nodes(),
            "overdamped step did not cover every used vertex");
    require(nearly_equal(audit.time_step, time_step)
            && nearly_equal(audit.damping_coefficient, damping),
            "overdamped step parameters were not frozen in the audit");
    require(nearly_equal(audit.active_energy_before, before_active.audit.total_energy),
            "overdamped pre-step energy ledger mismatch");
    require(nearly_equal(audit.active_energy_before, 0.04315625),
            "manufactured plateau active energy changed");
    require(after_active.audit.total_energy < audit.active_energy_before,
            "overdamped active step did not descend active energy");
    require(nearly_equal(after_active.audit.total_energy, 0.04279879638351551),
            "manufactured post-step active energy changed");
    require(nearly_equal(audit.active_input_power, 0.0),
            "plateau activation should have zero control-input power");
    require(nearly_equal(audit.active_control_energy, 0.0),
            "plateau activation should add no control energy");
    const double expected_active_force_norm = active_force_l2_norm(before_active);
    require(nearly_equal(audit.preassembled_force_l2_norm, 0.0)
            && nearly_equal(audit.active_force_l2_norm, expected_active_force_norm)
            && nearly_equal(audit.total_force_l2_norm, expected_active_force_norm),
            "overdamped force-norm ledger mismatch");
    require(nearly_equal(
                audit.displacement_l2_norm,
                time_step * expected_active_force_norm / damping
            ),
            "overdamped displacement-norm ledger mismatch");
    require(audit.total_force_work > 0.0, "overdamped mechanical work is not positive");
    require(nearly_equal(audit.total_force_work, 0.000358196875),
            "manufactured force-work ledger changed");
    require(audit.viscous_dissipation > 0.0,
            "overdamped viscous dissipation is not positive");
    require(audit.work_dissipation_residual <= tolerance,
            "overdamped force work and viscous dissipation diverged");
    require(audit.net_displacement_residual <= tolerance,
            "balanced active force translated the cell centroid");

    for(std::size_t index = 0; index < before_mesh.vertices.size(); ++index) {
        const auto& before_vertex = before_mesh.vertices[index];
        const auto& after_vertex = after_mesh.vertices[index];
        require(after_vertex.persistent_id == before_vertex.persistent_id,
                "overdamped step changed persistent vertex identity");
        const auto force = active_force_for(before_active, before_vertex.persistent_id);
        for(std::size_t component = 0; component < 3; ++component) {
            const double expected_position = before_vertex.position[component]
                + time_step * force[component] / damping;
            require(nearly_equal(after_vertex.position[component], expected_position),
                    "overdamped node displacement does not equal dt/damping times force");
        }
    }
    for(const node& current_node : current_cell->get_node_lst()) {
        if(!current_node.is_used()) continue;
        require(nearly_equal(current_node.force().norm(), 0.0),
                "overdamped step did not consume and reset the force buffer");
    }
    require(after_active.unit_states.at(0).length < before_active.unit_states.at(0).length,
            "overdamped active step did not shorten the contraction axis");
    require(nearly_equal(after_active.unit_states.at(0).length, 0.9286596550414490),
            "manufactured post-step contraction length changed");
    return 0;
}

int rejected_active_overdamped_step_is_atomic() {
    using namespace prl::core;
    auto current_cell = active_test_cell();
    const auto before_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const MyocardialCellMaterialState material{
        17,
        0,
        active_material_points(*current_cell, 2.5),
    };
    const auto unit = build_active_contraction_unit(
        before_mesh,
        material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );
    const std::array<double, 3> baseline_force{0.01, -0.02, 0.03};
    current_cell->add_force(vec3{
        baseline_force[0],
        baseline_force[1],
        baseline_force[2],
    });

    bool damping_rejected = false;
    try {
        static_cast<void>(prl::cell_engine::advance_active_cell_overdamped_one_step(
            *current_cell,
            material,
            {unit},
            1.0e-3,
            0.0
        ));
    } catch(const std::invalid_argument&) {
        damping_rejected = true;
    }
    require(damping_rejected, "nonpositive active-step damping was accepted");

    auto stale_material = material;
    stale_material.revision = 1;
    bool stale_material_rejected = false;
    try {
        static_cast<void>(prl::cell_engine::advance_active_cell_overdamped_one_step(
            *current_cell,
            stale_material,
            {unit},
            1.0e-3,
            1.0
        ));
    } catch(const std::invalid_argument&) {
        stale_material_rejected = true;
    }
    require(stale_material_rejected, "stale material entered the active overdamped step");

    auto overflowing_power_material = material;
    overflowing_power_material.points.at(0).material.active_state.at(1)
        = std::numeric_limits<double>::max();
    auto overflowing_power_unit = unit;
    overflowing_power_unit.stiffness = 20.0;
    bool overflowing_power_rejected = false;
    try {
        static_cast<void>(prl::cell_engine::advance_active_cell_overdamped_one_step(
            *current_cell,
            overflowing_power_material,
            {overflowing_power_unit},
            1.0e-3,
            1.0
        ));
    } catch(const std::runtime_error&) {
        overflowing_power_rejected = true;
    }
    require(overflowing_power_rejected,
            "non-finite active power entered the active overdamped commit");

    const auto after_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    require(after_mesh.vertices.size() == before_mesh.vertices.size(),
            "rejected active step changed the vertex count");
    for(std::size_t index = 0; index < before_mesh.vertices.size(); ++index) {
        require(after_mesh.vertices[index].persistent_id
                    == before_mesh.vertices[index].persistent_id
                && after_mesh.vertices[index].position
                    == before_mesh.vertices[index].position,
                "rejected active step changed a vertex");
    }
    for(const node& current_node : current_cell->get_node_lst()) {
        if(!current_node.is_used()) continue;
        require(nearly_equal(current_node.force().dx(), baseline_force[0])
                && nearly_equal(current_node.force().dy(), baseline_force[1])
                && nearly_equal(current_node.force().dz(), baseline_force[2]),
                "rejected active step changed or consumed a force buffer");
    }
    return 0;
}

int active_overdamped_step_tracks_the_post_remesh_revision() {
    using namespace prl::core;
    auto current_cell = active_test_cell();
    auto sink = std::make_shared<MyocardialMaterialTransferSink>(tolerance);
    const auto original_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    sink->register_cell(original_mesh, active_material_points(*current_cell, 2.5));
    const auto original_material = sink->cell_state(17);
    const auto unit = build_active_contraction_unit(
        original_mesh,
        original_material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );

    local_mesh_refiner refiner(0.1, 10.0, true, sink);
    const auto edge_iterator = current_cell->get_edge_set().find(edge(0, 1));
    require(edge_iterator != current_cell->get_edge_set().end(), "swap edge is missing");
    refiner.swap_edge(const_cast<edge&>(*edge_iterator), current_cell);

    const auto before_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto material = sink->cell_state(17);
    const auto before_active = evaluate_active_contraction(before_mesh, material, {unit});
    const double time_step = 1.0e-3;
    const double damping = 1.0;
    const auto audit = prl::cell_engine::advance_active_cell_overdamped_one_step(
        *current_cell,
        material,
        {unit},
        time_step,
        damping
    );
    const auto after_mesh = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto after_active = evaluate_active_contraction(after_mesh, material, {unit});

    require(before_mesh.revision == 1 && material.revision == 1,
            "real remesh did not synchronize the step revision");
    require(audit.revision == 1 && after_mesh.revision == 1,
            "active step did not preserve the post-remesh revision");
    require(after_active.audit.total_energy < before_active.audit.total_energy,
            "post-remesh active step did not descend active energy");
    require(audit.work_dissipation_residual <= tolerance,
            "post-remesh work-dissipation residual mismatch");
    require(audit.net_displacement_residual <= tolerance,
            "post-remesh active step translated the centroid");
    for(std::size_t index = 0; index < before_mesh.vertices.size(); ++index) {
        const auto& before_vertex = before_mesh.vertices[index];
        const auto& after_vertex = after_mesh.vertices[index];
        require(after_vertex.persistent_id == before_vertex.persistent_id,
                "post-remesh active step changed persistent identity");
        const auto force = active_force_for(before_active, before_vertex.persistent_id);
        for(std::size_t component = 0; component < 3; ++component) {
            const double expected_position = before_vertex.position[component]
                + time_step * force[component] / damping;
            require(nearly_equal(after_vertex.position[component], expected_position),
                    "post-remesh active-step displacement mismatch");
        }
    }
    for(const node& current_node : current_cell->get_node_lst()) {
        if(!current_node.is_used()) continue;
        require(nearly_equal(current_node.force().norm(), 0.0),
                "post-remesh active step did not reset a force buffer");
    }
    return 0;
}

} // namespace

int main(const int argc, const char* const argv[]) {
    try {
        if(argc != 2) throw std::invalid_argument("one behavior name is required");
        const std::string behavior = argv[1];
        if(behavior == "single_step_accumulation") {
            return active_force_accumulates_into_the_real_cell_buffer();
        }
        if(behavior == "failure_atomicity") {
            return rejected_force_injection_leaves_the_real_cell_buffer_unchanged();
        }
        if(behavior == "post_remesh_revision") {
            return active_force_assembly_tracks_the_post_remesh_revision();
        }
        if(behavior == "overdamped_single_step") {
            return one_overdamped_step_moves_the_real_cell_down_active_energy();
        }
        if(behavior == "overdamped_failure_atomicity") {
            return rejected_active_overdamped_step_is_atomic();
        }
        if(behavior == "overdamped_post_remesh") {
            return active_overdamped_step_tracks_the_post_remesh_revision();
        }
        throw std::invalid_argument("unknown behavior: " + behavior);
    } catch(const std::exception& error) {
        std::cerr << "prl_cell_engine_active_force_assembly_integration_test: "
                  << error.what() << '\n';
        return 1;
    }
}
