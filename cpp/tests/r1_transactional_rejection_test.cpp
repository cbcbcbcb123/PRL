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
#include <cstdint>
#include <future>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace {

constexpr double tolerance = 1.0e-12;

void require(const bool condition, const char* const message) {
    if(!condition) throw std::runtime_error(message);
}

std::shared_ptr<cell_type_parameters> zero_passive_cell_type() {
    face_type_parameters face_type;
    face_type.name_ = "v11_zero_passive_surface";
    face_type.face_type_global_id_ = 0;
    face_type.surface_tension_ = 0.0;
    face_type.adherence_strength_ = 0.0;
    face_type.repulsion_strength_ = 0.0;
    face_type.bending_modulus_ = 0.0;

    auto result = std::make_shared<cell_type_parameters>();
    result->name_ = "v11_transaction_probe_cell";
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

cell_ptr probe_cell(const unsigned cell_id = 17) {
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
    auto result = std::make_shared<cell>(
        cell_mesh,
        cell_id,
        zero_passive_cell_type()
    );
    result->initialize_cell_properties();
    return result;
}

prl::core::VertexId persistent_node_id(
    const cell& current_cell,
    const unsigned local_id
) {
    return current_cell.get_node_lst().at(local_id).get_persistent_id();
}

std::vector<prl::core::SurfaceMaterialPoint> probe_material(const cell& current_cell) {
    using namespace prl::core;
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
    };
}

struct NodeAudit {
    unsigned local_id{};
    prl::core::VertexId persistent_id{};
    bool used{};
    std::array<double, 3> position{};
    std::array<double, 3> force{};
#if DYNAMIC_MODEL_INDEX == 0
    std::array<double, 3> momentum{};
#endif

    bool operator==(const NodeAudit& other) const noexcept {
        return local_id == other.local_id
            && persistent_id == other.persistent_id
            && used == other.used
            && position == other.position
            && force == other.force
#if DYNAMIC_MODEL_INDEX == 0
            && momentum == other.momentum
#endif
            ;
    }
};

struct FaceAudit {
    unsigned local_id{};
    bool used{};
    std::array<unsigned, 3> nodes{};
    std::array<double, 3> normal{};
    double area{};
    unsigned short type_id{};

    bool operator==(const FaceAudit& other) const noexcept {
        return local_id == other.local_id
            && used == other.used
            && nodes == other.nodes
            && normal == other.normal
            && area == other.area
            && type_id == other.type_id;
    }
};

struct EdgeAudit {
    std::array<unsigned, 2> nodes{};
    std::array<unsigned, 2> faces{};

    bool operator==(const EdgeAudit& other) const noexcept {
        return nodes == other.nodes && faces == other.faces;
    }
};

struct CellAudit {
    prl::core::SurfaceMeshSnapshot surface{};
    std::vector<NodeAudit> nodes{};
    std::vector<FaceAudit> faces{};
    std::vector<EdgeAudit> edges{};
    std::array<double, 3> centroid{};
    std::array<double, 10> scalars{};
};

std::vector<EdgeAudit> capture_edges(const edge_set& edges) {
    std::vector<EdgeAudit> result;
    result.reserve(edges.size());
    for(const auto& current_edge : edges) {
        const auto node_ids = current_edge.get_node_ids();
        const auto face_ids = current_edge.get_face_ids();
        result.push_back({
            {node_ids.first, node_ids.second},
            {face_ids.first, face_ids.second},
        });
    }
    return result;
}

CellAudit capture_cell(const cell& current_cell) {
    CellAudit result;
    result.surface = prl::cell_engine::capture_surface_snapshot(current_cell);
    for(const auto& current_node : current_cell.get_node_lst()) {
        NodeAudit audit{
            current_node.get_local_id(),
            current_node.get_persistent_id(),
            current_node.is_used(),
            current_node.pos().to_array(),
            current_node.force().to_array(),
#if DYNAMIC_MODEL_INDEX == 0
            current_node.momentum().to_array(),
#endif
        };
        result.nodes.push_back(audit);
    }
    for(const auto& current_face : current_cell.get_face_lst()) {
        result.faces.push_back({
            current_face.get_local_id(),
            current_face.is_used(),
            current_face.get_node_ids(),
            current_face.get_normal().to_array(),
            current_face.get_area(),
            current_face.get_local_face_type_id(),
        });
    }
    result.edges = capture_edges(current_cell.get_edge_set());
    result.centroid = current_cell.get_centroid().to_array();
    result.scalars = {
        current_cell.get_area(),
        current_cell.get_volume(),
        current_cell.get_pressure(),
        current_cell.get_target_volume(),
        current_cell.get_surface_tension_energy(),
        current_cell.get_membrane_elasticity_energy(),
        current_cell.get_bending_energy(),
        current_cell.get_pressure_energy(),
        current_cell.get_kinetic_energy(),
        current_cell.get_growth_rate(),
    };
    return result;
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

bool exactly_equal(const CellAudit& left, const CellAudit& right) {
    return exactly_equal(left.surface, right.surface)
        && left.nodes == right.nodes
        && left.faces == right.faces
        && left.edges == right.edges
        && left.centroid == right.centroid
        && left.scalars == right.scalars;
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
        const auto& a = left.points[index];
        const auto& b = right.points[index];
        if(a.material.material_point_id != b.material.material_point_id
           || a.material.region != b.material.region
           || a.material.fiber_direction != b.material.fiber_direction
           || a.material.active_state != b.material.active_state
           || a.host_vertex_ids != b.host_vertex_ids
           || a.barycentric != b.barycentric
           || a.reference_weight != b.reference_weight) {
            return false;
        }
    }
    return true;
}

