#include "prl/core/myocardial_material_transfer.hpp"

#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <future>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

using prl::core::CellId;
using prl::core::MaterialPointId;
using prl::core::MeshRevision;
using prl::core::MyocardialCellMaterialState;
using prl::core::MyocardialMaterialState;
using prl::core::MyocardialMaterialTransferSink;
using prl::core::RemeshEvent;
using prl::core::RemeshOperation;
using prl::core::SurfaceFace;
using prl::core::SurfaceMaterialPoint;
using prl::core::SurfaceMeshSnapshot;
using prl::core::SurfaceRegion;
using prl::core::SurfaceVertex;

constexpr double tolerance = 1.0e-12;

SurfaceMeshSnapshot old_mesh() {
    return {
        17,
        41,
        {
            SurfaceVertex{10, {0.0, 0.0, 0.0}},
            SurfaceVertex{11, {1.0, 0.0, 0.0}},
            SurfaceVertex{12, {1.0, 1.0, 0.0}},
            SurfaceVertex{13, {0.0, 1.0, 0.0}},
        },
        {
            SurfaceFace{{0, 1, 2}},
            SurfaceFace{{0, 2, 3}},
        },
    };
}

SurfaceMeshSnapshot swapped_mesh() {
    auto mesh = old_mesh();
    mesh.revision = 42;
    mesh.faces = {
        SurfaceFace{{0, 1, 3}},
        SurfaceFace{{1, 2, 3}},
    };
    return mesh;
}

SurfaceMeshSnapshot split_mesh() {
    auto mesh = old_mesh();
    mesh.revision = 42;
    mesh.vertices.push_back(SurfaceVertex{14, {0.5, 0.5, 0.0}});
    mesh.faces = {
        SurfaceFace{{0, 1, 4}},
        SurfaceFace{{1, 2, 4}},
        SurfaceFace{{0, 4, 3}},
        SurfaceFace{{4, 2, 3}},
    };
    return mesh;
}

SurfaceMeshSnapshot merged_mesh() {
    auto mesh = old_mesh();
    mesh.revision = 43;
    return mesh;
}

SurfaceMeshSnapshot shifted_swapped_mesh() {
    auto mesh = swapped_mesh();
    for(auto& vertex : mesh.vertices) vertex.position[2] = 1.0e-4;
    return mesh;
}

SurfaceMeshSnapshot reordered_old_mesh() {
    return {
        17,
        41,
        {
            SurfaceVertex{12, {1.0, 1.0, 0.0}},
            SurfaceVertex{10, {0.0, 0.0, 0.0}},
            SurfaceVertex{13, {0.0, 1.0, 0.0}},
            SurfaceVertex{11, {1.0, 0.0, 0.0}},
        },
        {
            SurfaceFace{{1, 3, 0}},
            SurfaceFace{{1, 0, 2}},
        },
    };
}

SurfaceMeshSnapshot reordered_swapped_mesh() {
    auto mesh = reordered_old_mesh();
    mesh.revision = 42;
    mesh.faces = {
        SurfaceFace{{1, 3, 2}},
        SurfaceFace{{3, 0, 2}},
    };
    return mesh;
}

SurfaceMeshSnapshot tilted_swapped_mesh() {
    auto mesh = swapped_mesh();
    mesh.vertices[2].position[2] = 0.04;
    mesh.vertices[3].position[2] = 0.02;
    return mesh;
}

SurfaceMeshSnapshot mesh_for_cell(SurfaceMeshSnapshot mesh, const CellId cell_id) {
    mesh.cell_id = cell_id;
    return mesh;
}

