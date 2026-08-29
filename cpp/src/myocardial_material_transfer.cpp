#include "prl/core/myocardial_material_transfer.hpp"

#include "prl/core/active_myocardial_mechanics.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <mutex>
#include <optional>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>
#include <utility>

namespace prl::core {
namespace {

using Vector3 = std::array<double, 3>;

constexpr double geometric_epsilon = 1.0e-14;
constexpr double barycentric_tolerance = 1.0e-12;
constexpr double fiber_tangency_tolerance = 1.0e-10;

Vector3 subtract(const Vector3& left, const Vector3& right) noexcept {
    return {left[0] - right[0], left[1] - right[1], left[2] - right[2]};
}

Vector3 add(const Vector3& left, const Vector3& right) noexcept {
    return {left[0] + right[0], left[1] + right[1], left[2] + right[2]};
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
    return dot(value, value);
}

double norm(const Vector3& value) noexcept {
    return std::sqrt(squared_norm(value));
}

bool is_finite(const Vector3& value) noexcept {
    return std::all_of(value.begin(), value.end(), [](const double component) {
        return std::isfinite(component);
    });
}

Vector3 normalized(const Vector3& value, const char* const failure_message) {
    const double length = norm(value);
    if(!std::isfinite(length) || length <= geometric_epsilon) {
        throw std::invalid_argument(failure_message);
    }
    return scale(value, 1.0 / length);
}

struct Triangle {
    std::array<VertexId, 3> vertex_ids{};
    std::array<Vector3, 3> positions{};
};

std::unordered_map<VertexId, std::uint32_t> vertex_index_by_id(
    const SurfaceMeshSnapshot& mesh
) {
    std::unordered_map<VertexId, std::uint32_t> result;
    result.reserve(mesh.vertices.size());
    for(std::uint32_t index = 0; index < mesh.vertices.size(); ++index) {
        const auto& vertex = mesh.vertices[index];
        if(!is_finite(vertex.position)) {
            throw std::invalid_argument("surface snapshot contains a non-finite vertex");
        }
        if(!result.emplace(vertex.persistent_id, index).second) {
            throw std::invalid_argument("surface snapshot vertex IDs must be unique");
        }
    }
    return result;
}

Triangle triangle_at(const SurfaceMeshSnapshot& mesh, const std::size_t face_index) {
    if(face_index >= mesh.faces.size()) {
        throw std::invalid_argument("surface snapshot references an invalid face");
    }
    Triangle result;
    const auto& indices = mesh.faces[face_index].vertex_indices;
    for(std::size_t corner = 0; corner < 3; ++corner) {
        if(indices[corner] >= mesh.vertices.size()) {
            throw std::invalid_argument("surface face references an invalid vertex");
        }
        result.vertex_ids[corner] = mesh.vertices[indices[corner]].persistent_id;
        result.positions[corner] = mesh.vertices[indices[corner]].position;
    }
    const auto twice_area = cross(
        subtract(result.positions[1], result.positions[0]),
        subtract(result.positions[2], result.positions[0])
    );
    if(norm(twice_area) <= geometric_epsilon) {
        throw std::invalid_argument("surface snapshot contains a degenerate face");
    }
    return result;
}

void validate_mesh(const SurfaceMeshSnapshot& mesh) {
    static_cast<void>(vertex_index_by_id(mesh));
    for(std::size_t face_index = 0; face_index < mesh.faces.size(); ++face_index) {
        static_cast<void>(triangle_at(mesh, face_index));
    }
}

bool same_vertex_set(
    const std::array<VertexId, 3>& left,
    const std::array<VertexId, 3>& right
) {
    auto sorted_left = left;
    auto sorted_right = right;
    std::sort(sorted_left.begin(), sorted_left.end());
    std::sort(sorted_right.begin(), sorted_right.end());
    return sorted_left == sorted_right;
}

Triangle host_triangle(
    const SurfaceMeshSnapshot& mesh,
    const std::array<VertexId, 3>& host_vertex_ids
) {
    for(std::size_t face_index = 0; face_index < mesh.faces.size(); ++face_index) {
        const auto candidate = triangle_at(mesh, face_index);
        if(!same_vertex_set(candidate.vertex_ids, host_vertex_ids)) continue;

        Triangle ordered;
        ordered.vertex_ids = host_vertex_ids;
        for(std::size_t corner = 0; corner < 3; ++corner) {
            const auto vertex = std::find(
                candidate.vertex_ids.begin(),
                candidate.vertex_ids.end(),
                host_vertex_ids[corner]
            );
            ordered.positions[corner] = candidate.positions[
                static_cast<std::size_t>(std::distance(candidate.vertex_ids.begin(), vertex))
            ];
        }
        return ordered;
    }
    throw std::invalid_argument("material point host is not a face of the before snapshot");
}

Vector3 barycentric_position(
    const Triangle& triangle,
    const std::array<double, 3>& barycentric
) noexcept {
    return add(
        add(
            scale(triangle.positions[0], barycentric[0]),
            scale(triangle.positions[1], barycentric[1])
        ),
        scale(triangle.positions[2], barycentric[2])
    );
}

Vector3 unit_normal(const Triangle& triangle) {
    return normalized(
        cross(
            subtract(triangle.positions[1], triangle.positions[0]),
            subtract(triangle.positions[2], triangle.positions[0])
        ),
        "material point has a degenerate host face"
    );
}

struct ClosestPoint {
    Vector3 position{};
    std::array<double, 3> barycentric{};
    double squared_distance{};
};

ClosestPoint closest_point_on_triangle(const Vector3& point, const Triangle& triangle) {
    const auto& a = triangle.positions[0];
    const auto& b = triangle.positions[1];
    const auto& c = triangle.positions[2];
    const auto ab = subtract(b, a);
    const auto ac = subtract(c, a);
    const auto ap = subtract(point, a);
    const double d1 = dot(ab, ap);
    const double d2 = dot(ac, ap);
    Vector3 closest;
    std::array<double, 3> barycentric{};

    if(d1 <= 0.0 && d2 <= 0.0) {
        closest = a;
        barycentric = {1.0, 0.0, 0.0};
    } else {
        const auto bp = subtract(point, b);
        const double d3 = dot(ab, bp);
        const double d4 = dot(ac, bp);
        if(d3 >= 0.0 && d4 <= d3) {
            closest = b;
            barycentric = {0.0, 1.0, 0.0};
        } else {
            const double vc = d1 * d4 - d3 * d2;
            if(vc <= 0.0 && d1 >= 0.0 && d3 <= 0.0) {
                const double weight = d1 / (d1 - d3);
                closest = add(a, scale(ab, weight));
                barycentric = {1.0 - weight, weight, 0.0};
            } else {
                const auto cp = subtract(point, c);
                const double d5 = dot(ab, cp);
                const double d6 = dot(ac, cp);
                if(d6 >= 0.0 && d5 <= d6) {
                    closest = c;
                    barycentric = {0.0, 0.0, 1.0};
                } else {
                    const double vb = d5 * d2 - d1 * d6;
                    if(vb <= 0.0 && d2 >= 0.0 && d6 <= 0.0) {
                        const double weight = d2 / (d2 - d6);
                        closest = add(a, scale(ac, weight));
                        barycentric = {1.0 - weight, 0.0, weight};
                    } else {
                        const double va = d3 * d6 - d5 * d4;
                        if(va <= 0.0 && (d4 - d3) >= 0.0 && (d5 - d6) >= 0.0) {
                            const auto bc = subtract(c, b);
                            const double weight = (d4 - d3) / ((d4 - d3) + (d5 - d6));
                            closest = add(b, scale(bc, weight));
                            barycentric = {0.0, 1.0 - weight, weight};
                        } else {
                            const double inverse = 1.0 / (va + vb + vc);
                            const double weight_b = vb * inverse;
                            const double weight_c = vc * inverse;
                            closest = add(add(a, scale(ab, weight_b)), scale(ac, weight_c));
                            barycentric = {1.0 - weight_b - weight_c, weight_b, weight_c};
                        }
                    }
                }
            }
        }
    }
    return {closest, barycentric, squared_norm(subtract(point, closest))};
}

void validate_material_point(
    const SurfaceMaterialPoint& point,
    const SurfaceMeshSnapshot& mesh
) {
    if(!std::isfinite(point.reference_weight) || point.reference_weight < 0.0) {
        throw std::invalid_argument("reference weight must be finite and nonnegative");
    }
    if(!is_finite(point.material.fiber_direction)) {
        throw std::invalid_argument("fiber direction must be finite");
    }
    for(const double value : point.material.active_state) {
        if(!std::isfinite(value)) {
            throw std::invalid_argument("active state must be finite");
        }
    }
    double barycentric_sum = 0.0;
    for(const double value : point.barycentric) {
        if(!std::isfinite(value)
            || value < -barycentric_tolerance
            || value > 1.0 + barycentric_tolerance) {
            throw std::invalid_argument("barycentric coordinate lies outside its host face");
        }
        barycentric_sum += value;
    }
    if(std::abs(barycentric_sum - 1.0) > barycentric_tolerance) {
        throw std::invalid_argument("barycentric coordinates must sum to one");
    }

    const auto triangle = host_triangle(mesh, point.host_vertex_ids);
    const auto fiber = normalized(point.material.fiber_direction, "fiber direction must be nonzero");
    if(std::abs(dot(fiber, unit_normal(triangle))) > fiber_tangency_tolerance) {
        throw std::invalid_argument("pre-remesh fiber is not tangent to its host face");
    }
}

} // namespace

class MyocardialMaterialTransferSink::Impl {
public:
    struct ActiveEnergyLedgerState {
        std::vector<ActiveContractionUnit> units{};
        std::unordered_map<MaterialPointId, Vector3> initial_fibers{};
        RemeshEnergyLedgerAudit audit{};
        std::optional<RemeshEnergyDefectAudit> last_defect{};
    };