bool exactly_equal_material_payload(
    const prl::core::MyocardialCellMaterialState& left,
    const prl::core::MyocardialCellMaterialState& right
) {
    if(left.cell_id != right.cell_id || left.points.size() != right.points.size()) {
        return false;
    }
    for(std::size_t index = 0; index < left.points.size(); ++index) {
        const auto& a = left.points[index];
        const auto& b = right.points[index];
        if(a.material.material_point_id != b.material.material_point_id
           || a.material.region != b.material.region
           || a.material.fiber_direction != b.material.fiber_direction
           || a.material.active_state != b.material.active_state
           || a.reference_weight != b.reference_weight) {
            return false;
        }
        std::map<prl::core::VertexId, double> a_host_weights;
        std::map<prl::core::VertexId, double> b_host_weights;
        for(std::size_t host_index = 0; host_index < 3; ++host_index) {
            a_host_weights.emplace(
                a.host_vertex_ids[host_index],
                a.barycentric[host_index]
            );
            b_host_weights.emplace(
                b.host_vertex_ids[host_index],
                b.barycentric[host_index]
            );
        }
        if(a_host_weights.size() != b_host_weights.size()) return false;
        for(const auto& [vertex_id, weight] : a_host_weights) {
            const auto found = b_host_weights.find(vertex_id);
            if(found == b_host_weights.end()
               || std::abs(found->second - weight) > tolerance) {
                return false;
            }
        }
    }
    return true;
}

bool exactly_equal(
    const prl::core::RemeshTransferAudit& a,
    const prl::core::RemeshTransferAudit& b
) {
    return std::tie(
        a.operation,
        a.point_count,
        a.region_retention_fraction,
        a.active_state_residual,
        a.maximum_fiber_norm_error,
        a.maximum_fiber_tangency_error,
        a.minimum_fiber_alignment,
        a.maximum_rebind_error,
        a.id_retention_fraction,
        a.reference_weight_residual
    ) == std::tie(
        b.operation,
        b.point_count,
        b.region_retention_fraction,
        b.active_state_residual,
        b.maximum_fiber_norm_error,
        b.maximum_fiber_tangency_error,
        b.minimum_fiber_alignment,
        b.maximum_rebind_error,
        b.id_retention_fraction,
        b.reference_weight_residual
    );
}

bool exactly_equal(
    const prl::core::RemeshEnergyDefectAudit& a,
    const prl::core::RemeshEnergyDefectAudit& b
) {
    return std::tie(
        a.cell_id,
        a.operation,
        a.before_revision,
        a.after_revision,
        a.coverage,
        a.active_unit_count,
        a.stored_energy_before,
        a.stored_energy_after,
        a.inter_event_stored_energy_change,
        a.delta_psi_remesh,
        a.declared_remesh_work,
        a.algorithmic_energy_defect,
        a.minimum_step_fiber_alignment,
        a.minimum_initial_fiber_alignment,
        a.maximum_rebind_error
    ) == std::tie(
        b.cell_id,
        b.operation,
        b.before_revision,
        b.after_revision,
        b.coverage,
        b.active_unit_count,
        b.stored_energy_before,
        b.stored_energy_after,
        b.inter_event_stored_energy_change,
        b.delta_psi_remesh,
        b.declared_remesh_work,
        b.algorithmic_energy_defect,
        b.minimum_step_fiber_alignment,
        b.minimum_initial_fiber_alignment,
        b.maximum_rebind_error
    );
}

bool exactly_equal(
    const prl::core::RemeshEnergyLedgerAudit& a,
    const prl::core::RemeshEnergyLedgerAudit& b
) {
    return std::tie(
        a.cell_id,
        a.initial_revision,
        a.current_revision,
        a.coverage,
        a.active_unit_count,
        a.event_count,
        a.split_event_count,
        a.swap_event_count,
        a.merge_event_count,
        a.initial_stored_energy,
        a.final_stored_energy,
        a.cumulative_inter_event_stored_energy_change,
        a.cumulative_absolute_inter_event_stored_energy_change,
        a.maximum_absolute_inter_event_stored_energy_change,
        a.cumulative_delta_psi_remesh,
        a.cumulative_absolute_delta_psi_remesh,
        a.cumulative_declared_remesh_work,
        a.cumulative_algorithmic_energy_defect,
        a.cumulative_absolute_algorithmic_energy_defect,
        a.maximum_absolute_delta_psi_remesh,
        a.energy_telescoping_residual,
        a.minimum_step_fiber_alignment,
        a.minimum_initial_fiber_alignment,
        a.maximum_rebind_error
    ) == std::tie(
        b.cell_id,
        b.initial_revision,
        b.current_revision,
        b.coverage,
        b.active_unit_count,
        b.event_count,
        b.split_event_count,
        b.swap_event_count,
        b.merge_event_count,
        b.initial_stored_energy,
        b.final_stored_energy,
        b.cumulative_inter_event_stored_energy_change,
        b.cumulative_absolute_inter_event_stored_energy_change,
        b.maximum_absolute_inter_event_stored_energy_change,
        b.cumulative_delta_psi_remesh,
        b.cumulative_absolute_delta_psi_remesh,
        b.cumulative_declared_remesh_work,
        b.cumulative_algorithmic_energy_defect,
        b.cumulative_absolute_algorithmic_energy_defect,
        b.maximum_absolute_delta_psi_remesh,
        b.energy_telescoping_residual,
        b.minimum_step_fiber_alignment,
        b.minimum_initial_fiber_alignment,
        b.maximum_rebind_error
    );
}

