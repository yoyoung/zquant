#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2025 ZQuant Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: kevin
# Contact:
#     - Email: kevin@vip.qq.com
#     - Wechat: zquant2025
#     - Issues: https://github.com/zquant/zquant/issues
#     - Documentation: https://docs.zquant.com
#     - Repository: https://github.com/zquant/zquant

"""
一键运行所有单元测试脚本
"""

import sys
import unittest
from io import StringIO


def run_all_tests(verbosity=2):
    """
    运行所有单元测试

    Args:
        verbosity: 详细程度 (0=安静, 1=正常, 2=详细)

    Returns:
        bool: 所有测试是否通过
    """
    # 创建测试加载器
    loader = unittest.TestLoader()

    # 发现并加载所有测试
    # 从 tests/unittest 目录加载测试
    start_dir = "tests/unittest"
    suite = loader.discover(start_dir=start_dir, pattern="test_*.py", top_level_dir=".")

    # 创建测试运行器
    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream, verbosity=verbosity, buffer=True)

    # 运行测试
    print("=" * 70)
    print("开始运行单元测试...")
    print("=" * 70)
    print()

    result = runner.run(suite)

    # 输出结果
    print(stream.getvalue())

    # 打印摘要
    print("=" * 70)
    print("测试摘要")
    print("=" * 70)
    print(f"运行测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"跳过: {len(result.skipped)}")

    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"  - {test}")

    if result.errors:
        print("\n错误的测试:")
        for test, traceback in result.errors:
            print(f"  - {test}")

    print("=" * 70)

    # 返回是否所有测试都通过
    return result.wasSuccessful()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="运行所有单元测试")
    parser.add_argument(
        "-v",
        "--verbosity",
        type=int,
        choices=[0, 1, 2],
        default=2,
        help="输出详细程度 (0=安静, 1=正常, 2=详细，默认: 2)",
    )
    parser.add_argument("-m", "--module", type=str, help="只运行指定模块的测试 (例如: test_security)")

    args = parser.parse_args()

    if args.module:
        # 运行指定模块的测试
        module_name = f"tests.unittest.{args.module}"
        try:
            suite = unittest.TestLoader().loadTestsFromName(module_name)
            runner = unittest.TextTestRunner(verbosity=args.verbosity)
            result = runner.run(suite)
            sys.exit(0 if result.wasSuccessful() else 1)
        except Exception as e:
            print(f"错误: 无法加载测试模块 {args.module}: {e}")
            sys.exit(1)
    else:
        # 运行所有测试
        success = run_all_tests(verbosity=args.verbosity)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
