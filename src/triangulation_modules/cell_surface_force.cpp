#include "prl_cell_engine/cell_surface_force.hpp"

#include "cell.hpp"
#include "face.hpp"
#include "node.hpp"
#include "vec3.hpp"

#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
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

Vector3 subtract(const Vector3& left, const Vector3& right) noexcept {
    return {left[0] - right[0], left[1] - right[1], left[2] - right[2]};
}

Vector3 scale(const Vector3& value, const double factor) noexcept {
    return {factor * value[0], factor * value[1], factor * value[2]};
}

double dot(const Vector3& left, const Vector3& right) noexcept {
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2];
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

struct PendingPositionWrite {
    std::size_t node_index{};
    vec3 resulting_position{};
};

struct PendingSurfaceGeometry {
    std::size_t face_count{};
    double surface_area{};
    double volume{};
    Vector3 centroid{};
    double minimum_face_area{};
};

std::vector<Vector3> current_positions(const ::cell& target) {
    std::vector<Vector3> result(target.get_node_lst().size());
    for(std::size_t index = 0; index < target.get_node_lst().size(); ++index) {
        const node& current_node = target.get_node_lst()[index];
        if(!current_node.is_used()) continue;
        result[index] = {
            current_node.pos().dx(),
            current_node.pos().dy(),
            current_node.pos().dz(),
        };
        if(!finite_vector(result[index])) {
            throw std::runtime_error("surface geometry position must be finite");
        }
    }
    return result;
}

PendingSurfaceGeometry validated_surface_geometry(
    const ::cell& target,
    const std::vector<Vector3>& positions
) {
    if(positions.size() != target.get_node_lst().size()) {
        throw std::invalid_argument("surface geometry position count mismatch");
    }
    PendingSurfaceGeometry result;
    result.minimum_face_area = std::numeric_limits<double>::infinity();
    double signed_six_volume = 0.0;
    for(const face& current_face : target.get_face_lst()) {
        if(!current_face.is_used()) continue;
        const auto node_ids = current_face.get_node_ids();
        for(const unsigned node_id : node_ids) {
            if(node_id >= positions.size()
               || !target.get_node_lst()[node_id].is_used()) {
                throw std::runtime_error("surface geometry face references an invalid node");
            }
        }
        const auto& a = positions[node_ids[0]];
        const auto& b = positions[node_ids[1]];
        const auto& c = positions[node_ids[2]];
        const auto normal = cross(subtract(b, a), subtract(c, a));
        const double face_area = 0.5 * std::sqrt(squared_norm(normal));
        if(!std::isfinite(face_area) || face_area <= 0.0) {
            throw std::runtime_error("surface geometry contains a degenerate face");
        }
        result.face_count += 1;
        result.surface_area += face_area;
        result.minimum_face_area = std::min(result.minimum_face_area, face_area);
        result.centroid = add(
            result.centroid,
            scale(add(add(a, b), c), face_area / 3.0)
        );
        signed_six_volume += dot(a, cross(b, c));
    }
    if(result.face_count == 0
       || !std::isfinite(result.surface_area)
       || result.surface_area <= 0.0) {
        throw std::runtime_error("surface geometry requires positive finite area");
    }
    result.volume = std::abs(signed_six_volume) / 6.0;
    result.centroid = scale(result.centroid, 1.0 / result.surface_area);
    if(!std::isfinite(result.volume)
       || result.volume <= 0.0
       || !finite_vector(result.centroid)
       || !std::isfinite(result.minimum_face_area)) {
        throw std::runtime_error("surface geometry audit must be finite and nondegenerate");
    }
    return result;
}

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