std::vector<SurfaceMaterialPoint> material_points() {
    return {
        {
            MyocardialMaterialState{101, SurfaceRegion::apical, {1.0, 0.0, 0.0}, {0.2, 0.3}},
            {10, 11, 12},
            {0.2, 0.3, 0.5},
            0.17,
        },
        {
            MyocardialMaterialState{205, SurfaceRegion::basal, {0.0, 1.0, 0.0}, {0.4, 0.7}},
            {10, 12, 13},
            {0.4, 0.25, 0.35},
            0.23,
        },
        {
            MyocardialMaterialState{999, SurfaceRegion::lateral, {0.6, 0.8, 0.0}, {0.9, -0.1}},
            {10, 12, 13},
            {0.7, 0.2, 0.1},
            0.11,
        },
    };
}

const SurfaceMaterialPoint& point_with_id(
    const MyocardialCellMaterialState& state,
    const MaterialPointId id
) {
    const auto point = std::find_if(
        state.points.begin(),
        state.points.end(),
        [id](const SurfaceMaterialPoint& candidate) {
            return candidate.material.material_point_id == id;
        }
    );
    assert(point != state.points.end());
    return *point;
}

bool nearly_equal(const double left, const double right) {
    return std::abs(left - right) <= tolerance;
}

std::array<double, 3> subtract_vectors(
    const std::array<double, 3>& left,
    const std::array<double, 3>& right
) {
    return {left[0] - right[0], left[1] - right[1], left[2] - right[2]};
}

std::array<double, 3> cross_product(
    const std::array<double, 3>& left,
    const std::array<double, 3>& right
) {
    return {
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    };
}

double dot_product(
    const std::array<double, 3>& left,
    const std::array<double, 3>& right
) {
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2];
}

std::array<double, 3> vertex_position(
    const SurfaceMeshSnapshot& mesh,
    const std::uint64_t persistent_id
) {
    const auto vertex = std::find_if(
        mesh.vertices.begin(),
        mesh.vertices.end(),
        [persistent_id](const SurfaceVertex& candidate) {
            return candidate.persistent_id == persistent_id;
        }
    );
    assert(vertex != mesh.vertices.end());
    return vertex->position;
}

std::array<double, 3> host_unit_normal(
    const SurfaceMeshSnapshot& mesh,
    const SurfaceMaterialPoint& point
) {
    const auto a = vertex_position(mesh, point.host_vertex_ids[0]);
    const auto b = vertex_position(mesh, point.host_vertex_ids[1]);
    const auto c = vertex_position(mesh, point.host_vertex_ids[2]);
    auto normal = cross_product(subtract_vectors(b, a), subtract_vectors(c, a));
    const double length = std::sqrt(dot_product(normal, normal));
    for(double& component : normal) component /= length;
    return normal;
}

int edge_swap_preserves_material_state() {
    MyocardialMaterialTransferSink sink(tolerance);
    sink.register_cell(old_mesh(), material_points());
    sink.on_remesh(
        RemeshEvent{17, RemeshOperation::edge_swap, 41, 42},
        old_mesh(),
        swapped_mesh()
    );

    const auto state = sink.cell_state(17);
    assert(state.cell_id == 17);
    assert(state.revision == 42);
    assert(state.points.size() == 3);

    const auto& apical = point_with_id(state, 101);
    const auto& basal = point_with_id(state, 205);
    const auto& lateral = point_with_id(state, 999);
    assert(apical.material.region == SurfaceRegion::apical);
    assert(basal.material.region == SurfaceRegion::basal);
    assert(lateral.material.region == SurfaceRegion::lateral);
    assert(apical.material.active_state == std::vector<double>({0.2, 0.3}));
    assert(basal.material.active_state == std::vector<double>({0.4, 0.7}));
    assert(lateral.material.active_state == std::vector<double>({0.9, -0.1}));
    assert(nearly_equal(apical.reference_weight, 0.17));
    assert(nearly_equal(basal.reference_weight, 0.23));
    assert(nearly_equal(lateral.reference_weight, 0.11));

    const auto audit = sink.last_audit(17);
    assert(audit.operation == RemeshOperation::edge_swap);
    assert(audit.point_count == 3);
    assert(nearly_equal(audit.region_retention_fraction, 1.0));
    assert(nearly_equal(audit.active_state_residual, 0.0));
    assert(audit.maximum_fiber_norm_error <= tolerance);
    assert(audit.maximum_fiber_tangency_error <= tolerance);
    assert(audit.minimum_fiber_alignment >= 1.0 - tolerance);
    assert(audit.maximum_rebind_error <= tolerance);
    assert(nearly_equal(audit.id_retention_fraction, 1.0));
    assert(nearly_equal(audit.reference_weight_residual, 0.0));
    return 0;
}

