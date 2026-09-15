cmake_minimum_required(VERSION 3.0)
set(CMAKE_CXX_STANDARD 17)

add_executable(
    test_surface_tension_cache_precision
    test_surface_tension_cache_precision.cpp
)

target_link_libraries(
    test_surface_tension_cache_precision
    PUBLIC src mesh
)

target_include_directories(
    test_surface_tension_cache_precision
    PUBLIC
        "${PROJECT_SOURCE_DIR}/include/"
        "${PROJECT_SOURCE_DIR}/include/math_modules"
        "${PROJECT_SOURCE_DIR}/include/mesh"
)

add_test(
    NAME mesh_cell_surface_tension_cache_precision
    COMMAND test_surface_tension_cache_precision
)
