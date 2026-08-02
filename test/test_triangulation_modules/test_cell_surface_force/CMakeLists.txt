cmake_minimum_required(VERSION 3.0)
set(CMAKE_CXX_STANDARD 17)

add_executable(test_cell_surface_force test_cell_surface_force.cpp)

target_link_libraries(
    test_cell_surface_force
    PUBLIC
        triangulation_modules
        mesh
)

target_include_directories(
    test_cell_surface_force
    PUBLIC
        "${PROJECT_SOURCE_DIR}/include/"
        "${PROJECT_SOURCE_DIR}/include/math_modules"
        "${PROJECT_SOURCE_DIR}/include/mesh"
)

add_test(
    NAME triangulation_modules_cell_surface_force_accumulation
    COMMAND test_cell_surface_force accumulation
)
add_test(
    NAME triangulation_modules_cell_surface_force_failure_atomicity
    COMMAND test_cell_surface_force failure_atomicity
)
add_test(
    NAME triangulation_modules_cell_surface_overdamped_step
    COMMAND test_cell_surface_force overdamped_step
)
add_test(
    NAME triangulation_modules_cell_surface_overdamped_failure_atomicity
    COMMAND test_cell_surface_force overdamped_failure_atomicity
)