int edge_split_preserves_material_state() {
    MyocardialMaterialTransferSink sink(tolerance);
    sink.register_cell(old_mesh(), material_points());
    sink.on_remesh(
        RemeshEvent{17, RemeshOperation::edge_split, 41, 42},
        old_mesh(),
        split_mesh()
    );

    const auto state = sink.cell_state(17);
    assert(state.revision == 42);
    assert(state.points.size() == 3);
    assert(point_with_id(state, 101).material.active_state == std::vector<double>({0.2, 0.3}));
    assert(point_with_id(state, 205).material.region == SurfaceRegion::basal);
    assert(point_with_id(state, 999).material.region == SurfaceRegion::lateral);
    const auto audit = sink.last_audit(17);
    assert(audit.operation == RemeshOperation::edge_split);
    assert(audit.point_count == 3);
    assert(nearly_equal(audit.region_retention_fraction, 1.0));
    assert(nearly_equal(audit.active_state_residual, 0.0));
    assert(audit.maximum_rebind_error <= tolerance);
    assert(audit.maximum_fiber_tangency_error <= tolerance);
    assert(audit.minimum_fiber_alignment >= 1.0 - tolerance);
    return 0;
}

int edge_merge_preserves_material_state() {
    MyocardialMaterialTransferSink sink(tolerance);
    sink.register_cell(old_mesh(), material_points());
    sink.on_remesh(
        RemeshEvent{17, RemeshOperation::edge_split, 41, 42},
        old_mesh(),
        split_mesh()
    );
    sink.on_remesh(
        RemeshEvent{17, RemeshOperation::edge_merge, 42, 43},
        split_mesh(),
        merged_mesh()
    );

    const auto state = sink.cell_state(17);
    assert(state.revision == 43);
    assert(state.points.size() == 3);
    assert(point_with_id(state, 101).material.region == SurfaceRegion::apical);
    assert(point_with_id(state, 205).material.active_state == std::vector<double>({0.4, 0.7}));
    assert(nearly_equal(point_with_id(state, 999).reference_weight, 0.11));
    const auto audit = sink.last_audit(17);
    assert(audit.operation == RemeshOperation::edge_merge);
    assert(audit.point_count == 3);
    assert(nearly_equal(audit.region_retention_fraction, 1.0));
    assert(nearly_equal(audit.active_state_residual, 0.0));
    assert(audit.maximum_rebind_error <= tolerance);
    assert(audit.maximum_fiber_norm_error <= tolerance);
    assert(audit.maximum_fiber_tangency_error <= tolerance);
    assert(audit.minimum_fiber_alignment >= 1.0 - tolerance);
    return 0;
}

int failed_transfer_is_atomic_and_identifies_point() {
    MyocardialMaterialTransferSink sink(1.0e-8);
    sink.register_cell(old_mesh(), material_points());

    bool identified_point = false;
    try {
        sink.on_remesh(
            RemeshEvent{17, RemeshOperation::edge_swap, 41, 42},
            old_mesh(),
            shifted_swapped_mesh()
        );
    } catch(const std::runtime_error& error) {
        const std::string message = error.what();
        identified_point = message.find("id=101") != std::string::npos
            && message.find("distance=") != std::string::npos;
    }
    assert(identified_point);

    const auto state = sink.cell_state(17);
    assert(state.revision == 41);
    assert(state.points.size() == 3);
    bool audit_absent = false;
    try {
        static_cast<void>(sink.last_audit(17));
    } catch(const std::logic_error&) {
        audit_absent = true;
    }
    assert(audit_absent);
    return 0;
}

