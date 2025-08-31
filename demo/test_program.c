/*
 * ElfScope 测试程序
 * 
 * 这个程序包含了各种复杂的函数调用关系，用于测试 ElfScope 工具的功能：
 * - 直接函数调用
 * - 递归调用
 * - 相互递归调用
 * - 条件调用
 * - 函数指针调用
 * - 深层调用链
 * - 循环调用关系
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

// 前向声明
void function_a(int depth);
void function_b(int depth);
void complex_recursive_chain(int n);
void utility_function_1(void);
void utility_function_2(void);
void utility_function_3(void);
void deep_call_chain_1(int level);
void deep_call_chain_2(int level);
void deep_call_chain_3(int level);
void deep_call_chain_4(int level);
void deep_call_chain_5(int level);

// ========================================
// 工具函数组
// ========================================

void print_message(const char* msg) {
    printf("[MESSAGE] %s\n", msg);
}

void debug_info(int line, const char* func) {
    printf("[DEBUG] Line %d in %s\n", line, func);
}

void error_handler(const char* error) {
    fprintf(stderr, "[ERROR] %s\n", error);
}

// ========================================
// 数学计算函数组
// ========================================

int fibonacci_recursive(int n) {
    debug_info(__LINE__, __func__);
    
    if (n <= 1) {
        return n;
    }
    
    // 递归调用自己
    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2);
}

int factorial_recursive(int n) {
    print_message("Computing factorial");
    
    if (n <= 1) {
        return 1;
    }
    
    // 递归调用
    return n * factorial_recursive(n - 1);
}

long long power_iterative(int base, int exp) {
    utility_function_1();  // 调用工具函数
    
    long long result = 1;
    for (int i = 0; i < exp; i++) {
        result *= base;
    }
    
    return result;
}

// ========================================
// 字符串处理函数组
// ========================================

char* string_duplicate(const char* str) {
    debug_info(__LINE__, __func__);
    
    if (!str) {
        error_handler("Null string pointer");
        return NULL;
    }
    
    size_t len = strlen(str);
    char* new_str = malloc(len + 1);
    
    if (!new_str) {
        error_handler("Memory allocation failed");
        return NULL;
    }
    
    strcpy(new_str, str);
    return new_str;
}

void string_reverse(char* str) {
    utility_function_2();  // 调用工具函数
    
    if (!str) {
        error_handler("Null string pointer");
        return;
    }
    
    int len = strlen(str);
    for (int i = 0; i < len / 2; i++) {
        char temp = str[i];
        str[i] = str[len - 1 - i];
        str[len - 1 - i] = temp;
    }
}

int string_compare_custom(const char* str1, const char* str2) {
    debug_info(__LINE__, __func__);
    
    if (!str1 || !str2) {
        error_handler("Null string pointer in comparison");
        return -999;
    }
    
    // 使用标准库函数
    int result = strcmp(str1, str2);
    
    if (result == 0) {
        print_message("Strings are equal");
    }
    
    return result;
}

// ========================================
// 相互递归函数组
// ========================================

void function_a(int depth) {
    debug_info(__LINE__, __func__);
    
    if (depth <= 0) {
        print_message("Reached bottom of function_a");
        return;
    }
    
    printf("function_a: depth = %d\n", depth);
    
    if (depth % 2 == 0) {
        // 偶数深度调用 function_b
        function_b(depth - 1);
    } else {
        // 奇数深度调用工具函数
        utility_function_3();
    }
}

void function_b(int depth) {
    debug_info(__LINE__, __func__);
    
    if (depth <= 0) {
        print_message("Reached bottom of function_b");
        return;
    }
    
    printf("function_b: depth = %d\n", depth);
    
    // 总是调用 function_a，形成相互递归
    function_a(depth - 1);
    
    // 还调用一些工具函数
    if (depth > 3) {
        utility_function_1();
        utility_function_2();
    }
}

// ========================================
// 复杂调用链
// ========================================

void deep_call_chain_1(int level) {
    print_message("Entering deep_call_chain_1");
    
    if (level > 0) {
        deep_call_chain_2(level - 1);
    }
}

void deep_call_chain_2(int level) {
    debug_info(__LINE__, __func__);
    
    if (level > 0) {
        deep_call_chain_3(level - 1);
    }
    
    // 调用数学函数
    factorial_recursive(3);
}

void deep_call_chain_3(int level) {
    utility_function_1();
    
    if (level > 0) {
        deep_call_chain_4(level - 1);
    }
}

void deep_call_chain_4(int level) {
    debug_info(__LINE__, __func__);
    
    if (level > 0) {
        deep_call_chain_5(level - 1);
    }
    
    // 调用字符串函数
    char test_str[] = "hello";
    string_reverse(test_str);
}

void deep_call_chain_5(int level) {
    print_message("Reached deep_call_chain_5");
    
    if (level > 0) {
        // 回到开始，形成一个大的调用环
        deep_call_chain_1(level - 1);
    }
    
    // 调用斐波那契
    fibonacci_recursive(5);
}

// ========================================
// 函数指针和条件调用
// ========================================

typedef void (*operation_func_t)(void);

void operation_add(void) {
    print_message("Performing ADD operation");
    utility_function_1();
}

void operation_subtract(void) {
    print_message("Performing SUBTRACT operation");
    utility_function_2();
}

void operation_multiply(void) {
    print_message("Performing MULTIPLY operation");
    utility_function_3();
    
    // 递归调用一些函数
    fibonacci_recursive(3);
}

void execute_operation(int op_type) {
    debug_info(__LINE__, __func__);
    
    operation_func_t operations[] = {
        operation_add,
        operation_subtract,
        operation_multiply
    };
    
    if (op_type >= 0 && op_type < 3) {
        // 通过函数指针调用
        operations[op_type]();
    } else {
        error_handler("Invalid operation type");
    }
}

// ========================================
// 工具函数实现
// ========================================

void utility_function_1(void) {
    printf("Utility function 1 called\n");
    // 有时调用其他工具函数
    if (rand() % 3 == 0) {
        utility_function_2();
    }
}

void utility_function_2(void) {
    printf("Utility function 2 called\n");
    // 偶尔调用调试函数
    if (rand() % 4 == 0) {
        debug_info(__LINE__, __func__);
    }
}

void utility_function_3(void) {
    printf("Utility function 3 called\n");
    // 偶尔调用打印函数
    print_message("From utility_function_3");
}

// ========================================
// 复杂的递归链
// ========================================

void complex_recursive_chain(int n) {
    debug_info(__LINE__, __func__);
    
    if (n <= 0) {
        return;
    }
    
    printf("Complex recursive chain: n = %d\n", n);
    
    // 根据不同条件调用不同函数
    switch (n % 4) {
        case 0:
            function_a(n / 2);
            break;
        case 1:
            function_b(n / 2);
            break;
        case 2:
            deep_call_chain_1(n / 3);
            break;
        case 3:
            // 直接递归
            complex_recursive_chain(n - 1);
            break;
    }
    
    // 总是调用一些工具函数
    utility_function_1();
    
    // 调用数学函数
    if (n > 5) {
        factorial_recursive(n % 6);
        fibonacci_recursive(n % 8);
    }
}

// ========================================
// 数据处理函数组
// ========================================

void process_array(int* arr, size_t size) {
    debug_info(__LINE__, __func__);
    
    if (!arr || size == 0) {
        error_handler("Invalid array parameters");
        return;
    }
    
    print_message("Processing array");
    
    for (size_t i = 0; i < size; i++) {
        // 对每个元素进行一些计算
        arr[i] = factorial_recursive(arr[i] % 5);
        
        // 偶尔调用其他函数
        if (i % 3 == 0) {
            utility_function_3();
        }
    }
}

void data_analysis(int* data, size_t count) {
    print_message("Starting data analysis");
    
    if (!data) {
        error_handler("Null data pointer");
        return;
    }
    
    // 先处理数组
    process_array(data, count);
    
    // 进行一些分析
    int sum = 0;
    for (size_t i = 0; i < count; i++) {
        sum += data[i];
        
        // 调用字符串处理函数
        if (data[i] > 10) {
            char buffer[32];
            snprintf(buffer, sizeof(buffer), "Value: %d", data[i]);
            char* dup = string_duplicate(buffer);
            if (dup) {
                string_reverse(dup);
                printf("Reversed: %s\n", dup);
                free(dup);
            }
        }
    }
    
    printf("Sum: %d\n", sum);
    
    // 调用深度调用链
    deep_call_chain_1(3);
}

// ========================================
// 主程序
// ========================================

void show_help(const char* program_name) {
    printf("Usage: %s [options]\n", program_name);
    printf("Options:\n");
    printf("  -h          Show this help\n");
    printf("  -t <type>   Test type (1-5)\n");
    printf("  -v          Verbose output\n");
    
    // 调用一些函数展示调用关系
    utility_function_1();
}

int main(int argc, char* argv[]) {
    print_message("ElfScope Test Program Starting");
    
    int test_type = 1;
    int verbose = 0;
    int opt;
    
    // 简单的命令行解析
    while ((opt = getopt(argc, argv, "ht:v")) != -1) {
        switch (opt) {
            case 'h':
                show_help(argv[0]);
                return 0;
            case 't':
                test_type = atoi(optarg);
                break;
            case 'v':
                verbose = 1;
                break;
            default:
                error_handler("Invalid option");
                show_help(argv[0]);
                return 1;
        }
    }
    
    if (verbose) {
        debug_info(__LINE__, __func__);
        printf("Test type: %d\n", test_type);
    }
    
    // 根据测试类型运行不同的测试
    switch (test_type) {
        case 1:
            print_message("Running basic function tests");
            function_a(5);
            function_b(4);
            break;
            
        case 2:
            print_message("Running mathematical tests");
            printf("Fibonacci(8) = %d\n", fibonacci_recursive(8));
            printf("Factorial(6) = %d\n", factorial_recursive(6));
            printf("Power(2, 10) = %lld\n", power_iterative(2, 10));
            break;
            
        case 3:
            print_message("Running string processing tests");
            {
                char test_str[] = "Hello, ElfScope!";
                char* dup = string_duplicate(test_str);
                if (dup) {
                    printf("Original: %s\n", dup);
                    string_reverse(dup);
                    printf("Reversed: %s\n", dup);
                    free(dup);
                }
                
                int cmp_result = string_compare_custom("test", "test");
                printf("String comparison result: %d\n", cmp_result);
            }
            break;
            
        case 4:
            print_message("Running deep call chain tests");
            deep_call_chain_1(4);
            complex_recursive_chain(10);
            break;
            
        case 5:
            print_message("Running data processing tests");
            {
                int test_data[] = {1, 3, 5, 7, 9, 2, 4, 6, 8, 0};
                size_t data_size = sizeof(test_data) / sizeof(test_data[0]);
                data_analysis(test_data, data_size);
            }
            break;
            
        default:
            error_handler("Unknown test type");
            show_help(argv[0]);
            return 1;
    }
    
    // 运行一些函数指针测试
    for (int i = 0; i < 3; i++) {
        execute_operation(i);
    }
    
    // 最后的复杂调用
    complex_recursive_chain(6);
    
    print_message("ElfScope Test Program Completed");
    return 0;
}
