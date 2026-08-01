#include "prl/core/myocardial_material_transfer.hpp"
#include "prl_cell_engine/cell_surface_snapshot.hpp"

#include "cell.hpp"
#include "edge.hpp"
#include "local_mesh_refiner.hpp"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <type_traits>
#include <vector>

#if defined(__linux__) || defined(__APPLE__)
#include <sys/resource.h>
#endif

namespace {

using Clock = std::chrono::steady_clock;

enum class OperationPattern {
    alternating_swap,
    split_merge,
};

struct BenchmarkConfig {
    std::size_t cell_count{};
    std::size_t operations_per_cell{};
    std::size_t requested_threads{};
    bool verify_determinism{};
    OperationPattern operation_pattern{OperationPattern::alternating_swap};
};

struct BenchmarkResult {
    BenchmarkConfig config{};
    std::size_t worker_threads{};
    std::uint64_t total_events{};
    double setup_seconds{};
    double remesh_seconds{};
    double events_per_second{};
    std::uint64_t semantic_digest{};
    long peak_rss_kib{};
    bool determinism_verified{};
    std::uint64_t determinism_reference_digest{};
};

std::size_t parse_positive_size(const std::string& text, const std::string& option) {
    if(text.empty() || !std::all_of(text.begin(), text.end(), [](const char value) {
        return value >= '0' && value <= '9';
    })) {
        throw std::invalid_argument(option + " requires a positive integer");
    }
    std::size_t consumed = 0;
    unsigned long long parsed = 0;
    try {
        parsed = std::stoull(text, &consumed);
    } catch(const std::exception&) {
        throw std::invalid_argument(option + " requires a positive integer");
    }
    if(consumed != text.size() || parsed == 0
       || parsed > static_cast<unsigned long long>(std::numeric_limits<std::size_t>::max())) {
        throw std::invalid_argument(option + " requires a positive integer");
    }
    return static_cast<std::size_t>(parsed);
}

BenchmarkConfig parse_arguments(const int argc, const char* const argv[]) {
    BenchmarkConfig config;
    for(int index = 1; index < argc; index += 2) {
        if(index + 1 >= argc) throw std::invalid_argument("missing option value");
        const std::string option = argv[index];
        const std::string value = argv[index + 1];
        if(option == "--cells") {
            config.cell_count = parse_positive_size(value, option);
        } else if(option == "--operations-per-cell") {
            config.operations_per_cell = parse_positive_size(value, option);
        } else if(option == "--threads") {
            config.requested_threads = parse_positive_size(value, option);
        } else if(option == "--verify-determinism") {
            if(value != "true" && value != "false") {
                throw std::invalid_argument(option + " requires true or false");
            }
            config.verify_determinism = value == "true";
        } else if(option == "--operation-pattern") {
            if(value == "alternating_swap") {
                config.operation_pattern = OperationPattern::alternating_swap;
            } else if(value == "split_merge") {
                config.operation_pattern = OperationPattern::split_merge;
            } else {
                throw std::invalid_argument(
                    option + " requires alternating_swap or split_merge"
                );
            }
        } else {
            throw std::invalid_argument("unknown option: " + option);
        }
    }
    if(config.cell_count == 0 || config.operations_per_cell == 0 || config.requested_threads == 0) {
        throw std::invalid_argument(
            "required options: --cells N --operations-per-cell N --threads N"
        );
    }
    if(config.operation_pattern == OperationPattern::split_merge
       && config.operations_per_cell != 2) {
        throw std::invalid_argument("split_merge requires exactly two events per cell");
    }
    if(config.cell_count > std::numeric_limits<std::uint64_t>::max()
                               / config.operations_per_cell) {
        throw std::overflow_error("total event count exceeds uint64 range");
    }
    return config;
}

cell_ptr closed_swap_cell(const unsigned cell_id, const double x_offset) {
    mesh cell_mesh;
    cell_mesh.node_pos_lst = {
        x_offset + 0.0,  0.0,  0.0,
        x_offset + 0.0, -3.0,  0.0,
        x_offset - 1.0, -1.5,  0.0,
        x_offset + 1.0, -1.5,  0.0,
        x_offset + 0.0,  0.0, -1.0,
        x_offset + 0.0, -3.0, -1.0,
        x_offset - 1.0, -1.5, -1.0,
        x_offset + 1.0, -1.5, -1.0,
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
    auto result = std::make_shared<cell>(cell_mesh, cell_id);
    result->generate_edge_set();
    return result;
}

prl::core::VertexId persistent_node_id(const cell& current_cell, const unsigned local_id) {
    return current_cell.get_node_lst().at(local_id).get_persistent_id();
}

std::vector<prl::core::SurfaceMaterialPoint> myocardial_points(
    const cell& current_cell,
    const prl::core::CellId cell_id
) {
    using namespace prl::core;
    const auto a = persistent_node_id(current_cell, 0);
    const auto b = persistent_node_id(current_cell, 1);
    const auto c = persistent_node_id(current_cell, 2);
    const auto d = persistent_node_id(current_cell, 3);
    return {
        {
            MyocardialMaterialState{
                cell_id * 10 + 1,
                SurfaceRegion::apical,
                {1.0, 0.0, 0.0},
                {0.2, 0.3},
            },
            {a, b, c},
            {0.2, 0.3, 0.5},
            0.17,
        },
        {
            MyocardialMaterialState{
                cell_id * 10 + 2,
                SurfaceRegion::basal,
                {0.0, 1.0, 0.0},
                {0.4, 0.7},
            },
            {a, b, d},
            {0.4, 0.25, 0.35},
            0.23,
        },
    };
}

void run_cell_operations(
    const cell_ptr& current_cell,
    const BenchmarkConfig& config,
    const local_mesh_refiner& refiner
) {
    if(config.operation_pattern == OperationPattern::split_merge) {
        edge_set edges_to_check;
        const auto original_edge = current_cell->get_edge_set().find(edge(0, 1));
        if(original_edge == current_cell->get_edge_set().end()) {
            throw std::runtime_error("split benchmark edge is absent");
        }
        refiner.split_edge(const_cast<edge&>(*original_edge), current_cell, edges_to_check);
        if(current_cell->get_mesh_revision() != 1) {
            throw std::runtime_error("real edge split did not emit exactly one accepted event");
        }
        const auto split_node_id = static_cast<unsigned>(current_cell->get_node_lst().size() - 1);
        const auto split_edge = current_cell->get_edge_set().find(edge(0, split_node_id));
        if(split_edge == current_cell->get_edge_set().end()) {
            throw std::runtime_error("merge benchmark edge is absent");
        }
        refiner.merge_edge(const_cast<edge&>(*split_edge), current_cell, edges_to_check);
        if(current_cell->get_mesh_revision() != 2) {
            throw std::runtime_error("real edge merge did not emit exactly one accepted event");
        }
        return;
    }

    for(std::size_t operation_index = 0;
        operation_index < config.operations_per_cell;
        ++operation_index) {
        const edge target = operation_index % 2 == 0 ? edge(0, 1) : edge(2, 3);
        const auto edge_iterator = current_cell->get_edge_set().find(target);
        if(edge_iterator == current_cell->get_edge_set().end()) {
            throw std::runtime_error("alternating benchmark edge is absent");
        }
        const auto before_revision = current_cell->get_mesh_revision();
        refiner.swap_edge(const_cast<edge&>(*edge_iterator), current_cell);
        if(current_cell->get_mesh_revision() != before_revision + 1) {
            throw std::runtime_error("real edge swap did not emit exactly one accepted event");
        }
    }
}

constexpr std::uint64_t fnv_offset = 1469598103934665603ULL;
constexpr std::uint64_t fnv_prime = 1099511628211ULL;

void hash_bytes(std::uint64_t& hash, const void* data, const std::size_t size) {
    const auto* bytes = static_cast<const unsigned char*>(data);
    for(std::size_t index = 0; index < size; ++index) {
        hash ^= bytes[index];
        hash *= fnv_prime;
    }
}

template<typename Value>
void hash_value(std::uint64_t& hash, const Value& value) {
    static_assert(std::is_trivially_copyable_v<Value>);
    hash_bytes(hash, &value, sizeof(value));
}

std::uint64_t verify_and_digest(
    const std::vector<cell_ptr>& cells,
    const prl::core::MyocardialMaterialTransferSink& sink,
    const BenchmarkConfig& config
) {
    using namespace prl::core;
    std::uint64_t digest = fnv_offset;
    for(const auto& current_cell : cells) {
        const auto cell_id = static_cast<CellId>(current_cell->get_id());
        const auto state = sink.cell_state(cell_id);
        const auto audit = sink.last_audit(cell_id);
        const auto expected_audit_operation = config.operation_pattern == OperationPattern::split_merge
            ? RemeshOperation::edge_merge
            : RemeshOperation::edge_swap;
        const auto maximum_rebind_error = config.operation_pattern == OperationPattern::split_merge
            ? 1.0
            : 1.0e-12;
        const auto& apical = state.points.at(0);
        const auto& basal = state.points.at(1);
        if(current_cell->get_mesh_revision() != config.operations_per_cell
           || state.revision != config.operations_per_cell
           || state.points.size() != 2
           || audit.operation != expected_audit_operation
           || audit.point_count != 2
           || audit.region_retention_fraction != 1.0
           || audit.active_state_residual != 0.0
           || audit.reference_weight_residual != 0.0
           || audit.id_retention_fraction != 1.0
           || audit.maximum_fiber_norm_error > 1.0e-12
           || audit.maximum_fiber_tangency_error > 1.0e-12
           || audit.minimum_fiber_alignment < 1.0 - 1.0e-12
           || apical.material.material_point_id != cell_id * 10 + 1
           || apical.material.region != SurfaceRegion::apical
           || apical.material.active_state != std::vector<double>({0.2, 0.3})
           || std::abs(apical.reference_weight - 0.17) > 1.0e-12
           || basal.material.material_point_id != cell_id * 10 + 2
           || basal.material.region != SurfaceRegion::basal
           || basal.material.active_state != std::vector<double>({0.4, 0.7})
           || std::abs(basal.reference_weight - 0.23) > 1.0e-12
           || audit.maximum_rebind_error > maximum_rebind_error) {
            throw std::runtime_error("material-state invariant failed after multicell remeshing");
        }

        hash_value(digest, cell_id);
        hash_value(digest, state.revision);
        for(const auto& point : state.points) {
            hash_value(digest, point.material.material_point_id);
            hash_value(digest, point.material.region);
            for(const auto value : point.material.fiber_direction) hash_value(digest, value);
            for(const auto value : point.material.active_state) hash_value(digest, value);
            for(const auto vertex_id : point.host_vertex_ids) hash_value(digest, vertex_id);
            for(const auto value : point.barycentric) hash_value(digest, value);
            hash_value(digest, point.reference_weight);
        }
    }
    return digest;
}

long peak_rss_kib() {
#if defined(__linux__) || defined(__APPLE__)
    rusage usage{};
    if(getrusage(RUSAGE_SELF, &usage) != 0) return -1;
#if defined(__APPLE__)
    return usage.ru_maxrss / 1024;
#else
    return usage.ru_maxrss;
#endif
#else
    return -1;
#endif
}

BenchmarkResult run_benchmark(const BenchmarkConfig& config) {
    const auto setup_start = Clock::now();
    const auto maximum_rebind_distance = config.operation_pattern == OperationPattern::split_merge
        ? 1.0
        : 1.0e-12;
    auto sink = std::make_shared<prl::core::MyocardialMaterialTransferSink>(
        maximum_rebind_distance
    );
    local_mesh_refiner refiner(0.1, 10.0, true, sink);
    std::vector<cell_ptr> cells;
    cells.reserve(config.cell_count);
    for(std::size_t index = 0; index < config.cell_count; ++index) {
        if(index + 1 > static_cast<std::size_t>(std::numeric_limits<unsigned>::max())) {
            throw std::overflow_error("cell count exceeds cell-engine ID range");
        }
        const auto cell_id = static_cast<unsigned>(index + 1);
        auto current_cell = closed_swap_cell(cell_id, static_cast<double>(index) * 4.0);
        sink->register_cell(
            prl::cell_engine::capture_surface_snapshot(*current_cell),
            myocardial_points(*current_cell, cell_id)
        );
        cells.push_back(std::move(current_cell));
    }
    const auto setup_end = Clock::now();

    const auto worker_count = std::min(config.requested_threads, config.cell_count);
    std::atomic<std::size_t> next_cell{0};
    std::mutex failure_mutex;
    std::exception_ptr failure;
    const auto remesh_start = Clock::now();
    std::vector<std::thread> workers;
    workers.reserve(worker_count);
    for(std::size_t worker = 0; worker < worker_count; ++worker) {
        workers.emplace_back([&]() {
            try {
                while(true) {
                    const auto index = next_cell.fetch_add(1, std::memory_order_relaxed);
                    if(index >= cells.size()) return;
                    run_cell_operations(cells[index], config, refiner);
                }
            } catch(...) {
                std::lock_guard<std::mutex> lock(failure_mutex);
                if(!failure) failure = std::current_exception();
            }
        });
    }
    for(auto& worker : workers) worker.join();
    const auto remesh_end = Clock::now();
    if(failure) std::rethrow_exception(failure);

    const auto digest = verify_and_digest(cells, *sink, config);
    const auto setup_seconds = std::chrono::duration<double>(setup_end - setup_start).count();
    const auto remesh_seconds = std::chrono::duration<double>(remesh_end - remesh_start).count();
    const auto total_events = static_cast<std::uint64_t>(config.cell_count)
        * static_cast<std::uint64_t>(config.operations_per_cell);
    return {
        config,
        worker_count,
        total_events,
        setup_seconds,
        remesh_seconds,
        static_cast<double>(total_events) / remesh_seconds,
        digest,
        peak_rss_kib(),
        false,
        0,
    };
}

BenchmarkResult run_requested_benchmark(const BenchmarkConfig& config) {
    if(!config.verify_determinism) return run_benchmark(config);

    auto serial_config = config;
    serial_config.requested_threads = 1;
    serial_config.verify_determinism = false;
    const auto serial_result = run_benchmark(serial_config);
    auto parallel_result = run_benchmark(config);
    if(serial_result.semantic_digest != parallel_result.semantic_digest) {
        throw std::runtime_error("serial and parallel semantic digests differ");
    }
    parallel_result.determinism_verified = true;
    parallel_result.determinism_reference_digest = serial_result.semantic_digest;
    parallel_result.peak_rss_kib = peak_rss_kib();
    return parallel_result;
}

void print_json(const BenchmarkResult& result) {
    std::ostringstream digest;
    digest << std::hex << std::setw(16) << std::setfill('0') << result.semantic_digest;
    std::ostringstream reference_digest;
    reference_digest << std::hex << std::setw(16) << std::setfill('0')
                     << result.determinism_reference_digest;
    const char* operation_pattern = result.config.operation_pattern == OperationPattern::split_merge
        ? "split_merge"
        : "alternating_swap";
    std::cout << std::setprecision(17)
              << "{\n"
              << "  \"status\": \"passed\",\n"
              << "  \"cell_count\": " << result.config.cell_count << ",\n"
              << "  \"operations_per_cell\": " << result.config.operations_per_cell << ",\n"
              << "  \"operation_pattern\": \"" << operation_pattern << "\",\n"
              << "  \"requested_threads\": " << result.config.requested_threads << ",\n"
              << "  \"worker_threads\": " << result.worker_threads << ",\n"
              << "  \"total_events\": " << result.total_events << ",\n"
              << "  \"setup_seconds\": " << result.setup_seconds << ",\n"
              << "  \"remesh_seconds\": " << result.remesh_seconds << ",\n"
              << "  \"events_per_second\": " << result.events_per_second << ",\n"
              << "  \"peak_rss_kib\": " << result.peak_rss_kib << ",\n"
              << "  \"semantic_digest\": \"" << digest.str() << "\",\n"
              << "  \"determinism_verified\": "
              << (result.determinism_verified ? "true" : "false") << ",\n"
              << "  \"determinism_reference_digest\": ";
    if(result.determinism_verified) {
        std::cout << "\"" << reference_digest.str() << "\"";
    } else {
        std::cout << "null";
    }
    std::cout << ",\n"
              << "  \"invariants_verified\": true\n"
              << "}\n";
}

} // namespace

int main(const int argc, const char* const argv[]) {
    try {
        print_json(run_requested_benchmark(parse_arguments(argc, argv)));
        return 0;
    } catch(const std::exception& error) {
        std::cerr << "prl_multicell_remesh_benchmark: " << error.what() << '\n';
        return 1;
    }
}