template<typename Value>
void append_canonical(std::ostringstream& stream, const Value& value) {
    stream << value << ';';
}

void append_canonical(std::ostringstream& stream, const double value) {
    stream << std::hexfloat << value << ';' << std::defaultfloat;
}

template<typename Value, std::size_t Size>
void append_canonical(
    std::ostringstream& stream,
    const std::array<Value, Size>& values
) {
    for(const auto& value : values) append_canonical(stream, value);
}

std::uint64_t fnv1a64(const std::string& text) {
    std::uint64_t result = 14695981039346656037ULL;
    for(const unsigned char byte : text) {
        result ^= byte;
        result *= 1099511628211ULL;
    }
    return result;
}

std::uint64_t hash_cell_audit(const CellAudit& audit) {
    std::ostringstream stream;
    append_canonical(stream, audit.surface.cell_id);
    append_canonical(stream, audit.surface.revision);
    for(const auto& vertex : audit.surface.vertices) {
        append_canonical(stream, vertex.persistent_id);
        append_canonical(stream, vertex.position);
    }
    for(const auto& current_face : audit.surface.faces) {
        append_canonical(stream, current_face.vertex_indices);
    }
    for(const auto& current_node : audit.nodes) {
        append_canonical(stream, current_node.local_id);
        append_canonical(stream, current_node.persistent_id);
        append_canonical(stream, current_node.used);
        append_canonical(stream, current_node.position);
        append_canonical(stream, current_node.force);
#if DYNAMIC_MODEL_INDEX == 0
        append_canonical(stream, current_node.momentum);
#endif
    }
    for(const auto& current_face : audit.faces) {
        append_canonical(stream, current_face.local_id);
        append_canonical(stream, current_face.used);
        append_canonical(stream, current_face.nodes);
        append_canonical(stream, current_face.normal);
        append_canonical(stream, current_face.area);
        append_canonical(stream, current_face.type_id);
    }
    for(const auto& current_edge : audit.edges) {
        append_canonical(stream, current_edge.nodes);
        append_canonical(stream, current_edge.faces);
    }
    append_canonical(stream, audit.centroid);
    append_canonical(stream, audit.scalars);
    return fnv1a64(stream.str());
}

std::uint64_t hash_material_state(
    const prl::core::MyocardialCellMaterialState& state,
    const bool include_revision = true
) {
    std::ostringstream stream;
    append_canonical(stream, state.cell_id);
    if(include_revision) append_canonical(stream, state.revision);
    for(const auto& point : state.points) {
        append_canonical(stream, point.material.material_point_id);
        append_canonical(
            stream,
            static_cast<unsigned>(point.material.region)
        );
        append_canonical(stream, point.material.fiber_direction);
        for(const auto active : point.material.active_state) {
            append_canonical(stream, active);
        }
        append_canonical(stream, point.host_vertex_ids);
        append_canonical(stream, point.barycentric);
        append_canonical(stream, point.reference_weight);
    }
    return fnv1a64(stream.str());
}

std::uint64_t hash_edges(const std::vector<EdgeAudit>& edges) {
    std::ostringstream stream;
    for(const auto& current_edge : edges) {
        append_canonical(stream, current_edge.nodes);
        append_canonical(stream, current_edge.faces);
    }
    return fnv1a64(stream.str());
}

std::uint64_t hash_transfer_audit(const prl::core::RemeshTransferAudit& audit) {
    std::ostringstream stream;
    append_canonical(stream, static_cast<unsigned>(audit.operation));
    append_canonical(stream, audit.point_count);
    append_canonical(stream, audit.region_retention_fraction);
    append_canonical(stream, audit.active_state_residual);
    append_canonical(stream, audit.maximum_fiber_norm_error);
    append_canonical(stream, audit.maximum_fiber_tangency_error);
    append_canonical(stream, audit.minimum_fiber_alignment);
    append_canonical(stream, audit.maximum_rebind_error);
    append_canonical(stream, audit.id_retention_fraction);
    append_canonical(stream, audit.reference_weight_residual);
    return fnv1a64(stream.str());
}

std::uint64_t hash_energy_defect(
    const prl::core::RemeshEnergyDefectAudit& audit
) {
    std::ostringstream stream;
    append_canonical(stream, audit.cell_id);
    append_canonical(stream, static_cast<unsigned>(audit.operation));
    append_canonical(stream, audit.before_revision);
    append_canonical(stream, audit.after_revision);
    append_canonical(stream, static_cast<unsigned>(audit.coverage));
    append_canonical(stream, audit.active_unit_count);
    append_canonical(stream, audit.stored_energy_before);
    append_canonical(stream, audit.stored_energy_after);
    append_canonical(stream, audit.inter_event_stored_energy_change);
    append_canonical(stream, audit.delta_psi_remesh);
    append_canonical(stream, audit.declared_remesh_work);
    append_canonical(stream, audit.algorithmic_energy_defect);
    append_canonical(stream, audit.minimum_step_fiber_alignment);
    append_canonical(stream, audit.minimum_initial_fiber_alignment);
    append_canonical(stream, audit.maximum_rebind_error);
    return fnv1a64(stream.str());
}

