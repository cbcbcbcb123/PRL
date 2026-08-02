#include "prl/core/active_myocardial_mechanics.hpp"
#include "prl/core/myocardial_material_transfer.hpp"
#include "prl_cell_engine/cell_surface_snapshot.hpp"

#include "cell.hpp"
#include "edge.hpp"
#include "local_mesh_refiner.hpp"

#include <cassert>
#include <cmath>
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
    assert(failure_propagated);
    assert(current_cell->get_mesh_revision() == 1);
    assert(sink->cell_state(17).revision == 0);

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
    return 1;
}
