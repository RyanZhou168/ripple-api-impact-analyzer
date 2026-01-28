#!/usr/bin/env python3
"""
Ripple v1.0 - API Impact Analyzer

Features:
- Config file support (ripple.json)
- Multi-threaded scanning
- HTML visualization report (ECharts)
- JSON machine-readable output
- CI/CD integration mode
- Line number tracking with code preview
- Smart comment filtering
"""

import yaml
import re
import os
import sys
import json
import time
import argparse
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional


DEFAULT_CONFIG = {
    "extensions": [".js", ".ts", ".py", ".go", ".java", ".php"],
    "skip_dirs": [
        "node_modules", ".git", "venv", ".venv", "env",
        "__pycache__", "dist", "build", ".idea", ".vscode",
        "target", "bin", "obj", "vendor", "third_party"
    ],
    "max_workers": 4
}


def load_config(config_path: str = "ripple.json") -> dict:
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
        except Exception as e:
            print(f"Warning: Failed to load config, using defaults: {e}")
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def load_api_paths(yaml_path: str) -> List[str]:
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    paths = data.get('paths', {})
    return list(paths.keys())


def path_to_pattern(path: str) -> str:
    return re.sub(r'/\{[^}]+\}', r'/', path)


def get_comment_char(file_ext: str) -> str:
    return '#' if file_ext == '.py' else '//'


def remove_inline_comment(line: str, comment_char: str) -> str:
    comment_pos = line.find(comment_char)
    if comment_pos != -1:
        before_comment = line[:comment_pos]
        single_quotes = before_comment.count("'")
        double_quotes = before_comment.count('"')
        if single_quotes % 2 == 0 and double_quotes % 2 == 0:
            return before_comment.rstrip()
    return line


def is_multiline_comment_start(line: str, file_ext: str) -> bool:
    stripped = line.strip()
    if file_ext == '.py':
        return stripped.startswith('"""') or stripped.startswith("'''")
    return '/*' in stripped


def is_multiline_comment_end(line: str, file_ext: str) -> bool:
    stripped = line.strip()
    if file_ext == '.py':
        return '"""' in stripped or "'''" in stripped
    return '*/' in stripped


def process_code_line(line: str, file_ext: str, in_multiline_comment: bool) -> Tuple[str, bool]:
    if in_multiline_comment:
        if is_multiline_comment_end(line, file_ext):
            return "", False
        return "", True
    
    if is_multiline_comment_start(line, file_ext):
        if file_ext == '.py':
            stripped = line.strip()
            for marker in ['"""', "'''"]:
                if stripped.startswith(marker):
                    end_pos = stripped.find(marker, 3)
                    if end_pos != -1:
                        return stripped[end_pos + 3:].strip(), False
                    return "", True
        else:
            if '/*' in line:
                before = line[:line.find('/*')]
                after_marker = line[line.find('/*') + 2:]
                if '*/' in after_marker:
                    after = after_marker[after_marker.find('*/') + 2:]
                    return (before + after).strip(), False
                return before.strip(), True
    
    comment_char = get_comment_char(file_ext)
    line = remove_inline_comment(line, comment_char)
    return line, False


def find_api_references(api_path: str, lines: List[str], file_ext: str) -> List[Dict]:
    references = []
    in_multiline_comment = False
    
    for line_num, raw_line in enumerate(lines, 1):
        processed_line, in_multiline_comment = process_code_line(
            raw_line, file_ext, in_multiline_comment
        )
        
        if not processed_line:
            continue
        
        matched = False
        if api_path in processed_line:
            matched = True
        elif '{' in api_path:
            base_path = path_to_pattern(api_path)
            if base_path in processed_line:
                matched = True
        
        if matched:
            references.append({
                "line": line_num,
                "code": raw_line.strip()[:100]
            })
    
    return references


def should_skip_directory(dir_name: str, skip_dirs: List[str]) -> bool:
    return dir_name in skip_dirs