std::uint64_t hash_energy_ledger(
    const prl::core::RemeshEnergyLedgerAudit& audit
) {
    std::ostringstream stream;
    append_canonical(stream, audit.cell_id);
    append_canonical(stream, audit.initial_revision);
    append_canonical(stream, audit.current_revision);
    append_canonical(stream, static_cast<unsigned>(audit.coverage));
    append_canonical(stream, audit.active_unit_count);
    append_canonical(stream, audit.event_count);
    append_canonical(stream, audit.split_event_count);
    append_canonical(stream, audit.swap_event_count);
    append_canonical(stream, audit.merge_event_count);
    append_canonical(stream, audit.initial_stored_energy);
    append_canonical(stream, audit.final_stored_energy);
    append_canonical(stream, audit.cumulative_inter_event_stored_energy_change);
    append_canonical(
        stream,
        audit.cumulative_absolute_inter_event_stored_energy_change
    );
    append_canonical(
        stream,
        audit.maximum_absolute_inter_event_stored_energy_change
    );
    append_canonical(stream, audit.cumulative_delta_psi_remesh);
    append_canonical(stream, audit.cumulative_absolute_delta_psi_remesh);
    append_canonical(stream, audit.cumulative_declared_remesh_work);
    append_canonical(stream, audit.cumulative_algorithmic_energy_defect);
    append_canonical(stream, audit.cumulative_absolute_algorithmic_energy_defect);
    append_canonical(stream, audit.maximum_absolute_delta_psi_remesh);
    append_canonical(stream, audit.energy_telescoping_residual);
    append_canonical(stream, audit.minimum_step_fiber_alignment);
    append_canonical(stream, audit.minimum_initial_fiber_alignment);
    append_canonical(stream, audit.maximum_rebind_error);
    return fnv1a64(stream.str());
}

std::map<prl::core::VertexId, std::array<double, 3>> positions_by_id(
    const prl::core::SurfaceMeshSnapshot& snapshot
);

std::set<std::array<prl::core::VertexId, 3>> persistent_faces(
    const prl::core::SurfaceMeshSnapshot& snapshot
);

void candidate_three_rejection_is_atomic() {
    auto current_cell = probe_cell();
    auto sink = std::make_shared<prl::core::MyocardialMaterialTransferSink>(
        tolerance
    );
    const auto initial = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto initial_material = probe_material(*current_cell);
    sink->register_cell(initial, initial_material);
    const auto registered_initial_material = sink->cell_state(17);
    const auto unit = prl::core::build_active_contraction_unit(
        initial,
        registered_initial_material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );
    sink->begin_active_remesh_energy_ledger(initial, {unit});

    local_mesh_refiner refiner(0.1, 10.0, true, sink);
    edge_set edges_to_check;
    const auto split_edge_iterator = current_cell->get_edge_set().find(edge(0, 1));
    require(split_edge_iterator != current_cell->get_edge_set().end(),
            "v11 split edge is missing");
    refiner.split_edge(
        const_cast<edge&>(*split_edge_iterator),
        current_cell,
        edges_to_check
    );
    require(current_cell->get_node_lst().size() == 9,
            "v11 split-node local identity drifted");

    const auto candidate_iterator = current_cell->get_edge_set().find(edge(2, 8));
    require(candidate_iterator != current_cell->get_edge_set().end(),
            "v11 frozen candidate 3 edge (2,8) is missing");
    auto& candidate = const_cast<edge&>(*candidate_iterator);
    require(refiner.can_be_merged(candidate, current_cell),
            "v11 candidate 3 lost topological eligibility");

    const auto before_cell = capture_cell(*current_cell);
    const auto before_material = sink->cell_state(17);
    const auto before_transfer = sink->last_audit(17);
    const auto before_defect = sink->last_remesh_energy_defect(17);
    const auto before_ledger = sink->remesh_energy_ledger(17);
    const auto before_workset = capture_edges(edges_to_check);

    bool expected_rejection = false;
    try {
        refiner.merge_edge(candidate, current_cell, edges_to_check);
    } catch(const std::runtime_error& error) {
        expected_rejection = std::string(error.what()).find(
            "material point cannot be rebound within the configured distance: "
            "id=101, distance=0.047434164902525666"
        ) != std::string::npos;
    }
    require(expected_rejection,
            "v11 candidate 3 did not reproduce the frozen material rejection");
    require(exactly_equal(capture_cell(*current_cell), before_cell),
            "v11 rejected candidate changed cell state");
    require(exactly_equal(sink->cell_state(17), before_material),
            "v11 rejected candidate changed material state");
    require(exactly_equal(sink->last_audit(17), before_transfer),
            "v11 rejected candidate changed the last committed transfer audit");
    require(exactly_equal(sink->last_remesh_energy_defect(17), before_defect),
            "v11 rejected candidate changed the last committed energy defect");
    require(exactly_equal(sink->remesh_energy_ledger(17), before_ledger),
            "v11 rejected candidate changed the energy ledger");
    require(capture_edges(edges_to_check) == before_workset,
            "v11 rejected candidate changed the external edge workset");

    const auto after_cell = capture_cell(*current_cell);
    const auto after_material = sink->cell_state(17);
    const auto after_transfer = sink->last_audit(17);
    const auto after_defect = sink->last_remesh_energy_defect(17);
    const auto after_ledger = sink->remesh_energy_ledger(17);
    const auto after_workset = capture_edges(edges_to_check);
    std::cout << "transaction_state_hashes,algorithm,fnv1a64_canonical_hexfloat"
              << ",cell_before," << hash_cell_audit(before_cell)
              << ",cell_after," << hash_cell_audit(after_cell)
              << ",material_before," << hash_material_state(before_material)
              << ",material_after," << hash_material_state(after_material)
              << ",transfer_before," << hash_transfer_audit(before_transfer)
              << ",transfer_after," << hash_transfer_audit(after_transfer)
              << ",defect_before," << hash_energy_defect(before_defect)
              << ",defect_after," << hash_energy_defect(after_defect)
              << ",ledger_before," << hash_energy_ledger(before_ledger)
              << ",ledger_after," << hash_energy_ledger(after_ledger)
              << ",workset_before," << hash_edges(before_workset)
              << ",workset_after," << hash_edges(after_workset)
              << '\n';

    const auto legal_half_edge = current_cell->get_edge_set().find(edge(0, 8));
    require(legal_half_edge != current_cell->get_edge_set().end(),
            "F1R legal half-edge is missing after candidate rejection");
    refiner.collapse_edge_to_survivor(
        const_cast<edge&>(*legal_half_edge),
        prl::core::VertexId{0},
        current_cell,
        edges_to_check
    );
    const auto recovered =
        prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto recovered_material = sink->cell_state(17);
    const auto recovered_ledger = sink->remesh_energy_ledger(17);
    require(recovered.revision == 2 && recovered_material.revision == 2,
            "F1R legal survivor collapse did not commit after rejection");
    require(positions_by_id(recovered) == positions_by_id(initial)
                && persistent_faces(recovered) == persistent_faces(initial),
            "F1R legal survivor cycle did not restore the original surface");
    require(exactly_equal_material_payload(
                recovered_material,
                registered_initial_material
            )
                && recovered_ledger.event_count == 2
                && recovered_ledger.split_event_count == 1
                && recovered_ledger.merge_event_count == 1,
            "F1R rejection polluted the following legal transaction");

    std::cout << "f1r,topology_eligible,1,transfer_acceptable,0,"
                 "operation_committed,0,rebind_distance,"
              << std::setprecision(17) << 0.047434164902525666
              << ",atomic_rejection,1,following_survivor_cycle,passed,"
                 "final_revision,"
              << recovered.revision << '\n';
}