SurfaceOverdampedStepAudit advance_surface_overdamped(
    ::cell& target,
    const core::MeshRevision expected_revision,
    const double time_step,
    const double damping_coefficient,
    const std::vector<SurfaceVertexForce>& additional_forces
) {
    if(target.get_mesh_revision() != expected_revision) {
        throw std::logic_error("overdamped step revision does not match target cell");
    }
    if(target.is_static()) {
        throw std::logic_error("overdamped step cannot advance a static cell");
    }
    if(!std::isfinite(time_step) || time_step <= 0.0) {
        throw std::invalid_argument("overdamped time step must be finite and positive");
    }
    if(!std::isfinite(damping_coefficient) || damping_coefficient <= 0.0) {
        throw std::invalid_argument("overdamped damping coefficient must be finite and positive");
    }
    const double mobility_step = time_step / damping_coefficient;
    if(!std::isfinite(mobility_step)) {
        throw std::invalid_argument("overdamped dt/damping ratio must be finite");
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
    if(node_by_persistent_id.empty()) {
        throw std::invalid_argument("overdamped step requires at least one used vertex");
    }

    std::unordered_set<core::VertexId> additional_force_ids;
    additional_force_ids.reserve(additional_forces.size());
    std::unordered_map<std::size_t, Vector3> additional_by_node;
    additional_by_node.reserve(additional_forces.size());
    for(const auto& vertex_force : additional_forces) {
        if(!additional_force_ids.emplace(vertex_force.vertex_id).second) {
            throw std::invalid_argument("overdamped additional-force vertex IDs must be unique");
        }
        if(!finite_vector(vertex_force.force)) {
            throw std::invalid_argument("overdamped additional-force increment must be finite");
        }
        const auto target_node = node_by_persistent_id.find(vertex_force.vertex_id);
        if(target_node == node_by_persistent_id.end()) {
            throw std::out_of_range(
                "overdamped additional-force vertex is not present in the target cell"
            );
        }
        additional_by_node.emplace(target_node->second, vertex_force.force);
    }

    auto pending_positions = current_positions(target);
    std::vector<PendingPositionWrite> pending_writes;
    pending_writes.reserve(node_by_persistent_id.size());
    double additional_squared_norm = 0.0;
    double preassembled_squared_norm = 0.0;
    double total_squared_norm = 0.0;
    double displacement_squared_norm = 0.0;
    double total_force_work = 0.0;
    Vector3 net_displacement{};
    for(std::size_t index = 0; index < target.node_lst_.size(); ++index) {
        const node& current_node = target.node_lst_[index];
        if(!current_node.is_used()) continue;
        const Vector3 position{
            current_node.pos().dx(),
            current_node.pos().dy(),
            current_node.pos().dz(),
        };
        const Vector3 preassembled_force{
            current_node.force().dx(),
            current_node.force().dy(),
            current_node.force().dz(),
        };
        if(!finite_vector(position) || !finite_vector(preassembled_force)) {
            throw std::runtime_error("overdamped target state must be finite");
        }
        Vector3 additional_force{};
        const auto additional = additional_by_node.find(index);
        if(additional != additional_by_node.end()) additional_force = additional->second;
        const auto total_force = add(preassembled_force, additional_force);
        const auto displacement = scale(total_force, mobility_step);
        const auto resulting_position = add(position, displacement);
        if(!finite_vector(total_force)
           || !finite_vector(displacement)
           || !finite_vector(resulting_position)) {
            throw std::runtime_error("overdamped step would create a non-finite state");
        }
        pending_writes.push_back({
            index,
            vec3{resulting_position[0], resulting_position[1], resulting_position[2]},
        });
        pending_positions[index] = resulting_position;
        additional_squared_norm += squared_norm(additional_force);
        preassembled_squared_norm += squared_norm(preassembled_force);
        total_squared_norm += squared_norm(total_force);
        displacement_squared_norm += squared_norm(displacement);
        total_force_work += dot(total_force, displacement);
        net_displacement = add(net_displacement, displacement);
    }
    const double viscous_dissipation = damping_coefficient
        * displacement_squared_norm / time_step;
    if(!std::isfinite(additional_squared_norm)
       || !std::isfinite(preassembled_squared_norm)
       || !std::isfinite(total_squared_norm)
       || !std::isfinite(displacement_squared_norm)
       || !std::isfinite(total_force_work)
       || !std::isfinite(viscous_dissipation)
       || !finite_vector(net_displacement)) {
        throw std::runtime_error("overdamped step audit became non-finite");
    }
    const auto geometry = validated_surface_geometry(target, pending_positions);

    for(const auto& write : pending_writes) {
        node& current_node = target.node_lst_[write.node_index];
        current_node.pos_.reset(write.resulting_position);
        current_node.force_.reset();
    }
    target.update_all_face_normals_and_areas();
    target.area_ = geometry.surface_area;
    target.volume_ = geometry.volume;
    target.centroid_.reset(vec3{
        geometry.centroid[0],
        geometry.centroid[1],
        geometry.centroid[2],
    });
    #if CONTACT_MODEL_INDEX == 1 || CONTACT_MODEL_INDEX == 2
        target.compute_node_curvature_and_normals();
    #endif
    return {
        target.get_id(),
        expected_revision,
        pending_writes.size(),
        time_step,
        damping_coefficient,
        std::sqrt(preassembled_squared_norm),
        std::sqrt(additional_squared_norm),
        std::sqrt(total_squared_norm),
        std::sqrt(displacement_squared_norm),
        total_force_work,
        viscous_dissipation,
        std::abs(total_force_work - viscous_dissipation),
        std::sqrt(squared_norm(net_displacement)),
        geometry.face_count,
        geometry.surface_area,
        geometry.volume,
        geometry.centroid,
        geometry.minimum_face_area,
    };
}

SurfaceGeometryAudit refresh_surface_geometry(
    ::cell& target,
    const core::MeshRevision expected_revision
) {
    if(target.get_mesh_revision() != expected_revision) {
        throw std::logic_error("surface geometry revision does not match target cell");
    }
    const auto geometry = validated_surface_geometry(target, current_positions(target));
    target.update_all_face_normals_and_areas();
    target.area_ = geometry.surface_area;
    target.volume_ = geometry.volume;
    target.centroid_.reset(vec3{
        geometry.centroid[0],
        geometry.centroid[1],
        geometry.centroid[2],
    });
    #if CONTACT_MODEL_INDEX == 1 || CONTACT_MODEL_INDEX == 2
        target.compute_node_curvature_and_normals();
    #endif
    return {
        target.get_id(),
        expected_revision,
        geometry.face_count,
        geometry.surface_area,
        geometry.volume,
        geometry.centroid,
        geometry.minimum_face_area,
    };
}

std::size_t reset_surface_forces(
    ::cell& target,
    const core::MeshRevision expected_revision
) {
    if(target.get_mesh_revision() != expected_revision) {
        throw std::logic_error("surface-force reset revision does not match target cell");
    }
    std::size_t reset_count = 0;
    for(node& current_node : target.node_lst_) {
        if(!current_node.is_used()) continue;
        current_node.set_force(vec3{});
        reset_count += 1;
    }
    return reset_count;
}

} // namespace prl::cell_engine