def scan_code_files(root_dir: str, config: dict) -> List[str]:
    code_files = []
    extensions = set(ext.lower() for ext in config["extensions"])
    skip_dirs = config["skip_dirs"]
    root_path = Path(root_dir).resolve()
    
    for path in root_path.rglob('*'):
        if path.is_dir():
            continue
        
        if any(should_skip_directory(part, skip_dirs) for part in path.parts):
            continue
        
        if path.suffix.lower() in extensions:
            code_files.append(str(path))
    
    return code_files


def analyze_single_file(file_path: str, api_paths: List[str], base_dir: str) -> Tuple[str, List[Tuple[str, Dict]]]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        file_ext = os.path.splitext(file_path)[1].lower()
        rel_path = os.path.relpath(file_path, base_dir)
        
        results = []
        for api_path in api_paths:
            references = find_api_references(api_path, lines, file_ext)
            for ref in references:
                results.append((api_path, {"file": rel_path, "line": ref["line"], "code": ref["code"]}))
        
        return rel_path, results
    except Exception as e:
        return os.path.relpath(file_path, base_dir), []


def analyze_api_usage_parallel(api_paths: List[str], code_files: List[str], 
                                base_dir: str, max_workers: int) -> Dict[str, List[Dict]]:
    api_locations = {path: [] for path in api_paths}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(analyze_single_file, file_path, api_paths, base_dir): file_path
            for file_path in code_files
        }
        
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                rel_path, results = future.result()
                for api_path, location in results:
                    api_locations[api_path].append(location)
            except Exception as e:
                print(f"  Warning: Failed to process {file_path}: {e}")
    
    return api_locations


