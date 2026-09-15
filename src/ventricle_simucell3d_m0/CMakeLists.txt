cmake_minimum_required(VERSION 3.20)

project(prl_ventricle_simucell3d_m0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POLICY_VERSION_MINIMUM 3.5 CACHE STRING "" FORCE)
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(ENABLE_PYTHON_BINDINGS OFF CACHE BOOL "" FORCE)
set(PRL_CELL_ENGINE_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(PRL_CELL_ENGINE_BUILD_EXECUTABLE OFF CACHE BOOL "" FORCE)

if(MSVC)
    add_compile_options($<$<COMPILE_LANGUAGE:CXX>:/EHsc>)
    add_compile_options($<$<COMPILE_LANGUAGE:CXX>:/FS>)
    add_compile_options($<$<COMPILE_LANGUAGE:CXX>:/openmp:llvm>)
    add_compile_definitions(_USE_MATH_DEFINES)
endif()

add_subdirectory(
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d"
    "${CMAKE_BINARY_DIR}/simucell3d"
    EXCLUDE_FROM_ALL
)

# Candidate-2 migration seam: project-owned value types, mesh I/O and result
# schemas only. Existing applications do not consume it in this safe slice.
set(PRL_VENTRICLE_SUPPORT_BUILD_TESTS ON)
enable_testing()
add_subdirectory(
    "${CMAKE_CURRENT_LIST_DIR}/../prl_ventricle_support"
    "${CMAKE_BINARY_DIR}/prl_ventricle_support"
)

add_executable(prl_ventricle_simucell3d_m0 ventricle_simucell3d_m0.cpp)
target_link_libraries(prl_ventricle_simucell3d_m0 PRIVATE src)
target_include_directories(prl_ventricle_simucell3d_m0 PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/mesh"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/math_modules"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/contact_models"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/triangulation_modules"
)

add_executable(prl_myo_sheet_contact_probe_v01 myo_sheet_contact_probe_v01.cpp)
target_link_libraries(prl_myo_sheet_contact_probe_v01 PRIVATE src)
get_target_property(PRL_M0_INCLUDES prl_ventricle_simucell3d_m0 INCLUDE_DIRECTORIES)
target_include_directories(prl_myo_sheet_contact_probe_v01 PRIVATE ${PRL_M0_INCLUDES})

# Expose the existing spring path only in this qualification target; core ABI stays model 2.
add_executable(prl_myo_sheet_contact_probe_v02 myo_sheet_contact_probe_v02.cpp
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/src/contact_models/contact_node_face_via_spring.cpp")
target_compile_definitions(prl_myo_sheet_contact_probe_v02 PRIVATE PRL_CONTACT_SPRING_PROBE=1)
target_link_libraries(prl_myo_sheet_contact_probe_v02 PRIVATE src)
target_include_directories(prl_myo_sheet_contact_probe_v02 PRIVATE ${PRL_M0_INCLUDES})

add_executable(prl_myo_sheet_contact_probe_v03 myo_sheet_contact_probe_v03.cpp
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/src/contact_models/contact_node_face_via_spring.cpp")
target_compile_definitions(prl_myo_sheet_contact_probe_v03 PRIVATE PRL_CONTACT_SPRING_PROBE=1)
target_link_libraries(prl_myo_sheet_contact_probe_v03 PRIVATE src)
target_include_directories(prl_myo_sheet_contact_probe_v03 PRIVATE ${PRL_M0_INCLUDES})

add_executable(prl_myo_sheet_relaxation_v01 myo_sheet_relaxation_v01.cpp
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/src/contact_models/contact_node_face_via_spring.cpp")
target_compile_definitions(prl_myo_sheet_relaxation_v01 PRIVATE PRL_CONTACT_SPRING_PROBE=1 PRL_MYO_BENDING_MODULUS=0.0 PRL_MYO_SKIP_ACTIVE_EQUILIBRATION=1)
target_link_libraries(prl_myo_sheet_relaxation_v01 PRIVATE src)
target_include_directories(prl_myo_sheet_relaxation_v01 PRIVATE ${PRL_M0_INCLUDES})

foreach(kind probe relaxation)
    add_executable(prl_myo_contact_barrier_${kind}_v01 myo_contact_barrier_${kind}_v01.cpp
        "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/src/contact_models/contact_node_face_via_spring.cpp")
    target_compile_definitions(prl_myo_contact_barrier_${kind}_v01 PRIVATE PRL_CONTACT_SPRING_PROBE=1 PRL_MYO_BENDING_MODULUS=0.0 PRL_MYO_SKIP_ACTIVE_EQUILIBRATION=1)
    target_link_libraries(prl_myo_contact_barrier_${kind}_v01 PRIVATE src)
    target_include_directories(prl_myo_contact_barrier_${kind}_v01 PRIVATE ${PRL_M0_INCLUDES})
endforeach()

# Read-only force-assembly timing; no integrator or production-kernel copy.
add_executable(prl_myo_contact_scaling_probe_v01 myo_contact_scaling_probe_v01.cpp
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/src/contact_models/contact_node_face_via_spring.cpp")
target_compile_definitions(prl_myo_contact_scaling_probe_v01 PRIVATE PRL_CONTACT_SPRING_PROBE=1)
target_link_libraries(prl_myo_contact_scaling_probe_v01 PRIVATE src)
target_include_directories(prl_myo_contact_scaling_probe_v01 PRIVATE ${PRL_M0_INCLUDES})