class RecordingTransferSink final : public prl::core::RemeshEventSink {
public:
    explicit RecordingTransferSink(
        std::shared_ptr<prl::core::MyocardialMaterialTransferSink> target
    ) : target_(std::move(target)) {
        events.reserve(4);
    }

    void on_remesh(
        const prl::core::RemeshEvent& event,
        const prl::core::SurfaceMeshSnapshot& before,
        const prl::core::SurfaceMeshSnapshot& after
    ) override {
        target_->on_remesh(event, before, after);
        events.push_back(event);
    }

    [[nodiscard]] bool supports_transactional_remesh() const noexcept override {
        return true;
    }

    prl::core::RemeshPreparationToken prepare_remesh(
        const prl::core::RemeshEvent& event,
        const prl::core::SurfaceMeshSnapshot& before,
        const prl::core::SurfaceMeshSnapshot& after
    ) override {
        const auto token = target_->prepare_remesh(event, before, after);
        try {
            prepared_events_.emplace(token.preparation_id, event);
        } catch(...) {
            target_->reject_prepared_remesh(token);
            throw;
        }
        return token;
    }

    void commit_prepared_remesh(
        const prl::core::RemeshPreparationToken& token
    ) override {
        const auto prepared = prepared_events_.find(token.preparation_id);
        if(prepared == prepared_events_.end()) {
            throw std::logic_error("recording sink preparation token is absent");
        }
        target_->commit_prepared_remesh(token);
        events.push_back(prepared->second);
        prepared_events_.erase(prepared);
    }

    void reject_prepared_remesh(
        const prl::core::RemeshPreparationToken& token
    ) noexcept override {
        target_->reject_prepared_remesh(token);
        prepared_events_.erase(token.preparation_id);
    }

    std::vector<prl::core::RemeshEvent> events{};

private:
    std::shared_ptr<prl::core::MyocardialMaterialTransferSink> target_;
    std::map<std::uint64_t, prl::core::RemeshEvent> prepared_events_{};
};

std::map<prl::core::VertexId, std::array<double, 3>> positions_by_id(
    const prl::core::SurfaceMeshSnapshot& snapshot
) {
    std::map<prl::core::VertexId, std::array<double, 3>> result;
    for(const auto& vertex : snapshot.vertices) {
        result.emplace(vertex.persistent_id, vertex.position);
    }
    return result;
}

std::set<std::array<prl::core::VertexId, 3>> persistent_faces(
    const prl::core::SurfaceMeshSnapshot& snapshot
) {
    std::set<std::array<prl::core::VertexId, 3>> result;
    for(const auto& current_face : snapshot.faces) {
        std::array<prl::core::VertexId, 3> ids{
            snapshot.vertices.at(current_face.vertex_indices[0]).persistent_id,
            snapshot.vertices.at(current_face.vertex_indices[1]).persistent_id,
            snapshot.vertices.at(current_face.vertex_indices[2]).persistent_id,
        };
        std::sort(ids.begin(), ids.end());
        result.insert(ids);
    }
    return result;
}

