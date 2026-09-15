#include "prl/ventricle_support/result_schema.hpp"
#include "prl/ventricle_support/surface_mesh.hpp"
#include "prl/ventricle_support/vector3.hpp"

#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace support = prl::ventricle_support;

namespace {

void require(const bool condition, const char* message) {
    if(!condition) throw std::runtime_error(message);
}

void vector_contract() {
    const support::Vector3 x{1.0, 0.0, 0.0};
    const support::Vector3 y{0.0, 2.0, 0.0};
    require(support::add(x, y) == support::Vector3{1.0, 2.0, 0.0}, "vector add");
    require(support::subtract(y, x) == support::Vector3{-1.0, 2.0, 0.0}, "vector subtract");
    require(support::scale(y, 0.5) == support::Vector3{0.0, 1.0, 0.0}, "vector scale");
    require(support::dot(x, y) == 0.0, "vector dot");
    require(support::cross(x, y) == support::Vector3{0.0, 0.0, 2.0}, "vector cross");
    require(std::abs(support::norm(y) - 2.0) < 1e-15, "vector norm");
    require(support::normalized(y) == support::Vector3{0.0, 1.0, 0.0}, "vector normalize");
    bool rejected_zero = false;
    try {
        static_cast<void>(support::normalized({0.0, 0.0, 0.0}));
    } catch(const std::invalid_argument&) {
        rejected_zero = true;
    }
    require(rejected_zero, "zero vector must be rejected");
}

void mesh_contract() {
    const support::SurfaceMesh expected{
        {{0.0, 0.0, 0.0}, {1.0, 0.0, 0.0}, {0.0, 1.0, 0.0}, {0.0, 0.0, 1.0}},
        {{0, 2, 1}, {0, 1, 3}, {0, 3, 2}, {1, 2, 3}},
    };
    std::ostringstream output;
    support::write_plain_surface_mesh(output, expected);
    std::istringstream input(output.str());
    const support::SurfaceMesh actual = support::read_plain_surface_mesh(input);
    require(actual.vertices == expected.vertices, "mesh vertices round trip");
    require(actual.faces == expected.faces, "mesh faces round trip");

    bool rejected_index = false;
    try {
        std::istringstream invalid("3 1\n0 0 0\n1 0 0\n0 1 0\n0 1 9\n");
        static_cast<void>(support::read_plain_surface_mesh(invalid));
    } catch(const std::invalid_argument&) {
        rejected_index = true;
    }
    require(rejected_index, "out-of-range face index must be rejected");
}

void schema_contract() {
    const auto nodes = support::result_schema(support::ResultTable::long_doublet_nodes_v1);
    require(nodes.identifier == "prl.long_doublet.nodes.v1", "nodes schema id");
    require(nodes.column_count == 27, "nodes schema column count");
    require(nodes.header.find("curvature,pressure,fixed") != std::string_view::npos, "nodes fields");

    const auto separation = support::result_schema(support::ResultTable::long_doublet_separation_v1);
    require(separation.column_count == 6, "separation schema column count");
    require(separation.header == "step,coordinate,intercell_distance,nonincident_distance,min_height,increment", "separation fields");
    require(support::csv_escape("plain") == "plain", "plain CSV field");
    require(support::csv_escape("a,\"b\"") == "\"a,\"\"b\"\"\"", "escaped CSV field");
}

void retained_artifact_contract(
    const std::filesystem::path& mesh_path,
    const std::filesystem::path& case_path
) {
    std::ifstream mesh_stream(mesh_path);
    require(static_cast<bool>(mesh_stream), "retained mesh fixture is missing");
    unsigned cell_count{};
    require(static_cast<bool>(mesh_stream >> cell_count), "retained mesh cell count");
    require(cell_count == 2, "retained long-doublet mesh must contain two cells");
    for(unsigned cell_index = 0; cell_index < cell_count; ++cell_index) {
        const auto mesh = support::read_plain_surface_mesh(mesh_stream);
        require(mesh.vertices.size() == 194, "retained mesh vertex count");
        require(mesh.faces.size() == 384, "retained mesh face count");
    }

    const std::array<std::pair<const char*, support::ResultTable>, 6> tables{{
        {"nodes.csv", support::ResultTable::long_doublet_nodes_v1},
        {"faces.csv", support::ResultTable::long_doublet_faces_v1},
        {"states.csv", support::ResultTable::long_doublet_states_v1},
        {"cells.csv", support::ResultTable::long_doublet_cells_v1},
        {"step_audits.csv", support::ResultTable::long_doublet_step_audits_v1},
        {"separation.csv", support::ResultTable::long_doublet_separation_v1},
    }};
    for(const auto& table : tables) {
        std::ifstream stream(case_path / table.first);
        require(static_cast<bool>(stream), "retained result table is missing");
        std::string header;
        std::getline(stream, header);
        if(header != support::result_schema(table.second).header) {
            throw std::runtime_error(std::string("retained result schema mismatch: ") + table.first);
        }
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        vector_contract();
        mesh_contract();
        schema_contract();
        if(argc == 3) retained_artifact_contract(argv[1], argv[2]);
        else if(argc != 1) throw std::runtime_error("usage: support_contract_test [mesh case_directory]");
        std::cout << "prl_ventricle_support contract: passed\n";
        return 0;
    } catch(const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
