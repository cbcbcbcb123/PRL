#include "prl_cell_engine/cell_surface_force.hpp"

#include "cell.hpp"
#include "node.hpp"
#include "vec3.hpp"

#include <array>
#include <cmath>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace prl::cell_engine {
namespace {

using Vector3 = std::array<double, 3>;

bool finite_vector(const Vector3& value) noexcept {
    return std::isfinite(value[0])
        && std::isfinite(value[1])
        && std::isfinite(value[2]);
}

Vector3 add(const Vector3& left, const Vector3& right) noexcept {
    return {left[0] + right[0], left[1] + right[1], left[2] + right[2]};
}

Vector3 cross(const Vector3& left, const Vector3& right) noexcept {
    return {
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    };
}

double squared_norm(const Vector3& value) noexcept {
    return value[0] * value[0] + value[1] * value[1] + value[2] * value[2];
}

struct PendingForceWrite {
    std::size_t node_index{};
    vec3 resulting_force{};
};

} // namespace

SurfaceForceInjectionAudit apply_surface_vertex_forces(
    ::cell& target,
    const core::MeshRevision expected_revision,
    const std::vector<SurfaceVertexForce>& forces
) {
    if(target.get_mesh_revision() != expected_revision) {
        throw std::logic_error("surface-force injection revision does not match target cell");
    }
    if(forces.empty()) {
        throw std::invalid_argument("surface-force injection requires at least one vertex");
    }

    std::unordered_map<core::VertexId, std::size_t> node_by_persistent_id;
    node_by_persistent_id.reserve(target.get_nb_of_nodes());
    for(std::size_t index = 0; index < target.node_lst_.size(); ++index) {
        const node& current_node = target.node_lst_[index];
        if(!current_node.is_used()) continue;
        if(!node_by_persistent_id.emplace(current_node.get_persistent_id(), index).second) {
            throw std::runtime_error("target cell contains duplicate persistent vertex IDs");
        }
    }

    std::unordered_set<core::VertexId> force_ids;
    force_ids.reserve(forces.size());
    std::vector<PendingForceWrite> pending_writes;
    pending_writes.reserve(forces.size());
    Vector3 net_force{};
    Vector3 net_moment{};
    double injected_squared_norm = 0.0;
    for(const auto& vertex_force : forces) {
        if(!force_ids.emplace(vertex_force.vertex_id).second) {
            throw std::invalid_argument("surface-force vertex IDs must be unique");
        }
        if(!finite_vector(vertex_force.force)) {
            throw std::invalid_argument("surface-force increment must be finite");
        }
        const auto target_node = node_by_persistent_id.find(vertex_force.vertex_id);
        if(target_node == node_by_persistent_id.end()) {
            throw std::out_of_range("surface-force vertex is not present in the target cell");
        }
        const node& current_node = target.node_lst_[target_node->second];
        const Vector3 existing_force{
            current_node.force().dx(),
            current_node.force().dy(),
            current_node.force().dz(),
        };
        const auto resulting_force = add(existing_force, vertex_force.force);
        if(!finite_vector(existing_force) || !finite_vector(resulting_force)) {
            throw std::runtime_error("surface-force injection would create a non-finite buffer");
        }
        pending_writes.push_back({
            target_node->second,
            vec3{resulting_force[0], resulting_force[1], resulting_force[2]},
        });
        net_force = add(net_force, vertex_force.force);
        const Vector3 position{
            current_node.pos().dx(),
            current_node.pos().dy(),
            current_node.pos().dz(),
        };
        net_moment = add(net_moment, cross(position, vertex_force.force));
        injected_squared_norm += squared_norm(vertex_force.force);
    }
    if(!finite_vector(net_force)
       || !finite_vector(net_moment)
       || !std::isfinite(injected_squared_norm)) {
        throw std::runtime_error("surface-force injection audit became non-finite");
    }

    for(const auto& write : pending_writes) {
        target.node_lst_[write.node_index].set_force(write.resulting_force);
    }
    return {
        target.get_id(),
        expected_revision,
        pending_writes.size(),
        std::sqrt(injected_squared_norm),
        std::sqrt(squared_norm(net_force)),
        std::sqrt(squared_norm(net_moment)),
    };
}

} // namespace prl::cell_engine