def generate_html_report(api_paths: List[str], api_locations: Dict[str, List[Dict]], 
                         output_path: str, spec_path: str, code_dir: str, config: dict):
    reference_counts = {path: len(locs) for path, locs in api_locations.items()}
    
    file_api_map = defaultdict(set)
    for api_path, locations in api_locations.items():
        for loc in locations:
            file_api_map[loc["file"]].add(api_path)
    
    nodes = []
    links = []
    
    for i, api_path in enumerate(api_paths):
        count = reference_counts.get(api_path, 0)
        nodes.append({
            'id': f'api_{i}',
            'name': api_path,
            'category': 0,
            'value': count,
            'symbolSize': 30 + min(count * 5, 40),
            'label': {'show': True},
            'itemStyle': {'color': '#e74c3c'}
        })
    
    file_list = list(file_api_map.keys())
    for i, file_path in enumerate(file_list):
        api_count = len(file_api_map[file_path])
        nodes.append({
            'id': f'file_{i}',
            'name': file_path,
            'category': 1,
            'value': api_count,
            'symbolSize': 20 + min(api_count * 5, 30),
            'label': {'show': True},
            'itemStyle': {'color': '#3498db'}
        })
    
    for file_idx, file_path in enumerate(file_list):
        for api_path in file_api_map[file_path]:
            api_idx = api_paths.index(api_path)
            links.append({
                'source': f'api_{api_idx}',
                'target': f'file_{file_idx}',
                'value': 1
            })
    
    referenced_apis = sum(1 for count in reference_counts.values() if count > 0)
    unreferenced_apis = len(api_paths) - referenced_apis
    
    html_content = f'''<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ripple v1.0 - API Impact Report</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{ text-align: center; color: white; margin-bottom: 30px; position: relative; }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }}
        .header p {{ font-size: 1.1em; opacity: 0.9; }}
        .lang-switch {{
            position: absolute;
            top: 0;
            right: 0;
            background: rgba(255,255,255,0.2);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.3s;
        }}
        .lang-switch:hover {{ background: rgba(255,255,255,0.3); }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}
        .stat-card:hover {{ transform: translateY(-5px); }}
        .stat-card .number {{ font-size: 2.5em; font-weight: bold; margin-bottom: 5px; }}
        .stat-card .label {{ color: #666; font-size: 0.9em; }}
        .stat-card.api-total .number {{ color: #9b59b6; }}
        .stat-card.api-referenced .number {{ color: #27ae60; }}
        .stat-card.api-unreferenced .number {{ color: #e74c3c; }}
        .stat-card.files-scanned .number {{ color: #3498db; }}
        .chart-container {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .chart-title {{
            font-size: 1.3em;
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}
        #dependency-graph {{ width: 100%; height: 600px; }}
        .legend {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 15px;
            flex-wrap: wrap;
        }}
        .legend-item {{ display: flex; align-items: center; gap: 8px; }}
        .legend-dot {{ width: 16px; height: 16px; border-radius: 50%; }}
        .legend-dot.api {{ background: #e74c3c; }}
        .legend-dot.file {{ background: #3498db; }}
        .api-list {{
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .api-list-title {{
            font-size: 1.3em;
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}
        .api-item {{
            margin-bottom: 10px;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #e0e0e0;
        }}
        .api-header {{
            display: flex;
            align-items: center;
            padding: 15px;
            cursor: pointer;
            transition: background 0.2s;
            background: #f8f9fa;
        }}
        .api-header:hover {{ background: #e9ecef; }}
        .api-header.referenced {{ border-left: 4px solid #27ae60; }}
        .api-header.unreferenced {{ border-left: 4px solid #e74c3c; }}
        .api-path {{
            flex: 1;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.95em;
            font-weight: 500;
        }}
        .api-count {{
            background: #ecf0f1;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            color: #555;
            margin-right: 10px;
        }}
        .api-count.active {{ background: #d5f4e6; color: #27ae60; }}
        .api-count.inactive {{ background: #fadbd8; color: #e74c3c; }}
        .toggle-icon {{
            font-size: 1.2em;
            color: #666;
            transition: transform 0.3s;
        }}
        .toggle-icon.expanded {{ transform: rotate(90deg); }}
        .api-details {{ display: none; background: white; border-top: 1px solid #e0e0e0; }}
        .api-details.expanded {{ display: block; }}
        .reference-item {{
            padding: 12px 15px;
            border-bottom: 1px solid #f0f0f0;
            font-size: 0.9em;
        }}
        .reference-item:last-child {{ border-bottom: none; }}
        .ref-location {{ color: #3498db; font-weight: 500; margin-bottom: 5px; }}
        .ref-code {{
            font-family: 'Monaco', 'Consolas', monospace;
            background: #f8f9fa;
            padding: 8px 12px;
            border-radius: 4px;
            color: #333;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }}
        .no-references {{ padding: 20px; text-align: center; color: #999; font-style: italic; }}
        .footer {{ text-align: center; color: white; margin-top: 30px; opacity: 0.8; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <button class="lang-switch" onclick="toggleLanguage()">English</button>
            <h1>🌊 Ripple v1.0</h1>
            <p data-i18n="subtitle">API 影响分析报告</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card api-total">
                <div class="number">{len(api_paths)}</div>
                <div class="label" data-i18n="totalApis">API 总数</div>
            </div>
            <div class="stat-card api-referenced">
                <div class="number">{referenced_apis}</div>
                <div class="label" data-i18n="referencedApis">已引用 API</div>
            </div>
            <div class="stat-card api-unreferenced">
                <div class="number">{unreferenced_apis}</div>
                <div class="label" data-i18n="unreferencedApis">未引用 API</div>
            </div>
            <div class="stat-card files-scanned">
                <div class="number">{len(file_api_map)}</div>
                <div class="label" data-i18n="filesScanned">扫描文件数</div>
            </div>
        </div>
        
        <div class="chart-container">
            <div class="chart-title" data-i18n="chartTitle">📊 API 依赖关系图</div>
            <div id="dependency-graph"></div>
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-dot api"></div>
                    <span data-i18n="legendApi">API 端点（红色）</span>
                </div>
                <div class="legend-item">
                    <div class="legend-dot file"></div>
                    <span data-i18n="legendFile">代码文件（蓝色）</span>
                </div>
            </div>
        </div>
        
        <div class="api-list">
            <div class="api-list-title" data-i18n="listTitle">📋 API 引用详情（点击展开）</div>
            {generate_api_details_html(api_paths, api_locations)}
        </div>
        
        <div class="footer">
            <p><span data-i18n="generated">生成时间</span>: {os.path.basename(output_path)} | <span data-i18n="specFile">规范文件</span>: {os.path.basename(spec_path)}</p>
        </div>
    </div>
    
    <script>
        const translations = {{
            zh: {{
                subtitle: 'API 影响分析报告',
                totalApis: 'API 总数',
                referencedApis: '已引用 API',
                unreferencedApis: '未引用 API',
                filesScanned: '扫描文件数',
                chartTitle: '📊 API 依赖关系图',
                legendApi: 'API 端点（红色）',
                legendFile: '代码文件（蓝色）',
                listTitle: '📋 API 引用详情（点击展开）',
                generated: '生成时间',
                specFile: '规范文件',
                referenced: '引用',
                notReferenced: '未引用',
                noReferences: '暂无引用',
                categoryApi: 'API',
                categoryFile: '文件',
                tooltipRefs: '引用数',
                tooltipRefRelation: '引用关系'
            }},
            en: {{
                subtitle: 'API Impact Analysis Report',
                totalApis: 'Total APIs',
                referencedApis: 'Referenced APIs',
                unreferencedApis: 'Unreferenced APIs',
                filesScanned: 'Files Scanned',
                chartTitle: '📊 API Dependency Graph',
                legendApi: 'API Endpoint (Red)',
                legendFile: 'Code File (Blue)',
                listTitle: '📋 API References (Click to Expand)',
                generated: 'Generated',
                specFile: 'Spec File',
                referenced: 'references',
                notReferenced: 'Not referenced',
                noReferences: 'No references found',
                categoryApi: 'API',
                categoryFile: 'File',
                tooltipRefs: 'Refs',
                tooltipRefRelation: 'Reference'
            }}
        }};
        
        let currentLang = 'zh';
        
        function toggleLanguage() {{
            currentLang = currentLang === 'zh' ? 'en' : 'zh';
            document.querySelector('.lang-switch').textContent = currentLang === 'zh' ? 'English' : '中文';
            updateLanguage();
        }}
        
        function updateLanguage() {{
            const t = translations[currentLang];
            
            document.querySelectorAll('[data-i18n]').forEach(el => {{
                const key = el.getAttribute('data-i18n');
                if (t[key]) el.textContent = t[key];
            }});
            
            document.querySelectorAll('.api-count.active').forEach(el => {{
                const count = el.textContent.match(/\d+/)?.[0] || '0';
                el.textContent = `${{count}} ${{t.referenced}}`;
            }});
            
            document.querySelectorAll('.api-count.inactive').forEach(el => {{
                el.textContent = t.notReferenced;
            }});
            
            document.querySelectorAll('.no-references').forEach(el => {{
                el.textContent = t.noReferences;
            }});
            
            myChart.setOption({{
                legend: {{ data: [t.categoryApi, t.categoryFile] }},
                series: [{{
                    categories: [{{name: t.categoryApi}}, {{name: t.categoryFile}}]
                }}]
            }});
        }}
        
        const chartDom = document.getElementById('dependency-graph');
        const myChart = echarts.init(chartDom);
        
        const nodes = {json.dumps(nodes, ensure_ascii=False)};
        const links = {json.dumps(links, ensure_ascii=False)};
        
        const option = {{
            tooltip: {{
                trigger: 'item',
                formatter: function(params) {{
                    const t = translations[currentLang];
                    if (params.dataType === 'node') {{
                        const category = params.data.category === 0 ? t.categoryApi : t.categoryFile;
                        return `<strong>${{category}}</strong><br/>${{params.data.name}}<br/>${{t.tooltipRefs}}: ${{params.data.value}}`;
                    }} else {{
                        return `<strong>${{t.tooltipRefRelation}}</strong><br/>${{params.data.source}} → ${{params.data.target}}`;
                    }}
                }}
            }},
            legend: {{ data: [translations.zh.categoryApi, translations.zh.categoryFile], top: 10 }},
            series: [{{
                type: 'graph',
                layout: 'force',
                data: nodes,
                links: links,
                categories: [{{name: translations.zh.categoryApi}}, {{name: translations.zh.categoryFile}}],
                roam: true,
                label: {{ show: true, position: 'right', formatter: '{{b}}' }},
                force: {{ repulsion: 300, edgeLength: 150, gravity: 0.1 }},
                lineStyle: {{ color: 'source', curveness: 0.3, opacity: 0.6 }},
                emphasis: {{ focus: 'adjacency', lineStyle: {{ width: 4, opacity: 1 }} }}
            }}]
        }};
        
        myChart.setOption(option);
        window.addEventListener('resize', function() {{ myChart.resize(); }});
        
        document.querySelectorAll('.api-header').forEach(header => {{
            header.addEventListener('click', function() {{
                const details = this.nextElementSibling;
                const icon = this.querySelector('.toggle-icon');
                details.classList.toggle('expanded');
                icon.classList.toggle('expanded');
            }});
        }});
    </script>
</body>
</html>'''
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


