#include "prl/core/active_myocardial_mechanics.hpp"
#include "prl/core/myocardial_material_transfer.hpp"
#include "prl_cell_engine/cell_surface_snapshot.hpp"

#include "cell.hpp"
#include "custom_structures.hpp"
#include "edge.hpp"
#include "face.hpp"
#include "local_mesh_refiner.hpp"
#include "node.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace {

using Vector3 = std::array<double, 3>;
using PersistentFace = std::array<prl::core::VertexId, 3>;

constexpr double tolerance = 1.0e-12;

void require(const bool condition, const char* const message) {
    if(!condition) throw std::runtime_error(message);
}

Vector3 subtract(const Vector3& left, const Vector3& right) noexcept {
    return {left[0] - right[0], left[1] - right[1], left[2] - right[2]};
}

Vector3 add(const Vector3& left, const Vector3& right) noexcept {
    return {left[0] + right[0], left[1] + right[1], left[2] + right[2]};
}

Vector3 scale(const Vector3& value, const double factor) noexcept {
    return {factor * value[0], factor * value[1], factor * value[2]};
}

Vector3 cross(const Vector3& left, const Vector3& right) noexcept {
    return {
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    };
}

double dot(const Vector3& left, const Vector3& right) noexcept {
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2];
}

double norm(const Vector3& value) noexcept {
    return std::sqrt(dot(value, value));
}

bool finite_vector(const Vector3& value) noexcept {
    return std::all_of(value.begin(), value.end(), [](const double component) {
        return std::isfinite(component);
    });
}

