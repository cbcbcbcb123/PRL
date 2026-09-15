cmake_minimum_required(VERSION 3.20)

if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
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
endif()

if(NOT TARGET src)
    add_subdirectory(
        "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d"
        "${CMAKE_BINARY_DIR}/simucell3d"
        EXCLUDE_FROM_ALL
    )
endif()
if(NOT TARGET prl_bioform_model)
    add_subdirectory(
        "${CMAKE_CURRENT_LIST_DIR}/../ventricle_bioform_myo"
        "${CMAKE_BINARY_DIR}/ventricle_bioform_myo"
    )
endif()
if(NOT TARGET prl_ventricle_support)
    add_subdirectory(
        "${CMAKE_CURRENT_LIST_DIR}/../prl_ventricle_support"
        "${CMAKE_BINARY_DIR}/prl_ventricle_support"
    )
endif()

set(PRL_SIMUCELL_INCLUDE_DIRS
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/mesh"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/math_modules"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/contact_models"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/triangulation_modules"
)

add_library(prl_m0_model STATIC ventricle_simucell3d_m0.cpp)
add_library(prl::m0_model ALIAS prl_m0_model)
target_link_libraries(prl_m0_model PUBLIC src)
target_include_directories(prl_m0_model PUBLIC
    "${CMAKE_CURRENT_LIST_DIR}"
    ${PRL_SIMUCELL_INCLUDE_DIRS}
)

add_library(prl_contact_spring_probe STATIC
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/src/contact_models/contact_node_face_via_spring.cpp"
)
target_compile_definitions(prl_contact_spring_probe PUBLIC PRL_CONTACT_SPRING_PROBE=1)
target_link_libraries(prl_contact_spring_probe PUBLIC src)
target_include_directories(prl_contact_spring_probe PUBLIC ${PRL_SIMUCELL_INCLUDE_DIRS})

add_executable(prl_ventricle_simucell3d_m0 ventricle_simucell3d_m0_main.cpp)
target_link_libraries(prl_ventricle_simucell3d_m0 PRIVATE prl::m0_model)

add_executable(prl_myo_sheet_contact_probe_v01 myo_sheet_contact_probe_v01.cpp)
target_link_libraries(prl_myo_sheet_contact_probe_v01 PRIVATE prl::m0_model)

foreach(kind sheet_contact_probe_v02 sheet_contact_probe_v03 contact_barrier_probe_v01 contact_scaling_probe_v01)
    add_executable(prl_myo_${kind} myo_${kind}.cpp)
    target_link_libraries(prl_myo_${kind} PRIVATE prl::m0_model prl_contact_spring_probe)
endforeach()

foreach(kind sheet_relaxation_v01 contact_barrier_relaxation_v01)
    add_executable(prl_myo_${kind} myo_${kind}.cpp)
    target_link_libraries(prl_myo_${kind} PRIVATE prl::bioform_model prl_contact_spring_probe)
endforeach()