def generate_api_details_html(api_paths: List[str], api_locations: Dict[str, List[Dict]]) -> str:
    items = []
    
    for api_path in api_paths:
        locations = api_locations.get(api_path, [])
        count = len(locations)
        
        if count > 0:
            header_class = "referenced"
            count_class = "active"
            count_text = f'{count} <span data-i18n="referenced">引用</span>'
        else:
            header_class = "unreferenced"
            count_class = "inactive"
            count_text = '<span data-i18n="notReferenced">未引用</span>'
        
        if locations:
            details_html = []
            for loc in locations:
                escaped_code = loc["code"].replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                details_html.append(f'''
                    <div class="reference-item">
                        <div class="ref-location">📄 {loc["file"]}:{loc["line"]}</div>
                        <div class="ref-code">{escaped_code}</div>
                    </div>
                ''')
            details_content = '\n'.join(details_html)
        else:
            details_content = '<div class="no-references" data-i18n="noReferences">暂无引用</div>'
        
        items.append(f'''
            <div class="api-item">
                <div class="api-header {header_class}">
                    <span class="api-path">{api_path}</span>
                    <span class="api-count {count_class}">{count_text}</span>
                    <span class="toggle-icon">▶</span>
                </div>
                <div class="api-details">
                    {details_content}
                </div>
            </div>
        ''')
    
    return '\n'.join(items)