void split_then_survivor_collapse_restores_the_surface() {
    auto current_cell = probe_cell();
    const auto initial = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto initial_cell_audit = capture_cell(*current_cell);
    const auto initial_points = probe_material(*current_cell);
    auto material_sink =
        std::make_shared<prl::core::MyocardialMaterialTransferSink>(tolerance);
    material_sink->register_cell(initial, initial_points);
    const auto initial_material = material_sink->cell_state(17);
    const auto unit = prl::core::build_active_contraction_unit(
        initial,
        initial_material,
        501,
        101,
        205,
        101,
        10.0,
        0.9
    );
    material_sink->begin_active_remesh_energy_ledger(initial, {unit});
    auto recording_sink = std::make_shared<RecordingTransferSink>(material_sink);
    local_mesh_refiner refiner(0.1, 10.0, true, recording_sink);
    edge_set edges_to_check;

    const auto original_edge = current_cell->get_edge_set().find(edge(0, 1));
    require(original_edge != current_cell->get_edge_set().end(),
            "v11 survivor-cycle split edge is missing");
    refiner.split_edge(
        const_cast<edge&>(*original_edge),
        current_cell,
        edges_to_check
    );
    const auto after_split =
        prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto after_split_cell_audit = capture_cell(*current_cell);
    const auto material_after_split = material_sink->cell_state(17);
    const auto after_split_edge_count = current_cell->get_edge_set().size();
    const unsigned split_local = 8;
    const auto split_persistent = persistent_node_id(*current_cell, split_local);
    const auto half_edge = current_cell->get_edge_set().find(edge(0, split_local));
    require(half_edge != current_cell->get_edge_set().end(),
            "v11 survivor-cycle half-edge is missing");
    refiner.collapse_edge_to_survivor(
        const_cast<edge&>(*half_edge),
        prl::core::VertexId{0},
        current_cell,
        edges_to_check
    );

    const auto recovered = prl::cell_engine::capture_surface_snapshot(*current_cell);
    const auto recovered_cell_audit = capture_cell(*current_cell);
    const auto recovered_material = material_sink->cell_state(17);
    const auto ledger = material_sink->remesh_energy_ledger(17);
    require(recovered.revision == 2 && recovered_material.revision == 2,
            "v11 survivor cycle did not commit two synchronized revisions");
    require(positions_by_id(recovered) == positions_by_id(initial),
            "v11 survivor collapse did not restore persistent vertex coordinates");
    require(persistent_faces(recovered) == persistent_faces(initial),
            "v11 survivor collapse did not restore persistent face connectivity");
    if(!exactly_equal_material_payload(recovered_material, initial_material)) {
        for(std::size_t index = 0; index < recovered_material.points.size(); ++index) {
            const auto& before_point = initial_material.points.at(index);
            const auto& after_point = recovered_material.points.at(index);
            std::cerr << "v11_material_difference,index," << index
                      << ",before_host," << before_point.host_vertex_ids[0]
                      << ':' << before_point.host_vertex_ids[1]
                      << ':' << before_point.host_vertex_ids[2]
                      << ",after_host," << after_point.host_vertex_ids[0]
                      << ':' << after_point.host_vertex_ids[1]
                      << ':' << after_point.host_vertex_ids[2]
                      << ",before_barycentric," << before_point.barycentric[0]
                      << ':' << before_point.barycentric[1]
                      << ':' << before_point.barycentric[2]
                      << ",after_barycentric," << after_point.barycentric[0]
                      << ':' << after_point.barycentric[1]
                      << ':' << after_point.barycentric[2]
                      << ",before_fiber," << before_point.material.fiber_direction[0]
                      << ':' << before_point.material.fiber_direction[1]
                      << ':' << before_point.material.fiber_direction[2]
                      << ",after_fiber," << after_point.material.fiber_direction[0]
                      << ':' << after_point.material.fiber_direction[1]
                      << ':' << after_point.material.fiber_direction[2]
                      << '\n';
        }
    }
    require(exactly_equal_material_payload(recovered_material, initial_material),
            "v11 survivor collapse did not restore myocardial material payload");
    require(ledger.event_count == 2
                && ledger.split_event_count == 1
                && ledger.swap_event_count == 0
                && ledger.merge_event_count == 1,
            "v11 survivor cycle operation accounting is wrong");
    require(ledger.initial_stored_energy > 1.0e-2,
            "v11 survivor cycle is not a nontrivial active-energy case");
    require(std::abs(ledger.final_stored_energy - ledger.initial_stored_energy)
                <= tolerance
                && ledger.cumulative_absolute_algorithmic_energy_defect <= tolerance
                && ledger.cumulative_absolute_inter_event_stored_energy_change
                    <= tolerance
                && ledger.maximum_absolute_inter_event_stored_energy_change
                    <= tolerance
                && std::abs(ledger.cumulative_declared_remesh_work) <= tolerance
                && ledger.energy_telescoping_residual <= tolerance
                && ledger.minimum_step_fiber_alignment >= 1.0 - tolerance
                && ledger.minimum_initial_fiber_alignment >= 1.0 - tolerance
                && ledger.maximum_rebind_error <= tolerance,
            "v11 survivor cycle failed the active material/energy gate");
    require(recording_sink->events.size() == 2,
            "v11 survivor cycle did not emit exactly two committed events");
    const auto& split_event = recording_sink->events[0];
    const auto& collapse_event = recording_sink->events[1];
    require(split_event.operation == prl::core::RemeshOperation::edge_split
                && split_event.created_persistent_id.has_value()
                && split_event.created_persistent_id.value() == split_persistent,
            "v11 split event lost created-vertex identity");
    require(collapse_event.operation
                == prl::core::RemeshOperation::edge_collapse_survivor
                && collapse_event.collapse_mode
                    == prl::core::RemeshCollapseMode::endpoint_survivor
                && collapse_event.survivor_persistent_id.has_value()
                && collapse_event.survivor_persistent_id.value() == 0
                && collapse_event.deleted_persistent_ids
                    == std::vector<prl::core::VertexId>{split_persistent}
                && !collapse_event.created_persistent_id.has_value(),
            "v11 survivor-collapse event identity is incomplete");
    std::cout << "survivor_stage,stage,initial,revision," << initial.revision
              << ",vertices," << initial.vertices.size()
              << ",faces," << initial.faces.size()
              << ",edges," << current_cell->get_edge_set().size()
              << ",material_points," << initial_material.points.size()
              << ",cell_state_hash," << hash_cell_audit(initial_cell_audit)
              << ",material_state_hash," << hash_material_state(initial_material)
              << ",material_payload_hash,"
              << hash_material_state(initial_material, false) << '\n'
              << "survivor_stage,stage,after_split,revision,"
              << after_split.revision
              << ",vertices," << after_split.vertices.size()
              << ",faces," << after_split.faces.size()
              << ",edges," << after_split_edge_count
              << ",material_points," << material_after_split.points.size()
              << ",cell_state_hash," << hash_cell_audit(after_split_cell_audit)
              << ",material_state_hash,"
              << hash_material_state(material_after_split)
              << ",material_payload_hash,"
              << hash_material_state(material_after_split, false) << '\n'
              << "survivor_stage,stage,recovered,revision,"
              << recovered.revision
              << ",vertices," << recovered.vertices.size()
              << ",faces," << recovered.faces.size()
              << ",edges," << current_cell->get_edge_set().size()
              << ",material_points," << recovered_material.points.size()
              << ",cell_state_hash," << hash_cell_audit(recovered_cell_audit)
              << ",material_state_hash,"
              << hash_material_state(recovered_material)
              << ",material_payload_hash,"
              << hash_material_state(recovered_material, false)
              << ",initial_energy," << std::setprecision(17)
              << ledger.initial_stored_energy
              << ",final_energy," << ledger.final_stored_energy
              << ",events," << ledger.event_count
              << ",split_created_id," << split_persistent
              << ",collapse_survivor_id,0,collapse_deleted_id,"
              << split_persistent << '\n';
}