std::shared_ptr<cell_type_parameters> zero_passive_cell_type() {
    face_type_parameters face_type;
    face_type.name_ = "v10_zero_passive_surface";
    face_type.face_type_global_id_ = 0;
    face_type.surface_tension_ = 0.0;
    face_type.adherence_strength_ = 0.0;
    face_type.repulsion_strength_ = 0.0;
    face_type.bending_modulus_ = 0.0;

    auto result = std::make_shared<cell_type_parameters>();
    result->name_ = "v10_midpoint_probe_cell";
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

cell_ptr probe_cell() {
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

prl::core::MyocardialCellMaterialState probe_material(const cell& current_cell) {
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

struct Geometry {
    double area{};
    double volume{};
    Vector3 centroid{};
    double minimum_face_area{std::numeric_limits<double>::infinity()};
    double minimum_quality{1.0};
    double minimum_orientation_alignment{1.0};
};

struct FaceReference {
    PersistentFace vertex_ids{};
    Vector3 oriented{};
};

std::vector<FaceReference> face_references(
    const prl::core::SurfaceMeshSnapshot& snapshot
) {
    std::vector<FaceReference> result;
    result.reserve(snapshot.faces.size());
    for(const auto& current_face : snapshot.faces) {
        const auto& a = snapshot.vertices.at(current_face.vertex_indices[0]);
        const auto& b = snapshot.vertices.at(current_face.vertex_indices[1]);
        const auto& c = snapshot.vertices.at(current_face.vertex_indices[2]);
        result.push_back({
            {a.persistent_id, b.persistent_id, c.persistent_id},
            cross(subtract(b.position, a.position), subtract(c.position, a.position)),
        });
    }
    return result;
}

bool contains_id(const PersistentFace& face_ids, const prl::core::VertexId id) {
    return std::find(face_ids.begin(), face_ids.end(), id) != face_ids.end();
}

Geometry independent_geometry(
    const prl::core::SurfaceMeshSnapshot& snapshot,
    const std::vector<FaceReference>& references
) {
    std::set<prl::core::VertexId> reference_ids;
    for(const auto& reference : references) {
        reference_ids.insert(reference.vertex_ids.begin(), reference.vertex_ids.end());
    }
    Geometry result;
    double signed_six_volume = 0.0;
    for(const auto& current_face : snapshot.faces) {
        const auto& a = snapshot.vertices.at(current_face.vertex_indices[0]);
        const auto& b = snapshot.vertices.at(current_face.vertex_indices[1]);
        const auto& c = snapshot.vertices.at(current_face.vertex_indices[2]);
        const auto ab = subtract(b.position, a.position);
        const auto ac = subtract(c.position, a.position);
        const auto bc = subtract(c.position, b.position);
        const auto oriented = cross(ab, ac);
        const double twice_area = norm(oriented);
        const double area = 0.5 * twice_area;
        const double edge_square_sum = dot(ab, ab) + dot(ac, ac) + dot(bc, bc);
        const double quality = 2.0 * std::sqrt(3.0) * twice_area / edge_square_sum;
        if(!std::isfinite(area) || area <= 0.0
           || !std::isfinite(quality) || quality <= 0.0) {
            throw std::runtime_error("v10 geometry contains a degenerate face");
        }
        result.area += area;
        result.minimum_face_area = std::min(result.minimum_face_area, area);
        result.minimum_quality = std::min(result.minimum_quality, quality);
        for(std::size_t component = 0; component < 3; ++component) {
            result.centroid[component] += area
                * (a.position[component] + b.position[component]
                   + c.position[component]) / 3.0;
        }
        signed_six_volume += dot(a.position, cross(b.position, c.position));

        std::vector<prl::core::VertexId> retained;
        for(const auto* vertex : {&a, &b, &c}) {
            if(reference_ids.count(vertex->persistent_id) != 0) {
                retained.push_back(vertex->persistent_id);
            }
        }
        double selected = -std::numeric_limits<double>::infinity();
        double selected_absolute = -1.0;
        for(const auto& reference : references) {
            if(!std::all_of(retained.begin(), retained.end(), [&](const auto id) {
                return contains_id(reference.vertex_ids, id);
            })) {
                continue;
            }
            const double alignment = dot(reference.oriented, oriented)
                / (norm(reference.oriented) * twice_area);
            if(std::abs(alignment) > selected_absolute) {
                selected = alignment;
                selected_absolute = std::abs(alignment);
            }
        }
        if(!std::isfinite(selected)) {
            throw std::runtime_error("v10 face has no orientation ancestor");
        }
        result.minimum_orientation_alignment = std::min(
            result.minimum_orientation_alignment,
            selected
        );
    }
    if(!std::isfinite(result.area) || result.area <= 0.0) {
        throw std::runtime_error("v10 surface area is invalid");
    }
    for(double& component : result.centroid) component /= result.area;
    result.volume = std::abs(signed_six_volume) / 6.0;
    if(!std::isfinite(result.volume) || result.volume <= 0.0
       || !finite_vector(result.centroid)) {
        throw std::runtime_error("v10 geometry is non-finite");
    }
    return result;
}

struct Qoi {
    double axis_length{};
    double active_energy{};
};

Qoi evaluate_qoi(
    const prl::core::SurfaceMeshSnapshot& snapshot,
    const prl::core::MyocardialCellMaterialState& material,
    const prl::core::ActiveContractionUnit& unit
) {
    const auto active = prl::core::evaluate_active_contraction(
        snapshot,
        material,
        {unit}
    );
    require(active.unit_states.size() == 1, "v10 active unit count changed");
    return {active.unit_states.front().length, active.audit.total_energy};
}

std::map<prl::core::VertexId, Vector3> positions_by_id(
    const prl::core::SurfaceMeshSnapshot& snapshot
) {
    std::map<prl::core::VertexId, Vector3> result;
    for(const auto& vertex : snapshot.vertices) {
        result.emplace(vertex.persistent_id, vertex.position);
    }
    return result;
}

std::set<PersistentFace> persistent_faces(
    const prl::core::SurfaceMeshSnapshot& snapshot
) {
    std::set<PersistentFace> result;
    for(const auto& current_face : snapshot.faces) {
        PersistentFace ids{
            snapshot.vertices.at(current_face.vertex_indices[0]).persistent_id,
            snapshot.vertices.at(current_face.vertex_indices[1]).persistent_id,
            snapshot.vertices.at(current_face.vertex_indices[2]).persistent_id,
        };
        std::sort(ids.begin(), ids.end());
        result.emplace(ids);
    }
    return result;
}

bool all_edges_manifold(const cell& current_cell) {
    return std::all_of(
        current_cell.get_edge_set().begin(),
        current_cell.get_edge_set().end(),
        [](const edge& current_edge) { return current_edge.is_manifold(); }
    );
}

long long euler_characteristic(const cell& current_cell) {
    return static_cast<long long>(current_cell.get_nb_of_nodes())
        - static_cast<long long>(current_cell.get_edge_set().size())
        + static_cast<long long>(current_cell.get_nb_of_faces());
}

std::string bool_text(const bool value) {
    return value ? "true" : "false";
}

void emit_stage(
    const std::string& branch,
    const std::string& stage,
    const cell& current_cell,
    const prl::core::MyocardialCellMaterialState& material,
    const prl::core::ActiveContractionUnit& unit,
    const std::vector<FaceReference>& references
) {
    const auto snapshot = prl::cell_engine::capture_surface_snapshot(current_cell);
    const auto geometry = independent_geometry(snapshot, references);
    const auto qoi = evaluate_qoi(snapshot, material, unit);
    std::cout << "v10_stage,branch," << branch
              << ",stage," << stage
              << ",revision," << snapshot.revision
              << ",vertex_count," << snapshot.vertices.size()
              << ",edge_count," << current_cell.get_edge_set().size()
              << ",face_count," << snapshot.faces.size()
              << ",euler," << euler_characteristic(current_cell)
              << ",all_edges_manifold," << bool_text(all_edges_manifold(current_cell))
              << ",area," << geometry.area
              << ",volume," << geometry.volume
              << ",centroid_x," << geometry.centroid[0]
              << ",centroid_y," << geometry.centroid[1]
              << ",centroid_z," << geometry.centroid[2]
              << ",minimum_face_area," << geometry.minimum_face_area
              << ",minimum_quality," << geometry.minimum_quality
              << ",minimum_orientation_alignment,"
              << geometry.minimum_orientation_alignment
              << ",axis_length," << qoi.axis_length
              << ",active_energy," << qoi.active_energy
              << '\n';

    for(const node& current_node : current_cell.get_node_lst()) {
        if(!current_node.is_used()) continue;
        std::cout << "v10_vertex,branch," << branch
                  << ",stage," << stage
                  << ",local_id," << current_node.get_local_id()
                  << ",persistent_id," << current_node.get_persistent_id()
                  << ",x," << current_node.pos().dx()
                  << ",y," << current_node.pos().dy()
                  << ",z," << current_node.pos().dz()
                  << '\n';
    }
    for(const face& current_face : current_cell.get_face_lst()) {
        if(!current_face.is_used()) continue;
        const auto local_ids = current_face.get_node_ids();
        std::cout << "v10_face,branch," << branch
                  << ",stage," << stage
                  << ",local_face_id," << current_face.get_local_id()
                  << ",local_0," << local_ids[0]
                  << ",local_1," << local_ids[1]
                  << ",local_2," << local_ids[2]
                  << ",persistent_0," << persistent_node_id(current_cell, local_ids[0])
                  << ",persistent_1," << persistent_node_id(current_cell, local_ids[1])
                  << ",persistent_2," << persistent_node_id(current_cell, local_ids[2])
                  << '\n';
    }
    std::size_t edge_index = 0;
    for(const edge& current_edge : current_cell.get_edge_set()) {
        std::cout << "v10_edge,branch," << branch
                  << ",stage," << stage
                  << ",edge_index," << edge_index++
                  << ",local_0," << current_edge.n1()
                  << ",local_1," << current_edge.n2()
                  << ",persistent_0,"
                  << persistent_node_id(current_cell, current_edge.n1())
                  << ",persistent_1,"
                  << persistent_node_id(current_cell, current_edge.n2())
                  << ",face_0," << current_edge.f1()
                  << ",face_1," << current_edge.f2()
                  << ",manifold," << bool_text(current_edge.is_manifold())
                  << '\n';
    }
    for(const auto& point : material.points) {
        std::cout << "v10_material,branch," << branch
                  << ",stage," << stage
                  << ",material_point_id," << point.material.material_point_id
                  << ",host_0," << point.host_vertex_ids[0]
                  << ",host_1," << point.host_vertex_ids[1]
                  << ",host_2," << point.host_vertex_ids[2]
                  << ",barycentric_0," << point.barycentric[0]
                  << ",barycentric_1," << point.barycentric[1]
                  << ",barycentric_2," << point.barycentric[2]
                  << ",fiber_x," << point.material.fiber_direction[0]
                  << ",fiber_y," << point.material.fiber_direction[1]
                  << ",fiber_z," << point.material.fiber_direction[2]
                  << '\n';
    }
}

struct Fixture {
    cell_ptr target{};
    std::shared_ptr<prl::core::MyocardialMaterialTransferSink> sink{};
    prl::core::MyocardialCellMaterialState initial_material{};
    prl::core::ActiveContractionUnit unit{};
    prl::core::SurfaceMeshSnapshot initial_snapshot{};
    std::vector<FaceReference> initial_references{};
};

Fixture fixture() {
    Fixture result;
    result.target = probe_cell();
    result.initial_snapshot = prl::cell_engine::capture_surface_snapshot(*result.target);
    result.initial_material = probe_material(*result.target);
    result.unit = prl::core::build_active_contraction_unit(
        result.initial_snapshot,
        result.initial_material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );
    result.initial_references = face_references(result.initial_snapshot);
    result.sink = std::make_shared<prl::core::MyocardialMaterialTransferSink>(
        tolerance
    );
    result.sink->register_cell(
        result.initial_snapshot,
        result.initial_material.points
    );
    result.sink->begin_active_remesh_energy_ledger(
        result.initial_snapshot,
        {result.unit}
    );
    return result;
}

unsigned split_original_edge(
    Fixture& current,
    local_mesh_refiner& refiner,
    edge_set& edges_to_check,
    const std::string& branch
) {
    const auto original = current.target->get_edge_set().find(edge(0, 1));
    require(original != current.target->get_edge_set().end(),
            "v10 original split edge is missing");
    refiner.split_edge(
        const_cast<edge&>(*original),
        current.target,
        edges_to_check
    );
    const unsigned split_local = static_cast<unsigned>(
        current.target->get_node_lst().size() - 1
    );
    const auto defect = current.sink->last_remesh_energy_defect(17);
    const auto transfer = current.sink->last_audit(17);
    std::cout << "v10_event,branch," << branch
              << ",action_id,split_original_0_1"
              << ",parent_action_id,root"
              << ",operation,edge_split"
              << ",input_local_0,0,input_local_1,1"
              << ",before_revision," << defect.before_revision
              << ",after_revision," << defect.after_revision
              << ",new_local_id," << split_local
              << ",new_persistent_id," << persistent_node_id(*current.target, split_local)
              << ",minimum_fiber_alignment," << transfer.minimum_fiber_alignment
              << ",maximum_rebind_error," << transfer.maximum_rebind_error
              << '\n';
    return split_local;
}

struct DifferenceSet {
    std::vector<prl::core::VertexId> deleted{};
    std::vector<prl::core::VertexId> created{};
};

DifferenceSet vertex_difference(
    const prl::core::SurfaceMeshSnapshot& before,
    const prl::core::SurfaceMeshSnapshot& after
) {
    const auto before_positions = positions_by_id(before);
    const auto after_positions = positions_by_id(after);
    DifferenceSet result;
    for(const auto& [id, position] : before_positions) {
        static_cast<void>(position);
        if(after_positions.count(id) == 0) result.deleted.push_back(id);
    }
    for(const auto& [id, position] : after_positions) {
        static_cast<void>(position);
        if(before_positions.count(id) == 0) result.created.push_back(id);
    }
    return result;
}

Vector3 position_of_local(const cell& current_cell, const unsigned local_id) {
    const auto& current_node = current_cell.get_node_lst().at(local_id);
    require(current_node.is_used(), "v10 requested an unused local node");
    return {
        current_node.pos().dx(),
        current_node.pos().dy(),
        current_node.pos().dz(),
    };
}

double normalized_position_recovery_error(
    const prl::core::SurfaceMeshSnapshot& initial,
    const prl::core::SurfaceMeshSnapshot& candidate,
    const double length_scale
) {
    const auto initial_positions = positions_by_id(initial);
    const auto candidate_positions = positions_by_id(candidate);
    if(initial_positions.size() != candidate_positions.size()) {
        return std::numeric_limits<double>::infinity();
    }
    double result = 0.0;
    for(const auto& [id, position] : initial_positions) {
        const auto found = candidate_positions.find(id);
        if(found == candidate_positions.end()) {
            return std::numeric_limits<double>::infinity();
        }
        result = std::max(result, norm(subtract(found->second, position)) / length_scale);
    }
    return result;
}

double normalized_original_vertex_position_error(
    const prl::core::SurfaceMeshSnapshot& initial,
    const prl::core::SurfaceMeshSnapshot& candidate,
    const double length_scale
) {
    const auto initial_positions = positions_by_id(initial);
    const auto candidate_positions = positions_by_id(candidate);
    double result = 0.0;
    for(const auto& [id, position] : initial_positions) {
        const auto found = candidate_positions.find(id);
        if(found == candidate_positions.end()) {
            return std::numeric_limits<double>::infinity();
        }
        result = std::max(result, norm(subtract(found->second, position)) / length_scale);
    }
    return result;
}

std::string finite_or_inf(const double value) {
    if(std::isfinite(value)) {
        std::ostringstream stream;
        stream << std::setprecision(17) << value;
        return stream.str();
    }
    return "inf";
}

struct CandidateKey {
    unsigned local_0{};
    unsigned local_1{};

    bool operator<(const CandidateKey& other) const noexcept {
        return std::tie(local_0, local_1) < std::tie(other.local_0, other.local_1);
    }
};

std::vector<CandidateKey> discover_candidates() {
    auto current = fixture();
    local_mesh_refiner refiner(0.1, 10.0, true, current.sink);
    edge_set edges_to_check;
    const unsigned split_local = split_original_edge(
        current,
        refiner,
        edges_to_check,
        "candidate_discovery"
    );
    std::vector<CandidateKey> result;
    for(const edge& current_edge : current.target->get_edge_set()) {
        if(!current_edge.has_node(split_local)) continue;
        unsigned first = current_edge.n1();
        unsigned second = current_edge.n2();
        if(first > second) std::swap(first, second);
        result.push_back({first, second});
    }
    std::sort(result.begin(), result.end());
    return result;
}

struct CandidateResult {
    std::size_t candidate_id{};
    CandidateKey key{};
    bool can_merge{};
    bool merge_succeeded{};
    bool topology_legal{};
    bool geometric_inverse{};
    double analytic_residual{std::numeric_limits<double>::infinity()};
    std::string failure_reason{};
};

CandidateResult run_candidate(
    const CandidateKey key,
    const std::size_t candidate_id
) {
    auto current = fixture();
    const auto initial_geometry = independent_geometry(
        current.initial_snapshot,
        current.initial_references
    );
    const auto initial_qoi = evaluate_qoi(
        current.initial_snapshot,
        current.initial_material,
        current.unit
    );
    const double length_scale = std::cbrt(initial_geometry.volume);
    local_mesh_refiner refiner(0.1, 10.0, true, current.sink);
    edge_set edges_to_check;
    const unsigned split_local = split_original_edge(
        current,
        refiner,
        edges_to_check,
        "candidate_" + std::to_string(candidate_id)
    );
    require(key.local_0 == split_local || key.local_1 == split_local,
            "v10 candidate is not adjacent to the split node");
    const auto candidate_iterator = current.target->get_edge_set().find(
        edge(key.local_0, key.local_1)
    );
    require(candidate_iterator != current.target->get_edge_set().end(),
            "v10 candidate edge is absent after replayed split");
    auto& candidate_edge = const_cast<edge&>(*candidate_iterator);
    CandidateResult result;
    result.candidate_id = candidate_id;
    result.key = key;
    result.can_merge = refiner.can_be_merged(candidate_edge, current.target);
    const auto before = prl::cell_engine::capture_surface_snapshot(*current.target);
    const auto before_material = current.sink->cell_state(17);
    const auto before_geometry = independent_geometry(before, current.initial_references);
    const auto before_qoi = evaluate_qoi(before, before_material, current.unit);
    const auto endpoint_0 = position_of_local(*current.target, key.local_0);
    const auto endpoint_1 = position_of_local(*current.target, key.local_1);
    const auto analytic = scale(add(endpoint_0, endpoint_1), 0.5);
    const auto persistent_0 = persistent_node_id(*current.target, key.local_0);
    const auto persistent_1 = persistent_node_id(*current.target, key.local_1);
    const bool original_half_edge = (key.local_0 == 0 && key.local_1 == split_local)
        || (key.local_0 == 1 && key.local_1 == split_local);

    if(!result.can_merge) {
        std::cout << "v10_candidate,candidate_id," << candidate_id
                  << ",local_0," << key.local_0
                  << ",local_1," << key.local_1
                  << ",persistent_0," << persistent_0
                  << ",persistent_1," << persistent_1
                  << ",original_half_edge," << bool_text(original_half_edge)
                  << ",can_be_merged,false,merge_succeeded,false"
                  << ",collapse_x," << analytic[0]
                  << ",collapse_y," << analytic[1]
                  << ",collapse_z," << analytic[2]
                  << ",topology_legal,false,geometric_inverse,false"
                  << '\n';
        return result;
    }

    try {
        refiner.merge_edge(candidate_edge, current.target, edges_to_check);
        result.merge_succeeded = true;
    } catch(const std::exception& error) {
        std::string reason = error.what();
        result.failure_reason = reason;
        std::replace(reason.begin(), reason.end(), ',', ';');
        std::cout << "v10_candidate,candidate_id," << candidate_id
                  << ",local_0," << key.local_0
                  << ",local_1," << key.local_1
                  << ",persistent_0," << persistent_0
                  << ",persistent_1," << persistent_1
                  << ",original_half_edge," << bool_text(original_half_edge)
                  << ",can_be_merged,true,merge_succeeded,false"
                  << ",collapse_x," << analytic[0]
                  << ",collapse_y," << analytic[1]
                  << ",collapse_z," << analytic[2]
                  << ",topology_legal,false,geometric_inverse,false"
                  << ",exception," << reason
                  << '\n';
        return result;
    }

    const auto after = prl::cell_engine::capture_surface_snapshot(*current.target);
    const auto after_material = current.sink->cell_state(17);
    const auto after_geometry = independent_geometry(after, face_references(before));
    const auto after_qoi = evaluate_qoi(after, after_material, current.unit);
    const auto difference = vertex_difference(before, after);
    require(difference.deleted.size() == 2 && difference.created.size() == 1,
            "v10 midpoint merge identity difference is not 2 deleted / 1 created");
    const auto after_positions = positions_by_id(after);
    const auto machine = after_positions.at(difference.created.front());
    result.analytic_residual = norm(subtract(machine, analytic)) / length_scale;
    const double recovery_position_error = normalized_position_recovery_error(
        current.initial_snapshot,
        after,
        length_scale
    );
    const bool face_identity_recovered = persistent_faces(current.initial_snapshot)
        == persistent_faces(after);
    const double recovery_area_error = std::abs(
        after_geometry.area - initial_geometry.area
    ) / initial_geometry.area;
    const double recovery_volume_error = std::abs(
        after_geometry.volume - initial_geometry.volume
    ) / initial_geometry.volume;
    const double recovery_centroid_error = norm(subtract(
        after_geometry.centroid,
        initial_geometry.centroid
    )) / length_scale;
    const double recovery_axis_error = std::abs(
        after_qoi.axis_length - initial_qoi.axis_length
    ) / initial_qoi.axis_length;
    const double recovery_energy_error = std::abs(
        after_qoi.active_energy - initial_qoi.active_energy
    ) / initial_qoi.active_energy;
    result.topology_legal = euler_characteristic(*current.target) == 2
        && all_edges_manifold(*current.target)
        && after_geometry.minimum_orientation_alignment > 0.0
        && after_geometry.minimum_quality >= 0.05;
    result.geometric_inverse = recovery_position_error <= tolerance
        && face_identity_recovered
        && recovery_area_error <= tolerance
        && recovery_volume_error <= tolerance
        && recovery_centroid_error <= tolerance
        && recovery_axis_error <= tolerance
        && recovery_energy_error <= tolerance;
    const auto transfer = current.sink->last_audit(17);
    const auto defect = current.sink->last_remesh_energy_defect(17);

    std::cout << "v10_candidate,candidate_id," << candidate_id
              << ",local_0," << key.local_0
              << ",local_1," << key.local_1
              << ",persistent_0," << persistent_0
              << ",persistent_1," << persistent_1
              << ",split_local," << split_local
              << ",original_half_edge," << bool_text(original_half_edge)
              << ",can_be_merged,true,merge_succeeded,true"
              << ",collapse_x," << analytic[0]
              << ",collapse_y," << analytic[1]
              << ",collapse_z," << analytic[2]
              << ",machine_x," << machine[0]
              << ",machine_y," << machine[1]
              << ",machine_z," << machine[2]
              << ",analytic_residual," << result.analytic_residual
              << ",deleted_persistent_0," << difference.deleted[0]
              << ",deleted_persistent_1," << difference.deleted[1]
              << ",created_persistent," << difference.created[0]
              << ",before_revision," << defect.before_revision
              << ",after_revision," << defect.after_revision
              << ",euler," << euler_characteristic(*current.target)
              << ",all_edges_manifold," << bool_text(all_edges_manifold(*current.target))
              << ",minimum_orientation_alignment,"
              << after_geometry.minimum_orientation_alignment
              << ",minimum_quality," << after_geometry.minimum_quality
              << ",centroid_jump," << norm(subtract(
                    after_geometry.centroid, before_geometry.centroid
                 )) / length_scale
              << ",area_jump," << std::abs(
                    after_geometry.area - before_geometry.area
                 ) / initial_geometry.area
              << ",volume_jump," << std::abs(
                    after_geometry.volume - before_geometry.volume
                 ) / initial_geometry.volume
              << ",axis_jump," << std::abs(
                    after_qoi.axis_length - before_qoi.axis_length
                 ) / initial_qoi.axis_length
              << ",active_energy_jump," << std::abs(
                    after_qoi.active_energy - before_qoi.active_energy
                 ) / initial_qoi.active_energy
              << ",recovery_position_error," << finite_or_inf(recovery_position_error)
              << ",face_identity_recovered," << bool_text(face_identity_recovered)
              << ",recovery_area_error," << recovery_area_error
              << ",recovery_volume_error," << recovery_volume_error
              << ",recovery_centroid_error," << recovery_centroid_error
              << ",recovery_axis_error," << recovery_axis_error
              << ",recovery_energy_error," << recovery_energy_error
              << ",minimum_fiber_alignment," << transfer.minimum_fiber_alignment
              << ",maximum_rebind_error," << transfer.maximum_rebind_error
              << ",topology_legal," << bool_text(result.topology_legal)
              << ",geometric_inverse," << bool_text(result.geometric_inverse)
              << '\n';
    std::cout << "v10_event,branch,candidate_" << candidate_id
              << ",action_id,merge_candidate_" << candidate_id
              << ",parent_action_id,split_original_0_1"
              << ",operation,edge_merge"
              << ",input_local_0," << key.local_0
              << ",input_local_1," << key.local_1
              << ",before_revision," << defect.before_revision
              << ",after_revision," << defect.after_revision
              << ",created_persistent_id," << difference.created[0]
              << '\n';
    return result;
}

void run_frozen_main_branch() {
    auto current = fixture();
    const auto initial_geometry = independent_geometry(
        current.initial_snapshot,
        current.initial_references
    );
    const auto initial_qoi = evaluate_qoi(
        current.initial_snapshot,
        current.initial_material,
        current.unit
    );
    const double length_scale = std::cbrt(initial_geometry.volume);
    emit_stage(
        "frozen_main",
        "before_split",
        *current.target,
        current.initial_material,
        current.unit,
        current.initial_references
    );
    const auto x0 = position_of_local(*current.target, 0);
    const auto x1 = position_of_local(*current.target, 1);
    const auto x0_persistent = persistent_node_id(*current.target, 0);
    local_mesh_refiner refiner(0.1, 10.0, true, current.sink);
    edge_set edges_to_check;
    const unsigned split_local = split_original_edge(
        current,
        refiner,
        edges_to_check,
        "frozen_main"
    );
    const auto split_snapshot = prl::cell_engine::capture_surface_snapshot(*current.target);
    const auto split_material = current.sink->cell_state(17);
    const auto split_geometry = independent_geometry(
        split_snapshot,
        current.initial_references
    );
    const auto split_qoi = evaluate_qoi(split_snapshot, split_material, current.unit);
    const auto midpoint = scale(add(x0, x1), 0.5);
    const auto machine_midpoint = position_of_local(*current.target, split_local);
    const double split_midpoint_residual = norm(subtract(
        machine_midpoint,
        midpoint
    )) / length_scale;
    const double split_position_residual = normalized_original_vertex_position_error(
        current.initial_snapshot,
        split_snapshot,
        length_scale
    );
    const double split_area_jump = std::abs(
        split_geometry.area - initial_geometry.area
    ) / initial_geometry.area;
    const double split_volume_jump = std::abs(
        split_geometry.volume - initial_geometry.volume
    ) / initial_geometry.volume;
    const double split_centroid_jump = norm(subtract(
        split_geometry.centroid,
        initial_geometry.centroid
    )) / length_scale;
    const double split_axis_jump = std::abs(
        split_qoi.axis_length - initial_qoi.axis_length
    ) / initial_qoi.axis_length;
    const double split_energy_jump = std::abs(
        split_qoi.active_energy - initial_qoi.active_energy
    ) / initial_qoi.active_energy;
    const bool split_neutral = split_midpoint_residual <= tolerance
        && split_position_residual <= tolerance
        && split_area_jump <= tolerance
        && split_volume_jump <= tolerance
        && split_centroid_jump <= tolerance
        && split_axis_jump <= tolerance
        && split_energy_jump <= tolerance
        && split_geometry.minimum_orientation_alignment > 0.0
        && split_geometry.minimum_quality >= 0.05
        && euler_characteristic(*current.target) == 2
        && all_edges_manifold(*current.target);
    std::cout << "v10_split_gate,split_local," << split_local
              << ",split_persistent," << persistent_node_id(*current.target, split_local)
              << ",analytic_midpoint_x," << midpoint[0]
              << ",analytic_midpoint_y," << midpoint[1]
              << ",analytic_midpoint_z," << midpoint[2]
              << ",machine_midpoint_x," << machine_midpoint[0]
              << ",machine_midpoint_y," << machine_midpoint[1]
              << ",machine_midpoint_z," << machine_midpoint[2]
              << ",midpoint_residual," << split_midpoint_residual
              << ",original_vertex_position_residual," << split_position_residual
              << ",area_jump," << split_area_jump
              << ",volume_jump," << split_volume_jump
              << ",centroid_jump," << split_centroid_jump
              << ",axis_jump," << split_axis_jump
              << ",active_energy_jump," << split_energy_jump
              << ",passed," << bool_text(split_neutral)
              << '\n';
    emit_stage(
        "frozen_main",
        "after_split",
        *current.target,
        split_material,
        current.unit,
        current.initial_references
    );
    emit_stage(
        "frozen_main",
        "before_merge_frozen",
        *current.target,
        split_material,
        current.unit,
        current.initial_references
    );

    const auto before_merge = split_snapshot;
    const auto before_merge_geometry = split_geometry;
    const auto before_merge_qoi = split_qoi;
    const auto merge_iterator = current.target->get_edge_set().find(
        edge(0, split_local)
    );
    require(merge_iterator != current.target->get_edge_set().end(),
            "v10 frozen merge edge is absent");
    const auto q_analytic = scale(add(x0, midpoint), 0.5);
    refiner.merge_edge(
        const_cast<edge&>(*merge_iterator),
        current.target,
        edges_to_check
    );
    const auto after_merge = prl::cell_engine::capture_surface_snapshot(*current.target);
    const auto after_merge_material = current.sink->cell_state(17);
    const auto after_merge_geometry = independent_geometry(
        after_merge,
        face_references(before_merge)
    );
    const auto after_merge_qoi = evaluate_qoi(
        after_merge,
        after_merge_material,
        current.unit
    );
    const auto difference = vertex_difference(before_merge, after_merge);
    require(difference.deleted.size() == 2 && difference.created.size() == 1,
            "v10 frozen merge identity difference changed");
    const auto q_machine = positions_by_id(after_merge).at(difference.created.front());
    const double analytic_residual = norm(subtract(q_machine, q_analytic))
        / length_scale;
    const auto transfer = current.sink->last_audit(17);
    const auto defect = current.sink->last_remesh_energy_defect(17);
    std::cout << "v10_frozen_merge,local_0,0,local_1," << split_local
              << ",persistent_0," << x0_persistent
              << ",split_persistent," << before_merge.vertices.back().persistent_id
              << ",deleted_persistent_0," << difference.deleted[0]
              << ",deleted_persistent_1," << difference.deleted[1]
              << ",created_persistent," << difference.created[0]
              << ",analytic_x," << q_analytic[0]
              << ",analytic_y," << q_analytic[1]
              << ",analytic_z," << q_analytic[2]
              << ",machine_x," << q_machine[0]
              << ",machine_y," << q_machine[1]
              << ",machine_z," << q_machine[2]
              << ",analytic_residual," << analytic_residual
              << ",distance_from_x0_over_original_edge,"
              << norm(subtract(q_machine, x0)) / norm(subtract(x1, x0))
              << ",centroid_jump," << norm(subtract(
                    after_merge_geometry.centroid,
                    before_merge_geometry.centroid
                 )) / length_scale
              << ",area_jump," << std::abs(
                    after_merge_geometry.area - before_merge_geometry.area
                 ) / initial_geometry.area
              << ",volume_jump," << std::abs(
                    after_merge_geometry.volume - before_merge_geometry.volume
                 ) / initial_geometry.volume
              << ",axis_jump," << std::abs(
                    after_merge_qoi.axis_length - before_merge_qoi.axis_length
                 ) / initial_qoi.axis_length
              << ",active_energy_jump," << std::abs(
                    after_merge_qoi.active_energy - before_merge_qoi.active_energy
                 ) / initial_qoi.active_energy
              << ",minimum_fiber_alignment," << transfer.minimum_fiber_alignment
              << ",maximum_rebind_error," << transfer.maximum_rebind_error
              << ",passed_analytic," << bool_text(analytic_residual <= tolerance)
              << '\n';
    std::cout << "v10_event,branch,frozen_main"
              << ",action_id,merge_frozen_0_m"
              << ",parent_action_id,split_original_0_1"
              << ",operation,edge_merge"
              << ",input_local_0,0,input_local_1," << split_local
              << ",before_revision," << defect.before_revision
              << ",after_revision," << defect.after_revision
              << ",created_persistent_id," << difference.created[0]
              << '\n';
    emit_stage(
        "frozen_main",
        "after_merge_frozen",
        *current.target,
        after_merge_material,
        current.unit,
        face_references(before_merge)
    );
    require(split_neutral, "v10 split neutrality gate failed");
    require(analytic_residual <= tolerance,
            "v10 frozen merge analytic residual gate failed");
}

} // namespace

int main(const int argc, char* const argv[]) {
    try {
        const bool formal_response = argc == 2
            && std::string(argv[1]) == "--formal-response";
        if(argc > 2 || (argc == 2 && !formal_response)) {
            std::cerr << "usage: r1_midpoint_collapse_diagnostic_test "
                         "[--formal-response]\n";
            return 2;
        }
        std::cout << std::setprecision(17);
        run_frozen_main_branch();
        const auto candidates = discover_candidates();
        require(!candidates.empty(), "v10 found no split-node adjacent candidate");
        std::vector<CandidateResult> results;
        results.reserve(candidates.size());
        for(std::size_t index = 0; index < candidates.size(); ++index) {
            results.push_back(run_candidate(candidates[index], index + 1));
        }
        const bool all_eligible_completed = std::all_of(
            results.begin(),
            results.end(),
            [](const CandidateResult& result) {
                return !result.can_merge
                    || (result.merge_succeeded
                        && result.topology_legal
                        && result.analytic_residual <= tolerance);
            }
        );
        const bool any_inverse = std::any_of(
            results.begin(),
            results.end(),
            [](const CandidateResult& result) { return result.geometric_inverse; }
        );
        const auto first_failed = std::find_if(
            results.begin(),
            results.end(),
            [](const CandidateResult& result) {
                return result.can_merge
                    && (!result.merge_succeeded
                        || !result.topology_legal
                        || result.analytic_residual > tolerance);
            }
        );
        const std::string status = all_eligible_completed
            ? "passed_microprobe"
            : "failed_v10_midpoint_collapse_diagnosis_eligible_candidate_material_rebind";
        std::cout << "v10_summary,status," << status
                  << ",candidate_count," << results.size()
                  << ",eligible_count," << std::count_if(
                        results.begin(),
                        results.end(),
                        [](const CandidateResult& result) {
                            return result.can_merge;
                        }
                     )
                  << ",all_eligible_completed," << bool_text(all_eligible_completed)
                  << ",any_geometric_inverse," << bool_text(any_inverse)
                  << ",first_failed_candidate," << (
                        first_failed == results.end() ? 0 : first_failed->candidate_id
                     )
                  << ",classification_input_ready," << bool_text(all_eligible_completed)
                  << '\n';
        require(results.size() == 4, "v10 candidate count changed");
        require(!all_eligible_completed,
                "v10 frozen eligible-candidate failure unexpectedly disappeared");
        require(first_failed != results.end()
                    && first_failed->candidate_id == 3
                    && first_failed->key.local_0 == 2
                    && first_failed->key.local_1 == 8
                    && first_failed->can_merge
                    && !first_failed->merge_succeeded
                    && first_failed->failure_reason.find(
                        "material point cannot be rebound within the configured distance: "
                        "id=101, distance=0.047434164902525666"
                    ) != std::string::npos,
                "v10 first eligible-candidate failure boundary changed");
        require(!any_inverse,
                "v10 candidate enumeration unexpectedly found a geometric inverse");
        std::cout.flush();
        if(formal_response) return 1;
        std::cout << "v10_regression,status,passed_frozen_failure_regression,"
                     "formal_response_exit_code,1\n";
        std::cout << "[DEBUG-v10-midpoint] frozen failure regression completed\n";
        return 0;
    } catch(const std::exception& error) {
        std::cerr << "[DEBUG-v10-midpoint] failed: " << error.what() << '\n';
        return 1;
    }
}
