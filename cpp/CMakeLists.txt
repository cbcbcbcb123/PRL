cmake_minimum_required(VERSION 3.16)
project(prl_core LANGUAGES CXX)

include(CTest)
find_package(Threads REQUIRED)

add_library(prl_core STATIC src/myocardial_material_transfer.cpp)
target_compile_features(prl_core PUBLIC cxx_std_17)
target_link_libraries(prl_core PUBLIC Threads::Threads)
target_include_directories(
    prl_core
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../external/simucell3d/include>
)

if(BUILD_TESTING)
    add_executable(prl_remesh_contract_test tests/remesh_contract_test.cpp)
    target_link_libraries(prl_remesh_contract_test PRIVATE prl_core)
    add_test(NAME prl_remesh_contract_test COMMAND prl_remesh_contract_test)

    add_executable(
        prl_myocardial_material_transfer_test
        tests/myocardial_material_transfer_test.cpp
    )
    target_link_libraries(prl_myocardial_material_transfer_test PRIVATE prl_core)
    add_test(
        NAME prl_myocardial_material_transfer_swap
        COMMAND prl_myocardial_material_transfer_test edge_swap
    )
    add_test(
        NAME prl_myocardial_material_transfer_split
        COMMAND prl_myocardial_material_transfer_test edge_split
    )
    add_test(
        NAME prl_myocardial_material_transfer_merge
        COMMAND prl_myocardial_material_transfer_test edge_merge
    )
    add_test(
        NAME prl_myocardial_material_transfer_failure_atomicity
        COMMAND prl_myocardial_material_transfer_test failure_atomicity
    )
    add_test(
        NAME prl_myocardial_material_transfer_stable_host_ids
        COMMAND prl_myocardial_material_transfer_test stable_host_ids
    )
    add_test(
        NAME prl_myocardial_material_transfer_fiber_projection
        COMMAND prl_myocardial_material_transfer_test fiber_projection
    )
    add_test(
        NAME prl_myocardial_material_transfer_multicell_concurrency
        COMMAND prl_myocardial_material_transfer_test multicell_concurrency
    )
endif()