void invalid_survivor_and_nonmanifold_edge_are_precommit_rejections() {
    auto current_cell = probe_cell();
    auto sink = std::make_shared<prl::core::MyocardialMaterialTransferSink>(
        tolerance
    );
    const auto initial = prl::cell_engine::capture_surface_snapshot(*current_cell);
    sink->register_cell(initial, probe_material(*current_cell));
    local_mesh_refiner refiner(0.1, 10.0, true, sink);
    edge_set edges_to_check;
    const auto split_edge = current_cell->get_edge_set().find(edge(0, 1));
    require(split_edge != current_cell->get_edge_set().end(),
            "v11 invalid-survivor split edge is missing");
    refiner.split_edge(
        const_cast<edge&>(*split_edge),
        current_cell,
        edges_to_check
    );
    const auto half_edge = current_cell->get_edge_set().find(edge(0, 8));
    require(half_edge != current_cell->get_edge_set().end(),
            "v11 invalid-survivor half-edge is missing");
    const auto before_cell = capture_cell(*current_cell);
    const auto before_material = sink->cell_state(17);
    const auto before_transfer = sink->last_audit(17);
    const auto before_workset = capture_edges(edges_to_check);

    bool invalid_survivor_rejected = false;
    try {
        refiner.collapse_edge_to_survivor(
            const_cast<edge&>(*half_edge),
            prl::core::VertexId{999},
            current_cell,
            edges_to_check
        );
    } catch(const std::invalid_argument&) {
        invalid_survivor_rejected = true;
    }
    require(invalid_survivor_rejected
                && exactly_equal(capture_cell(*current_cell), before_cell)
                && exactly_equal(sink->cell_state(17), before_material)
                && exactly_equal(sink->last_audit(17), before_transfer)
                && capture_edges(edges_to_check) == before_workset,
            "invalid survivor was not rejected atomically before commit");

    edge nonmanifold_edge(0, 8);
    bool nonmanifold_rejected = false;
    try {
        refiner.collapse_edge_to_survivor(
            nonmanifold_edge,
            prl::core::VertexId{0},
            current_cell,
            edges_to_check
        );
    } catch(const std::invalid_argument&) {
        nonmanifold_rejected = true;
    }
    require(nonmanifold_rejected
                && exactly_equal(capture_cell(*current_cell), before_cell)
                && exactly_equal(sink->cell_state(17), before_material)
                && capture_edges(edges_to_check) == before_workset,
            "nonmanifold edge was not rejected atomically before commit");
}

