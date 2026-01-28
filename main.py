#!/usr/bin/env python3
"""
Ripple - API 影响分析工具
命令行版本：递归扫描代码目录，分析 API 引用情况
"""

import yaml
import re
import os
import argparse
from pathlib import Path
from collections import defaultdict


# 支持的代码文件扩展名
SUPPORTED_EXTENSIONS = {'.js', '.ts', '.py', '.go', '.java', '.php'}

# 需要跳过的目录
SKIP_DIRECTORIES = {
    'node_modules', '.git', 'venv', '.venv', 'env', 
    'dist', 'build', '__pycache__', '.idea', '.vscode',
    'target', 'bin', 'obj', 'vendor', 'third_party'
}


def load_api_paths(yaml_path: str) -> list:
    """从 OpenAPI YAML 文件中提取所有 API 路径"""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    paths = data.get('paths', {})
    return list(paths.keys())


def path_to_pattern(path: str) -> str:
    """
    将 API 路径转换为匹配模式
    例如：/products/{id} -> /products/
    """
    pattern = re.sub(r'/\{[^}]+\}', r'/', path)
    return pattern


def check_path_referenced(path: str, code_content: str) -> int:
    """
    检查 API 路径在代码中的引用次数
    返回引用次数
    """
    count = 0
    
    # 情况1：直接匹配完整路径（不含参数的静态路径）
    count += code_content.count(path)
    
    # 情况2：处理包含 {} 参数的路径
    if '{' in path:
        base_path = path_to_pattern(path)
        # 统计基础路径的引用次数
        count += code_content.count(base_path)
    
    return count


def should_skip_directory(dir_name: str) -> bool:
    """检查是否应该跳过该目录"""
    return dir_name in SKIP_DIRECTORIES


def scan_code_files(root_dir: str) -> list:
    """
    递归扫描代码目录，返回所有代码文件的路径列表
    """
    code_files = []
    root_path = Path(root_dir).resolve()
    
    for path in root_path.rglob('*'):
        # 跳过目录
        if path.is_dir():
            continue
        
        # 检查是否需要跳过（检查路径中的任何目录）
        should_skip = False
        for part in path.parts:
            if should_skip_directory(part):
                should_skip = True
                break
        
        if should_skip:
            continue
        
        # 检查文件扩展名
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            code_files.append(str(path))
    
    return code_files


def analyze_api_usage(api_paths: list, code_files: list) -> dict:
    """
    分析 API 在代码中的引用情况
    返回：{api_path: 引用次数}
    """
    # 初始化引用计数
    reference_counts = {path: 0 for path in api_paths}
    
    # 遍历所有代码文件
    for file_path in code_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
            
            # 检查每个 API 路径
            for api_path in api_paths:
                count = check_path_referenced(api_path, code_content)
                reference_counts[api_path] += count
                
        except Exception as e:
            print(f"  ⚠️  跳过文件（读取失败）: {file_path} - {e}")
    
    return reference_counts


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Ripple - API 影响分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --spec fixtures/api.yaml --dir ./src
  python main.py --spec openapi.yaml --dir ../my-project
        """
    )
    
    parser.add_argument(
        '--spec',
        required=True,
        help='OpenAPI YAML 文件的路径（必填）'
    )
    
    parser.add_argument(
        '--dir',
        required=True,
        help='要扫描的代码根目录（必填）'
    )
    
    args = parser.parse_args()
    
    # 验证文件路径
    spec_path = os.path.abspath(args.spec)
    code_dir = os.path.abspath(args.dir)
    
    if not os.path.exists(spec_path):
        print(f"❌ 错误：找不到 API 规范文件: {spec_path}")
        return
    
    if not os.path.exists(code_dir):
        print(f"❌ 错误：找不到代码目录: {code_dir}")
        return
    
    if not os.path.isdir(code_dir):
        print(f"❌ 错误：--dir 必须是一个目录: {code_dir}")
        return
    
    print("🔍 Ripple API 影响分析工具")
    print("=" * 50)
    
    # 1. 加载 API 路径
    print(f"\n📄 加载 API 规范: {spec_path}")
    try:
        api_paths = load_api_paths(spec_path)
        print(f"   发现 {len(api_paths)} 个 API 端点")
    except Exception as e:
        print(f"❌ 解析 YAML 失败: {e}")
        return
    
    # 2. 扫描代码文件
    print(f"\n📁 扫描代码目录: {code_dir}")
    print(f"   支持的文件类型: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
    print(f"   跳过的目录: {', '.join(sorted(SKIP_DIRECTORIES))}")
    
    code_files = scan_code_files(code_dir)
    print(f"   找到 {len(code_files)} 个代码文件")
    
    if len(code_files) == 0:
        print("⚠️ 警告：未找到任何可扫描的代码文件")
        return
    
    # 3. 分析 API 引用
    print(f"\n🔎 正在分析 API 引用情况...")
    reference_counts = analyze_api_usage(api_paths, code_files)
    
    # 4. 输出结果
    print(f"\n📊 分析结果:")
    print("-" * 50)
    
    referenced_count = 0
    unreferenced_count = 0
    
    for api_path in api_paths:
        count = reference_counts[api_path]
        if count > 0:
            print(f"✅ [引用中] {api_path} (引用次数: {count})")
            referenced_count += 1
        else:
            print(f"⚠️ [未引用] {api_path}")
            unreferenced_count += 1
    
    # 5. 汇总
    print("-" * 50)
    print(f"\n📈 汇总统计:")
    print(f"   - 已引用：{referenced_count} 个")
    print(f"   - 未引用：{unreferenced_count} 个")
    print(f"   - 总计：{len(api_paths)} 个 API")
    print(f"   - 扫描文件：{len(code_files)} 个")


if __name__ == '__main__':
    main()