def save_json_report(api_paths: List[str], api_locations: Dict[str, List[Dict]], 
                     output_path: str, spec_path: str, scan_time: float):
    report = {
        "version": "1.0",
        "spec_file": spec_path,
        "scan_time_seconds": round(scan_time, 2),
        "summary": {
            "total_apis": len(api_paths),
            "referenced_apis": sum(1 for locs in api_locations.values() if locs),
            "unreferenced_apis": sum(1 for locs in api_locations.values() if not locs)
        },
        "apis": {}
    }
    
    for api_path in api_paths:
        locations = api_locations.get(api_path, [])
        report["apis"][api_path] = {
            "referenced": len(locations) > 0,
            "reference_count": len(locations),
            "references": locations
        }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def print_terminal_report(api_paths: List[str], api_locations: Dict[str, List[Dict]], scan_time: float):
    print(f"\n📊 分析结果 (耗时: {scan_time:.2f}s):")
    print("-" * 70)
    
    referenced_count = 0
    unreferenced_count = 0
    
    for api_path in api_paths:
        locations = api_locations.get(api_path, [])
        count = len(locations)
        
        if count > 0:
            print(f"✅ {api_path}")
            referenced_count += 1
            for i, loc in enumerate(locations):
                is_last = (i == len(locations) - 1)
                prefix = "   └── " if is_last else "   ├── "
                code_preview = loc["code"][:50] + "..." if len(loc["code"]) > 50 else loc["code"]
                print(f"{prefix}{loc['file']}:{loc['line']}  {code_preview}")
        else:
            print(f"⚠️  {api_path} (未引用)")
            unreferenced_count += 1
    
    print("-" * 70)
    print(f"\n📈 汇总统计:")
    print(f"   - 已引用：{referenced_count} 个")
    print(f"   - 未引用：{unreferenced_count} 个")
    print(f"   - 总计：{len(api_paths)} 个 API")


