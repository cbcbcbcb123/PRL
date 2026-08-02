#include "prl/cell_engine/owned_active_overdamped_step.hpp"

#include "prl_cell_engine/cell_surface_force.hpp"
#include "prl_cell_engine/cell_surface_snapshot.hpp"

#include "contact_models/contact_face_face_via_coupling.hpp"
#include "mesh/cell.hpp"
#include "mesh/node.hpp"

#include <array>
#include <cmath>
#include <stdexcept>
#include <unordered_set>
#include <vector>

namespace prl::cell_engine {
namespace {

using Vector3 = std::array<double, 3>;

std::vector<Vector3> force_snapshot(const ::cell& target) {
    std::vector<Vector3> result;
    result.reserve(target.get_nb_of_nodes());
    for(const node& current_node : target.get_node_lst()) {
        if(!current_node.is_used()) continue;
        const Vector3 force{
            current_node.force().dx(),
            current_node.force().dy(),
            current_node.force().dz(),
        };
        if(!std::isfinite(force[0])
           || !std::isfinite(force[1])
           || !std::isfinite(force[2])) {
            throw std::runtime_error("owned-step force buffer must be finite");
        }
        result.push_back(force);
    }
    return result;
}

double force_l2_norm(const std::vector<Vector3>& forces) {
    double squared_norm = 0.0;
    for(const auto& force : forces) {
        for(const double component : force) squared_norm += component * component;
    }
    if(!std::isfinite(squared_norm)) {
        throw std::runtime_error("owned-step force norm must be finite");
    }
    return std::sqrt(squared_norm);
}

double force_difference_l2_norm(
    const std::vector<Vector3>& total,
    const std::vector<Vector3>& baseline
) {
    if(total.size() != baseline.size()) {
        throw std::runtime_error("owned-step force snapshots have different sizes");
    }
    double squared_norm = 0.0;
    for(std::size_t index = 0; index < total.size(); ++index) {
        for(std::size_t component = 0; component < 3; ++component) {
            const double difference = total[index][component] - baseline[index][component];
            squared_norm += difference * difference;
        }
    }
    if(!std::isfinite(squared_norm)) {
        throw std::runtime_error("owned-step force-increment norm must be finite");
    }
    return std::sqrt(squared_norm);
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

struct ForceBalance {
    double net_force_residual{};
    double net_moment_residual{};
};

ForceBalance force_balance(const std::vector<std::shared_ptr<::cell>>& cells) {
    Vector3 net_force{};
    Vector3 net_moment{};
    for(const auto& current_cell : cells) {
        for(const node& current_node : current_cell->get_node_lst()) {
            if(!current_node.is_used()) continue;
            const Vector3 position{
                current_node.pos().dx(),
                current_node.pos().dy(),
                current_node.pos().dz(),
            };
            const Vector3 force{
                current_node.force().dx(),
                current_node.force().dy(),
                current_node.force().dz(),
            };
            net_force = add(net_force, force);
            net_moment = add(net_moment, cross(position, force));
        }
    }
    if(!std::isfinite(squared_norm(net_force))
       || !std::isfinite(squared_norm(net_moment))) {
        throw std::runtime_error("owned contact-force balance must be finite");
    }
    return {
        std::sqrt(squared_norm(net_force)),
        std::sqrt(squared_norm(net_moment)),
    };
}

void validate_contact_context(
    ::cell& target,
    const std::vector<std::shared_ptr<::cell>>& contact_context
) {
    if(target.is_static()) {
        throw std::invalid_argument("owned contact target must be mobile");
    }
    if(contact_context.empty()) {
        throw std::invalid_argument("owned contact assembly requires a cell context");
    }
    std::unordered_set<const ::cell*> cell_pointers;
    std::unordered_set<unsigned> cell_ids;
    std::size_t target_count = 0;
    for(std::size_t index = 0; index < contact_context.size(); ++index) {
        const auto& current_cell = contact_context[index];
        if(current_cell == nullptr) {
            throw std::invalid_argument("owned contact context contains a null cell");
        }
        if(!cell_pointers.emplace(current_cell.get()).second
           || !cell_ids.emplace(current_cell->get_id()).second) {
            throw std::invalid_argument("owned contact context cells must be unique");
        }
        if(current_cell->get_local_id() != index) {
            throw std::invalid_argument("owned contact local IDs must match context order");
        }
        if(current_cell->get_cell_type() == nullptr) {
            throw std::invalid_argument("owned contact cells require initialized parameters");
        }
        if(current_cell.get() == &target) {
            target_count += 1;
        } else if(!current_cell->is_static()) {
            throw std::invalid_argument(
                "X1-H contact context permits only one active cell and static bodies"
            );
        }
        if(current_cell.get() != &target
           && target.get_cell_type()->global_type_id_ == 0
           && current_cell->get_cell_type()->global_type_id_ == 0) {
            throw std::invalid_argument(
                "X1-H rejects position-coupling epithelial contact semantics"
            );
        }
    }
    if(target_count != 1) {
        throw std::invalid_argument("owned contact context must contain target exactly once");
    }
}

} // namespace

OwnedActiveCellOverdampedStepAudit advance_owned_active_cell_overdamped_one_step(
    ::cell& target,
    const core::MyocardialCellMaterialState& material,
    const std::vector<core::ActiveContractionUnit>& units,
    const double time_step,
    const CellSurfaceDampingLaw damping,
    ::contact_face_face_via_coupling* const contact_model,
    const std::vector<std::shared_ptr<::cell>>& contact_context
) {
    if((contact_model == nullptr) != contact_context.empty()) {
        throw std::invalid_argument("owned-step contact model/context must be supplied together");
    }
    if(target.get_cell_type() == nullptr) {
        throw std::invalid_argument("owned step requires initialized cell parameters");
    }
    if(!std::isfinite(time_step) || time_step <= 0.0) {
        throw std::invalid_argument("owned-step time step must be finite and positive");
    }
    if(!std::isfinite(damping.coefficient) || damping.coefficient <= 0.0) {
        throw std::invalid_argument("owned-step damping must be finite and positive");
    }
    if(damping.measure != CellSurfaceDampingMeasure::uniform_per_vertex
       && damping.measure != CellSurfaceDampingMeasure::barycentric_dual_area) {
        throw std::invalid_argument("owned-step damping measure is not supported");
    }
    const auto before_mesh = capture_surface_snapshot(target);
    static_cast<void>(core::evaluate_active_contraction(before_mesh, material, units));
    std::vector<core::MeshRevision> context_revisions;
    if(contact_model != nullptr) {
        validate_contact_context(target, contact_context);
        context_revisions.reserve(contact_context.size());
        for(const auto& current_cell : contact_context) {
            const auto revision = current_cell->get_mesh_revision();
            context_revisions.push_back(revision);
            if(force_l2_norm(force_snapshot(*current_cell)) != 0.0) {
                throw std::logic_error("owned step requires empty context force buffers");
            }
            static_cast<void>(refresh_surface_geometry(*current_cell, revision));
        }
    } else {
        if(force_l2_norm(force_snapshot(target)) != 0.0) {
            throw std::logic_error("owned step requires empty force buffers at entry");
        }
        static_cast<void>(refresh_surface_geometry(target, before_mesh.revision));
    }

    auto reset_context_forces = [&]() {
        if(contact_model == nullptr) {
            static_cast<void>(reset_surface_forces(target, before_mesh.revision));
            return;
        }
        for(std::size_t index = 0; index < contact_context.size(); ++index) {
            static_cast<void>(reset_surface_forces(
                *contact_context[index],
                context_revisions[index]
            ));
        }
    };

    std::vector<Vector3> contact_target_forces(target.get_nb_of_nodes());
    ForceBalance contact_balance;
    double contact_force_norm = 0.0;
    double passive_force_norm = 0.0;
    double preactive_force_norm = 0.0;
    try {
        if(contact_model != nullptr) {
            contact_model->run(contact_context);
            contact_target_forces = force_snapshot(target);
            contact_force_norm = force_l2_norm(contact_target_forces);
            contact_balance = force_balance(contact_context);
        } else {
            contact_target_forces = force_snapshot(target);
        }

        target.apply_internal_forces(time_step);
        const auto preactive_forces = force_snapshot(target);
        passive_force_norm = force_difference_l2_norm(
            preactive_forces,
            contact_target_forces
        );
        preactive_force_norm = force_l2_norm(preactive_forces);
    } catch(...) {
        reset_context_forces();
        throw;
    }

    ActiveCellOverdampedStepAudit motion;
    try {
        motion = advance_active_cell_overdamped_one_step(
            target,
            material,
            units,
            time_step,
            damping
        );
    } catch(...) {
        reset_context_forces();
        throw;
    }
    if(contact_model != nullptr) {
        for(std::size_t index = 0; index < contact_context.size(); ++index) {
            if(contact_context[index].get() == &target) continue;
            static_cast<void>(reset_surface_forces(
                *contact_context[index],
                context_revisions[index]
            ));
        }
    }

    return {
        motion,
        contact_context.size(),
        contact_model != nullptr,
        contact_force_norm,
        contact_balance.net_force_residual,
        contact_balance.net_moment_residual,
        passive_force_norm,
        preactive_force_norm,
        motion.surface_area_after,
        motion.volume_after,
        motion.centroid_after,
        motion.minimum_face_area_after,
    };
}

OwnedActiveCellOverdampedStepAudit advance_owned_active_cell_overdamped_one_step(
    ::cell& target,
    const core::MyocardialCellMaterialState& material,
    const std::vector<core::ActiveContractionUnit>& units,
    const double time_step,
    const double damping_coefficient,
    ::contact_face_face_via_coupling* const contact_model,
    const std::vector<std::shared_ptr<::cell>>& contact_context
) {
    return advance_owned_active_cell_overdamped_one_step(
        target,
        material,
        units,
        time_step,
        CellSurfaceDampingLaw{
            CellSurfaceDampingMeasure::uniform_per_vertex,
            damping_coefficient,
        },
        contact_model,
        contact_context
    );
}

} // namespace prl::cell_engine
