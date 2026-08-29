cmake_minimum_required(VERSION 3.16)
project(prl_core LANGUAGES CXX)

include(CTest)
find_package(Threads REQUIRED)

option(
    PRL_BUILD_CELL_ENGINE_INTEGRATION_TESTS
    "Build tests that link the controlled prl-cell-engine fork"
    ON
)

add_library(
    prl_core
    STATIC
        src/active_force_assembly.cpp
        src/active_myocardial_mechanics.cpp
        src/myocardial_material_transfer.cpp
        src/owned_active_overdamped_step.cpp
        src/short_trajectory.cpp
)
target_compile_features(prl_core PUBLIC cxx_std_17)
target_link_libraries(prl_core PUBLIC Threads::Threads)
target_include_directories(
    prl_core
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
)
target_include_directories(
    prl_core
    SYSTEM PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../external/simucell3d/include>
)
target_include_directories(
    prl_core
    SYSTEM PRIVATE
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../external/simucell3d/include/mesh>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../external/simucell3d/include/math_modules>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../external/simucell3d/include/contact_models>
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/../external/simucell3d/include/uspg>
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
    add_test(
        NAME prl_x1k_v11_material_prepared_transaction
        COMMAND prl_myocardial_material_transfer_test prepared_transaction
    )
    add_test(
        NAME prl_myocardial_material_active_state_update
        COMMAND prl_myocardial_material_transfer_test active_state_update
    )
    add_test(
        NAME prl_myocardial_remesh_cycle_gate_failures
        COMMAND prl_myocardial_material_transfer_test remesh_cycle_gate
    )

    add_executable(
        prl_active_myocardial_mechanics_test
        tests/active_myocardial_mechanics_test.cpp
    )
    target_link_libraries(prl_active_myocardial_mechanics_test PRIVATE prl_core)
    add_test(
        NAME prl_active_myocardial_preferred_length_force_power
        COMMAND prl_active_myocardial_mechanics_test preferred_length_force_power
    )
    add_test(
        NAME prl_active_myocardial_activation_protocol
        COMMAND prl_active_myocardial_mechanics_test activation_protocol
    )
    add_test(
        NAME prl_active_myocardial_directional_derivative
        COMMAND prl_active_myocardial_mechanics_test directional_derivative
    )
    add_test(
        NAME prl_active_myocardial_rigid_objectivity
        COMMAND prl_active_myocardial_mechanics_test rigid_objectivity
    )

    if(PRL_BUILD_CELL_ENGINE_INTEGRATION_TESTS)
        set(ENABLE_PYTHON_BINDINGS OFF CACHE BOOL "" FORCE)
        set(PRL_CELL_ENGINE_BUILD_TESTS OFF CACHE BOOL "" FORCE)
        set(PRL_CELL_ENGINE_BUILD_EXECUTABLE OFF CACHE BOOL "" FORCE)
        add_subdirectory(
            "${CMAKE_CURRENT_SOURCE_DIR}/../external/simucell3d"
            "${CMAKE_CURRENT_BINARY_DIR}/cell_engine"
            EXCLUDE_FROM_ALL
        )

        add_library(
            prl_r1_remesh_robustness
            STATIC
                src/r1_remesh_robustness.cpp
        )
        target_compile_features(prl_r1_remesh_robustness PUBLIC cxx_std_17)
        target_link_libraries(
            prl_r1_remesh_robustness
            PUBLIC
                prl_core
                triangulation_modules
                mesh
        )
        target_include_directories(
            prl_r1_remesh_robustness
            PUBLIC
                $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        )

        add_executable(
            prl_cell_engine_material_transfer_integration_test
            tests/cell_engine_material_transfer_integration_test.cpp
        )
        target_link_libraries(
            prl_cell_engine_material_transfer_integration_test
            PRIVATE
                prl_core
                triangulation_modules
                mesh
        )
        add_test(
            NAME prl_cell_engine_material_transfer_real_swap
            COMMAND prl_cell_engine_material_transfer_integration_test real_swap
        )
        add_test(
            NAME prl_cell_engine_material_transfer_failure_propagation
            COMMAND prl_cell_engine_material_transfer_integration_test failure_propagation
        )
        add_test(
            NAME prl_cell_engine_material_transfer_real_split_merge
            COMMAND prl_cell_engine_material_transfer_integration_test real_split_merge
        )
        add_test(
            NAME prl_cell_engine_active_remesh_invariance
            COMMAND prl_cell_engine_material_transfer_integration_test active_remesh_invariance
        )
        add_test(
            NAME prl_cell_engine_real_swap_remesh_energy_ledger
            COMMAND prl_cell_engine_material_transfer_integration_test
                real_swap_energy_ledger
        )
        add_test(
            NAME prl_cell_engine_real_split_merge_remesh_energy_ledger
            COMMAND prl_cell_engine_material_transfer_integration_test
                real_split_merge_energy_ledger
        )
        add_test(
            NAME prl_cell_engine_real_swap_cycle_remesh_gate
            COMMAND prl_cell_engine_material_transfer_integration_test
                real_swap_cycle_gate
        )
        add_test(
            NAME prl_cell_engine_interleaved_remesh_energy_no_cancellation
            COMMAND prl_cell_engine_material_transfer_integration_test
                interleaved_energy_no_cancellation
        )

        add_executable(
            prl_cell_engine_active_force_assembly_integration_test
            tests/cell_engine_active_force_assembly_integration_test.cpp
        )
        target_link_libraries(
            prl_cell_engine_active_force_assembly_integration_test
            PRIVATE
                prl_core
                triangulation_modules
                mesh
        )
        add_test(
            NAME prl_cell_engine_active_force_assembly_single_step
            COMMAND prl_cell_engine_active_force_assembly_integration_test
                single_step_accumulation
        )
        add_test(
            NAME prl_cell_engine_active_force_assembly_failure_atomicity
            COMMAND prl_cell_engine_active_force_assembly_integration_test
                failure_atomicity
        )
        add_test(
            NAME prl_cell_engine_active_force_assembly_post_remesh_revision
            COMMAND prl_cell_engine_active_force_assembly_integration_test
                post_remesh_revision
        )
        add_test(
            NAME prl_cell_engine_active_overdamped_single_step
            COMMAND prl_cell_engine_active_force_assembly_integration_test
                overdamped_single_step
        )
        add_test(
            NAME prl_cell_engine_active_overdamped_failure_atomicity
            COMMAND prl_cell_engine_active_force_assembly_integration_test
                overdamped_failure_atomicity
        )
        add_test(
            NAME prl_cell_engine_active_overdamped_post_remesh
            COMMAND prl_cell_engine_active_force_assembly_integration_test
                overdamped_post_remesh
        )

        add_executable(
            prl_cell_engine_owned_step_integration_test
            tests/cell_engine_owned_step_integration_test.cpp
        )
        target_link_libraries(
            prl_cell_engine_owned_step_integration_test
            PRIVATE
                prl_core
                contact_models
                triangulation_modules
                mesh
        )
        add_test(
            NAME prl_cell_engine_owned_passive_active_geometry_step
            COMMAND prl_cell_engine_owned_step_integration_test
                passive_active_geometry_step
        )
        add_test(
            NAME prl_cell_engine_owned_real_contact_step
            COMMAND prl_cell_engine_owned_step_integration_test
                real_contact_step
        )
        add_test(
            NAME prl_cell_engine_owned_post_assembly_failure_cleanup
            COMMAND prl_cell_engine_owned_step_integration_test
                post_assembly_failure_cleanup
        )
        add_test(
            NAME prl_cell_engine_owned_dual_area_damping
            COMMAND prl_cell_engine_owned_step_integration_test
                dual_area_owned_step
        )
        add_test(
            NAME prl_x1k_v11_c1_short_contact_trajectory
            COMMAND prl_cell_engine_owned_step_integration_test
                c1_short_contact_trajectory
        )

        add_executable(
            prl_short_trajectory_integration_test
            tests/short_trajectory_integration_test.cpp
        )
        target_link_libraries(
            prl_short_trajectory_integration_test
            PRIVATE
                prl_core
                triangulation_modules
                mesh
        )
        add_test(
            NAME prl_x1k_active_fixed_topology_trajectory
            COMMAND prl_short_trajectory_integration_test active_fixed_topology
        )
        add_test(
            NAME prl_x1k_active_time_refinement_gate
            COMMAND prl_short_trajectory_integration_test active_time_refinement
        )
        add_test(
            NAME prl_x1k_v11_f1_non_finite_persistence
            COMMAND prl_short_trajectory_integration_test
                v11_f1_non_finite_persistence
        )
        add_test(
            NAME prl_x1k_surface_tension_trajectory
            COMMAND prl_short_trajectory_integration_test surface_tension_trajectory
        )
        add_test(
            NAME prl_x1k_cube_singularity_diagnostic_regression
            COMMAND prl_short_trajectory_integration_test
                cube_singularity_diagnostic
        )
        add_test(
            NAME prl_x1k_sphere_force_directional_derivative
            COMMAND prl_short_trajectory_integration_test
                sphere_force_directional_derivative
        )
        add_test(
            NAME prl_x1k_sphere_directional_derivative_refinement
            COMMAND prl_short_trajectory_integration_test
                sphere_directional_refinement
        )
        add_test(
            NAME prl_x1k_sphere_instantaneous_velocity_refinement
            COMMAND prl_short_trajectory_integration_test
                sphere_instantaneous_velocity
        )
        add_test(
            NAME prl_x1k_v03_sphere_mesh_diagnostic
            COMMAND prl_short_trajectory_integration_test
                sphere_mesh_diagnostic
        )
        add_test(
            NAME prl_x1k_v03_sphere_symmetry_class_diagnostic
            COMMAND prl_short_trajectory_integration_test
                sphere_symmetry_classes
        )
        add_test(
            NAME prl_x1k_v03_family_a_asymptotic_diagnosis
            COMMAND prl_short_trajectory_integration_test
                v03_family_a
        )
        add_test(
            NAME prl_x1k_v04_repaired_family_a_diagnosis
            COMMAND prl_short_trajectory_integration_test
                v04_repaired_family_a
        )
        add_test(
            NAME prl_x1k_v04_family_b_parameterized_diagnosis
            COMMAND prl_short_trajectory_integration_test
                v04_family_b
        )
        add_test(
            NAME prl_x1k_v05_diagnostic_public_seam
            COMMAND prl_short_trajectory_integration_test
                v05_diagnostic_public_seam
        )
        add_test(
            NAME prl_x1k_v05_family_c_quality_controlled_diagnosis
            COMMAND prl_short_trajectory_integration_test
                v05_family_c
        )
        add_test(
            NAME prl_x1k_v06_local_trajectory_public_seam
            COMMAND prl_short_trajectory_integration_test
                v06_local_trajectory_public_seam
        )
        add_test(
            NAME prl_x1k_v06_family_c_short_trajectory_gate
            COMMAND prl_short_trajectory_integration_test
                v06_family_c_short_trajectory
        )
        add_test(
            NAME prl_x1k_v07_structural_identity_public_seam
            COMMAND prl_short_trajectory_integration_test
                v07_structural_identity_public_seam
        )
        add_test(
            NAME prl_x1k_v07_four_level_structural_identity_gate
            COMMAND prl_short_trajectory_integration_test
                v07_four_level_structural_identity
        )
        add_test(
            NAME prl_x1k_v07_time_floor_public_gate
            COMMAND prl_short_trajectory_integration_test
                v07_time_floor_public_gate
        )
        add_test(
            NAME prl_x1k_v07_family_c_mean_radius_time_floor_gate
            COMMAND prl_short_trajectory_integration_test
                v07_family_c_time_floor
        )

        add_executable(
            prl_x1k_r1_remesh_robustness_integration_test
            tests/r1_remesh_robustness_integration_test.cpp
        )
        target_link_libraries(
            prl_x1k_r1_remesh_robustness_integration_test
            PRIVATE
                prl_r1_remesh_robustness
        )
        add_test(
            NAME prl_x1k_v09_r1_real_remesh_robustness
            COMMAND prl_x1k_r1_remesh_robustness_integration_test
        )
        add_test(
            NAME prl_x1k_v11_r1r_survivor_remesh_robustness
            COMMAND prl_x1k_r1_remesh_robustness_integration_test
                --survivor-repair
        )

        add_executable(
            prl_x1k_v10_midpoint_collapse_diagnostic_test
            tests/r1_midpoint_collapse_diagnostic_test.cpp
        )
        target_link_libraries(
            prl_x1k_v10_midpoint_collapse_diagnostic_test
            PRIVATE
                prl_core
                triangulation_modules
                mesh
        )
        add_test(
            NAME prl_x1k_v10_midpoint_collapse_microprobe
            COMMAND prl_x1k_v10_midpoint_collapse_diagnostic_test
        )

        add_executable(
            prl_x1k_v11_transactional_rejection_test
            tests/r1_transactional_rejection_test.cpp
        )
        target_link_libraries(
            prl_x1k_v11_transactional_rejection_test
            PRIVATE
                prl_core
                triangulation_modules
                mesh
        )
        add_test(
            NAME prl_x1k_v11_candidate_three_transactional_rejection
            COMMAND prl_x1k_v11_transactional_rejection_test
        )

        add_executable(
            prl_multicell_remesh_benchmark
            benchmarks/multicell_remesh_benchmark.cpp
        )
        target_link_libraries(
            prl_multicell_remesh_benchmark
            PRIVATE
                prl_core
                triangulation_modules
                mesh
        )
        add_test(
            NAME prl_multicell_remesh_scale_smoke
            COMMAND prl_multicell_remesh_benchmark
                --cells 4
                --operations-per-cell 8
                --threads 2
        )
        add_test(
            NAME prl_multicell_remesh_serial_parallel_determinism
            COMMAND prl_multicell_remesh_benchmark
                --cells 8
                --operations-per-cell 16
                --threads 4
                --verify-determinism true
        )
        add_test(
            NAME prl_multicell_remesh_split_merge_scale_smoke
            COMMAND prl_multicell_remesh_benchmark
                --cells 4
                --operations-per-cell 2
                --threads 2
                --operation-pattern split_merge
        )
    endif()
endif()