def main():
    parser = argparse.ArgumentParser(
        description='Ripple v1.0 - API Impact Analyzer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --spec api.yaml --dir ./src
  python main.py --spec api.yaml --dir ./src --output-json result.json
  python main.py --spec api.yaml --dir ./src --fail-on-unused
        """
    )
    
    parser.add_argument('--spec', required=True, help='OpenAPI YAML file path')
    parser.add_argument('--dir', required=True, help='Code root directory')
    parser.add_argument('--output', default='report.html', help='HTML report path (default: report.html)')
    parser.add_argument('--output-json', help='JSON report path (optional)')
    parser.add_argument('--fail-on-unused', action='store_true', help='Exit with error code if unreferenced APIs found (for CI/CD)')
    parser.add_argument('--config', default='ripple.json', help='Config file path (default: ripple.json)')
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    spec_path = os.path.abspath(args.spec)
    code_dir = os.path.abspath(args.dir)
    output_path = os.path.abspath(args.output)
    
    if not os.path.exists(spec_path):
        print(f"❌ 错误：找不到 API 规范文件: {spec_path}")
        sys.exit(1)
    
    if not os.path.exists(code_dir) or not os.path.isdir(code_dir):
        print(f"❌ 错误：无效的代码目录: {code_dir}")
        sys.exit(1)
    
    print("🌊 Ripple v1.0 - API Impact Analyzer")
    print("=" * 70)
    print(f"   配置文件: {args.config}")
    print(f"   工作线程: {config['max_workers']}")
    
    print(f"\n📄 加载 API 规范: {spec_path}")
    try:
        api_paths = load_api_paths(spec_path)
        print(f"   发现 {len(api_paths)} 个 API 端点")
    except Exception as e:
        print(f"❌ 解析 YAML 失败: {e}")
        sys.exit(1)
    
    print(f"\n📁 扫描代码目录: {code_dir}")
    print(f"   扩展名: {', '.join(config['extensions'])}")
    code_files = scan_code_files(code_dir, config)
    print(f"   找到 {len(code_files)} 个代码文件")
    
    if not code_files:
        print("⚠️ 警告：未找到任何可扫描的代码文件")
        sys.exit(0)
    
    print(f"\n🔎 正在分析 API 引用 (使用 {config['max_workers']} 线程)...")
    start_time = time.time()
    api_locations = analyze_api_usage_parallel(
        api_paths, code_files, code_dir, config['max_workers']
    )
    scan_time = time.time() - start_time
    
    print_terminal_report(api_paths, api_locations, scan_time)
    
    print(f"\n📝 生成 HTML 报告...")
    try:
        generate_html_report(api_paths, api_locations, output_path, spec_path, code_dir, config)
        print(f"✅ HTML 报告: {output_path}")
    except Exception as e:
        print(f"❌ HTML 报告生成失败: {e}")
    
    if args.output_json:
        try:
            json_path = os.path.abspath(args.output_json)
            save_json_report(api_paths, api_locations, json_path, spec_path, scan_time)
            print(f"✅ JSON 报告: {json_path}")
        except Exception as e:
            print(f"❌ JSON 报告生成失败: {e}")
    
    unreferenced_count = sum(1 for locs in api_locations.values() if not locs)
    if args.fail_on_unused and unreferenced_count > 0:
        print(f"\n❌ CI/CD 检查失败: 发现 {unreferenced_count} 个未引用的 API")
        sys.exit(1)
    
    print(f"\n🎉 分析完成!")


if __name__ == '__main__':
    main()
