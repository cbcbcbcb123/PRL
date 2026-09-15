cmake_minimum_required(VERSION 3.20)

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

add_subdirectory(
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d"
    "${CMAKE_BINARY_DIR}/simucell3d"
    EXCLUDE_FROM_ALL
)

add_executable(prl_ventricle_bioform_myo ventricle_bioform_myo.cpp)
target_link_libraries(prl_ventricle_bioform_myo PRIVATE src)
target_include_directories(prl_ventricle_bioform_myo PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/mesh"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/math_modules"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/triangulation_modules"
)

add_executable(prl_ventricle_bioform_myo_v03 ventricle_bioform_myo_v03.cpp)
target_compile_definitions(prl_ventricle_bioform_myo_v03 PRIVATE
    PRL_MYO_BENDING_MODULUS=0.0
    PRL_MYO_SKIP_ACTIVE_EQUILIBRATION=1
)
target_link_libraries(prl_ventricle_bioform_myo_v03 PRIVATE src)
target_include_directories(prl_ventricle_bioform_myo_v03 PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/mesh"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/math_modules"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/triangulation_modules"
)

add_executable(prl_ventricle_bioform_myo_v03_nobend ventricle_bioform_myo_v03.cpp)
target_compile_definitions(prl_ventricle_bioform_myo_v03_nobend PRIVATE PRL_MYO_BENDING_MODULUS=0.0)
target_link_libraries(prl_ventricle_bioform_myo_v03_nobend PRIVATE src)
target_include_directories(prl_ventricle_bioform_myo_v03_nobend PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/mesh"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/math_modules"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/triangulation_modules"
)

add_executable(prl_ventricle_bioform_myo_v03_nobend_rawactive ventricle_bioform_myo_v03.cpp)
target_compile_definitions(prl_ventricle_bioform_myo_v03_nobend_rawactive PRIVATE
    PRL_MYO_BENDING_MODULUS=0.0
    PRL_MYO_SKIP_ACTIVE_EQUILIBRATION=1
)
target_link_libraries(prl_ventricle_bioform_myo_v03_nobend_rawactive PRIVATE src)
target_include_directories(prl_ventricle_bioform_myo_v03_nobend_rawactive PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/mesh"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/math_modules"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/triangulation_modules"
)

add_executable(prl_ventricle_myo_strip_v01 ventricle_myo_strip_v01.cpp)
target_compile_definitions(prl_ventricle_myo_strip_v01 PRIVATE
    PRL_MYO_BENDING_MODULUS=0.0
    PRL_MYO_SKIP_ACTIVE_EQUILIBRATION=1
)
target_link_libraries(prl_ventricle_myo_strip_v01 PRIVATE src)
target_include_directories(prl_ventricle_myo_strip_v01 PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/mesh"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/math_modules"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/triangulation_modules"
)

add_executable(prl_ventricle_myo_strip_load_boundary_v01 ventricle_myo_strip_v01.cpp)
target_compile_definitions(prl_ventricle_myo_strip_load_boundary_v01 PRIVATE
    PRL_MYO_BENDING_MODULUS=0.0
    PRL_MYO_SKIP_ACTIVE_EQUILIBRATION=1
)
target_link_libraries(prl_ventricle_myo_strip_load_boundary_v01 PRIVATE src)
target_include_directories(prl_ventricle_myo_strip_load_boundary_v01 PRIVATE
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/mesh"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/math_modules"
    "${CMAKE_CURRENT_LIST_DIR}/../../external/simucell3d/include/triangulation_modules"
)
