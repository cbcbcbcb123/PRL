cmake_minimum_required(VERSION 3.20)

if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    project(prl_ventricle_bioform_myo LANGUAGES C CXX)
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

set(PRL_SIMUCELL_INCLUDE_DIRS
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/mesh"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/math_modules"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/triangulation_modules"
)

add_library(prl_bioform_model STATIC ventricle_bioform_myo_v03.cpp)
add_library(prl::bioform_model ALIAS prl_bioform_model)
target_compile_definitions(prl_bioform_model PRIVATE
    PRL_MYO_BENDING_MODULUS=0.0
    PRL_MYO_SKIP_ACTIVE_EQUILIBRATION=1
)
target_link_libraries(prl_bioform_model PUBLIC src)
target_include_directories(prl_bioform_model PUBLIC
    "${CMAKE_CURRENT_LIST_DIR}"
    ${PRL_SIMUCELL_INCLUDE_DIRS}
)

add_executable(prl_ventricle_bioform_myo_v03 ventricle_bioform_myo_v03_main.cpp)
target_link_libraries(prl_ventricle_bioform_myo_v03 PRIVATE prl::bioform_model)

add_executable(prl_ventricle_myo_strip_v01 ventricle_myo_strip_v01.cpp)
target_link_libraries(prl_ventricle_myo_strip_v01 PRIVATE prl::bioform_model)

option(PRL_BUILD_RETIRED_APPLICATIONS "Build superseded bioform entry points" OFF)
if(PRL_BUILD_RETIRED_APPLICATIONS)
    add_executable(prl_ventricle_bioform_myo ventricle_bioform_myo.cpp)
    target_link_libraries(prl_ventricle_bioform_myo PRIVATE src)
    target_include_directories(prl_ventricle_bioform_myo PRIVATE ${PRL_SIMUCELL_INCLUDE_DIRS})
endif()