    struct PreparedTransfer {
        RemeshPreparationToken token{};
        MyocardialCellMaterialState state{};
        RemeshTransferAudit audit{};
        std::optional<RemeshEnergyDefectAudit> energy_defect{};
        std::optional<RemeshEnergyLedgerAudit> energy_ledger{};
    };

    struct CellEntry {
        mutable std::mutex mutex{};
        MyocardialCellMaterialState state{};
        std::optional<RemeshTransferAudit> audit{};
        std::optional<ActiveEnergyLedgerState> active_energy_ledger{};
        std::optional<PreparedTransfer> prepared_transfer{};
        std::uint64_t next_preparation_id{1};
    };

    explicit Impl(const double maximum_rebind_distance)
        : maximum_rebind_distance_(maximum_rebind_distance) {}

    std::shared_ptr<CellEntry> find_cell(const CellId cell_id) const {
        std::lock_guard<std::mutex> lock(cells_mutex_);
        const auto cell = cells_.find(cell_id);
        if(cell == cells_.end()) {
            throw std::out_of_range("myocardial material cell is not registered");
        }
        return cell->second;
    }

    const double maximum_rebind_distance_;
    mutable std::mutex cells_mutex_{};
    std::unordered_map<CellId, std::shared_ptr<CellEntry>> cells_{};
};

MyocardialMaterialTransferSink::MyocardialMaterialTransferSink(
    const double maximum_rebind_distance
) : implementation_(std::make_unique<Impl>(maximum_rebind_distance)) {
    if(!std::isfinite(maximum_rebind_distance) || maximum_rebind_distance < 0.0) {
        throw std::invalid_argument("maximum rebind distance must be finite and nonnegative");
    }
}

MyocardialMaterialTransferSink::~MyocardialMaterialTransferSink() = default;

void MyocardialMaterialTransferSink::register_cell(
    const SurfaceMeshSnapshot& mesh,
    std::vector<SurfaceMaterialPoint> points
) {
    validate_mesh(mesh);
    std::unordered_set<MaterialPointId> point_ids;
    point_ids.reserve(points.size());
    for(const auto& point : points) {
        if(!point_ids.emplace(point.material.material_point_id).second) {
            throw std::invalid_argument("myocardial material-point IDs must be unique within a cell");
        }
        validate_material_point(point, mesh);
    }

    auto entry = std::make_shared<Impl::CellEntry>();
    entry->state = {mesh.cell_id, mesh.revision, std::move(points)};
    std::lock_guard<std::mutex> lock(implementation_->cells_mutex_);
    if(!implementation_->cells_.emplace(mesh.cell_id, std::move(entry)).second) {
        throw std::invalid_argument("myocardial material cell is already registered");
    }
}

RemeshPreparationToken MyocardialMaterialTransferSink::prepare_remesh(
    const RemeshEvent& event,
    const SurfaceMeshSnapshot& before,
    const SurfaceMeshSnapshot& after
) {
    if(!is_valid_remesh_event(event, before, after)) {
        throw std::invalid_argument("invalid remesh event");
    }
    validate_mesh(before);
    validate_mesh(after);
    const auto entry = implementation_->find_cell(event.cell_id);
    std::lock_guard<std::mutex> lock(entry->mutex);
    if(entry->prepared_transfer.has_value()) {
        throw std::logic_error(
            "myocardial material cell already has a prepared remesh"
        );
    }
    if(entry->state.revision != event.before_revision) {
        throw std::logic_error("remesh event revision does not match registered material state");
    }

    auto transferred_points = entry->state.points;
    double maximum_rebind_error = 0.0;
    double maximum_fiber_norm_error = 0.0;
    double maximum_fiber_tangency_error = 0.0;
    double minimum_fiber_alignment = 1.0;

    for(auto& point : transferred_points) {
        const auto old_triangle = host_triangle(before, point.host_vertex_ids);
        const auto old_position = barycentric_position(old_triangle, point.barycentric);
        const auto old_fiber = normalized(
            point.material.fiber_direction,
            "fiber direction must be nonzero"
        );
        if(std::abs(dot(old_fiber, unit_normal(old_triangle))) > fiber_tangency_tolerance) {
            throw std::invalid_argument("pre-remesh fiber is not tangent to its host face");
        }

        std::size_t best_face_index = 0;
        double best_squared_distance = std::numeric_limits<double>::infinity();
        ClosestPoint best_point;
        for(std::size_t face_index = 0; face_index < after.faces.size(); ++face_index) {
            const auto triangle = triangle_at(after, face_index);
            const auto candidate = closest_point_on_triangle(old_position, triangle);
            if(candidate.squared_distance < best_squared_distance) {
                best_face_index = face_index;
                best_squared_distance = candidate.squared_distance;
                best_point = candidate;
            }
        }
        const double rebind_error = std::sqrt(best_squared_distance);
        if(!std::isfinite(rebind_error)
            || rebind_error > implementation_->maximum_rebind_distance_) {
            std::ostringstream message;
            message << "material point cannot be rebound within the configured distance: id="
                    << point.material.material_point_id
                    << ", distance=" << std::setprecision(17) << rebind_error;
            throw std::runtime_error(message.str());
        }

        const auto new_triangle = triangle_at(after, best_face_index);
        const auto new_normal = unit_normal(new_triangle);
        auto projected_fiber = subtract(old_fiber, scale(new_normal, dot(old_fiber, new_normal)));
        projected_fiber = normalized(
            projected_fiber,
            "fiber transport collapsed during tangent-plane projection"
        );
        double signed_alignment = dot(projected_fiber, old_fiber);
        if(signed_alignment < 0.0) {
            projected_fiber = scale(projected_fiber, -1.0);
            signed_alignment = -signed_alignment;
        }

        point.host_vertex_ids = new_triangle.vertex_ids;
        point.barycentric = best_point.barycentric;
        point.material.fiber_direction = projected_fiber;
        maximum_rebind_error = std::max(maximum_rebind_error, rebind_error);
        maximum_fiber_norm_error = std::max(
            maximum_fiber_norm_error,
            std::abs(norm(projected_fiber) - 1.0)
        );
        maximum_fiber_tangency_error = std::max(
            maximum_fiber_tangency_error,
            std::abs(dot(projected_fiber, new_normal))
        );
        minimum_fiber_alignment = std::min(minimum_fiber_alignment, signed_alignment);
    }

    const double retained_fraction = transferred_points.empty() ? 0.0 : 1.0;
    const RemeshTransferAudit audit{
        event.operation,
        transferred_points.size(),
        retained_fraction,
        0.0,
        maximum_fiber_norm_error,
        maximum_fiber_tangency_error,
        minimum_fiber_alignment,
        maximum_rebind_error,
        retained_fraction,
        0.0,
    };

    MyocardialCellMaterialState transferred_state{
        event.cell_id,
        event.after_revision,
        transferred_points,
    };
    std::optional<RemeshEnergyDefectAudit> pending_defect;
    std::optional<RemeshEnergyLedgerAudit> pending_ledger;
    if(entry->active_energy_ledger.has_value()) {
        const auto before_energy = evaluate_active_contraction(
            before,
            entry->state,
            entry->active_energy_ledger->units
        );
        const auto after_energy = evaluate_active_contraction(
            after,
            transferred_state,
            entry->active_energy_ledger->units
        );
        const double inter_event_change = before_energy.audit.total_energy
            - entry->active_energy_ledger->audit.final_stored_energy;
        const double delta_psi_remesh = after_energy.audit.total_energy
            - before_energy.audit.total_energy;
        constexpr double declared_remesh_work = 0.0;
        const double algorithmic_energy_defect = delta_psi_remesh
            - declared_remesh_work;
        double minimum_initial_fiber_alignment = 1.0;
        for(const auto& point : transferred_state.points) {
            const auto initial = entry->active_energy_ledger->initial_fibers.find(
                point.material.material_point_id
            );
            if(initial == entry->active_energy_ledger->initial_fibers.end()) {
                throw std::runtime_error(
                    "remesh-energy ledger lost a registered material-point ID"
                );
            }
            const auto current_fiber = normalized(
                point.material.fiber_direction,
                "remesh-energy ledger fiber must be nonzero"
            );
            minimum_initial_fiber_alignment = std::min(
                minimum_initial_fiber_alignment,
                std::clamp(
                    std::abs(dot(initial->second, current_fiber)),
                    0.0,
                    1.0
                )
            );
        }
        pending_defect = RemeshEnergyDefectAudit{
            event.cell_id,
            event.operation,
            event.before_revision,
            event.after_revision,
            RemeshEnergyCoverage::active_contraction_only,
            entry->active_energy_ledger->units.size(),
            before_energy.audit.total_energy,
            after_energy.audit.total_energy,
            inter_event_change,
            delta_psi_remesh,
            declared_remesh_work,
            algorithmic_energy_defect,
            minimum_fiber_alignment,
            minimum_initial_fiber_alignment,
            maximum_rebind_error,
        };
        pending_ledger = entry->active_energy_ledger->audit;
        pending_ledger->current_revision = event.after_revision;
        pending_ledger->event_count += 1;
        switch(event.operation) {
            case RemeshOperation::edge_split:
                pending_ledger->split_event_count += 1;
                break;
            case RemeshOperation::edge_swap:
                pending_ledger->swap_event_count += 1;
                break;
            case RemeshOperation::edge_merge:
            case RemeshOperation::edge_collapse_survivor:
                pending_ledger->merge_event_count += 1;
                break;
        }
        pending_ledger->final_stored_energy = after_energy.audit.total_energy;
        pending_ledger->cumulative_inter_event_stored_energy_change
            += inter_event_change;
        pending_ledger->cumulative_absolute_inter_event_stored_energy_change
            += std::abs(inter_event_change);
        pending_ledger->maximum_absolute_inter_event_stored_energy_change
            = std::max(
                pending_ledger->maximum_absolute_inter_event_stored_energy_change,
                std::abs(inter_event_change)
            );
        pending_ledger->cumulative_delta_psi_remesh += delta_psi_remesh;
        pending_ledger->cumulative_absolute_delta_psi_remesh
            += std::abs(delta_psi_remesh);
        pending_ledger->cumulative_declared_remesh_work
            += declared_remesh_work;
        pending_ledger->cumulative_algorithmic_energy_defect
            += algorithmic_energy_defect;
        pending_ledger->cumulative_absolute_algorithmic_energy_defect
            += std::abs(algorithmic_energy_defect);
        pending_ledger->maximum_absolute_delta_psi_remesh = std::max(
            pending_ledger->maximum_absolute_delta_psi_remesh,
            std::abs(delta_psi_remesh)
        );
        pending_ledger->minimum_step_fiber_alignment = std::min(
            pending_ledger->minimum_step_fiber_alignment,
            minimum_fiber_alignment
        );
        pending_ledger->minimum_initial_fiber_alignment = std::min(
            pending_ledger->minimum_initial_fiber_alignment,
            minimum_initial_fiber_alignment
        );
        pending_ledger->maximum_rebind_error = std::max(
            pending_ledger->maximum_rebind_error,
            maximum_rebind_error
        );
        pending_ledger->energy_telescoping_residual = std::abs(
            (pending_ledger->final_stored_energy
             - pending_ledger->initial_stored_energy)
            - pending_ledger->cumulative_inter_event_stored_energy_change
            - pending_ledger->cumulative_delta_psi_remesh
        );
    }

    const RemeshPreparationToken token{
        event.cell_id,
        event.before_revision,
        event.after_revision,
        entry->next_preparation_id++,
    };
    entry->prepared_transfer = Impl::PreparedTransfer{
        token,
        std::move(transferred_state),
        audit,
        std::move(pending_defect),
        std::move(pending_ledger),
    };
    return token;
}

void MyocardialMaterialTransferSink::commit_prepared_remesh(
    const RemeshPreparationToken& token
) {
    const auto entry = implementation_->find_cell(token.cell_id);
    std::lock_guard<std::mutex> lock(entry->mutex);
    if(!entry->prepared_transfer.has_value()) {
        throw std::logic_error("remesh preparation token is absent or already used");
    }
    const auto& prepared_token = entry->prepared_transfer->token;
    if(prepared_token.cell_id != token.cell_id
       || prepared_token.before_revision != token.before_revision
       || prepared_token.after_revision != token.after_revision
       || prepared_token.preparation_id != token.preparation_id
       || entry->state.revision != token.before_revision) {
        throw std::logic_error("remesh preparation token is stale or mismatched");
    }
    if(entry->prepared_transfer->energy_ledger.has_value()
       && (!entry->active_energy_ledger.has_value()
           || !entry->prepared_transfer->energy_defect.has_value())) {
        throw std::logic_error(
            "prepared remesh energy state is internally inconsistent"
        );
    }

    auto prepared = std::move(*entry->prepared_transfer);
    entry->state = std::move(prepared.state);
    entry->audit = prepared.audit;
    if(prepared.energy_ledger.has_value()) {
        entry->active_energy_ledger->audit = *prepared.energy_ledger;
        entry->active_energy_ledger->last_defect = *prepared.energy_defect;
    }
    entry->prepared_transfer.reset();
}

void MyocardialMaterialTransferSink::reject_prepared_remesh(
    const RemeshPreparationToken& token
) noexcept {
    try {
        const auto entry = implementation_->find_cell(token.cell_id);
        std::lock_guard<std::mutex> lock(entry->mutex);
        if(!entry->prepared_transfer.has_value()) return;
        const auto& prepared_token = entry->prepared_transfer->token;
        if(prepared_token.cell_id == token.cell_id
           && prepared_token.before_revision == token.before_revision
           && prepared_token.after_revision == token.after_revision
           && prepared_token.preparation_id == token.preparation_id) {
            entry->prepared_transfer.reset();
        }
    } catch(...) {
    }
}

void MyocardialMaterialTransferSink::on_remesh(
    const RemeshEvent& event,
    const SurfaceMeshSnapshot& before,
    const SurfaceMeshSnapshot& after
) {
    const auto token = prepare_remesh(event, before, after);
    try {
        commit_prepared_remesh(token);
    } catch(...) {
        reject_prepared_remesh(token);
        throw;
    }
}

void MyocardialMaterialTransferSink::update_active_state(
    const CellId cell_id,
    const MaterialPointId material_point_id,
    const MeshRevision expected_revision,
    std::vector<double> active_state
) {
    if(!std::all_of(active_state.begin(), active_state.end(), [](const double value) {
        return std::isfinite(value);
    })) {
        throw std::invalid_argument("active state must be finite");
    }
    const auto entry = implementation_->find_cell(cell_id);
    std::lock_guard<std::mutex> lock(entry->mutex);
    if(entry->prepared_transfer.has_value()) {
        throw std::logic_error(
            "active-state update cannot cross a prepared remesh"
        );
    }
    if(entry->state.revision != expected_revision) {
        throw std::logic_error("active-state update revision does not match material state");
    }
    const auto point = std::find_if(
        entry->state.points.begin(),
        entry->state.points.end(),
        [material_point_id](const SurfaceMaterialPoint& candidate) {
            return candidate.material.material_point_id == material_point_id;
        }
    );
    if(point == entry->state.points.end()) {
        throw std::out_of_range("active-state material point is not registered");
    }
    point->material.active_state = std::move(active_state);
}

void MyocardialMaterialTransferSink::begin_active_remesh_energy_ledger(
    const SurfaceMeshSnapshot& mesh,
    std::vector<ActiveContractionUnit> units
) {
    validate_mesh(mesh);
    const auto entry = implementation_->find_cell(mesh.cell_id);
    std::lock_guard<std::mutex> lock(entry->mutex);
    if(entry->prepared_transfer.has_value()) {
        throw std::logic_error(
            "remesh-energy ledger cannot start during a prepared remesh"
        );
    }
    if(entry->state.revision != mesh.revision) {
        throw std::logic_error(
            "remesh-energy ledger mesh revision does not match material state"
        );
    }
    if(entry->active_energy_ledger.has_value()) {
        throw std::logic_error("remesh-energy ledger is already active for this cell");
    }
    const auto initial_energy = evaluate_active_contraction(mesh, entry->state, units);
    Impl::ActiveEnergyLedgerState ledger;
    ledger.units = std::move(units);
    ledger.initial_fibers.reserve(entry->state.points.size());
    for(const auto& point : entry->state.points) {
        if(!ledger.initial_fibers.emplace(
                point.material.material_point_id,
                normalized(
                    point.material.fiber_direction,
                    "remesh-energy ledger initial fiber must be nonzero"
                )
            ).second) {
            throw std::runtime_error(
                "remesh-energy ledger material-point IDs must be unique"
            );
        }
    }
    ledger.audit.cell_id = mesh.cell_id;
    ledger.audit.initial_revision = mesh.revision;
    ledger.audit.current_revision = mesh.revision;
    ledger.audit.coverage = RemeshEnergyCoverage::active_contraction_only;
    ledger.audit.active_unit_count = ledger.units.size();
    ledger.audit.initial_stored_energy = initial_energy.audit.total_energy;
    ledger.audit.final_stored_energy = initial_energy.audit.total_energy;
    entry->active_energy_ledger = std::move(ledger);
}

MyocardialCellMaterialState MyocardialMaterialTransferSink::cell_state(
    const CellId cell_id
) const {
    const auto entry = implementation_->find_cell(cell_id);
    std::lock_guard<std::mutex> lock(entry->mutex);
    return entry->state;
}

RemeshTransferAudit MyocardialMaterialTransferSink::last_audit(
    const CellId cell_id
) const {
    const auto entry = implementation_->find_cell(cell_id);
    std::lock_guard<std::mutex> lock(entry->mutex);
    if(!entry->audit.has_value()) {
        throw std::logic_error("myocardial material cell has no remesh audit");
    }
    return entry->audit.value();
}

RemeshEnergyDefectAudit MyocardialMaterialTransferSink::last_remesh_energy_defect(
    const CellId cell_id
) const {
    const auto entry = implementation_->find_cell(cell_id);
    std::lock_guard<std::mutex> lock(entry->mutex);
    if(!entry->active_energy_ledger.has_value()
       || !entry->active_energy_ledger->last_defect.has_value()) {
        throw std::logic_error("myocardial material cell has no remesh-energy defect");
    }
    return entry->active_energy_ledger->last_defect.value();
}

RemeshEnergyLedgerAudit MyocardialMaterialTransferSink::remesh_energy_ledger(
    const CellId cell_id
) const {
    const auto entry = implementation_->find_cell(cell_id);
    std::lock_guard<std::mutex> lock(entry->mutex);
    if(!entry->active_energy_ledger.has_value()) {
        throw std::logic_error("myocardial material cell has no remesh-energy ledger");
    }
    return entry->active_energy_ledger->audit;
}

RemeshCycleGateAudit evaluate_remesh_cycle_gate(
    const RemeshEnergyLedgerAudit& ledger,
    const RemeshCycleGateThresholds& thresholds
) {
    const std::array<double, 8> nonnegative_thresholds{
        thresholds.maximum_absolute_final_energy_drift,
        thresholds.maximum_cumulative_absolute_energy_defect,
        thresholds.maximum_absolute_inter_event_energy_change,
        thresholds.maximum_absolute_declared_remesh_work,
        thresholds.maximum_energy_telescoping_residual,
        thresholds.maximum_rebind_error,
        thresholds.maximum_cumulative_absolute_inter_event_energy_change,
        thresholds.maximum_per_event_absolute_inter_event_energy_change,
    };
    if(!std::all_of(
            nonnegative_thresholds.begin(),
            nonnegative_thresholds.end(),
            [](const double value) { return std::isfinite(value) && value >= 0.0; }
        )
       || !std::isfinite(thresholds.minimum_initial_fiber_alignment)
       || thresholds.minimum_initial_fiber_alignment < 0.0
       || thresholds.minimum_initial_fiber_alignment > 1.0
       || thresholds.minimum_event_count == 0) {
        throw std::invalid_argument("remesh-cycle gate thresholds are invalid");
    }
    const std::array<double, 11> audited_values{
        ledger.initial_stored_energy,
        ledger.final_stored_energy,
        ledger.cumulative_absolute_delta_psi_remesh,
        ledger.cumulative_inter_event_stored_energy_change,
        ledger.cumulative_absolute_inter_event_stored_energy_change,
        ledger.maximum_absolute_inter_event_stored_energy_change,
        ledger.cumulative_declared_remesh_work,
        ledger.cumulative_algorithmic_energy_defect,
        ledger.cumulative_absolute_algorithmic_energy_defect,
        ledger.energy_telescoping_residual,
        ledger.maximum_rebind_error,
    };
    if(!std::all_of(
            audited_values.begin(),
            audited_values.end(),
            [](const double value) { return std::isfinite(value); }
        )
       || !std::isfinite(ledger.minimum_initial_fiber_alignment)
       || ledger.cumulative_absolute_delta_psi_remesh < 0.0
       || ledger.cumulative_absolute_inter_event_stored_energy_change < 0.0
       || ledger.maximum_absolute_inter_event_stored_energy_change < 0.0
       || ledger.cumulative_absolute_algorithmic_energy_defect < 0.0
       || ledger.energy_telescoping_residual < 0.0
       || ledger.maximum_rebind_error < 0.0
       || ledger.minimum_initial_fiber_alignment < 0.0
       || ledger.minimum_initial_fiber_alignment > 1.0) {
        throw std::invalid_argument("remesh-cycle gate ledger is non-finite");
    }

    RemeshCycleGateAudit result;
    result.final_energy_drift = ledger.final_stored_energy
        - ledger.initial_stored_energy;
    result.fiber_drift = 1.0 - ledger.minimum_initial_fiber_alignment;
    result.event_count_passed = ledger.event_count >= thresholds.minimum_event_count;
    result.energy_drift_passed = std::abs(result.final_energy_drift)
        <= thresholds.maximum_absolute_final_energy_drift;
    result.absolute_defect_passed
        = ledger.cumulative_absolute_algorithmic_energy_defect
        <= thresholds.maximum_cumulative_absolute_energy_defect;
    result.inter_event_change_passed = std::abs(
        ledger.cumulative_inter_event_stored_energy_change
    ) <= thresholds.maximum_absolute_inter_event_energy_change;
    result.absolute_inter_event_change_passed
        = ledger.cumulative_absolute_inter_event_stored_energy_change
        <= thresholds.maximum_cumulative_absolute_inter_event_energy_change;
    result.maximum_inter_event_change_passed
        = ledger.maximum_absolute_inter_event_stored_energy_change
        <= thresholds.maximum_per_event_absolute_inter_event_energy_change;
    result.remesh_work_passed = std::abs(ledger.cumulative_declared_remesh_work)
        <= thresholds.maximum_absolute_declared_remesh_work;
    result.telescoping_passed = ledger.energy_telescoping_residual
        <= thresholds.maximum_energy_telescoping_residual;
    result.fiber_drift_passed = ledger.minimum_initial_fiber_alignment
        >= thresholds.minimum_initial_fiber_alignment;
    result.rebind_passed = ledger.maximum_rebind_error
        <= thresholds.maximum_rebind_error;
    result.passed = result.event_count_passed
        && result.energy_drift_passed
        && result.absolute_defect_passed
        && result.inter_event_change_passed
        && result.absolute_inter_event_change_passed
        && result.maximum_inter_event_change_passed
        && result.remesh_work_passed
        && result.telescoping_passed
        && result.fiber_drift_passed
        && result.rebind_passed;
    return result;
}

} // namespace prl::core
