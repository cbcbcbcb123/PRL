#include "prl/core/myocardial_material_transfer.hpp"

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
    struct CellEntry {
        mutable std::mutex mutex{};
        MyocardialCellMaterialState state{};
        std::optional<RemeshTransferAudit> audit{};
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

void MyocardialMaterialTransferSink::on_remesh(
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
    entry->state.revision = event.after_revision;
    entry->state.points = std::move(transferred_points);
    entry->audit = audit;
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

} // namespace prl::core