void degenerate_or_flipping_survivor_candidate_is_rejected_atomically() {
    const auto reference_cell = probe_cell();
    std::vector<std::array<unsigned, 2>> candidate_edges;
    candidate_edges.reserve(reference_cell->get_edge_set().size());
    for(const auto& current_edge : reference_cell->get_edge_set()) {
        const auto node_ids = current_edge.get_node_ids();
        candidate_edges.push_back({node_ids.first, node_ids.second});
    }

    bool geometry_rejection_observed = false;
    for(const auto& candidate_nodes : candidate_edges) {
        for(const unsigned survivor_local_id : candidate_nodes) {
            auto current_cell = probe_cell();
            local_mesh_refiner refiner(0.1, 10.0, true);
            edge_set workset;
            const auto candidate = current_cell->get_edge_set().find(edge(
                candidate_nodes[0],
                candidate_nodes[1]
            ));
            require(candidate != current_cell->get_edge_set().end(),
                    "geometry-rejection candidate edge is missing");
            auto& mutable_candidate = const_cast<edge&>(*candidate);
            if(!refiner.can_be_merged(mutable_candidate, current_cell)) continue;
            const auto before_cell = capture_cell(*current_cell);
            const auto before_workset = capture_edges(workset);
            try {
                refiner.collapse_edge_to_survivor(
                    mutable_candidate,
                    persistent_node_id(*current_cell, survivor_local_id),
                    current_cell,
                    workset
                );
            } catch(const std::exception& error) {
                const std::string reason = error.what();
                if(reason.find("degenerate") == std::string::npos
                   && reason.find("low-quality") == std::string::npos
                   && reason.find("flip") == std::string::npos) {
                    continue;
                }
                require(exactly_equal(capture_cell(*current_cell), before_cell)
                            && capture_edges(workset) == before_workset,
                        "geometry-rejected survivor candidate changed state");
                geometry_rejection_observed = true;
            }
            if(geometry_rejection_observed) break;
        }
        if(geometry_rejection_observed) break;
    }
    require(geometry_rejection_observed,
            "v11 fixture did not exercise a degenerate/flipping rejection");
}

void two_cells_commit_survivor_cycles_without_cross_talk() {
    auto first_cell = probe_cell(17);
    auto second_cell = probe_cell(18);
    auto sink = std::make_shared<prl::core::MyocardialMaterialTransferSink>(
        tolerance
    );
    const auto first_initial =
        prl::cell_engine::capture_surface_snapshot(*first_cell);
    const auto second_initial =
        prl::cell_engine::capture_surface_snapshot(*second_cell);
    sink->register_cell(first_initial, probe_material(*first_cell));
    sink->register_cell(second_initial, probe_material(*second_cell));
    const auto first_material = sink->cell_state(17);
    const auto second_material = sink->cell_state(18);

    auto run_cycle = [sink](const cell_ptr& target) {
        local_mesh_refiner refiner(0.1, 10.0, true, sink);
        edge_set workset;
        const auto split_edge = target->get_edge_set().find(edge(0, 1));
        if(split_edge == target->get_edge_set().end()) {
            throw std::runtime_error("concurrent survivor split edge is missing");
        }
        refiner.split_edge(
            const_cast<edge&>(*split_edge),
            target,
            workset
        );
        const auto half_edge = target->get_edge_set().find(edge(0, 8));
        if(half_edge == target->get_edge_set().end()) {
            throw std::runtime_error("concurrent survivor half-edge is missing");
        }
        refiner.collapse_edge_to_survivor(
            const_cast<edge&>(*half_edge),
            prl::core::VertexId{0},
            target,
            workset
        );
    };
    auto first = std::async(std::launch::async, run_cycle, first_cell);
    auto second = std::async(std::launch::async, run_cycle, second_cell);
    first.get();
    second.get();

    const auto first_after =
        prl::cell_engine::capture_surface_snapshot(*first_cell);
    const auto second_after =
        prl::cell_engine::capture_surface_snapshot(*second_cell);
    require(first_after.cell_id == 17 && second_after.cell_id == 18
                && first_after.revision == 2 && second_after.revision == 2,
            "concurrent survivor cycles crossed cell identity or revision");
    require(positions_by_id(first_after) == positions_by_id(first_initial)
                && positions_by_id(second_after) == positions_by_id(second_initial)
                && persistent_faces(first_after) == persistent_faces(first_initial)
                && persistent_faces(second_after) == persistent_faces(second_initial),
            "concurrent survivor cycles did not independently restore geometry");
    require(exactly_equal_material_payload(sink->cell_state(17), first_material)
                && exactly_equal_material_payload(
                    sink->cell_state(18),
                    second_material
                ),
            "concurrent survivor cycles cross-contaminated material state");
}

} // namespace

int main() {
    try {
        candidate_three_rejection_is_atomic();
        split_then_survivor_collapse_restores_the_surface();
        invalid_survivor_and_nonmanifold_edge_are_precommit_rejections();
        degenerate_or_flipping_survivor_candidate_is_rejected_atomically();
        two_cells_commit_survivor_cycles_without_cross_talk();
        return 0;
    } catch(const std::exception& error) {
        std::cerr << "[X1-K-v11-transaction] failed: " << error.what() << '\n';
        return 1;
    }
}
