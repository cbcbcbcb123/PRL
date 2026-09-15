cmake_minimum_required(VERSION 3.20)

if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    project(prl_ventricle_support LANGUAGES CXX)
    set(CMAKE_CXX_STANDARD 17)
    set(CMAKE_CXX_STANDARD_REQUIRED ON)
endif()

add_library(prl_ventricle_support STATIC
    src/result_schema.cpp
    src/surface_mesh.cpp
    src/vector3.cpp
)
add_library(prl::ventricle_support ALIAS prl_ventricle_support)
target_compile_features(prl_ventricle_support PUBLIC cxx_std_17)
target_include_directories(prl_ventricle_support
    PUBLIC
        "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>"
)

option(PRL_VENTRICLE_SUPPORT_BUILD_TESTS "Build support-library contract tests" OFF)
if(PRL_VENTRICLE_SUPPORT_BUILD_TESTS)
    enable_testing()
    add_executable(prl_ventricle_support_contract_test
        tests/support_contract_test.cpp
    )
    target_link_libraries(prl_ventricle_support_contract_test
        PRIVATE prl::ventricle_support
    )
    add_test(
        NAME prl_ventricle_support_contract
        COMMAND prl_ventricle_support_contract_test
    )
endif()