int stable_host_ids_survive_local_reordering() {
    MyocardialMaterialTransferSink sink(tolerance);
    sink.register_cell(old_mesh(), material_points());
    sink.on_remesh(
        RemeshEvent{17, RemeshOperation::edge_swap, 41, 42},
        reordered_old_mesh(),
        reordered_swapped_mesh()
    );

    const auto state = sink.cell_state(17);
    assert(state.revision == 42);
    assert(state.points.size() == 3);
    assert(point_with_id(state, 101).material.region == SurfaceRegion::apical);
    assert(point_with_id(state, 205).material.active_state == std::vector<double>({0.4, 0.7}));
    assert(sink.last_audit(17).maximum_rebind_error <= tolerance);
    return 0;
}

int fibers_are_projected_to_the_new_host_tangent_plane() {
    MyocardialMaterialTransferSink sink(0.05);
    sink.register_cell(old_mesh(), material_points());
    const auto after = tilted_swapped_mesh();
    sink.on_remesh(
        RemeshEvent{17, RemeshOperation::edge_swap, 41, 42},
        old_mesh(),
        after
    );

    const auto state = sink.cell_state(17);
    for(const auto& point : state.points) {
        const auto normal = host_unit_normal(after, point);
        const auto& fiber = point.material.fiber_direction;
        assert(nearly_equal(std::sqrt(dot_product(fiber, fiber)), 1.0));
        assert(std::abs(dot_product(fiber, normal)) <= tolerance);
    }
    const auto audit = sink.last_audit(17);
    assert(audit.maximum_rebind_error > 0.0);
    assert(audit.maximum_rebind_error <= 0.05);
    assert(audit.maximum_fiber_norm_error <= tolerance);
    assert(audit.maximum_fiber_tangency_error <= tolerance);
    assert(audit.minimum_fiber_alignment > 0.99);
    return 0;
}

int different_cells_transfer_concurrently() {
    MyocardialMaterialTransferSink sink(tolerance);
    sink.register_cell(mesh_for_cell(old_mesh(), 17), material_points());
    sink.register_cell(mesh_for_cell(old_mesh(), 18), material_points());

    auto transfer = [&sink](const CellId cell_id) {
        sink.on_remesh(
            RemeshEvent{cell_id, RemeshOperation::edge_swap, 41, 42},
            mesh_for_cell(old_mesh(), cell_id),
            mesh_for_cell(swapped_mesh(), cell_id)
        );
    };
    auto first = std::async(std::launch::async, transfer, 17);
    auto second = std::async(std::launch::async, transfer, 18);
    first.get();
    second.get();

    assert(sink.cell_state(17).revision == 42);
    assert(sink.cell_state(18).revision == 42);
    assert(sink.last_audit(17).point_count == 3);
    assert(sink.last_audit(18).point_count == 3);
    return 0;
}

} // namespace

int main(const int argc, const char* const argv[]) {
    assert(argc == 2);
    const std::string behavior = argv[1];
    if(behavior == "edge_swap") return edge_swap_preserves_material_state();
    if(behavior == "edge_split") return edge_split_preserves_material_state();
    if(behavior == "edge_merge") return edge_merge_preserves_material_state();
    if(behavior == "failure_atomicity") return failed_transfer_is_atomic_and_identifies_point();
    if(behavior == "stable_host_ids") return stable_host_ids_survive_local_reordering();
    if(behavior == "fiber_projection") return fibers_are_projected_to_the_new_host_tangent_plane();
    if(behavior == "multicell_concurrency") return different_cells_transfer_concurrently();
    return 1;
}
